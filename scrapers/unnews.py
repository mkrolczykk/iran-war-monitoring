"""UN News RSS scraper – Middle East region feed."""

from scrapers.rss_base import RSSBaseScraper


class UNNewsRSSScraper(RSSBaseScraper):
    SOURCE_NAME = "UN News"
    SOURCE_URL = "https://news.un.org/feed/subscribe/en/news/region/middle-east/feed/rss.xml"

    # No filter – feed is already Middle East-specific
