#!/bin/bash
# Kramnik chess, the desktop app (PyQt6): ./run.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${SGW_BUILD:-}" ] && b=$(git -C "$ROOT" rev-parse --short=12 HEAD 2>/dev/null); then
    git -C "$ROOT" diff --quiet HEAD -- ":(glob)**/*.py" 2>/dev/null || b="$b-dirty"
    export SGW_BUILD="$b"
fi
cd "$ROOT" && exec python3 -m kramnikchess "$@"
