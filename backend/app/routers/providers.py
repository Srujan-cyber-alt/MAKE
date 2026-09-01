from fastapi import APIRouter, Depends, HTTPException
from app.providers.registry import get_provider_registry
from app.providers.base import ProviderRegistry, ProviderCapability, ModelInfo


def _serialize_model(model: ModelInfo) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "capabilities": [c.value if isinstance(c, ProviderCapability) else c for c in model.capabilities],
        "limits": {
            "max_duration_seconds": model.limits.max_duration_seconds,
            "min_duration_seconds": model.limits.min_duration_seconds,
            "max_width": model.limits.max_width,
            "max_height": model.limits.max_height,
            "supported_aspect_ratios": model.limits.supported_aspect_ratios,
            "max_input_images": model.limits.max_input_images,
            "max_reference_images": model.limits.max_reference_images,
            "supports_seed": model.limits.supports_seed,
            "supports_negative_prompt": model.limits.supports_negative_prompt,
            "supports_guidance_scale": model.limits.supports_guidance_scale,
            "cost_per_second": model.limits.cost_per_second,
        },
        "metadata": model.metadata,
    }


router = APIRouter()


def get_registry() -> ProviderRegistry:
    return get_provider_registry()


@router.get("")
async def list_providers(registry: ProviderRegistry = Depends(get_registry)):
    providers = []
    for name, provider in registry.get_all().items():
        providers.append({
            "name": name,
            "api_base": provider.api_base,
            "capabilities": [c.value for c in provider.get_capabilities()],
            "models": [_serialize_model(m) for m in provider.get_supported_models()],
        })
    return providers


@router.get("/{provider_name}/health")
async def provider_health(provider_name: str, registry: ProviderRegistry = Depends(get_registry)):
    provider = registry.get(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    health = await provider.health_check()
    return {"status": health.status, "latency_ms": health.latency_ms, "error": health.error}


@router.get("/capabilities/{capability}")
async def providers_by_capability(capability: str, registry: ProviderRegistry = Depends(get_registry)):
    try:
        cap = ProviderCapability(capability)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid capability")
    providers = registry.get_by_capability(cap)
    return [{"name": p.name, "api_base": p.api_base, "models": [_serialize_model(m) for m in p.get_supported_models()]} for p in providers]
