#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! cmp -s requirements.txt .venv/installed-requirements.txt; then
  .venv/bin/python -m pip install -r requirements.txt
  cp requirements.txt .venv/installed-requirements.txt
fi
if .venv/bin/python build.py "$@"; then
  open docs/index.html
else
  echo 'The update failed. See the message above.'
  read -r -p 'Press Enter to close.'
  exit 1
fi
