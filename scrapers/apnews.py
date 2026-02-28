"""AP News RSS scraper – world news feed."""

from scrapers.rss_base import RSSBaseScraper

_CRISIS_KEYWORDS = [
    "iran", "israel", "tehran", "idf", "hamas", "hezbollah", "gaza",
    "strike", "missile", "airstrike", "bomb", "attack", "military",
    "nuclear", "irgc", "pentagon", "jerusalem", "netanyahu", "khamenei",
    "middle east", "war", "conflict", "ceasefire", "escalat",
]


class APNewsRSSScraper(RSSBaseScraper):
    SOURCE_NAME = "AP News"
    SOURCE_URL = "https://apnews.com/hub/world-news?format=rss"

    def _filter_entry(self, entry) -> bool:
        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        return any(kw in text for kw in _CRISIS_KEYWORDS)
