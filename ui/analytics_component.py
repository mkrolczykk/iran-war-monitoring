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

    # ── Hourly activity (last 24 h) ──────────────────────────────
    hourly: dict[int, int] = {}
    for h in range(24):
        hourly[h] = 0
    cutoff_24h = now - timedelta(hours=24)
    recent_events = [ev for ev in events if ev.timestamp >= cutoff_24h]

    for ev in recent_events:
        hours_ago = int((now - ev.timestamp).total_seconds() / 3600)
        if 0 <= hours_ago < 24:
            hourly[hours_ago] += 1

    max_hourly = max(hourly.values()) if hourly else 1
    max_hourly = max(max_hourly, 1)

    hour_bars = ""
    for h in range(23, -1, -1):
        count = hourly[h]
        pct = (count / max_hourly) * 100
        t = now - timedelta(hours=h)
        label = t.strftime("%H:%M")
        opacity = 0.3 if count == 0 else 0.7 + 0.3 * (count / max_hourly)
        hour_bars += (
            f'<div class="an-hbar-col" title="{label} UTC — {count} events">'
            f'<div class="an-hbar-fill" style="height:{max(pct, 2)}%;opacity:{opacity:.2f};"></div>'
            f'<span class="an-hbar-lbl">{label if h % 3 == 0 else ""}</span>'
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
    total_24h = len(recent_events)
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
.an-hbar-container {{
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 80px;
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
</style>
<div class="analytics">
    <div class="an-metrics">
        <div class="an-metric-card">
            <div class="an-metric-value">{total_24h}</div>
            <div class="an-metric-label">Events (24h)</div>
        </div>
        <div class="an-metric-card">
            <div class="an-metric-value">{critical_count}</div>
            <div class="an-metric-label">Critical Events</div>
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
        <div class="an-panel-title">Event Activity (last 24h, by hour)</div>
        <div class="an-hbar-container">
            {hour_bars}
        </div>
    </div>
    <div class="an-panel">
        <div class="an-panel-title">Event Types (24h)</div>
        {type_bars if type_bars else no_data}
    </div>
    <div class="an-panel">
        <div class="an-panel-title">Source Activity (24h)</div>
        {source_bars if source_bars else no_data}
    </div>
    <div class="an-panel an-panel-full" style="grid-column: 1 / -1;">
        <div class="an-panel-title">Top Affected Locations (24h)</div>
        {loc_bars if loc_bars else no_data}
    </div>
</div>"""
