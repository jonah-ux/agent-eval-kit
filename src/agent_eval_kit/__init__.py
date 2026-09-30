"""Provider-neutral agent fixture evaluation."""

__version__ = "0.1.0"

from .models import EvaluationConfig, EvaluationResult, FileExpectation, FixtureResult
from .runner import run_config, run_fixture

__all__ = [
    "EvaluationConfig",
    "EvaluationResult",
    "FileExpectation",
    "FixtureResult",
    "run_config",
    "run_fixture",
    "__version__",
]
