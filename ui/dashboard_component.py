"""
Unified dashboard component: map + news feed in a SINGLE HTML page.

By rendering both in one DOM (instead of separate iframes), we get:
- Hover on a news card → highlight the corresponding marker on the map
- MarkerCluster with spiderfy for overlapping markers
- Consistent height between map and feed
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import List

from config.settings import (
    MAP_DEFAULT_CENTER,
    MAP_DEFAULT_ZOOM,
    MAX_NEWS_FEED_ITEMS,
    EVENT_RECENT_MINUTES,
    SOURCES_BY_NAME,
)
from models.events import NewsEvent, EVENT_TYPE_CONFIG
from ui.styles import get_custom_css
import re

# CSS colours for event types
_CSS_COLORS = {
    "red": "#e74c3c", "orange": "#e67e22", "yellow": "#f1c40f",
    "blue": "#3498db", "purple": "#9b59b6", "pink": "#e91e63",
    "gray": "#95a5a6", "white": "#bdc3c7",
}

# External-link SVG icon
_EXT_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/>'
    '<line x1="10" y1="14" x2="21" y2="3"/>'
    '</svg>'
)


def build_dashboard_html(
    all_events: List[NewsEvent],
    geo_events: List[NewsEvent],
    component_height: int = 750,
) -> str:
    """
    Build a complete HTML page with Leaflet map + news feed side by side.

    Returns an HTML string ready for ``streamlit.components.v1.html()``.
    """
    now = datetime.now(timezone.utc)
    feed_items = all_events[:MAX_NEWS_FEED_ITEMS]

    # Build marker data as JSON for Leaflet
    markers_json = json.dumps([
        {
            "id": ev.id,
            "lat": ev.latitude,
            "lng": ev.longitude,
            "title": _esc(ev.title),
            "type_label": ev.display_config["label"],
            "color": _CSS_COLORS.get(ev.display_config["color"], "#95a5a6"),
            "source": ev.source_name,
            "age": _format_age(ev.age_minutes(now)),
            "summary": _esc((ev.summary or "")[:150]),
            "source_url": ev.source_url or "",
            "location": ev.location_name or "",
        }
        for ev in geo_events
    ], ensure_ascii=False)

    # Build feed cards HTML
    cards_html = "\n".join(_render_card(ev, now) for ev in feed_items)

    # Stats chips
    stats_html = _render_stats(all_events)

    css = get_custom_css()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
{css}
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        background: #0e1117;
        color: #fafafa;
        font-family: 'Inter', -apple-system, sans-serif;
        overflow: hidden;
    }}
    .dashboard {{
        display: flex;
        height: {component_height}px;
        gap: 12px;
    }}
    .map-panel {{
        flex: 7;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }}
    #map {{
        width: 100%;
        height: 100%;
    }}
    .feed-panel {{
        flex: 3;
        display: flex;
        flex-direction: column;
        min-width: 0;
    }}
    .news-feed-container {{
        flex: 1;
        overflow-y: auto;
        padding-right: 4px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.15) transparent;
    }}
    .news-feed-container::-webkit-scrollbar {{ width: 4px; }}
    .news-feed-container::-webkit-scrollbar-track {{ background: transparent; }}
    .news-feed-container::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.15);
        border-radius: 10px;
    }}
    /* Override MarkerCluster dark-theme */
    .marker-cluster {{
        background: rgba(231,76,60,0.3) !important;
    }}
    .marker-cluster div {{
        background: rgba(231,76,60,0.6) !important;
        color: #fff !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }}
    .leaflet-popup-content-wrapper {{
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .leaflet-popup-content {{
        margin: 10px 12px !important;
    }}
    /* Highlight animation */
    @keyframes markerPulse {{
        0% {{ transform: scale(1); opacity: 0.7; }}
        50% {{ transform: scale(1.4); opacity: 0.3; }}
        100% {{ transform: scale(1); opacity: 0.7; }}
    }}
    .marker-highlight {{
        animation: markerPulse 1s infinite;
    }}
    /* Card hover → cursor pointer for geo-enabled cards */
    .news-card[data-lat] {{
        cursor: pointer;
    }}
    .news-card[data-lat]:hover {{
        border-color: rgba(231,76,60,0.4);
        background: rgba(231,76,60,0.06);
    }}
</style>
</head>
<body>
<div class="dashboard">
    <div class="map-panel">
        <div id="map"></div>
    </div>
    <div class="feed-panel">
        <div class="feed-header">
            NEWS LIVE &nbsp;
            <span style="font-weight:400;opacity:0.5;">
                {now.strftime('%d/%m/%Y %H:%M:%S')} UTC
            </span>
        </div>
        <div class="news-feed-container">
            {cards_html if cards_html else _empty_state()}
        </div>
    </div>
</div>

<script>
(function() {{
    // ── Map ──────────────────────────────────────────────────────
    var map = L.map('map', {{
        center: [{MAP_DEFAULT_CENTER[0]}, {MAP_DEFAULT_CENTER[1]}],
        zoom: {MAP_DEFAULT_ZOOM},
        minZoom: 3,
        maxZoom: 18,
        zoomControl: true,
    }});

    // Dark tiles
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
    }}).addTo(map);

    // ── Markers with clustering ──────────────────────────────────
    var cluster = L.markerClusterGroup({{
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        maxClusterRadius: 35,
        disableClusteringAtZoom: 10,
        spiderfyDistanceMultiplier: 1.5,
    }});

    var markersData = {markers_json};
    var markerLookup = {{}};

    markersData.forEach(function(d) {{
        var marker = L.circleMarker([d.lat, d.lng], {{
            radius: 7,
            fillColor: d.color,
            color: '#222',
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.9,
        }});

        var popupHtml =
            '<div style="font-family:Inter,sans-serif;max-width:280px;">' +
            '<div style="display:flex;align-items:center;gap:5px;margin-bottom:5px;">' +
            '<span style="background:' + d.color + ';color:#fff;font-size:9px;font-weight:700;' +
            'padding:2px 5px;border-radius:3px;letter-spacing:0.05em;">' +
            d.type_label.toUpperCase() + '</span>' +
            '<span style="font-size:10px;color:#888;">' + d.age + '</span>' +
            '</div>' +
            '<div style="font-size:13px;font-weight:600;color:#222;margin-bottom:4px;line-height:1.3;">' +
            d.title + '</div>' +
            (d.summary ? '<div style="font-size:11px;color:#555;margin-bottom:4px;">' + d.summary + '</div>' : '') +
            '<div style="display:flex;justify-content:space-between;align-items:center;' +
            'padding-top:4px;border-top:1px solid #ddd;font-size:10px;color:#888;">' +
            '<span>' + d.location + ' &middot; ' + d.source + '</span>' +
            (d.source_url ? '<a href="' + d.source_url + '" target="_blank" ' +
            'style="color:#4da6ff;text-decoration:none;">' + d.source + ' &nearr;</a>' : '') +
            '</div></div>';

        marker.bindPopup(popupHtml, {{ maxWidth: 300 }});
        markerLookup[d.id] = {{ marker: marker, lat: d.lat, lng: d.lng, color: d.color }};
        cluster.addLayer(marker);
    }});

    map.addLayer(cluster);

    // ── Hover interaction: feed card → map marker ────────────────
    var highlightCircle = null;

    function highlightMarker(eventId) {{
        clearHighlight();
        var info = markerLookup[eventId];
        if (!info) return;

        highlightCircle = L.circleMarker([info.lat, info.lng], {{
            radius: 22,
            color: info.color,
            fillColor: info.color,
            fillOpacity: 0.2,
            weight: 2.5,
            className: 'marker-highlight',
        }}).addTo(map);

        // Open popup and pan
        info.marker.openPopup();
    }}

    function clearHighlight() {{
        if (highlightCircle) {{
            map.removeLayer(highlightCircle);
            highlightCircle = null;
        }}
        map.closePopup();
    }}

    // Attach to feed cards
    document.querySelectorAll('.news-card[data-event-id]').forEach(function(card) {{
        card.addEventListener('mouseenter', function() {{
            highlightMarker(this.dataset.eventId);
        }});
        card.addEventListener('mouseleave', function() {{
            clearHighlight();
        }});
        // Click → pan to marker
        card.addEventListener('click', function() {{
            var info = markerLookup[this.dataset.eventId];
            if (info) {{
                map.setView([info.lat, info.lng], 8, {{ animate: true }});
                highlightMarker(this.dataset.eventId);
            }}
        }});
    }});

    // Force map resize after render
    setTimeout(function() {{ map.invalidateSize(); }}, 100);
}})();
</script>
</body>
</html>"""


# ── Card renderer ─────────────────────────────────────────────────────────

def _render_card(event: NewsEvent, now: datetime) -> str:
    """Render a single news card with data attributes for map interaction."""
    cfg = event.display_config
    age_min = event.age_minutes(now)
    is_recent = age_min < EVENT_RECENT_MINUTES
    recent_class = " recent" if is_recent else ""

    type_color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
    type_indicator = (
        f'<span class="type-indicator" '
        f'style="background:rgba({_hex_to_rgb(type_color)},0.15);'
        f'color:{type_color};">{cfg["label"]}</span>'
    )

    time_str = _format_age(age_min)

    badge_class = _source_badge_class(event.source_name)
    severity_html = _severity_dots(event.severity)

    location_html = ""
    if event.location_name:
        location_html = f'<div class="location-tag">{event.location_name}</div>'

    # Source link → article URL
    article_url = event.source_url or ""
    source_link = ""
    if article_url:
        source_link = (
            f'<a href="{article_url}" target="_blank" rel="noopener" '
            f'class="source-link" onclick="event.stopPropagation();">'
            f'{_EXT_ICON_SVG} Source</a>'
        )

    # Data attributes for map interaction (only for geolocated events)
    data_attrs = ""
    if event.has_location:
        data_attrs = (
            f'data-event-id="{event.id}" '
            f'data-lat="{event.latitude}" '
            f'data-lng="{event.longitude}"'
        )

    return f"""
    <div class="news-card{recent_class}" {data_attrs}>
        <div class="news-card-header">
            <div class="news-card-meta">
                {type_indicator}
                <span class="time-ago">{time_str}</span>
            </div>
            {source_link}
        </div>
        <p class="news-card-title">{_esc(event.title)}</p>
        {location_html}
        <div class="news-card-footer">
            <span class="source-badge {badge_class}">{event.source_name}</span>
            {severity_html}
        </div>
    </div>
    """


def _render_stats(events: List[NewsEvent]) -> str:
    """Render stats bar (used in app.py, not in the component)."""
    from collections import Counter
    counts: Counter = Counter()
    for ev in events:
        counts[ev.event_type] += 1

    chips = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        c = counts.get(etype, 0)
        if c > 0:
            type_color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
            chips.append(
                f'<span class="stat-chip">'
                f'<span class="stat-dot" style="background:{type_color};"></span>'
                f'{cfg["label"]} <span class="count">{c}</span>'
                f'</span>'
            )
    return f'<div class="stats-bar">{"".join(chips)}</div>'


# ── Helpers ───────────────────────────────────────────────────────────────

def _source_badge_class(source_name: str) -> str:
    key = re.sub(r"[^a-z]", "", source_name.lower())
    mapping = {
        "aljazeera": "source-aljazeera",
        "apnews": "source-apnews",
        "reuters": "source-reuters",
        "jerusalempost": "source-jerusalempost",
        "unnews": "source-unnews",
        "bbcnews": "source-bbcnews",
        "cnn": "source-cnn",
        "liveuamap": "source-liveuamap",
        "npr": "source-npr",
    }
    return mapping.get(key, "source-default")


def _severity_dots(severity: int) -> str:
    dots = []
    for i in range(1, 6):
        sev_class = f"sev-{severity}" if severity <= 3 else ""
        active = " active " + sev_class if i <= severity else ""
        dots.append(f'<span class="severity-dot{active}"></span>')
    return f'<span class="severity-bar">{"".join(dots)}</span>'


def _format_age(minutes: float) -> str:
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{int(minutes)} min ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _empty_state() -> str:
    return """
    <div style="text-align:center;padding:2rem;opacity:0.4;">
        <div style="font-size:1.2rem;margin-bottom:0.5rem;font-weight:600;">
            MONITORING
        </div>
        <div style="font-size:0.8rem;">Fetching latest updates...</div>
    </div>
    """
