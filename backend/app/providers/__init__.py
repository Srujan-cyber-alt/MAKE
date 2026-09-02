from app.providers.runway import RunwayProvider
from app.providers.pika import PikaProvider
from app.providers.test_provider import TestVideoProvider
from app.providers.local_provider import LocalProvider
from app.providers.base import ProviderRegistry, VideoProviderAdapter


def init_providers() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(LocalProvider())

    runway = RunwayProvider()
    if runway.api_key:
        registry.register(runway)
    else:
        registry.register(TestVideoProvider())

    pika = PikaProvider()
    if pika.api_key:
        registry.register(pika)

    registry.register(TestVideoProvider())

    return registry
