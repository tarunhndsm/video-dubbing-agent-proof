"""JSON boundary for the agent-facing wrapper; local files only."""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from dub_core import Stop, apply_translations, inspect_source, sha256, validate_brief, validate_lines

ROOT = Path(__file__).resolve().parent


def verify(output):
    value = json.loads((output / 'manifest.json').read_text())
    expected_names = {'dub-fr.mp4', 'dub-fr.wav', 'dub-fr.srt', 'translated-script.json', 'REPORT.md'}
    if set(value.get('files', {})) != expected_names or set(p.name for p in output.iterdir()) != expected_names | {'manifest.json'}:
        raise Stop('INVALID_MANIFEST', 'The delivery must contain exactly its five declared artifacts and manifest.')
    for name, expected in value['files'].items():
        if Path(name).name != name or name == 'manifest.json':
            raise Stop('INVALID_MANIFEST')
        path = output / name
        if not path.is_file() or path.stat().st_size != expected['bytes'] or sha256(path) != expected['sha256']:
            raise Stop('OUTPUT_CHANGED', 'Preserve the delivery and inspect the changed file before proceeding.')
    return value


def create(source, brief_path, transcript_path, output, translations_path=None):
    from dub_audio import separate, synthesize, transcribe
    from dub_models import translate, voice_model
    from dub_render import files_manifest, render
    source = source.resolve(); output = output.resolve()
    metadata = inspect_source(source)
    brief = validate_brief(json.loads(brief_path.read_text()))
    supplied = json.loads(transcript_path.read_text()) if transcript_path else None
    editorial = json.loads(translations_path.read_text()) if translations_path else None
    if supplied is not None:
        validate_lines(supplied, metadata['sha256'], metadata['duration'])
    code = {name: sha256(ROOT / name) for name in
            ['backend.py', 'dub_core.py', 'dub_audio.py', 'dub_models.py', 'dub_render.py']}
    request = {'source': metadata['sha256'], 'brief': brief, 'transcript': supplied,
               'translations': editorial, 'code': code}
    request_hash = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if output.exists():
        manifest = verify(output)
        if manifest['request_sha256'] != request_hash:
            raise Stop('OUTPUT_DIFFERENT_REQUEST', 'Choose a new output directory; the existing delivery is preserved.')
        return {'status': 'verified_noop', 'output': str(output), 'lines': manifest['summary']['lines']}
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / ('.' + output.name + '.lock')
    try:
        with lock.open('x') as handle:
            handle.write('local dubbing preparation\n')
    except FileExistsError:
        raise Stop('OUTPUT_LOCKED', 'Inspect the existing preparation before starting another.') from None
    temporary = Path(tempfile.mkdtemp(prefix='.dubbing-', dir=output.parent))
    try:
        work, delivery = temporary / 'work', temporary / 'delivery'
        work.mkdir(); delivery.mkdir()
        if supplied is None:
            print('Transcribing the local English source.', file=sys.stderr)
            supplied, lines = transcribe(source, metadata, work)
            origin = 'automatic faster-whisper small.en; review required'
        else:
            lines = validate_lines(supplied, metadata['sha256'], metadata['duration'])
            origin = 'source-hash-bound supplied transcript'
        if editorial is None:
            translated = translate(lines, brief['glossary'])
            translation_origin = 'automatic model output; fluent human review pending'
        else:
            translated = apply_translations(editorial, lines, metadata['sha256'], brief['glossary'])
            translation_origin = editorial['review_type'] + '; fluent human review not independently verified'
        print('Separating the original mixed audio locally.', file=sys.stderr)
        backing = separate(source, work)
        foreground, timed = synthesize(translated, metadata['duration'], work, voice_model(), brief['glossary'])
        summary = render(source, backing, foreground, timed, metadata, delivery, origin, translation_origin)
        manifest = {'version': 1, 'request_sha256': request_hash, 'source': metadata,
                    'brief': brief, 'code_sha256': code, 'summary': summary,
                    'files': files_manifest(delivery), 'earningsVerified': False}
        (delivery / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        verify(delivery)
        delivery.rename(output)
        return {'status': 'created', 'output': str(output), 'lines': len(timed), 'language': 'fr'}
    finally:
        shutil.rmtree(temporary)
        lock.unlink()


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('USAGE', 'Run agent.mjs create --help for supported flags.')


def main():
    parser = Parser(add_help=False)
    parser.add_argument('command', choices=['home', 'models', 'create', 'verify', 'inspect'])
    parser.add_argument('--source', type=Path)
    parser.add_argument('--brief', type=Path)
    parser.add_argument('--transcript', type=Path)
    parser.add_argument('--translations', type=Path)
    parser.add_argument('--output', type=Path)
    try:
        args = parser.parse_args()
        if args.command == 'home':
            result = {'bin': str(ROOT / 'agent.mjs').replace(str(Path.home()), '~', 1),
                      'description': 'Create local English-to-French video dubs with a stock voice.',
                      'status': 'local_proof', 'demo_deliveries': len(list((ROOT / 'demo').glob('*/manifest.json'))),
                      'hint': 'Run agent.mjs create --help or agent.mjs verify --output <directory>.'}
        elif args.command == 'models':
            from dub_models import prepare
            result = prepare()
        elif args.command == 'inspect' and args.source:
            result = {'status': 'source_read', **inspect_source(args.source)}
        elif args.command == 'verify' and args.output:
            manifest = verify(args.output)
            result = {'status': 'files_verified', 'files': len(manifest['files']),
                      'lines': manifest['summary']['lines'], 'output': str(args.output)}
        elif args.command == 'create' and args.source and args.brief and args.output:
            result = create(args.source, args.brief, args.transcript, args.output, args.translations)
        else:
            raise Stop('USAGE', 'Run agent.mjs --help for required arguments.')
        print(json.dumps(result))
    except Stop as error:
        print(json.dumps({'status': 'stopped', 'code': error.code, 'hint': error.hint}))
        return 2 if error.code == 'USAGE' else 1
    except Exception:
        print(json.dumps({'status': 'stopped', 'code': 'LOCAL_PROCESS_FAILED',
                          'hint': 'Inspect local inputs and installed dependencies; the source is preserved.'}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
