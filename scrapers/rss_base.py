"""
Base RSS scraper using feedparser.

Parses RSS/Atom feeds and converts entries into NewsEvent objects.
Reuses the HTTP fetching and enrichment logic from BaseScraper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import feedparser
from dateutil import parser as dateparser

from config.settings import SOURCES_BY_NAME
from models.events import NewsEvent
from processing.categorizer import categorize_event, estimate_severity
from processing.geocoder import extract_primary_location
from utils.logger import get_logger

logger = get_logger(__name__)


class RSSBaseScraper:
    """
    Generic RSS feed scraper.

    Subclasses set SOURCE_NAME and SOURCE_URL.
    Override ``_filter_entry`` to drop irrelevant entries.
    """

    SOURCE_NAME: str = ""
    SOURCE_URL: str = ""

    def scrape(self) -> List[NewsEvent]:
        """Fetch and parse the RSS feed, returning enriched events."""
        try:
            feed = feedparser.parse(self.SOURCE_URL)
            if feed.bozo and not feed.entries:
                logger.warning("%s – feed parse error: %s", self.SOURCE_NAME, feed.bozo_exception)
                return []

            events: list[NewsEvent] = []
            for entry in feed.entries[:50]:  # cap per-source
                if not self._filter_entry(entry):
                    continue
                ev = self._entry_to_event(entry)
                if ev:
                    events.append(self._enrich(ev))

            logger.info("%s – %d entries parsed", self.SOURCE_NAME, len(events))
            return events

        except Exception as exc:
            logger.error("%s RSS scrape failed: %s", self.SOURCE_NAME, exc)
            return []

    # ------------------------------------------------------------------
    # Override in subclasses to filter irrelevant entries
    # ------------------------------------------------------------------

    def _filter_entry(self, entry) -> bool:
        """Return True if entry should be included. Default: include all."""
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _entry_to_event(self, entry) -> Optional[NewsEvent]:
        """Convert a feedparser entry dict into a NewsEvent."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        summary = entry.get("summary", "") or entry.get("description", "")
        # Strip HTML tags from summary
        import re
        summary = re.sub(r"<[^>]+>", " ", summary).strip()
        summary = re.sub(r"\s+", " ", summary)[:300]

        link = entry.get("link", "")

        # Parse timestamp
        timestamp = self._parse_timestamp(entry)

        # Get source config for the URL
        source_cfg = SOURCES_BY_NAME.get(self.SOURCE_NAME)
        source_url = source_cfg.url if source_cfg else link

        return NewsEvent(
            title=title,
            summary=summary,
            source_name=self.SOURCE_NAME,
            source_url=link or (source_cfg.url if source_cfg else ""),
            timestamp=timestamp,
        )

    def _parse_timestamp(self, entry) -> datetime:
        """Extract and parse timestamp from an RSS entry."""
        raw = entry.get("published") or entry.get("updated") or ""
        if raw:
            try:
                return dateparser.parse(raw)
            except (ValueError, TypeError):
                pass
        return datetime.now(timezone.utc)

    def _enrich(self, event: NewsEvent) -> NewsEvent:
        """Fill in event_type, severity, and geolocation if missing."""
        if event.event_type.value == "other":
            event.event_type = categorize_event(event.title, event.summary)
        if event.severity == 3:
            event.severity = estimate_severity(event.title, event.summary)

        if not event.has_location:
            text = f"{event.title} {event.summary}"
            loc = extract_primary_location(text)
            if loc:
                event.location_name = loc[0]
                event.latitude = loc[1]
                event.longitude = loc[2]

        if not event.source_name:
            event.source_name = self.SOURCE_NAME

        return event
