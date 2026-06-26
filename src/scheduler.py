from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agents import Agent
    from .simulation import Simulation


class Scheduler:
    def __init__(self) -> None:
        self.agents: list["Agent"] = []

    def add(self, agent: "Agent") -> None:
        self.agents.append(agent)

    def remove(self, agent: "Agent") -> None:
        if agent in self.agents:
            self.agents.remove(agent)

    def __len__(self) -> int:
        return len(self.agents)

    def step(self, sim: "Simulation") -> None:
        rng: random.Random = sim.rng
        order = self.agents[:]            # snapshot; new births act next tick
        rng.shuffle(order)
        for agent in order:
            if agent.alive:
                agent.step(sim)
