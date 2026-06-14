#!/usr/bin/env python3
"""Precompute a compact data/stops.json from the raw GTFS .txt files.

The giant file is stop_times.txt (~1.4 GB): an arrival time for every stop of
every trip. For "which lines pass near an address?" we only need to know which
bus lines serve each stop, so we stream it once and collapse it.

Output: data/stops.json — a list of [name, lat, lon, [line, ...]] per stop.
After running this you can DELETE every .txt file; the static site only needs
the JSON. Run:  python3 build_data.py
"""
import csv
import json
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)
HERE = Path(__file__).parent
OUT = HERE / "data"


def rows(name):
    with open(HERE / name, newline="", encoding="utf-8-sig") as f:
        yield from csv.DictReader(f)


def main():
    print("Loading routes (route_id -> line name)...")
    route_name = {r["route_id"]: (r["route_short_name"] or r["route_long_name"]) for r in rows("routes.txt")}

    print("Loading trips (trip_id -> route_id)...")
    trip_route = {r["trip_id"]: r["route_id"] for r in rows("trips.txt")}
    print(f"  {len(trip_route):,} trips")

    print("Streaming stop_times.txt (the big one) -> lines per stop...")
    stop_lines = {}  # stop_id -> set of line names
    for i, r in enumerate(rows("stop_times.txt"), 1):
        route_id = trip_route.get(r["trip_id"])
        if route_id is None:
            continue
        line = route_name.get(route_id)
        if line:
            stop_lines.setdefault(r["stop_id"], set()).add(line)
        if i % 2_000_000 == 0:
            print(f"  {i:,} rows...")

    print("Loading stops + joining...")
    out = []
    for r in rows("stops.txt"):
        lines = sorted(stop_lines.get(r["stop_id"], ()))
        if not lines:
            continue  # skip stops no line actually serves
        out.append([
            r["stop_name"],
            round(float(r["stop_lat"]), 5),
            round(float(r["stop_lon"]), 5),
            lines,
        ])

    OUT.mkdir(exist_ok=True)
    path = OUT / "stops.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Done. {len(out):,} stops -> {path} ({path.stat().st_size / 1e6:.1f} MB)")
    print("You can now delete the .txt files.")


if __name__ == "__main__":
    main()
