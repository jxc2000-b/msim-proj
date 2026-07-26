"""Run the full M4 analysis: sensitivity, scenarios, extreme conditions,
statistical summary, and trajectory ensembles. Saves data files to
analysis/results/ and figures to report/.
"""
from __future__ import annotations

import csv
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import matplotlib.ticker as mtick   # noqa: E402

from harness import (Params, run_once, run_ensemble, summarize,   # noqa: E402
                     collapse_rate, extinction_rate, enable_fast_mode,
                     disable_fast_mode, _REAL_MORANS)
from src import Simulation                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIG = os.path.join(os.path.dirname(HERE), "report")
os.makedirs(RES, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

# ---- plotting style ---------------------------------------------------------
FOREST = "#2ca02c"
BARREN = "#c8843c"
ACCENT = "#1f6fb2"
plt.rcParams.update({"figure.dpi": 140, "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})

N_SWEEP = 30       # seeds per sensitivity/scenario config
N_EXTREME = 20     # seeds per extreme-condition config
N_BASE = 60        # seeds for the headline baseline ensemble

SUMMARY: dict = {}


def _save_rows(name, rows):
    if not rows:
        return
    with open(os.path.join(RES, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ============================================================ sensitivity
SWEEPS = {
    "otter_mortality": [0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30],
    "kelp_growth":     [0.10, 0.20, 0.30, 0.40, 0.50],
    "storm_rate":      [0.0, 0.05, 0.10, 0.20, 0.40],
    "n_urchins0":      [40, 80, 160, 240, 320],
}
BASELINE = {"otter_mortality": 0.02, "kelp_growth": 0.30,
            "storm_rate": 0.05, "n_urchins0": 160}


def run_sensitivity():
    print("== sensitivity ==")
    out = {}
    for param, values in SWEEPS.items():
        rows_summary = []
        for v in values:
            t0 = time.perf_counter()
            rows = run_ensemble(N_SWEEP, **{param: v})
            p, lo, hi, k, n = collapse_rate(rows)
            cov = summarize([r["final_kelp_cover"] for r in rows])
            rows_summary.append({
                "param": param, "value": v,
                "collapse_rate": round(p, 4), "cr_lo": round(lo, 4), "cr_hi": round(hi, 4),
                "k_collapsed": k, "n": n,
                "mean_cover": round(cov["mean"], 4), "std_cover": round(cov["std"], 4),
                "min_cover": round(cov["min"], 4), "max_cover": round(cov["max"], 4),
            })
            print(f"  {param}={v:<6} collapse={p:.2f} [{lo:.2f},{hi:.2f}] "
                  f"cover_mean={cov['mean']:.2f}  ({time.perf_counter()-t0:.1f}s)")
        out[param] = rows_summary
        _save_rows(f"sensitivity_{param}.csv", rows_summary)
    SUMMARY["sensitivity"] = out
    return out


def sensitivity_indices(sens):
    """Elasticity of collapse rate w.r.t. each parameter around baseline, plus
    the total collapse-rate swing across the swept range (influence score)."""
    idx = {}
    for param, rows in sens.items():
        base_v = BASELINE[param]
        # baseline collapse rate = value nearest baseline
        base_row = min(rows, key=lambda r: abs(r["value"] - base_v))
        base_cr = base_row["collapse_rate"]
        crs = [r["collapse_rate"] for r in rows]
        swing = max(crs) - min(crs)
        # local elasticity: use the two swept points bracketing baseline
        vals = sorted(rows, key=lambda r: r["value"])
        elasticity = None
        for i in range(len(vals) - 1):
            lo, hi = vals[i], vals[i + 1]
            if lo["value"] <= base_v <= hi["value"] and hi["value"] != lo["value"]:
                d_out = hi["collapse_rate"] - lo["collapse_rate"]
                d_in = hi["value"] - lo["value"]
                if base_cr > 0 and base_v > 0:
                    elasticity = (d_out / base_cr) / (d_in / base_v)
                break
        idx[param] = {"baseline_value": base_v, "baseline_collapse_rate": base_cr,
                      "swing": round(swing, 3),
                      "elasticity": round(elasticity, 3) if elasticity is not None else None}
    SUMMARY["sensitivity_indices"] = idx
    return idx


# ============================================================ scenarios
SCENARIOS = {
    "Balanced (baseline)": {},
    "Predator loss": {"otter_mortality": 0.25},
    "Storm season": {"storm_rate": 0.30, "disease_rate": 0.10},
    "Protected reserve": {"otter_mortality": 0.0, "kelp_growth": 0.40,
                          "storm_rate": 0.0, "disease_rate": 0.0},
    "Grazer outbreak": {"n_urchins0": 320, "urchin_repro_prob": 0.18},
}


def run_scenarios():
    print("== scenarios ==")
    rows_summary = []
    for name, kw in SCENARIOS.items():
        rows = run_ensemble(N_SWEEP, **kw)
        p, lo, hi, k, n = collapse_rate(rows)
        cov = summarize([r["final_kelp_cover"] for r in rows])
        ttc = summarize([r["time_to_collapse"] for r in rows if r["time_to_collapse"] is not None])
        rows_summary.append({
            "scenario": name, "params": json.dumps(kw),
            "collapse_rate": round(p, 4), "cr_lo": round(lo, 4), "cr_hi": round(hi, 4),
            "mean_cover": round(cov["mean"], 4), "std_cover": round(cov["std"], 4),
            "cover_ci_lo": round(cov["ci_low"], 4), "cover_ci_hi": round(cov["ci_high"], 4),
            "mean_ttc": round(ttc["mean"], 1) if ttc["mean"] is not None else None,
            "n": n,
        })
        print(f"  {name:22s} collapse={p:.2f} [{lo:.2f},{hi:.2f}] cover={cov['mean']:.2f}")
    _save_rows("scenarios.csv", rows_summary)
    SUMMARY["scenarios"] = rows_summary
    return rows_summary


# ============================================================ extreme conditions
EXTREME = {
    "No otters": {"n_otters0": 0},
    "No urchins": {"n_urchins0": 0},
    "Zero kelp growth": {"kelp_growth": 0.0},
    "No disturbance": {"storm_rate": 0.0, "disease_rate": 0.0},
    "Max otter mortality": {"otter_mortality": 1.0},
    "Zero otter mortality": {"otter_mortality": 0.0},
}
EXTREME_EXPECT = {
    "No otters": "urchins irrupt, kelp grazed to a barren",
    "No urchins": "kelp grows to carrying capacity; forest persists",
    "Zero kelp growth": "no regeneration; kelp depletes to a barren",
    "No disturbance": "baseline dynamics; forest more likely to persist",
    "Max otter mortality": "otters die out immediately; barren",
    "Zero otter mortality": "strongest otter control; best forest survival",
}


def run_extreme():
    print("== extreme conditions ==")
    rows_summary = []
    for name, kw in EXTREME.items():
        rows = run_ensemble(N_EXTREME, **kw)
        p, lo, hi, k, n = collapse_rate(rows)
        cov = summarize([r["final_kelp_cover"] for r in rows])
        fu = summarize([r["final_urchins"] for r in rows])
        fo = summarize([r["final_otters"] for r in rows])
        rows_summary.append({
            "condition": name, "params": json.dumps(kw),
            "expected": EXTREME_EXPECT[name],
            "collapse_rate": round(p, 4),
            "mean_cover": round(cov["mean"], 4),
            "mean_final_urchins": round(fu["mean"], 1),
            "mean_final_otters": round(fo["mean"], 1),
            "n": n,
        })
        print(f"  {name:22s} collapse={p:.2f} cover={cov['mean']:.2f} "
              f"urch={fu['mean']:.0f} ott={fo['mean']:.0f}")
    _save_rows("extreme.csv", rows_summary)
    SUMMARY["extreme"] = rows_summary
    return rows_summary


# ============================================================ baseline ensemble
def run_baseline_ensemble():
    print("== baseline ensemble ==")
    rows = run_ensemble(N_BASE, seed0=1000)   # distinct seed block
    _save_rows("baseline_ensemble.csv", rows)
    metrics = ["final_kelp_cover", "final_urchins", "final_otters",
               "steps_completed", "peak_urchins"]
    stats = {m: summarize([r[m] for r in rows]) for m in metrics}
    # collapse + extinction proportions
    cp, clo, chi, ck, cn = collapse_rate(rows)
    ep, elo, ehi, ek, en = extinction_rate(rows)
    ttc_vals = [r["time_to_collapse"] for r in rows if r["time_to_collapse"] is not None]
    SUMMARY["baseline_ensemble"] = {
        "n": N_BASE, "stats": stats,
        "collapse": {"p": cp, "lo": clo, "hi": chi, "k": ck, "n": cn},
        "extinction": {"p": ep, "lo": elo, "hi": ehi, "k": ek, "n": en},
        "time_to_collapse": summarize(ttc_vals),
    }
    print(f"  collapse={cp:.2f} [{clo:.2f},{chi:.2f}]  extinction={ep:.2f}")
    for m in metrics:
        s = stats[m]
        print(f"  {m:20s} mean={s['mean']:.2f} std={s['std']:.2f} "
              f"[{s['min']:.2f},{s['max']:.2f}]")
    return rows


# ============================================================ trajectories
def cover_trajectory(seed, steps=400, **kw):
    sim = Simulation(Params(seed=seed, steps=steps, **kw))
    sim.run()
    return [(r["tick"], r["kelp_cover"]) for r in sim.collector.records]


# ============================================================ figures
def fig_tipping(sens):
    rows = sorted(sens["otter_mortality"], key=lambda r: r["value"])
    x = [r["value"] for r in rows]
    y = [r["collapse_rate"] * 100 for r in rows]           # collapse rate as a percentage
    lo = [r["cr_lo"] * 100 for r in rows]
    hi = [r["cr_hi"] * 100 for r in rows]

    # tipping point = mortality with the steepest rise in collapse rate
    tip_i = max(range(1, len(x)), key=lambda i: (y[i] - y[i - 1]) / (x[i] - x[i - 1]))
    tip_x, tip_y = x[tip_i], y[tip_i]

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.fill_between(x, lo, hi, color=ACCENT, alpha=0.18, label="95% CI (Wilson)")
    ax.plot(x, y, "-o", color=ACCENT, lw=2, label="collapse rate")

    # horizontal + vertical guide lines at the tipping point
    ax.axhline(tip_y, color=BARREN, ls="--", lw=1.2, zorder=1)
    ax.axvline(tip_x, color=BARREN, ls="--", lw=1.2, zorder=1,
               label=f"tipping point (mortality {tip_x:g})")

    ax.set_xlabel("otter mortality (per-step probability)")
    ax.set_ylabel("collapse rate (% of runs → barren)")
    ax.set_title(f"Tipping response to otter mortality ({N_SWEEP} seeds per point)")
    ax.set_ylim(-3, 103)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "sens_otter_mortality.png"))
    plt.close(fig)


def fig_sensitivity_panels(sens):
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.4))
    titles = {"otter_mortality": "otter mortality", "kelp_growth": "kelp growth rate",
              "storm_rate": "storm rate", "n_urchins0": "initial urchins"}
    for ax, param in zip(axes.flat, SWEEPS):
        rows = sorted(sens[param], key=lambda r: r["value"])
        x = [r["value"] for r in rows]
        y = [r["collapse_rate"] * 100 for r in rows]       # collapse rate as a percentage
        lo = [r["cr_lo"] * 100 for r in rows]
        hi = [r["cr_hi"] * 100 for r in rows]
        ax.fill_between(x, lo, hi, color=ACCENT, alpha=0.15)
        ax.plot(x, y, "-o", color=ACCENT, lw=1.8)

        # tipping point = value with the steepest rise in collapse rate
        tip_i = max(range(1, len(x)),
                    key=lambda i: (y[i] - y[i - 1]) / (x[i] - x[i - 1]))
        tip_x, tip_y = x[tip_i], y[tip_i]
        ax.axhline(tip_y, color=BARREN, ls="--", lw=1.0, zorder=1)
        ax.axvline(tip_x, color=BARREN, ls="--", lw=1.0, zorder=1)

        ax.set_title(titles[param])
        ax.set_ylabel("collapse rate")
        ax.set_ylim(-5, 105)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    fig.suptitle(f"Sensitivity of collapse rate to each parameter ({N_SWEEP} seeds/point)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "sens_panels.png"))
    plt.close(fig)


def fig_scenarios(scn):
    names = [r["scenario"] for r in scn]
    y = [r["collapse_rate"] for r in scn]
    lo = [r["collapse_rate"] - r["cr_lo"] for r in scn]
    hi = [r["cr_hi"] - r["collapse_rate"] for r in scn]
    colors = [BARREN if v >= 0.5 else FOREST for v in y]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(range(len(names)), y, yerr=[lo, hi], capsize=4,
           color=colors, edgecolor="#333", linewidth=0.5)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("collapse rate")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Collapse rate by scenario ({N_SWEEP} seeds each, 95% CI)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "scenarios.png"))
    plt.close(fig)


def fig_baseline_hist(rows_file="baseline_ensemble.csv"):
    import csv as _csv
    with open(os.path.join(RES, rows_file)) as f:
        rows = list(_csv.DictReader(f))
    covers = [float(r["final_kelp_cover"]) * 100 for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.hist(covers, bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            color=ACCENT, edgecolor="#333", alpha=0.85)
    ax.axvline(10, ls="--", color="#555", lw=1)
    ax.text(11, ax.get_ylim()[1]*0.9, "barren threshold", color="#555", fontsize=9)
    ax.set_xlabel("final kelp cover (%)")
    ax.set_ylabel("number of runs")
    ax.set_title(f"Bimodal outcome distribution ({len(covers)} baseline seeds)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "baseline_hist.png"))
    plt.close(fig)


def fig_trajectories():
    fig, ax = plt.subplots(figsize=(8, 4.4))
    forest_seen = barren_seen = False
    for seed in range(1000, 1024):
        traj = cover_trajectory(seed)
        x = [t for t, _ in traj]
        y = [c * 100 for _, c in traj]
        final = y[-1]
        if final >= 10:
            ax.plot(x, y, color=FOREST, alpha=0.5, lw=1,
                    label=None if forest_seen else "ends as forest"); forest_seen = True
        else:
            ax.plot(x, y, color=BARREN, alpha=0.5, lw=1,
                    label=None if barren_seen else "ends as barren"); barren_seen = True
    ax.axhline(10, ls="--", color="#555", lw=1)
    ax.set_xlabel("time step")
    ax.set_ylabel("kelp cover (%)")
    ax.set_title("Baseline kelp-cover trajectories (24 seeds) diverge to two states")
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "trajectories.png"))
    plt.close(fig)


def main():
    t0 = time.perf_counter()
    sens = run_sensitivity()
    sensitivity_indices(sens)
    scn = run_scenarios()
    run_extreme()
    run_baseline_ensemble()

    print("== figures ==")
    fig_tipping(sens)
    fig_sensitivity_panels(sens)
    fig_scenarios(scn)
    fig_baseline_hist()
    fig_trajectories()

    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(SUMMARY, f, indent=2)
    print(f"\nDONE in {time.perf_counter()-t0:.0f}s. "
          f"Data -> analysis/results/, figures -> report/")


if __name__ == "__main__":
    main()
