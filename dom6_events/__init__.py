"""
Dominions 6 random-event gold-impact analysis.

Public API
----------
.. autoclass:: Event
.. autoclass:: EventPoolStats
.. autoclass:: ResultRow
.. autofunction:: parse_tsv
.. autofunction:: parse_dm
.. autofunction:: analyze
"""

from __future__ import annotations

from dom6_events.analysis import analyze
from dom6_events.models import Event, EventPoolStats, ResultRow
from dom6_events.parsers import parse_dm, parse_tsv

__all__: list[str] = [
    "Event",
    "EventPoolStats",
    "ResultRow",
    "analyze",
    "parse_dm",
    "parse_tsv",
]
