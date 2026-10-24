"""Independent checks against the fixture's original script, frames and music."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent


def command(arguments):
    return subprocess.run(arguments, check=True, capture_output=True, timeout=180).stdout


def words(text):
    return re.findall(r'\w+', text.casefold())


def frames(path):
    result = command(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path),
                      '-map', '0:v:0', '-f', 'framemd5', 'pipe:1']).decode()
    return [line.rsplit(',', 1)[-1].strip() for line in result.splitlines()
            if line and not line.startswith('#')]


def main(directory):
    source = ROOT / 'demo/source/original.mp4'
    reference = json.loads((ROOT / 'demo/source/reference.json').read_text())
    script = json.loads((directory / 'translated-script.json').read_text())
    lines, known = script['lines'], reference['sentences']
    checks = []
    assert len(lines) == len(known) == 4, 'The four actual utterances must remain distinct.'
    assert [words(x['text']) for x in lines] == [words(x['text']) for x in known]
    checks.append('all_known_source_words_present_once_in_the_four_actual_utterances')
    deviations = [abs(x['dub_start'] - y['start']) for x, y in zip(lines, known)]
    assert max(deviations) <= 1
    assert all(x['dub_end'] <= known[i + 1]['start'] for i, x in enumerate(lines[:-1]))
    assert lines[-1]['dub_end'] <= reference['duration']
    checks += ['starts_within_one_second_of_known_original', 'no_overlap_into_next_utterance']
    cues = (directory / 'dub-fr.srt').read_text().strip().split('\n\n')
    assert len(cues) == 4
    for cue, line in zip(cues, lines):
        assert words(' '.join(cue.splitlines()[2:])) == words(line['translation'])
    checks.append('every_subtitle_cue_matches_the_full_synthesis_script')
    original_frames, dubbed_frames = frames(source), frames(directory / 'dub-fr.mp4')
    assert original_frames == dubbed_frames and len(original_frames) > 1000
    checks.append('every_decoded_video_frame_is_unchanged')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(directory / 'dub-fr.mp4'), '-f', 'null', '-'])
    checks.append('entire_finished_video_and_audio_decode')
    mixed, rate = sf.read(directory / 'dub-fr.wav', dtype='float32', always_2d=True)
    music, music_rate = sf.read(ROOT / 'demo/source/music-reference.wav', dtype='float32', always_2d=True)
    assert rate == music_rate == 44100
    windows = []
    for i, (actual, original) in enumerate(zip(lines, known)):
        next_start = known[i + 1]['start'] if i + 1 < len(known) else reference['duration']
        start, end = max(actual['dub_end'], original['end']) + .3, next_start - .3
        if end - start < .3:
            continue
        a, b = round(start * rate), round(end * rate)
        expected, observed = music[a:b, 0], mixed[a:b, 0]
        correlation = float(np.corrcoef(expected, observed)[0, 1])
        ratio = float(np.sqrt(np.mean(observed ** 2)) / np.sqrt(np.mean(expected ** 2)))
        assert correlation > .8 and .25 < ratio < 1.5
        windows.append({'start': start, 'end': end, 'correlation': correlation, 'rms_ratio': ratio})
    assert len(windows) >= 3
    checks.append('original_music_is_retained_in_at_least_three_independent_quiet_windows')
    result = {'status': 'verified', 'checks': checks, 'check_count': len(checks),
              'source_words': sum(len(words(x['text'])) for x in known),
              'source_utterances': len(known), 'maximum_start_deviation_seconds': max(deviations),
              'identical_decoded_frames': len(original_frames), 'music_windows': windows,
              'limits': ['Synthetic single-speaker fixture only.',
                         'Music checks cover quiet windows, not every sound effect under arbitrary speech.',
                         'French human fluency and proper-name pronunciation review remain unverified.']}
    (ROOT / 'probe' / (directory.name + '-media-verification.json')).write_text(json.dumps(result, indent=2) + '\n')
    print('status: verified\nchecks: ' + str(len(checks)))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
