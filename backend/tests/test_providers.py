import pytest
from app.providers.base import VideoProviderAdapter, GenerationRequest, GenerationResponse, ProviderHealth
from app.providers.runway import RunwayProvider
from app.providers.pika import PikaProvider


class TestProviderAbstraction:
    def test_runway_provider_instantiation(self):
        provider = RunwayProvider()
        assert provider.name == "runway"
        assert provider.api_base == "https://api.runwayml.com/v1"

    def test_pika_provider_instantiation(self):
        provider = PikaProvider()
        assert provider.name == "pika"
        assert provider.api_base == "https://api.pika.art/v1"

    def test_runway_capabilities(self):
        provider = RunwayProvider()
        capabilities = provider.get_capabilities()
        assert "text_to_video" in [c.value for c in capabilities]
        assert "image_to_video" in [c.value for c in capabilities]

    def test_pika_capabilities(self):
        provider = PikaProvider()
        capabilities = provider.get_capabilities()
        assert "text_to_video" in [c.value for c in capabilities]
        assert "image_to_video" in [c.value for c in capabilities]
        assert "video_to_video" in [c.value for c in capabilities]

    def test_runway_models(self):
        provider = RunwayProvider()
        models = provider.get_supported_models()
        assert len(models) > 0
        assert "id" in models[0]
        assert "name" in models[0]

    def test_health_check_no_key(self):
        provider = RunwayProvider()
        health = asyncio.run(provider.health_check())
        assert health.status == "inactive"
        assert "API key" in health.error


import asyncio


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
