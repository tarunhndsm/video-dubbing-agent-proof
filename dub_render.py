"""Render finished media and a reproducible report from measured line audio."""
import json
import textwrap
from pathlib import Path

from dub_core import Stop, run, sha256, timestamp
from dub_models import TRANSLATION, REVISION


def render(source, backing_path, foreground, lines, metadata, destination, origin,
           translation_origin='automatic model output; fluent human review pending'):
    import numpy as np
    import soundfile as sf
    backing, rate = sf.read(backing_path, dtype='float32', always_2d=True)
    delta = len(backing) - len(foreground)
    if rate != 44100 or backing.shape[1] != 2 or abs(delta) > rate * .1:
        raise Stop('BACKING_DURATION_MISMATCH')
    aligned = np.zeros_like(foreground)
    length = min(len(backing), len(foreground))
    aligned[:length] = backing[:length]
    backing = aligned
    mixed = foreground + backing * .85
    peak = float(np.max(np.abs(mixed)))
    gain = min(1.0, .98 / max(peak, 1e-9))
    sf.write(destination / 'dub-fr.wav', mixed * gain, rate, subtype='PCM_16')
    run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
         '-i', str(source), '-i', str(destination / 'dub-fr.wav'),
         '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
         '-b:a', '160k', '-t', str(metadata['duration']), '-movflags', '+faststart',
         str(destination / 'dub-fr.mp4')])
    cues = []
    for i, line in enumerate(lines, 1):
        cues.append(f'{i}\n{timestamp(line["dub_start"])} --> {timestamp(line["dub_end"])}\n' +
                    '\n'.join(textwrap.wrap(line['translation'], width=50)) + '\n')
    (destination / 'dub-fr.srt').write_text('\n'.join(cues), encoding='utf8')
    transcript = {'source_sha256': metadata['sha256'], 'source_language': 'en',
                  'target_language': 'fr', 'origin': origin,
                  'translation_origin': translation_origin, 'lines': lines}
    (destination / 'translated-script.json').write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + '\n')
    report = [
        '# English-to-French dubbing proof', '',
        'Local prototype using original synthetic footage. This is preparation, not a customer acceptance or payment receipt.', '',
        f'Source SHA-256: `{metadata["sha256"]}`. Duration: {metadata["duration"]:.3f} seconds.',
        f'Transcript origin: {origin}. Single speaker; stock voice only.',
        f'Automatic translation model: {TRANSLATION}, revision `{REVISION}` (Apache-2.0).',
        f'Applied translation provenance: {translation_origin}.',
        'Speech: Kokoro v1.0 int8 ONNX, stock voice ff_siwis (Apache-2.0 model weights).',
        'Background: Demucs 4.0.1 htdemucs separation of the original mixed audio; no supplied clean stem used.',
        f'Background gain: 0.85; shared master gain: {gain:.6f}.', '',
        'Every translated line is synthesized in full. A rate above 1.30× stops the job for review; no line is silently cut.',
        'Separation can leave speech residuals or remove background detail. Recognition, translation and punctuation can be wrong.',
        'No fluent human review, arbitrary customer-footage acceptance, speaker diarization, lip-sync or live commercial listing is claimed.', '',
        '| Line | Source window | Dub window | Rate |', '| --- | --- | --- | --- |'
    ]
    for line in lines:
        report.append(f'| {line["id"]} | {line["start"]:.3f}–{line["end"]:.3f} | '
                      f'{line["dub_start"]:.3f}–{line["dub_end"]:.3f} | {line["speed"]:.4f}× |')
    report += ['', '## Review script', '']
    for line in lines:
        report += [f'### {line["id"]}', '', 'English: ' + line['text'], '', 'French: ' + line['translation'], '']
    (destination / 'REPORT.md').write_text('\n'.join(report), encoding='utf8')
    return {'lines': len(lines), 'master_gain': gain, 'duration': metadata['duration'],
            'backing_tail_alignment_samples': delta}


def files_manifest(directory):
    return {p.name: {'bytes': p.stat().st_size, 'sha256': sha256(p)}
            for p in sorted(Path(directory).iterdir()) if p.is_file() and p.name != 'manifest.json'}
