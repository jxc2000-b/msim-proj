from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .agents import Otter, Urchin

if TYPE_CHECKING:
    from .simulation import Simulation


class DataCollector:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def collect(self, sim: "Simulation") -> None:
        urchins = sum(isinstance(a, Urchin) for a in sim.scheduler.agents)
        otters = sum(isinstance(a, Otter) for a in sim.scheduler.agents)

        rock_cells = 0
        kelp_biomass = 0.0
        kelp_covered = 0
        for cell in sim.grid.iter_cells():
            if cell.kelp is not None:
                rock_cells += 1
                kelp_biomass += cell.kelp.biomass
                if cell.kelp.biomass > 0.1 * cell.kelp.max_density:
                    kelp_covered += 1

        kelp_cover = kelp_covered / rock_cells if rock_cells else 0.0

        self.records.append(
            {
                "tick": sim.tick,
                "urchins": urchins,
                "otters": otters,
                "kelp_biomass": round(kelp_biomass, 3),
                "kelp_cover": round(kelp_cover, 4),
                "morans_i": round(self.morans_i(sim), 4),
            }
        )

    def morans_i(self, sim: "Simulation") -> float:
        """Moran's I of urchin counts over the grid (rook adjacency).

        Returns 0.0 when undefined (no variance / no urchins).
        """
        grid = sim.grid
        w, h = grid.width, grid.height
        counts = [[0 for _ in range(w)] for _ in range(h)]
        for a in sim.scheduler.agents:
            if isinstance(a, Urchin):
                counts[a.y][a.x] += 1

        flat = [counts[y][x] for y in range(h) for x in range(w)]
        n = len(flat)
        mean = sum(flat) / n
        denom = sum((v - mean) ** 2 for v in flat)
        if denom == 0:
            return 0.0

        num = 0.0
        wsum = 0
        for y in range(h):
            for x in range(w):
                zi = counts[y][x] - mean
                # 4-neighbor (rook) adjacency, toroidal
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = (x + dx) % w, (y + dy) % h
                    zj = counts[ny][nx] - mean
                    num += zi * zj
                    wsum += 1
        return (n / wsum) * (num / denom)

    def to_dataframe(self):
        try:
            import pandas as pd

            return pd.DataFrame(self.records)
        except ImportError:
            return self.records
