"""Analysis harness for the kelp-forest simulation (Milestone 4).

Runs seeded ensembles of the simulation in-process and extracts summary metrics
for sensitivity analysis, scenario testing, extreme-condition validation, and
statistical summaries.

The per-tick Moran's I computation dominates runtime but is a pure observer
(it never affects the dynamics), so for bulk ensembles we disable it and, when a
spatial statistic is needed, compute the final-tick Moran's I once. This changes
nothing about the simulated trajectory -- only how much we measure along the way.
"""
from __future__ import annotations

import math
import os
import statistics
import sys
from dataclasses import replace

# make the simulation package importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "msim-proj"))

from src import Params, Simulation          # noqa: E402
import src.datacollector as _dc             # noqa: E402

BARREN_THRESHOLD = 0.10   # kelp cover below this = "barren" (matches M3 rule)

# --- speed: disable the expensive per-tick Moran's I for bulk runs -----------
_REAL_MORANS = _dc.DataCollector.morans_i


def _fast_morans(self, sim):
    return 0.0


def enable_fast_mode():
    _dc.DataCollector.morans_i = _fast_morans


def disable_fast_mode():
    _dc.DataCollector.morans_i = _REAL_MORANS


enable_fast_mode()  # default: fast


# --- single run + metric extraction ------------------------------------------
def run_once(base: Params | None = None, seed: int = 0,
             want_morans: bool = False, **overrides) -> dict:
    """Run one simulation and return a dict of summary metrics."""
    params = replace(base or Params(), seed=seed, **overrides)
    sim = Simulation(params)
    sim.run()

    rec = sim.collector.records
    final = rec[-1]
    covers = [r["kelp_cover"] for r in rec]
    urch = [r["urchins"] for r in rec]
    ott = [r["otters"] for r in rec]

    # time to collapse: first tick at/after which cover stays below threshold
    ttc = None
    for r in rec:
        if r["kelp_cover"] < BARREN_THRESHOLD:
            ttc = r["tick"]
            break

    final_morans = None
    if want_morans:
        disable_fast_mode()
        final_morans = _REAL_MORANS(sim.collector, sim)
        enable_fast_mode()

    return {
        "seed": seed,
        "steps_completed": sim.tick,
        "final_kelp_cover": final["kelp_cover"],
        "final_kelp_biomass": final["kelp_biomass"],
        "final_urchins": final["urchins"],
        "final_otters": final["otters"],
        "peak_urchins": max(urch),
        "peak_otters": max(ott),
        "mean_kelp_cover": round(statistics.fmean(covers), 4),
        "collapsed": 1 if final["kelp_cover"] < BARREN_THRESHOLD else 0,
        "extinct": 1 if len(sim.scheduler) == 0 else 0,
        "time_to_collapse": ttc,
        "storms": sim.disturbance.storm_count,
        "disease": sim.disturbance.disease_count,
        "final_morans_i": final_morans,
    }


def run_ensemble(n_seeds: int, base: Params | None = None,
                 seed0: int = 0, want_morans: bool = False, **overrides) -> list[dict]:
    """Run ``n_seeds`` replicates with consecutive seeds."""
    return [run_once(base, seed=seed0 + i, want_morans=want_morans, **overrides)
            for i in range(n_seeds)]


# --- statistics helpers ------------------------------------------------------
def summarize(values: list[float]) -> dict:
    """Mean, std, min, max, and 95% CI (normal approx) for a numeric list."""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "min": None, "max": None,
                "ci_low": None, "ci_high": None}
    mean = statistics.fmean(vals)
    std = statistics.stdev(vals) if n > 1 else 0.0
    half = 1.96 * std / math.sqrt(n) if n > 1 else 0.0
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "min": min(vals),
        "max": max(vals),
        "ci_low": mean - half,
        "ci_high": mean + half,
    }


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson 95% score interval for a binomial proportion. Returns (p, lo, hi)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return p, max(0.0, center - margin), min(1.0, center + margin)


def collapse_rate(rows: list[dict]) -> tuple[float, float, float, int, int]:
    """(rate, lo, hi, k_collapsed, n) collapse proportion with Wilson CI."""
    n = len(rows)
    k = sum(r["collapsed"] for r in rows)
    p, lo, hi = wilson_ci(k, n)
    return p, lo, hi, k, n


def extinction_rate(rows: list[dict]) -> tuple[float, float, float, int, int]:
    n = len(rows)
    k = sum(r["extinct"] for r in rows)
    p, lo, hi = wilson_ci(k, n)
    return p, lo, hi, k, n
