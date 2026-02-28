"""
Event-type classifier based on keyword matching.

Maps headline / summary text to the appropriate EventType enum value.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from models.events import EventType

# Ordered by priority – first match wins
_RULES: List[Tuple[EventType, re.Pattern]] = [
    (EventType.AIRSTRIKE, re.compile(
        r"airstrike|air\s*strike|bomb(?:ing|ed|s)|strikes?\s+on|struck|"
        r"sortie|fighter\s*jet|warplane|b-2|stealth|bunker\s*buster",
        re.IGNORECASE,
    )),
    (EventType.MISSILE, re.compile(
        r"missile|ballistic|cruise\s*missile|intercept|iron\s*dome|"
        r"patriot|arrow\s*system|thaad|s-?300|launch(?:ed|es)?.*(?:missile|rocket)|"
        r"rocket|drone\s*strike|drone\s*attack|UAV",
        re.IGNORECASE,
    )),
    (EventType.EXPLOSION, re.compile(
        r"explosion|blast|detonat|explod|boom|fire\b|burning|"
        r"smoke\s*(?:rising|seen|billowing)|damage",
        re.IGNORECASE,
    )),
    (EventType.ALERT, re.compile(
        r"siren|alert|warning|shelter|evacuat|airspace\s*clos|"
        r"take\s*cover|emergency|no-fly\s*zone",
        re.IGNORECASE,
    )),
    (EventType.MILITARY_MOVEMENT, re.compile(
        r"military\s*movement|troop|deploy|naval|carrier|fleet|"
        r"aircraft\s*carrier|destroyer|submarine|convoy|mobiliz|"
        r"operation\b|combat\s*operation|regiment|battalion|"
        r"pentagon|defense\s*minister|IDF|IRGC|5th\s*fleet",
        re.IGNORECASE,
    )),
    (EventType.HUMANITARIAN, re.compile(
        r"casualt|killed|dead|wounded|injur|hospital|refugee|"
        r"humanitarian|civilian|school|children|rescue|aid\b|red\s*cross|"
        r"red\s*crescent|relief",
        re.IGNORECASE,
    )),
    (EventType.POLITICAL, re.compile(
        r"sanction|diplomat|UN\b|united\s*nations|security\s*council|"
        r"president\b|prime\s*minister|foreign\s*minister|condemn|"
        r"statement|ceasefire|negotiat|peace\s*talk|resolution|"
        r"urge.*restraint|calls\s+on|appeals?\s+to",
        re.IGNORECASE,
    )),
]


def categorize_event(title: str, summary: str = "") -> EventType:
    """
    Classify an event by scanning title (priority) then summary.
    Returns the first matching EventType, or OTHER.
    """
    combined = f"{title} {summary}"
    for event_type, pattern in _RULES:
        if pattern.search(combined):
            return event_type
    return EventType.OTHER


def estimate_severity(title: str, summary: str = "") -> int:
    """
    Heuristic severity score 1-5.
    Higher for confirmed strikes, casualties; lower for political statements.
    """
    combined = f"{title} {summary}".lower()

    score = 3  # default

    # Escalate
    if re.search(r"killed|dead|casualt|mass|catastroph", combined):
        score = 5
    elif re.search(r"airstrike|struck|missile\s*hit|explosion", combined):
        score = 4
    elif re.search(r"launch|intercept|siren|alert", combined):
        score = 4

    # De-escalate
    if re.search(r"condemn|urge|statement|negotiat|diplomat", combined):
        score = min(score, 2)
    if re.search(r"suspend.*flight|close.*airspace", combined):
        score = min(score, 3)

    return max(1, min(5, score))
