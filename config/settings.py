"""
Application settings and constants.
Central configuration for all modules – source URLs, refresh intervals, map defaults.
"""

from dataclasses import dataclass
from typing import Dict, List


# ---------------------------------------------------------------------------
# Source configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceConfig:
    """Configuration for a single news source."""
    name: str
    short_name: str
    url: str                    # feed URL (RSS or HTML scrape target)
    website_url: str            # public-facing website for attribution links
    color: str                  # badge colour (hex)
    source_type: str = "rss"    # "rss" or "html"
    enabled: bool = True


SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="Al Jazeera",
        short_name="AJ",
        url="https://www.aljazeera.com/xml/rss/all.xml",
        website_url="https://www.aljazeera.com",
        color="#fa9f1c",
        source_type="rss",
    ),
    SourceConfig(
        name="AP News",
        short_name="AP",
        url="https://apnews.com/hub/world-news?format=rss",
        website_url="https://apnews.com",
        color="#ee3024",
        source_type="rss",
        enabled=False,
    ),
    SourceConfig(
        name="Reuters",
        short_name="REU",
        url="https://www.reuters.com/arc/outboundfeeds/world/?outputType=xml",
        website_url="https://www.reuters.com",
        color="#ff8000",
        source_type="rss",
        enabled=False,
    ),
    SourceConfig(
        name="Jerusalem Post",
        short_name="JPOST",
        url="https://www.jpost.com/rss/rssfeedsiran",
        website_url="https://www.jpost.com",
        color="#003b6f",
        source_type="rss",
    ),
    SourceConfig(
        name="UN News",
        short_name="UN",
        url="https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml",
        website_url="https://news.un.org",
        color="#009edb",
        source_type="rss",
        enabled=False,
    ),
    SourceConfig(
        name="BBC News",
        short_name="BBC",
        url="http://feeds.bbci.co.uk/news/world/rss.xml",
        website_url="https://www.bbc.com/news",
        color="#bb1919",
        source_type="rss",
    ),
    SourceConfig(
        name="CNN",
        short_name="CNN",
        url="https://www.cnn.com/world/live-news/israel-iran-attack-02-28-26-hnk-intl",
        website_url="https://www.cnn.com",
        color="#cc0000",
        source_type="html",
    ),
    SourceConfig(
        name="NPR",
        short_name="NPR",
        url="https://feeds.npr.org/1004/rss.xml",
        website_url="https://www.npr.org",
        color="#1a1a2e",
        source_type="rss",
    ),
]

SOURCES_BY_NAME: Dict[str, SourceConfig] = {s.name: s for s in SOURCES}

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

REFRESH_INTERVAL_SECONDS: int = 60          # auto-refresh every N seconds
REQUEST_TIMEOUT_SECONDS: int = 15           # HTTP request timeout
MAX_RETRIES: int = 2                        # per-source retry count

# ---------------------------------------------------------------------------
# Map defaults
# ---------------------------------------------------------------------------

MAP_DEFAULT_CENTER: tuple = (32.0, 50.0)    # roughly centre of Iran / ME region
MAP_DEFAULT_ZOOM: int = 5
MAP_TILE_PROVIDER: str = "CartoDB dark_matter"

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

MAX_NEWS_FEED_ITEMS: int = 100              # max items shown in the feed
EVENT_RECENT_MINUTES: int = 10              # events younger than this get a pulse
APP_TITLE: str = "Iran Crisis News Scanner"

# ---------------------------------------------------------------------------
# User-Agent rotation pool (polite scraping)
# ---------------------------------------------------------------------------

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]
