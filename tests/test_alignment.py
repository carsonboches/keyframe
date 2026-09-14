import unittest

from keyframe.alignment import AudioOnset, align_onsets, build_measure_timing
from keyframe.musicxml import ScoreOnset


class AlignmentTests(unittest.TestCase):
    def test_exact_octave_required(self):
        audio = [
            AudioOnset(1000, [60], [0]),
            AudioOnset(2000, [62], [1]),
        ]
        score = [
            ScoreOnset(0, "1", 0, [48]),
            ScoreOnset(1, "2", 0, [62]),
        ]

        matches, _ = align_onsets(audio, score)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["measure_number"], "2")

    def test_chord_similarity(self):
        audio = [AudioOnset(1000, [60, 64, 67], [0, 1, 2])]
        score = [ScoreOnset(0, "1", 0, [60, 64, 67])]

        matches, _ = align_onsets(audio, score)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["match_score"], 1.0)

    def test_measure_timing(self):
        matches = [
            {
                "measure_index": 0,
                "measure_number": "1",
                "audio_onset_ms": 1000,
                "match_score": 1.0,
            },
            {
                "measure_index": 1,
                "measure_number": "2",
                "audio_onset_ms": 3000,
                "match_score": 1.0,
            },
        ]

        measures = build_measure_timing(
            matches,
            ["1", "2"],
            [{"onset_ms": 1000, "offset_ms": 4500}],
        )

        self.assertLess(measures[0]["start_ms"], measures[0]["end_ms"])
        self.assertLess(measures[0]["end_ms"], measures[1]["end_ms"])


if __name__ == "__main__":
    unittest.main()
