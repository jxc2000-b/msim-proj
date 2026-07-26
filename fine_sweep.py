"""Fine-resolution sweep of otter mortality to locate the tipping point.

M4 bracketed the transition between otter_mortality 0.02 and 0.04 with 30 seeds
at each of {0.00, 0.02, 0.04, ...}. That is too coarse to say where inside the
bracket the system flips. This script sweeps 0.000-0.050 at 0.005 resolution
with 60 seeds per point, fits a logistic curve to the collapse rate, and reports
the 50% crossing (mu) with a bootstrap confidence interval.

Writes:
    results/fine_sweep.csv          per-value collapse rates + Wilson intervals
    results/fine_sweep.json         fitted logistic parameters and CIs
    ../report/fine_tipping.png      the figure used in the final report

Run from m5/analysis:  python3 fine_sweep.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "msim-proj"))

from src import Params, Simulation  # noqa: E402

BARREN_THRESHOLD = 0.10
MORTALITIES = [round(0.005 * i, 4) for i in range(11)]  # 0.000 .. 0.050
N_SEEDS = 60
OUT = os.path.join(os.path.dirname(__file__), "results")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def one_run(job: tuple[float, int]) -> tuple[float, int, float, int]:
    """Run a single seeded simulation; return (mortality, seed, cover, ttc)."""
    mortality, seed = job
    sim = Simulation(Params(otter_mortality=mortality, seed=seed))
    sim.run()
    recs = sim.collector.records
    cover = recs[-1]["kelp_cover"]
    ttc = -1
    for r in recs:
        if r["kelp_cover"] < BARREN_THRESHOLD:
            ttc = r["tick"]
            break
    return (mortality, seed, cover, ttc)


def logistic_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares fit of p(x) = 1 / (1 + exp(-(x - mu) / s)) by grid search.

    A grid search is used rather than an optimizer so the script keeps its
    numpy-only dependency and stays reproducible.
    """
    best = (None, None, float("inf"))
    mu_grid = [0.0 + 0.0002 * i for i in range(301)]        # 0.000 .. 0.060
    s_grid = [0.0005 + 0.0005 * i for i in range(60)]       # 0.0005 .. 0.030
    for mu in mu_grid:
        for s in s_grid:
            err = 0.0
            for x, y in zip(xs, ys):
                z = (x - mu) / s
                z = max(-50.0, min(50.0, z))
                pred = 1.0 / (1.0 + math.exp(-z))
                err += (pred - y) ** 2
            if err < best[2]:
                best = (mu, s, err)
    return best[0], best[1]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    jobs = [(m, s) for m in MORTALITIES for s in range(N_SEEDS)]
    print(f"running {len(jobs)} simulations "
          f"({len(MORTALITIES)} values x {N_SEEDS} seeds)")

    with Pool(processes=2) as pool:
        results = pool.map(one_run, jobs, chunksize=8)

    by_value: dict[float, list[tuple[float, int]]] = {m: [] for m in MORTALITIES}
    for m, _seed, cover, ttc in results:
        by_value[m].append((cover, ttc))

    rows = []
    for m in MORTALITIES:
        runs = by_value[m]
        k = sum(1 for cover, _ in runs if cover < BARREN_THRESHOLD)
        n = len(runs)
        lo, hi = wilson(k, n)
        covers = [c for c, _ in runs]
        ttcs = [t for _, t in runs if t >= 0]
        rows.append({
            "otter_mortality": m,
            "collapse_rate": round(k / n, 4),
            "cr_lo": round(lo, 4),
            "cr_hi": round(hi, 4),
            "k_collapsed": k,
            "n": n,
            "mean_cover": round(sum(covers) / n, 4),
            "mean_ttc": round(sum(ttcs) / len(ttcs), 1) if ttcs else None,
        })
        print(f"  m={m:.3f}  collapse={k}/{n} = {k/n:.2f}  cover={rows[-1]['mean_cover']:.3f}")

    xs = [r["otter_mortality"] for r in rows]
    ys = [r["collapse_rate"] for r in rows]
    mu, s = logistic_fit(xs, ys)

    # bootstrap the fit over resampled seeds to get an interval on mu
    import random as _random
    rng = _random.Random(0)
    mus = []
    for _ in range(300):
        boot_ys = []
        for m in MORTALITIES:
            runs = by_value[m]
            draw = [runs[rng.randrange(len(runs))] for _ in runs]
            k = sum(1 for cover, _ in draw if cover < BARREN_THRESHOLD)
            boot_ys.append(k / len(draw))
        b_mu, _ = logistic_fit(xs, boot_ys)
        mus.append(b_mu)
    mus.sort()
    mu_lo, mu_hi = mus[int(0.025 * len(mus))], mus[int(0.975 * len(mus))]

    summary = {
        "n_seeds_per_point": N_SEEDS,
        "values": MORTALITIES,
        "rows": rows,
        "logistic_fit": {
            "mu": round(mu, 5),
            "scale": round(s, 5),
            "mu_ci_low": round(mu_lo, 5),
            "mu_ci_high": round(mu_hi, 5),
        },
    }
    with open(os.path.join(OUT, "fine_sweep.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    with open(os.path.join(OUT, "fine_sweep.csv"), "w") as fh:
        fh.write("otter_mortality,collapse_rate,cr_lo,cr_hi,k_collapsed,n,mean_cover,mean_ttc\n")
        for r in rows:
            fh.write(",".join(str(r[c]) for c in
                              ["otter_mortality", "collapse_rate", "cr_lo", "cr_hi",
                               "k_collapsed", "n", "mean_cover", "mean_ttc"]) + "\n")

    print(f"\nlogistic fit: mu = {mu:.4f} [{mu_lo:.4f}, {mu_hi:.4f}], scale = {s:.4f}")
    plot(rows, mu, s, mu_lo, mu_hi)


def plot(rows, mu, s, mu_lo, mu_hi) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [r["otter_mortality"] for r in rows]
    ys = [r["collapse_rate"] for r in rows]
    lo = [r["cr_lo"] for r in rows]
    hi = [r["cr_hi"] for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.fill_between(xs, lo, hi, alpha=0.20, color="#2b6cb0", linewidth=0,
                    label="95% Wilson interval")
    ax.plot(xs, ys, "o-", color="#2b6cb0", markersize=5, label="collapse rate (60 seeds)")

    fine = [xs[0] + (xs[-1] - xs[0]) * i / 400 for i in range(401)]
    fit = [1.0 / (1.0 + math.exp(-max(-50, min(50, (x - mu) / s)))) for x in fine]
    ax.plot(fine, fit, "--", color="#c53030", linewidth=1.6, label="logistic fit")

    ax.axvspan(mu_lo, mu_hi, color="#c53030", alpha=0.12, linewidth=0)
    ax.axvline(mu, color="#c53030", linewidth=1.0)
    ax.annotate(f"50% crossing\nm = {mu:.4f}", xy=(mu, 0.5),
                xytext=(mu + 0.006, 0.35), fontsize=9, color="#c53030",
                arrowprops=dict(arrowstyle="->", color="#c53030", lw=1))

    ax.axhline(0.5, color="grey", linewidth=0.6, linestyle=":")
    ax.set_xlabel("otter mortality (per step)")
    ax.set_ylabel("collapse rate")
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlim(min(xs), max(xs))
    ax.set_title("Locating the tipping point: 0.005 resolution, 60 seeds per point")
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), "..", "report", "fine_tipping.png")
    fig.savefig(out, dpi=160)
    print(f"wrote {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
