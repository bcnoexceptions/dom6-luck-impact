"""
Domain models for Dominions 6 event analysis.

``Event``  — a single parsed random event with its gold-related effects and
             the Luck-scale range over which it can fire.
``EventPoolStats`` — weighted-average statistics for a pool of events at a
                     single Luck scale (before multiplying by province count).
``ResultRow`` — one row of final output: a (luck_scale, province_count) pair
                with all computed expected values.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import IO, Sequence

from dom6_events.constants import (
    BASE_PROVINCE_INCOME,
    COMMON_WEIGHT,
    UNCOMMON_WEIGHT,
)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Event:
    """A parsed random event with its effects and luck-scale availability.

    Attributes:
        rarity:   Raw rarity from the data file.  Sign encodes good (< 0) vs
                  bad (> 0); absolute value encodes common (1) vs uncommon (2).
        luck_min: Minimum Luck scale at which this event can fire (inclusive).
        luck_max: Maximum Luck scale at which this event can fire (inclusive).
        gold:     One-time gold granted (negative = gold lost).
        landgold: Permanent province-income change per turn.
        taxboost: One-turn percentage modifier on province income
                  (e.g. ``taxboost 100`` → +100 % income for one turn).
    """

    rarity: int
    luck_min: int
    luck_max: int
    gold: int
    landgold: int
    taxboost: int

    # -- derived properties --------------------------------------------------

    @property
    def is_good(self) -> bool:
        """Good events have negative rarity (per Illwiki convention)."""
        return self.rarity < 0

    @property
    def is_common(self) -> bool:
        """Common events have ``|rarity| == 1``; uncommon have ``|rarity| == 2``."""
        return abs(self.rarity) == 1

    @property
    def pool_weight(self) -> int:
        """Pool sampling weight (common 4× vs uncommon 1×)."""
        return COMMON_WEIGHT if self.is_common else UNCOMMON_WEIGHT

    @property
    def gold_value(self) -> float:
        """Total immediate gold impact, converting *taxboost* to a one-time
        gold equivalent.

        ``taxboost 100`` on a province earning *BASE_PROVINCE_INCOME* gold
        yields ``+BASE_PROVINCE_INCOME`` extra gold for that turn.
        """
        return self.gold + (self.taxboost * BASE_PROVINCE_INCOME / 100.0)

    # -- predicates ----------------------------------------------------------

    def available_at(self, luck_scale: int) -> bool:
        """Whether this event can fire at *luck_scale*."""
        return self.luck_min <= luck_scale <= self.luck_max

    def has_gold_effect(self) -> bool:
        """Whether this event carries any gold-related effect."""
        return self.gold != 0 or self.landgold != 0 or self.taxboost != 0


# ---------------------------------------------------------------------------
# EventPoolStats — per-scale, province-independent averages
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EventPoolStats:
    """Weighted-average statistics for the good and bad event pools at a
    single Luck scale.

    These numbers are independent of province count and are computed once per
    Luck scale, then reused for every province-count scenario.

    Attributes:
        luck_scale:             The Luck scale these stats describe.
        p_good:                 Probability an event is good at this scale.
        p_bad:                  Probability an event is bad at this scale.
        good_pool_size:         Number of good events available.
        bad_pool_size:          Number of bad events available.
        avg_gold_good:          Weighted-average gold_value across good events.
        avg_gold_bad:           Weighted-average gold_value across bad events.
        avg_gold_per_event:     Combined average (p_good × good + p_bad × bad).
        avg_landgold_good:      Weighted-average landgold across good events.
        avg_landgold_bad:       Weighted-average landgold across bad events.
        avg_landgold_per_event: Combined average landgold.
    """

    luck_scale: int
    p_good: float
    p_bad: float
    good_pool_size: int
    bad_pool_size: int
    avg_gold_good: float
    avg_gold_bad: float
    avg_gold_per_event: float
    avg_landgold_good: float
    avg_landgold_bad: float
    avg_landgold_per_event: float


# ---------------------------------------------------------------------------
# ResultRow — one row of CSV output
# ---------------------------------------------------------------------------

_CSV_FIELDS: tuple[str, ...] = (
    "Luck Scale",
    "Provinces",
    "Expected Events/Turn",
    "Expected Gold/Turn",
    "Expected Landgold/Turn",
    "Avg Gold per Good Event",
    "Avg Gold per Bad Event",
    "Avg Gold per Event",
    "Avg Landgold per Good Event",
    "Avg Landgold per Bad Event",
    "Avg Landgold per Event",
)


@dataclass(frozen=True, slots=True)
class ResultRow:
    """One row of output: a (luck_scale, provinces) combination with all
    computed averages and expected per-turn values.

    Attributes:
        pool:                    The pre-computed pool stats for this Luck scale.
        provinces:               Number of provinces in the scenario.
        expected_events_per_turn: Expected random events per turn.
        expected_gold_per_turn:  Expected gold per turn from events.
        expected_landgold_per_turn: Expected permanent income change per turn.
    """

    pool: EventPoolStats
    provinces: int
    expected_events_per_turn: float
    expected_gold_per_turn: float
    expected_landgold_per_turn: float

    def as_csv_dict(self) -> dict[str, int | float]:
        """Return an ordered dict suitable for :class:`csv.DictWriter`."""
        p: EventPoolStats = self.pool
        return {
            "Luck Scale": p.luck_scale,
            "Provinces": self.provinces,
            "Expected Events/Turn": round(self.expected_events_per_turn, 4),
            "Expected Gold/Turn": round(self.expected_gold_per_turn, 2),
            "Expected Landgold/Turn": round(self.expected_landgold_per_turn, 4),
            "Avg Gold per Good Event": round(p.avg_gold_good, 2),
            "Avg Gold per Bad Event": round(p.avg_gold_bad, 2),
            "Avg Gold per Event": round(p.avg_gold_per_event, 2),
            "Avg Landgold per Good Event": round(p.avg_landgold_good, 2),
            "Avg Landgold per Bad Event": round(p.avg_landgold_bad, 2),
            "Avg Landgold per Event": round(p.avg_landgold_per_event, 2),
        }

    @staticmethod
    def csv_fieldnames() -> tuple[str, ...]:
        """Column headers for the output CSV."""
        return _CSV_FIELDS

    @staticmethod
    def write_csv(
        results: Sequence[ResultRow],
        dest: str | IO[str],
    ) -> None:
        """Write *results* as CSV to *dest* (a file path or open file).

        If *dest* is a string it is treated as a file path; otherwise it must
        be a writable text stream.
        """
        if not results:
            return

        rows: list[dict[str, int | float]] = [r.as_csv_dict() for r in results]
        fieldnames: list[str] = list(_CSV_FIELDS)

        if isinstance(dest, str):
            with open(dest, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            writer = csv.DictWriter(dest, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
