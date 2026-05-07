# ASR Baseline Report

**Status:** PENDING — script ready, awaiting hardware + samples.

## Wymagania do uruchomienia

1. Sprzęt: stacja z RTX 4090 (lub inny GPU z CUDA 12+).
2. 5 nagrań Akademii (long-form 20–60 min), reprezentatywnych dla typowego workflow:
   - 1× Zoom webinar z słabym mikrofonem klienta (worst-case)
   - 1× studio recording, dobry sprzęt (best-case)
   - 1× talking head, jeden mówca
   - 1× wywiad 2-osobowy
   - 1× nagranie z B-rollem / muzyką w tle
3. Manualna ground truth `.txt` per sample (transkrypcja zrobiona ręcznie lub poprawiona po automatycznej).
4. Pliki w `scripts/data/akademia_samples/sample_NN.{mp4,wav}` + `sample_NN.txt` obok.

## Run

```bash
make up                          # stack musi działać
make asr-spike                   # wewnątrz worker container
# lub lokalnie:
python scripts/asr_spike.py --samples-dir scripts/data/akademia_samples
```

Skrypt zaktualizuje ten plik z wynikami.

## Cele

- **WER ≤ 10%** (NFR-LANG-03, MET-06) — **gate przed Sprint 1**.
- **RTF (real-time factor) ≤ 0.083** (transcribe_s/audio_s; PRD NFR-PERF-02 = 5 min na 60 min input).

## Bramka decyzji

| Wynik WER | Status | Akcja |
|---|---|---|
| ≤ 10% | 🟢 zielony | Idź do Sprint 1 |
| 10–15% | 🟡 żółty | Sprint 1 OK, Sprint 2 dodaje denoising preprocessing (RNNoise, librosa) przed ASR |
| > 15% | 🔴 czerwony | Stop. Eskalacja do Janka. Opcje: zmiana stacku ASR (NeMo Canary), fine-tuning, ręczna preprocessing pipeline |

## Wybór modelu (po spike'u, do uzupełnienia)

A/B między:
- `distil-whisper-large-v3-pl` (Aspik101) — Polish-only distilled, mniejszy, szybszy
- `large-v3-turbo` — multilingual turbo

Decyzja: _TBD po pierwszym uruchomieniu._

## Uwagi

- Spike używa pure-Python WER/CER (bez `jiwer`) — zero external deps poza faster-whisper.
- Jeśli WER baseline jest słaby na konkretnych typach (np. Zoom z reverb), Sprint 2 dodaje dedykowany audio preprocessing (silero-vad cleaning + spectral noise gate).
- WhisperX forced alignment **nie jest** mierzony tym spike'm — to osobny test (caption sync error ≤120 ms, MET-07) zaplanowany w Sprint 6.
