"""Tests for vendor/samurai/dedupe.py — IoU-based NMS."""

from dataclasses import dataclass

from astoka_highlight.vendor.samurai.dedupe import (
    calculate_iou,
    deduplicate_highlights,
)


@dataclass
class Candidate:
    start: float
    end: float
    viral_score: float
    label: str = ""


def test_iou_no_overlap() -> None:
    a = Candidate(0, 10, 80)
    b = Candidate(20, 30, 70)
    assert calculate_iou(a, b) == 0


def test_iou_full_overlap() -> None:
    a = Candidate(10, 20, 80)
    b = Candidate(10, 20, 70)
    assert calculate_iou(a, b) == 1.0


def test_iou_half_overlap() -> None:
    a = Candidate(0, 20, 80)
    b = Candidate(10, 30, 70)
    # intersection = 10, union = 30. IoU = 0.333
    assert abs(calculate_iou(a, b) - 1 / 3) < 1e-6


def test_dedupe_keeps_higher_score() -> None:
    candidates = [
        Candidate(0, 30, 90, "A"),
        Candidate(5, 35, 70, "B"),  # high overlap with A
        Candidate(60, 90, 80, "C"),
    ]
    kept = deduplicate_highlights(candidates)
    labels = [c.label for c in kept]
    assert "A" in labels
    assert "C" in labels
    assert "B" not in labels


def test_dedupe_threshold_respected() -> None:
    # IoU of (0,10) and (5,15) = 5/15 ≈ 0.333. Below default 0.5 threshold — keep both.
    candidates = [
        Candidate(0, 10, 90, "A"),
        Candidate(5, 15, 80, "B"),
    ]
    assert len(deduplicate_highlights(candidates)) == 2

    # Same candidates with stricter threshold — drop B.
    assert len(deduplicate_highlights(candidates, iou_threshold=0.3)) == 1


def test_dedupe_empty_input() -> None:
    assert deduplicate_highlights([]) == []
