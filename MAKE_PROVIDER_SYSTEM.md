# MAKE PROVIDER SYSTEM

## Architecture

```
Provider Registry (singleton)
 ├── RunwayProvider
 │   ├── gen3a_turbo (10s, 1920x1080, seed, references)
 │   └── gen2 (4s, 1280x720, legacy)
 ├── PikaProvider
 │   ├── pika-1.0 (4s, 16:9/9:16/1:1/4:5)
 │   └── pika-1.5 (8s, V2V, extension)
 └── TestVideoProvider
     └── test-model-1 (10s, all capabilities)
```

## Interface

Every provider must implement:
- `health_check()` — returns `ProviderHealth(status, latency_ms, error)`
- `submit_generation(request, model_id)` — returns `GenerationResponse`
- `check_status(provider_job_id)` — returns `GenerationResponse`
- `cancel_job(provider_job_id)` — returns `bool`
- `get_result(provider_job_id)` — returns `GenerationResponse` or `None`
- `get_capabilities()` — returns `Set[ProviderCapability]`
- `get_supported_models()` — returns `List[ModelInfo]`

## Secrets

All API keys are server-side only. Never exposed to frontend.

## Error Normalization

Provider-specific errors are caught by orchestrator and stored in `Job.error`.

## Health Checks

Cached in Redis for 300s via `ProviderHealthService`.

## Model Router

`SmartModelRouterV3` considers:
- Capability match
- Duration compatibility
- Aspect ratio support
- Reference image support
- Provider health
- Quality/speed/cost preferences
- Character/product consistency requirements

## Verification

- TestVideoProvider always registered
- Provider adapters tested with mocked HTTP
- input_video_url support verified
- Health check states verified
