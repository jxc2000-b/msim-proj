from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .grid import Grid

if TYPE_CHECKING:
    from .simulation import Simulation

_next_id = 0


def _new_id() -> int:
    global _next_id
    _next_id = _next_id + 1
    return _next_id


def _sign(d: int) -> int:
    return (d > 0) - (d < 0)


def _short_delta(target: int, origin: int, size: int) -> int:
    """Signed shortest step from ``origin`` to ``target`` on a ring of length
    ``size`` (handles toroidal wrap-around)."""
    d = (target - origin) % size
    if d > size // 2:
        d -= size
    return d


class Agent(ABC):
    __slots__ = ("id", "x", "y", "energy", "age", "alive")

    def __init__(self, x: int, y: int, energy: float):
        self.id = _new_id()
        self.x = x
        self.y = y
        self.energy = energy
        self.age = 0
        self.alive = True

    @abstractmethod
    def step(self, sim: "Simulation") -> None:
        """Advance this agent by one tick (sense + act + metabolism)."""

    def _random_walk_target(self, grid: Grid, rng: random.Random) -> tuple[int, int]:
        n = rng.choice(grid.moore_neighbors(self.x, self.y, 1))
        return n.x, n.y

    def die(self) -> None:
        self.alive = False


class Urchin(Agent):
    """Herbivore: grazes kelp, flees otters, reproduces when well-fed."""

    __slots__ = ()

    def step(self, sim: "Simulation") -> None:
        grid, rng, p = sim.grid, sim.rng, sim.params

        # --- sense: flee if a predator is adjacent, else move toward kelp ---
        neighbors = grid.moore_neighbors(self.x, self.y, 1)
        predator_near = any(
            isinstance(o, Otter) for c in neighbors for o in c.occupants
        )
        if predator_near:
            # move to the adjacent cell with the fewest otters
            target = min(
                neighbors,
                key=lambda c: sum(isinstance(o, Otter) for o in c.occupants),
            )
            grid.move_agent(self, target.x, target.y)
        else:
            # move toward the richest adjacent kelp cell (greedy foraging)
            best = max(neighbors, key=lambda c: c.kelp_biomass)
            here = grid.at(self.x, self.y)
            if best.kelp_biomass > here.kelp_biomass:
                grid.move_agent(self, best.x, best.y)

        # --- act: graze local kelp ---
        cell = grid.at(self.x, self.y)
        if cell.kelp is not None:
            self.energy += cell.kelp.consume(p.urchin_graze)

        # --- metabolism ---
        self.energy -= p.urchin_metabolism
        self.age += 1


class Otter(Agent):
    """Keystone predator: hunts urchins with a Holling Type II response."""

    __slots__ = ("hunger",)

    def __init__(self, x: int, y: int, energy: float):
        super().__init__(x, y, energy)
        self.hunger = 0.0

    def step(self, sim: "Simulation") -> None:
        grid, rng, p = sim.grid, sim.rng, sim.params

        # --- sense local urchins within hunt radius ---
        area = grid.moore_neighbors(self.x, self.y, p.otter_hunt_radius)
        area.append(grid.at(self.x, self.y))
        urchins = [o for c in area for o in c.occupants if isinstance(o, Otter) is False]
        urchins = [u for u in urchins if isinstance(u, Urchin) and u.alive]

        n = len(urchins)
        if n > 0:
            # Holling Type II functional response: f(N) = aN / (1 + a*h*N).
            # This saturates at 1/h as prey density rises (handling-time limit);
            # we read it as this otter's probability of capturing one urchin
            # this step, capped at 1.
            a, h = p.holling_a, p.holling_h
            capture_prob = min(1.0, (a * n) / (1.0 + a * h * n))
            prey = rng.choice(urchins)
            if rng.random() < capture_prob:
                prey.die()
                self.energy += p.otter_energy_gain
                self.hunger = 0.0
        else:
            # no prey adjacent: search a wider vision range and step toward the
            # nearest urchin (directed foraging); else random walk.
            self.hunger += 1.0
            target = self._nearest_urchin(grid, p.otter_vision)
            if target is not None:
                nx = self.x + _sign(_short_delta(target[0], self.x, grid.width))
                ny = self.y + _sign(_short_delta(target[1], self.y, grid.height))
                grid.move_agent(self, nx, ny)
            else:
                nx, ny = self._random_walk_target(grid, rng)
                grid.move_agent(self, nx, ny)

        # --- metabolism ---
        self.energy -= p.otter_metabolism
        self.age += 1

    def _nearest_urchin(self, grid: Grid, vision: int):
        """Return (x, y) of the closest urchin within Chebyshev ``vision``."""
        best = None
        best_d = vision + 1
        for r in range(1, vision + 1):
            for cell in grid.moore_neighbors(self.x, self.y, r):
                if any(isinstance(o, Urchin) for o in cell.occupants):
                    d = max(
                        abs(_short_delta(cell.x, self.x, grid.width)),
                        abs(_short_delta(cell.y, self.y, grid.height)),
                    )
                    if d < best_d:
                        best_d, best = d, (cell.x, cell.y)
            if best is not None:
                return best
        return best
