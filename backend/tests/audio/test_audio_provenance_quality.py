"""Provenance and quality tests for MAKE Audio."""

import pytest
import numpy as np
import os
from app.make_model.audio.provenance import AudioProvenanceTracker
from app.make_model.audio.quality import AudioQualityEvaluator
from app.make_model.audio.config_loader import load_audio_config
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder
from app.make_model.audio.inference import AudioInferenceEngine
from app.make_model.audio.architecture import GenerationRequest
import asyncio


class TestProvenance:
    def test_record_and_retrieve(self):
        tracker = AudioProvenanceTracker("/tmp/test_audio_prov_sec.json")
        record = tracker.record(
            artifact_id="prov_test_1",
            model_id="tiny",
            model_version="1.0",
            generation_parameters={"prompt": "test"},
            source_inputs=["input.wav"],
            transformations=[],
            content_hash="abc123",
        )
        assert record.artifact_id == "prov_test_1"
        retrieved = tracker.get_record("prov_test_1")
        assert retrieved is not None
        assert retrieved.content_hash == "abc123"

    def test_missing_record(self):
        tracker = AudioProvenanceTracker("/tmp/test_audio_prov_missing.json")
        assert tracker.get_record("nonexistent") is None

    def test_provenance_fields(self):
        tracker = AudioProvenanceTracker("/tmp/test_audio_prov_fields.json")
        record = tracker.record(
            artifact_id="prov_fields",
            model_id="m",
            model_version="v",
            generation_parameters={},
            source_inputs=[],
            transformations=[{"op": "enhance"}],
            content_hash="hash1",
        )
        assert record.model_id == "m"
        assert record.model_version == "v"
        assert record.transformations == [{"op": "enhance"}]
        assert record.content_hash == "hash1"


class TestQualityGate:
    def test_evaluate_valid_wav(self, tmp_path):
        import scipy.io.wavfile as wavfile
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        vocoder = TinyVocoder(sample_rate=config.sample_rate)
        params = model.forward("quality test", "s1", None)
        audio = vocoder.synthesize(params, 1.0)
        out = str(tmp_path / "quality.wav")
        wavfile.write(out, config.sample_rate, (audio * 32767).astype(np.int16))
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(out))
        assert report is not None
        assert hasattr(report, "snr_db")
        assert hasattr(report, "clipping_ratio")

    def test_evaluate_silence(self, tmp_path):
        import scipy.io.wavfile as wavfile
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        silence = np.zeros(int(config.sample_rate * 1.0), dtype=np.float32)
        out = str(tmp_path / "silence.wav")
        wavfile.write(out, config.sample_rate, (silence * 32767).astype(np.int16))
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(out))
        assert report.silence_ratio > 0.9
