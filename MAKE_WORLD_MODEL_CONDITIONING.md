# MAKE World Model X — Conditioning

Lives at `backend/app/make_model/world/conditioning.py`.

## What the compiler does

`ConditioningCompiler.compile(prompt, first_frame, references,
camera, motion, world, seed) -> ConditioningBundle`

It produces:

- `text_tokens`  — integer tokens (B, S) for the text
  conditioning. The real tokenizer (SentencePiece) will replace
  the deterministic UTF-8 mapper. The mapper is fully deterministic
  and unit-testable; nothing in the inference engine depends on
  the *source* of the tokens.
- `first_frame`  — image latent (B, C, 1, H, W) for the
  image-to-video path. Concat-ed along channels of the noisy
  latent in the model.
- `last_frame`   — image latent (B, C, 1, H, W) for the
  last-frame conditioning path (future).
- `ref_slots`    — (B, 4, D) reference slots for the
  multi-reference path. Identity, product, character, world all
  map to slots.
- `camera`       — CameraRepresentation (model-side conditioning
  via the existing CameraControlEngine).
- `motion`       — MotionRepresentation (model-side conditioning
  via the existing Vision Engine).
- `world`        — WorldSample (full world representation for
  scene-level conditioning).
- `seed`         — random seed.

## Conditioning modes

| Mode | Mechanism |
|---|---|
| Text only                 | text_tokens + diffusion timestep |
| Image to video            | text + first_frame (concat along channels) |
| Reference to video        | text + ref_slots (cross-attention) |
| Multi-reference to video  | text + ref_slots with up to 4 references |
| First frame to video      | text + first_frame |
| Last frame to video       | text + last_frame (planned) |
| Camera-controlled video   | text + camera |
| Motion-controlled video   | text + motion |
| World-conditioned video   | text + world |
| Identity-locked video     | text + identity reference (slot 0) |
| Product-locked video      | text + product reference (slot 1) |

## Integration with existing MAKE systems

The compiler does NOT re-implement:

- `AdvancedPromptCompiler`     — produces the prompt before we tokenize
- `VisionEngine`               — produces motion + flow (future)
- `CameraControlEngine`        — produces camera intent
- `IdentityEngine`             — produces identity embeddings (slot 0)
- `ProductSystem`              — produces product embeddings (slot 1)
- `WorldSystem`                — produces world embeddings (slot 2)
- `ReferenceManager`           — produces the reference sequence

The compiler accepts their outputs and turns them into the
model-side tensor vocabulary.

## Status

| Capability | Status |
|---|---|
| Text conditioning          | YES |
| First-frame conditioning    | YES |
| Last-frame conditioning     | INTERFACE ONLY |
| Reference slots            | YES (4 slots) |
| Camera conditioning         | INTERFACE (camera rep exists) |
| Motion conditioning         | INTERFACE (motion rep exists) |
| World conditioning          | INTERFACE (WorldSample exists) |
| Identity / product slots    | INTERFACE (slots exist) |
| Real SentencePiece tokenizer| NOT IMPLEMENTED |
| Real image encoder          | NOT IMPLEMENTED (placeholder hash) |
| Real camera encoder         | NOT IMPLEMENTED |
| Real motion encoder         | NOT IMPLEMENTED |

## Where to read next

- `MAKE_WORLD_MODEL_TRAINING.md`
- `MAKE_WORLD_MODEL_EVALUATION.md`
