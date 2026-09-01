from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.providers.base import ProviderRegistry, ProviderCapability
from app.core.config import settings

router = APIRouter()


def get_provider_registry() -> ProviderRegistry:
    from app.main import provider_registry
    return provider_registry


@router.get("")
async def list_providers(registry: ProviderRegistry = Depends(get_provider_registry)):
    providers = []
    for name, provider in registry.get_all().items():
        providers.append({
            "name": name,
            "api_base": provider.api_base,
            "capabilities": [c.value for c in provider.get_capabilities()],
            "models": provider.get_supported_models(),
        })
    return providers


@router.get("/{provider_name}/health")
async def provider_health(provider_name: str, registry: ProviderRegistry = Depends(get_provider_registry)):
    provider = registry.get(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    health = await provider.health_check()
    return {"status": health.status, "latency_ms": health.latency_ms, "error": health.error}


@router.get("/capabilities/{capability}")
async def providers_by_capability(capability: str, registry: ProviderRegistry = Depends(get_provider_registry)):
    try:
        cap = ProviderCapability(capability)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid capability")
    providers = registry.get_by_capability(cap)
    return [{"name": p.name, "api_base": p.api_base, "models": p.get_supported_models()} for p in providers]
