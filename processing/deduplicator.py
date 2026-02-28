"""
Cross-source deduplication.

Detects near-duplicate events from different sources by comparing
title similarity and timestamps.

Same-source duplicates use a wider window (120 min) and higher similarity
(0.85) to catch re-scraped headlines reliably.
"""

from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher
from typing import List

from models.events import NewsEvent

# ── Thresholds ────────────────────────────────────────────────────────────
# Cross-source: different outlets covering the same story
_CROSS_SOURCE_WINDOW_MIN = 30
_CROSS_SOURCE_SIM = 0.65

# Same-source: the same outlet re-publishing / updating a headline
_SAME_SOURCE_WINDOW_MIN = 120
_SAME_SOURCE_SIM = 0.85


def _similar(a: str, b: str, threshold: float) -> bool:
    """Return True if normalised similarity ≥ threshold."""
    a_norm = a.lower().strip()
    b_norm = b.lower().strip()
    if a_norm == b_norm:
        return True
    return SequenceMatcher(None, a_norm, b_norm).ratio() >= threshold


def _is_duplicate(event: NewsEvent, existing: NewsEvent) -> bool:
    """Check whether *event* is a duplicate of *existing*."""
    same_source = event.source_name == existing.source_name

    if same_source:
        window = timedelta(minutes=_SAME_SOURCE_WINDOW_MIN)
        threshold = _SAME_SOURCE_SIM
    else:
        window = timedelta(minutes=_CROSS_SOURCE_WINDOW_MIN)
        threshold = _CROSS_SOURCE_SIM

    time_close = abs(event.timestamp - existing.timestamp) <= window
    return time_close and _similar(event.title, existing.title, threshold)


def deduplicate(events: List[NewsEvent]) -> List[NewsEvent]:
    """
    Remove near-duplicates from *events*.

    When duplicates are found, the event with the longer summary is kept
    (i.e. the more detailed report).
    """
    if not events:
        return []

    kept: List[NewsEvent] = []

    for event in events:
        is_dup = False
        for i, existing in enumerate(kept):
            if _is_duplicate(event, existing):
                if len(event.summary) > len(existing.summary):
                    kept[i] = event
                is_dup = True
                break
        if not is_dup:
            kept.append(event)

    return kept


def deduplicate_against_existing(
    incoming: List[NewsEvent],
    existing: List[NewsEvent],
) -> List[NewsEvent]:
    """Return only those *incoming* events that are NOT duplicates of *existing*.

    This is used to filter a freshly-scraped batch against the store before
    adding, catching duplicates that survived the batch-only dedup.
    """
    novel: List[NewsEvent] = []
    for event in incoming:
        is_dup = False
        for ex in existing:
            if _is_duplicate(event, ex):
                is_dup = True
                break
        if not is_dup:
            novel.append(event)
    return novel
