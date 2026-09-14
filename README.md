# KeyFrame

KeyFrame synchronizes a piano performance recording with a MusicXML score.

## Workflow

1. Upload a performance video.
2. Upload the matching MusicXML/MXL score.
3. KeyFrame converts the full recording to a browser-friendly MP4.
4. It extracts and transcribes the performance audio.
5. It parses score onsets from MusicXML.
6. It aligns the detected performance notes to the score.
7. It calculates measure timing.
8. The project page renders the score beside the complete recording.
9. Click a score measure to jump to and optionally loop that measure in the video.

## Run

```bash
./setup_main_env.sh
source .venv/bin/activate
./setup_audio_env.sh
python keyframe.py doctor
python app.py
```

Open the local Flask address shown in the terminal.

## Command line

```bash
python keyframe.py process --video "/path/to/performance.mov" --score "/path/to/score.mxl"
```

> Note: Sample files are available in the samples/ directory.

## Main files

- `app.py` — upload and project web routes.
- `keyframe/processor.py` — full processing pipeline.
- `keyframe/audio.py` — browser-video preparation, audio extraction, transcription.
- `keyframe/musicxml.py` — MusicXML score parsing.
- `keyframe/alignment.py` — score/performance alignment and measure timings.
- `static/js/project.js` — score rendering, measure clicking, playback, looping.


