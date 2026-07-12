"""Tests for the kelp-forest simulation core."""
import math

import pytest

from src import Kelp, Otter, Params, Simulation, Urchin
from src.disturbance import _poisson
from src.grid import Grid, GridCell, SubstrateType


# --------------------------------------------------------------- Kelp model
def test_logistic_regrowth_is_bounded():
    k = Kelp(biomass=0.5, growth_rate=0.5, max_density=1.0)
    for _ in range(200):
        k.regrow()
    assert k.biomass <= 1.0
    assert k.biomass == pytest.approx(1.0, abs=1e-3)


def test_logistic_regrowth_increases_below_capacity():
    k = Kelp(biomass=0.2, growth_rate=0.3, max_density=1.0)
    before = k.biomass
    k.regrow()
    assert k.biomass > before


def test_consume_never_negative():
    k = Kelp(biomass=0.3, growth_rate=0.1, max_density=1.0)
    eaten = k.consume(1.0)
    assert eaten == pytest.approx(0.3)
    assert k.biomass == 0.0


# --------------------------------------------------------------- Grid
def test_grid_wraps_toroidally():
    g = Grid(5, 5)
    assert g.wrap(-1, -1) == (4, 4)
    assert g.wrap(5, 5) == (0, 0)


def test_moore_neighbors_count():
    g = Grid(10, 10)
    assert len(g.moore_neighbors(5, 5, 1)) == 8
    assert len(g.moore_neighbors(5, 5, 2)) == 24


# --------------------------------------------------------------- Poisson
def test_poisson_zero_rate():
    import random
    assert _poisson(0.0, random.Random(0)) == 0


def test_poisson_mean_is_reasonable():
    import random
    rng = random.Random(1)
    lam = 3.0
    draws = [_poisson(lam, rng) for _ in range(5000)]
    assert math.isclose(sum(draws) / len(draws), lam, rel_tol=0.1)


# --------------------------------------------------------------- Simulation
def test_simulation_runs_and_collects():
    sim = Simulation(Params(width=20, height=20, steps=30, seed=42))
    df = sim.run()
    records = sim.collector.records
    assert len(records) == 31  # tick 0 + 30 steps
    assert all("kelp_cover" in r for r in records)


def test_determinism_same_seed():
    a = Simulation(Params(width=20, height=20, steps=40, seed=7))
    b = Simulation(Params(width=20, height=20, steps=40, seed=7))
    a.run(); b.run()
    assert a.collector.records == b.collector.records


def test_removing_otters_drives_urchin_increase():
    """Top-down control: high otter mortality should let urchins grow
    relative to a low-mortality control (over the same seed)."""
    low = Simulation(Params(width=25, height=25, steps=120, seed=3,
                            otter_mortality=0.01))
    high = Simulation(Params(width=25, height=25, steps=120, seed=3,
                             otter_mortality=0.5))
    low.run(); high.run()
    u_low, _ = low.counts()
    u_high, _ = high.counts()
    assert u_high >= u_low


def test_morans_i_in_range():
    sim = Simulation(Params(width=20, height=20, steps=20, seed=5))
    sim.run()
    i = sim.collector.morans_i(sim)
    assert -1.01 <= i <= 1.01
