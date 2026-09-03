from app.providers.runway import RunwayProvider
from app.providers.pika import PikaProvider
from app.providers.test_provider import TestVideoProvider
from app.providers.local_provider import LocalProvider
from app.providers.base import ProviderRegistry, VideoProviderAdapter


def init_providers() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(LocalProvider())

    # MAKE proprietary model provider. Only registers as a real generation
    # path if a checkpoint exists; otherwise the provider's health() reports
    # UNAVAILABLE and generation requests fail with a structured error
    # rather than silently falling back to FFmpeg.
    try:
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        registry.register(MakeLocalNeuralProvider())
    except Exception:
        # never let the make_model package break provider init
        pass

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
