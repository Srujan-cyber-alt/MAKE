import pytest
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse, ProviderHealth, ProviderCapability, ModelInfo, ModelLimits
from app.providers.runway import RunwayProvider
from app.providers.pika import PikaProvider
from app.providers.registry import ProviderRegistry


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        provider = RunwayProvider()
        registry.register(provider)
        assert registry.get("runway") is provider
        assert registry.get("nonexistent") is None

    def test_get_all(self):
        registry = ProviderRegistry()
        runway = RunwayProvider()
        pika = PikaProvider()
        registry.register(runway)
        registry.register(pika)
        all_providers = registry.get_all()
        assert len(all_providers) == 2
        assert "runway" in all_providers
        assert "pika" in all_providers

    def test_get_by_capability(self):
        registry = ProviderRegistry()
        runway = RunwayProvider()
        pika = PikaProvider()
        registry.register(runway)
        registry.register(pika)
        text_to_video_providers = registry.get_by_capability(ProviderCapability.TEXT_TO_VIDEO)
        assert len(text_to_video_providers) == 2
        video_to_video_providers = registry.get_by_capability(ProviderCapability.VIDEO_TO_VIDEO)
        assert len(video_to_video_providers) == 1
        assert video_to_video_providers[0].name == "pika"

    def test_get_provider_model(self):
        registry = ProviderRegistry()
        runway = RunwayProvider()
        registry.register(runway)
        model = registry.get_provider_model("runway", "gen3a_turbo")
        assert model is not None
        assert model.id == "gen3a_turbo"
        assert model.name == "Gen-3 Alpha Turbo"
        assert model.limits.max_duration_seconds == 10.0

    def test_get_provider_model_not_found(self):
        registry = ProviderRegistry()
        runway = RunwayProvider()
        registry.register(runway)
        model = registry.get_provider_model("runway", "nonexistent")
        assert model is None


class TestModelInfo:
    def test_runway_model_limits(self):
        provider = RunwayProvider()
        models = provider.get_supported_models()
        turbo = next(m for m in models if m.id == "gen3a_turbo")
        assert turbo.limits.max_duration_seconds == 10.0
        assert turbo.limits.max_reference_images == 3
        assert turbo.limits.supports_seed is True
        assert "16:9" in turbo.limits.supported_aspect_ratios
        assert "9:16" in turbo.limits.supported_aspect_ratios

    def test_pika_model_limits(self):
        provider = PikaProvider()
        models = provider.get_supported_models()
        pika_15 = next(m for m in models if m.id == "pika-1.5")
        assert ProviderCapability.VIDEO_TO_VIDEO in pika_15.capabilities
        assert ProviderCapability.VIDEO_EXTENSION in pika_15.capabilities

    def test_capability_discovery(self):
        runway = RunwayProvider()
        assert runway.supports_capability(ProviderCapability.TEXT_TO_VIDEO) is True
        assert runway.supports_capability(ProviderCapability.VIDEO_TO_VIDEO) is False
        assert runway.supports_capability(ProviderCapability.SEED_CONTROL) is True


class TestProviderCapabilities:
    def test_runway_capabilities_set(self):
        provider = RunwayProvider()
        caps = provider.get_capabilities()
        assert isinstance(caps, set)
        assert ProviderCapability.TEXT_TO_VIDEO in caps
        assert ProviderCapability.IMAGE_TO_VIDEO in caps
        assert ProviderCapability.REFERENCE_IMAGES in caps

    def test_pika_capabilities_set(self):
        provider = PikaProvider()
        caps = provider.get_capabilities()
        assert isinstance(caps, set)
        assert ProviderCapability.TEXT_TO_VIDEO in caps
        assert ProviderCapability.VIDEO_TO_VIDEO in caps
        assert ProviderCapability.ASPECT_RATIO in caps


class TestCommandInterpreter:
    def test_remove_person_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Remove the person on the left")
        assert result.operations[0]["operation"] == "object_removal"
        assert result.operations[0]["target"] == "person"

    def test_black_car_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Make the car black")
        assert result.operations[0]["operation"] == "object_recoloring"
        assert result.operations[0]["target"] == "car"

    def test_background_replacement_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Replace the background with a beach")
        assert result.operations[0]["operation"] == "background_replacement"

    def test_action_transformation_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Make the man run toward the camera")
        assert result.operations[0]["operation"] == "action_transformation"
        assert result.operations[0]["new_action"] == "run"

    def test_add_captions_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Add captions")
        assert result.operations[0]["operation"] == "add_captions"

    def test_video_extension_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Extend the video by 10 seconds")
        assert result.operations[0]["operation"] == "video_extension"

    def test_unknown_command(self):
        from app.routers.editing import AICommandInterpreter
        interpreter = AICommandInterpreter()
        result = interpreter.interpret("Do something completely random xyz")
        assert result.operations[0]["operation"] == "general_transform"
        assert result.confidence < 0.8
        assert result.requires_clarification is True
