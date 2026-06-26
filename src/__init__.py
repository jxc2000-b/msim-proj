from .agents import Agent, Otter, Urchin 
from .grid import Grid, GridCell, Kelp, SubstrateType
from .params import Params
from .simulation import Simulation


__version__ = "0.1.0"

__all__ = [
    "Agent", "Urchin", "Otter",
    "Grid", "GridCell", "Kelp", "SubstrateType",
    "Params", "Simulation", 
]