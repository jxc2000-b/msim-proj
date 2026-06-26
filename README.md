# msim-proj
This repository is part of a project in my modeling and simulations course. 

## Overview
Wild Kelp forests have been observed to abruptly flip from a lush garden into a barren desert. This typically happens when their key predator, the sea urchin, loses its keystone predator. Kelp forest are important because they are a critical ecosystem that provide food, shelter and habitats for a huge range of marine species. This project hopes to simulate that transition to study three research questions: 

1. **The Tipping Point**: at what point does the sea otter's (keystone predator of the sea urchin) mortality rate cause the Kelp forest to collapse?
2. **Reversibility**: is collapse reversible by restoring the otters, or does recovery require far more effort than the disruption that caused it?
3. **Spatial Effects**: how does the spatial clustering of sea urchins change the outcome, and which intervention (urchin culling, kelp replanting) restores the forest most effectively?

 ## Models implemented

| # | Model | Where it is/ will be |
|---|-------|-------|
| 1 | Lotka–Volterra | `src/agents.py`, `src/simulation.py` |
| 2 | Holling Type II functional response | `src/agents.py` (`Otter.step`) |
| 3 | Logistic resource regeneration | `src/grid.py` (`Kelp.regrow`) |
| 4 | Stochastic events  | `src/disturbance.py`, `src/simulation.py` |

> Overkill: Implementing 4 algorithims instead of the 2 required. Program should run fine on any modern laptop. 

## Requirements

- **Python 3.10+** (uses `X | Y` type syntax)
- The core simulation doesn't need any third-party packages
- Optional extras for analysis and plots:
  - **matplotlib>=3.8**
  - **pandas>=2.1**
  - **numpy>=1.26**

To install first set up a virtual environment:
For macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

For windows use 

```bash
python3 -m venv venv
.\venv\Scripts\activate.bat # in command prompt
.\venv\Scripts\activate.ps1 # in powershell 
```

Then 
```bash
cd msim_proj
python -m pip install -r requirements.txt
```

## To run

Run all commands `msim_/proj/` directory.

```bash
# Baseline run — prints progress + final ecosystem state
python3 run.py

# Push the system toward collapse with high otter mortality
python3 run.py --otter-mortality 0.30 --steps 500

# Locate the collapse tipping point (sweeps otter mortality 0.00 -> 0.30)
python3 run.py --sweep
```

every run is seeded (`--seed`), so the same seed gives identical output.

