"""
MAKE proprietary model program — package root.

This package implements the foundation for MAKE's own learned neural video
generation model. It contains:

  - make_model.arch             : model architecture (from-scratch, MIT-licensed code)
  - make_model.dataset          : video frame dataset preparation
  - make_model.training         : training loop + experiment tracking
  - make_model.inference        : inference pipeline (loads MAKE checkpoints only)
  - make_model.registry         : checkpoint registry + provenance + integrity
  - make_model.utils            : shared utilities (config, logging, seeding)

Design principles (see MAKE_MODEL_PROGRAM.md for the full charter):

  1. NO third-party pretrained generative weights are used.
  2. The architecture is written from scratch in this repository.
  3. State is explicit: UNTRAINED -> TRAINING -> CHECKPOINT_AVAILABLE ->
     INFERENCE_READY -> PRODUCTION_READY. The state is derived from
     real artifacts, never from assertions or hope.
  4. Every checkpoint carries a manifest with SHA-256, training config,
     step count, loss curve summary, and a unique model id.
  5. Inference refuses to load any checkpoint that does not declare itself
     a MAKE-OWNED checkpoint.
  6. Optional heavy deps (torch, einops) are imported lazily so the package
     does not break existing systems that run without them.

Public entry points:

  - make_model.registry.list_checkpoints()
  - make_model.registry.get_status()
  - make_model.inference.MakeModelInference.load(checkpoint_id)
  - make_model.training.train(config_path)
"""

__version__ = "0.1.0"
__program__ = "MAKE Proprietary Video Model"
