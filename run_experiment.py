#!/usr/bin/env python3
"""Experiment runner for the kelp-forest simulation.

Runs a single simulation with optional parameter overrides, times it, and writes
two structured, self-documenting data files into ``results/``:

  * ``run_<id>.csv``  -- per-tick time series (one row per simulation step).
  * ``run_<id>.json`` -- run metadata: parameters, timestamps, execution time,
                         summary statistics, and event counts.

It also appends a one-line summary of every run to ``results/manifest.csv`` so
all runs can be compared in one place (this is the source for the report's Run
Table).

Usage
-----
    python3 run_experiment.py --id 001 --purpose "Baseline (all defaults)"

    python3 run_experiment.py --id 003 --purpose "High otter mortality" \
        --set otter_mortality=0.30

    python3 run_experiment.py --id 005 --purpose "Slow kelp regrowth" \
        --set kelp_growth=0.10 --set steps=500

Any field of the ``Params`` dataclass can be overridden with ``--set name=value``
(repeatable). Values are coerced to the type declared on ``Params``.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone

from src import Params, Simulation

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# Human-readable units for every column/metric we emit (documentation in-file).
UNITS = {
    "tick": "step (~1 week of simulated time)",
    "urchins": "count",
    "otters": "count",
    "kelp_biomass": "biomass units (summed over cells)",
    "kelp_cover": "fraction of rock cells with kelp cover > 10%",
    "morans_i": "dimensionless spatial autocorrelation in [-1, 1]",
    "duration_ms": "milliseconds (wall-clock)",
    "steps_per_second": "simulation steps per wall-clock second",
}

# ecosystem-state decision rule (matches run.py's classification threshold)
BARREN_COVER_THRESHOLD = 0.10


def _coerce(name: str, value: str):
    """Coerce a string override to the type declared on the Params field."""
    fields = {f.name: f.type for f in dataclasses.fields(Params)}
    if name not in fields:
        raise SystemExit(f"Unknown parameter '{name}'. Valid: {sorted(fields)}")
    t = fields[name]
    # dataclass field types come through as strings under `from __future__`.
    if t in ("int", int):
        return int(value)
    if t in ("float", float):
        return float(value)
    if t in ("bool", bool):
        return value.lower() in ("1", "true", "yes")
    return value


def _summary(records: list[dict], key: str) -> dict:
    series = [r[key] for r in records]
    return {
        "min": min(series),
        "max": max(series),
        "mean": round(statistics.fmean(series), 4),
        "final": series[-1],
    }


def run_experiment(run_id: str, purpose: str, overrides: dict) -> dict:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    params = Params(**overrides)

    # --- execute, timed ---
    wall_start = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    sim = Simulation(params)
    sim.run()
    duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    wall_end = datetime.now(timezone.utc)

    records = sim.collector.records
    steps_completed = sim.tick
    final = records[-1]
    cover = final["kelp_cover"]
    state = "barren" if cover < BARREN_COVER_THRESHOLD else "kelp_forest"

    # --- CSV: per-tick time series ---
    csv_name = f"run_{run_id}.csv"
    csv_path = os.path.join(RESULTS_DIR, csv_name)
    fieldnames = ["run_id", "tick", "urchins", "otters",
                  "kelp_biomass", "kelp_cover", "morans_i"]
    with open(csv_path, "w", newline="") as f:
        f.write(f"# run_id={run_id} purpose={purpose}\n")
        f.write(f"# columns/units: {json.dumps(UNITS)}\n")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow({"run_id": run_id, **{k: r[k] for k in fieldnames[1:]}})

    # --- JSON: metadata + summary statistics ---
    meta = {
        "run_id": run_id,
        "purpose": purpose,
        "overrides": overrides,
        "parameters": dataclasses.asdict(params),
        "timestamps": {
            "wall_start_utc": wall_start.isoformat(),
            "wall_end_utc": wall_end.isoformat(),
            "sim_start_tick": 0,
            "sim_end_tick": steps_completed,
        },
        "performance": {
            "duration_ms": duration_ms,
            "steps_completed": steps_completed,
            "steps_per_second": round(steps_completed / (duration_ms / 1000.0), 2)
            if duration_ms > 0 else None,
        },
        "event_counts": {
            "storms": sim.disturbance.storm_count,
            "disease_outbreaks": sim.disturbance.disease_count,
            "extinction": len(sim.scheduler) == 0,
        },
        "final_state": {
            "urchins": final["urchins"],
            "otters": final["otters"],
            "kelp_biomass": final["kelp_biomass"],
            "kelp_cover": cover,
            "morans_i": final["morans_i"],
            "ecosystem_state": state,
        },
        "summary_statistics": {
            "urchins": _summary(records, "urchins"),
            "otters": _summary(records, "otters"),
            "kelp_cover": _summary(records, "kelp_cover"),
            "kelp_biomass": _summary(records, "kelp_biomass"),
            "morans_i": _summary(records, "morans_i"),
        },
        "units": UNITS,
        "data_files": {"time_series_csv": csv_name},
    }
    json_name = f"run_{run_id}.json"
    with open(os.path.join(RESULTS_DIR, json_name), "w") as f:
        json.dump(meta, f, indent=2)

    _append_manifest(run_id, purpose, overrides, duration_ms, state, csv_name)

    # --- console echo ---
    changed = ", ".join(f"{k}={v}" for k, v in overrides.items()) or "defaults"
    print(f"[run {run_id}] {purpose}")
    print(f"  params changed : {changed}")
    print(f"  steps          : {steps_completed}")
    print(f"  duration       : {duration_ms} ms "
          f"({meta['performance']['steps_per_second']} steps/s)")
    print(f"  final          : urchins={final['urchins']} otters={final['otters']} "
          f"kelp_cover={cover:.2%}")
    print(f"  events         : {sim.disturbance.storm_count} storms, "
          f"{sim.disturbance.disease_count} disease")
    print(f"  ecosystem state: {state.upper()}")
    print(f"  wrote          : results/{csv_name}, results/{json_name}")
    return meta


def _append_manifest(run_id, purpose, overrides, duration_ms, state, csv_name):
    manifest = os.path.join(RESULTS_DIR, "manifest.csv")
    is_new = not os.path.exists(manifest)
    with open(manifest, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["run_id", "purpose", "parameters_changed",
                        "duration_ms", "ecosystem_state", "data_file"])
        changed = "; ".join(f"{k}={v}" for k, v in overrides.items()) or "defaults"
        w.writerow([run_id, purpose, changed, duration_ms, state, csv_name])


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one timed simulation experiment.")
    ap.add_argument("--id", required=True, help="run identifier, e.g. 001")
    ap.add_argument("--purpose", required=True, help="short description of the run")
    ap.add_argument("--set", action="append", default=[], metavar="name=value",
                    help="override a Params field (repeatable)")
    args = ap.parse_args()

    overrides = {}
    for item in args.set:
        if "=" not in item:
            raise SystemExit(f"--set expects name=value, got '{item}'")
        name, value = item.split("=", 1)
        overrides[name.strip()] = _coerce(name.strip(), value.strip())

    run_experiment(args.id, args.purpose, overrides)


if __name__ == "__main__":
    main()
