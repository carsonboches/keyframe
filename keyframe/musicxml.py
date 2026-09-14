from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET


STEP_TO_SEMITONE = {
    "C": 0, "D": 2, "E": 4, "F": 5,
    "G": 7, "A": 9, "B": 11,
}


def local_name(tag: str) -> str:
    return tag.split("}")[-1]


def namespace(root) -> str:
    if root.tag.startswith("{"):
        return root.tag[1:].split("}")[0]
    return ""


def tag(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}" if ns else name


def duration_ticks(element, ns: str) -> int:
    text = element.findtext(tag(ns, "duration"))
    if text is None:
        return 0
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def note_midi(note, ns: str):
    pitch = note.find(tag(ns, "pitch"))
    if pitch is None:
        return None

    step = pitch.findtext(tag(ns, "step"))
    octave = pitch.findtext(tag(ns, "octave"))
    alter = pitch.findtext(tag(ns, "alter"), default="0")

    if step is None or octave is None:
        return None

    return (
        12 * (int(octave) + 1)
        + STEP_TO_SEMITONE[step]
        + int(round(float(alter)))
    )


@dataclass
class ScoreOnset:
    measure_index: int
    measure_number: str
    onset_ticks: int
    midis: list[int]


def _read_musicxml_bytes(score_path: Path) -> bytes:
    """Return the actual MusicXML XML bytes.

    Supports:
    - plain .musicxml / .xml
    - compressed .mxl
    - ZIP-compressed MusicXML even when the filename has the wrong extension
    """
    score_path = Path(score_path)

    if not score_path.exists():
        raise FileNotFoundError(f"Score not found: {score_path}")

    if zipfile.is_zipfile(score_path):
        with zipfile.ZipFile(score_path, "r") as archive:
            names = archive.namelist()

            # Standard MXL files identify the root score in container.xml.
            container_name = "META-INF/container.xml"
            if container_name in names:
                container_root = ET.fromstring(archive.read(container_name))

                rootfile = None
                for element in container_root.iter():
                    if local_name(element.tag) == "rootfile":
                        rootfile = element.attrib.get("full-path")
                        if rootfile:
                            break

                if rootfile and rootfile in names:
                    return archive.read(rootfile)

            # Fallback for nonstandard ZIPs: use the first likely MusicXML file.
            candidates = [
                name for name in names
                if name.lower().endswith((".musicxml", ".xml"))
                and not name.startswith("META-INF/")
            ]

            if not candidates:
                raise ValueError(
                    "The uploaded score is a ZIP/compressed file, but no MusicXML "
                    "document was found inside it."
                )

            return archive.read(candidates[0])

    return score_path.read_bytes()


def _parse_musicxml(score_path: Path):
    raw = _read_musicxml_bytes(score_path)

    # UTF-8 BOM is legal, but stripping it makes malformed exported files easier
    # to handle consistently.
    raw = raw.lstrip(b"\xef\xbb\xbf")

    # Some editors accidentally prepend whitespace before the XML declaration.
    raw = raw.lstrip()

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        prefix = raw[:80]
        raise ValueError(
            "The uploaded score is not valid MusicXML/XML. "
            f"XML parser error: {exc}. "
            f"File begins with: {prefix!r}"
        ) from exc

    return ET.ElementTree(root)


def parse_score_onsets(score_path):
    """Parse MusicXML into ordered note-onset groups.

    Chord tones share the same onset. Backup/forward elements are honored so
    grand-staff piano music and multiple voices can collapse to one
    measure-level timeline.
    """
    tree = _parse_musicxml(Path(score_path))
    root = tree.getroot()
    ns = namespace(root)

    parts = [child for child in root if local_name(child.tag) == "part"]
    if not parts:
        raise ValueError("No <part> elements were found in the MusicXML score.")

    # For a piano score, the first part normally contains both staves.
    part = parts[0]
    measures = [child for child in part if local_name(child.tag) == "measure"]

    onsets = []
    measure_numbers = []

    for measure_index, measure in enumerate(measures):
        measure_number = measure.attrib.get("number", str(measure_index + 1))
        measure_numbers.append(measure_number)

        cursor = 0
        previous_note_onset = 0
        onset_to_midis = defaultdict(list)

        for child in measure:
            name = local_name(child.tag)

            if name == "backup":
                cursor -= duration_ticks(child, ns)
                continue

            if name == "forward":
                cursor += duration_ticks(child, ns)
                continue

            if name != "note":
                continue

            duration = duration_ticks(child, ns)
            is_chord = child.find(tag(ns, "chord")) is not None

            if is_chord:
                onset = previous_note_onset
            else:
                onset = cursor
                previous_note_onset = onset
                cursor += duration

            if child.find(tag(ns, "rest")) is not None:
                continue

            if child.find(tag(ns, "grace")) is not None:
                continue

            tie_types = {
                tie.attrib.get("type")
                for tie in child.findall(tag(ns, "tie"))
            }
            if "stop" in tie_types and "start" not in tie_types:
                continue

            midi = note_midi(child, ns)
            if midi is not None:
                onset_to_midis[onset].append(int(midi))

        for onset_ticks in sorted(onset_to_midis):
            onsets.append(
                ScoreOnset(
                    measure_index=measure_index,
                    measure_number=measure_number,
                    onset_ticks=int(onset_ticks),
                    midis=sorted(onset_to_midis[onset_ticks]),
                )
            )

    if not onsets:
        raise ValueError(
            "The MusicXML score was parsed, but no pitched notes were found."
        )

    return onsets, measure_numbers
