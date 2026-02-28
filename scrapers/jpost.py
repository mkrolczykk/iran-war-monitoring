"""Jerusalem Post RSS scraper – Iran-specific feed."""

from scrapers.rss_base import RSSBaseScraper


class JPostRSSScraper(RSSBaseScraper):
    SOURCE_NAME = "Jerusalem Post"
    SOURCE_URL = "https://www.jpost.com/rss/rssfeedsiran"

    # No filter – this feed is already Iran-specific
