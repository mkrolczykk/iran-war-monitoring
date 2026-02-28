"""
Cross-source deduplication.

Detects near-duplicate events from different sources by comparing
title similarity and timestamps.
"""

from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher
from typing import List

from models.events import NewsEvent


def _similar(a: str, b: str, threshold: float = 0.65) -> bool:
    """Return True if normalised similarity ≥ threshold."""
    a_norm = a.lower().strip()
    b_norm = b.lower().strip()
    return SequenceMatcher(None, a_norm, b_norm).ratio() >= threshold


def deduplicate(
    events: List[NewsEvent],
    *,
    time_window_minutes: int = 30,
    similarity_threshold: float = 0.65,
) -> List[NewsEvent]:
    """
    Remove near-duplicates from *events*.

    Two events are considered duplicates if:
    - Their titles are similar (above *similarity_threshold*), AND
    - They occurred within *time_window_minutes* of each other.

    When duplicates are found, the event with the longer summary is kept
    (i.e. the more detailed report).
    """
    if not events:
        return []

    kept: List[NewsEvent] = []
    window = timedelta(minutes=time_window_minutes)

    for event in events:
        is_dup = False
        for i, existing in enumerate(kept):
            time_close = abs(event.timestamp - existing.timestamp) <= window
            if time_close and _similar(event.title, existing.title, similarity_threshold):
                # Keep the more detailed one
                if len(event.summary) > len(existing.summary):
                    kept[i] = event
                is_dup = True
                break
        if not is_dup:
            kept.append(event)

    return kept
