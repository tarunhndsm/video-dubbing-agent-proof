"""Explicit free-model setup and offline synthesis/translation."""
import json
import os
import urllib.request
from pathlib import Path

from dub_core import Stop, sha256

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / '.models'
TRANSLATION = 'Helsinki-NLP/opus-mt-en-fr'
REVISION = 'dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18'
KOKORO = {
    'kokoro-v1.0.int8.onnx': '6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb',
    'voices-v1.0.bin': 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'
}
RELEASE = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('DO_NOT_TRACK', '1')


def prepare():
    from huggingface_hub import snapshot_download
    MODELS.mkdir(exist_ok=True)
    for name, expected in KOKORO.items():
        path = MODELS / name
        if path.exists():
            if sha256(path) != expected:
                raise Stop('MODEL_HASH_MISMATCH', 'Inspect the existing model; setup will not overwrite it.')
            continue
        temporary = MODELS / (name + '.download')
        if temporary.exists():
            raise Stop('MODEL_DOWNLOAD_INCOMPLETE', 'Inspect the incomplete model download before repeating setup.')
        try:
            with urllib.request.urlopen(RELEASE + name, timeout=60) as response, temporary.open('xb') as output:
                size = 0
                while block := response.read(1048576):
                    size += len(block)
                    if size > 268435456:
                        raise Stop('MODEL_DOWNLOAD_SIZE')
                    output.write(block)
            if sha256(temporary) != expected:
                raise Stop('MODEL_HASH_MISMATCH')
            temporary.rename(path)
        except Stop:
            raise
        except Exception:
            raise Stop('MODEL_DOWNLOAD_FAILED', 'Check connectivity; inspect the partial download before retrying.') from None
    snapshot_download(TRANSLATION, revision=REVISION, local_dir=MODELS / 'translation-en-fr',
                      allow_patterns=['config.json', 'generation_config.json',
                                      'pytorch_model.bin', '*.spm', '*.json', 'README.md'])
    return {'status': 'models_prepared', 'translationRevision': REVISION,
            'hint': 'The first transcription and separation also download free public model weights.'}


def voice_model():
    from kokoro_onnx import Kokoro
    for name, expected in KOKORO.items():
        if not (MODELS / name).is_file() or sha256(MODELS / name) != expected:
            raise Stop('VOICE_MODEL_REQUIRED', 'Run agent.mjs models before creating a delivery.')
    return Kokoro(str(MODELS / 'kokoro-v1.0.int8.onnx'), str(MODELS / 'voices-v1.0.bin'))


def translate(lines, glossary):
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    path = MODELS / 'translation-en-fr'
    if not (path / 'pytorch_model.bin').is_file():
        raise Stop('TRANSLATION_MODEL_REQUIRED', 'Run agent.mjs models before creating a delivery.')
    tokenizer = MarianTokenizer.from_pretrained(path, local_files_only=True)
    model = MarianMTModel.from_pretrained(path, local_files_only=True).eval()
    torch.set_num_threads(4)
    result = []
    for line in lines:
        encoded = tokenizer(line['text'], return_tensors='pt')
        if encoded['input_ids'].shape[1] > 384:
            raise Stop('TRANSLATION_LINE_TOO_LONG', 'Split the source transcript at complete sentence boundaries.')
        with torch.inference_mode():
            ids = model.generate(**encoded, max_new_tokens=384, num_beams=4)
        if ids[0, -1].item() != tokenizer.eos_token_id:
            raise Stop('TRANSLATION_INCOMPLETE')
        text = tokenizer.decode(ids[0], skip_special_tokens=True).strip()
        if not text:
            raise Stop('EMPTY_TRANSLATION')
        for term in glossary:
            if line['text'].count(term) != text.count(term):
                raise Stop('GLOSSARY_REVIEW_REQUIRED', 'Review the translation; a protected term changed or disappeared.')
        result.append({**line, 'translation': text})
    return result
