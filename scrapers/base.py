"""
Abstract base class for all news scrapers.

Provides HTTP fetching with retry, User-Agent rotation,
timeout, response caching, and graceful error handling.
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import requests

from config.settings import (
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENTS,
)
from models.events import NewsEvent
from processing.categorizer import categorize_event, estimate_severity
from processing.geocoder import extract_primary_location
from utils.cache import TTLCache
from utils.logger import get_logger

_response_cache = TTLCache(ttl=55)
logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Base class that every source scraper inherits from.

    Subclasses only need to implement:
      • ``SOURCE_NAME``  – human-readable name
      • ``SOURCE_URL``   – the URL to scrape
      • ``parse(html)``  – extract events from raw HTML
    """

    SOURCE_NAME: str = ""
    SOURCE_URL: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self) -> List[NewsEvent]:
        """
        Full scrape cycle: fetch → parse → enrich → return.
        Never raises – returns empty list on failure.
        """
        try:
            html = self._fetch()
            if not html:
                return []
            events = self.parse(html)
            return [self._enrich(ev) for ev in events]
        except Exception as exc:
            logger.error("Scraper %s failed: %s", self.SOURCE_NAME, exc)
            return []

    # ------------------------------------------------------------------
    # To be implemented by subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def parse(self, html: str) -> List[NewsEvent]:
        """Parse raw HTML and return a list of NewsEvent objects."""
        ...

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fetch(self) -> Optional[str]:
        """HTTP GET with retry, caching, and User-Agent rotation."""
        cached = _response_cache.get(self.SOURCE_URL)
        if cached is not None:
            return cached

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    self.SOURCE_URL,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                _response_cache.set(self.SOURCE_URL, resp.text)
                return resp.text
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                logger.warning(
                    "%s – attempt %d/%d failed: %s",
                    self.SOURCE_NAME, attempt, MAX_RETRIES, exc,
                )
                # Don't retry on permanent rejections (401/403)
                if status in (401, 403):
                    break
                time.sleep(0.5)
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "%s – attempt %d/%d failed: %s",
                    self.SOURCE_NAME, attempt, MAX_RETRIES, exc,
                )
                time.sleep(0.5)

        logger.error("%s – all attempts exhausted: %s", self.SOURCE_NAME, last_error)
        return None

    def _enrich(self, event: NewsEvent) -> NewsEvent:
        """Fill in event_type, severity, and geolocation if missing."""
        # Auto-classify
        if event.event_type.value == "other":
            event.event_type = categorize_event(event.title, event.summary)
        if event.severity == 3:
            event.severity = estimate_severity(event.title, event.summary)

        # Auto-geolocate
        if not event.has_location:
            text = f"{event.title} {event.summary}"
            loc = extract_primary_location(text)
            if loc:
                event.location_name = loc[0]
                event.latitude = loc[1]
                event.longitude = loc[2]

        # Ensure source is set
        if not event.source_name:
            event.source_name = self.SOURCE_NAME

        return event
