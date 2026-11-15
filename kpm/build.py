#!/usr/bin/env python3
"""Build the static KPM repository with pinned upstream release assets."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile


ROOT = Path(__file__).resolve().parent
BUILD = ROOT.parent / "build"
SITE = BUILD / "site"


def download(spec):
    """Only return cached or downloaded inputs that match the lockfile."""
    cache = BUILD / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / spec["sha256"]
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as output:
            temporary = Path(output.name)
            try:
                print(f"Downloading {spec['url']}", flush=True)
                with urlopen(spec["url"], timeout=120) as response:
                    shutil.copyfileobj(response, output)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != spec["sha256"]:
            temporary.unlink()
            raise ValueError(f"SHA-256 mismatch: {spec['url']}")
        temporary.replace(target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError(f"Corrupt cached input; remove {target} and retry")
    return target


def unpack_plugin(archive, destination, plugin_id):
    # Check every member before extraction; reject links and paths outside the plugin.
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != f"{plugin_id}.koplugin"
                or any(c in entry.filename for c in "\\\r\n")
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError(f"Unsafe plugin archive entry: {entry.filename}")
        for required in ("main.lua", "_meta.lua"):
            bundle.getinfo(f"{plugin_id}.koplugin/{required}")
        bundle.extractall(destination)


def main():
    if sys.version_info < (3, 12):
        raise SystemExit("Python 3.12+ is required by the pinned upstream KPM helper")
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    manifest = json.loads((ROOT / "package/manifest.json").read_text())
    helper = download(lock["kpm_helper"])
    BUILD.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BUILD) as temporary:
        work = Path(temporary)
        package = work / "package"
        shutil.copytree(ROOT / "package", package)
        shutil.copyfile(ROOT / "LICENSE", package / "LICENSE")
        shutil.copyfile(ROOT / "sources.lock.json", package / "sources.lock.json")
        (package / "payload").mkdir()
        (package / "licenses").mkdir()
        site = work / "site"
        (site / "sources").mkdir(parents=True)
        notices = [
            "# Third-party software\n",
            "Release payloads are unmodified. Upstream license and asset notices apply.",
            "Matching source archives are provided in the KPM repository's sources/ directory.",
            "Immutable upstream source URLs and SHA-256 hashes are also in sources.lock.json.\n",
        ]
        for plugin in lock["plugins"]:
            unpack_plugin(download(plugin), package / "payload", plugin["id"])
            source = download(plugin["source"])
            source_name = f"{plugin['id']}-{plugin['version']}-source.tar.gz"
            shutil.copyfile(source, site / "sources" / source_name)
            with tarfile.open(source) as archive:
                with archive.extractfile(plugin["source"]["license_path"]) as license_file:
                    (package / "licenses" / f"{plugin['id']}.txt").write_bytes(license_file.read())
            notices.append(
                f"- {plugin['id']} {plugin['version']}: {plugin['license']}; "
                f"source: sources/{source_name}; upstream: {plugin['source']['url']}"
            )
        notices.append(
            "\nKOReader is a separate dependency, not redistributed here. "
            "Its own package supplies its software and license notices. "
            "The KPM helper is a build-only tool whose contents are CC0."
        )
        (package / "THIRD_PARTY.md").write_text("\n".join(notices) + "\n")
        for hook in ("install.sh", "uninstall.sh"):
            subprocess.run(["sh", "-n", str(package / hook)], check=True)
        subprocess.run(
            [sys.executable, str(helper), "package", "pack", str(package), str(work)],
            check=True,
        )
        archive = next(work.glob("*.kpkg"))
        # Use the upstream repository writer as well as its package packer.
        index = {
            "manifest_version": 2,
            "id": "kindle-starter",
            "name": "Kindle Starter",
            "description": "KOReader starter setup with Bookshelf and Storefront",
            "packages": {},
        }
        (site / "manifest.json").write_text(json.dumps(index, indent=2) + "\n")
        subprocess.run(
            [sys.executable, str(helper), "repo", "add", str(site), str(archive)],
            check=True,
        )
        shutil.copyfile(ROOT / "sources.lock.json", site / "sources.lock.json")
        shutil.copyfile(package / "THIRD_PARTY.md", site / "THIRD_PARTY.md")
        (site / ".nojekyll").touch()
        checksums = []
        for path in sorted(site.rglob("*")):
            if path.is_file():
                checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(site)}")
        (site / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
        # Do not replace the previous successful build if a download or packing fails.
        if SITE.exists():
            shutil.rmtree(SITE)
        shutil.move(str(site), SITE)
    print(f"Built {manifest['id']} into {SITE}")


if __name__ == "__main__":
    main()
