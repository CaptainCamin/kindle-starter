#!/bin/sh
set -eu

# KPM also calls this hook after a failed install. Never remove user-owned files.
if [ "${1:-}" != upgrade ]; then
    echo "Starter package removed. Installed plugins, books and preferences are retained."
    echo "Remove plugins with KOReader's plugin manager if desired."
    echo "Warning: uninstalling the separate official koreader package deletes its entire directory."
fi
