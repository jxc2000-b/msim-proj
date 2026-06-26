from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Params:
    # --- this are the fraction of cells that support kelp ---
    width: int = 40
    height: int = 40
    rock_fraction: float = 0.85          # fraction of cells that support kelp

    # --- kelp (logistic resource regeneration) ---
    kelp_growth: float = 0.30            # g: this is the intrinsic regrowth rate per step
    kelp_max: float = 1.0                # B_max: the max kelp biomass that can grow on a rock cell
    kelp_init: float = 0.8               # initial rock cells that host the kelp 

    # --- urchins ---
    n_urchins0: int = 160
    urchin_graze: float = 0.18           # kelp biomass eaten per step when feeding
    urchin_metabolism: float = 0.07      # urchin energy burned per step
    urchin_repro_threshold: float = 1.6  # urchin energy needed to reproduce
    urchin_repro_prob: float = 0.13      # Bernoulli prob once above threshold
    urchin_repro_cost: float = 0.9       # energy paid to produce offspring
    urchin_base_mortality: float = 0.02  # urchin mortality at each step 

    # --- otters ---
    n_otters0: int = 35
    otter_mortality: float = 0.02        # CONTROL VARIABLE for collapse sweeps
    otter_metabolism: float = 0.105
    otter_hunt_radius: int = 1           # Moore neighborhood radius for hunting
    otter_vision: int = 3                # range for directed prey-seeking moves
    holling_a: float = 0.8               # attack rate (Holling Type II)
    holling_h: float = 0.4               # handling time (Holling Type II)
    otter_energy_gain: float = 1.15      # energy spent per urchin eaten
    otter_repro_threshold: float = 2.5
    otter_repro_prob: float = 0.12
    otter_repro_cost: float = 1.2

    # --- stochastic disturbance (Poisson events) ---
    storm_rate: float = 0.05             # lambda: expected storms per step
    storm_radius: int = 3                # radius of the environment reset by a storm
    disease_rate: float = 0.02           # lambda: expected urchin die-offs / step
    disease_kill_frac: float = 0.4       # fraction of local urchins killed

    # --- run control ---
    steps: int = 400
    seed: int = 0

    # --- initial agent energy ranges ---
    urchin_init_energy: float = 0.8
    otter_init_energy: float = 4.0

    extra: dict = field(default_factory=dict)
