# MAKE World Model X — Temporal Learning

Temporal understanding is a first-class objective.

## Mechanisms

1. **Spacetime tokens.** The DiT operates on `(T*H*W/P^2)` tokens
   in one block, so attention already mixes time and space from
   layer 1.

2. **Diagonal positional encoding.** 3D sinusoidal encoding for
   `(T, H, W)`. This makes frame position explicit at every layer.

3. **Time embedding.** Sinusoidal embedding of diffusion timestep
   `t` enters the adaLN-Zero modulation in every block.

4. **Temporal consistency loss.** `temporal_consistency_loss(pred)`
   computes L1 between consecutive predicted frames:

   ```
   L_t = mean_t( | x_{t+1} - x_t | )
   ```

   Default weight: 0.1 (configurable; off when weight = 0).

5. **Motion consistency loss.** `motion_consistency_loss(pred, gt)`
   compares predicted optical flow to ground truth. The training
   data must contain optical-flow annotations; the data engine
   currently does not produce these (placeholder; future).

6. **Hard-example mining.** `WeightedSampler` upweights samples
   that the existing FailureIntelligence flagged as temporally bad.

7. **Reference persistence.** When the same character / product /
   world appears in consecutive frames of a clip, the reference
   conditioning forces the model to keep it stable.

## Why independent-frame generation is wrong

- A frame-by-frame generator has no notion of "this is the same
  person" across time. It samples i.i.d. pixels.
- It cannot enforce motion smoothness.
- It cannot enforce camera continuity.
- It cannot enforce lighting / scene continuity.

The DiT avoids this by attending across the full time axis at
every layer. The temporal consistency loss reinforces it.

## What is NOT yet implemented

- Real optical-flow computation in the data engine (placeholder)
- A learned flow model
- Explicit frame-correspondence supervision
- A "long-context" training mode that treats 16+ frame clips as
  one document (planned for 0.7.0)

## Status

| Capability | Status |
|---|---|
| Spacetime tokens           | YES |
| Diagonal positional enc    | YES |
| Time embedding             | YES |
| Temporal consistency loss  | YES (L1) |
| Motion consistency loss    | YES (signature; no GT yet) |
| Hard-example mining        | YES |
| Reference persistence      | YES (slots) |
| Flow supervision           | NOT IMPLEMENTED |
| Long-context mode          | NOT IMPLEMENTED |

## Where to read next

- `MAKE_WORLD_MODEL_TRAINING.md`
- `MAKE_WORLD_MODEL_EVALUATION.md` (long_temporal category)
