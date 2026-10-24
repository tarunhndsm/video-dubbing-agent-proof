"""Create original single-speaker footage with a known musical backing."""
import json
import textwrap
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

from dub_core import run, sha256
from dub_models import voice_model

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'demo' / 'source'
LINES = [
    ('Start with the outcome', 'Welcome to LumenDesk. This short lesson explains how to prepare a clear project brief.'),
    ('Make the scope visible', 'First, describe the result you need. Then list the files, the deadline, and the people who will review the work.'),
    ('Keep the important details', 'Keep product names unchanged. Ask one clear question when a detail is missing.'),
    ('Review before publishing', 'Review the finished files before publishing. A useful report explains what was tested and what still needs confirmation.')
]


def main():
    if DEST.exists():
        raise SystemExit('Completed fixture exists; preserving it.')
    DEST.mkdir(parents=True)
    voice = voice_model()
    rate, cursor = 24000, int(0.65 * 24000)
    chunks = [np.zeros(cursor, dtype=np.float32)]
    lines, frames = [], ['ffconcat version 1.0']
    chapter_start = 0
    for index, (title, text) in enumerate(LINES, 1):
        samples, actual_rate = voice.create(text, voice='af_heart', lang='en-us', speed=1.0)
        assert actual_rate == rate
        begin, end = cursor / rate, (cursor + len(samples)) / rate
        lines.append({'start': begin, 'end': end, 'text': text, 'speaker': 'speaker-01'})
        gap = np.zeros(round(3.5 * rate), dtype=np.float32)
        chunks.extend([samples, gap]); cursor += len(samples) + len(gap)
        frame = Image.new('RGB', (1280, 720), '#10202a')
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((50, 48, 1230, 672), radius=28, fill='#173340', outline='#345364', width=2)
        draw.text((94, 85), 'LUMENDESK  /  THE CLEAR BRIEF', fill='#80dfcc', font=ImageFont.load_default(size=25))
        draw.text((94, 156), f'{index:02}', fill='#80dfcc', font=ImageFont.load_default(size=66))
        draw.text((94, 255), title, fill='white', font=ImageFont.load_default(size=48))
        draw.multiline_text((94, 351), '\n'.join(textwrap.wrap(text, width=65)), fill='#d5e6ed',
                            font=ImageFont.load_default(size=29), spacing=14)
        draw.text((94, 605), 'Original synthetic footage · Stock voice · Original music', fill='#9bb6c2',
                  font=ImageFont.load_default(size=22))
        name = f'chapter-{index:02}.png'; frame.save(DEST / name)
        frames += [f"file '{name}'", f'duration {cursor / rate - chapter_start:.6f}']
        chapter_start = cursor / rate
    frames.append("file 'chapter-04.png'")
    sf.write(DEST / 'narration.wav', np.concatenate(chunks), rate, subtype='PCM_16')
    music_rate, duration = 44100, cursor / rate
    clock = np.arange(round(duration * music_rate)) / music_rate
    notes = np.array([261.6256, 329.6276, 391.9954, 523.2511, 391.9954, 329.6276])
    note_index = np.floor(clock / 2).astype(int) % len(notes)
    phase = 2 * np.pi * np.cumsum(notes[note_index]) / music_rate
    envelope = np.minimum((clock % 2) / .08, 1) * np.exp(-1.5 * (clock % 2))
    music = .055 * envelope * (np.sin(phase) + .3 * np.sin(2 * phase))
    stereo = np.stack([music, .94 * music], axis=1).astype(np.float32)
    sf.write(DEST / 'music-reference.wav', stereo, music_rate, subtype='PCM_16')
    (DEST / 'source.ffconcat').write_text('\n'.join(frames) + '\n')
    run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe', '1',
         '-i', str(DEST / 'source.ffconcat'), '-i', str(DEST / 'narration.wav'),
         '-i', str(DEST / 'music-reference.wav'), '-filter_complex',
         '[1:a]volume=0.85[v];[v][2:a]amix=inputs=2:duration=longest:normalize=0[a]',
         '-map', '0:v:0', '-map', '[a]', '-t', str(duration), '-r', '30', '-c:v', 'libx264',
         '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
         '-b:a', '160k', '-movflags', '+faststart', str(DEST / 'original.mp4')])
    reference = {'source_sha256': sha256(DEST / 'original.mp4'), 'synthetic': True,
                 'duration': duration, 'sentences': lines}
    (DEST / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n')
    print(json.dumps({'status': 'fixture_created', 'duration': round(duration, 3), 'lines': len(lines)}))


if __name__ == '__main__':
    main()
