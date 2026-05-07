"""IoU-based deduplication for highlight candidates.

Adapted from SamurAIGPT/AI-Youtube-Shorts-Generator (MIT). PRD HIGH-07, RESEARCH §5.

Eliminates the "Vizard problem" — algorithmic redundancy where ten near-identical
clips of the same minute pollute the candidate list. Sort by score desc, walk the
list, and drop any candidate whose temporal IoU with an already-kept item exceeds
the threshold (default 0.5).
"""

from typing import Protocol, TypeVar


class HasInterval(Protocol):
    @property
    def start(self) -> float: ...
    @property
    def end(self) -> float: ...
    @property
    def viral_score(self) -> float: ...


T = TypeVar("T", bound=HasInterval)


def calculate_iou(a: HasInterval, b: HasInterval) -> float:
    """Intersection-over-Union for time intervals."""
    intersection_start = max(a.start, b.start)
    intersection_end = min(a.end, b.end)
    intersection = max(0.0, intersection_end - intersection_start)

    union = (a.end - a.start) + (b.end - b.start) - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def deduplicate_highlights(
    candidates: list[T],
    *,
    iou_threshold: float = 0.5,
) -> list[T]:
    """Greedy NMS on time intervals, ordered by viral_score desc.

    Args:
        candidates: highlight candidates with start/end/viral_score.
        iou_threshold: drop if IoU with a higher-scored kept item exceeds this.

    Returns:
        Subset of input, preserving the highest-scoring representative of each cluster.
    """
    if not candidates:
        return []

    sorted_candidates = sorted(candidates, key=lambda x: x.viral_score, reverse=True)
    kept: list[T] = []

    for candidate in sorted_candidates:
        is_duplicate = any(calculate_iou(candidate, k) > iou_threshold for k in kept)
        if not is_duplicate:
            kept.append(candidate)

    return kept
