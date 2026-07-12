#!/usr/bin/env python3
"""Command-line entry point for the kelp-forest simulation.

Examples
--------
    python run.py                      # single baseline run, prints metrics
    python run.py --steps 600 --seed 3
    python run.py --otter-mortality 0.25   # push toward collapse
    python run.py --sweep                   # tipping-point mortality sweep
    python run.py --plot results.png        # save a time-series plot
"""
from __future__ import annotations

import argparse

from src import Params, Simulation
from src.agents import Urchin


def single_run(args) -> None:
    p = Params(steps=args.steps, seed=args.seed, otter_mortality=args.otter_mortality)
    sim = Simulation(p)
    print(f"Running {p.steps} steps on a {p.width}x{p.height} grid "
          f"(seed={p.seed}, otter_mortality={p.otter_mortality}) ...")
    df = sim.run(verbose=True)

    last = sim.collector.records[-1]
    print("\nFinal state:")
    print(f"  urchins      = {last['urchins']}")
    print(f"  otters       = {last['otters']}")
    print(f"  kelp cover   = {last['kelp_cover']:.2%}")
    print(f"  Moran's I    = {last['morans_i']:.3f} (urchin clustering)")
    print(f"  storms fired = {sim.disturbance.storm_count}, "
          f"disease events = {sim.disturbance.disease_count}")

    state = "COLLAPSED (urchin barren)" if last["kelp_cover"] < 0.1 else "kelp forest"
    print(f"  => ecosystem state: {state}")

    if args.csv:
        _write_csv(sim.collector.records, args.csv)
        print(f"  metrics written to {args.csv}")
    if args.plot:
        _plot(sim.collector.records, args.plot)
        print(f"  plot written to {args.plot}")


def sweep(args) -> None:
    """Sweep otter mortality upward to locate the collapse tipping point."""
    print("Otter-mortality sweep (final kelp cover after full run):\n")
    print(f"  {'mortality':>9} | {'kelp_cover':>10} | state")
    print("  " + "-" * 34)
    prev_state = "forest"
    tipping = None
    for m in [round(0.02 * i, 2) for i in range(0, 16)]:
        p = Params(steps=args.steps, seed=args.seed, otter_mortality=m)
        sim = Simulation(p)
        sim.run()
        cover = sim.collector.records[-1]["kelp_cover"]
        state = "barren" if cover < 0.1 else "forest"
        if prev_state == "forest" and state == "barren" and tipping is None:
            tipping = m
        prev_state = state
        print(f"  {m:>9.2f} | {cover:>10.2%} | {state}")
    if tipping is not None:
        print(f"\n  => collapse tipping point near otter_mortality = {tipping}")
    else:
        print("\n  => no collapse observed in the swept range")


def _write_csv(records, path) -> None:
    import csv

    if not records:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)


def _plot(records, path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib not installed; skipping plot)")
        return

    ticks = [r["tick"] for r in records]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(ticks, [r["urchins"] for r in records], "C1", label="urchins")
    ax1.plot(ticks, [r["otters"] for r in records], "C0", label="otters")
    ax1.set_xlabel("time step")
    ax1.set_ylabel("population")
    ax2 = ax1.twinx()
    ax2.plot(ticks, [r["kelp_cover"] for r in records], "C2--", label="kelp cover")
    ax2.set_ylabel("kelp cover (fraction)")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main() -> None:
    ap = argparse.ArgumentParser(description="Kelp forest collapse & recovery simulator")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--otter-mortality", type=float, default=0.02)
    ap.add_argument("--sweep", action="store_true", help="run a tipping-point sweep")
    ap.add_argument("--csv", metavar="PATH", help="write per-step metrics to CSV")
    ap.add_argument("--plot", metavar="PATH", help="save a time-series PNG")
    args = ap.parse_args()

    if args.sweep:
        sweep(args)
    else:
        single_run(args)


if __name__ == "__main__":
    main()
