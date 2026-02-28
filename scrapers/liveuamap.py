"""
Liveuamap scraper.

Liveuamap is heavily JS-rendered and returns 403 for plain HTTP.
This scraper attempts two strategies:
 1. Try the API endpoint (ajax-based) that Liveuamap uses internally.
 2. Fallback: return empty (source can be revisited with playwright later).
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import List

import requests

from config.settings import REQUEST_TIMEOUT_SECONDS, USER_AGENTS
from models.events import NewsEvent
from scrapers.base import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)

# Liveuamap internal API patterns (may change)
_API_URL = "https://iran.liveuamap.com/ajax/do"


class LiveUAMapScraper(BaseScraper):
    SOURCE_NAME = "Liveuamap"
    SOURCE_URL = "https://iran.liveuamap.com/"

    def scrape(self) -> List[NewsEvent]:
        """Override scrape to attempt API first, then fallback."""
        try:
            events = self._try_api()
            if events:
                return [self._enrich(ev) for ev in events]
        except Exception as exc:
            logger.debug("Liveuamap API attempt failed: %s", exc)

        # Fallback: standard scrape (likely returns empty due to 403)
        return super().scrape()

    def parse(self, html: str) -> List[NewsEvent]:
        """Parse HTML fallback — usually blocked, returns empty."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        events: List[NewsEvent] = []

        entries = soup.select(".event, [class*='event-title']")
        for entry in entries[:50]:
            title = entry.get_text(strip=True)
            if not title:
                continue

            events.append(
                NewsEvent(
                    title=title[:200],
                    source_name=self.SOURCE_NAME,
                    source_url=self.SOURCE_URL,
                    timestamp=datetime.now(timezone.utc),
                    raw_text=title,
                )
            )

        return events

    def _try_api(self) -> List[NewsEvent]:
        """
        Attempt Liveuamap's internal AJAX endpoint.
        This may or may not work depending on their current anti-bot setup.
        """
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.SOURCE_URL,
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        try:
            resp = requests.get(
                _API_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
                params={"act": "do", "lang": "en"},
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError):
            return []

        events: List[NewsEvent] = []
        items = data if isinstance(data, list) else data.get("events", [])

        for item in items[:50]:
            if isinstance(item, dict):
                title = item.get("title", "") or item.get("description", "")
                lat = item.get("lat")
                lon = item.get("lng") or item.get("lon")
                ts = item.get("time") or item.get("date")

                timestamp = datetime.now(timezone.utc)
                if ts:
                    try:
                        timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                if title:
                    events.append(
                        NewsEvent(
                            title=title[:200],
                            source_name=self.SOURCE_NAME,
                            source_url=self.SOURCE_URL,
                            timestamp=timestamp,
                            latitude=float(lat) if lat else None,
                            longitude=float(lon) if lon else None,
                            raw_text=title,
                        )
                    )

        return events
