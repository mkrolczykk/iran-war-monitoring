"""
Data models for the Iran War Monitoring application.

Uses Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Classification of a news event."""
    AIRSTRIKE = "airstrike"
    MISSILE = "missile"
    EXPLOSION = "explosion"
    ALERT = "alert"
    MILITARY_MOVEMENT = "military_movement"
    POLITICAL = "political"
    HUMANITARIAN = "humanitarian"
    OTHER = "other"


# Mapping of EventType → display properties
EVENT_TYPE_CONFIG = {
    EventType.AIRSTRIKE:          {"icon": "bomb",       "color": "red",       "indicator": "STR", "label": "Airstrike"},
    EventType.MISSILE:            {"icon": "rocket",     "color": "purple",    "indicator": "MSL", "label": "Missile"},
    EventType.EXPLOSION:          {"icon": "fire",       "color": "orange",    "indicator": "EXP", "label": "Explosion"},
    EventType.ALERT:              {"icon": "bell",       "color": "yellow",    "indicator": "ALT", "label": "Alert"},
    EventType.MILITARY_MOVEMENT:  {"icon": "shield",     "color": "blue",      "indicator": "MIL", "label": "Military"},
    EventType.POLITICAL:          {"icon": "institution","color": "gray",      "indicator": "POL", "label": "Political"},
    EventType.HUMANITARIAN:       {"icon": "heart",      "color": "pink",      "indicator": "HUM", "label": "Humanitarian"},
    EventType.OTHER:              {"icon": "info-sign",  "color": "white",     "indicator": "INF", "label": "Other"},
}


# ---------------------------------------------------------------------------
# NewsEvent
# ---------------------------------------------------------------------------

class NewsEvent(BaseModel):
    """A single geolocated news event from any source."""

    id: str = Field(default="", description="Unique hash (auto-generated if empty)")
    title: str
    summary: str = ""
    source_name: str
    source_url: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location_name: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_type: EventType = EventType.OTHER
    severity: int = Field(default=3, ge=1, le=5)

    # For internal processing – not displayed
    raw_text: str = Field(default="", repr=False)

    def model_post_init(self, __context) -> None:
        """Auto-generate a deterministic id from title + source (no timestamp).

        Dropping the timestamp guarantees the exact same headline from the
        same source always maps to the same ID, regardless of scrape time.
        """
        if not self.id:
            norm_title = self.title.lower().strip()
            blob = f"{norm_title}|{self.source_name}"
            self.id = hashlib.sha256(blob.encode()).hexdigest()[:16]

    @field_validator("severity", mode="before")
    @classmethod
    def clamp_severity(cls, v):
        if isinstance(v, (int, float)):
            return max(1, min(5, int(v)))
        return v

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def display_config(self) -> dict:
        """Return icon/colour/emoji for this event type."""
        return EVENT_TYPE_CONFIG.get(self.event_type, EVENT_TYPE_CONFIG[EventType.OTHER])

    def age_minutes(self, now: datetime | None = None) -> float:
        """Minutes elapsed since the event timestamp."""
        now = now or datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds() / 60.0


# ---------------------------------------------------------------------------
# EventStore – in-memory collection with dedup & sorting
# ---------------------------------------------------------------------------

class EventStore:
    """Thread-safe in-memory store for NewsEvent instances."""

    def __init__(self, max_events: int = 500) -> None:
        self._events: dict[str, NewsEvent] = {}   # id → event
        self._max_events = max_events

    def add(self, event: NewsEvent) -> bool:
        """Add event if not already present. Returns True if newly added."""
        if event.id in self._events:
            return False
        self._events[event.id] = event
        self._trim()
        return True

    def add_many(self, events: List[NewsEvent]) -> int:
        """Add multiple events; returns count of newly added."""
        added = 0
        for ev in events:
            if self.add(ev):
                added += 1
        return added

    def get_all(self, *, with_location_only: bool = False) -> List[NewsEvent]:
        """Return events sorted newest-first."""
        events = list(self._events.values())
        if with_location_only:
            events = [e for e in events if e.has_location]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()

    def _trim(self) -> None:
        """Remove oldest events if store exceeds max."""
        if len(self._events) > self._max_events:
            sorted_ids = sorted(
                self._events, key=lambda k: self._events[k].timestamp
            )
            for eid in sorted_ids[: len(self._events) - self._max_events]:
                del self._events[eid]
