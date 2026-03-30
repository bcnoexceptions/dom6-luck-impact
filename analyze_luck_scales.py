#!/usr/bin/env python3
"""
Analyze the expected gold and gem impact of random events across Luck scales in
Dominions 6.

This is a thin entry point.  All logic lives in the ``dom6_events`` package.
Run from the directory containing ``events.tsv`` (and optionally ``.dm`` mod
files).
"""

from __future__ import annotations

import os

from dom6_events import Event, ResultRow, analyze, parse_dm, parse_tsv


def main() -> None:
    all_events: list[Event] = []

    for filename in sorted(os.listdir(".")):
        filepath: str = os.path.join(".", filename)

        if filename.endswith(".tsv"):
            events: list[Event] = parse_tsv(filepath)
        elif filename.endswith(".dm"):
            events = parse_dm(filepath)
        else:
            continue

        print(f"Parsed {len(events)} qualifying events from {filename}")
        all_events.extend(events)

    good_count: int = sum(1 for e in all_events if e.is_good)
    bad_count: int = sum(1 for e in all_events if not e.is_good)
    print(
        f"\nTotal events: {len(all_events)} "
        f"(good: {good_count}, bad: {bad_count})"
    )

    results: list[ResultRow] = analyze(all_events)
    ResultRow.write_csv(results, "output.csv")
    print(f"\nResults written to output.csv ({len(results)} rows)")


if __name__ == "__main__":
    main()
