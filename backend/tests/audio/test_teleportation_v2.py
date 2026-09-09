"""Tests for acoustic teleportation, microphone teleportation, microphone DNA."""

import numpy as np
import pytest

from app.make_model.audio.acoustic_teleportation import AcousticTeleportation, AcousticEnvironment, ENVIRONMENT_PROFILES
from app.make_model.audio.microphone_teleportation import MicrophoneTeleportation, MicrophoneDNA, PolarPattern, MIC_LIBRARY
from app.make_model.audio.microphone_dna import MicrophoneDNA as MicDNA


class TestAcousticTeleportation:
    def test_all_environments(self):
        tele = AcousticTeleportation(sample_rate=16000)
        for env in AcousticEnvironment:
            assert env.value in tele.available_environments()
            assert env in ENVIRONMENT_PROFILES

    def test_teleport_studio(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.STUDIO)
        assert result.size == audio.size

    def test_teleport_bathroom(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.BATHROOM)
        assert result.size == audio.size

    def test_teleport_church(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.CHURCH)
        assert result.size == audio.size

    def test_teleport_warehouse(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.WAREHOUSE)
        assert result.size == audio.size

    def test_teleport_car(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.CAR)
        assert result.size == audio.size

    def test_teleport_street(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.STREET)
        assert result.size == audio.size

    def test_teleport_forest(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.FOREST)
        assert result.size == audio.size

    def test_teleport_underwater(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.UNDERWATER)
        assert result.size == audio.size

    def test_teleport_mountain(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.MOUNTAIN)
        assert result.size == audio.size

    def test_teleport_bedroom(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.BEDROOM)
        assert result.size == audio.size

    def test_intensity(self):
        tele = AcousticTeleportation(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.teleport(audio, AcousticEnvironment.CHURCH, intensity=0.5)
        assert result.size == audio.size


class TestMicrophoneTeleportation:
    def test_polar_omni(self):
        tele = MicrophoneTeleportation(sample_rate=16000)
        gain = tele._polar_gain(PolarPattern.OMNI, 90)
        assert gain == 1.0

    def test_polar_cardioid(self):
        tele = MicrophoneTeleportation(sample_rate=16000)
        gain = tele._polar_gain(PolarPattern.CARDIOID, 0)
        assert gain > 0.9

    def test_polar_hypercardioid(self):
        tele = MicrophoneTeleportation(sample_rate=16000)
        gain = tele._polar_gain(PolarPattern.HYPERCARDIOID, 0)
        assert gain > 0.9

    def test_polar_figure8(self):
        tele = MicrophoneTeleportation(sample_rate=16000)
        gain = tele._polar_gain(PolarPattern.FIGURE8, 90)
        assert gain < 0.1

    def test_apply_mic(self):
        tele = MicrophoneTeleportation(sample_rate=16000)
        mic = MicrophoneDNA(mic_id="test_mic", distance=1.0)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = tele.apply(audio, mic)
        assert result.size == audio.size

    def test_get_mic(self):
        tele = MicrophoneTeleportation()
        mic = tele.get_mic("studio_condenser")
        assert mic.mic_id == "studio_condenser"

    def test_available_mics(self):
        tele = MicrophoneTeleportation()
        assert len(tele.available_mics()) > 0


class TestMicrophoneDNA:
    def test_constructor(self):
        dna = MicDNA(mic_id="mic1", distance=0.5, proximity_effect=0.8)
        assert dna.mic_id == "mic1"
        assert dna.distance == 0.5

    def test_to_dict_roundtrip(self):
        dna = MicDNA(mic_id="mic1", polar_pattern=PolarPattern.OMNI)
        data = dna.to_dict()
        restored = MicDNA.from_dict(data)
        assert restored.polar_pattern == PolarPattern.OMNI