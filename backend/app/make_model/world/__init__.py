"""MAKE World Model X — top-level package.

Modules:
    arch            - spacetime DiT architecture
    representation  - world / camera / motion / material representations
    conditioning    - multimodal conditioning compiler
    data_engine     - ingest / dedup / quality / sharding
    curriculum      - curriculum learning + hard-example mining
    losses          - loss functions and weights
    training        - trainer, optimizer, EMA, distributed config, experiment tracker
    inference       - inference engine + errors
    audit           - world-model ownership audit
    evaluation      - 20-category evaluation harness (no benchmarks until real inference)
    scaling         - model size presets and parameter / VRAM tables
    evaluation_set  - 100+ evaluation prompts across 20 categories
    timeline        - research timeline and roadmap

This package is designed to be importable WITHOUT torch. When torch
is available, the same code path is used (numpy arrays are passed
through torch.from_numpy / np.asarray).
"""

from .arch import MakeWorldModelConfig, MakeWorldModelV0
from .representation import (
    ObjectRepresentation,
    PersonRepresentation,
    EnvironmentRepresentation,
    MotionRepresentation,
    CameraRepresentation,
    MaterialRepresentation,
    WorldSample,
)
from .conditioning import ConditioningBundle, ConditioningCompiler
from .data_engine import (
    DataEngineConfig,
    DatasetManifest,
    QualityMetrics,
    SourceLicense,
    TrainingSample,
    ingest_directory,
    load_manifest,
    manifest_to_dict,
)
from .curriculum import (
    Curriculum,
    CurriculumStage,
    DEFAULT_STAGES,
    FailureRecord,
    HardExampleSet,
    WeightedSampler,
)
from .losses import (
    LossWeights,
    camera_adherence_loss,
    identity_consistency_loss,
    motion_consistency_loss,
    perceptual_loss,
    product_consistency_loss,
    reconstruction_loss,
    temporal_consistency_loss,
    text_alignment_loss,
    total_loss,
)
from .training import (
    DistributedConfig,
    ExperimentTracker,
    LRSchedule,
    OptimizerConfig,
    Trainer,
    TrainingConfig,
    TrainingMetrics,
)
from .inference import (
    MakeModelXArchitectureMismatch,
    MakeModelXCheckpointInvalid,
    MakeModelXCheckpointMissing,
    MakeModelXDependencyMissing,
    MakeModelXError,
    MakeModelXUntrainedError,
    MakeWorldInferenceEngine,
    MakeWorldInferenceRequest,
    MakeWorldInferenceResult,
)
from .audit import WorldModelAuditReport, run_world_ownership_audit
from .evaluation import (
    EVALUATION_PROMPTS,
    EvaluationHarness,
    EvaluationRow,
    EvaluationSummary,
)
from .scaling import ScalingRow, scaling_table, scaling_table_dict
from .roadmap import ROADMAP, RoadmapItem, roadmap_dict

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "MakeWorldModelConfig",
    "MakeWorldModelV0",
    "ObjectRepresentation",
    "PersonRepresentation",
    "EnvironmentRepresentation",
    "MotionRepresentation",
    "CameraRepresentation",
    "MaterialRepresentation",
    "WorldSample",
    "ConditioningBundle",
    "ConditioningCompiler",
    "DataEngineConfig",
    "DatasetManifest",
    "QualityMetrics",
    "SourceLicense",
    "TrainingSample",
    "ingest_directory",
    "load_manifest",
    "manifest_to_dict",
    "Curriculum",
    "CurriculumStage",
    "DEFAULT_STAGES",
    "FailureRecord",
    "HardExampleSet",
    "WeightedSampler",
    "LossWeights",
    "reconstruction_loss",
    "temporal_consistency_loss",
    "motion_consistency_loss",
    "text_alignment_loss",
    "identity_consistency_loss",
    "product_consistency_loss",
    "camera_adherence_loss",
    "perceptual_loss",
    "total_loss",
    "OptimizerConfig",
    "LRSchedule",
    "TrainingConfig",
    "TrainingMetrics",
    "Trainer",
    "DistributedConfig",
    "ExperimentTracker",
    "MakeWorldInferenceEngine",
    "MakeWorldInferenceRequest",
    "MakeWorldInferenceResult",
    "MakeModelXError",
    "MakeModelXUntrainedError",
    "MakeModelXCheckpointMissing",
    "MakeModelXCheckpointInvalid",
    "MakeModelXArchitectureMismatch",
    "MakeModelXDependencyMissing",
    "WorldModelAuditReport",
    "run_world_ownership_audit",
    "EVALUATION_PROMPTS",
    "EvaluationHarness",
    "EvaluationRow",
    "EvaluationSummary",
    "ScalingRow",
    "scaling_table",
    "scaling_table_dict",
    "ROADMAP",
    "RoadmapItem",
    "roadmap_dict",
]
