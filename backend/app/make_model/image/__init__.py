"""MAKE Image Engine — Core Architecture.

Implements the MAKE-native image intelligence stack:
- Foundation model architecture
- World representation
- Conditioning engine
- Generation/editing/reconstruction
- Identity/object/material/camera/lighting systems
- Training/inference pipelines
- Quality gate and provenance
"""

from __future__ import annotations

from app.make_model.image.arch import (
    ImageConfig,
    ImageFoundationModel,
    TextEncoder,
    VisionEncoder,
    IdentityEncoder,
    ObjectEncoder,
    SceneEncoder,
    SpatialEncoder,
    LatentCodec,
    DetailRefiner,
    SuperResolutionModule,
    QualityController,
)
from app.make_model.image.conditioning import (
    ConditioningEngine,
    ConditioningBundle,
    compose_conditioning,
)
from app.make_model.image.world import (
    WorldRepresentation,
    WorldState,
    Scene,
    Object,
    Human,
    Camera,
    Lighting,
    Material,
    Relationship,
    RealityDNA,
    WorldFork,
    CameraTeleport,
    TimeMachine,
    PersistentWorldState,
)
from app.make_model.image.identity import (
    IdentityGenome,
    IdentityEncoder,
    IdentityPreservationEngine,
)
from app.make_model.image.objects import (
    ObjectGenome,
    ObjectEncoder,
    ObjectManipulationEngine,
)
from app.make_model.image.camera import (
    CinemaCameraEngine,
    CameraParameters,
    CameraPath,
)
from app.make_model.image.lighting import (
    LightingDirector,
    LightSetup,
)
from app.make_model.image.materials import (
    MaterialLab,
    MaterialProperties,
)
from app.make_model.image.generation import (
    GenerationEngine,
    GenerationResult,
    ResolutionCascade,
)
from app.make_model.image.editing import (
    EditingEngine,
    EditOperation,
    IntentBrush,
)
from app.make_model.image.reconstruction import (
    RealityReconstruction,
    ReconstructionResult,
    VisualForensics,
    ImpossibleSceneEngine,
)
from app.make_model.image.quality import (
    QualityGate,
    QualityMetrics,
    PhotographicRealismEngine,
    DetailRecoveryEngine,
)
from app.make_model.image.provenance import (
    ProvenanceSystem,
    ProvenanceRecord,
)
from app.make_model.image.training import (
    ImageTrainingConfig,
    ImageTrainer,
    SyntheticDataEngine,
)
from app.make_model.image.inference import (
    ImageInferenceEngine,
    ImageInferenceRequest,
    ImageInferenceResult,
)
from app.make_model.image.dataset import (
    ImageDatasetConfig,
    ImageDatasetEngine,
    DatasetProvenance,
)
from app.make_model.image.evaluation import (
    ImageBenchmark,
    BenchmarkSuite,
    HumanEvaluationWorkflow,
)

__all__ = [
    "ImageConfig",
    "ImageFoundationModel",
    "ConditioningEngine",
    "ConditioningBundle",
    "WorldRepresentation",
    "WorldState",
    "RealityDNA",
    "IdentityGenome",
    "ObjectGenome",
    "CinemaCameraEngine",
    "LightingDirector",
    "MaterialLab",
    "GenerationEngine",
    "EditingEngine",
    "RealityReconstruction",
    "QualityGate",
    "ProvenanceSystem",
    "ImageTrainer",
    "ImageInferenceEngine",
    "ImageDatasetEngine",
    "ImageBenchmark",
]
