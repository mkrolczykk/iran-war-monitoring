"""Reuters RSS scraper – world news feed."""

from scrapers.rss_base import RSSBaseScraper

_CRISIS_KEYWORDS = [
    "iran", "israel", "tehran", "idf", "hamas", "hezbollah", "gaza",
    "strike", "missile", "airstrike", "bomb", "attack", "military",
    "nuclear", "irgc", "pentagon", "jerusalem", "netanyahu", "khamenei",
    "middle east", "war", "conflict", "ceasefire", "escalat",
]


class ReutersRSSScraper(RSSBaseScraper):
    SOURCE_NAME = "Reuters"
    SOURCE_URL = "https://www.reuters.com/arc/outboundfeeds/world/?outputType=xml"

    def _filter_entry(self, entry) -> bool:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        return any(kw in text for kw in _CRISIS_KEYWORDS)
