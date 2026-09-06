# MAKE Foundation-5B Training Handoff

## Current State

Software implementation: COMPLETE
Training execution: PENDING (requires GPU cluster)

## What Is Ready

1. Production architecture (~4.9B parameters)
2. Flow matching training objective
3. 19-conditioning pipeline
4. VideoVAE
5. Checkpoint system with provenance
6. Curriculum system (21 stages defined)
7. Data engine (acquisition pipeline)
8. Benchmark harness (105 prompts)
9. Production launcher
10. Final production gate

## What Is Required to Start Training

### Hardware
- 8x NVIDIA H100 80GB or A100 80GB
- NCCL-enabled interconnect
- 512GB+ system RAM
- 15TB+ NVMe storage

### Data
- ~850K licensed video clips
- Manifest with SHA-256, perceptual hashes
- Train/validation/test split verified for leakage
- All sources with commercial licenses

### Software
- PyTorch 2.x with CUDA
- NCCL
- FFmpeg
- Python dependencies from `backend/requirements.txt`

## First Command

```bash
python scripts/production_launcher.py train --config configs/production_5b.json
```

## Expected Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Dataset preparation | 2-4 weeks | Download, verify, deduplicate |
| Stage 1-7 (basic) | 1-2 weeks | Motion, camera, composition |
| Stage 8-14 (intermediate) | 2-3 weeks | People, identity, products |
| Stage 15-21 (advanced) | 3-4 weeks | Interaction, VFX, long-form |
| Total | 8-13 weeks | With 8x H100 |

## Verification Gates

After each stage:
1. Run validation set
2. Check quality metrics
3. Generate samples
4. Human review (if available)
5. Promote checkpoint if metrics improve

## Do Not

- Fabricate training results
- Call smoke-test output production
- Skip dataset license verification
- Merge train/validation/test data
- Claim cinematic quality without human evaluation

## Contact

All software issues: repository issues tracker
Hardware procurement: infrastructure team
Dataset licensing: legal team
