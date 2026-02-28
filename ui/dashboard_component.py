"""
Unified dashboard component: map + news feed in a SINGLE HTML page.

Features:
- Pin markers with event-type SVG icons (bomber, bomb, rocket, etc.)
- Natural offset for same-city markers (no clustering)
- Hover on news card → center map on marker + highlight + popup
- Map state preserved across fragment refreshes via sessionStorage
- Only events from last 8h shown on map; all events in the feed
- Mini pin icon in sidebar card type badges matching map pins 1:1
"""

from __future__ import annotations

import html
import json
import math
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

# Maximum age (hours) for events shown on the map
MAP_MAX_AGE_HOURS = 8

# ─── SVG icon paths ──────────────────────────────────────────────────────
# Each is rendered inside a 24x24 viewBox, white fill/stroke on colored bg.
# Designed to be *instantly* recognizable at pin size (16x16px rendered).

_TYPE_ICONS = {
    # Bomber/jet silhouette — airstrike
    "Airstrike": (
        '<path d="M12 4L10 8L3 10L5 12L3 14L10 13L12 20L14 13L21 14L19 12'
        'L21 10L14 8L12 4Z" fill="white"/>'
    ),
    # Rocket — missile
    "Missile": (
        '<path d="M12 2C12 2 15 6 15 10L17 13L15 14L13 20L12 22L11 20L9 14'
        'L7 13L9 10C9 6 12 2 12 2Z" fill="white"/>'
        '<circle cx="12" cy="10" r="1.5" fill="none" stroke="currentColor" stroke-width="0.8"/>'
    ),
    # Round bomb with fuse spark — explosion
    "Explosion": (
        '<circle cx="12" cy="13" r="7" fill="white"/>'
        '<line x1="15" y1="6" x2="17" y2="3" stroke="white" stroke-width="2" stroke-linecap="round"/>'
        '<circle cx="18" cy="2.5" r="1.5" fill="#FFD700"/>'
        '<line x1="17" y1="1" x2="19" y2="0" stroke="#FFD700" stroke-width="1"/>'
        '<line x1="19.5" y1="2" x2="21" y2="1.5" stroke="#FFD700" stroke-width="1"/>'
        '<line x1="18.5" y1="4" x2="20" y2="4.5" stroke="#FFD700" stroke-width="1"/>'
    ),
    # Warning triangle — alert
    "Alert": (
        '<path d="M12 3L2 21H22L12 3Z" fill="white"/>'
        '<line x1="12" y1="10" x2="12" y2="15" stroke="currentColor" stroke-width="2.5" '
        'stroke-linecap="round"/>'
        '<circle cx="12" cy="18" r="1.2" fill="currentColor"/>'
    ),
    # Shield with star — military
    "Military": (
        '<path d="M12 2L4 6V11C4 16.5 7.8 21.7 12 23C16.2 21.7 20 16.5 20 11V6L12 2Z" fill="white"/>'
        '<polygon points="12,8 13.2,11 16.5,11 13.8,13 14.8,16 12,14.2 9.2,16 '
        '10.2,13 7.5,11 10.8,11" fill="currentColor"/>'
    ),
    # Parliament building — political
    "Political": (
        '<path d="M12 2L3 8H21L12 2Z" fill="white"/>'
        '<rect x="5" y="9" width="2" height="9" fill="white" rx="0.5"/>'
        '<rect x="9" y="9" width="2" height="9" fill="white" rx="0.5"/>'
        '<rect x="13" y="9" width="2" height="9" fill="white" rx="0.5"/>'
        '<rect x="17" y="9" width="2" height="9" fill="white" rx="0.5"/>'
        '<rect x="3" y="18" width="18" height="2.5" fill="white" rx="0.5"/>'
    ),
    # Heart — humanitarian
    "Humanitarian": (
        '<path d="M12 21.35L10.55 20.03C5.4 15.36 2 12.28 2 8.5C2 5.42 4.42 3 '
        '7.5 3C9.24 3 10.91 3.81 12 5.09C13.09 3.81 14.76 3 16.5 3C19.58 3 '
        '22 5.42 22 8.5C22 12.28 18.6 15.36 13.45 20.04L12 21.35Z" fill="white"/>'
    ),
    # Info circle — other
    "Other": (
        '<circle cx="12" cy="12" r="9" fill="white"/>'
        '<line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" stroke-width="2.5" '
        'stroke-linecap="round"/>'
        '<circle cx="12" cy="8" r="1.3" fill="currentColor"/>'
    ),
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


def _mini_pin_svg(color: str, icon_svg: str, size: int = 18) -> str:
    """Generate a small inline SVG pin icon that matches the map markers exactly."""
    # Pin body height = 70% of total, tail = 30%
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{int(size*1.4)}" '
        f'viewBox="0 0 30 42" style="vertical-align:middle;flex-shrink:0;">'
        # Pin body (teardrop rotated)
        f'<g transform="translate(15,15)">'
        f'<g transform="rotate(-45)">'
        f'<rect x="-13" y="-13" width="26" height="26" rx="13" ry="13" fill="{color}" '
        f'stroke="rgba(255,255,255,0.7)" stroke-width="2"/>'
        f'<rect x="-13" y="0" width="13" height="13" fill="{color}"/>'
        f'</g></g>'
        # Icon inside (centered, unrotated)
        f'<g transform="translate(5,3) scale(0.83)">{icon_svg}</g>'
        # Tail dot
        f'<circle cx="15" cy="39" r="3" fill="{color}" opacity="0.3"/>'
        f'</svg>'
    )


def build_dashboard_html(
    all_events: List[NewsEvent],
    geo_events: List[NewsEvent],
    component_height: int = 750,
) -> str:
    """Build complete HTML page with Leaflet map + news feed side by side."""
    now = datetime.now(timezone.utc)
    feed_items = all_events[:MAX_NEWS_FEED_ITEMS]

    # Filter map events to last N hours only
    max_age_min = MAP_MAX_AGE_HOURS * 60
    recent_geo = [ev for ev in geo_events if ev.age_minutes(now) <= max_age_min]

    # Build marker data as JSON for Leaflet
    markers_json = json.dumps([
        {
            "id": ev.id,
            "lat": ev.latitude,
            "lng": ev.longitude,
            "title": _esc(ev.title),
            "type_label": ev.display_config["label"],
            "color": _CSS_COLORS.get(ev.display_config["color"], "#95a5a6"),
            "icon_svg": _TYPE_ICONS.get(ev.display_config["label"], _TYPE_ICONS["Other"]),
            "source": ev.source_name,
            "age": _format_age(ev.age_minutes(now)),
            "summary": _esc((ev.summary or "")[:150]),
            "source_url": ev.source_url or "",
            "location": ev.location_name or "",
        }
        for ev in recent_geo
    ], ensure_ascii=False)

    # Build filter buttons HTML — one per event type that has markers
    from collections import Counter
    type_counts: Counter = Counter()
    for ev in recent_geo:
        type_counts[ev.display_config["label"]] += 1
    filter_buttons = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        label = cfg["label"]
        cnt = type_counts.get(label, 0)
        if cnt <= 0:
            continue
        color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
        icon_svg = _TYPE_ICONS.get(label, _TYPE_ICONS["Other"])
        mini = _mini_pin_svg(color, icon_svg, size=12)
        filter_buttons.append(
            f'<button class="filter-btn active" data-type="{label}" '
            f'style="--btn-color:{color};">{mini} {label} <span class="fbtn-count">{cnt}</span></button>'
        )
    all_btn = '<button class="filter-btn active" data-type="__all__" style="--btn-color:#aaa;">Clear all</button>'
    filter_bar_html = all_btn + '<span style="width:1px;height:20px;background:rgba(255,255,255,0.15);align-self:center;"></span>' + ''.join(filter_buttons)

    # Build feed cards HTML
    cards_html = "\n".join(_render_card(ev, now) for ev in feed_items)

    css = get_custom_css()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
    .leaflet-popup-content-wrapper {{
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .leaflet-popup-content {{
        margin: 10px 12px !important;
    }}
    /* ── Custom pin marker ──────────────────────────── */
    .pin-marker {{
        position: relative;
        width: 30px;
        height: 42px;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
        transition: transform 0.15s ease;
    }}
    .pin-marker:hover {{
        transform: scale(1.15);
        z-index: 9999 !important;
    }}
    .pin-body {{
        width: 30px;
        height: 30px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        position: absolute;
        top: 0; left: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid rgba(255,255,255,0.7);
    }}
    .pin-icon {{
        transform: rotate(45deg);
        width: 16px;
        height: 16px;
    }}
    .pin-dot {{
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 6px;
        height: 6px;
        border-radius: 50%;
        opacity: 0.4;
    }}
    @keyframes markerPulse {{
        0% {{ transform: scale(1); opacity: 0.6; }}
        50% {{ transform: scale(1.5); opacity: 0.2; }}
        100% {{ transform: scale(1); opacity: 0.6; }}
    }}
    .marker-highlight {{
        animation: markerPulse 1s infinite;
    }}
    .news-card[data-lat] {{
        cursor: pointer;
    }}
    .news-card[data-lat]:hover {{
        border-color: rgba(231,76,60,0.4);
        background: rgba(231,76,60,0.06);
    }}
    /* Disclaimer bar */
    .disclaimer {{
        font-size: 0.62rem;
        color: rgba(255,255,255,0.35);
        text-align: center;
        padding: 6px 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
        line-height: 1.4;
    }}
    /* ── Filter bar ──────────────────────────────── */
    .filter-bar {{
        position: absolute;
        top: 10px;
        left: 50px;
        right: 10px;
        z-index: 1000;
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        pointer-events: auto;
    }}
    .filter-btn {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 16px;
        background: rgba(14,17,23,0.85);
        color: #ddd;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
    }}
    .filter-btn:hover {{
        background: rgba(255,255,255,0.12);
    }}
    .filter-btn.active {{
        border-color: var(--btn-color);
        box-shadow: 0 0 6px color-mix(in srgb, var(--btn-color) 40%, transparent);
    }}
    .filter-btn.dimmed {{
        opacity: 0.35;
        border-color: rgba(255,255,255,0.06);
        box-shadow: none;
    }}
    .fbtn-count {{
        font-weight: 400;
        opacity: 0.6;
        font-size: 10px;
    }}

</style>
</head>
<body>
<div class="dashboard">
    <div class="map-panel" style="position:relative;">
        <div class="filter-bar">{filter_bar_html}</div>
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
        <div class="disclaimer">
            Information shown is partial and automated.
            For full, verified reporting, visit the original source of each item.
        </div>
    </div>
</div>

<script>
(function() {{
    // ── Restore / init map state ─────────────────────────────────
    var savedState = null;
    try {{
        var raw = sessionStorage.getItem('icm_map_state');
        if (raw) savedState = JSON.parse(raw);
    }} catch(e) {{}}

    var initCenter = savedState ? [savedState.lat, savedState.lng]
                                : [{MAP_DEFAULT_CENTER[0]}, {MAP_DEFAULT_CENTER[1]}];
    var initZoom = savedState ? savedState.zoom : {MAP_DEFAULT_ZOOM};

    var map = L.map('map', {{
        center: initCenter,
        zoom: initZoom,
        minZoom: 3,
        maxZoom: 18,
        zoomControl: true,
    }});

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
    }}).addTo(map);

    // Save map state on every move
    map.on('moveend', function() {{
        var c = map.getCenter();
        sessionStorage.setItem('icm_map_state', JSON.stringify({{
            lat: c.lat, lng: c.lng, zoom: map.getZoom()
        }}));
    }});

    // ── Spread overlapping markers naturally ─────────────────────
    var markersData = {markers_json};
    var markerLookup = {{}};
    var markersByType = {{}};

    // Group by approximate location (~1km precision)
    var coordGroups = {{}};
    markersData.forEach(function(d) {{
        var key = d.lat.toFixed(2) + ',' + d.lng.toFixed(2);
        if (!coordGroups[key]) coordGroups[key] = [];
        coordGroups[key].push(d);
    }});

    // Scatter markers randomly within a small rectangle around the city center
    Object.values(coordGroups).forEach(function(group) {{
        if (group.length <= 1) return;
        var n = group.length;
        // Rectangle half-size scales slightly with count (~0.5-1.2km)
        var halfW = 0.004 + n * 0.001;
        var halfH = 0.003 + n * 0.0008;
        group.forEach(function(d) {{
            d.lat += (Math.random() - 0.5) * 2 * halfH;
            d.lng += (Math.random() - 0.5) * 2 * halfW;
        }});
    }});

    // ── Add pin markers ──────────────────────────────────────────
    markersData.forEach(function(d) {{
        var pinHtml =
            '<div class="pin-marker">' +
            '<div class="pin-body" style="background:' + d.color + ';">' +
            '<svg class="pin-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
            d.icon_svg +
            '</svg>' +
            '</div>' +
            '<div class="pin-dot" style="background:' + d.color + ';"></div>' +
            '</div>';

        var icon = L.divIcon({{
            html: pinHtml,
            className: '',
            iconSize: [30, 42],
            iconAnchor: [15, 42],
            popupAnchor: [0, -42],
        }});

        var marker = L.marker([d.lat, d.lng], {{ icon: icon }});

        var popupHtml =
            '<div style="font-family:Inter,sans-serif;max-width:280px;">' +
            '<div style="display:flex;align-items:center;gap:5px;margin-bottom:5px;">' +
            '<span style="background:' + d.color + ';color:#fff;font-size:9px;font-weight:700;' +
            'padding:2px 6px;border-radius:3px;letter-spacing:0.05em;">' +
            d.type_label.toUpperCase() + '</span>' +
            '<span style="font-size:10px;color:#888;">' + d.age + '</span>' +
            '</div>' +
            '<div style="font-size:13px;font-weight:600;color:#222;margin-bottom:4px;line-height:1.3;">' +
            d.title + '</div>' +
            (d.summary ? '<div style="font-size:11px;color:#555;margin-bottom:4px;">' + d.summary + '</div>' : '') +
            '<div style="display:flex;justify-content:space-between;align-items:center;' +
            'padding-top:4px;border-top:1px solid #eee;font-size:10px;color:#888;">' +
            '<span>' + d.location + ' &middot; ' + d.source + '</span>' +
            (d.source_url ? '<a href="' + d.source_url + '" target="_blank" ' +
            'style="color:#4da6ff;text-decoration:none;font-weight:600;">' +
            d.source + ' &nearr;</a>' : '') +
            '</div></div>';

        marker.bindPopup(popupHtml, {{ maxWidth: 300 }});
        marker.addTo(map);
        markerLookup[d.id] = {{ marker: marker, lat: d.lat, lng: d.lng, color: d.color }};

        // Track markers by type for filtering
        if (!markersByType[d.type_label]) markersByType[d.type_label] = [];
        markersByType[d.type_label].push(marker);
    }});

    // ── Multi-toggle filter logic ───────────────────────────────
    // All types start active; clicking toggles that type on/off
    var activeTypes = new Set(Object.keys(markersByType));

    function applyFilters() {{
        Object.keys(markersByType).forEach(function(t) {{
            markersByType[t].forEach(function(m) {{
                if (activeTypes.has(t)) m.addTo(map);
                else map.removeLayer(m);
            }});
        }});
        document.querySelectorAll('.filter-btn').forEach(function(b) {{
            if (activeTypes.has(b.dataset.type)) {{
                b.classList.add('active');
                b.classList.remove('dimmed');
            }} else {{
                b.classList.remove('active');
                b.classList.add('dimmed');
            }}
        }});
    }}

    document.querySelectorAll('.filter-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var type = this.dataset.type;

            if (type === '__all__') {{
                var allTypes = Object.keys(markersByType);
                if (activeTypes.size === allTypes.length) {{
                    // All are on → clear all
                    activeTypes.clear();
                }} else {{
                    // Some or none on → select all
                    allTypes.forEach(function(t) {{ activeTypes.add(t); }});
                }}
                applyFilters();
                updateAllBtn();
                return;
            }}

            if (activeTypes.has(type)) {{
                activeTypes.delete(type);
            }} else {{
                activeTypes.add(type);
            }}
            applyFilters();
            updateAllBtn();
        }});
    }});

    // Update "All" button label dynamically
    var allBtn = document.querySelector('.filter-btn[data-type="__all__"]');
    function updateAllBtn() {{
        if (!allBtn) return;
        var total = Object.keys(markersByType).length;
        if (activeTypes.size === total) {{
            allBtn.textContent = 'Clear all';
            allBtn.classList.add('active');
            allBtn.classList.remove('dimmed');
        }} else {{
            allBtn.textContent = 'Select all';
            allBtn.classList.remove('active');
            allBtn.classList.add('dimmed');
        }}
    }}

    // ── Hover interaction ────────────────────────────────────────
    var highlightCircle = null;

    function highlightMarker(eventId) {{
        clearHighlight();
        var info = markerLookup[eventId];
        if (!info) return;

        // Center map on marker smoothly
        map.panTo([info.lat, info.lng], {{ animate: true, duration: 0.4 }});

        highlightCircle = L.circleMarker([info.lat, info.lng], {{
            radius: 24,
            color: info.color,
            fillColor: info.color,
            fillOpacity: 0.2,
            weight: 2.5,
            className: 'marker-highlight',
        }}).addTo(map);
        info.marker.openPopup();
    }}

    function clearHighlight() {{
        if (highlightCircle) {{
            map.removeLayer(highlightCircle);
            highlightCircle = null;
        }}
        map.closePopup();
    }}

    document.querySelectorAll('.news-card[data-event-id]').forEach(function(card) {{
        card.addEventListener('mouseenter', function() {{
            highlightMarker(this.dataset.eventId);
        }});
        card.addEventListener('mouseleave', function() {{
            clearHighlight();
        }});
        card.addEventListener('click', function() {{
            var info = markerLookup[this.dataset.eventId];
            if (info) {{
                map.setView([info.lat, info.lng], 10, {{ animate: true }});
                setTimeout(function() {{
                    highlightMarker(card.dataset.eventId);
                }}, 300);
            }}
        }});
    }});

    setTimeout(function() {{ map.invalidateSize(); }}, 100);
}})();
</script>
</body>
</html>"""


# ── Card renderer ─────────────────────────────────────────────────────────

def _render_card(event: NewsEvent, now: datetime) -> str:
    """Render a single news card with mini pin icon in type badge."""
    cfg = event.display_config
    age_min = event.age_minutes(now)
    is_recent = age_min < EVENT_RECENT_MINUTES
    recent_class = " recent" if is_recent else ""

    type_color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
    icon_svg = _TYPE_ICONS.get(cfg["label"], _TYPE_ICONS["Other"])

    # Mini pin SVG next to the type label — matches map markers exactly
    mini = _mini_pin_svg(type_color, icon_svg, size=14)

    type_indicator = (
        f'<span class="type-indicator" '
        f'style="background:rgba({_hex_to_rgb(type_color)},0.15);'
        f'color:{type_color};display:inline-flex;align-items:center;gap:3px;">'
        f'{mini}{cfg["label"]}</span>'
    )

    time_str = _format_age(age_min)
    badge_class = _source_badge_class(event.source_name)
    severity_html = _severity_dots(event.severity)

    location_html = ""
    if event.location_name:
        location_html = f'<div class="location-tag">{event.location_name}</div>'

    article_url = event.source_url or ""
    source_link = ""
    if article_url:
        source_link = (
            f'<a href="{article_url}" target="_blank" rel="noopener" '
            f'class="source-link" onclick="event.stopPropagation();">'
            f'{_EXT_ICON_SVG} Source</a>'
        )

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
    """Render stats bar with mini pin icons matching the map markers 1:1."""
    from collections import Counter
    counts: Counter = Counter()
    for ev in events:
        counts[ev.event_type] += 1

    chips = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        c = counts.get(etype, 0)
        if c > 0:
            type_color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
            icon_svg = _TYPE_ICONS.get(cfg["label"], _TYPE_ICONS["Other"])
            mini = _mini_pin_svg(type_color, icon_svg, size=14)
            chips.append(
                f'<span class="stat-chip">'
                f'{mini}'
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
