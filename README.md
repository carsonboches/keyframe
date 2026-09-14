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

## Sample Files

Want to try KeyFrame without your own recording and score?

Sample files are available on [Google Drive](https://drive.google.com/drive/folders/1lMi5dIqtS9cwZ3QsBR8CmXVNHkQ_uB56?usp=share_link).

The folder contains:
- A sample piano performance recording
- The corresponding MusicXML score

Download both files and upload them to KeyFrame to test the application.

## Main files

- `app.py` — upload and project web routes.
- `keyframe/processor.py` — full processing pipeline.
- `keyframe/audio.py` — browser-video preparation, audio extraction, transcription.
- `keyframe/musicxml.py` — MusicXML score parsing.
- `keyframe/alignment.py` — score/performance alignment and measure timings.
- `static/js/project.js` — score rendering, measure clicking, playback, looping.


