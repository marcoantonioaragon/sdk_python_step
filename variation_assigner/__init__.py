"""Package exports for variation_assigner.

Expose the public SDK symbols from their implementation module.
"""

from .service import RemoteExperimentService, ExperimentConfig, AssignmentResult
from .step_python_local import VariationAssigner

__version__ = "0.1.0"

__all__ = [
    "VariationAssigner",
    "RemoteExperimentService",
    "ExperimentConfig",
    "AssignmentResult",
    "__version__",
]
