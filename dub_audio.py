"""Real source separation and bounded line synthesis."""
from pathlib import Path

from dub_core import Stop, fitting_rate, run, validate_lines


def transcribe(source, metadata, work):
    import numpy as np
    from faster_whisper import WhisperModel
    model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=4)
    pcm = run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(source),
               '-vn', '-ar', '16000', '-ac', '1', '-f', 'f32le', 'pipe:1'])
    audio = np.frombuffer(pcm, dtype='<f4').copy()
    segments, _ = model.transcribe(audio, language='en', beam_size=5, vad_filter=True,
                                   word_timestamps=True)
    raw = []
    for segment in segments:
        if not segment.text.strip():
            continue
        words = [word for word in segment.words or [] if word.word.strip()]
        if not words:
            raise Stop('WORD_ALIGNMENT_REQUIRED', 'Supply a reviewed, source-bound transcript.')
        raw.append({'start': words[0].start, 'end': words[-1].end,
                    'text': segment.text.strip()})
    merged = []
    for line in raw:
        if merged and line['start'] - merged[-1]['end'] <= .75 and (
                len((merged[-1]['text'] + ' ' + line['text']).split()) <= 65 and
                line['end'] - merged[-1]['start'] <= 28):
            merged[-1] = {**merged[-1], 'end': line['end'],
                          'text': merged[-1]['text'] + ' ' + line['text']}
        else:
            merged.append(dict(line))
    value = {'source_sha256': metadata['sha256'], 'raw_segments': raw, 'sentences': merged}
    return value, validate_lines(value, metadata['sha256'], metadata['duration'])


def separate(source, work):
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    path = Path(work) / 'mixed-source.wav'
    run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
         '-i', str(source), '-vn', '-ar', '44100', '-ac', '2', '-c:a', 'pcm_f32le', str(path)])
    audio, rate = sf.read(path, dtype='float32', always_2d=True)
    tensor = torch.from_numpy(audio.T.copy())
    reference = tensor.mean(0)
    scale, mean = reference.std(), reference.mean()
    if not np.isfinite(audio).all() or scale.item() < 1e-8:
        raise Stop('SILENT_OR_INVALID_AUDIO')
    torch.set_num_threads(4)
    model = get_model('htdemucs').eval()
    with torch.inference_mode():
        separated = apply_model(model, ((tensor - mean) / scale)[None], device='cpu',
                                shifts=0, split=True, overlap=.25, segment=7.5,
                                progress=True, num_workers=0)[0]
    separated = separated * scale + mean
    indices = [i for i, name in enumerate(model.sources) if name != 'vocals']
    backing = separated[indices].sum(0).cpu().numpy().T
    if backing.shape != audio.shape or not np.isfinite(backing).all():
        raise Stop('INVALID_SEPARATION')
    target = Path(work) / 'separated-backing.wav'
    sf.write(target, backing, rate, subtype='FLOAT')
    return target


def synthesize(lines, duration, work, voice, glossary=()):
    import numpy as np
    import soundfile as sf
    sample_rate = 44100
    foreground = np.zeros((round(duration * sample_rate), 2), dtype=np.float32)
    result = []
    for i, line in enumerate(lines):
        boundary = lines[i + 1]['start'] if i + 1 < len(lines) else duration
        available = boundary - line['start'] - .12
        text, pronunciation = glossary_phonemes(line['translation'], glossary)
        samples, rate = voice.create(text, voice='ff_siwis', lang='fr-fr', speed=1.0,
                                     is_phonemes=bool(pronunciation))
        speed = fitting_rate(len(samples) / rate, available)
        raw, fitted = Path(work) / f'{line["id"]}-raw.wav', Path(work) / f'{line["id"]}-fitted.wav'
        sf.write(raw, samples, rate, subtype='FLOAT')
        run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-n', '-i', str(raw),
             '-af', f'atempo={speed:.9f}', '-ar', str(sample_rate), '-ac', '2', str(fitted)])
        audio, actual_rate = sf.read(fitted, dtype='float32', always_2d=True)
        begin = round(line['start'] * sample_rate); end = begin + len(audio)
        if actual_rate != sample_rate or end > round((boundary - .03) * sample_rate):
            raise Stop('DUB_OVERLAP', 'Review the translation timing; no line was truncated.')
        if not len(audio) or not np.isfinite(audio).all():
            raise Stop('INVALID_SYNTHESIS')
        foreground[begin:end] += audio
        result.append({**line, 'dub_start': begin / sample_rate, 'dub_end': end / sample_rate,
                       'speed': speed, 'stock_voice': 'ff_siwis', 'raw_seconds': len(samples) / rate,
                       'glossary_pronunciation': pronunciation})
    return foreground, result


def glossary_phonemes(text, glossary):
    import re
    if not glossary or not any(term in text for term in glossary):
        return text, []
    from kokoro_onnx.tokenizer import Tokenizer
    tokenizer = Tokenizer()
    pattern = '|'.join(re.escape(t) for t in sorted(glossary, key=len, reverse=True))
    chunks, terms, cursor = [], [], 0
    for match in re.finditer(pattern, text):
        chunks.append(tokenizer.phonemize(text[cursor:match.start()], lang='fr-fr'))
        phonemes = tokenizer.phonemize(match.group(), lang='en-us')
        if not phonemes:
            raise Stop('GLOSSARY_PRONUNCIATION_REQUIRED')
        chunks.append(phonemes)
        terms.append({'term': match.group(), 'language': 'en-us', 'phonemes': phonemes})
        cursor = match.end()
    chunks.append(tokenizer.phonemize(text[cursor:], lang='fr-fr'))
    return ' '.join(chunks), terms
