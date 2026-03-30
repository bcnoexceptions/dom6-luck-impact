"""Helpers for parsing gem-related event effects.

This module computes expected gem impact from effect tags by replacing dice
rolls with their average values.
"""

from __future__ import annotations

import re
from typing import Final


_VIS_AVERAGES: Final[dict[str, float]] = {
    "1d3vis": 2.0,
    "1d6vis": 3.5,
    "2d4vis": 5.0,
    "2d6vis": 7.0,
    "3d6vis": 10.5,
    "4d6vis": 14.0,
    "force1d3vis": 2.0,
    "force1d6vis": 3.5,
    "force2d4vis": 5.0,
    "force2d6vis": 7.0,
    "force3d6vis": 10.5,
    "force4d6vis": 14.0,
}

_VIS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![a-z0-9_])#?(force(?:1d3|1d6|2d4|2d6|3d6|4d6)vis|(?:1d3|1d6|2d4|2d6|3d6|4d6)vis)(?:\s+([A-Za-z0-9_]+))?"
)

_GEMLOSS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![a-z0-9_])#?(gemloss|gemlosssmall|gemlosslarge)(?:\s+(-?\d+))?"
)

_GEMLOSS_BASE: Final[dict[str, float]] = {
    "gemloss": -10.5,
    "gemlosssmall": -7.0,
    "gemlosslarge": -14.0,
}


def _is_all_gems(token: str | None) -> bool:
    return (token or "").lower() == "all"


def _gemloss_value(tag: str, arg: str | None) -> float:
    if arg in {"53", "56"}:
        return -28.0
    return _GEMLOSS_BASE[tag]


def parse_expected_gem_impact(effects: str) -> float:
    """Return expected net gem impact encoded in *effects*."""
    total: float = 0.0

    for match in _VIS_PATTERN.finditer(effects):
        tag: str = match.group(1)
        gem_type: str | None = match.group(2)
        multiplier: float = 8.0 if _is_all_gems(gem_type) else 1.0
        total += _VIS_AVERAGES[tag] * multiplier

    for match in _GEMLOSS_PATTERN.finditer(effects):
        tag: str = match.group(1)
        arg: str | None = match.group(2)
        total += _gemloss_value(tag, arg)

    return total
