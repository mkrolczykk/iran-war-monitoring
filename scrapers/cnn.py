"""
CNN live updates scraper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from bs4 import BeautifulSoup

from models.events import NewsEvent
from scrapers.base import BaseScraper


class CNNScraper(BaseScraper):
    SOURCE_NAME = "CNN"
    SOURCE_URL = (
        "https://www.cnn.com/world/live-news/"
        "israel-iran-attack-02-28-26-hnk-intl"
    )

    def parse(self, html: str) -> List[NewsEvent]:
        soup = BeautifulSoup(html, "lxml")
        events: List[NewsEvent] = []

        entries = soup.select(
            "[class*='live-story'], "
            "[data-type='live-story'], "
            "[class*='LiveStory'], "
            "article[class*='live']"
        )

        if not entries:
            entries = soup.find_all("article")

        for entry in entries[:50]:
            title_el = entry.find(["h2", "h3", "h4"])
            title = title_el.get_text(strip=True) if title_el else ""

            paragraphs = entry.find_all("p")
            summary = " ".join(p.get_text(strip=True) for p in paragraphs[:3])

            if not title and not summary:
                continue
            if not title:
                title = summary[:120] + ("…" if len(summary) > 120 else "")

            time_el = entry.find("time")
            timestamp = datetime.now(timezone.utc)
            if time_el:
                dt_str = time_el.get("datetime", "")
                if dt_str:
                    try:
                        timestamp = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

            link = ""
            a_tag = entry.find("a", href=True)
            if a_tag:
                href = a_tag["href"]
                link = href if href.startswith("http") else f"https://www.cnn.com{href}"

            events.append(
                NewsEvent(
                    title=title,
                    summary=summary[:500],
                    source_name=self.SOURCE_NAME,
                    source_url=link or self.SOURCE_URL,
                    timestamp=timestamp,
                    raw_text=f"{title} {summary}",
                )
            )

        return events
