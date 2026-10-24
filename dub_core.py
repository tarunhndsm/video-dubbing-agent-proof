"""Input, timing and artifact invariants for the local dubbing proof."""
import hashlib
import json
import math
import subprocess
from pathlib import Path


class Stop(Exception):
    def __init__(self, code, hint='Review the brief and run create --help.'):
        super().__init__(code)
        self.code, self.hint = code, hint


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def run(args, timeout=300):
    try:
        return subprocess.run(args, check=True, capture_output=True,
                              timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        raise Stop('PROCESS_TIMEOUT', 'Use a shorter source or inspect the local process.') from None
    except (OSError, subprocess.CalledProcessError):
        raise Stop('MEDIA_PROCESS_FAILED', 'Check FFmpeg availability and the supported input formats.') from None


def inspect_source(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 1073741824:
        raise Stop('SOURCE_SIZE', 'Provide a local MP4 under 1 GiB.')
    try:
        metadata = json.loads(run(['ffprobe', '-v', 'error', '-show_streams',
                                   '-show_format', '-of', 'json', str(path)], 30))
        duration = float(metadata['format']['duration'])
        video = [s for s in metadata['streams'] if s['codec_type'] == 'video']
        audio = [s for s in metadata['streams'] if s['codec_type'] == 'audio']
        if not math.isfinite(duration) or not 1 <= duration <= 600:
            raise ValueError()
        if len(video) != 1 or len(audio) != 1 or video[0]['codec_name'] != 'h264':
            raise ValueError()
        if video[0].get('color_transfer') in ['smpte2084', 'arib-std-b67']:
            raise ValueError()
        return {'duration': duration, 'width': video[0]['width'],
                'height': video[0]['height'], 'sha256': sha256(path)}
    except (KeyError, TypeError, ValueError):
        raise Stop('UNSUPPORTED_SOURCE', 'Use a 1–600 second SDR H.264 MP4 with one audio track.') from None


def validate_brief(value):
    fields = {'rights_confirmed', 'target_languages', 'voice_mode', 'glossary'}
    if not isinstance(value, dict) or set(value) - fields:
        raise Stop('INVALID_BRIEF')
    if value.get('rights_confirmed') is not True:
        raise Stop('RIGHTS_REQUIRED', 'Confirm rights in the brief before processing the source.')
    if value.get('target_languages') != ['fr'] or value.get('voice_mode', 'stock') != 'stock':
        raise Stop('UNSUPPORTED_LANGUAGE_OR_VOICE', 'This proof supports English to French with stock voices.')
    glossary = value.get('glossary', [])
    if not isinstance(glossary, list) or len(glossary) > 30 or any(
        not isinstance(t, str) or not t.strip() or len(t) > 100 for t in glossary):
        raise Stop('INVALID_GLOSSARY')
    if len(set(glossary)) != len(glossary):
        raise Stop('INVALID_GLOSSARY')
    return {'rights_confirmed': True, 'target_languages': ['fr'],
            'voice_mode': 'stock', 'glossary': glossary}


def validate_lines(value, source_hash, duration):
    if not isinstance(value, dict) or value.get('source_sha256') != source_hash:
        raise Stop('TRANSCRIPT_SOURCE_MISMATCH')
    lines = value.get('sentences')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 150:
        raise Stop('INVALID_TRANSCRIPT')
    normalized, previous_end = [], 0
    for i, line in enumerate(lines):
        try:
            start, end, text = line['start'], line['end'], line['text']
            if isinstance(start, bool) or isinstance(end, bool):
                raise ValueError()
            start, end = float(start), float(end)
            if not math.isfinite(start + end) or not previous_end <= start < end <= duration:
                raise ValueError()
            if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise ValueError()
            if line.get('speaker', 'speaker-01') != 'speaker-01':
                raise Stop('MULTIPLE_SPEAKERS_UNSUPPORTED', 'This proof accepts one speaker only.')
            normalized.append({'id': f'line-{i + 1:03d}', 'start': start,
                               'end': end, 'text': text.strip(), 'speaker': 'speaker-01'})
            previous_end = end
        except (KeyError, TypeError, ValueError):
            raise Stop('INVALID_TRANSCRIPT', 'Check finite, ordered, non-overlapping line timestamps and text.') from None
    return normalized


def fitting_rate(raw_seconds, available_seconds, maximum=1.30):
    if not all(math.isfinite(x) and x > 0 for x in [raw_seconds, available_seconds]):
        raise Stop('INVALID_TIMING')
    rate = max(1.0, raw_seconds / available_seconds)
    if rate > maximum:
        raise Stop('LINE_TOO_LONG', 'Review or retime the translation; no spoken audio was truncated.')
    return rate


def apply_translations(value, lines, source_hash, glossary):
    """Apply explicit editorial text without dropping or rebinding a source line."""
    fields = {'source_sha256', 'target_language', 'review_type', 'lines'}
    if not isinstance(value, dict) or set(value) != fields:
        raise Stop('INVALID_TRANSLATIONS')
    if value['source_sha256'] != source_hash or value['target_language'] != 'fr':
        raise Stop('TRANSLATION_SOURCE_MISMATCH')
    if value['review_type'] not in ['ai_editorial', 'buyer_supplied']:
        raise Stop('INVALID_TRANSLATION_REVIEW')
    supplied = value['lines']
    if not isinstance(supplied, list) or len(supplied) != len(lines):
        raise Stop('TRANSLATION_LINE_COVERAGE')
    result = []
    for original, edited in zip(lines, supplied):
        if (not isinstance(edited, dict) or set(edited) != {'id', 'source_text', 'translation'}
                or edited['id'] != original['id'] or edited['source_text'] != original['text']):
            raise Stop('TRANSLATION_LINE_MISMATCH')
        text = edited['translation']
        if not isinstance(text, str) or not text.strip() or len(text) > 2000 or '\n' in text or '\r' in text:
            raise Stop('INVALID_TRANSLATION_TEXT')
        if any(original['text'].count(term) != text.count(term) for term in glossary):
            raise Stop('GLOSSARY_REVIEW_REQUIRED', 'Preserve every protected term in its original line.')
        result.append({**original, 'translation': text.strip()})
    return result


def timestamp(seconds):
    value = round(seconds * 1000)
    hours, value = divmod(value, 3600000)
    minutes, value = divmod(value, 60000)
    seconds, milliseconds = divmod(value, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'
