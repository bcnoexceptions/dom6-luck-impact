"""
Shared constants for Dominions 6 event analysis.

These encode the game mechanics documented on the Illwiki Dom5 random-events
page, plus the filtering heuristics we use to isolate "general random events"
from nation-specific, commander-specific, or site-gated ones.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Province economy
# ---------------------------------------------------------------------------

BASE_PROVINCE_INCOME: Final[int] = 100
"""Approximate base gold income per province, used to convert ``taxboost``
percentage modifiers into one-time gold equivalents."""

# ---------------------------------------------------------------------------
# Rarity / pool weighting
# ---------------------------------------------------------------------------

RELEVANT_RARITIES: Final[frozenset[int]] = frozenset({1, -1, 2, -2})
"""Only random luck-based events are relevant.

- |rarity| == 1 → common (80 % of the pool)
- |rarity| == 2 → uncommon (20 % of the pool)
- Negative rarity → good event; positive → bad event.

Rarity 0 / 5 / 10–15 are story, global, or triggered events — excluded.
"""

COMMON_WEIGHT: Final[int] = 4
"""Pool weight for common events (|rarity| == 1).  4 : 1 = 80 : 20."""

UNCOMMON_WEIGHT: Final[int] = 1
"""Pool weight for uncommon events (|rarity| == 2)."""

# ---------------------------------------------------------------------------
# Luck scale range
# ---------------------------------------------------------------------------

LUCK_SCALE_MIN: Final[int] = -5
"""Minimum Luck scale value (Misfortune 5)."""

LUCK_SCALE_MAX: Final[int] = 5
"""Maximum Luck scale value (Luck 5)."""

# ---------------------------------------------------------------------------
# Scenario parameters
# ---------------------------------------------------------------------------

PROVINCE_COUNTS: Final[tuple[int, ...]] = (10, 20, 30)
"""Province counts to model (small / medium / large empire)."""

# ---------------------------------------------------------------------------
# Event-filtering keywords
# ---------------------------------------------------------------------------

FILTER_KEYWORDS: Final[tuple[str, ...]] = (
    "fullowner",   # nation-specific event
    "fornation",   # nation-specific event
    "monster",     # requires a specific commander in the province
    "unique",      # one-time event — negligible long-run expected value
    "foundsite",   # requires a specific found magic site
    "hiddensite",  # requires a specific hidden magic site
    "nearbysite",  # requires a nearby magic site
    "land 0",      # underwater-only (we model land nations)
)
"""Substrings whose presence in an event's requirements (or DM block) causes
the event to be excluded from the general random-event analysis."""
