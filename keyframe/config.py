from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "static" / "projects"

AUDIO_PYTHON = ROOT / ".venv-audio" / "bin" / "python"
AUDIO_TRANSCRIBE_SCRIPT = ROOT / "keyframe" / "transcribe_audio.py"

# Audio notes that begin this close together are treated as one performed onset/chord.
AUDIO_GROUP_TOLERANCE_MS = 70

# Dynamic-programming costs.
ALIGN_GAP_COST = 1.0
ALIGN_NO_COMMON_PITCH_COST = 2.6

# Minimum quality for trusting a matched score onset.
MIN_GROUP_MATCH_SCORE = 0.18

# Padding around measure playback.
MEASURE_PREROLL_MS = 100
MEASURE_POSTROLL_MS = 120

# If the final measure has no later aligned onset, use this much after its last match.
FINAL_MEASURE_TAIL_MS = 1200

# Full-frame browser video.
WARP_OUTPUT_WIDTH = 1300
WARP_OUTPUT_HEIGHT = 380
