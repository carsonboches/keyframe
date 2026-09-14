from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import AUDIO_PYTHON, AUDIO_TRANSCRIBE_SCRIPT


def prepare_browser_video(input_video: Path, output_video: Path):
    """Create a browser-friendly MP4 with H.264 video and AAC audio.

    iPhone/MOV recordings can contain codecs that OpenCV/QuickTime understand
    while the browser's <video> element either has no audio or cannot decode the
    media reliably. The web UI always plays this normalized file.
    """
    output_video.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_video),
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return output_video


def extract_audio(video_path: Path, wav_path: Path):
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "22050",
        str(wav_path),
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return wav_path


def transcribe_audio(wav_path: Path, output_json: Path):
    if not AUDIO_PYTHON.exists():
        raise RuntimeError(
            "The Basic Pitch environment is missing. "
            "Run ./setup_audio_env.sh first."
        )

    subprocess.run(
        [
            str(AUDIO_PYTHON),
            str(AUDIO_TRANSCRIBE_SCRIPT),
            str(wav_path),
            str(output_json),
        ],
        check=True,
    )

    with open(output_json, "r", encoding="utf-8") as file:
        return json.load(file)
