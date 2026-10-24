import json
import tempfile
import unittest
from pathlib import Path

from backend import verify
from dub_core import Stop, apply_translations, sha256, validate_brief, validate_lines


class Invariants(unittest.TestCase):
    def test_editorial_translations_keep_line_bindings_and_protected_terms(self):
        lines = [{'id': 'line-001', 'text': 'Welcome to LumenDesk.'},
                 {'id': 'line-002', 'text': 'Review the files.'}]
        value = {'source_sha256': 'a' * 64, 'target_language': 'fr', 'review_type': 'ai_editorial',
                 'lines': [{'id': 'line-001', 'source_text': lines[0]['text'],
                            'translation': 'Bienvenue à LumenDesk.'},
                           {'id': 'line-002', 'source_text': lines[1]['text'],
                            'translation': 'Vérifiez les fichiers.'}]}
        result = apply_translations(value, lines, 'a' * 64, ['LumenDesk'])
        self.assertEqual([x['text'] for x in result], [x['text'] for x in lines])
        self.assertEqual(result[0]['translation'], 'Bienvenue à LumenDesk.')
        changes = [
            lambda v: v.update(source_sha256='b' * 64),
            lambda v: v['lines'].pop(),
            lambda v: v['lines'].reverse(),
            lambda v: v['lines'][0].update(source_text='A different claim.'),
            lambda v: v['lines'][0].update(translation='Bienvenue.'),
            lambda v: v['lines'][1].update(translation='Une ligne\nUn autre sous-titre'),
            lambda v: v.update(review_type='unverified_human_claim')
        ]
        for change in changes:
            candidate = json.loads(json.dumps(value))
            change(candidate)
            with self.subTest(change=changes.index(change)), self.assertRaises(Stop):
                apply_translations(candidate, lines, 'a' * 64, ['LumenDesk'])

    def test_brief_requires_rights_and_declared_capabilities(self):
        valid = {'rights_confirmed': True, 'target_languages': ['fr']}
        self.assertEqual(validate_brief(valid)['voice_mode'], 'stock')
        for patch in [{'rights_confirmed': 1}, {'target_languages': ['es']},
                      {'voice_mode': 'clone'}, {'glossary': ['name', 'name']}, {'extra': True}]:
            with self.subTest(patch=patch), self.assertRaises(Stop):
                validate_brief({**valid, **patch})

    def test_transcript_is_bound_to_the_actual_source(self):
        value = {'source_sha256': 'a' * 64, 'sentences': [{'start': 0, 'end': 1, 'text': 'A line.'}]}
        self.assertEqual(len(validate_lines(value, 'a' * 64, 2)), 1)
        with self.assertRaises(Stop):
            validate_lines(value, 'b' * 64, 2)

    def test_rejects_ambiguous_or_impossible_line_windows(self):
        bad = [
            [{'start': True, 'end': 1, 'text': 'A'}],
            [{'start': 0, 'end': float('nan'), 'text': 'A'}],
            [{'start': 0, 'end': 3, 'text': 'A'}],
            [{'start': 0, 'end': 1, 'text': ''}],
            [{'start': 0, 'end': 1, 'text': 'A', 'speaker': 'speaker-02'}],
            [{'start': 0, 'end': 1.5, 'text': 'A'}, {'start': 1, 'end': 2, 'text': 'B'}]
        ]
        for lines in bad:
            with self.subTest(lines=lines), self.assertRaises(Stop):
                validate_lines({'source_sha256': 'a' * 64, 'sentences': lines}, 'a' * 64, 2)

    def test_changed_and_extra_delivery_files_are_detected(self):
        names = ['dub-fr.mp4', 'dub-fr.wav', 'dub-fr.srt', 'translated-script.json', 'REPORT.md']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in names:
                (root / name).write_bytes(b'original artifact')
            manifest = {'files': {name: {'bytes': (root / name).stat().st_size,
                         'sha256': sha256(root / name)} for name in names}}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            verify(root)
            (root / 'unexpected.txt').write_text('extra')
            with self.assertRaises(Stop):
                verify(root)
            (root / 'unexpected.txt').unlink()
            (root / 'dub-fr.srt').write_text('changed')
            with self.assertRaises(Stop):
                verify(root)


if __name__ == '__main__':
    unittest.main()
