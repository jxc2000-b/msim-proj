import random

from .agents import Agent, Otter, Urchin
from .datacollector import DataCollector
from .disturbance import DisturbanceModel
from .grid import Grid, GridCell, Kelp, SubstrateType
from .params import Params
from .scheduler import Scheduler


class Simulation:
    def __init__(self, params: Params | None = None):
        self.params = params or Params()
        self.rng = random.Random(self.params.seed)
        self.tick = 0
        self.grid = Grid(self.params.width, self.params.height)
        self.scheduler = Scheduler()
        self.disturbance = DisturbanceModel(
            self.params.storm_rate, self.params.disease_rate
        )
        self.collector = DataCollector()
        self.setup()

    # ------------------------------------------------------------------ setup
    def setup(self) -> None:
        p, rng = self.params, self.rng

        # build substrate + kelp
        for y in range(p.height):
            for x in range(p.width):
                if rng.random() < p.rock_fraction:
                    kelp = Kelp(p.kelp_init, p.kelp_growth, p.kelp_max)
                    sub = SubstrateType.ROCK
                else:
                    kelp = None
                    sub = SubstrateType.SAND
                self.grid.set_cell(GridCell(x, y, sub, kelp))

        # seed agents at random positions
        for _ in range(p.n_urchins0):
            self._spawn(Urchin(rng.randrange(p.width), rng.randrange(p.height),
                               p.urchin_init_energy))
        for _ in range(p.n_otters0):
            self._spawn(Otter(rng.randrange(p.width), rng.randrange(p.height),
                              p.otter_init_energy))

        self.collector.collect(self)  # record initial state at tick 0

    def _spawn(self, agent: Agent) -> None:
        self.scheduler.add(agent)
        self.grid.place(agent)

    def _kill(self, agent: Agent) -> None:
        self.scheduler.remove(agent)
        self.grid.remove(agent)

    # ------------------------------------------------------------------- loop
    def step(self) -> None:
        p, rng = self.params, self.rng

        # 1. resource update
        self.grid.regrow_kelp()

        # 2. agents sense & act
        self.scheduler.step(self)

        # 3. demographics: reproduction then death
        self._reproduce()
        self._resolve_death()

        # 4. stochastic (random storm) disturbance
        self.disturbance.maybe_fire(self)
        self._resolve_death()  # sweep out disease/storm casualties

        # 5. metrics
        self.tick += 1
        self.collector.collect(self)

    def _reproduce(self) -> None:
        p, rng = self.params, self.rng
        newborns: list[Agent] = []
        for a in self.scheduler.agents:
            if not a.alive:
                continue
            if isinstance(a, Urchin):
                if a.energy >= p.urchin_repro_threshold and rng.random() < p.urchin_repro_prob:
                    a.energy -= p.urchin_repro_cost
                    newborns.append(Urchin(a.x, a.y, p.urchin_repro_cost))
            elif isinstance(a, Otter):
                if a.energy >= p.otter_repro_threshold and rng.random() < p.otter_repro_prob:
                    a.energy -= p.otter_repro_cost
                    newborns.append(Otter(a.x, a.y, p.otter_repro_cost))
        for b in newborns:
            self._spawn(b)

    def _resolve_death(self) -> None:
        p, rng = self.params, self.rng
        for a in list(self.scheduler.agents):
            if not a.alive:
                self._kill(a)
                continue
            # starvation
            if a.energy <= 0.0:
                self._kill(a)
                continue
            # baseline / control mortality (form Bernoulli)
            if isinstance(a, Urchin):
                if rng.random() < p.urchin_base_mortality:
                    self._kill(a)
            elif isinstance(a, Otter):
                if rng.random() < p.otter_mortality:
                    self._kill(a)

    # ------------------------------------------------------------------- run
    def run(self, steps: int | None = None, verbose: bool = False):
        n = steps if steps is not None else self.params.steps
        for _ in range(n):
            self.step()
            if verbose and self.tick % max(1, n // 10) == 0:
                last = self.collector.records[-1]
                print(
                    f"  t={last['tick']:4d}  urchins={last['urchins']:4d}  "
                    f"otters={last['otters']:3d}  kelp_cover={last['kelp_cover']:.2f}"
                )
            if len(self.scheduler) == 0:
                break
        return self.collector.to_dataframe()

    # ----------------------------------------------------------- convenience
    def counts(self) -> tuple[int, int]:
        u = sum(isinstance(a, Urchin) for a in self.scheduler.agents)
        o = sum(isinstance(a, Otter) for a in self.scheduler.agents)
        return u, o
