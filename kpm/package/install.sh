#!/bin/sh
set -eu

# The override permits installation tests without writing to a real Kindle tree.
reader=${KOREADER_DIR:-/mnt/us/koreader}
stage="$reader/.kindle-starter-install"
added_bookshelf=false
added_storefront=false
added_settings=false

if [ ! -f "$reader/koreader.sh" ] || [ ! -f "$reader/plugins/coverbrowser.koplugin/main.lua" ]; then
    echo "Install the official KOReader KPM dependency first (including Cover browser)." >&2
    exit 1
fi
if pidof luajit >/dev/null 2>&1; then
    echo "Close KOReader and other LuaJIT applications before installing." >&2
    exit 1
fi
if ! mkdir "$stage"; then
    echo "Another or interrupted setup exists at $stage. See the recovery instructions." >&2
    exit 1
fi

cleanup() {
    result=$?
    trap - 0 HUP INT TERM
    if [ "$result" -ne 0 ]; then
        # Only undo files created by this attempt. Existing plugins are untouched.
        if "$added_settings"; then rm -f "$reader/settings.reader.lua"; fi
        if "$added_storefront"; then rm -rf "$reader/plugins/storefront.koplugin"; fi
        if "$added_bookshelf"; then rm -rf "$reader/plugins/bookshelf.koplugin"; fi
    fi
    rm -rf "$stage"
    exit "$result"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

# Copy both before deploying either, so a copy/space failure leaves no partial setup.
for plugin in bookshelf storefront; do
    if [ -e "$reader/plugins/$plugin.koplugin" ] || [ -L "$reader/plugins/$plugin.koplugin" ]; then
        if [ ! -f "$reader/plugins/$plugin.koplugin/main.lua" ] || [ ! -f "$reader/plugins/$plugin.koplugin/_meta.lua" ]; then
            echo "Existing $plugin is incomplete; back it up and repair it before retrying." >&2
            exit 1
        fi
        echo "Keeping existing $plugin (including its version and customizations)."
    else
        cp -R "payload/$plugin.koplugin" "$stage/"
    fi
done

if [ -e "$stage/bookshelf.koplugin" ]; then
    mv "$stage/bookshelf.koplugin" "$reader/plugins/"
    added_bookshelf=true
fi
if [ -e "$stage/storefront.koplugin" ]; then
    mv "$stage/storefront.koplugin" "$reader/plugins/"
    added_storefront=true
fi

if [ ! -e "$reader/settings.reader.lua" ] && [ ! -L "$reader/settings.reader.lua" ] &&
        [ ! -e "$reader/settings.reader.lua.old" ] && [ ! -L "$reader/settings.reader.lua.old" ]; then
    cp settings.reader.lua "$stage/settings.reader.lua"
    mv "$stage/settings.reader.lua" "$reader/settings.reader.lua"
    added_settings=true
    echo "Fresh installation: Bookshelf is the home screen."
else
    echo "Keeping your KOReader settings. Enable Bookshelf, Storefront and Cover browser if disabled."
    echo "To use Bookshelf as home, select Start with > bookshelf in the file browser menu."
fi

echo "Launch the official KOReader scriptlet, or run ;kpm launch koreader."
echo "Use Bookshelf and Storefront's own updaters; this starter package will not replace them."
