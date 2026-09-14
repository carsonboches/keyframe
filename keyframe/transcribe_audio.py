"""Run Basic Pitch inside the dedicated audio environment."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: transcribe_audio.py <input.wav> <output.json>"
        )

    input_wav = Path(sys.argv[1])
    output_json = Path(sys.argv[2])

    try:
        from basic_pitch.inference import predict
    except Exception as exc:
        raise RuntimeError(
            "Basic Pitch could not be imported in .venv-audio. "
            "Run ./setup_audio_env.sh."
        ) from exc

    model_output, midi_data, note_events = predict(str(input_wav))

    events = []

    # Basic Pitch commonly returns tuples:
    # (start_time_s, end_time_s, pitch_midi, amplitude, pitch_bends)
    for note in note_events:
        start_s = float(note[0])
        end_s = float(note[1])
        midi = int(round(note[2]))
        amplitude = float(note[3]) if len(note) > 3 else 0.0

        events.append({
            "onset_ms": int(round(start_s * 1000)),
            "offset_ms": int(round(end_s * 1000)),
            "duration_ms": int(round((end_s - start_s) * 1000)),
            "midi": midi,
            "amplitude": amplitude,
        })

    events.sort(key=lambda event: (event["onset_ms"], event["midi"]))

    payload = {
        "model": "spotify/basic-pitch",
        "events": events,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"Transcribed {len(events)} audio note events -> {output_json}")


if __name__ == "__main__":
    main()
