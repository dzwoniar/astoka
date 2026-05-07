"""Long-Video Aware chunking — 20-min windows with 60s overlap.

Adapted from SamurAIGPT/AI-Youtube-Shorts-Generator (MIT). Rewritten as a pure
function over transcript segments. PRD HIGH-04, RESEARCH §6.

Why chunk: Llama 3.3 8B's 128k context technically holds 90 min of transcript,
but the "Lost in the Middle" effect collapses precision past ~30 min (RESEARCH §6).
We hard-chunk at 20 min and overlap by 60s so highlights spanning a boundary are
visible to both chunks; dedupe via IoU then merges them (see dedupe.py).
"""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TranscriptSegment:
    """Minimal interface — accepts anything with these three fields.

    Sprint 2 ASR populates these from WhisperX output.
    """

    text: str
    start: float
    end: float


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_id: str
    start: float
    end: float
    segments: tuple[TranscriptSegment, ...]


def chunk_transcript(
    segments: Sequence[TranscriptSegment],
    *,
    window_s: float = 20 * 60,
    overlap_s: float = 60,
) -> list[TranscriptChunk]:
    """Split transcript into overlapping windows.

    Args:
        segments: Transcript segments sorted by start time.
        window_s: Window size in seconds (default 20 min).
        overlap_s: Overlap between adjacent windows in seconds (default 60s).

    Returns:
        List of TranscriptChunk. Each segment may appear in multiple chunks
        (within the overlap zone). Empty input yields empty output.

    Raises:
        ValueError: if overlap_s >= window_s.
    """
    if overlap_s >= window_s:
        raise ValueError(f"overlap_s ({overlap_s}) must be less than window_s ({window_s})")
    if not segments:
        return []

    total_duration = segments[-1].end
    if total_duration <= window_s:
        return [
            TranscriptChunk(
                chunk_id="chunk_00",
                start=segments[0].start,
                end=total_duration,
                segments=tuple(segments),
            )
        ]

    step = window_s - overlap_s
    chunks: list[TranscriptChunk] = []
    chunk_start = 0.0
    idx = 0
    while chunk_start < total_duration:
        chunk_end = min(chunk_start + window_s, total_duration)
        chunk_segments = tuple(s for s in segments if s.start < chunk_end and s.end > chunk_start)
        if chunk_segments:
            chunks.append(
                TranscriptChunk(
                    chunk_id=f"chunk_{idx:02d}",
                    start=chunk_start,
                    end=chunk_end,
                    segments=chunk_segments,
                )
            )
            idx += 1
        if chunk_end >= total_duration:
            break
        chunk_start += step
    return chunks
