# MAKE Image Engine — Human Evaluation

## Evaluation Package

MAKE Image includes a human evaluation package generator for subjective quality assessment.

## Evaluation Criteria

For each generated sample, human evaluators rate:

1. **Realism** (1-10): Does this look like a real photograph?
2. **Cinematic quality** (1-10): Does this look like professional cinematography?
3. **Human quality** (1-10): Are humans rendered naturally?
4. **Detail** (1-10): Is fine detail present and coherent?
5. **Lighting** (1-10): Is lighting physically believable?
6. **Composition** (1-10): Is composition professional?
7. **Identity** (1-10): Is identity preserved across variations?
8. **Overall quality** (1-10): Overall impression

## Binary Questions

- "Would you mistake this for a real photograph?" YES / NO
- "Would you consider this production-ready?" YES / NO

## Evaluation Categories

A. Cinematic human portrait
B. Full-body human
C. Human + environment
D. Complex architecture
E. Product photography
F. Night cinematic scene
G. Daylight scene
H. Low-light portrait
I. Multi-person scene
J. Difficult hands/pose scene
K. Material-control sample
L. Camera-control sample
M. Lighting-control sample
N. Identity-consistency sequence
O. Editing-preservation sequence
P. 4K high-resolution sample

## Script

```bash
python3 scripts/image_human_eval.py --output-dir ./outputs/evaluations --samples 16
```

## Current Status

- Evaluation package generator: IMPLEMENTED
- Sample set: NOT GENERATED (no trained weights)
- Human evaluation: NOT PERFORMED

## Blocker

Human evaluation requires trained production weights and actual generated images.
