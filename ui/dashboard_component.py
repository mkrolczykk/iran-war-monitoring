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

# Max age for map pins (in hours) to prevent map clutter over days
MAP_MAX_AGE_HOURS = 72

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
    summary_text: str = "",
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
            "timestamp_ms": int(ev.timestamp.timestamp() * 1000),
        }
        for ev in recent_geo
    ], ensure_ascii=False)

    from collections import Counter

    # ── Map filter buttons ──────────────────────────────────────
    map_type_counts: Counter = Counter()
    for ev in recent_geo:
        map_type_counts[ev.display_config["label"]] += 1
    map_filter_buttons = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        label = cfg["label"]
        cnt = map_type_counts.get(label, 0)
        if cnt <= 0:
            continue
        color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
        icon_svg = _TYPE_ICONS.get(label, _TYPE_ICONS["Other"])
        mini = _mini_pin_svg(color, icon_svg, size=12)
        map_filter_buttons.append(
            f'<button class="filter-btn active" data-type="{label}" '
            f'style="--btn-color:{color};">{mini} {label} <span class="fbtn-count">{cnt}</span></button>'
        )
    all_btn = '<button class="filter-btn active" data-type="__all__" style="--btn-color:#aaa;">Clear all</button>'
    filter_bar_html = all_btn + '<span style="width:1px;height:20px;background:rgba(255,255,255,0.15);align-self:center;"></span>' + ''.join(map_filter_buttons)

    # ── Feed filter buttons ─────────────────────────────────────
    feed_type_counts: Counter = Counter()
    for ev in feed_items:
        feed_type_counts[ev.display_config["label"]] += 1
    feed_filter_buttons = []
    for etype, cfg in EVENT_TYPE_CONFIG.items():
        label = cfg["label"]
        cnt = feed_type_counts.get(label, 0)
        if cnt <= 0:
            continue
        color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
        icon_svg = _TYPE_ICONS.get(label, _TYPE_ICONS["Other"])
        mini = _mini_pin_svg(color, icon_svg, size=12)
        feed_filter_buttons.append(
            f'<button class="feed-filter-btn active" data-type="{label}" '
            f'style="--btn-color:{color};">{mini} {label} <span class="fbtn-count">{cnt}</span></button>'
        )
    feed_all_btn = '<button class="feed-filter-btn active" data-type="__all__" style="--btn-color:#aaa;">Clear all</button>'
    feed_filter_bar_html = feed_all_btn + '<span style="width:1px;height:16px;background:rgba(255,255,255,0.15);align-self:center;"></span>' + ''.join(feed_filter_buttons)

    # Build feed cards HTML
    cards_html = "\n".join(_render_card(ev, now) for ev in feed_items)

    # Escape summary for safe HTML embedding
    summary_html = _esc(summary_text) if summary_text else ""

    css = get_custom_css()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
{css}
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        background: #0e1117;
        color: #fafafa;
        font-family: 'Inter', -apple-system, sans-serif;
        overflow: hidden;
    }}
    .dashboard {{
        display: flex;
        height: 100vh;
        max-height: 720px;
        gap: 12px;
    }}
    .map-section {{
        flex: 7;
        display: flex;
        flex-direction: column;
        min-width: 0;
    }}
    .map-panel {{
        flex: 1;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
        position: relative;
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
        -webkit-overflow-scrolling: touch;
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
        will-change: transform;
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
    .news-card {{
        contain: content;
    }}
    .news-card[data-lat] {{
        cursor: pointer;
        background: linear-gradient(90deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.12);
        border-left: 3px solid rgba(255, 255, 255, 0.4);
    }}
    .news-card[data-lat]:hover {{
        border-left-color: #e74c3c;
        border-color: rgba(231,76,60,0.4);
        background: linear-gradient(90deg, rgba(231,76,60,0.12) 0%, rgba(231,76,60,0.03) 100%);
    }}
    .news-card[data-lat] .location-tag {{
        color: #e67e22;
        font-weight: 600;
        text-shadow: 0 0 8px rgba(230,126,34,0.4);
    }}
    /* Lazy-loaded cards: hidden initially, revealed by IntersectionObserver */
    .news-card.lazy-hidden {{
        display: none;
    }}
    /* Disclaimer bar */
    .disclaimer {{
        font-size: 0.62rem;
        color: rgba(255,255,255,0.35);
        text-align: left;
        padding: 6px 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
        line-height: 1.4;
    }}
    /* ── Filter bar (desktop: inside map via absolute) ── */
    .map-filters-above {{
        display: none;  /* hidden on desktop */
    }}
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
        transition: opacity 0.15s, border-color 0.15s, box-shadow 0.15s;
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
    .feed-empty-msg {{
        text-align: center;
        padding: 2rem 1rem;
        color: rgba(255,255,255,0.3);
        font-size: 0.8rem;
        display: none;
    }}
    .fbtn-count {{
        font-weight: 400;
        opacity: 0.6;
        font-size: 10px;
    }}
    /* ── Feed filter bar ─────────────────────────── */
    .feed-filter-bar {{
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        padding: 6px 4px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }}
    .feed-filter-btn {{
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 2px 7px;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        background: rgba(14,17,23,0.85);
        color: #ccc;
        font-family: 'Inter', sans-serif;
        font-size: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s, border-color 0.15s, box-shadow 0.15s;
    }}
    .feed-filter-btn:hover {{
        background: rgba(255,255,255,0.1);
    }}
    .feed-filter-btn.active {{
        border-color: var(--btn-color);
        box-shadow: 0 0 4px color-mix(in srgb, var(--btn-color) 30%, transparent);
    }}
    .feed-filter-btn.dimmed {{
        opacity: 0.3;
        border-color: rgba(255,255,255,0.05);
        box-shadow: none;
    }}

    /* ── Timeline slider ────────────────────────── */
    .timeline-bar {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        background: rgba(14,17,23,0.95);
        border-top: 1px solid rgba(255,255,255,0.06);
        flex-shrink: 0;
    }}
    .timeline-play {{
        background: none;
        border: 1px solid rgba(255,255,255,0.2);
        color: #ccc;
        border-radius: 50%;
        width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 11px;
        transition: border-color 0.15s;
        flex-shrink: 0;
    }}
    .timeline-play:hover {{ border-color: rgba(255,255,255,0.5); color: #fff; }}
    .timeline-play.playing {{ border-color: #e74c3c; color: #e74c3c; }}
    .timeline-slider {{
        flex: 1;
        -webkit-appearance: none;
        appearance: none;
        height: 4px;
        background: rgba(255,255,255,0.12);
        border-radius: 2px;
        outline: none;
        cursor: pointer;
    }}
    .timeline-slider::-webkit-slider-thumb {{
        -webkit-appearance: none;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #e74c3c;
        box-shadow: 0 0 6px rgba(231,76,60,0.5);
        cursor: grab;
    }}
    .timeline-slider::-moz-range-thumb {{
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #e74c3c;
        border: none;
        box-shadow: 0 0 6px rgba(231,76,60,0.5);
        cursor: grab;
    }}
    .timeline-label {{
        font-size: 10px;
        color: rgba(255,255,255,0.5);
        white-space: nowrap;
        min-width: 70px;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }}
    .timeline-hint {{
        display: none;
        font-size: 9px;
        color: rgba(255,255,255,0.3);
        font-style: italic;
        text-align: center;
        padding: 2px 10px 4px;
        background: rgba(14,17,23,0.95);
    }}
    /* ── Summary card ──────────────────────────── */
    .summary-card {{
        background: linear-gradient(135deg, rgba(231,76,60,0.08), rgba(155,89,182,0.06));
        border: 1px solid rgba(231,76,60,0.15);
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: border-color 0.2s;
    }}
    .summary-card:hover {{ border-color: rgba(231,76,60,0.3); }}
    .summary-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
    }}
    .summary-label {{
        font-size: 9px;
        font-weight: 700;
        color: #e74c3c;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: flex;
        align-items: center;
        gap: 4px;
    }}
    .summary-chevron {{
        font-size: 10px;
        color: rgba(255,255,255,0.3);
        transition: transform 0.2s;
    }}
    .summary-card.open .summary-chevron {{ transform: rotate(180deg); }}
    .summary-text {{
        font-size: 0.72rem;
        color: rgba(255,255,255,0.7);
        line-height: 1.5;
        margin-top: 6px;
        display: none;
    }}
    .summary-card.open .summary-text {{ display: block; }}
    /* ── Notification toggle ──────────────────── */
    .notif-toggle {{
        background: none;
        border: 1px solid rgba(255,255,255,0.15);
        color: rgba(255,255,255,0.4);
        border-radius: 4px;
        padding: 2px 6px;
        cursor: pointer;
        font-size: 14px;
        line-height: 1;
        transition: all 0.15s;
        flex-shrink: 0;
    }}
    .notif-toggle:hover {{ border-color: rgba(255,255,255,0.3); color: rgba(255,255,255,0.7); }}
    .notif-toggle.enabled {{ border-color: #e74c3c; color: #e74c3c; }}

    /* ── Mobile layout ────────────────────────────── */
    @media (max-width: 768px) {{
        .dashboard {{
            flex-direction: column;
            gap: 6px;
            height: 1200px !important;
            max-height: none !important;
        }}
        .map-section {{
            flex: none;
            height: 50% !important;
            order: 2;
        }}
        .feed-panel {{
            flex: none;
            height: 50% !important;
            order: 1;
        }}
        /* Show filter bar ABOVE map on mobile — matches feed filter style */
        .map-filters-above {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            padding: 6px 4px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        /* Shrink map filter buttons to match feed-filter-btn size */
        .map-filters-above .filter-btn {{
            display: inline-flex !important;
            padding: 2px 7px;
            font-size: 10px;
            border-radius: 12px;
            gap: 3px;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
        }}
        /* Hide the overlay version on mobile */
        .filter-bar {{
            display: none !important;
        }}
        .timeline-hint {{
            display: block;
        }}
        .map-panel {{
            flex: 1;
        }}
        .news-feed-container {{
            max-height: 100% !important;
        }}
    }}

</style>
</head>
<body>
<div class="dashboard">
    <div class="map-section">
        <div class="map-filters-above">{filter_bar_html}</div>
        <div class="map-panel">
            <div class="filter-bar">{filter_bar_html}</div>
            <div id="map"></div>
        </div>
        <div class="timeline-bar">
            <span style="font-size:9px;font-weight:700;color:rgba(255,255,255,0.45);text-transform:uppercase;letter-spacing:0.08em;white-space:nowrap;">Event Timeline (72h)</span>
            <button class="timeline-play" id="timelinePlay" title="Play/Pause — watch events appear chronologically on the map">&#9654;</button>
            <input type="range" class="timeline-slider" id="timelineSlider" min="0" max="100" value="100" title="Drag to travel back in time and see when events occurred">
            <span class="timeline-label" id="timelineLabel">Now</span>
        </div>
        <div class="timeline-hint">Drag the slider or press play to see events appear on the map over time</div>
    </div>
    <div class="feed-panel">
        <div class="feed-header" style="display:flex;align-items:center;justify-content:space-between;">
            <span>
                NEWS LIVE &nbsp;
                <span style="font-weight:400;opacity:0.5;">
                    {now.strftime('%d/%m/%Y %H:%M:%S')} UTC
                </span>
            </span>
            <button class="notif-toggle" id="notifToggle" title="Toggle sound & browser notifications for critical events">
                🔔
            </button>
        </div>
        {f'<div class="summary-card open" id="summaryCard"><div class="summary-header" id="summaryToggle"><span class="summary-label"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg> Situation Overview</span><span class="summary-chevron">▼</span></div><div class="summary-text">' + summary_html + '</div></div>' if summary_html else ''}
        <div class="feed-filter-bar">{feed_filter_bar_html}</div>
        <div class="news-feed-container">
            {cards_html if cards_html else _empty_state()}
            <div class="feed-empty-msg" id="feedEmptyMsg">
                No events to display.<br/>Select at least one category above.
            </div>
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

        if (!markersByType[d.type_label]) markersByType[d.type_label] = [];
        markersByType[d.type_label].push(marker);
    }});

    // ── Multi-toggle filter logic ───────────────────────────────
    var activeTypes = new Set(Object.keys(markersByType));

    function applyFilters() {{
        Object.keys(markersByType).forEach(function(t) {{
            markersByType[t].forEach(function(m) {{
                if (activeTypes.has(t)) m.addTo(map);
                else map.removeLayer(m);
            }});
        }});
        // Update both desktop and mobile filter button sets
        document.querySelectorAll('.filter-btn').forEach(function(b) {{
            if (b.dataset.type === '__all__') return;
            if (activeTypes.has(b.dataset.type)) {{
                b.classList.add('active');
                b.classList.remove('dimmed');
            }} else {{
                b.classList.remove('active');
                b.classList.add('dimmed');
            }}
        }});
    }}

    // Attach click handlers to ALL .filter-btn elements (desktop overlay + mobile above-map)
    document.querySelectorAll('.filter-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var type = this.dataset.type;

            if (type === '__all__') {{
                var allTypes = Object.keys(markersByType);
                if (activeTypes.size === allTypes.length) {{
                    activeTypes.clear();
                }} else {{
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

    // Update ALL "All" buttons (both desktop + mobile)
    function updateAllBtn() {{
        var total = Object.keys(markersByType).length;
        document.querySelectorAll('.filter-btn[data-type="__all__"]').forEach(function(btn) {{
            if (activeTypes.size === total) {{
                btn.textContent = 'Clear all';
                btn.classList.add('active');
                btn.classList.remove('dimmed');
            }} else {{
                btn.textContent = 'Select all';
                btn.classList.remove('active');
                btn.classList.add('dimmed');
            }}
        }});
    }}

    // ── Hover interaction (debounced for performance) ────────────
    var highlightCircle = null;
    var hoverTimer = null;

    function highlightMarker(eventId) {{
        clearHighlight();
        var info = markerLookup[eventId];
        if (!info) return;

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
        if (hoverTimer) {{ clearTimeout(hoverTimer); hoverTimer = null; }}
        if (highlightCircle) {{
            map.removeLayer(highlightCircle);
            highlightCircle = null;
        }}
        map.closePopup();
    }}

    document.querySelectorAll('.news-card[data-event-id]').forEach(function(card) {{
        card.addEventListener('mouseenter', function() {{
            var id = this.dataset.eventId;
            if (hoverTimer) clearTimeout(hoverTimer);
            hoverTimer = setTimeout(function() {{ 
                var info = markerLookup[id];
                if (info) {{
                    map.setView([info.lat, info.lng], 10, {{ animate: true }});
                    setTimeout(function() {{
                        // Don't draw popup if mouse already left
                        if (!hoverTimer) return;
                        highlightMarker(id);
                    }}, 300);
                }} else {{
                    highlightMarker(id);
                }}
            }}, 150);
        }});
        card.addEventListener('mouseleave', function() {{
            clearHighlight();
        }});
        card.addEventListener('click', function() {{
            var info = markerLookup[this.dataset.eventId];
            if (info) {{
                // Scroll the map into view to improve mobile UX
                document.getElementById('map').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                
                map.setView([info.lat, info.lng], 10, {{ animate: true }});
                setTimeout(function() {{
                    highlightMarker(card.dataset.eventId);
                }}, 300);
            }}
        }});
    }});

    setTimeout(function() {{ map.invalidateSize(); }}, 100);

    // ── Lazy card rendering (IntersectionObserver) ───────────────
    var INITIAL_VISIBLE = 20;
    var cards = document.querySelectorAll('.news-card[data-type]');
    if (cards.length > INITIAL_VISIBLE) {{
        // Hide cards beyond the first batch
        for (var i = INITIAL_VISIBLE; i < cards.length; i++) {{
            cards[i].classList.add('lazy-hidden');
        }}
        // Sentinel element to trigger loading more
        var sentinel = document.createElement('div');
        sentinel.id = 'lazySentinel';
        sentinel.style.height = '1px';
        var feedContainer = document.querySelector('.news-feed-container');
        if (feedContainer) {{
            feedContainer.appendChild(sentinel);
            var lazyIdx = INITIAL_VISIBLE;
            var observer = new IntersectionObserver(function(entries) {{
                if (!entries[0].isIntersecting) return;
                var end = Math.min(lazyIdx + 15, cards.length);
                for (var j = lazyIdx; j < end; j++) {{
                    cards[j].classList.remove('lazy-hidden');
                }}
                lazyIdx = end;
                if (lazyIdx >= cards.length) observer.disconnect();
            }}, {{ root: feedContainer, rootMargin: '200px' }});
            observer.observe(sentinel);
        }}
    }}

    // ── Feed filter logic ────────────────────────────────────────
    var feedActiveTypes = new Set();
    document.querySelectorAll('.feed-filter-btn.active').forEach(function(b) {{
        if (b.dataset.type !== '__all__') feedActiveTypes.add(b.dataset.type);
    }});
    var feedEmptyMsg = document.getElementById('feedEmptyMsg');

    function applyFeedFilters() {{
        var anyVisible = false;
        document.querySelectorAll('.news-card[data-type]').forEach(function(card) {{
            if (feedActiveTypes.size === 0 || !feedActiveTypes.has(card.dataset.type)) {{
                card.style.display = 'none';
            }} else {{
                card.style.display = '';
                card.classList.remove('lazy-hidden');
                anyVisible = true;
            }}
        }});
        if (feedEmptyMsg) feedEmptyMsg.style.display = anyVisible ? 'none' : 'block';
        document.querySelectorAll('.feed-filter-btn').forEach(function(b) {{
            if (b.dataset.type === '__all__') return;
            if (feedActiveTypes.has(b.dataset.type)) {{
                b.classList.add('active');
                b.classList.remove('dimmed');
            }} else {{
                b.classList.remove('active');
                b.classList.add('dimmed');
            }}
        }});
        updateFeedAllBtn();
    }}

    var feedAllBtn = document.querySelector('.feed-filter-btn[data-type="__all__"]');
    function updateFeedAllBtn() {{
        if (!feedAllBtn) return;
        var allFeedTypes = new Set();
        document.querySelectorAll('.feed-filter-btn:not([data-type="__all__"])').forEach(function(b) {{
            allFeedTypes.add(b.dataset.type);
        }});
        if (feedActiveTypes.size === allFeedTypes.size) {{
            feedAllBtn.textContent = 'Clear all';
            feedAllBtn.classList.add('active');
            feedAllBtn.classList.remove('dimmed');
        }} else {{
            feedAllBtn.textContent = 'Select all';
            feedAllBtn.classList.remove('active');
            feedAllBtn.classList.add('dimmed');
        }}
    }}

    document.querySelectorAll('.feed-filter-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var type = this.dataset.type;
            if (type === '__all__') {{
                var allFeedTypes = [];
                document.querySelectorAll('.feed-filter-btn:not([data-type="__all__"])').forEach(function(b) {{
                    allFeedTypes.push(b.dataset.type);
                }});
                if (feedActiveTypes.size === allFeedTypes.length) {{
                    feedActiveTypes.clear();
                }} else {{
                    allFeedTypes.forEach(function(t) {{ feedActiveTypes.add(t); }});
                }}
                applyFeedFilters();
                return;
            }}
            if (feedActiveTypes.has(type)) {{
                feedActiveTypes.delete(type);
            }} else {{
                feedActiveTypes.add(type);
            }}
            applyFeedFilters();
        }});
    }});

    // ── Timeline slider ──────────────────────────────────────────
    var slider = document.getElementById('timelineSlider');
    var tlLabel = document.getElementById('timelineLabel');
    var tlPlay = document.getElementById('timelinePlay');

    // Compute time range from marker data
    var timestamps = markersData.map(function(d) {{ return d.timestamp_ms; }}).filter(Boolean);
    var tsMin = timestamps.length ? Math.min.apply(null, timestamps) : 0;
    var tsMax = timestamps.length ? Math.max.apply(null, timestamps) : 0;
    var tsRange = tsMax - tsMin;

    function formatTs(ms) {{
        if (!ms) return 'Now';
        var d = new Date(ms);
        var hh = String(d.getUTCHours()).padStart(2, '0');
        var mm = String(d.getUTCMinutes()).padStart(2, '0');
        var dd = String(d.getUTCDate()).padStart(2, '0');
        var mo = String(d.getUTCMonth() + 1).padStart(2, '0');
        return dd + '/' + mo + ' ' + hh + ':' + mm;
    }}

    function applyTimeline(pct) {{
        if (!tsRange || timestamps.length === 0) return;
        var cutoff = tsMin + (pct / 100) * tsRange;
        markersData.forEach(function(d) {{
            var info = markerLookup[d.id];
            if (!info) return;
            // Only filter by timeline if the type is also active
            if (d.timestamp_ms <= cutoff && activeTypes.has(d.type_label)) {{
                info.marker.addTo(map);
            }} else {{
                map.removeLayer(info.marker);
            }}
        }});
        if (pct >= 100) {{
            tlLabel.textContent = 'Now';
        }} else {{
            tlLabel.textContent = formatTs(cutoff);
        }}
    }}

    if (slider) {{
        slider.addEventListener('input', function() {{
            applyTimeline(parseInt(this.value));
        }});
    }}

    // Auto-play animation
    var isPlaying = false;
    var playInterval = null;

    if (tlPlay) {{
        tlPlay.addEventListener('click', function() {{
            isPlaying = !isPlaying;
            this.classList.toggle('playing', isPlaying);
            this.textContent = isPlaying ? '⏸' : '▶';

            if (isPlaying) {{
                // Start from beginning if at the end
                if (parseInt(slider.value) >= 100) slider.value = 0;
                playInterval = setInterval(function() {{
                    var val = parseInt(slider.value) + 1;
                    if (val > 100) {{
                        val = 100;
                        isPlaying = false;
                        tlPlay.classList.remove('playing');
                        tlPlay.textContent = '▶';
                        clearInterval(playInterval);
                        playInterval = null;
                    }}
                    slider.value = val;
                    applyTimeline(val);
                }}, 400);
            }} else {{
                if (playInterval) {{ clearInterval(playInterval); playInterval = null; }}
            }}
        }});
    }}

    // ── Notification system ───────────────────────────────────────
    var notifBtn = document.getElementById('notifToggle');
    var CRITICAL_TYPES = ['Airstrike', 'Missile', 'Explosion'];
    var notifEnabled = false;
    var audioCtx = null;

    // Restore preference
    try {{
        notifEnabled = localStorage.getItem('icm_notif_enabled') === 'true';
    }} catch(e) {{}}

    function updateNotifBtn() {{
        if (!notifBtn) return;
        notifBtn.classList.toggle('enabled', notifEnabled);
        notifBtn.title = notifEnabled
            ? 'Notifications ON — click to disable'
            : 'Toggle sound & browser notifications for critical events';
    }}
    updateNotifBtn();

    function playAlertBeep() {{
        try {{
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            // Two-tone warning beep
            [520, 680].forEach(function(freq, i) {{
                var osc = audioCtx.createOscillator();
                var gain = audioCtx.createGain();
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.frequency.value = freq;
                osc.type = 'sine';
                gain.gain.value = 0.15;
                var start = audioCtx.currentTime + i * 0.18;
                osc.start(start);
                gain.gain.exponentialRampToValueAtTime(0.001, start + 0.15);
                osc.stop(start + 0.15);
            }});
        }} catch(e) {{}}
    }}

    function showNotification(title, body) {{
        try {{
            if (Notification.permission === 'granted') {{
                new Notification(title, {{
                    body: body,
                    icon: 'data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><text y=\".9em\" font-size=\"90\">🚨</text></svg>',
                    tag: 'icm-alert',
                    requireInteraction: false,
                }});
            }}
        }} catch(e) {{}}
    }}

    // Check for new critical events
    var seenIds = new Set();
    try {{
        var stored = sessionStorage.getItem('icm_seen_ids');
        if (stored) JSON.parse(stored).forEach(function(id) {{ seenIds.add(id); }});
    }} catch(e) {{}}

    if (notifEnabled) {{
        var newCritical = [];
        markersData.forEach(function(d) {{
            if (CRITICAL_TYPES.indexOf(d.type_label) !== -1 && !seenIds.has(d.id)) {{
                newCritical.push(d);
            }}
        }});
        if (newCritical.length > 0) {{
            playAlertBeep();
            var first = newCritical[0];
            showNotification(
                '⚠ ' + first.type_label.toUpperCase(),
                first.title + (newCritical.length > 1 ? ' (+' + (newCritical.length - 1) + ' more)' : '')
            );
        }}
    }}

    // Mark all current events as seen
    markersData.forEach(function(d) {{ seenIds.add(d.id); }});
    try {{
        sessionStorage.setItem('icm_seen_ids', JSON.stringify(Array.from(seenIds)));
    }} catch(e) {{}}

    if (notifBtn) {{
        notifBtn.addEventListener('click', function() {{
            notifEnabled = !notifEnabled;
            updateNotifBtn();
            try {{
                localStorage.setItem('icm_notif_enabled', notifEnabled ? 'true' : 'false');
            }} catch(e) {{}}
            if (notifEnabled) {{
                // Request notification permission + init audio context with user gesture
                if ('Notification' in window && Notification.permission === 'default') {{
                    Notification.requestPermission();
                }}
                if (!audioCtx) {{
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }}
                // Play a very quiet test beep so user knows it works
                playAlertBeep();
            }}
        }});
    }}

    // ── Summary card toggle ──────────────────────────────────────
    var summaryToggle = document.getElementById('summaryToggle');
    var summaryCard = document.getElementById('summaryCard');
    if (summaryToggle && summaryCard) {{
        summaryToggle.addEventListener('click', function() {{
            summaryCard.classList.toggle('open');
        }});
    }}

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
        location_html = f'<div class="location-tag">📍 {event.location_name}</div>'

    article_url = event.source_url or ""
    source_link = ""
    if article_url:
        source_link = (
            f'<a href="{article_url}" target="_blank" rel="noopener" '
            f'class="source-link" onclick="event.stopPropagation();">'
            f'{_EXT_ICON_SVG} Source</a>'
        )

    data_attrs = f'data-type="{cfg["label"]}"'
    if event.has_location:
        data_attrs += (
            f' data-event-id="{event.id}"'
            f' data-lat="{event.latitude}"'
            f' data-lng="{event.longitude}"'
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
