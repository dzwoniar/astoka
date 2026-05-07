"""Highlight detection worker — heuristic scoring + Ollama LLM reranking.

Pipeline (RESEARCH §1-6):
  1. Compute heuristic scores on transcript segments + audio + scene changes
  2. Pick top-K candidates (score >= 70 by default)
  3. Chunk into 20-min windows with 60s overlap (vendor/samurai/chunking)
  4. For each chunk: ask Ollama Llama 3.3 8B to rerank with RESEARCH §4 schema
  5. Audio-correct boundaries (find nearest silence/sentence end within ±2s)
  6. IoU dedupe at 0.5 threshold (vendor/samurai/dedupe)
  7. Persist top-N highlights with feature scores + LLM rationale

Ollama unavailable → heuristic fallback: top-N candidates ranked by score,
no typology/hook_sentence/virality_reason set; llm_provider = "heuristic_fallback".
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from astoka_api.db.models import (
    Highlight,
    HighlightStatus,
    Job,
    JobStatus,
    JobType,
    SourceMaterial,
    Transcript,
)
from astoka_highlight.vendor.samurai.dedupe import deduplicate_highlights
from astoka_worker.celery_app import celery_app
from astoka_worker.config import get_worker_settings
from astoka_worker.tasks._helpers import (
    mark_failed,
    mark_running,
    mark_succeeded,
    update_progress,
)
from astoka_worker.util.db import db_session
from astoka_worker.util.events import publish_event
from astoka_worker.util.storage import download_file

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.3:8b-instruct-q4_K_M")
HEURISTIC_THRESHOLD = 70.0
LLM_TIMEOUT_S = float(os.environ.get("HIGHLIGHT_LLM_TIMEOUT_S", "600"))


# === Heuristic scoring ===

def _segment_score(
    seg: dict[str, Any],
    audio_features: dict[str, Any],
    scene_boundaries: list[float],
) -> tuple[float, dict[str, float]]:
    """Combine simple heuristics into 0-100 score for one transcript segment.

    Wagi z RESEARCH §2 (skompresowane do dostępnych w MVP cech):
      - text density (TF-IDF stub: word density per second) — 0.30
      - audio energy peak proximity                          — 0.30
      - scene change proximity                               — 0.20
      - segment length sweet spot (30-60s)                   — 0.20
    """
    start = float(seg.get("start", 0))
    end = float(seg.get("end", 0))
    duration = max(0.001, end - start)
    word_count = len(seg.get("words") or seg.get("text", "").split())

    # Density: words per second, normalized to typical 2-3 wps.
    wps = word_count / duration
    density_score = min(1.0, wps / 3.0)

    # Energy peak proximity (0-1 if any peak within 2s of segment center).
    center = (start + end) / 2
    peaks = audio_features.get("peaks", [])
    energy_score = 0.0
    if isinstance(peaks, list):
        for peak_t in peaks:
            if abs(peak_t - center) < 2.0:
                energy_score = 1.0
                break
            elif abs(peak_t - center) < 5.0:
                energy_score = max(energy_score, 0.5)

    # Scene change proximity.
    scene_score = 0.0
    for scene_t in scene_boundaries:
        if abs(scene_t - start) < 1.0 or abs(scene_t - end) < 1.0:
            scene_score = 1.0
            break
        elif abs(scene_t - center) < 5.0:
            scene_score = max(scene_score, 0.4)

    # Length sweet spot — prefer 30-60s segments. Linear penalty outside.
    if 25 <= duration <= 70:
        length_score = 1.0
    elif duration < 25:
        length_score = duration / 25
    else:
        length_score = max(0.0, 1.0 - (duration - 70) / 60)

    feature_scores = {
        "density": density_score,
        "audio_energy": energy_score,
        "scene_change": scene_score,
        "length": length_score,
    }

    composite = (
        0.30 * density_score
        + 0.30 * energy_score
        + 0.20 * scene_score
        + 0.20 * length_score
    ) * 100

    return composite, feature_scores


def _build_segment_windows(
    segments: list[dict[str, Any]], target_window_s: float = 45.0
) -> list[dict[str, Any]]:
    """Group consecutive transcript segments into ~target_window_s candidate clips."""
    if not segments:
        return []

    windows: list[dict[str, Any]] = []
    current_start = segments[0]["start"]
    current_end = segments[0]["end"]
    current_text: list[str] = [segments[0].get("text", "")]
    current_words: list[Any] = list(segments[0].get("words") or [])

    for seg in segments[1:]:
        if seg["end"] - current_start >= target_window_s:
            windows.append(
                {
                    "start": current_start,
                    "end": current_end,
                    "text": " ".join(current_text).strip(),
                    "words": current_words,
                }
            )
            current_start = seg["start"]
            current_end = seg["end"]
            current_text = [seg.get("text", "")]
            current_words = list(seg.get("words") or [])
        else:
            current_end = seg["end"]
            current_text.append(seg.get("text", ""))
            if seg.get("words"):
                current_words.extend(seg["words"])

    windows.append(
        {
            "start": current_start,
            "end": current_end,
            "text": " ".join(current_text).strip(),
            "words": current_words,
        }
    )
    return windows


def _audio_corrected_boundary(
    target_s: float, segments: list[dict[str, Any]], window_s: float = 2.0
) -> tuple[float, bool]:
    """Snap timestamp to nearest segment boundary within ±window_s.

    RESEARCH §3 simplified: sentence_end > silence > energy_min.
    Sentence boundaries are inferred from segment ends in transcript.
    """
    candidates = []
    for s in segments:
        for t in (s["start"], s["end"]):
            if abs(t - target_s) <= window_s:
                candidates.append(t)
    if not candidates:
        return target_s, False
    nearest = min(candidates, key=lambda t: abs(t - target_s))
    return nearest, True


# === Audio dynamics (lightweight: peak detection over time) ===

def _compute_audio_peaks(input_path: str, total_duration_s: float) -> list[float]:
    """Return list of timestamps where audio energy spikes.

    Cheap implementation: sample audio every 100ms via ffmpeg, find local maxima.
    Uses subprocess instead of a Python audio lib so no extra deps.
    """
    import subprocess

    from scipy.signal import find_peaks

    try:
        # Extract audio as raw PCM 16-bit mono 16kHz.
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp:
            tmp_path = tmp.name
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            tmp_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)

        import numpy as np

        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        sample_rate = 16000

        # Compute RMS energy in 100ms windows.
        win = sample_rate // 10
        n_windows = len(samples) // win
        energy = np.zeros(n_windows)
        for i in range(n_windows):
            energy[i] = np.sqrt(np.mean(samples[i * win : (i + 1) * win] ** 2))

        # Find peaks at least 1s apart (10 windows), height >= 1.5x median.
        if len(energy) == 0:
            return []
        threshold = 1.5 * float(np.median(energy))
        peaks, _ = find_peaks(energy, height=threshold, distance=10)
        return [float(p) / 10.0 for p in peaks]
    except Exception:
        return []


# === Scene detection ===

def _detect_scenes(input_path: str) -> list[float]:
    """Return list of scene-change timestamps using PySceneDetect."""
    try:
        from scenedetect import ContentDetector, SceneManager, open_video

        video = open_video(input_path)
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=27.0))
        sm.detect_scenes(video)
        scene_list = sm.get_scene_list()
        return [s[0].get_seconds() for s in scene_list]
    except Exception:
        return []


# === LLM reranking (Ollama) ===

PROMPT_TEMPLATE = """Jesteś ekspertem od wirusowych krótkich form wideo (TikTok/Reels/Shorts).
Otrzymasz pre-filtrowane kandydatów na highlights z transkrypcji wideo. Zrerankuj
ich i zwróć top {top_k} jako JSON.

REGUŁY:
1. KAŻDY highlight musi mieć clear hook w pierwszych 3 sekundach.
2. KAŻDY musi mieć krótkie virality_reason (jedno-dwuzdaniowe).
3. Klasyfikuj typology jako jedno z: opinion_bomb | hook_moment | story_peak | practical_value | revelation | comedy_punch.
4. Podawaj confidence (0.0-1.0) — jeśli nie jesteś pewny, daj <0.6.

ZWRÓĆ TYLKO JSON (bez markdown wrappera):
{{
  "candidates": [
    {{
      "id": "h_01",
      "start": <seconds>,
      "end": <seconds>,
      "viral_score": <0-100>,
      "typology": "<one of the 6>",
      "hook_sentence": "<copy from transcript>",
      "virality_reason": "<short>",
      "suggested_title": "<short>",
      "confidence": <0.0-1.0>
    }}
  ]
}}

PRE-FILTERED CANDIDATES:
{candidates_json}

DOSTĘPNYCH KANDYDATÓW: {n_candidates}
ZWRÓĆ TOP {top_k} (lub mniej jeśli słabe).
"""


def _ollama_rerank(
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 5,
    timeout_s: float = LLM_TIMEOUT_S,
) -> list[dict[str, Any]] | None:
    """Call Ollama API. Returns reranked candidates or None on failure."""
    settings = get_worker_settings()

    candidates_summary = [
        {
            "id": f"h_{i:02d}",
            "start": c["start"],
            "end": c["end"],
            "heuristic_score": round(c["score"], 1),
            "text": (c["text"][:500] + "...") if len(c["text"]) > 500 else c["text"],
        }
        for i, c in enumerate(candidates[: top_k * 3])  # don't pass more than 3x to LLM
    ]

    prompt = PROMPT_TEMPLATE.format(
        top_k=top_k,
        n_candidates=len(candidates_summary),
        candidates_json=json.dumps(candidates_summary, ensure_ascii=False, indent=2),
    )

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            parsed = json.loads(response_text)
            llm_candidates = parsed.get("candidates", [])
            if not isinstance(llm_candidates, list):
                return None
            return llm_candidates
    except Exception:
        return None


# === Main task ===

@celery_app.task(name="astoka.highlights", bind=True, max_retries=1)
def detect_highlights(self, source_material_id: str) -> str:
    """Main highlight detection pipeline."""
    sm_uuid = UUID(source_material_id)

    # Create job upfront in own session.
    with db_session() as session:
        sm = session.get(SourceMaterial, sm_uuid)
        if sm is None:
            raise RuntimeError(f"SourceMaterial {sm_uuid} not found")

        job = Job(
            source_material_id=sm_uuid,
            job_type=JobType.HIGHLIGHT,
            status=JobStatus.PENDING,
            celery_task_id=self.request.id,
        )
        session.add(job)
        session.flush()
        job_id = str(job.id)

    with db_session() as session:
        job, sm = mark_running(session, job_id, message="Pobieram transkrypcję...")

        # Load transcript.
        from sqlalchemy import select

        transcript = (
            session.execute(
                select(Transcript)
                .where(Transcript.source_material_id == sm.id)
                .order_by(Transcript.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if transcript is None or not transcript.segments_json:
            mark_failed(session, job, sm, error="No transcript available")
            raise RuntimeError("no transcript")

        segments = list(transcript.segments_json)

        # Phase 1: candidate windows from transcript.
        update_progress(session, job, sm, progress=0.10, message="Buduję kandydatów...")
        windows = _build_segment_windows(segments, target_window_s=45.0)
        if not windows:
            mark_succeeded(session, job, sm, result={"highlight_count": 0})
            return str(sm.id)

        # Phase 2: download proxy/source for audio + scene detection.
        update_progress(
            session, job, sm, progress=0.25, message="Analizuję audio + sceny..."
        )
        scenes_list: list[float] = []
        peaks: list[float] = []

        if sm.proxy_storage_key or sm.storage_key:
            with tempfile.TemporaryDirectory() as tmpdir:
                local_in = str(Path(tmpdir) / "media.mp4")
                key = sm.proxy_storage_key or sm.storage_key
                try:
                    if key:
                        download_file(key, local_in)
                        peaks = _compute_audio_peaks(local_in, sm.duration_s or 0.0)
                        scenes_list = _detect_scenes(local_in)
                except Exception:
                    # Best-effort. Fall through with empty signals.
                    pass

        audio_features = {"peaks": peaks}

        # Phase 3: heuristic scoring.
        update_progress(session, job, sm, progress=0.50, message="Heurystyczny scoring...")
        scored = []
        for w in windows:
            score, features = _segment_score(w, audio_features, scenes_list)
            scored.append({**w, "score": score, "feature_scores": features})

        # Filter to top candidates and chunk for LLM.
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = scored[:15]  # safety cap

        # Phase 4: LLM rerank (best effort).
        update_progress(session, job, sm, progress=0.65, message="LLM reranking...")
        llm_results = _ollama_rerank(top_candidates, top_k=10)
        used_llm = llm_results is not None
        llm_provider = (
            f"ollama_{OLLAMA_MODEL}" if used_llm else "heuristic_fallback"
        )

        # Phase 5: build final highlight list.
        update_progress(
            session, job, sm, progress=0.85, message="Audio-correction + dedupe..."
        )

        finals: list[dict[str, Any]] = []
        if used_llm:
            for llm_c in (llm_results or [])[:10]:
                start = float(llm_c.get("start", 0))
                end = float(llm_c.get("end", 0))
                if end <= start:
                    continue
                # Match heuristic record by closest interval to inherit feature_scores.
                base = min(
                    top_candidates,
                    key=lambda c: abs(c["start"] - start) + abs(c["end"] - end),
                )
                finals.append(
                    {
                        "start": start,
                        "end": end,
                        "viral_score": int(llm_c.get("viral_score", 0)),
                        "typology": llm_c.get("typology"),
                        "hook_sentence": llm_c.get("hook_sentence"),
                        "virality_reason": llm_c.get("virality_reason"),
                        "suggested_title": llm_c.get("suggested_title"),
                        "confidence": float(llm_c.get("confidence", 0.0)),
                        "feature_scores": base.get("feature_scores", {}),
                    }
                )
        else:
            # Heuristic fallback: top 7.
            for c in top_candidates[:7]:
                finals.append(
                    {
                        "start": c["start"],
                        "end": c["end"],
                        "viral_score": int(c["score"]),
                        "typology": None,
                        "hook_sentence": (c["text"][:200] if c["text"] else None),
                        "virality_reason": "Heurystyczny scoring (LLM niedostępny).",
                        "suggested_title": None,
                        "confidence": None,
                        "feature_scores": c["feature_scores"],
                    }
                )

        # Audio-correct boundaries.
        for f in finals:
            new_start, snapped_s = _audio_corrected_boundary(f["start"], segments)
            new_end, snapped_e = _audio_corrected_boundary(f["end"], segments)
            f["start"] = new_start
            f["end"] = new_end
            f["audio_corrected"] = snapped_s or snapped_e

        # IoU dedupe.
        class _Cand:
            def __init__(self, d: dict[str, Any]):
                self._d = d

            @property
            def start(self) -> float:
                return self._d["start"]

            @property
            def end(self) -> float:
                return self._d["end"]

            @property
            def viral_score(self) -> float:
                return float(self._d["viral_score"])

        wrapped = [_Cand(f) for f in finals]
        kept = deduplicate_highlights(wrapped, iou_threshold=0.5)
        final_dicts = [w._d for w in kept]

        # Persist.
        update_progress(session, job, sm, progress=0.95, message="Zapisuję highlights...")
        for f in final_dicts:
            h = Highlight(
                source_material_id=sm.id,
                start_s=f["start"],
                end_s=f["end"],
                audio_corrected=f.get("audio_corrected", False),
                viral_score=f["viral_score"],
                confidence=f.get("confidence"),
                typology=f.get("typology"),
                hook_sentence=f.get("hook_sentence"),
                virality_reason=f.get("virality_reason"),
                suggested_title=f.get("suggested_title"),
                llm_provider=llm_provider,
                feature_scores=f.get("feature_scores", {}),
                status=HighlightStatus.PENDING,
            )
            session.add(h)
        session.flush()

        mark_succeeded(
            session,
            job,
            sm,
            result={
                "highlight_count": len(final_dicts),
                "llm_provider": llm_provider,
                "used_llm": used_llm,
            },
        )

        publish_event(
            sm.project_id,
            {
                "event": "highlights_ready",
                "project_id": str(sm.project_id),
                "source_material_id": str(sm.id),
                "highlight_count": len(final_dicts),
            },
        )

        return str(sm.id)
