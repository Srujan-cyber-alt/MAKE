from app.providers.base import ProviderRegistry

_provider_registry: Optional[ProviderRegistry] = None


def set_provider_registry(registry: ProviderRegistry):
    global _provider_registry
    _provider_registry = registry


def get_provider_registry() -> ProviderRegistry:
    if _provider_registry is None:
        raise RuntimeError("Provider registry not initialized. Call set_provider_registry() first.")
    return _provider_registry
