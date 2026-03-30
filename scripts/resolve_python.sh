#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    printf '%s\n' "$PROJECT_ROOT/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    printf '%s\n' python
elif command -v python3 >/dev/null 2>&1; then
    printf '%s\n' python3
else
    echo "Error: Python interpreter not found. Install python or python3, or create .venv." >&2
    exit 1
fi
