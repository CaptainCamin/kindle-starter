"""Exercise package hooks against disposable Kindle filesystem layouts."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "package"


class InstallationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="kindle setup ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.reader = self.root / "koreader"
        self.plugins = self.reader / "plugins"
        (self.plugins / "coverbrowser.koplugin").mkdir(parents=True)
        (self.plugins / "coverbrowser.koplugin/main.lua").write_text("return {}\n")
        (self.reader / "koreader.sh").write_text("#!/bin/sh\n")
        self.package = self.root / "package"
        shutil.copytree(PACKAGE, self.package)
        for plugin in ("bookshelf", "storefront"):
            directory = self.package / "payload" / f"{plugin}.koplugin"
            directory.mkdir(parents=True)
            (directory / "main.lua").write_text(f"return {{name = '{plugin}'}}\n")
            (directory / "_meta.lua").write_text("return {version = 'bundled'}\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.command("pidof", "exit 1\n")
        self.environment = dict(os.environ, KOREADER_DIR=str(self.reader))
        self.environment["PATH"] = f"{self.bin}:{os.environ['PATH']}"

    def command(self, name, body):
        script = self.bin / name
        script.write_text("#!/bin/sh\n" + body)
        script.chmod(0o755)

    def hook(self, name="install.sh", *arguments):
        return subprocess.run(
            ["sh", str(self.package / name), *arguments],
            cwd=self.package,
            env=self.environment,
            text=True,
            capture_output=True,
        )

    def test_fresh_install_sets_bookshelf_and_keeps_unrelated_data(self):
        book = self.reader / "my-book.epub"
        book.write_bytes(b"existing book")
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        for plugin in ("bookshelf", "storefront"):
            self.assertEqual(
                (self.plugins / f"{plugin}.koplugin/main.lua").read_bytes(),
                (self.package / f"payload/{plugin}.koplugin/main.lua").read_bytes(),
            )
        settings = (self.reader / "settings.reader.lua").read_text()
        self.assertIn('["start_with"] = "bookshelf"', settings)
        self.assertIn('["home_dir"] = "/mnt/us/documents"', settings)
        self.assertEqual(book.read_bytes(), b"existing book")
        self.assertFalse((self.reader / ".kindle-starter-install").exists())

    def test_reinstall_upgrade_and_uninstall_keep_user_updates_and_settings(self):
        self.assertEqual(self.hook().returncode, 0)
        settings = self.reader / "settings.reader.lua"
        settings.write_text('return {start_with = "history", plugins_disabled = {storefront = true}}\n')
        updated = self.plugins / "bookshelf.koplugin/main.lua"
        updated.write_text("return {version = 'newer-user-installed'}\n")
        custom = self.plugins / "storefront.koplugin/custom.txt"
        custom.write_bytes(b"user customization")
        expected_settings = settings.read_bytes()
        for name, arguments in (
            ("install.sh", ()),
            ("uninstall.sh", ("upgrade",)),
            ("install.sh", ("upgrade",)),
            ("uninstall.sh", ()),
        ):
            result = self.hook(name, *arguments)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_bytes(), expected_settings)
            self.assertIn("newer-user-installed", updated.read_text())
            self.assertEqual(custom.read_bytes(), b"user customization")

    def test_settings_backup_is_not_replaced_by_fresh_defaults(self):
        backup = self.reader / "settings.reader.lua.old"
        backup.write_text('return {start_with = "last"}\n')
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.reader / "settings.reader.lua").exists())
        self.assertEqual(backup.read_text(), 'return {start_with = "last"}\n')

    def test_preflight_refuses_missing_core_running_reader_and_stale_stage(self):
        core = self.reader / "koreader.sh"
        core.unlink()
        self.assertNotEqual(self.hook().returncode, 0)
        core.touch()
        self.command("pidof", "exit 0\n")
        self.assertNotEqual(self.hook().returncode, 0)
        self.command("pidof", "exit 1\n")
        stage = self.reader / ".kindle-starter-install"
        stage.mkdir()
        (stage / "recoverable.txt").write_text("previous attempt")
        self.assertNotEqual(self.hook().returncode, 0)
        self.assertEqual((stage / "recoverable.txt").read_text(), "previous attempt")
        self.assertFalse((self.plugins / "bookshelf.koplugin").exists())

    def test_incomplete_existing_plugin_and_copy_failure_leave_no_partial_install(self):
        existing = self.plugins / "storefront.koplugin"
        existing.mkdir()
        (existing / "user.txt").write_text("do not remove")
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.plugins / "bookshelf.koplugin").exists())
        self.assertEqual((existing / "user.txt").read_text(), "do not remove")
        (existing / "main.lua").write_text("return {}")
        (existing / "_meta.lua").write_text("return {}")
        shutil.rmtree(self.package / "payload/bookshelf.koplugin")
        self.assertNotEqual(self.hook().returncode, 0)
        self.assertFalse((self.reader / ".kindle-starter-install").exists())
        self.assertEqual((existing / "user.txt").read_text(), "do not remove")

    def test_failed_second_deploy_rolls_back_only_new_files(self):
        move = shutil.which("mv")
        self.command(
            "mv",
            f'case "$1" in */storefront.koplugin) exit 1;; esac\nexec "{move}" "$@"\n',
        )
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.plugins / "bookshelf.koplugin").exists())
        self.assertFalse((self.plugins / "storefront.koplugin").exists())
        self.assertFalse((self.reader / "settings.reader.lua").exists())
        self.assertFalse((self.reader / ".kindle-starter-install").exists())
        self.assertTrue((self.plugins / "coverbrowser.koplugin/main.lua").is_file())
        # KPM runs uninstall after a hook failure; that must also leave user data alone.
        self.assertEqual(self.hook("uninstall.sh").returncode, 0)
        self.assertTrue((self.reader / "koreader.sh").is_file())


if __name__ == "__main__":
    unittest.main()
