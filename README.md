# Kindle Starter

A starter package for **KOReader + Bookshelf + Storefront** on already-jailbroken
Kindles with working KPM. KOReader comes from the official KindleModding repository;
this repository bundles the two plugins, not another copy of KOReader.

**Status:** experimental preview, not a hardware-tested release. GitHub Pages
publication is manual. Nothing is installed on your Kindle by building this project.

Repository: [CaptainCamin/kindle-starter](https://github.com/CaptainCamin/kindle-starter).
KPM manifest: <https://captaincamin.github.io/kindle-starter/manifest.json>.

## Package behavior

`kindle-starter` installs missing Bookshelf and Storefront plugin directories.
On a fresh KOReader installation, it selects Bookshelf as the home screen and
`/mnt/us/documents` as the library home. It uses the official KOReader launcher.
Storefront appears in KOReader's Tools menu.

- Existing plugin installations and preferences are **never overwritten**. If a
  plugin directory is incomplete, installation stops rather than trying to repair it.
- With existing settings, enable Bookshelf, Storefront and the built-in Cover browser
  if disabled. To select the shelf as home, use **Start with → bookshelf** in the
  file browser menu. Existing disabled-plugin/security choices are preserved.
- Subsequent updates use KOReader, Bookshelf and Storefront's own update mechanisms.
  Reinstalling/upgrading this starter package only adds missing plugins; it does
  not enforce or downgrade plugin versions. The lockfile describes the bundled
  starting versions, not the user's eventual installation.
- Removing **this starter package** retains the installed plugins and preferences.
  Remove plugins through KOReader's plugin manager if desired.
- **Warning:** removing the separate official `koreader` KPM package currently
  deletes `/mnt/us/koreader`, including plugins, settings and any books placed there.
  Back it up before removal. Book sidecars and settings are not backed up by this package.

The initial target is `kindlehf` (**firmware 5.16.3+**, on a recognized and
supported model). It does not jailbreak stock devices or install KPM. Older
`kindlepw2` and legacy targets are not advertised until tested. Firmware
compatibility alone does not establish jailbreak availability; use the
[official wizard](https://kindlemodding.org/jailbreak-wizard.html).

The initial dependency range is official KOReader **KPM packaging version**
2026.7.2 through, but excluding, 2026.8.0. The inspected 2026.7.2 package contains
upstream KOReader v2026.07.1. Later KOReader OTA changes are not reflected in KPM's
database. Widen the dependency range only after checking compatibility.

## Build and check

Requires Python **3.12+**, POSIX `sh`, and network access to GitHub on the build
machine. A Kindle does not need Python, Git, Node or a GitHub account.

```sh
python3 -m unittest discover -s kpm/tests -v
python3 kpm/build.py
```

The build verifies every download against `kpm/sources.lock.json`, validates
plugin archive paths, and uses the pinned upstream `kpm-helper.py` to pack the
package and write the repository index. No install-time GitHub downloads or
credentials are embedded. Reusable verified inputs are cached in `build/downloads`.

The complete static repository is generated in `build/site/`:

- `manifest.json`: KPM repository index with absolute GitHub Pages artifact URLs,
  so a direct HTTP redirect to the manifest can also be used with `add-repo`.
- `packages/kindle-starter/artifacts/*.kpkg`: installer and plugin payloads.
- `sources/`: matching upstream source archives, including build scripts/notices.
- `sources.lock.json`, `THIRD_PARTY.md`, `SHA256SUMS`: provenance, licenses and hashes.

Serve **all** of `build/site`, including `sources/`, from the same HTTPS base URL.
If moving or forking the repository, update the canonical artifact base URL in
`kpm/build.py` before building. Short links must redirect directly to the JSON,
without a preview page, login or CAPTCHA; the full manifest URL above remains usable.
Keep corresponding sources available for every package version you distribute.
The build currently publishes the version in `kpm/package/manifest.json`; bump it
for a changed release. It does not build a historical repository of prior versions.

## Publish on GitHub Pages

1. Commit release changes to `CaptainCamin/kindle-starter`. No GitHub repository is
   created and no remote is changed by the build scripts in this project.
2. In **Settings → Pages**, select **GitHub Actions** as the build/deployment source.
3. In **Actions**, run **Publish KPM repository** on the release commit. This is a
   manual public deployment; ordinary pushes and pull requests only check/build.
4. Use the Pages deployment's actual URL with `/manifest.json` appended. Confirm
   the JSON, referenced package and source archives are publicly downloadable.
5. Add the repository once, then run these commands separately in the Kindle search bar:

```text
;kpm add-repo https://captaincamin.github.io/kindle-starter/manifest.json
;kpm update
;kpm install kindle-starter
```

The default official repository must remain configured to resolve `koreader`.
After installation, open the normal **KOReader** scriptlet or run
`;kpm launch koreader`. This setup package intentionally adds no duplicate launcher.
Network access is required for KPM downloads and Storefront catalogue refreshes.
Reading and browsing local books work offline; no PAT is required for initial setup.

The `Check KPM package` workflow runs the hook tests and a real build and attaches
the generated repository for review without publishing it.

## Validation and recovery

Before publishing as a supported release, test on a real Kindle: fresh install,
existing preferences/disabled plugins, launching Bookshelf, opening a book,
Storefront download, exit, sleep/wake, offline use and reinstall/uninstall.
The host tests validate filesystem effects; they cannot validate Kindle UI or power
management. No firmware update, jailbreak or rootfs change belongs in these hooks.

Exit KOReader before installing. Hooks refuse installation while a LuaJIT process
is running, because replacing live plugin files is unsafe. They stage both payloads
before deploying and roll back new files on ordinary command failure. A power loss
can leave a partial **additive** setup or `.kindle-starter-install` staging directory;
existing plugins/preferences are not overwritten. With KOReader and KPM stopped,
inspect and remove **only** `/mnt/us/koreader/.kindle-starter-install` after an
interruption, then retry. Do not delete the entire `koreader` directory. Contact a
KindleModding helper if unsure whether an installation is still running.

For host integration tests only, `KOREADER_DIR` redirects the hook's target tree.
KPM uses the default `/mnt/us/koreader`. Do not point it at a live installation
while KOReader is running.

## Upstream software and licenses

- [KOReader](https://github.com/koreader/koreader): separate AGPL-3.0 dependency.
- [Bookshelf](https://github.com/AndyHazz/bookshelf.koplugin): AGPL-3.0.
- [Storefront](https://github.com/ultimatejimmy/storefront.koplugin): GPL-3.0.
- [KPM helper](https://github.com/KindleModding/KPM/blob/main/kpm-helper.py): CC0
  build tool; KPM itself has its own license.

Project-owned packaging code under `kpm/` uses its scoped MIT license. Upstream
plugins/assets retain their own licenses and attribution. The build includes full
upstream plugin license texts even when a release ZIP omits its root license, and
hosts the matching source archives. No commercial theme packs are included.
