from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from .alignment import align_onsets, build_measure_timing, group_audio_events
from .audio import extract_audio, prepare_browser_video, transcribe_audio
from .config import PROJECTS_DIR
from .musicxml import parse_score_onsets


def prepare_project_inputs(video_path, score_path, project_id=None):
    """Copy the user's original video and score into a KeyFrame project.

    KeyFrame no longer performs visual keyboard calibration or perspective
    correction. The full recording is preserved exactly as framed by the user.
    """
    video_path = Path(video_path).resolve()
    score_path = Path(score_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not score_path.exists():
        raise FileNotFoundError(f"Score not found: {score_path}")

    project_id = project_id or uuid.uuid4().hex[:12]
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    source_video = project_dir / f"source{video_path.suffix.lower() or '.mov'}"
    stored_score = project_dir / f"score{score_path.suffix.lower() or '.musicxml'}"

    shutil.copy2(video_path, source_video)
    shutil.copy2(score_path, stored_score)

    return {
        "project_id": project_id,
        "source_video": str(source_video),
        "stored_score": str(stored_score),
    }


def process_prepared_project(project_id):
    project_dir = PROJECTS_DIR / project_id

    source_candidates = sorted(project_dir.glob("source.*"))
    score_candidates = sorted(project_dir.glob("score.*"))
    if not source_candidates or not score_candidates:
        raise FileNotFoundError("Prepared project inputs were not found.")

    source_video = source_candidates[0]
    stored_score = score_candidates[0]
    browser_video = project_dir / "performance.mp4"
    audio_wav = project_dir / "audio.wav"
    audio_json = project_dir / "audio_notes.json"
    alignment_json = project_dir / "alignment.json"
    project_json = project_dir / "project.json"

    print("[1/4] Parsing MusicXML")
    score_onsets, measure_numbers = parse_score_onsets(stored_score)

    print("[2/4] Creating full-frame browser video")
    # Only normalize the codec/container for browser playback. Do not crop,
    # warp, stretch, or otherwise change the user's framing.
    prepare_browser_video(source_video, browser_video)

    print("[3/4] Transcribing performance audio")
    extract_audio(source_video, audio_wav)
    audio_payload = transcribe_audio(audio_wav, audio_json)
    audio_events = audio_payload["events"]
    audio_groups = group_audio_events(audio_events)

    print("[4/4] Aligning score to performance")
    matches, alignment_cost = align_onsets(audio_groups, score_onsets)
    measures = build_measure_timing(matches, measure_numbers, audio_events)

    report = {
        "score_onsets": len(score_onsets),
        "audio_onsets": len(audio_groups),
        "matched_onsets": len(matches),
        "alignment_cost": round(alignment_cost, 4),
        "matches": matches,
    }
    with open(alignment_json, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    payload = {
        "project_id": project_id,
        "title": stored_score.stem,
        "video_url": f"/static/projects/{project_id}/{browser_video.name}",
        "score_url": f"/static/projects/{project_id}/{stored_score.name}",
        "measures": measures,
        "alignment": {
            "score_onsets": len(score_onsets),
            "audio_onsets": len(audio_groups),
            "matched_onsets": len(matches),
            "cost": round(alignment_cost, 4),
        },
    }
    with open(project_json, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"Project ready: {project_id}")
    return payload


def process_project(video_path, score_path, project_id=None):
    prepared = prepare_project_inputs(video_path, score_path, project_id=project_id)
    return process_prepared_project(prepared["project_id"])
