"""Tests for Audio Teleportation V2 - 14 environments."""
import numpy as np
import pytest
from app.make_model.audio.audio_teleportation import (
    AudioTeleporter, EnvironmentType, ENVIRONMENT_PRESETS, EnvironmentPreset,
)


class TestAudioTeleportation:
    @pytest.fixture
    def teleporter(self):
        return AudioTeleporter(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_teleporter_creation(self, teleporter):
        assert teleporter.sample_rate == 16000
        assert len(teleporter.presets) == 14

    def test_all_14_environments(self):
        expected = {"bedroom", "bathroom", "studio", "theater", "tunnel",
                    "cave", "street", "forest", "underwater", "warehouse",
                    "church", "metal_room", "concrete_bunker", "spaceship"}
        actual = set(ENVIRONMENT_PRESETS.keys())
        assert expected == actual

    def test_teleport_basic(self, teleporter, test_audio):
        result = teleporter.teleport(test_audio, "bathroom", distance=2.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_teleport_each_environment(self, teleporter, test_audio):
        for env in ENVIRONMENT_PRESETS:
            result = teleporter.teleport(test_audio, env, distance=3.0)
            assert len(result) > 0
            assert np.max(np.abs(result)) <= 0.99

    def test_different_environments_differ(self, teleporter, test_audio):
        bathroom = teleporter.teleport(test_audio, "bathroom")
        cave = teleporter.teleport(test_audio, "cave")
        forest = teleporter.teleport(test_audio, "forest")
        assert not np.allclose(bathroom, cave)
        assert not np.allclose(bathroom, forest)

    def test_underwater_effects(self, teleporter, test_audio):
        result = teleporter.teleport(test_audio, "underwater")
        result_studio = teleporter.teleport(test_audio, "studio")
        assert np.max(np.abs(result)) < np.max(np.abs(test_audio))

    def test_distance_attenuation(self, teleporter, test_audio):
        near = teleporter.teleport(test_audio, "studio", distance=1.0)
        far = teleporter.teleport(test_audio, "studio", distance=10.0)
        assert np.mean(np.abs(far)) < np.mean(np.abs(near))

    def test_get_environment_names(self, teleporter):
        names = teleporter.get_environment_names()
        assert len(names) == 14
        assert "bathroom" in names

    def test_get_preset(self, teleporter):
        preset = teleporter.get_preset("cave")
        assert preset is not None
        assert preset.name == "cave"
        assert preset.rt60 > 1.0

    def test_get_preset_invalid(self, teleporter):
        assert teleporter.get_preset("nonexistent") is None

    def test_stereo_teleport(self, teleporter, test_audio):
        stereo = np.column_stack([test_audio, test_audio * 0.8])
        result = teleporter.teleport_stereo(stereo, "church", distance=3.0)
        assert result.shape[1] == 2
        assert np.max(np.abs(result)) <= 0.99

    def test_custom_preset(self, teleporter, test_audio):
        custom = EnvironmentPreset("custom", 0.5, 1.0, 0.5, 0.3, 0.5, 6000, 100, 0.5, 8, 0.4)
        result = teleporter.teleport(test_audio, "studio", custom_preset=custom, distance=2.0)
        assert len(result) > 0

    def test_echo_in_tunnel(self, teleporter, test_audio):
        tunnel = teleporter.get_preset("tunnel")
        assert tunnel.echo_delay is not None
        assert tunnel.echo_delay > 0

    def test_church_long_reverb(self, teleporter, test_audio):
        church = teleporter.get_preset("church")
        assert church.rt60 > 2.0
        studio = teleporter.get_preset("studio")
        assert studio.rt60 < church.rt60

    def test_metal_room_high_reflection(self, teleporter):
        metal = teleporter.get_preset("metal_room")
        assert metal.reflection_strength > 0.5

    def test_concrete_bunker_low_absorption(self, teleporter):
        bunker = teleporter.get_preset("concrete_bunker")
        assert bunker.absorption < 0.3
