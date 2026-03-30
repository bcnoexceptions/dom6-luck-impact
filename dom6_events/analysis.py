"""
Analysis engine for Dominions 6 random-event gold impact.

The pipeline has three stages:

1. **Pool statistics** — for each Luck scale, partition events into good / bad
   pools and compute weighted-average gold and landgold per event.
2. **Event frequency** — for a given (provinces, luck_scale) pair, compute how
   many random events fire per turn (4 checks with base rates, scale modifier,
   3 % floor, 4th-check halving).
3. **Expected value** — multiply pool averages by event frequency to get
   per-turn gold and landgold expectations.
"""

from __future__ import annotations

from typing import Callable, Sequence

from dom6_events.constants import (
    LUCK_SCALE_MAX,
    LUCK_SCALE_MIN,
    PROVINCE_COUNTS,
)
from dom6_events.models import Event, EventPoolStats, ResultRow


# ---------------------------------------------------------------------------
# Weighted average helper
# ---------------------------------------------------------------------------

def _weighted_average(
    events: Sequence[Event],
    value_fn: Callable[[Event], float],
) -> float:
    """Weighted average of *value_fn* over *events*, using each event's
    :pyattr:`~Event.pool_weight`.  Returns ``0.0`` for an empty sequence."""
    total_value: float = 0.0
    total_weight: float = 0.0
    for ev in events:
        w: int = ev.pool_weight
        total_value += value_fn(ev) * w
        total_weight += w
    return total_value / total_weight if total_weight else 0.0


# ---------------------------------------------------------------------------
# Stage 1 — pool statistics (per-scale, province-independent)
# ---------------------------------------------------------------------------

def _partition_pool(
    all_events: Sequence[Event],
    luck_scale: int,
) -> tuple[list[Event], list[Event]]:
    """Split *all_events* into (good, bad) lists available at *luck_scale*."""
    good: list[Event] = []
    bad: list[Event] = []
    for ev in all_events:
        if not ev.available_at(luck_scale):
            continue
        (good if ev.is_good else bad).append(ev)
    return good, bad


def _good_bad_probability(luck_scale: int) -> tuple[float, float]:
    """Return ``(p_good, p_bad)`` for a given Luck scale.

    ``P(good) = 50 % + luck_scale × 10 %``, clamped to [0, 1].
    """
    p_good: float = min(max(0.50 + luck_scale * 0.10, 0.0), 1.0)
    return p_good, 1.0 - p_good


def compute_pool_stats(
    all_events: Sequence[Event],
    luck_scale: int,
) -> EventPoolStats:
    """Compute weighted-average gold/landgold for the good and bad pools at
    *luck_scale*, and combine them using the good/bad probability split."""
    good, bad = _partition_pool(all_events, luck_scale)
    p_good, p_bad = _good_bad_probability(luck_scale)

    avg_gold_good: float = _weighted_average(good, lambda e: e.gold_value)
    avg_gold_bad: float = _weighted_average(bad, lambda e: e.gold_value)
    avg_landgold_good: float = _weighted_average(
        good, lambda e: float(e.landgold)
    )
    avg_landgold_bad: float = _weighted_average(
        bad, lambda e: float(e.landgold)
    )
    avg_gems_good: float = _weighted_average(good, lambda e: e.gems)
    avg_gems_bad: float = _weighted_average(bad, lambda e: e.gems)

    return EventPoolStats(
        luck_scale=luck_scale,
        p_good=p_good,
        p_bad=p_bad,
        good_pool_size=len(good),
        bad_pool_size=len(bad),
        avg_gold_good=avg_gold_good,
        avg_gold_bad=avg_gold_bad,
        avg_gold_per_event=p_good * avg_gold_good + p_bad * avg_gold_bad,
        avg_landgold_good=avg_landgold_good,
        avg_landgold_bad=avg_landgold_bad,
        avg_landgold_per_event=(
            p_good * avg_landgold_good + p_bad * avg_landgold_bad
        ),
        avg_gems_good=avg_gems_good,
        avg_gems_bad=avg_gems_bad,
        avg_gems_per_event=(p_good * avg_gems_good + p_bad * avg_gems_bad),
    )


# ---------------------------------------------------------------------------
# Stage 2 — event frequency
# ---------------------------------------------------------------------------

#: Base percentage rates for the four per-turn event checks.
#: Checks 2–4 are province-count dependent; see ``_check_base_rate``.
_FIXED_BASE_RATE: int = 15

#: Multipliers for province-dependent checks (indices 1, 2, 3).
_PROVINCE_MULTIPLIERS: tuple[int, ...] = (3, 2, 1)

#: Additive constant for province-dependent checks.
_PROVINCE_ADDEND: int = 2


def _check_base_rates(provinces: int) -> tuple[float, float, float, float]:
    """Return the four base-percentage rates before scale modifiers."""
    return (
        float(_FIXED_BASE_RATE),
        float(_PROVINCE_MULTIPLIERS[0] * provinces + _PROVINCE_ADDEND),
        float(_PROVINCE_MULTIPLIERS[1] * provinces + _PROVINCE_ADDEND),
        float(_PROVINCE_MULTIPLIERS[2] * provinces + _PROVINCE_ADDEND),
    )


def expected_events_per_turn(provinces: int, luck_scale: int) -> float:
    """Expected number of random events per turn.

    Both Luck and Misfortune increase event frequency by +5 % per point
    (``abs(luck_scale)``).  The 4th check is halved after applying the floor.
    Minimum rate per check is 3 % (before the halving).
    """
    scale_modifier: int = abs(luck_scale) * 5
    base_rates: tuple[float, float, float, float] = _check_base_rates(
        provinces
    )

    total: float = 0.0
    for i, base in enumerate(base_rates):
        rate: float = min(max(base + scale_modifier, 3.0), 100.0)
        if i == 3:
            rate /= 2.0  # 4th check halved
        total += rate / 100.0
    return total


# ---------------------------------------------------------------------------
# Stage 3 — assemble results
# ---------------------------------------------------------------------------

def analyze(all_events: Sequence[Event]) -> list[ResultRow]:
    """Run the full analysis across all Luck scales and province counts.

    Returns one :class:`ResultRow` per (luck_scale, provinces) pair, ordered
    by provinces ascending, then luck_scale ascending.
    """
    results: list[ResultRow] = []

    for provinces in PROVINCE_COUNTS:
        for luck_scale in range(LUCK_SCALE_MIN, LUCK_SCALE_MAX + 1):
            pool: EventPoolStats = compute_pool_stats(all_events, luck_scale)
            ev_per_turn: float = expected_events_per_turn(
                provinces, luck_scale
            )
            results.append(ResultRow(
                pool=pool,
                provinces=provinces,
                expected_events_per_turn=ev_per_turn,
                expected_gold_per_turn=ev_per_turn * pool.avg_gold_per_event,
                expected_gems_per_turn=ev_per_turn * pool.avg_gems_per_event,
                expected_landgold_per_turn=(
                    ev_per_turn * pool.avg_landgold_per_event
                ),
            ))

    return results
