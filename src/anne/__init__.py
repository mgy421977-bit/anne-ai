"""
ANNE – Adaptive Neural Nexus Engine

Six-stage cognitive architecture with ethical core, fractal memory,
and Mythos curiosity engine.
"""

from anne.bridge import AnneMythosBridge
from anne.core.cognitive_state import CognitiveState, Consciousness, EthicScore, Hypothesis
from anne.core.decision_loop import DecisionLoop, DecisionResult
from anne.core.ethic_core import EthicCore
from anne.core.fail_fast import FailFastGate
from anne.core.pipeline import AnnePipeline
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.engine import MythosEngine
from anne.runtime import AnneRequest, AnneResponse, AnneRuntime
from anne.language_curriculum import ENGLISH_FOUNDATION, TURKISH_FOUNDATION
from anne.language_learning import (
    LanguageLearningEngine,
    LanguageLearningMission,
    LanguageObservation,
    LanguageProfile,
    LanguageStatus,
    LearningAuthorization,
    LearningSource,
)

__version__ = "0.1.0"
__all__ = [
    "AnneMythosBridge",
    "AnnePipeline",
    "CognitiveState",
    "Consciousness",
    "DecisionLoop",
    "DecisionResult",
    "EthicScore",
    "Hypothesis",
    "EthicCore",
    "FailFastGate",
    "FractalMemory",
    "MythosEngine",
    "AnneRequest",
    "AnneResponse",
    "AnneRuntime",
    "TURKISH_FOUNDATION",
    "ENGLISH_FOUNDATION",
    "LanguageLearningEngine",
    "LanguageLearningMission",
    "LanguageObservation",
    "LanguageProfile",
    "LanguageStatus",
    "LearningAuthorization",
    "LearningSource",
]