"""MAKE World Model X — Research timeline / roadmap.

The roadmap records, version-by-version, what is expected to exist,
what is in scope, what is NOT in scope, and which experiments are
planned. The actual results will be appended to each version as
experiments complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


# ----------------------------------------------------------------------
# Roadmap
# ----------------------------------------------------------------------


@dataclass
class RoadmapItem:
    version: str
    title: str
    scope: List[str]
    not_in_scope: List[str]
    parameter_target: str
    data_target: str
    gpu_target: str
    expected_metric: str
    notes: str = ""


ROADMAP: List[RoadmapItem] = [
    RoadmapItem(
        version="0.1.0-foundation",
        title="Foundation: architecture + data + training + inference skeleton",
        scope=[
            "spacetime DiT reference implementation (numpy)",
            "DDPM-style denoising loop",
            "multimodal conditioning compiler (text / image / ref / camera / motion)",
            "world / camera / motion / material representations",
            "data engine: ingest, dedup, quality scoring, sharding, license",
            "curriculum learning (10 configurable stages)",
            "hard-example mining hook",
            "training engine: AdamW, EMA, gradient clipping, LR schedule",
            "distributed-training readiness (config, env-based, no claim of multi-node)",
            "inference engine: refuse-untrained, real decode, provenance sidecar",
            "evaluation harness with 100+ prompts across 20 categories",
            "ownership audit",
        ],
        not_in_scope=[
            "real training run",
            "real inference output",
            "torch-only optimizations",
            "multi-node training",
            "external model comparison benchmarks",
        ],
        parameter_target="TINY (≤1M params) reference only",
        data_target="local user-supplied clips only",
        gpu_target="none required to ship the code",
        expected_metric="no metric; model is UNTRAINED",
    ),
    RoadmapItem(
        version="0.2.0",
        title="First real training: TINY on a small curated set",
        scope=[
            "real training on a single GPU",
            "real inference producing real video frames",
            "first checkpoints on disk",
            "first val-loss numbers",
        ],
        not_in_scope=[
            "competitor benchmarks",
            "production readiness",
            "long video / 4K",
        ],
        parameter_target="TINY (~0.3M)",
        data_target="≥ 10k short curated clips",
        gpu_target="1x RTX 4090 or A100 40GB",
        expected_metric="val recon loss only",
    ),
    RoadmapItem(
        version="0.3.0",
        title="Conditioning: image / reference / motion integration",
        scope=[
            "frozen image encoder (CLIP-ViT-B/32) for first-frame",
            "cross-attention ref slots for identity / product / world",
            "motion conditioning via optical flow",
            "camera conditioning via canonical CameraRepresentation",
        ],
        not_in_scope=[
            "real-time inference",
            "long video",
        ],
        parameter_target="SMALL (~3M)",
        data_target="≥ 100k clips with conditioning",
        gpu_target="1x A100 80GB",
        expected_metric="control-set accuracy on identity / camera",
    ),
    RoadmapItem(
        version="0.5.0",
        title="Scale to MEDIUM with progressive resolution",
        scope=[
            "MEDIUM preset (~30M params)",
            "progressive resolution training (32 -> 64 -> 128)",
            "curriculum stages 1-7 active",
            "hard-example mining on FailureIntelligence",
        ],
        not_in_scope=[
            "long video",
            "real-time",
        ],
        parameter_target="MEDIUM (~30M)",
        data_target="≥ 1M clips",
        gpu_target="4x A100 80GB",
        expected_metric="vs MAKE-LOCAL baseline on the 100-prompt eval",
    ),
    RoadmapItem(
        version="0.7.0",
        title="Temporal intelligence + 16-frame clips",
        scope=[
            "longer clips (16 frames)",
            "temporal attention strengthened",
            "identity persistence measurements",
        ],
        not_in_scope=["4K", "real-time"],
        parameter_target="MEDIUM (~30M)",
        data_target="≥ 5M clips",
        gpu_target="8x A100 80GB",
        expected_metric="temporal consistency on the long_temporal category",
    ),
    RoadmapItem(
        version="1.0.0",
        title="MAKE World Model X — first competitive release",
        scope=[
            "LARGE preset (~300M params)",
            "≥ 16 frames at 128 short-side",
            "controlled benchmark vs SOTA models on the 100-prompt set",
        ],
        not_in_scope=["real-time"],
        parameter_target="LARGE (~300M)",
        data_target="≥ 50M clips",
        gpu_target="16x H100 80GB or equivalent",
        expected_metric="documented win / draw / loss vs competitors per category",
    ),
]


def roadmap_dict() -> List[Dict[str, Any]]:
    return [
        {
            "version": r.version,
            "title": r.title,
            "scope": r.scope,
            "not_in_scope": r.not_in_scope,
            "parameter_target": r.parameter_target,
            "data_target": r.data_target,
            "gpu_target": r.gpu_target,
            "expected_metric": r.expected_metric,
            "notes": r.notes,
        }
        for r in ROADMAP
    ]


__all__ = ["RoadmapItem", "ROADMAP", "roadmap_dict"]
