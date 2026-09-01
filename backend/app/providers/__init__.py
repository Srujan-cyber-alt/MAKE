from app.providers.runway import RunwayProvider
from app.providers.pika import PikaProvider
from app.providers.base import ProviderRegistry, VideoProviderAdapter


def init_providers() -> ProviderRegistry:
    registry = ProviderRegistry()

    runway = RunwayProvider()
    if runway.api_key:
        registry.register(runway)

    pika = PikaProvider()
    if pika.api_key:
        registry.register(pika)

    return registry
