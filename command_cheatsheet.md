python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
# Defaults: 400 steps, seed 0, otter mortality 0.02
python3 run.py

# Shorter and longer runs
python3 run.py --steps 100
python3 run.py --steps 600

# Change the seed — same seed always gives identical output
python3 run.py --seed 7
python3 run.py --seed 42

# Otter mortality: below, at, and above the tipping point (~0.0136)
python3 run.py --otter-mortality 0.0        # predator fully protected
python3 run.py --otter-mortality 0.01       # below threshold, usually survives
python3 run.py --otter-mortality 0.30       # collapse is certain

# Same run, three different seeds — shows how much the outcome varies
python3 run.py --otter-mortality 0.02 --seed 1
python3 run.py --otter-mortality 0.02 --seed 2
python3 run.py --otter-mortality 0.02 --seed 3

# Push toward collapse, longer run
python3 run.py --otter-mortality 0.30 --steps 500

# Export per-step metrics to CSV
python3 run.py --csv baseline.csv

# Save a time-series PNG (needs matplotlib)
python3 run.py --plot baseline.png

# Both at once
python3 run.py --csv results.csv --plot results.png

# Everything together — a reproducible, documented collapse
python3 run.py --otter-mortality 0.30 --steps 500 --seed 7 \
    --csv collapse_s7.csv --plot collapse_s7.png

# Tipping-point sweep: 16 mortality values, 0.00 to 0.30 in steps of 0.02
python3 run.py --sweep

# Sweep with a shorter run per value, and a fixed seed
python3 run.py --sweep --steps 200 --seed 5

# Testing
python3 -m pytest -q

# The threshold study: 660 runs (11 mortality values x 60 seeds), ~8 min on 2 cores.
# Writes analysis/results/fine_sweep.{csv,json} and report/fine_tipping.png
python3 analysis/fine_sweep.py

# Redraw the figure from saved results — seconds, no simulations
python3 analysis/fine_sweep.py --replot

python3 analysis/fine_sweep.py --help

time python3 analysis/run_analysis.py

# The standard run — all four experiment groups, then all five figures
python3 analysis/run_analysis.py

# From anywhere; it resolves its own paths
cd ~ && python3 /path/to/project/analysis/run_analysis.py

# Time it
time python3 analysis/run_analysis.py

# Keep a timestamped log of the run
python3 analysis/run_analysis.py 2>&1 | tee "analysis_$(date +%Y%m%d_%H%M).log"

# Detach it — survives logout, useful since it takes a while
nohup python3 analysis/run_analysis.py > analysis.log 2>&1 &
tail -f analysis.log

# Unbuffered, so progress lines appear immediately rather than in chunks
python3 -u analysis/run_analysis.py

# Headless box with no display configured
MPLBACKEND=Agg python3 analysis/run_analysis.py

# Snapshot the figures before they get overwritten
mkdir -p report/before && cp report/*.png report/before/
python3 analysis/run_analysis.py

# Sensitivity only, then its two figures
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
sens = ra.run_sensitivity()
ra.fig_tipping(sens)
ra.fig_sensitivity_panels(sens)"

# Scenarios only
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
ra.fig_scenarios(ra.run_scenarios())"

# Extreme-condition checks only — fastest group, 20 seeds each
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
ra.run_extreme()"

# Baseline group, then both figures that depend on it
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
ra.run_baseline_ensemble()
ra.fig_baseline_hist()
ra.fig_trajectories()"

# Redraw figures from data already on disk — no simulations
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
ra.fig_baseline_hist()"

# A quick test: shrink the seed counts before running
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
ra.N_SWEEP, ra.N_EXTREME, ra.N_BASE = 3, 3, 5
ra.main()"

# Real Moran's I instead of the fast approximation (much slower)
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra, harness
harness.disable_fast_mode()
ra.run_baseline_ensemble()"

# One trajectory at chosen settings
python3 -c "
import sys; sys.path.insert(0, 'analysis')
import run_analysis as ra
print(ra.cover_trajectory(seed=7, steps=400, otter_mortality=0.05)[:20])"
