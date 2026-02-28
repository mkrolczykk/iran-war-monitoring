"""
Interactive map component using Folium + streamlit-folium.

Renders a dark-themed map with colour-coded markers for each event type,
custom popups, and pulse animations on recent events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import folium
from folium.plugins import MarkerCluster

from config.settings import MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, EVENT_RECENT_MINUTES
from models.events import EventType, EVENT_TYPE_CONFIG, NewsEvent


# Folium icon colour mapping
_FOLIUM_COLORS = {
    "red": "red",
    "orange": "orange",
    "yellow": "orange",     # folium doesn't have yellow – use orange
    "blue": "blue",
    "purple": "purple",
    "pink": "pink",
    "gray": "gray",
    "white": "lightgray",
}

# CSS colour values for popup styling
_CSS_COLORS = {
    "red": "#e74c3c",
    "orange": "#e67e22",
    "yellow": "#f1c40f",
    "blue": "#3498db",
    "purple": "#9b59b6",
    "pink": "#e91e63",
    "gray": "#95a5a6",
    "white": "#bdc3c7",
}


def build_map(events: List[NewsEvent], *, height: int = 600) -> folium.Map:
    """
    Build a Folium map centred on the Middle East with event markers.

    Parameters
    ----------
    events : list of NewsEvent
        Only events with lat/lon will be plotted.
    height : int
        Map height in pixels (width is always 100%).

    Returns
    -------
    folium.Map
    """
    m = folium.Map(
        location=MAP_DEFAULT_CENTER,
        zoom_start=MAP_DEFAULT_ZOOM,
        tiles="CartoDB dark_matter",
        control_scale=True,
        prefer_canvas=True,
    )

    # Add a secondary tile layer option
    folium.TileLayer("CartoDB positron", name="Light Mode").add_to(m)
    folium.LayerControl(position="bottomleft").add_to(m)

    now = datetime.now(timezone.utc)

    geo_events = [e for e in events if e.has_location]

    # Use marker cluster when many events
    use_cluster = len(geo_events) > 80
    cluster = MarkerCluster(name="Events") if use_cluster else None
    if cluster:
        cluster.add_to(m)

    for event in geo_events:
        cfg = event.display_config
        folium_color = _FOLIUM_COLORS.get(cfg["color"], "gray")
        is_recent = event.age_minutes(now) < EVENT_RECENT_MINUTES

        # Popup content
        popup_html = _build_popup_html(event, is_recent)

        # Tooltip (hover) – professional text, no emoji
        tooltip = f"[{cfg['label'].upper()}] {event.title[:80]}"

        icon = folium.Icon(
            color=folium_color,
            icon=cfg["icon"],
            prefix="glyphicon",
        )

        marker = folium.Marker(
            location=[event.latitude, event.longitude],
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=tooltip,
            icon=icon,
        )

        if cluster and use_cluster:
            marker.add_to(cluster)
        else:
            marker.add_to(m)

        # Pulse circle for recent events
        if is_recent:
            folium.CircleMarker(
                location=[event.latitude, event.longitude],
                radius=18,
                color=folium_color,
                fill=True,
                fill_color=folium_color,
                fill_opacity=0.15,
                weight=1,
                opacity=0.4,
            ).add_to(m)

    return m


def _build_popup_html(event: NewsEvent, is_recent: bool) -> str:
    """Build the HTML for a marker popup."""
    cfg = event.display_config
    css_color = _CSS_COLORS.get(cfg["color"], "#95a5a6")
    
    recent_badge = (
        '<span style="background:#e74c3c;color:#fff;padding:1px 6px;'
        'border-radius:3px;font-size:10px;margin-left:5px;font-weight:600;'
        'letter-spacing:0.03em;">LIVE</span>'
        if is_recent else ""
    )

    # Source link always points to the main live blog
    source_link = ""
    if event.source_url:
        source_link = (
            f'<a href="{event.source_url}" target="_blank" '
            f'style="color:#4da6ff;font-size:11px;text-decoration:none;">'
            f'{event.source_name} &nearr;</a>'
        )

    age_str = _format_age(event.age_minutes())

    return f"""
    <div style="font-family:Inter,-apple-system,sans-serif;max-width:300px;padding:4px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <span style="background:{css_color};color:#fff;font-size:9px;font-weight:700;
                          padding:2px 5px;border-radius:3px;letter-spacing:0.05em;">
                {cfg['label'].upper()}
            </span>
            {recent_badge}
        </div>
        <div style="font-size:13px;font-weight:600;color:#222;margin-bottom:6px;
                    line-height:1.3;">
            {event.title}
        </div>
        {'<div style="font-size:11px;color:#555;margin-bottom:6px;line-height:1.4;">'
         + event.summary[:200] + '</div>' if event.summary else ''}
        <div style="display:flex;justify-content:space-between;align-items:center;
                    margin-top:4px;padding-top:4px;border-top:1px solid #ddd;">
            <span style="font-size:10px;color:#888;">
                {event.location_name} &middot; {age_str}
            </span>
            {source_link}
        </div>
    </div>
    """


def _format_age(minutes: float) -> str:
    """Format age in human-readable form."""
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"
