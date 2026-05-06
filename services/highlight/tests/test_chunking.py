"""Tests for vendor/samurai/chunking.py — Long-Video Aware chunking."""

import pytest

from astoka_highlight.vendor.samurai.chunking import (
    TranscriptSegment,
    chunk_transcript,
)


def _seg(start: float, end: float, text: str = "x") -> TranscriptSegment:
    return TranscriptSegment(text=text, start=start, end=end)


def test_empty_input_returns_empty() -> None:
    assert chunk_transcript([]) == []


def test_short_transcript_single_chunk() -> None:
    segments = [_seg(0, 60), _seg(60, 120), _seg(120, 180)]
    chunks = chunk_transcript(segments)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk_00"
    assert chunks[0].start == 0
    assert chunks[0].end == 180


def test_chunks_have_60s_overlap_for_25min_input() -> None:
    # 25 min total, 20-min window, 60s overlap.
    # Expect 2 chunks: [0, 1200] and [1140, 1500].
    segments = [_seg(i * 30, (i + 1) * 30) for i in range(50)]
    chunks = chunk_transcript(segments, window_s=1200, overlap_s=60)
    assert len(chunks) == 2
    assert chunks[0].start == 0
    assert chunks[0].end == 1200
    assert chunks[1].start == 1140  # 1200 - 60 overlap
    # Overlap zone (1140s..1200s) is in both chunks.
    overlap_segs = [s for s in segments if 1140 <= s.start < 1200]
    for s in overlap_segs:
        assert s in chunks[0].segments
        assert s in chunks[1].segments


def test_invalid_overlap_raises() -> None:
    with pytest.raises(ValueError):
        chunk_transcript([_seg(0, 100)], window_s=60, overlap_s=120)
