from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .agents import Urchin

if TYPE_CHECKING:
    from .simulation import Simulation


def _poisson(lam: float, rng: random.Random) -> int:
    """Knuth's algorithm for sampling a Poisson(lam) without numpy."""
    if lam <= 0:
        return 0
    import math

    L = math.exp(-lam)
    k = 0
    prod = 1.0
    while True:
        k += 1
        prod *= rng.random()
        if prod <= L:
            return k - 1


class DisturbanceModel:
    def __init__(self, storm_rate: float, disease_rate: float):
        self.storm_rate = storm_rate
        self.disease_rate = disease_rate
        self.storm_count = 0
        self.disease_count = 0

    def maybe_fire(self, sim: "Simulation") -> None:
        grid, rng, p = sim.grid, sim.rng, sim.params

        # --- storms: wipe kelp in a circular patch ---
        for _ in range(_poisson(self.storm_rate, rng)):
            self.storm_count += 1
            cx, cy = rng.randrange(grid.width), rng.randrange(grid.height)
            patch = grid.moore_neighbors(cx, cy, p.storm_radius)
            patch.append(grid.at(cx, cy))
            for cell in patch:
                cell.disturbed = True
                if cell.kelp is not None:
                    cell.kelp.biomass = 0.0

        # --- disease: cull a fraction of urchins in a patch ---
        for _ in range(_poisson(self.disease_rate, rng)):
            self.disease_count += 1
            cx, cy = rng.randrange(grid.width), rng.randrange(grid.height)
            patch = grid.moore_neighbors(cx, cy, p.storm_radius)
            patch.append(grid.at(cx, cy))
            for cell in patch:
                for occ in list(cell.occupants):
                    if isinstance(occ, Urchin) and rng.random() < p.disease_kill_frac:
                        occ.die()
