# Sources Registry

Live tracking of all data sources used by the Iran Crisis Monitor.

## Active Sources

| # | Source | Type | URL | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Al Jazeera | RSS | `aljazeera.com/xml/rss/all.xml` | ✅ Active | Keyword-filtered for crisis content |
| 2 | AP News | RSS | `apnews.com/hub/world-news?format=rss` | ✅ Active | Keyword-filtered |
| 3 | Reuters | RSS | `reuters.com/arc/outboundfeeds/world/?outputType=xml` | ✅ Active | Keyword-filtered |
| 4 | Jerusalem Post | RSS | `jpost.com/rss/rssfeedsiran` | ✅ Active | Iran-specific, no filter needed |
| 5 | UN News | RSS | `news.un.org/.../middle-east/feed/rss.xml` | ✅ Active | Middle East region, no filter |
| 6 | BBC News | RSS | `feeds.bbci.co.uk/news/world/rss.xml` | ✅ Active | Keyword-filtered |
| 7 | CNN | HTML scrape | `cnn.com/world/live-news/israel-iran-attack-...` | ✅ Active | BeautifulSoup live blog parser |
| 8 | NPR | RSS | `feeds.npr.org/1004/rss.xml` | ✅ Active | Keyword-filtered |

## Removed Sources

| Source | Reason | Date |
| --- | --- | --- |
| Liveuamap | Requested by user | 2026-02-28 |
| NBC News (live blog) | HTML scraper returned 0 events, JS-rendered content | 2026-02-28 |
| The Washington Post (live blog) | Persistent read timeout (>15s per attempt) | 2026-02-28 |

## Filter Keywords

RSS sources are filtered using these crisis-related keywords:
`iran`, `israel`, `tehran`, `idf`, `hamas`, `hezbollah`, `gaza`, `strike`, `missile`, `airstrike`, `bomb`, `attack`, `military`, `nuclear`, `irgc`, `pentagon`, `jerusalem`, `netanyahu`, `khamenei`, `middle east`, `war`, `conflict`, `ceasefire`, `escalat`
