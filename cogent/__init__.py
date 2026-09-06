"""Cogent: behavioral decentralization infrastructure for GenLayer validators."""

from .analysis import AnalysisConfig, analyze
from .models import Challenge, Observation, Outcome, ValidatorProfile

__all__ = [
    "AnalysisConfig",
    "Challenge",
    "Observation",
    "Outcome",
    "ValidatorProfile",
    "analyze",
]

__version__ = "0.1.0"
