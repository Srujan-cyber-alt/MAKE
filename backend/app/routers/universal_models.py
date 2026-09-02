"""
Universal Models API Router for MAKE AI Video Phase 16.
"""

from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.universal_model_registry import UniversalModelRegistry
from app.services.canonical_provider_registry import CanonicalProviderRegistry
from app.services.model_router_4 import ModelRouter4, RoutingMode
from app.services.provider_connectivity_test import ProviderConnectivityTest
from app.services.model_performance_memory import model_performance_memory
from app.services.routing_audit import routing_audit
from app.services.provider_credential_manager import provider_credential_manager
from app.core.security import get_current_user
from app.models.models import User

router = APIRouter()

_um_registry = None
_cp_registry = None
_router = None


def get_universal_registry() -> UniversalModelRegistry:
    global _um_registry
    if _um_registry is None:
        from app.providers.registry import get_provider_registry
        legacy = get_provider_registry()
        _um_registry = UniversalModelRegistry.get_instance(legacy)
    return _um_registry


def get_canonical_registry() -> CanonicalProviderRegistry:
    global _cp_registry
    if _cp_registry is None:
        from app.providers.registry import get_provider_registry
        legacy = get_provider_registry()
        _cp_registry = CanonicalProviderRegistry.get_instance(legacy)
    return _cp_registry


def get_model_router() -> ModelRouter4:
    global _router
    if _router is None:
        um = get_universal_registry()
        cp = get_canonical_registry()
        from app.providers.registry import get_provider_registry
        legacy = get_provider_registry()
        _router = ModelRouter4(legacy, um, cp)
    return _router


@router.get("/models")
async def list_models(
    modality: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    registry = get_universal_registry()
    models = registry.get_all_models()
    if modality:
        models = [m for m in models if m.modality == modality]
    if capability:
        models = [m for m in models if capability in m.capabilities]
    if status:
        models = [m for m in models if m.status.value == status]
    return {"models": registry.to_dict()["models"], "total": len(models)}


@router.get("/models/{model_id}")
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
):
    registry = get_universal_registry()
    model = registry.get_model(model_id) or registry.get_legacy_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    data = registry.to_dict()
    for m in data["models"]:
        if m["id"] == model_id:
            return m
    raise HTTPException(status_code=404, detail="Model not found")


@router.get("/providers")
async def list_providers(current_user: User = Depends(get_current_user)):
    cp = get_canonical_registry()
    await cp.check_all_health()
    return cp.to_dict()


@router.get("/providers/{provider_id}/health")
async def get_provider_health(provider_id: str, current_user: User = Depends(get_current_user)):
    cp = get_canonical_registry()
    await cp.check_all_health()
    provider = cp.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider.get("health", {})


@router.post("/route")
async def route_model(request: Dict[str, Any], current_user: User = Depends(get_current_user)):
    router = get_model_router()
    try:
        from app.schemas.director import GenerationRequirement
        req = GenerationRequirement(**request.get("requirement", {}))
        selection = await router.route(req, preferences=request.get("preferences"))
        return {
            "selected_model": selection.model_id,
            "provider_id": selection.provider_id,
            "score": selection.score,
            "reasons": selection.reasons,
            "estimated_cost": selection.estimated_cost,
            "estimated_duration": selection.estimated_duration,
            "fallback_models": selection.fallback_models,
            "routing_mode": selection.routing_mode,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/routing/audit")
async def get_routing_audit(limit: int = Query(50), current_user: User = Depends(get_current_user)):
    events = await routing_audit.get_audit_log(limit=limit)
    return {"audit_log": events, "total": len(events)}


@router.get("/models/{model_id}/performance")
async def get_model_performance(model_id: str, provider_id: str, current_user: User = Depends(get_current_user)):
    stats = await model_performance_memory.get_model_stats(model_id, provider_id)
    return stats


@router.get("/providers/connectivity")
async def test_provider_connectivity(current_user: User = Depends(get_current_user)):
    cp = get_canonical_registry()
    test = ProviderConnectivityTest(cp)
    results = await test.test_all_providers()
    return results


@router.get("/credentials/status")
async def get_credential_status(current_user: User = Depends(get_current_user)):
    cp = get_canonical_registry()
    statuses = {}
    for provider_id in cp.get_all_providers().keys():
        statuses[provider_id] = provider_credential_manager.get_credential_status(provider_id)
    return statuses
