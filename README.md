# English-to-French video dubbing proof

A local prototype that transcribes English speech, translates it to French, generates a declared stock voice, separates the original mixed audio and returns a dubbed MP4, WAV, SRT, line-by-line script and report. Original synthetic footage is supplied so the measured claims are reproducible.

This is AI-assisted preparation for a prospective project. It is not a live commercial listing, a customer delivery, a fluent-human language certification or evidence of earnings.

- [Original English video](demo/source/original.mp4)
- [French video with AI editorial corrections](demo/editorial-v4/dub-fr.mp4)
- [French subtitles](demo/editorial-v4/dub-fr.srt)
- [Full report and bilingual script](demo/editorial-v4/REPORT.md)
- [Automatic translation baseline](demo/automatic-v3/REPORT.md)
- [Measured media checks](probe/editorial-v4-media-verification.json)
- [Independent French speech recognition](probe/editorial-v4-speech-measurement.json)

The 38.181-second fixture contains four utterances and 65 known English words. Both the automatic baseline and editorial version preserve all four actual utterances, begin within 0.31 seconds of the known starts and finish before the next utterance. All 1,108 decoded video frames are unchanged. Four independent quiet windows retain the original music with correlation above 0.9999 and about 82% of its reference RMS level. These quiet-window measurements do not establish preservation of arbitrary sound effects under speech.

The French editorial text corrects awkward automatic wording and is explicitly labelled `ai_editorial`. It has not been approved by a fluent human. Independent multilingual ASR recovers all four sentences; word agreement ranges from 75% to 100%, including French homophone spelling differences and a differently spelled brand name. This is audibility evidence, not semantic or pronunciation certification. The complete measurement is linked above.

## Setup and commands

Measured on macOS with Python 3.12, Node 24 and FFmpeg. Other systems are unverified. Install FFmpeg and an eSpeak-compatible phonemizer, then:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
node agent.mjs models --json
node agent.mjs inspect --source demo/source/original.mp4 --json
```

`models` explicitly downloads the free public Kokoro stock-voice weights and the pinned English-to-French translation model. The first automatic transcription and separation also download free Whisper and Demucs weights. No paid generation API or account key is used. Model weights, caches and environments are excluded from the repository and archive.

Create a new automatic delivery:

```sh
node agent.mjs create --source demo/source/original.mp4 --brief demo-brief.json --output demo/new-automatic --json
```

Apply the supplied source-bound AI editorial text:

```sh
node agent.mjs create --source demo/source/original.mp4 --brief demo-brief.json --translations demo/editorial-translations.json --output demo/new-editorial --json
node agent.mjs verify --output demo/new-editorial --json
```

Use a new output directory for a changed request or changed processing code. Repeating the exact request against a verified delivery returns `verified_noop`; it does not rerun inference or overwrite files. Changed or unexpected delivery files stop verification. A source-bound supplied English transcript is optional through `--transcript`; otherwise transcription is automatic.

Without `--json`, the wrapper uses TOON. No arguments show the local proof state. Every command supports `--help`, and unknown, duplicate or missing flags fail before environment access. `DUBBING_PYTHON` can explicitly select an existing development environment.

## Scope and timing

- English to French; one speaker; Kokoro `ff_siwis` stock voice only. The source fixture uses a different declared stock voice, `af_heart`.
- A local SDR H.264 MP4 with one audio track, 1–600 seconds and at most 1 GiB is accepted by the input validator. Only the supplied short fixture has end-to-end evidence; these limits are not a claim that unseen ten-minute videos pass review.
- No URL downloader, speaker diarization, cloned voice or lip-sync is implemented. Multiple speakers require separate future work. The caller must check that the source meets the single-speaker English scope.
- A rights confirmation and target language are required before processing. See [the example brief](demo-brief.json).
- Each complete synthesized line starts at its recognized source time. It can use the silence before the following utterance. Longer speech is time-stretched by at most 1.30×; a line that cannot fit stops with `LINE_TOO_LONG`. The audio is never silently truncated to fit.
- Protected terms must retain their exact occurrence count in each translated line. Their synthesis uses English phonemes within the French voice. A fluent listener must still verify pronunciation.
- Editorial input binds every line ID and exact English text to the original source SHA-256. Missing, reordered, replaced or extra lines and changed glossary terms are rejected.

Source separation can retain original-speech residue or remove background detail. Transcription and translation can make errors. The buyer's fluent reviewer must confirm meaning and names before publication. Processing temporary files are deleted after completion; final local delivery files remain in the chosen output directory. The caller controls deletion and any backups. Nothing uploads footage automatically.

## Verification

```sh
.venv/bin/python -m unittest test_core test_audio
node --test agent.test.mjs
.venv/bin/python verify_media.py demo/editorial-v4
```

Seven Python tests cover source/translation binding, rights and capability limits, changed/extra delivery files, real FFmpeg rate fitting with an audible end marker, and a too-long line that stops before audio is written. Six Node tests cover flag validation and environment-independent help. Seven independent fixture media checks cover source words, timing, subtitles, every video frame, complete decoding and background music.

The optional speech measurement requires a separately cached multilingual Whisper `small` model. It reads the final mixed WAV, not an isolated synthesis stem. It does not force the expected transcript into recognition.

## Components and rights

New code and original fixture graphics, script and synthesized music: MIT; see [LICENSE](LICENSE). Third-party software and models retain their own terms; see [THIRD-PARTY.md](THIRD-PARTY.md). No third-party model weights are redistributed. No private footage, credentials, client data or external account state is included.
