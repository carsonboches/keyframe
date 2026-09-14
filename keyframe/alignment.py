from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .config import (
    ALIGN_GAP_COST,
    ALIGN_NO_COMMON_PITCH_COST,
    AUDIO_GROUP_TOLERANCE_MS,
    FINAL_MEASURE_TAIL_MS,
    MEASURE_POSTROLL_MS,
    MEASURE_PREROLL_MS,
    MIN_GROUP_MATCH_SCORE,
)


@dataclass
class AudioOnset:
    onset_ms: int
    midis: list[int]
    event_indices: list[int]


def group_audio_events(events):
    indexed = list(enumerate(events))
    indexed.sort(key=lambda item: int(item[1]["onset_ms"]))

    groups = []
    current = []

    for item in indexed:
        if not current:
            current = [item]
            continue

        first_onset = int(current[0][1]["onset_ms"])
        onset = int(item[1]["onset_ms"])

        if onset - first_onset <= AUDIO_GROUP_TOLERANCE_MS:
            current.append(item)
        else:
            groups.append(current)
            current = [item]

    if current:
        groups.append(current)

    result = []
    for group in groups:
        onset_ms = int(round(sum(int(event["onset_ms"]) for _, event in group) / len(group)))
        result.append(
            AudioOnset(
                onset_ms=onset_ms,
                midis=sorted(int(event["midi"]) for _, event in group),
                event_indices=[index for index, _ in group],
            )
        )

    return result


def _counter(midis):
    return Counter(int(midi) for midi in midis)


def group_match_score(audio_group: AudioOnset, score_group):
    """0..1 similarity between a performed onset and a score onset.

    Exact MIDI pitch matters. Octave-equivalent notes do not count as matches.
    Extra Basic-Pitch notes are tolerated because transcription noise often
    creates short harmonics or duplicate events.
    """
    audio_counter = _counter(audio_group.midis)
    score_counter = _counter(score_group.midis)

    common = audio_counter & score_counter
    matched = sum(common.values())

    if matched == 0:
        return 0.0

    score_total = max(1, sum(score_counter.values()))
    audio_total = max(1, sum(audio_counter.values()))

    recall = matched / score_total
    precision = matched / audio_total

    # Score recall matters more: if a three-note score chord is present, we want
    # evidence for all three pitches, while still tolerating a few audio extras.
    return 0.72 * recall + 0.28 * precision


def substitution_cost(audio_group, score_group):
    score = group_match_score(audio_group, score_group)
    if score <= 0.0:
        return ALIGN_NO_COMMON_PITCH_COST

    # A perfect match costs zero. A partial chord match remains possible but
    # more expensive than a complete onset.
    return 1.15 * (1.0 - score)


def align_onsets(audio_groups, score_groups):
    n = len(audio_groups)
    m = len(score_groups)

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = i * ALIGN_GAP_COST
        back[i][0] = "up"

    for j in range(1, m + 1):
        dp[0][j] = j * ALIGN_GAP_COST
        back[0][j] = "left"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = (
                dp[i - 1][j - 1]
                + substitution_cost(audio_groups[i - 1], score_groups[j - 1])
            )
            up = dp[i - 1][j] + ALIGN_GAP_COST
            left = dp[i][j - 1] + ALIGN_GAP_COST

            best = min(diag, up, left)
            dp[i][j] = best

            if best == diag:
                back[i][j] = "diag"
            elif best == up:
                back[i][j] = "up"
            else:
                back[i][j] = "left"

    matches = []
    i, j = n, m

    while i > 0 or j > 0:
        move = back[i][j]

        if move == "diag":
            audio_group = audio_groups[i - 1]
            score_group = score_groups[j - 1]
            score = group_match_score(audio_group, score_group)

            if score >= MIN_GROUP_MATCH_SCORE:
                matches.append({
                    "audio_index": i - 1,
                    "score_index": j - 1,
                    "audio_onset_ms": audio_group.onset_ms,
                    "measure_index": score_group.measure_index,
                    "measure_number": score_group.measure_number,
                    "score_midis": score_group.midis,
                    "audio_midis": audio_group.midis,
                    "audio_event_indices": audio_group.event_indices,
                    "match_score": round(score, 4),
                })

            i -= 1
            j -= 1

        elif move == "up":
            i -= 1
        elif move == "left":
            j -= 1
        else:
            break

    matches.reverse()
    return matches, float(dp[n][m])


def _interpolate_missing(starts, measure_count):
    known = sorted((idx, value) for idx, value in starts.items())

    if not known:
        return starts

    # Fill internal gaps linearly between known neighboring measures.
    for left_pos in range(len(known) - 1):
        left_idx, left_time = known[left_pos]
        right_idx, right_time = known[left_pos + 1]
        gap = right_idx - left_idx

        if gap <= 1:
            continue

        step = (right_time - left_time) / gap
        for offset in range(1, gap):
            starts[left_idx + offset] = int(round(left_time + step * offset))

    # Extrapolate before first/after last with median known measure spacing.
    spacings = []
    known_after = sorted((idx, starts[idx]) for idx in starts)
    for (i1, t1), (i2, t2) in zip(known_after, known_after[1:]):
        if i2 > i1:
            spacings.append((t2 - t1) / (i2 - i1))

    typical = int(round(sorted(spacings)[len(spacings)//2])) if spacings else 2000
    typical = max(300, typical)

    first_idx = min(starts)
    for idx in range(first_idx - 1, -1, -1):
        starts[idx] = max(0, starts[idx + 1] - typical)

    last_idx = max(starts)
    for idx in range(last_idx + 1, measure_count):
        starts[idx] = starts[idx - 1] + typical

    return starts


def build_measure_timing(matches, measure_numbers, audio_events):
    measure_count = len(measure_numbers)

    # Use the earliest trusted aligned onset in each measure as its anchor.
    starts = {}
    confidences = {}

    grouped = {}
    for match in matches:
        grouped.setdefault(match["measure_index"], []).append(match)

    for measure_index, items in grouped.items():
        items = sorted(items, key=lambda item: item["audio_onset_ms"])
        starts[measure_index] = int(items[0]["audio_onset_ms"])
        confidences[measure_index] = round(
            sum(item["match_score"] for item in items) / len(items),
            4,
        )

    starts = _interpolate_missing(starts, measure_count)

    if not starts:
        raise RuntimeError(
            "No score/audio alignment was strong enough to locate any measures."
        )

    measures = []

    for index, number in enumerate(measure_numbers):
        start_ms = max(0, int(starts[index]) - MEASURE_PREROLL_MS)

        if index + 1 < measure_count:
            # Stop before the first onset of the next measure.  The old code
            # added post-roll here, so every measure audibly spilled into the
            # following measure.
            end_ms = max(start_ms + 250, int(starts[index + 1]) - 1)
        else:
            # Do not use the end of *all* transcribed audio for the final
            # measure; Basic Pitch can emit stray notes after the piece ends.
            # Prefer offsets from audio events that actually participated in
            # trusted matches for the final score measure.
            trusted_offsets = []
            for item in grouped.get(index, []):
                for event_index in item.get("audio_event_indices", []):
                    if 0 <= event_index < len(audio_events):
                        event = audio_events[event_index]
                        trusted_offsets.append(
                            int(event.get("offset_ms", event.get("onset_ms", 0)))
                        )

            if trusted_offsets:
                final_end = max(trusted_offsets) + MEASURE_POSTROLL_MS
            else:
                final_end = int(starts[index]) + FINAL_MEASURE_TAIL_MS

            end_ms = max(start_ms + 250, final_end)

        measures.append({
            "index": index,
            "number": str(number),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "confidence": confidences.get(index),
            "inferred": index not in confidences,
        })

    return measures
