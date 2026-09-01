# MAKE REAL GENERATION

## End-to-End Pipeline

```
USER COMMAND
 → UNIVERSAL COMMAND ENGINE
 → CREATIVE DIRECTOR
 → DIRECTOR PLAN
 → SHOT PLAN
 → PROMPT COMPILER
 → MODEL ROUTER
 → GENERATION ENGINE
 → PROVIDER (Runway/Pika/Test)
 → RESULT DOWNLOAD (httpx)
 → FFPROBE VALIDATION
 → QUALITY GATES
 → REPAIR (if needed)
 → ASSET REGISTRATION
 → TIMELINE
 → EXPORT
```

## Orchestrator

The `JobOrchestrator` is a polling worker that:
- Processes one job at a time with `asyncio.Semaphore(3)` for concurrency
- Submits generation requests to providers
- Polls for completion every 5 seconds
- Downloads result video via `httpx`
- Validates with FFprobe
- Registers as project asset
- Updates real-time progress via Redis SSE

## Provider Adapters

All providers implement `VideoProviderAdapter`:
- `health_check()` → `ProviderHealth`
- `submit_generation(request, model_id)` → `GenerationResponse`
- `check_status(provider_job_id)` → `GenerationResponse`
- `cancel_job(provider_job_id)` → `bool`
- `get_result(provider_job_id)` → `GenerationResponse`
- `get_capabilities()` → `Set[ProviderCapability]`
- `get_supported_models()` → `List[ModelInfo]`

## Health States

| State | Meaning |
|-------|---------|
| AVAILABLE | Provider responding, model ready |
| DEGRADED | Provider responding but slow/limited |
| RATE_LIMITED | Provider returning 429 |
| UNAVAILABLE | Provider not responding |
| ERROR | Provider returning error |

## Verification

- 208 backend tests passing
- Provider adapter system tested
- Real generation pipeline tested
- Download/validate/register tested
