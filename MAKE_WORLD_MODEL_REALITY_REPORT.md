# MAKE World Model X — Reality Report

Generated 2026-09-03 from the live audit endpoint.

## Verdict

```
audit.verdict            = PARTIAL
audit.verdict_reason     = MAKE World Model X has all engineering
                            modules but no real checkpoint has been
                            produced yet.
audit.owner              = MAKE
audit.owner_consistent   = True
audit.has_checkpoint     = False
audit.parameter_count    = 16,066,048    # default MEDIUM-preset param count
audit.suspicious_files   = []
audit.hardware.gpu_name  = ""
audit.hardware.cuda_available = False
audit.hardware.pytorch_available = False
audit.hardware.can_train_production = False
```

## Subsystem status

| Subsystem | Status | Why |
|---|---|---|
| Architecture code        | READY    | MakeWorldModelV0 + 4 presets |
| World representations    | READY    | objects / people / env / motion / camera / material |
| Conditioning compiler    | READY    | text / image / ref / camera / motion / world |
| Data engine              | READY    | ingest / dedup / quality / manifest / license |
| Curriculum               | READY    | 10 configurable stages + weighted sampler |
| Hard-example mining      | READY    | FailureRecord + HardExampleSet + WeightedSampler |
| Loss system              | READY    | 8 modular losses + total_loss |
| Training engine          | READY    | AdamW, EMA, grad clip, LR schedule, distributed config |
| Checkpointing            | READY    | numpy npz, SHA-256, owner=MAKE |
| Inference engine         | READY    | real decode, refuse-untrained, provenance sidecar |
| Evaluation harness       | READY    | 105 prompts × 20 categories |
| Ownership audit          | READY    | YES / PARTIAL / NO + weight scanner |
| Scaling table            | READY    | TINY..LARGE with param / VRAM estimates |
| **Trained weights**      | **NO**   | no checkpoint has been produced |
| **Real neural video**    | **NO**   | no inference has produced neural output |
| **GPU training**         | **BLOCKED** | no GPU on this host |

## Proof test

`tests/test_world_model.py::TestInference::test_real_training_inference_roundtrip`
exercises the entire chain:

1. instantiate a TINY model
2. run the trainer (3 steps, deterministic)
3. save the parameters as a `.npz`
4. register the checkpoint with owner=MAKE, SHA-256, arch_config
5. build a MakeWorldInferenceEngine against the registry
6. run an inference
7. assert the output is a real MP4 with a valid provenance sidecar

The proof test PASSES in this sandbox. It uses a *deterministic*
fake gradient (numpy reference); the resulting checkpoint is
explicitly NOT a real trained model. The point of the proof test
is to verify the pipeline plumbing — not to claim a real model.

## What has been built

- A from-scratch DiT-style transformer (`world/arch.py`) with
  spacetime tokens, 3D positional encoding, adaLN-Zero,
  self-attention, cross-attention, SwiGLU FFN
- Four size presets with real parameter counts
- A real data engine with SHA-256, perceptual dedup, ffprobe,
  quality scoring, scene detection, and a full manifest
- 10-stage curriculum and weighted sampling for hard examples
- 8 modular losses with configurable weights
- A production-grade training engine skeleton (AdamW, EMA, grad
  clip, LR schedule, distributed config)
- A real inference engine that refuses to fall back to FFmpeg and
  produces real MP4 output from a real checkpoint
- An evaluation harness with 105 prompts across 20 categories
- A weight-file scanner that flags any third-party model
- An audit that returns PARTIAL until a real checkpoint exists

## What has NOT been built

- A real trained model (no GPU)
- A real inference artifact (no checkpoint)
- A learned VAE / VAVAE decoder
- A real SentencePiece tokenizer
- A real CLIP-style image encoder for reference conditioning
- A real optical-flow model
- A real aesthetic scoring head
- A real benchmark on a competitor model (will be done after the
  first real MAKE checkpoint exists)

## Most important

The repository does NOT contain a trained MAKE proprietary video
model. It contains the engineering foundation that will, on a real
training host with a real GPU, produce the first real checkpoint.

We have not promised that MAKE will beat every other video model.
We have built the strongest training system we can, on this host,
without lying about what it can do today.
