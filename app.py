"""
Iran Crisis Monitor – Main Streamlit Application

Real-time monitoring dashboard that aggregates events from 9 news sources,
displays them on an interactive dark-themed map, and shows a live news feed.

Uses @st.fragment for partial refresh — map + feed update without full-page reload.
Map and feed are rendered in a single HTML component for hover interaction.

Usage:
    streamlit run app.py
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from config.settings import (
    APP_TITLE,
    REFRESH_INTERVAL_SECONDS,
    SOURCES,
    SOURCES_BY_NAME,
)
from models.events import EventStore, NewsEvent
from processing.deduplicator import deduplicate, deduplicate_against_existing
from processing.summarizer import generate_summary
from scrapers import ALL_SCRAPERS
from ui.dashboard_component import build_dashboard_html
from ui.analytics_component import build_analytics_html
from ui.styles import get_custom_css
from utils.logger import get_logger

logger = get_logger("app")

# ──────────────────────────────────────────────────────────────────────────
# Page config (must be the first Streamlit command)
# ──────────────────────────────────────────────────────────────────────────

from pathlib import Path

_FAVICON = Path(__file__).parent / "assets" / "favicon.png"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=str(_FAVICON) if _FAVICON.exists() else "📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject custom CSS + hide deploy button
st.markdown(get_custom_css(), unsafe_allow_html=True)
st.markdown(
    """
    <style>
    /* Hide Streamlit chrome and kill ALL top spacing */
    [data-testid="stToolbar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; height: 0 !important; min-height: 0 !important; }
    .block-container { padding-top: 0 !important; margin-top: 0 !important; }
    [data-testid="stAppViewContainer"] { padding-top: 0 !important; }
    [data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; margin-top: 0 !important; }
    .appview-container { margin-top: 0 !important; padding-top: 0 !important; }
    section[data-testid="stMain"] > div { padding-top: 0 !important; }
    .stApp > header + div { margin-top: 0 !important; }
    .footer-copy {
        font-size: 14px;
        color: rgba(250, 250, 250, 0.6);
    }
    @media (max-width: 768px) {
        .footer-copy { text-align: center; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ──────────────────────────────────────────────────────────────────────────

if "event_store" not in st.session_state:
    st.session_state.event_store = EventStore()

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0.0

if "scrape_errors" not in st.session_state:
    st.session_state.scrape_errors = []


# ──────────────────────────────────────────────────────────────────────────
# Scraping logic
# ──────────────────────────────────────────────────────────────────────────

def _run_all_scrapers() -> list[NewsEvent]:
    """Execute all scrapers in parallel and return merged, deduplicated events."""
    all_events: list[NewsEvent] = []
    errors: list[str] = []

    # Only run scrapers that are enabled in the configuration
    scrapers = [
        cls() for cls in ALL_SCRAPERS 
        if cls.SOURCE_NAME in SOURCES_BY_NAME and SOURCES_BY_NAME[cls.SOURCE_NAME].enabled
    ]

    with ThreadPoolExecutor(max_workers=len(scrapers) or 1) as pool:
        futures = {pool.submit(s.scrape): s for s in scrapers}
        try:
            for future in as_completed(futures, timeout=60):
                scraper = futures[future]
                try:
                    events = future.result()
                    all_events.extend(events)
                    logger.info(
                        "%s → %d events", scraper.SOURCE_NAME, len(events)
                    )
                except Exception as exc:
                    errors.append(f"{scraper.SOURCE_NAME}: {exc}")
                    logger.error("Scraper %s error: %s", scraper.SOURCE_NAME, exc)
        except TimeoutError:
            for future, scraper in futures.items():
                if not future.done():
                    future.cancel()
                    errors.append(f"{scraper.SOURCE_NAME}: timed out")
                    logger.warning("%s timed out", scraper.SOURCE_NAME)

    all_events = deduplicate(all_events)

    # Second pass: drop events that duplicate something already in the store
    existing = st.session_state.event_store.get_all()
    if existing:
        all_events = deduplicate_against_existing(all_events, existing)

    st.session_state.scrape_errors = errors
    return all_events


def _do_refresh() -> None:
    """Fetch fresh data from all sources."""
    events = _run_all_scrapers()
    new_count = st.session_state.event_store.add_many(events)
    st.session_state.last_refresh = time.time()
    logger.info(
        "Refresh complete: %d new events (total: %d)",
        new_count,
        st.session_state.event_store.count(),
    )


# ──────────────────────────────────────────────────────────────────────────
# Initial data load
# ──────────────────────────────────────────────────────────────────────────

if st.session_state.last_refresh == 0.0:
    with st.spinner("Loading initial data from sources..."):
        _do_refresh()


# ──────────────────────────────────────────────────────────────────────────
# Static header
# ──────────────────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div class="app-header">
        <div>
            <h1 style="margin-bottom:2px;">{APP_TITLE}</h1>
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.45);font-weight:400;letter-spacing:0.02em;line-height:1.5;">
                Near real-time news aggregation from {len([s for s in SOURCES if s.enabled])} sources:
                {' · '.join(f'<a href="{s.website_url}" target="_blank" style="color:rgba(255,255,255,0.55);text-decoration:none;border-bottom:1px dotted rgba(255,255,255,0.25);">{s.name}</a>' for s in SOURCES if s.enabled)}
                <br/>Map shows last 24h · Data refreshes every ~60s · Hover a card to locate on map · Click filters to narrow view
            </div>
        </div>
        <div class="header-meta">
            <span class="live-indicator">
                <span class="live-dot"></span> LIVE
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────
# Auto-refreshing fragment – only this section re-renders every 60s
# ──────────────────────────────────────────────────────────────────────────

@st.fragment(run_every=REFRESH_INTERVAL_SECONDS)
def live_dashboard():
    """Fragment that auto-refreshes the map and news feed."""

    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= REFRESH_INTERVAL_SECONDS:
        _do_refresh()

    store: EventStore = st.session_state.event_store
    all_events = store.get_all()
    map_events = store.get_all(with_location_only=True)

    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")

    # ── Status line ───────────────────────────────────────────────
    from ui.dashboard_component import MAP_MAX_AGE_HOURS
    now = datetime.now(timezone.utc)
    recent_count = sum(
        1 for ev in all_events
        if ev.age_minutes(now) <= MAP_MAX_AGE_HOURS * 60
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem;">
            <span class="event-count">
                {len(all_events)} events total &middot;
                {recent_count} in last {MAP_MAX_AGE_HOURS}h &middot;
                {len(map_events)} geolocated
            </span>
            <span style="font-size:0.7rem;color:rgba(255,255,255,0.35);">
                Last update: {now_utc}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── AI summary ─────────────────────────────────────────────────
    summary_text = generate_summary(all_events)

    # ── Unified map + feed component ──────────────────────────────
    # We pass the default desktop height explicitly so Streamlit doesn't render voids.
    # For mobile screens, an overriding CSS selector inside ui/styles.py expands it.
    dashboard_html = build_dashboard_html(
        all_events=all_events,
        geo_events=map_events,
        component_height=720,
        summary_text=summary_text,
    )
    # Streamlit wrapper iframe 
    components.html(dashboard_html, height=730, scrolling=False)

    # ── Analytics section ──────────────────────────────────────────
    st.markdown(
        '<div style="margin-top:0.5rem;margin-bottom:0.3rem;">'
        '<span style="font-size:0.8rem;font-weight:700;color:rgba(255,255,255,0.5);'
        'text-transform:uppercase;letter-spacing:0.1em;">'
        'Analytics &amp; Insights</span></div>',
        unsafe_allow_html=True,
    )
    analytics_html = build_analytics_html(all_events)
    st.markdown(analytics_html, unsafe_allow_html=True)

    # ── Error reporting ───────────────────────────────────────────
    if st.session_state.scrape_errors:
        with st.expander(
            f"{len(st.session_state.scrape_errors)} source error(s)",
            expanded=False,
        ):
            for err in st.session_state.scrape_errors:
                st.caption(err)


# Run the fragment
live_dashboard()

# ──────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────

st.markdown("---")
source_links = " · ".join(
    f"[{s.short_name}]({s.website_url})" for s in SOURCES if s.enabled
)
st.caption(f"Data sources: {source_links}")
st.caption(
    "Data refreshes automatically every ~60 seconds. "
    "This is an aggregation tool – all content belongs to the original publishers."
)
st.caption("&copy; 2026 created by mkrolczyk", text_alignment="left")