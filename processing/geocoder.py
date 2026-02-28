"""
Location extraction from news text.

Uses the curated location dictionary from config.locations to find
place-name mentions in free text and return their coordinates.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from config.locations import LOCATIONS, Coord

# Pre-compile patterns: sort by length desc so "Bandar Abbas" matches before "Abbas"
_SORTED_NAMES = sorted(LOCATIONS.keys(), key=len, reverse=True)
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _SORTED_NAMES) + r")\b",
    re.IGNORECASE,
)


def extract_locations(text: str) -> List[Tuple[str, float, float]]:
    """
    Find all known location mentions in *text*.

    Returns list of (canonical_name, lat, lon) tuples, deduplicated.
    """
    seen: set[str] = set()
    results: List[Tuple[str, float, float]] = []

    for match in _PATTERN.finditer(text):
        key = match.group(0).lower().strip()
        if key in seen:
            continue
        seen.add(key)
        coord: Optional[Coord] = LOCATIONS.get(key)
        if coord:
            lat, lon = coord
            results.append((key.title(), lat, lon))

    return results


def extract_primary_location(text: str) -> Optional[Tuple[str, float, float]]:
    """Return the first (most prominent) location in text, or None."""
    locations = extract_locations(text)
    return locations[0] if locations else None
