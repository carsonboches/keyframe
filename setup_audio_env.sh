#!/usr/bin/env bash
set -e

PYTHON_BIN="${PYTHON_AUDIO_BIN:-python3.10}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Could not find $PYTHON_BIN."
  echo "Basic Pitch is most reliable here in its own Python 3.10 environment."
  echo "Install Python 3.10 or run:"
  echo "  PYTHON_AUDIO_BIN=/path/to/python3.10 ./setup_audio_env.sh"
  exit 1
fi

"$PYTHON_BIN" -m venv .venv-audio
source .venv-audio/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-audio.txt

echo
echo "Audio environment ready."
echo "Test with:"
echo "  ./.venv-audio/bin/python -c \"from basic_pitch.inference import predict; print('Basic Pitch OK')\""
