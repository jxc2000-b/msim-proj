from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:  # avoid a runtime import cycle with agents
    from .agents import Agent


class SubstrateType(Enum):
    ROCK = "rock"   # supports kelp
    SAND = "sand"   # bare, no kelp growth


class Kelp:
    """Continuous kelp biomass living in a single cell.""" 
    
    __slots__ = ("biomass", "growth_rate", "max_density")

    def __init__(self, biomass: float, growth_rate: float, max_density: float):
        self.biomass = biomass
        self.growth_rate = growth_rate
        self.max_density = max_density

    def regrow(self) -> None:
        """Logistic growth: B_{t+1} = B_t + g*B_t*(1 - B_t/B_max)."""
        b = self.biomass
        self.biomass = b + self.growth_rate * b * (1.0 - b / self.max_density)
        if self.biomass > self.max_density:
            self.biomass = self.max_density

    def consume(self, amount: float) -> float:
        """Graze up to ``amount``; return the biomass actually eaten."""
        eaten = min(amount, self.biomass)
        self.biomass -= eaten
        return eaten


class GridCell:
    __slots__ = ("x", "y", "substrate", "temperature", "disturbed", "kelp", "occupants")

    def __init__(self, x: int, y: int, substrate: SubstrateType, kelp: Kelp | None):
        self.x = x
        self.y = y
        self.substrate = substrate
        self.temperature = 12.0
        self.disturbed = False
        self.kelp = kelp                      # None on SAND cells
        self.occupants: list["Agent"] = []

    @property
    def kelp_biomass(self) -> float:
        return self.kelp.biomass if self.kelp is not None else 0.0


class Grid:
    """A wrap-around (toroidal) 2D lattice of :class:`GridCell`."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.cells: list[list[GridCell]] = [
            [None for _ in range(width)] for _ in range(height)  # type: ignore[misc]
        ]

    def at(self, x: int, y: int) -> GridCell:
        x, y = self.wrap(x, y)
        return self.cells[y][x]

    def wrap(self, x: int, y: int) -> tuple[int, int]:
        return x % self.width, y % self.height

    def set_cell(self, cell: GridCell) -> None:
        self.cells[cell.y][cell.x] = cell

    def iter_cells(self) -> Iterator[GridCell]:
        for row in self.cells:
            for cell in row:
                yield cell

    def moore_neighbors(self, x: int, y: int, r: int = 1) -> list[GridCell]:
        """Cells within Chebyshev distance ``r`` (excluding the center)."""
        out = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx == 0 and dy == 0:
                    continue
                out.append(self.at(x + dx, y + dy))
        return out

    def place(self, agent: "Agent") -> None:
        self.at(agent.x, agent.y).occupants.append(agent)

    def remove(self, agent: "Agent") -> None:
        occ = self.at(agent.x, agent.y).occupants
        if agent in occ:
            occ.remove(agent)

    def move_agent(self, agent: "Agent", nx: int, ny: int) -> None:
        self.remove(agent)
        agent.x, agent.y = self.wrap(nx, ny)
        self.place(agent)

    def regrow_kelp(self) -> None:
        for cell in self.iter_cells():
            if cell.kelp is not None:
                cell.kelp.regrow()
