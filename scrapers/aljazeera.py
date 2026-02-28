"""Al Jazeera RSS scraper – all news feed."""

from scrapers.rss_base import RSSBaseScraper

# Keywords that indicate Iran/Israel/Middle East crisis relevance
_CRISIS_KEYWORDS = [
    "iran", "israel", "tehran", "idf", "hamas", "hezbollah", "gaza",
    "strike", "missile", "airstrike", "bomb", "attack", "military",
    "nuclear", "irgc", "pentagon", "jerusalem", "netanyahu", "khamenei",
    "middle east", "war", "conflict", "ceasefire", "escalat",
]


class AlJazeeraRSSScraper(RSSBaseScraper):
    SOURCE_NAME = "Al Jazeera"
    SOURCE_URL = "https://www.aljazeera.com/xml/rss/all.xml"

    def _filter_entry(self, entry) -> bool:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        return any(kw in text for kw in _CRISIS_KEYWORDS)
