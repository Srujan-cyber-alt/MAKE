# MAKE UNIVERSAL MODEL ENGINE

## Architecture Overview

```
CREATIVE REQUIREMENT
        ↓
TECHNICAL REQUIREMENTS
        ↓
CAPABILITY ENGINE (hard/soft filtering)
        ↓
MODEL ROUTER 4.0 (scoring, modes, fallback)
        ↓
PROMPT COMPILER (canonical → model-specific)
        ↓
PROVIDER ADAPTER (submit/status/download)
        ↓
OUTPUT NORMALIZER (canonical result)
        ↓
QUALITY VALIDATION
        ↓
BEST RESULT SELECTION
        ↓
PROVENANCE STORAGE
```

## Components

### Universal Model Registry
- Canonical model metadata
- Legacy model conversion
- Query by provider, capability, modality, status

### Canonical Provider Registry
- Provider health tracking
- Authentication status
- Rate limits, concurrency limits
- Region, latency, error rate

### Model Capability Engine
- Hard requirement elimination
- Soft requirement scoring
- Compatibility gaps analysis

### Model Router 4.0
- Routing modes: AUTO, FAST, QUALITY, CINEMATIC, CHEAP, BALANCED, CUSTOM
- Fallback chains
- Retry policy with exponential backoff
- Provider health integration
- Cost estimation integration

### Failure Intelligence
- 10 error types
- Retry/fallback policies
- User action requirements

### Provider Health Engine
- Rolling window metrics
- Success/failure/timeout tracking
- Automatic degradation

### Model Performance Memory
- Per-model/provider statistics
- Task-type-specific performance
- Redis-backed persistence

### Cost Engine
- Cost estimation
- Project-level tracking
- Unknown cost handling

### Routing Audit
- Explainable decisions
- Candidate elimination tracking
- Fallback chain logging

### Output Normalizer
- Canonical result format
- Provider-agnostic response handling
- Aspect ratio calculation

### Reference Manager
- Universal reference handling
- Model-specific validation
- First-frame/last-frame support

### Universal Prompt Compiler
- Canonical creative representation
- Model-specific compilation
- Negative prompt translation

### Input Preparation
- Resize, crop, aspect ratio
- Frame extraction
- Thumbnail creation

### Best Result Selection
- Objective-based ranking
- Multi-criteria scoring
- Variant selection

## Routing Modes

### AUTO
Best overall model balancing quality, speed, and cost.

### FAST
Optimize for latency. Prefer faster models.

### QUALITY
Optimize for visual quality. Prefer high-quality models.

### CINEMATIC
Optimize for cinematic output. Prefer models with cinematic strength.

### CHEAP
Optimize for cost. Prefer free or low-cost models.

### BALANCED
Balance all factors equally.

### CUSTOM
Advanced user controls for fine-tuning.

## Failure Types

| Type | Retryable | Fallback | User Action |
|------|-----------|----------|-------------|
| AUTH_ERROR | No | Yes | Yes |
| RATE_LIMIT | Yes | Yes | No |
| TEMPORARY_PROVIDER_FAILURE | Yes | Yes | No |
| INVALID_REQUEST | No | No | Yes |
| MODEL_UNAVAILABLE | No | Yes | No |
| CONTENT_POLICY_REJECTION | No | No | Yes |
| TIMEOUT | Yes | Yes | No |
| NETWORK_ERROR | Yes | Yes | No |
| OUTPUT_INVALID | No | Yes | No |
| UNKNOWN | Yes | Yes | No |

## Adding a New Provider

1. Create provider adapter inheriting from `VideoProviderAdapter`
2. Implement required methods: `health_check`, `submit_generation`, `check_status`, `cancel_job`, `get_result`, `get_capabilities`, `get_supported_models`
3. Register provider in `ProviderRegistry`
4. Add API credentials via environment variables
5. Provider automatically appears in Universal Model Registry

## Adding a New Model

1. Add model to provider adapter's `get_supported_models()`
2. Define `ModelInfo` with capabilities, limits, and metadata
3. Model automatically appears in Universal Model Registry
4. Routing automatically considers new model

## Testing

Run Phase 16 tests:
```bash
python3 -m pytest tests/test_phase16.py -v
```

Run full regression:
```bash
python3 -m pytest tests/ -v
```

## API Reference

See `backend/app/routers/universal_models.py` for endpoint definitions.
