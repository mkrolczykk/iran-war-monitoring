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
)
from models.events import EventStore, NewsEvent
from processing.deduplicator import deduplicate
from scrapers import ALL_SCRAPERS
from ui.dashboard_component import build_dashboard_html
from ui.styles import get_custom_css
from utils.logger import get_logger

logger = get_logger("app")

# ──────────────────────────────────────────────────────────────────────────
# Page config (must be the first Streamlit command)
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject custom CSS + hide deploy button
st.markdown(get_custom_css(), unsafe_allow_html=True)
st.markdown(
    """
    <style>
    /* Hide Streamlit deploy button and reduce top gap */
    [data-testid="stToolbar"] { display: none !important; }
    header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; padding: 0 !important; }
    .block-container { padding-top: 1rem !important; }
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

    scrapers = [cls() for cls in ALL_SCRAPERS]

    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
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
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.45);font-weight:400;letter-spacing:0.02em;">
                Real-time aggregation from {len(SOURCES)} news sources · Map shows last 8h
                · Hover a card to locate on map · Click filters to narrow view
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

    # ── Unified map + feed component ──────────────────────────────
    dashboard_html = build_dashboard_html(
        all_events=all_events,
        geo_events=map_events,
        component_height=720,
    )
    components.html(dashboard_html, height=730, scrolling=False)

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
    f"[{s.short_name}]({s.url})" for s in SOURCES
)
st.caption(f"Sources: {source_links}")
st.caption(
    "Data refreshes automatically every ~60 seconds. "
    "This is an aggregation tool – all content belongs to the original publishers."
)
