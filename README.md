# msim-proj
This repository is part of a project in my modeling and simulations course. 

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
cd msim-proj
python -m pip install -r requirements.txt
```

## To run

Run all commands from the `msim-proj/` root directory.

```bash
# Baseline run — prints progress + final ecosystem state
python3 run.py

# Push the system toward collapse with high otter mortality
python3 run.py --otter-mortality 0.30 --steps 500

# Locate the collapse tipping point (sweeps otter mortality 0.00 -> 0.30)
python3 run.py --sweep

# Export per-step metrics to CSV and a time-series plot
python3 run.py --csv results.csv --plot results.png
```

Every run is seeded (`--seed`), so the same seed gives identical output.

## Tests

```bash
python3 -m pytest -q
```



