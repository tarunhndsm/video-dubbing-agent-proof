# English-to-French dubbing proof

Local prototype using original synthetic footage. This is preparation, not a customer acceptance or payment receipt.

Source SHA-256: `a640b9d9884369573c4d257dadd58023c7b473822edabddc41232665a15d73a4`. Duration: 38.181 seconds.
Transcript origin: automatic faster-whisper small.en; review required. Single speaker; stock voice only.
Translation: Helsinki-NLP/opus-mt-en-fr, revision `dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18` (Apache-2.0).
Speech: Kokoro v1.0 int8 ONNX, stock voice ff_siwis (Apache-2.0 model weights).
Background: Demucs 4.0.1 htdemucs separation of the original mixed audio; no supplied clean stem used.
Background gain: 0.85; shared master gain: 1.000000.

Every translated line is synthesized in full. A rate above 1.30× stops the job for review; no line is silently cut.
Separation can leave speech residuals or remove background detail. Recognition, translation and punctuation can be wrong.
No fluent human review, arbitrary customer-footage acceptance, speaker diarization, lip-sync or live commercial listing is claimed.

| Line | Source window | Dub window | Rate |
| --- | --- | --- | --- |
| line-001 | 0.340–5.700 | 0.340–5.884 | 1.0000× |
| line-002 | 9.580–15.520 | 9.580–17.707 | 1.0000× |
| line-003 | 19.220–23.920 | 19.220–24.082 | 1.0000× |
| line-004 | 27.650–34.190 | 27.650–35.795 | 1.0000× |

## Review script

### line-001

English: Welcome to LumenDesk. This short lesson explains how to prepare a clear project brief.

French: Bienvenue à LumenDesk. Cette courte leçon explique comment préparer un mémoire de projet clair.

### line-002

English: First, describe the result you need. Then list the files, the deadline, and the people who will review the work.

French: D'abord, décrivez le résultat dont vous avez besoin. Ensuite, listez les fichiers, la date limite et les personnes qui examineront le travail.

### line-003

English: Keep product names unchanged. Ask one clear question when a detail is missing.

French: Gardez les noms des produits inchangés. Posez une question claire lorsqu'un détail manque.

### line-004

English: Review the finished files before publishing. A useful report explains what was tested and what still needs confirmation.

French: Examiner les dossiers terminés avant de publier. Un rapport utile explique ce qui a été testé et ce qui a encore besoin de confirmation.
