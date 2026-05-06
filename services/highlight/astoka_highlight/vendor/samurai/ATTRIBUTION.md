# Attribution

This directory contains code extracted and adapted from
[SamurAIGPT/AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator)
under the MIT License.

## What was extracted

| Module | Origin | Adaptation |
|---|---|---|
| `chunking.py` | Long-Video Aware chunking logic | Rewritten as pure function, no I/O side-effects |
| `dedupe.py` | IoU-based duplicate suppression | Rewritten with explicit type hints + tests |
| `prompts/highlight_reranker.txt` | Original highlight detection prompt | Adapted to RESEARCH §4 schema (typology, hook_sentence, virality_reason, confidence) — Polish + English support |

## What was deliberately NOT pulled

The upstream repo includes its own:
- ASR pipeline (we use faster-whisper + WhisperX)
- Face detection (we use YOLOv11s + ByteTrack — REFR-XX)
- FFmpeg orchestration (we use our own — RNDR-XX)
- Vertical video reframe (we replace with REFR-XX)

These are reimplemented from scratch using Astoki's chosen stack (PRD §8).

## Decision: copy + extract vs submodule

Per Sprint 0 plan (clarified with Janek): **selective copy** chosen over submodule
because:
1. The upstream repo's dependency graph is heavy and conflicts with our stack
2. We need to modify the prompt extensively for Polish + RESEARCH schema
3. Clean namespace under `services/highlight/astoka_highlight/vendor/samurai/` is easier to reason about

If upstream evolves significantly we re-pull manually and document deltas here.
