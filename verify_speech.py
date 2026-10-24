"""Independent multilingual recognition of actual mixed French delivery audio.

Recognition agreement is evidence of audibility, not fluent human review.
"""
import difflib
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


def words(text):
    plain = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                    if not unicodedata.combining(c))
    return re.findall(r'\w+', plain)


def main(directory):
    started = time.monotonic()
    script = json.loads((directory / 'translated-script.json').read_text())
    # Resample the final mixed track once, rather than reading any synthesis stem.
    pcm = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(directory / 'dub-fr.wav'),
                          '-ar', '16000', '-ac', '1', '-f', 'f32le', 'pipe:1'],
                         check=True, capture_output=True, timeout=60).stdout
    mono = np.frombuffer(pcm, dtype='<f4').copy()
    model = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4,
                         local_files_only=True)
    lines = []
    for line in script['lines']:
        start, end = round(line['dub_start'] * 16000), round(line['dub_end'] * 16000)
        segments, info = model.transcribe(mono[start:end], language='fr', beam_size=5,
                                         vad_filter=True, condition_on_previous_text=False)
        recognized = ' '.join(s.text.strip() for s in segments)
        expected_words, observed_words = words(line['translation']), words(recognized)
        matches = sum(x.size for x in difflib.SequenceMatcher(
            None, expected_words, observed_words, autojunk=False).get_matching_blocks())
        lines.append({'id': line['id'], 'expected': line['translation'],
                      'recognized': recognized, 'reference_words': len(expected_words),
                      'matched_words': matches, 'word_recall': matches / len(expected_words),
                      'final_word_matches': bool(observed_words) and expected_words[-1] == observed_words[-1]})
    result = {'status': 'measured', 'model': 'faster-whisper small multilingual int8',
              'source': 'final mixed dub-fr.wav, individually cropped to measured dub windows',
              'seconds': round(time.monotonic() - started, 3), 'lines': lines,
              'limits': ['ASR agreement is not fluent human review or a guarantee of semantic equivalence.',
                         'Protected-name pronunciation needs a fluent listener; ASR spelling can differ.']}
    target = Path(__file__).resolve().parent / 'probe' / (directory.name + '-speech-measurement.json')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'measured', 'lines': len(lines),
                      'minimum_word_recall': min(x['word_recall'] for x in lines),
                      'final_words_matching': sum(x['final_word_matches'] for x in lines)}))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
