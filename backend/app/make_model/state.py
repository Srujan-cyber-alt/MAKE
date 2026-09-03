"""
MAKE model lifecycle state machine.

States progress only when there is real artifact evidence on disk.
No state is set by assertion or by wish.

Transitions:

  UNTRAINED                  : no architecture file, no checkpoint directory
  ARCHITECTURE_DEFINED       : arch code committed + passes forward smoke test
  DATASET_PREPARED           : a manifest exists with at least one usable video
  TRAINING                   : an active training run is in progress
  CHECKPOINT_AVAILABLE       : at least one valid checkpoint with manifest exists
  INFERENCE_READY            : checkpoint passes forward-pass smoke test on target
  PRODUCTION_READY           : inference has been validated on real prompts with
                                real outputs and the metrics are recorded

Any failure transitions the model back to its previous stable state and
records a FailureReason in the manifest.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional


class ModelState(str, Enum):
    UNTRAINED = "untrained"
    ARCHITECTURE_DEFINED = "architecture_defined"
    DATASET_PREPARED = "dataset_prepared"
    TRAINING = "training"
    CHECKPOINT_AVAILABLE = "checkpoint_available"
    INFERENCE_READY = "inference_ready"
    PRODUCTION_READY = "production_ready"
    FAILED = "failed"


TERMINAL_STATES = {ModelState.FAILED}


# Forward-only transitions. Backward transitions (e.g. INFERENCE_READY ->
# CHECKPOINT_AVAILABLE when a regression is found) are allowed and recorded.
ALLOWED_TRANSITIONS: Dict[ModelState, set] = {
    ModelState.UNTRAINED: {
        ModelState.ARCHITECTURE_DEFINED,
        ModelState.FAILED,
    },
    ModelState.ARCHITECTURE_DEFINED: {
        ModelState.DATASET_PREPARED,
        ModelState.UNTRAINED,  # regression: arch removed
        ModelState.FAILED,
    },
    ModelState.DATASET_PREPARED: {
        ModelState.TRAINING,
        ModelState.ARCHITECTURE_DEFINED,
        ModelState.FAILED,
    },
    ModelState.TRAINING: {
        ModelState.CHECKPOINT_AVAILABLE,
        ModelState.DATASET_PREPARED,
        ModelState.FAILED,
    },
    ModelState.CHECKPOINT_AVAILABLE: {
        ModelState.INFERENCE_READY,
        ModelState.TRAINING,  # additional training
        ModelState.FAILED,
    },
    ModelState.INFERENCE_READY: {
        ModelState.PRODUCTION_READY,
        ModelState.CHECKPOINT_AVAILABLE,  # new checkpoint replaces
        ModelState.FAILED,
    },
    ModelState.PRODUCTION_READY: {
        ModelState.INFERENCE_READY,  # new checkpoint in production
        ModelState.FAILED,
    },
    ModelState.FAILED: {ModelState.UNTRAINED},  # full reset
}


def can_transition(current: ModelState, target: ModelState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def validate_transition(current: ModelState, target: ModelState) -> None:
    if not can_transition(current, target):
        raise ValueError(
            f"Illegal MAKE model state transition: {current.value} -> {target.value}"
        )


def state_summary(state: ModelState) -> Dict[str, Any]:
    return {
        "state": state.value,
        "is_terminal": state in TERMINAL_STATES,
        "is_production": state == ModelState.PRODUCTION_READY,
        "is_inference_capable": state in {
            ModelState.INFERENCE_READY,
            ModelState.PRODUCTION_READY,
        },
        "has_checkpoint": state in {
            ModelState.CHECKPOINT_AVAILABLE,
            ModelState.INFERENCE_READY,
            ModelState.PRODUCTION_READY,
        },
        "trained": state not in {
            ModelState.UNTRAINED,
            ModelState.ARCHITECTURE_DEFINED,
            ModelState.DATASET_PREPARED,
        },
    }
