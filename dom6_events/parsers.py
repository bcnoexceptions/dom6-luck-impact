"""
Parsers for Dominions 6 event data files.

Two formats are supported:

* **TSV** — the base-game ``events.tsv`` export (tab-separated, one row per
  event, columns: id, name, rarity, description, requirements, effects, end).
* **DM** — Dominions mod files (``#newevent … #end`` blocks with directives
  like ``#rarity``, ``#gold``, ``#req_luck``, etc.).

Both parsers apply the same filtering and rarity criteria, returning only
general random events that have at least one gold-related effect.
"""

from __future__ import annotations

import csv
import re

from dom6_events.constants import (
    FILTER_KEYWORDS,
    LUCK_SCALE_MAX,
    LUCK_SCALE_MIN,
    RELEVANT_RARITIES,
)
from dom6_events.models import Event


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _should_filter(text: str) -> bool:
    """Return ``True`` if *text* contains any substring that marks an event as
    non-general (nation-specific, commander-gated, site-gated, etc.)."""
    return any(kw in text for kw in FILTER_KEYWORDS)


def _parse_luck_range(
    requirements: str,
    luck_prefix: str = "luck",
    unluck_prefix: str = "unluck",
) -> tuple[int, int]:
    """Determine the Luck-scale availability window from requirement text.

    Returns ``(luck_min, luck_max)`` — the event fires when
    ``luck_min <= scale <= luck_max``.

    Rules:

    * ``luck N``   → requires Luck ≥ N   → sets *luck_min* = N.
    * ``unluck N`` → requires Misfortune ≥ N, i.e. Luck ≤ −N
                   → sets *luck_max* = −N.
    * ``unluck -1`` → Luck ≤ 1 (very permissive).
    * No requirement → available at all scales (−5 … +5).
    """
    luck_min: int = LUCK_SCALE_MIN
    luck_max: int = LUCK_SCALE_MAX

    # "luck N" — negative lookbehind prevents matching inside "unluck"
    luck_match: re.Match[str] | None = re.search(
        rf"(?<![a-z]){re.escape(luck_prefix)}\s+(-?\d+)", requirements
    )
    if luck_match:
        luck_min = max(luck_min, int(luck_match.group(1)))

    # "unluck N" — requires Misfortune ≥ N ⟹ Luck ≤ −N
    unluck_match: re.Match[str] | None = re.search(
        rf"{re.escape(unluck_prefix)}\s+(-?\d+)", requirements
    )
    if unluck_match:
        luck_max = min(luck_max, -int(unluck_match.group(1)))

    return luck_min, luck_max


def _parse_int_field(text: str, prefix: str) -> int:
    """Extract an integer value after *prefix* in *text*, or return 0.

    Handles negative values.  *prefix* is escaped for safe regex use, so
    callers may pass raw strings like ``"gold"`` or ``"#gold"``.
    """
    match: re.Match[str] | None = re.search(
        rf"{re.escape(prefix)}\s+(-?\d+)", text
    )
    return int(match.group(1)) if match else 0


def _build_event(
    rarity: int,
    requirements: str,
    effects: str,
    luck_prefix: str = "luck",
    unluck_prefix: str = "unluck",
    gold_prefix: str = "gold",
    landgold_prefix: str = "landgold",
    taxboost_prefix: str = "taxboost",
) -> Event | None:
    """Construct an :class:`Event` from raw text fields, or ``None`` if the
    event should be skipped (wrong rarity, filtered, impossible luck range,
    or no gold-related effect)."""
    if rarity not in RELEVANT_RARITIES:
        return None
    if _should_filter(requirements):
        return None

    luck_min, luck_max = _parse_luck_range(
        requirements, luck_prefix, unluck_prefix
    )
    if luck_min > luck_max:
        return None  # impossible range

    event = Event(
        rarity=rarity,
        luck_min=luck_min,
        luck_max=luck_max,
        gold=_parse_int_field(effects, gold_prefix),
        landgold=_parse_int_field(effects, landgold_prefix),
        taxboost=_parse_int_field(effects, taxboost_prefix),
    )
    return event if event.has_gold_effect() else None


# ---------------------------------------------------------------------------
# Public file parsers
# ---------------------------------------------------------------------------

def parse_tsv(file_path: str) -> list[Event]:
    """Parse a base-game ``events.tsv`` and return qualifying events.

    The TSV is expected to have columns: ``id``, ``name``, ``rarity``,
    ``description``, ``requirements``, ``effects``, ``end``.
    """
    events: list[Event] = []

    with open(file_path, "r", encoding="utf-8") as fh:
        reader: csv.DictReader[str] = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            event: Event | None = _build_event(
                rarity=int(row["rarity"]),
                requirements=row.get("requirements", "") or "",
                effects=row.get("effects", "") or "",
            )
            if event is not None:
                events.append(event)

    return events


def parse_dm(file_path: str) -> list[Event]:
    """Parse a ``.dm`` mod file and return qualifying events.

    Events are extracted from ``#newevent … #end`` blocks.  The DM format uses
    ``#rarity``, ``#gold``, ``#req_luck`` / ``#req_unluck``, etc.
    """
    events: list[Event] = []

    with open(file_path, "r", encoding="utf-8") as fh:
        content: str = fh.read()

    blocks: list[str] = re.findall(r"#newevent.*?#end", content, re.DOTALL)

    for block in blocks:
        rarity_match: re.Match[str] | None = re.search(
            r"#rarity\s+(-?\d+)", block
        )
        if rarity_match is None:
            continue

        # In DM files the entire block serves as both requirements and effects
        event: Event | None = _build_event(
            rarity=int(rarity_match.group(1)),
            requirements=block,
            effects=block,
            luck_prefix="#req_luck",
            unluck_prefix="#req_unluck",
            gold_prefix="#gold",
            landgold_prefix="#landgold",
            taxboost_prefix="#taxboost",
        )
        if event is not None:
            events.append(event)

    return events
