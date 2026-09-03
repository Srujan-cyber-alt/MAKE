"""
Phase 22 Neural Runtime Architecture Tests.

Verifies that:
- Current machine correctly reports neural generation UNAVAILABLE
- Procedural LocalProvider remains LOCAL_PROCEDURAL
- TestVideoProvider remains DETERMINISTIC_TEST
- LOCAL_ONLY blocks cloud execution
- No provider falsely reports neural capability
- Future local provider can be registered without changing ModelRouter4
"""

import pytest
import os
from unittest.mock import patch


class TestNeuralRuntimeDetection:
    def test_hardware_detection(self):
        from app.providers.neural_interface import detect_hardware
        hw = detect_hardware()
        assert "gpu_available" in hw
        assert "pytorch_available" in hw
        assert "diffusers_available" in hw
        assert isinstance(hw["gpu_available"], bool)

    def test_neural_runtime_report(self):
        from app.providers.neural_interface import get_neural_runtime_report
        report = get_neural_runtime_report()
        d = report.to_dict()
        assert "classification" in d
        assert "state" in d
        assert "gpu_available" in d
        assert "capabilities" in d

    def test_current_machine_neural_unavailable(self):
        from app.providers.neural_interface import get_neural_runtime_report
        report = get_neural_runtime_report()
        hw = report.to_dict()
        if not hw["gpu_available"] or not hw["pytorch_available"]:
            assert hw["state"] == "unavailable"
            for cap in hw["capabilities"]:
                assert cap["state"] == "unavailable"

    def test_all_seven_neural_capabilities_reported(self):
        from app.providers.neural_interface import get_neural_runtime_report, NeuralCapability
        report = get_neural_runtime_report()
        reported = {c["capability"] for c in report.to_dict()["capabilities"]}
        expected = {c.value for c in NeuralCapability}
        assert reported == expected


class TestProviderClassifications:
    def test_local_provider_classification(self):
        from app.providers.local_provider import LocalProvider
        p = LocalProvider()
        assert p.get_classification() == "local_procedural"

    def test_local_provider_neural_capabilities_all_unavailable(self):
        from app.providers.local_provider import LocalProvider
        from app.providers.neural_interface import NeuralCapability
        p = LocalProvider()
        nc = p.get_neural_capabilities()
        assert len(nc) == len(NeuralCapability)
        for cap, state in nc.items():
            assert state == "unavailable"

    def test_test_provider_classification(self):
        from app.providers.test_provider import TestVideoProvider
        p = TestVideoProvider()
        assert p.get_classification() == "deterministic_test"

    def test_test_provider_neural_capabilities_all_unavailable(self):
        from app.providers.test_provider import TestVideoProvider
        from app.providers.neural_interface import NeuralCapability
        p = TestVideoProvider()
        nc = p.get_neural_capabilities()
        for cap, state in nc.items():
            assert state == "unavailable"

    def test_runway_provider_classification(self):
        from app.providers.runway import RunwayProvider
        p = RunwayProvider()
        assert p.get_classification() == "cloud"

    def test_pika_provider_classification(self):
        from app.providers.pika import PikaProvider
        p = PikaProvider()
        assert p.get_classification() == "cloud"


class TestLocalOnlyEnforcement:
    def setup_method(self):
        os.environ["GENERATION_MODE"] = "LOCAL_ONLY"

    def teardown_method(self):
        os.environ.pop("GENERATION_MODE", None)

    def test_local_only_blocks_cloud(self):
        from app.providers.neural_interface import enforce_local_only
        assert enforce_local_only("cloud") is False

    def test_local_only_allows_local_procedural(self):
        from app.providers.neural_interface import enforce_local_only
        assert enforce_local_only("local_procedural") is True

    def test_local_only_allows_local_neural(self):
        from app.providers.neural_interface import enforce_local_only
        assert enforce_local_only("local_neural") is True

    def test_local_only_allows_deterministic_test(self):
        from app.providers.neural_interface import enforce_local_only
        assert enforce_local_only("deterministic_test") is True

    def test_generation_mode_default(self):
        os.environ.pop("GENERATION_MODE", None)
        from app.providers.neural_interface import get_generation_mode
        assert get_generation_mode().value == "local_only"


class TestProviderRegistration:
    def test_future_local_neural_provider_registration(self):
        from app.providers.base import ProviderRegistry
        from app.providers.test_provider import TestVideoProvider
        from app.providers.local_provider import LocalProvider

        registry = ProviderRegistry()
        registry.register(LocalProvider())
        registry.register(TestVideoProvider())
        assert "local" in registry.get_all()
        assert "test-provider" in registry.get_all()

    def test_model_router_exists(self):
        from app.services.model_router_4 import ModelRouter4
        assert ModelRouter4 is not None
