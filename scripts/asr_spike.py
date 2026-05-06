#!/usr/bin/env python3
"""ASR spike — Faza 0 gate przed Sprint 1.

Usage:
    # Inside worker container (has GPU + faster-whisper):
    python /app/scripts/asr_spike.py
    # Or locally if you have GPU + deps:
    python scripts/asr_spike.py --samples-dir scripts/data/akademia_samples

Cel:
    Zmierzyć WER (Word Error Rate) na 5 realnych nagraniach Akademii dla obu
    kandydatów modelu (PRD §8 stack) i podjąć decyzję przed Sprint 1.

    Modele A/B:
    - distil-whisper-large-v3-pl (Aspik101) — Polish-only distilled
    - large-v3-turbo                       — multilingual turbo

Gate (PRD MET-06, NFR-LANG-03):
    WER ≤ 10% → green light, idziemy z modelem zwycięskim
    WER 10–15% → yellow, kontynuujemy z planem dodania denoising preprocessing w Sprint 2
    WER > 15% → red, eskalacja do Janka, możliwa zmiana stacku ASR

Wymagane wejście:
    scripts/data/akademia_samples/
        sample_01.mp4 (lub .wav/.mp3)
        sample_01.txt  ← ground truth transkrypcja (manualna)
        sample_02.mp4
        sample_02.txt
        ...

Wyjście:
    docs/asr-baseline.md — markdown report z tabelą wyników, decyzją i rekomendacjami.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLES = REPO_ROOT / "scripts" / "data" / "akademia_samples"
DEFAULT_REPORT = REPO_ROOT / "docs" / "asr-baseline.md"

MODELS = [
    # (display_name, faster-whisper model id, language hint)
    ("distil-whisper-large-v3-pl", "Aspik101/distil-whisper-large-v3-pl-ct2", "pl"),
    ("large-v3-turbo", "large-v3-turbo", "pl"),
]


@dataclass
class SampleResult:
    sample: str
    model: str
    duration_s: float
    transcribe_s: float
    real_time_factor: float  # transcribe_s / duration_s
    wer: float | None  # None if no reference txt available
    cer: float | None
    error: str | None = None


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — matches typical WER conventions."""
    import re

    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate via Levenshtein on tokens. Pure Python — no jiwer dep needed for spike."""
    ref = normalize_text(reference).split()
    hyp = normalize_text(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0

    # Standard DP table for edit distance.
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[n][m] / n


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate — same DP but on chars. Useful sanity check for inflected langs."""
    ref = normalize_text(reference).replace(" ", "")
    hyp = normalize_text(hypothesis).replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[n][m] / n


def transcribe_one(
    model_id: str,
    audio_path: Path,
    language: str,
) -> tuple[str, float, float]:
    """Run faster-whisper. Returns (transcript, audio_duration_s, transcribe_duration_s)."""
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]

    # GPU + fp16 — RTX 4090 (PRD NFR-HW-01). Falls back to CPU int8 if no CUDA.
    try:
        model = WhisperModel(model_id, device="cuda", compute_type="float16")
    except Exception:
        model = WhisperModel(model_id, device="cpu", compute_type="int8")

    t0 = time.monotonic()
    segments, info = model.transcribe(str(audio_path), language=language, beam_size=5)
    chunks = [seg.text for seg in segments]
    transcript = " ".join(chunks).strip()
    elapsed = time.monotonic() - t0

    return transcript, info.duration, elapsed


def find_samples(samples_dir: Path) -> list[Path]:
    if not samples_dir.exists():
        return []
    audio_exts = {".mp4", ".mov", ".mkv", ".wav", ".mp3", ".m4a", ".flac"}
    return sorted(p for p in samples_dir.iterdir() if p.suffix.lower() in audio_exts)


def reference_for(sample: Path) -> str | None:
    txt = sample.with_suffix(".txt")
    if not txt.exists():
        return None
    return txt.read_text(encoding="utf-8")


def run_spike(samples_dir: Path) -> list[SampleResult]:
    samples = find_samples(samples_dir)
    if not samples:
        print(f"No samples found in {samples_dir}", file=sys.stderr)
        print("Add 5 .mp4/.wav files + matching .txt ground truth files. See script docstring.")
        return []

    results: list[SampleResult] = []
    for sample_path in samples:
        ref = reference_for(sample_path)
        for display_name, model_id, lang in MODELS:
            print(f"[{display_name}] {sample_path.name} ...", flush=True)
            try:
                hyp, audio_s, trans_s = transcribe_one(model_id, sample_path, lang)
                wer = compute_wer(ref, hyp) if ref else None
                cer = compute_cer(ref, hyp) if ref else None
                results.append(
                    SampleResult(
                        sample=sample_path.name,
                        model=display_name,
                        duration_s=audio_s,
                        transcribe_s=trans_s,
                        real_time_factor=trans_s / audio_s if audio_s else 0.0,
                        wer=wer,
                        cer=cer,
                    )
                )
                wer_str = f"{wer*100:.1f}%" if wer is not None else "n/a (no .txt)"
                print(
                    f"  duration={audio_s:.1f}s transcribe={trans_s:.1f}s "
                    f"RTF={trans_s/audio_s:.2f}× WER={wer_str}"
                )
            except Exception as exc:
                results.append(
                    SampleResult(
                        sample=sample_path.name,
                        model=display_name,
                        duration_s=0,
                        transcribe_s=0,
                        real_time_factor=0,
                        wer=None,
                        cer=None,
                        error=str(exc),
                    )
                )
                print(f"  ERROR: {exc}", file=sys.stderr)
    return results


def write_report(results: list[SampleResult], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not results:
        report_path.write_text(
            "# ASR Baseline Report\n\n"
            "**Status:** NO SAMPLES — add files to `scripts/data/akademia_samples/` and re-run.\n",
            encoding="utf-8",
        )
        return

    lines = [
        "# ASR Baseline Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Samples:** {len({r.sample for r in results})}",
        f"**Models tested:** {', '.join({r.model for r in results})}",
        "",
        "## Cele (PRD)",
        "",
        "- WER ≤ 10% (NFR-LANG-03, MET-06)",
        "- ASR ≤ 5 min na 60-min input → RTF ≤ 0.083 (NFR-PERF-02)",
        "",
        "## Wyniki per sample × model",
        "",
        "| Sample | Model | Duration | Transcribe | RTF | WER | CER |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x.sample, x.model)):
        wer_s = f"{r.wer*100:.1f}%" if r.wer is not None else "n/a"
        cer_s = f"{r.cer*100:.1f}%" if r.cer is not None else "n/a"
        err = f" ⚠ {r.error}" if r.error else ""
        lines.append(
            f"| {r.sample} | {r.model} | {r.duration_s:.1f}s | "
            f"{r.transcribe_s:.1f}s | {r.real_time_factor:.2f}× | {wer_s} | {cer_s} |{err}"
        )

    # Aggregate per model
    lines += ["", "## Średnia per model", "", "| Model | Avg WER | Avg CER | Avg RTF |", "|---|---|---|---|"]
    by_model: dict[str, list[SampleResult]] = {}
    for r in results:
        by_model.setdefault(r.model, []).append(r)
    for model, rows in by_model.items():
        wers = [r.wer for r in rows if r.wer is not None]
        cers = [r.cer for r in rows if r.cer is not None]
        rtfs = [r.real_time_factor for r in rows if r.real_time_factor > 0]
        avg_wer = f"{sum(wers)/len(wers)*100:.1f}%" if wers else "n/a"
        avg_cer = f"{sum(cers)/len(cers)*100:.1f}%" if cers else "n/a"
        avg_rtf = f"{sum(rtfs)/len(rtfs):.2f}×" if rtfs else "n/a"
        lines.append(f"| {model} | {avg_wer} | {avg_cer} | {avg_rtf} |")

    lines += [
        "",
        "## Decyzja (wypełnij ręcznie po analizie)",
        "",
        "- **Wybrany model:** _TBD_",
        "- **Status gate (zielony / żółty / czerwony):** _TBD_",
        "- **Komentarz:** _TBD_ (np. potrzeba denoising preprocessing, fine-tuning, zmiana stacku)",
        "",
        "## Surowe dane (JSON)",
        "",
        "```json",
        json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False),
        "```",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written: {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    results = run_spike(args.samples_dir)
    write_report(results, args.report)
    return 0 if results else 2


if __name__ == "__main__":
    sys.exit(main())
