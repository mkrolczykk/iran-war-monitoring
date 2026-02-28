"""
Situation summary generator.

Produces a concise, natural-language overview of the current crisis state
based on recent events — no external API required.

The summary analyses the last 2 hours of events, extracting:
- event type counts and dominant categories
- most-affected locations
- intensity trend (escalating / stable / calming)
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List

from models.events import EventType, EVENT_TYPE_CONFIG, NewsEvent


# ── Labels for natural language ───────────────────────────────────────────

_TYPE_NAMES = {
    "Airstrike":    ("airstrike",            "airstrikes"),
    "Missile":      ("missile event",        "missile events"),
    "Explosion":    ("explosion",            "explosions"),
    "Alert":        ("alert",                "alerts"),
    "Military":     ("military movement",    "military movements"),
    "Political":    ("political development", "political developments"),
    "Humanitarian": ("humanitarian report",  "humanitarian reports"),
    "Other":        ("other report",         "other reports"),
}

# Types considered "critical" for summary emphasis
_CRITICAL_TYPES = {"Airstrike", "Missile", "Explosion"}

# Time windows
_SUMMARY_WINDOW_HOURS = 2
_TREND_RECENT_MIN = 30
_TREND_OLDER_MIN = 90  # 30–120 min range for comparison


def _type_name(label: str, count: int) -> str:
    """Return the correct singular or plural form for a given event type."""
    singular, plural = _TYPE_NAMES.get(label, (label.lower(), label.lower() + "s"))
    return singular if count == 1 else plural


def generate_summary(events: List[NewsEvent]) -> str:
    """Generate a 2-3 sentence situation summary from the latest events.

    Parameters
    ----------
    events : list[NewsEvent]
        All events, newest-first.

    Returns
    -------
    str
        Natural-language summary. Empty string if no recent events.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=_SUMMARY_WINDOW_HOURS)

    recent = [ev for ev in events if ev.timestamp >= cutoff]
    if not recent:
        return "No significant events reported in the last 2 hours."

    # ── Counts by type ────────────────────────────────────────────
    type_counts: Counter = Counter()
    for ev in recent:
        label = ev.display_config["label"]
        type_counts[label] += 1

    # ── Top locations ─────────────────────────────────────────────
    loc_counts: Counter = Counter()
    for ev in recent:
        if ev.location_name:
            loc_counts[ev.location_name] += 1
    top_locations = [loc for loc, _ in loc_counts.most_common(3)]

    # ── Intensity trend ───────────────────────────────────────────
    trend_cutoff_recent = now - timedelta(minutes=_TREND_RECENT_MIN)
    trend_cutoff_older = now - timedelta(minutes=_TREND_RECENT_MIN + _TREND_OLDER_MIN)

    count_recent = sum(1 for ev in recent if ev.timestamp >= trend_cutoff_recent)
    count_older = sum(
        1 for ev in recent
        if trend_cutoff_older <= ev.timestamp < trend_cutoff_recent
    )

    # ── Build sentences ───────────────────────────────────────────
    sentences: list[str] = []

    # Sentence 1: main activity
    critical_parts = []
    other_parts = []
    for label, count in type_counts.most_common():
        phrase = f"{count} {_type_name(label, count)}"
        if label in _CRITICAL_TYPES:
            critical_parts.append(phrase)
        else:
            other_parts.append(phrase)

    if critical_parts:
        activity = _join_list(critical_parts)
        loc_suffix = ""
        if top_locations:
            loc_suffix = f" near {_join_list(top_locations)}"
        sentences.append(
            f"Active situation: {activity}{loc_suffix} "
            f"in the last {_SUMMARY_WINDOW_HOURS} hours."
        )
    elif other_parts:
        activity = _join_list(other_parts[:3])
        sentences.append(
            f"Monitoring: {activity} reported in the last "
            f"{_SUMMARY_WINDOW_HOURS} hours."
        )

    # Sentence 2: intensity trend
    if count_recent > 0 or count_older > 0:
        if count_recent > count_older * 1.5 and count_recent >= 3:
            sentences.append(
                f"Intensity is escalating with {count_recent} new events "
                f"in the last {_TREND_RECENT_MIN} minutes."
            )
        elif count_older > count_recent * 1.5 and count_older >= 3:
            sentences.append(
                f"Activity appears to be calming — {count_recent} events "
                f"in the last {_TREND_RECENT_MIN} min vs. {count_older} earlier."
            )
        else:
            sentences.append(
                f"{count_recent} events in the last {_TREND_RECENT_MIN} minutes, "
                f"situation remains fluid."
            )

    # Sentence 3: humanitarian / location breadth
    humanitarian_count = type_counts.get("Humanitarian", 0)
    if humanitarian_count >= 2:
        loc_count = len(loc_counts)
        sentences.append(
            f"Humanitarian impact reported "
            f"{'across ' + str(loc_count) + ' locations' if loc_count > 1 else 'in the region'}."
        )
    elif len(top_locations) >= 2 and not critical_parts:
        sentences.append(
            f"Events reported across {_join_list(top_locations)}."
        )

    return " ".join(sentences)


def _join_list(items: list[str]) -> str:
    """Join list items with commas and 'and'."""
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
