"""
SOTA Common Infrastructure (FAZ 0)

Shared modules used by all improved algorithms (E²BSO, R²DMA, P-AOEA).

Modules:
    multi_start_initializer  — Multi-start population generator (DNA #6)
    multi_layer_ls           — Multi-layer local search engine (DNA #3)
    penalty_manager          — Adaptive penalty manager (DNA #9)
    acceptance_criteria      — SA, LAHC, RTR acceptance (DNA #7)
    destroy_operators        — ALNS destroy operators (DNA #1 + #2)
    repair_operators         — ALNS repair operators (DNA #1 + #2)
    diversity_controller     — Population diversity management (DNA #8)
"""

import random as _random

from .multi_start_initializer import MultiStartInitializer
from .multi_layer_ls import MultiLayerLS
from .penalty_manager import PenaltyManager, PenaltyState
from .acceptance_criteria import (
    AcceptResult,
    AcceptanceCriterion,
    LateAcceptanceHC,
    RecordToRecordTravel,
    SimulatedAnnealing,
)
from .destroy_operators import (
    DestroyOperator,
    RandomRemoval,
    WorstRemoval,
    ShawRemoval,
    RelatedRemoval,
)
from .repair_operators import (
    RepairOperator,
    GreedyInsertion,
    Regret2Insertion,
    Regret3Insertion,
)
from .diversity_controller import DiversityController, DiversityState
SOTA_INFRA_VERSION = "3.0.0"

__all__ = [
    # Version
    "SOTA_INFRA_VERSION",
    # Initializer
    "MultiStartInitializer",
    # Local Search
    "MultiLayerLS",
    # Penalty
    "PenaltyManager",
    "PenaltyState",
    # Acceptance
    "AcceptResult",
    "AcceptanceCriterion",
    "SimulatedAnnealing",
    "LateAcceptanceHC",
    "RecordToRecordTravel",
    # Destroy
    "DestroyOperator",
    "RandomRemoval",
    "WorstRemoval",
    "ShawRemoval",
    "RelatedRemoval",
    # Repair
    "RepairOperator",
    "GreedyInsertion",
    "Regret2Insertion",
    "Regret3Insertion",
    # Diversity
    "DiversityController",
    "DiversityState",
]
