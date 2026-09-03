# MAKE World Model X — Provenance

## Inference provenance

Every output video from the MAKE World Model writes a
`*.provenance.json` sidecar with:

```json
{
  "ok": true,
  "code": "OK",
  "output_path": "...",
  "output_sha256": "...",
  "output_bytes": 12345,
  "model_name": "make-world-tiny",
  "checkpoint_id": "...",
  "checkpoint_sha256": "...",
  "arch_version": "0.1.0",
  "arch_config": { ... MakeWorldModelConfig ... },
  "seed": 0,
  "prompt": "...",
  "frames": 8, "fps": 8.0,
  "width": 64, "height": 64, "duration_seconds": 1.0,
  "inference_steps": 4, "elapsed_seconds": 0.12,
  "device": "cpu", "dtype": "float32",
  "hardware": { "cpu_cores": 4, "ram_gb": 11.9, "gpu_name": "", "pytorch_available": false },
  "software": { "make_model_version": "0.1.0", "numpy_version": "..." },
  "created_at": "2026-..."
}
```

## Checkpoint provenance

Every checkpoint is registered with a `CheckpointRecord` containing:

- `id`, `model_name`, `model_version`, `arch_version`
- `owner = "MAKE"` (loaders reject anything else)
- `path`, `sha256`, `bytes`
- `training_run_id`, `global_step`, `epoch`
- `config` (full arch config)
- `dataset_name`, `dataset_manifest_sha`
- `git_commit` (when in a git repo)
- `framework_version`, `pytorch_version`
- `metric_summary`

## Dataset provenance

Every `TrainingSample` carries:

- `source_path`, `source_sha256`, `source_bytes`
- `clip_path`, `clip_sha256`, `clip_bytes`
- `license` (source / license / permission_status /
  acquisition_method / notes)
- `dataset_version`
- `split` (deterministic by sample id)

## Integrity checks

`MakeModelRegistry.verify_checkpoint(cp_id)`:

1. Read the manifest
2. Recompute SHA-256 of the file
3. Compare to the manifest hash
4. Verify `owner == "MAKE"`
5. Verify `arch_config` matches the registered architecture

`MakeWorldInferenceEngine._load_model` performs all of the above
and refuses to load on any failure.

## What is NOT in provenance

- Secrets (no API keys, no auth tokens)
- External telemetry (no calls home)
- User personal data (only the prompt and seed)
- Fabricated metrics (every number is measured or absent)

## Status

| Capability | Status |
|---|---|
| Checkpoint SHA-256     | YES |
| Owner=MAKE enforcement | YES |
| Inference provenance sidecar | YES |
| Dataset SHA-256 + license | YES |
| Git commit capture    | YES (when in repo) |
| Hardware snapshot     | YES |
| Software snapshot     | YES |
| Repro from manifest   | YES |
| **External telemetry** | **NO (local only)** |

## Where to read next

- `MAKE_WORLD_MODEL_REALITY_REPORT.md`
