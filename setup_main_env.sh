#!/usr/bin/env bash
set -e

PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Could not find $PYTHON_BIN."
  echo "Install Python 3.12 or run: PYTHON_BIN=/path/to/python ./setup_main_env.sh"
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Main environment ready."
echo "Activate with: source .venv/bin/activate"
