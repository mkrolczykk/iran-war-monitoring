# 🌍 Iran Crisis Monitor

Real-time monitoring dashboard that aggregates live news from 7 major international sources and presents events on an interactive dark-themed map with a live news feed.

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- **Interactive dark-themed map** – powered by Folium with CartoDB Dark Matter tiles
- **7 live news sources** – Al Jazeera, Reuters, NBC News, Washington Post, CNN, AP News, Liveuamap
- **Colour-coded markers** – airstrikes (red), missiles (purple), explosions (orange), alerts (yellow), military (blue)
- **Live news feed** – scrollable panel with source badges, severity indicators, and relative timestamps
- **Auto-refresh** – fetches new data every ~60 seconds
- **Responsive design** – works on desktop and mobile browsers
- **Modular architecture** – easily add new sources or extend processing

## 🚀 Quick Start

### Prerequisites

- **Python 3.11.9** (recommended)
- `pip` package manager

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd iran-war-monitoring

# 2. Create and activate virtual environment
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at **<http://localhost:8501>**.

## 🏗️ Project Structure

```
iran-war-monitoring/
├── app.py                    # Streamlit entry point
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .streamlit/config.toml    # Streamlit theme & server config
│
├── config/
│   ├── settings.py           # Source registry, timing, map defaults
│   └── locations.py          # ~120 curated Middle East locations
│
├── models/
│   └── events.py             # NewsEvent model + EventStore
│
├── scrapers/
│   ├── base.py               # Abstract scraper with HTTP retry & caching
│   ├── aljazeera.py          # Al Jazeera live blog
│   ├── apnews.py             # AP News live updates
│   ├── reuters.py            # Reuters live
│   ├── nbcnews.py            # NBC News live blog
│   ├── washpost.py           # Washington Post live updates
│   ├── cnn.py                # CNN live updates
│   └── liveuamap.py          # Liveuamap (API + HTML fallback)
│
├── processing/
│   ├── geocoder.py           # Location extraction from text
│   ├── categorizer.py        # Event type classification
│   └── deduplicator.py       # Cross-source deduplication
│
├── ui/
│   ├── map_component.py      # Folium map builder
│   ├── news_feed.py          # News feed HTML renderer
│   └── styles.py             # Custom CSS (dark theme, responsive)
│
└── utils/
    ├── cache.py              # TTL response cache
    └── logger.py             # Logging setup
```

## ☁️ Deploy to Streamlit Community Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repository
4. Set:
   - **Main file path**: `app.py`
   - **Python version**: `3.11`
5. Click **Deploy**

No secrets or environment variables are required.

## 🔧 Configuration

Edit `config/settings.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `REFRESH_INTERVAL_SECONDS` | `60` | How often to fetch new data |
| `REQUEST_TIMEOUT_SECONDS` | `15` | HTTP timeout per source |
| `MAX_NEWS_FEED_ITEMS` | `100` | Max events in the feed panel |
| `EVENT_RECENT_MINUTES` | `10` | Highlight events newer than this |
| `MAP_DEFAULT_ZOOM` | `5` | Initial map zoom level |

## ➕ Adding a New Source

1. Create `scrapers/mysource.py` extending `BaseScraper`
2. Implement the `parse(html)` method
3. Add a `SourceConfig` entry in `config/settings.py`
4. Import and register in `scrapers/__init__.py`

## ➕ Adding a New Location

Edit `config/locations.py` and add an entry:

```python
"new city": (latitude, longitude),
```

The geocoder will automatically detect this name in news text.

## 📄 License

MIT – see individual source copyrights for news content.
