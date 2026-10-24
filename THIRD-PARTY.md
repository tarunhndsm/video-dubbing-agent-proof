# Third-party components

No model weights, executable dependencies or third-party media are redistributed here. Install dependencies and download models from their original publishers.

| Component | Purpose | Upstream terms/source |
| --- | --- | --- |
| Helsinki-NLP/opus-mt-en-fr | Automatic translation candidate | [Model card, Apache-2.0](https://huggingface.co/Helsinki-NLP/opus-mt-en-fr); revision `dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18` |
| Kokoro-82M v1.0 | Declared stock voices `af_heart` and `ff_siwis` | [Model card, Apache-2.0 weights](https://huggingface.co/hexgrad/Kokoro-82M) |
| kokoro-onnx 0.6.1 | Local voice inference | [Upstream repository](https://github.com/thewh1teagle/kokoro-onnx); downloads use its `model-files-v1.0` release and pinned SHA-256 values |
| faster-whisper 1.2.1 / Whisper small.en and small | English transcription and separate French recognition measurement | [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Whisper MIT license](https://github.com/openai/whisper/blob/main/LICENSE) |
| Demucs 4.0.1 / htdemucs | Separation of the original mixed audio | [Demucs repository](https://github.com/facebookresearch/demucs), [MIT source license](DEMUCS-LICENSE.txt); upstream model terms apply |
| FFmpeg and libx264 | Media decoding, time stretch, mixing and video muxing | [FFmpeg legal information](https://ffmpeg.org/legal.html); the installed binary has its own build-dependent terms and is not redistributed |
| @toon-format/toon 4.4.0 | CLI output serialization | [MIT upstream project](https://github.com/toon-format/toon) |

The stock voices are synthetic development voices; this project does not clone the source speaker. Model training and voice provenance are described by their publishers. No claim is made that a synthesized pronunciation has been certified by a fluent human.

The English script, fixture artwork and simple synthesized music were created for this demonstration. The fictional name LumenDesk is a glossary test. It does not imply a customer, commercial affiliation or prior paid work.
