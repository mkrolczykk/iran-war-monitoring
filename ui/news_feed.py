"""
News feed panel renderer.

Generates the HTML for the scrollable news feed sidebar with
source badges, timestamps, severity indicators, and source links.
All content is professional/text-based (no emoji).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List

from config.settings import MAX_NEWS_FEED_ITEMS, EVENT_RECENT_MINUTES, SOURCES_BY_NAME
from models.events import NewsEvent

# CSS colour values for event-type indicator badges
_TYPE_COLORS = {
    "red": "#e74c3c",
    "orange": "#e67e22",
    "yellow": "#f1c40f",
    "blue": "#3498db",
    "purple": "#9b59b6",
    "pink": "#e91e63",
    "gray": "#95a5a6",
    "white": "#bdc3c7",
}


def render_news_feed(events: List[NewsEvent]) -> str:
    """
    Return full HTML for the news feed panel.

    Parameters
    ----------
    events : list[NewsEvent]
        Should already be sorted newest-first.
    """
    now = datetime.now(timezone.utc)
    items = events[:MAX_NEWS_FEED_ITEMS]

    cards_html = "\n".join(_render_card(ev, now) for ev in items)

    return f"""
    <div class="feed-header">
        NEWS LIVE &nbsp;
        <span style="font-weight:400;opacity:0.5;">
            Updated {now.strftime('%d/%m/%Y %H:%M:%S')} UTC
        </span>
    </div>
    <div class="news-feed-container">
        {cards_html if cards_html else _empty_state()}
    </div>
    """


def _render_card(event: NewsEvent, now: datetime) -> str:
    """Render a single news card."""
    cfg = event.display_config
    age_min = event.age_minutes(now)
    is_recent = age_min < EVENT_RECENT_MINUTES
    recent_class = " recent" if is_recent else ""

    # Source badge CSS class
    badge_class = _source_badge_class(event.source_name)

    # Time display
    time_str = _format_age(age_min)

    # Severity dots
    severity_html = _severity_dots(event.severity)

    # Event type indicator badge (coloured text label, no emoji)
    type_color = _TYPE_COLORS.get(cfg["color"], "#95a5a6")
    type_indicator = (
        f'<span class="type-indicator" style="background:rgba({_hex_to_rgb(type_color)},0.15);'
        f'color:{type_color};">{cfg["label"]}</span>'
    )

    # Location
    location_html = ""
    if event.location_name:
        location_html = f'<div class="location-tag">{event.location_name}</div>'

    # Source link – always points to the main live blog URL for this source
    source_cfg = SOURCES_BY_NAME.get(event.source_name)
    original_url = source_cfg.url if source_cfg else event.source_url
    # For RSS feeds, use the entry link (actual article) not the feed URL
    article_url = event.source_url if event.source_url else (original_url or "")
    source_link = ""
    if article_url:
        # SVG external-link icon matching user's reference design
        ext_icon = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2.5" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
            '<polyline points="15 3 21 3 21 9"/>'
            '<line x1="10" y1="14" x2="21" y2="3"/>'
            '</svg>'
        )
        source_link = (
            f'<a href="{article_url}" target="_blank" rel="noopener" '
            f'class="source-link">{ext_icon} Source</a>'
        )

    return f"""
    <div class="news-card{recent_class}">
        <div class="news-card-header">
            <div class="news-card-meta">
                {type_indicator}
                <span class="time-ago">{time_str}</span>
            </div>
            {source_link}
        </div>
        <p class="news-card-title">{_escape(event.title)}</p>
        {location_html}
        <div class="news-card-footer">
            <span class="source-badge {badge_class}">{event.source_name}</span>
            {severity_html}
        </div>
    </div>
    """


def render_stats_bar(events: List[NewsEvent]) -> str:
    """Render a compact stats bar showing event type counts."""
    from collections import Counter
    from models.events import EVENT_TYPE_CONFIG

    counts: Counter = Counter()
    for ev in events:
        counts[ev.event_type] += 1

    chips = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        c = counts.get(etype, 0)
        if c > 0:
            type_color = _TYPE_COLORS.get(cfg["color"], "#95a5a6")
            chips.append(
                f'<span class="stat-chip">'
                f'<span class="stat-dot" style="background:{type_color};"></span>'
                f'{cfg["label"]} <span class="count">{c}</span>'
                f'</span>'
            )

    return f'<div class="stats-bar">{"".join(chips)}</div>'


# ── Helpers ───────────────────────────────────────────────────────────────

def _source_badge_class(source_name: str) -> str:
    """Return CSS class for a source badge."""
    key = re.sub(r"[^a-z]", "", source_name.lower())
    mapping = {
        "aljazeera": "source-aljazeera",
        "apnews": "source-apnews",
        "reuters": "source-reuters",
        "jerusalempost": "source-jerusalempost",
        "unnews": "source-unnews",
        "bbcnews": "source-bbcnews",
        "npr": "source-npr",
    }
    return mapping.get(key, "source-default")


def _severity_dots(severity: int) -> str:
    """Render 1-5 severity dots."""
    dots = []
    for i in range(1, 6):
        sev_class = f"sev-{severity}" if severity <= 3 else ""
        active = " active " + sev_class if i <= severity else ""
        dots.append(f'<span class="severity-dot{active}"></span>')
    return f'<span class="severity-bar">{"".join(dots)}</span>'


def _format_age(minutes: float) -> str:
    """Human-readable time ago string."""
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{int(minutes)} min ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex colour to 'r,g,b' string for CSS rgba()."""
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _empty_state() -> str:
    """Empty state placeholder."""
    return """
    <div style="text-align:center;padding:2rem;opacity:0.4;">
        <div style="font-size:1.2rem;margin-bottom:0.5rem;font-weight:600;">
            MONITORING
        </div>
        <div style="font-size:0.8rem;">
            Fetching latest updates from sources...
        </div>
        <div style="font-size:0.7rem;margin-top:0.25rem;opacity:0.6;">
            First results will appear shortly.
        </div>
    </div>
    """


def _escape(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
