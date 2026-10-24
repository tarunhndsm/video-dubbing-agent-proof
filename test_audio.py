import tempfile
import unittest
from pathlib import Path

import numpy as np

from dub_audio import synthesize
from dub_core import Stop


class ToneVoice:
    def create(self, text, **kwargs):
        rate = 24000
        time = np.arange(2 * rate) / rate
        phase = 2 * np.pi * np.cumsum(np.where(time < 1.7, 440., 880.)) / rate
        return (.15 * np.sin(phase)).astype(np.float32), rate


class RealAudioTiming(unittest.TestCase):
    def test_rate_fitting_preserves_the_end_marker_and_next_speaker_window(self):
        lines = [
            {'id': 'line-001', 'start': .1, 'translation': 'Première ligne.'},
            {'id': 'line-002', 'start': 1.9, 'translation': 'Deuxième ligne.'}
        ]
        with tempfile.TemporaryDirectory() as temporary:
            audio, measured = synthesize(lines, 4.5, Path(temporary), ToneVoice())
            self.assertEqual(audio.shape, (198450, 2))
            first = measured[0]
            self.assertGreater(first['speed'], 1)
            self.assertLessEqual(first['speed'], 1.3)
            self.assertLess(first['dub_end'], measured[1]['dub_start'])
            end = round(first['dub_end'] * 44100)
            tail = audio[end - 4410:end, 0]
            self.assertGreater(np.sqrt(np.mean(tail ** 2)), .04)
            spectrum = np.abs(np.fft.rfft(tail * np.hanning(len(tail))))
            frequency = np.fft.rfftfreq(len(tail), 1 / 44100)[np.argmax(spectrum)]
            self.assertGreater(frequency, 800)
            self.assertLess(frequency, 950)

    def test_unfittable_line_fails_before_writing_or_truncating_audio(self):
        lines = [{'id': 'line-001', 'start': 0, 'translation': 'Trop longue.'}]
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(Stop) as error:
                synthesize(lines, 1, Path(temporary), ToneVoice())
            self.assertEqual(error.exception.code, 'LINE_TOO_LONG')
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
