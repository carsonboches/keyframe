from __future__ import annotations

import shutil
import subprocess
import sys

from .config import AUDIO_PYTHON, PROJECTS_DIR


def run_doctor():
    checks = []

    checks.append(("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0]))
    checks.append(("ffmpeg", shutil.which("ffmpeg") is not None, shutil.which("ffmpeg") or "missing"))

    try:
        import flask
        checks.append(("Flask", True, getattr(flask, "__version__", "installed")))
    except Exception as exc:
        checks.append(("Flask", False, str(exc)))

    audio_ok = False
    audio_detail = "missing"
    if AUDIO_PYTHON.exists():
        try:
            result = subprocess.run(
                [
                    str(AUDIO_PYTHON),
                    "-c",
                    "from basic_pitch.inference import predict; print('OK')",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            audio_ok = result.returncode == 0
            audio_detail = "OK" if audio_ok else (result.stderr.strip()[-300:] or "import failed")
        except Exception as exc:
            audio_detail = str(exc)

    checks.append(("Basic Pitch audio env", audio_ok, audio_detail))

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    checks.append(("Projects directory", True, str(PROJECTS_DIR)))

    width = max(len(name) for name, _, _ in checks)

    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"{name:<{width}} : {'OK' if ok else 'FAIL'}  {detail}")

    return all_ok
