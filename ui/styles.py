"""
Custom CSS for the Iran Crisis Monitor dashboard.

Dark theme with responsive layout, source badges, professional styling,
and a clean Liveuamap-inspired aesthetic. No emoji – text-based indicators only.
"""


def get_custom_css() -> str:
    """Return the full CSS stylesheet as a string."""
    return """
<style>
    /* ─── Import Premium Font ─────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ─── Global Overrides ────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Hide Streamlit chrome for clean look */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: rgba(14, 17, 23, 0.95) !important;
        backdrop-filter: blur(10px);
    }

    /* Full-width layout – top padding accounts for Streamlit's fixed header */
    .block-container {
        padding: 3.5rem 1.5rem 1rem 1.5rem !important;
        max-width: 100% !important;
    }

    /* ─── Header Bar ──────────────────────────────────────────── */
    .app-header {
        background: linear-gradient(135deg, #1a1d23 0%, #0e1117 100%);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 0.8rem 1.5rem;
        margin: -1rem -1.5rem 1rem -1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .app-header h1 {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 0;
        color: #fafafa;
        letter-spacing: -0.02em;
        text-transform: uppercase;
    }

    .app-header .header-meta {
        display: flex;
        align-items: center;
        gap: 1rem;
        font-size: 0.78rem;
        color: rgba(255,255,255,0.5);
    }

    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .live-dot {
        width: 7px;
        height: 7px;
        background: #e74c3c;
        border-radius: 50%;
        animation: pulse-dot 1.5s infinite;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.3); }
    }

    .event-count {
        background: rgba(255,255,255,0.06);
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.75rem;
        letter-spacing: 0.02em;
    }

    /* ─── Map Container ───────────────────────────────────────── */
    .map-container {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    }

    .map-container iframe {
        border-radius: 8px;
    }

    /* ─── News Feed ───────────────────────────────────────────── */
    .news-feed-container {
        max-height: 78vh;
        overflow-y: auto;
        padding-right: 4px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.15) transparent;
    }

    .news-feed-container::-webkit-scrollbar {
        width: 4px;
    }
    .news-feed-container::-webkit-scrollbar-track {
        background: transparent;
    }
    .news-feed-container::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.15);
        border-radius: 10px;
    }

    .feed-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0.5rem 0;
        margin-bottom: 0.5rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    /* ─── News Card ───────────────────────────────────────────── */
    .news-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 6px;
        padding: 0.7rem 0.8rem;
        margin-bottom: 0.4rem;
        transition: all 0.2s ease;
        cursor: default;
    }

    .news-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.12);
    }

    .news-card.recent {
        border-left: 3px solid #e74c3c;
        animation: fade-in 0.5s ease;
    }

    @keyframes fade-in {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .news-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.35rem;
        gap: 0.5rem;
    }

    .news-card-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-shrink: 0;
    }

    /* ─── Event Type Indicator (replaces emoji) ───────────────── */
    .type-indicator {
        display: inline-block;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        padding: 0.15rem 0.4rem;
        border-radius: 3px;
        text-transform: uppercase;
        white-space: nowrap;
        line-height: 1.2;
    }

    .time-ago {
        font-size: 0.68rem;
        color: rgba(255, 255, 255, 0.35);
        white-space: nowrap;
    }

    .news-card-title {
        font-size: 0.8rem;
        font-weight: 500;
        color: #e0e0e0;
        line-height: 1.4;
        margin: 0;
    }

    .news-card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 0.4rem;
    }

    /* ─── Source Badges ────────────────────────────────────────── */
    .source-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.12rem 0.45rem;
        border-radius: 3px;
        font-size: 0.6rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .source-aljazeera     { background: rgba(250,159,28,0.15); color: #fa9f1c; }
    .source-apnews        { background: rgba(238,48,36,0.15);  color: #ee3024; }
    .source-reuters       { background: rgba(255,128,0,0.15);  color: #ff8000; }
    .source-jerusalempost { background: rgba(0,59,111,0.2);    color: #5b9bd5; }
    .source-unnews        { background: rgba(0,158,219,0.15);  color: #009edb; }
    .source-bbcnews       { background: rgba(187,25,25,0.15);  color: #e44; }
    .source-cnn           { background: rgba(204,0,0,0.15);    color: #ff4444; }
    .source-liveuamap     { background: rgba(211,84,0,0.15);   color: #d35400; }
    .source-npr           { background: rgba(26,26,46,0.2);    color: #8888cc; }
    .source-default       { background: rgba(255,255,255,0.06);color: #888; }

    .source-link {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.72rem;
        color: rgba(255,255,255,0.85);
        text-decoration: none;
        font-weight: 700;
        letter-spacing: 0.02em;
        padding: 0.2rem 0;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    .source-link:hover {
        color: #fff;
        text-decoration: underline;
    }
    .source-link svg {
        width: 12px;
        height: 12px;
        fill: currentColor;
    }

    /* ─── Severity Dots ───────────────────────────────────────── */
    .severity-bar {
        display: flex;
        gap: 2px;
    }
    .severity-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: rgba(255,255,255,0.12);
    }
    .severity-dot.active { background: #e74c3c; }
    .severity-dot.active.sev-3 { background: #f39c12; }
    .severity-dot.active.sev-2 { background: #f1c40f; }
    .severity-dot.active.sev-1 { background: #2ecc71; }

    /* ─── Location Tag ────────────────────────────────────────── */
    .location-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.65rem;
        color: rgba(255,255,255,0.35);
        margin-top: 0.25rem;
        font-style: italic;
    }

    /* ─── Stats Bar ───────────────────────────────────────────── */
    .stats-bar {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
    }

    .stat-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        padding: 0.25rem 0.55rem;
        border-radius: 4px;
        font-size: 0.7rem;
        color: rgba(255,255,255,0.55);
        font-weight: 500;
    }

    .stat-chip .count {
        font-weight: 700;
        color: #fafafa;
    }

    .stat-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }

    /* ─── Responsive ──────────────────────────────────────────── */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.5rem 0.75rem !important;
        }

        .app-header {
            padding: 0.6rem 0.75rem;
            margin: -0.5rem -0.75rem 0.5rem -0.75rem;
        }

        .app-header h1 {
            font-size: 0.95rem;
        }

        .news-feed-container {
            max-height: 50vh;
        }

        .news-card {
            padding: 0.55rem;
        }
    }

    /* ─── Folium map responsive height ────────────────────────── */
    [data-testid="stIFrame"] {
        min-height: 500px;
    }

    @media (min-width: 769px) {
        [data-testid="stIFrame"] {
            min-height: 75vh;
        }
    }
</style>
"""
