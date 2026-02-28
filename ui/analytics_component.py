"""
Analytics section – rendered as inline HTML via st.markdown (no iframe).

Provides four panels:
1. Hourly activity chart (last 24h) – shows escalation/de-escalation visually
2. Event type breakdown – horizontal bars per category
3. Source activity – which feeds produce the most events
4. Top affected locations – geographic hotspots
"""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List

from models.events import NewsEvent, EVENT_TYPE_CONFIG

# Color for each event label (matches dashboard)
_CSS_COLORS = {
    "red": "#e74c3c",
    "orange": "#e67e22",
    "yellow": "#f1c40f",
    "blue": "#3498db",
    "green": "#2ecc71",
    "purple": "#9b59b6",
    "pink": "#e91e8a",
    "gray": "#95a5a6",
}

_LABEL_COLORS: dict[str, str] = {}
for _et, _cfg in EVENT_TYPE_CONFIG.items():
    _LABEL_COLORS[_cfg["label"]] = _CSS_COLORS.get(_cfg["color"], "#95a5a6")


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def build_analytics_html(events: List[NewsEvent]) -> str:
    """Build inline HTML analytics section for st.markdown."""
    now = datetime.now(timezone.utc)

    # ── Analytics timeframe (72h for broad coverage) ─────────────
    cutoff_analytics = now - timedelta(hours=72)
    recent_events = [ev for ev in events if ev.timestamp >= cutoff_analytics]

    # ── Hourly activity (last 72 h) ─────────────────────────
    hourly: dict[int, int] = {}
    for h in range(72):
        hourly[h] = 0
    cutoff_72h = now - timedelta(hours=72)
    recent_72h_events = [ev for ev in events if ev.timestamp >= cutoff_72h]

    for ev in recent_72h_events:
        hours_ago = int((now - ev.timestamp).total_seconds() / 3600)
        if 0 <= hours_ago < 72:
            hourly[hours_ago] += 1

    max_hourly = max(hourly.values()) if hourly else 1
    max_hourly = max(max_hourly, 1)
    mid_hourly = max_hourly // 2

    # Y-axis labels for the bar chart
    y_axis_html = (
        f'<div class="an-y-axis">'
        f'<span>{max_hourly}</span>'
        f'<span>{mid_hourly}</span>'
        f'<span>0</span>'
        f'</div>'
    )
    
    # Grid lines behind the bars
    grid_lines_html = (
        f'<div class="an-grid-lines">'
        f'<div class="an-grid-line" style="bottom: 100%;"></div>'
        f'<div class="an-grid-line" style="bottom: 50%;"></div>'
        f'<div class="an-grid-line" style="bottom: 0%;"></div>'
        f'</div>'
    )

    hour_bars = ""
    for h in range(71, -1, -1):
        count = hourly[h]
        pct = (count / max_hourly) * 100
        t = now - timedelta(hours=h)
        label = t.strftime("%H:%M")
        opacity = 0.3 if count == 0 else 0.7 + 0.3 * (count / max_hourly)
        hour_bars += (
            f'<div class="an-hbar-col" title="{label} UTC — {count} events">'
            f'<div class="an-hbar-fill" style="height:{max(pct, 2)}%;opacity:{opacity:.2f};"></div>'
            f'<span class="an-hbar-lbl">{label if h % 12 == 0 else ""}</span>'
            f'</div>'
        )

    # ── Event type breakdown ─────────────────────────────────────
    type_counts: Counter = Counter()
    for ev in recent_events:
        type_counts[ev.display_config["label"]] += 1

    type_bars = ""
    type_max = max(type_counts.values()) if type_counts else 1
    for label, count in type_counts.most_common():
        color = _LABEL_COLORS.get(label, "#95a5a6")
        pct = (count / type_max) * 100
        type_bars += (
            f'<div class="an-tbar-row">'
            f'<span class="an-tbar-label">{_esc(label)}</span>'
            f'<div class="an-tbar-track"><div class="an-tbar-fill" style="width:{pct}%;background:{color};"></div></div>'
            f'<span class="an-tbar-count">{count}</span>'
            f'</div>'
        )

    # ── Source activity ──────────────────────────────────────────
    source_counts: Counter = Counter()
    for ev in recent_events:
        source_counts[ev.source_name] += 1

    source_bars = ""
    src_max = max(source_counts.values()) if source_counts else 1
    for src, count in source_counts.most_common(8):
        pct = (count / src_max) * 100
        source_bars += (
            f'<div class="an-tbar-row">'
            f'<span class="an-tbar-label">{_esc(src)}</span>'
            f'<div class="an-tbar-track"><div class="an-tbar-fill" style="width:{pct}%;background:#3498db;"></div></div>'
            f'<span class="an-tbar-count">{count}</span>'
            f'</div>'
        )

    # ── Top locations ────────────────────────────────────────────
    loc_counts: Counter = Counter()
    for ev in recent_events:
        if ev.location_name:
            loc_counts[ev.location_name] += 1

    loc_bars = ""
    loc_max = max(loc_counts.values()) if loc_counts else 1
    for loc, count in loc_counts.most_common(8):
        pct = (count / loc_max) * 100
        loc_bars += (
            f'<div class="an-tbar-row">'
            f'<span class="an-tbar-label">{_esc(loc)}</span>'
            f'<div class="an-tbar-track"><div class="an-tbar-fill" style="width:{pct}%;background:#e74c3c;"></div></div>'
            f'<span class="an-tbar-count">{count}</span>'
            f'</div>'
        )

    # ── Key metrics ──────────────────────────────────────────────
    total_72h = len(recent_events)
    critical_count = sum(
        1 for ev in recent_events
        if ev.display_config["label"] in {"Airstrike", "Missile", "Explosion"}
    )
    geo_count = sum(1 for ev in recent_events if ev.has_location)
    sources_active = len(source_counts)

    last_hour = sum(1 for ev in recent_events if ev.age_minutes(now) <= 60)
    prev_hour = sum(1 for ev in recent_events if 60 < ev.age_minutes(now) <= 120)
    if last_hour > prev_hour:
        trend_icon = "&#9650;"
        trend_color = "#e74c3c"
        trend_label = "escalating"
    elif last_hour < prev_hour:
        trend_icon = "&#9660;"
        trend_color = "#2ecc71"
        trend_label = "calming"
    else:
        trend_icon = "&#9679;"
        trend_color = "#f1c40f"
        trend_label = "stable"

    # ── Intensity trend SVG (72h, per-hour) ───────────────────────
    # hourly dict already computed above: hourly[h] = count where h=hours_ago
    # Build ordered list: oldest (71h ago) to newest (0h ago)
    trend_points = [hourly.get(h, 0) for h in range(71, -1, -1)]
    trend_max = max(trend_points) if trend_points else 1
    trend_max = max(trend_max, 1)

    # SVG dimensions
    svg_w, svg_h = 600, 140
    pad_l, pad_r, pad_t, pad_b = 0, 0, 5, 18  # space for labels at bottom
    chart_w = svg_w - pad_l - pad_r
    chart_h = svg_h - pad_t - pad_b
    n = len(trend_points)
    step_x = chart_w / max(n - 1, 1)

    # Build polyline points
    svg_line_pts = []
    svg_area_pts = []
    for i, val in enumerate(trend_points):
        x = pad_l + i * step_x
        y = pad_t + chart_h - (val / trend_max) * chart_h
        svg_line_pts.append(f"{x:.1f},{y:.1f}")
        svg_area_pts.append(f"{x:.1f},{y:.1f}")

    # Close area polygon at bottom
    area_bottom = pad_t + chart_h
    svg_area_pts.append(f"{pad_l + (n - 1) * step_x:.1f},{area_bottom:.1f}")
    svg_area_pts.append(f"{pad_l:.1f},{area_bottom:.1f}")

    line_pts_str = " ".join(svg_line_pts)
    area_pts_str = " ".join(svg_area_pts)

    # Average line
    avg_val = sum(trend_points) / max(len(trend_points), 1)
    avg_y = pad_t + chart_h - (avg_val / trend_max) * chart_h

    # Time labels (every 12 hours)
    svg_labels = ""
    for i in range(0, n, 12):
        x = pad_l + i * step_x
        t = now - timedelta(hours=71 - i)
        lbl = t.strftime("%H:%M")
        svg_labels += f'<text x="{x:.1f}" y="{svg_h}" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-size="7">{lbl}</text>'

    # Add Y-axis texts and grid lines
    svg_y_axis = ""
    mid_val = int(trend_max / 2)
    grid_y_mid = pad_t + chart_h - (mid_val / trend_max) * chart_h
    
    # Grid lines
    svg_y_axis += f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l + chart_w}" y2="{pad_t}" stroke="rgba(255,255,255,0.08)" stroke-width="1" stroke-dasharray="2,2"/>'
    svg_y_axis += f'<line x1="{pad_l}" y1="{grid_y_mid:.1f}" x2="{pad_l + chart_w}" y2="{grid_y_mid:.1f}" stroke="rgba(255,255,255,0.08)" stroke-width="1" stroke-dasharray="2,2"/>'
    svg_y_axis += f'<line x1="{pad_l}" y1="{pad_t + chart_h}" x2="{pad_l + chart_w}" y2="{pad_t + chart_h}" stroke="rgba(255,255,255,0.08)" stroke-width="1" stroke-dasharray="2,2"/>'
    
    # Y-axis Labels
    svg_y_axis += f'<text x="{pad_l - 4}" y="{pad_t + 3}" text-anchor="end" fill="rgba(255,255,255,0.4)" font-size="6">{trend_max}</text>'
    svg_y_axis += f'<text x="{pad_l - 4}" y="{grid_y_mid + 2:.1f}" text-anchor="end" fill="rgba(255,255,255,0.4)" font-size="6">{mid_val}</text>'
    svg_y_axis += f'<text x="{pad_l - 4}" y="{pad_t + chart_h + 2}" text-anchor="end" fill="rgba(255,255,255,0.4)" font-size="6">0</text>'

    # Dots on each point
    svg_dots = ""
    for i, val in enumerate(trend_points):
        x = pad_l + i * step_x
        y = pad_t + chart_h - (val / trend_max) * chart_h
        if val > 0:
            t = now - timedelta(hours=71 - i)
            lbl = t.strftime("%H:%M UTC")
            svg_dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#e74c3c" opacity="0.8"><title>{lbl} — {val} events</title></circle>'

    # Determine current gradient based on recent trend
    if trend_label == "escalating":
        grad_start, grad_end = "#e67e22", "#e74c3c"
    elif trend_label == "calming":
        grad_start, grad_end = "#e74c3c", "#2ecc71"
    else:
        grad_start, grad_end = "#f1c40f", "#e67e22"

    trend_svg = f"""<svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="{svg_h}" preserveAspectRatio="none" style="overflow:visible;margin-left:14px;" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="trendGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="{grad_start}" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="{grad_end}" stop-opacity="0.5"/>
        </linearGradient>
      </defs>
      {svg_y_axis}
      <polygon points="{area_pts_str}" fill="url(#trendGrad)"/>
      <polyline points="{line_pts_str}" fill="none" stroke="{trend_color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <line x1="{pad_l}" y1="{avg_y:.1f}" x2="{pad_l + (n-1) * step_x:.1f}" y2="{avg_y:.1f}" stroke="rgba(255,255,255,0.15)" stroke-width="1" stroke-dasharray="4,3"/>
      <text x="{pad_l + (n-1) * step_x + 3:.1f}" y="{avg_y:.1f}" fill="rgba(255,255,255,0.25)" font-size="7" dominant-baseline="middle">avg</text>
      {svg_dots}
      {svg_labels}
    </svg>"""

    no_data = '<div style="font-size:11px;color:rgba(255,255,255,0.3);">No data yet</div>'

    return f"""<style>
.analytics {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    padding: 4px 0;
}}
.an-panel {{
    background: rgba(14,17,23,0.85);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 12px 14px;
}}
.an-panel-title {{
    font-size: 9px;
    font-weight: 700;
    color: rgba(255,255,255,0.4);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
}}
.an-metrics {{
    grid-column: 1 / -1;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}}
.an-metric-card {{
    flex: 1;
    min-width: 120px;
    background: rgba(14,17,23,0.85);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 12px 14px;
    text-align: center;
}}
.an-metric-value {{
    font-size: 28px;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #e74c3c, #e67e22);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.an-metric-value.blue {{
    background: linear-gradient(135deg, #3498db, #2ecc71);
    -webkit-background-clip: text;
    background-clip: text;
}}
.an-metric-value.purple {{
    background: linear-gradient(135deg, #9b59b6, #e91e8a);
    -webkit-background-clip: text;
    background-clip: text;
}}
.an-metric-label {{
    font-size: 9px;
    color: rgba(255,255,255,0.4);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 4px;
}}
.an-trend-badge {{
    display: inline-block;
    font-size: 9px;
    padding: 1px 6px;
    border-radius: 8px;
    margin-top: 4px;
    font-weight: 600;
}}
.an-hourly-chart {{
    grid-column: 1 / -1;
}}
.an-hbar-wrapper {{
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 140px;
    position: relative;
    padding-top: 5px;
}}
.an-y-axis {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    font-size: 8px;
    color: rgba(255,255,255,0.4);
    text-align: right;
    min-width: 15px;
    padding-bottom: 13px; /* Align with labels bottom */
}}
.an-grid-lines {{
    position: absolute;
    left: 23px; /* Past Y axis */
    right: 0;
    top: 5px;
    bottom: 13px;
    z-index: 0;
    pointer-events: none;
}}
.an-grid-line {{
    position: absolute;
    left: 0;
    right: 0;
    border-bottom: 1px dashed rgba(255,255,255,0.08);
}}
.an-hbar-container {{
    display: flex;
    align-items: flex-end;
    gap: 2px;
    flex: 1;
    height: 100%;
    position: relative;
    z-index: 1;
}}
.an-hbar-col {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
}}
.an-hbar-fill {{
    width: 100%;
    background: linear-gradient(180deg, #e74c3c 0%, #e67e22 100%);
    border-radius: 2px 2px 0 0;
    min-height: 1px;
}}
.an-hbar-lbl {{
    font-size: 7px;
    color: rgba(255,255,255,0.3);
    margin-top: 3px;
    height: 10px;
}}
.an-tbar-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}}
.an-tbar-label {{
    font-size: 10px;
    color: rgba(255,255,255,0.6);
    width: 90px;
    text-align: right;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.an-tbar-track {{
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    overflow: hidden;
}}
.an-tbar-fill {{
    height: 100%;
    border-radius: 3px;
}}
.an-tbar-count {{
    font-size: 10px;
    color: rgba(255,255,255,0.5);
    width: 28px;
    text-align: right;
    font-variant-numeric: tabular-nums;
}}
@media (max-width: 768px) {{
    .analytics {{
        grid-template-columns: 1fr;
    }}
    .an-hourly-chart,
    .an-panel-full {{
        grid-column: 1;
    }}
    .an-metrics {{
        grid-column: 1;
        gap: 8px;
    }}
    .an-metric-card {{
        min-width: 70px;
        padding: 8px 6px;
    }}
    .an-metric-value {{
        font-size: 22px;
    }}
}}
.tooltip-trigger {{
    position: relative;
    cursor: help;
    display: inline-block;
}}
.tooltip-content {{
    visibility: hidden;
    position: absolute;
    bottom: 120%;
    left: 50%;
    transform: translateX(-50%);
    background-color: rgba(0, 0, 0, 0.9);
    color: #fff;
    text-align: center;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 10px;
    white-space: normal;
    width: max-content;
    max-width: 200px;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
    z-index: 1000;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}}
.tooltip-trigger:hover .tooltip-content,
.tooltip-trigger:active .tooltip-content {{
    visibility: visible;
    opacity: 1;
}}
</style>
<div class="analytics">
    <div class="an-metrics">
        <div class="an-metric-card">
            <div class="an-metric-value">{total_72h}</div>
            <div class="an-metric-label">Events (72h)</div>
        </div>
        <div class="an-metric-card">
            <div class="an-metric-value">{critical_count}</div>
            <div class="an-metric-label tooltip-trigger">
                Critical Events <span style="opacity:0.6;font-size:10px;">ⓘ</span>
                <div class="tooltip-content">Includes only kinetic events: Airstrike, Missile, and Explosion</div>
            </div>
        </div>
        <div class="an-metric-card">
            <div class="an-metric-value blue">{geo_count}</div>
            <div class="an-metric-label">Geolocated</div>
        </div>
        <div class="an-metric-card">
            <div class="an-metric-value purple">{sources_active}</div>
            <div class="an-metric-label">Active Sources</div>
        </div>
        <div class="an-metric-card">
            <div class="an-metric-value" style="font-size:22px;-webkit-text-fill-color:{trend_color};background:none;">{trend_icon}</div>
            <div class="an-metric-label">Trend</div>
            <span class="an-trend-badge" style="color:{trend_color};border:1px solid {trend_color}33;">{trend_label}</span>
        </div>
    </div>
    <div class="an-panel an-hourly-chart">
        <div class="an-panel-title">Event Activity (last 72h, by hour)</div>
        <div class="an-hbar-wrapper">
            {y_axis_html}
            {grid_lines_html}
            <div class="an-hbar-container">
                {hour_bars}
            </div>
        </div>
    </div>
    <div class="an-panel an-hourly-chart">
        <div class="an-panel-title" style="margin-bottom:4px;">Intensity Trend (72h)
            <span style="float:right;font-size:8px;font-weight:600;color:{trend_color};text-transform:uppercase;">{trend_icon} {trend_label}</span>
        </div>
        {trend_svg}
    </div>
    <div class="an-panel">
        <div class="an-panel-title">Event Types (72h)</div>
        {type_bars if type_bars else no_data}
    </div>
    <div class="an-panel">
        <div class="an-panel-title">Top Affected Locations (72h)</div>
        {loc_bars if loc_bars else no_data}
    </div>
    <div class="an-panel an-panel-full" style="grid-column: 1 / -1;">
        <div class="an-panel-title">Source Activity (72h)</div>
        {source_bars if source_bars else no_data}
    </div>
</div>"""
