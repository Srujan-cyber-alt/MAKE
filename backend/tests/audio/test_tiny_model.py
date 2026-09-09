"""Tests for the real tiny numpy audio model."""

import pytest
import numpy as np
import os
import asyncio

from app.make_model.audio.tiny_model import (
    TinyAudioModel,
    TinyVocoder,
    train_step,
    verify_gradients,
    generate_synthetic_target,
)
from app.make_model.audio.config_loader import load_audio_config
from app.make_model.audio.training import AudioTrainingPipeline
from app.make_model.audio.inference import AudioInferenceEngine
from app.make_model.audio.architecture import GenerationRequest


class TestTinyModelArchitecture:
    def test_model_parameters_exist(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        params = model.parameters()
        assert len(params) > 0
        for p in params:
            assert isinstance(p, np.ndarray)

    def test_model_forward_shape(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        out = model.forward("hello", "speaker_1", "happy")
        assert out.shape == (64,)
        assert out.dtype == np.float32

    def test_different_texts_produce_different_outputs(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        out1 = model.forward("hello world", "s1", None)
        out2 = model.forward("goodbye world", "s1", None)
        assert not np.allclose(out1, out2)

    def test_same_seed_deterministic(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        m1 = TinyAudioModel(config, seed=42)
        m2 = TinyAudioModel(config, seed=42)
        out1 = m1.forward("test", "s1", "neutral")
        out2 = m2.forward("test", "s1", "neutral")
        assert np.allclose(out1, out2)


class TestTinyVocoder:
    def test_synthesize_wav_valid(self):
        vocoder = TinyVocoder(sample_rate=16000)
        params = np.zeros(64, dtype=np.float32)
        audio = vocoder.synthesize(params, duration=0.5)
        assert audio.dtype == np.float32
        assert len(audio) == 8000
        assert np.max(np.abs(audio)) <= 0.99 + 1e-6

    def test_different_params_produce_different_audio(self):
        vocoder = TinyVocoder(sample_rate=16000)
        p1 = np.zeros(64, dtype=np.float32)
        p2 = np.zeros(64, dtype=np.float32)
        p2[0] = 1.0
        a1 = vocoder.synthesize(p1, 0.5)
        a2 = vocoder.synthesize(p2, 0.5)
        assert not np.allclose(a1, a2)

    def test_save_wav_file(self, tmp_path):
        import scipy.io.wavfile as wavfile
        vocoder = TinyVocoder(sample_rate=16000)
        params = np.zeros(64, dtype=np.float32)
        audio = vocoder.synthesize(params, 0.5)
        out = str(tmp_path / "test.wav")
        wavfile.write(out, 16000, (audio * 32767).astype(np.int16))
        assert os.path.exists(out)
        sr, data = wavfile.read(out)
        assert sr == 16000
        assert len(data) == 8000


class TestTraining:
    def test_train_step_reduces_loss(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        text = "hello world"
        target = generate_synthetic_target(text, 1.0, seed=42)
        pred_before = model.forward(text, "s1", None)
        target_mean = np.mean(target, axis=0)
        loss_before = float(np.mean((pred_before - target_mean) ** 2))
        train_step(model, [text], [1.0], lr=1e-2)
        pred_after = model.forward(text, "s1", None)
        loss_after = float(np.mean((pred_after - target_mean) ** 2))
        assert loss_after < loss_before

    def test_gradients_are_nonzero(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        assert verify_gradients(model, "test") is True

    def test_training_pipeline(self):
        pipeline = AudioTrainingPipeline()
        asyncio.run(pipeline.initialize())
        batch = {"texts": ["one", "two", "three"], "durations": [1.0, 1.0, 1.0]}
        metrics = asyncio.run(pipeline.train_step(batch))
        assert "loss" in metrics
        assert metrics["loss"] >= 0.0

    def test_checkpoint_save_load(self, tmp_path):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        ckpt = str(tmp_path / "model.npz")
        model.save_checkpoint(ckpt)
        assert os.path.exists(ckpt)
        model2 = TinyAudioModel(config, seed=0)
        model2.load_checkpoint(ckpt)
        out1 = model.forward("test", "s1", "happy")
        out2 = model2.forward("test", "s1", "happy")
        assert np.allclose(out1, out2)


class TestDeterministicGeneration:
    def test_same_seed_same_audio(self, tmp_path):
        import scipy.io.wavfile as wavfile
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        engine1 = AudioInferenceEngine(config)
        engine2 = AudioInferenceEngine(config)
        asyncio.run(engine1.initialize())
        asyncio.run(engine2.initialize())
        req1 = GenerationRequest(prompt="hello", conditioning={"speaker": "s1"}, seed=42, duration_seconds=0.5)
        req2 = GenerationRequest(prompt="hello", conditioning={"speaker": "s1"}, seed=42, duration_seconds=0.5)
        r1 = asyncio.run(engine1.infer(req1))
        r2 = asyncio.run(engine2.infer(req2))
        sr1, d1 = wavfile.read(r1.audio_path)
        sr2, d2 = wavfile.read(r2.audio_path)
        assert sr1 == sr2
        assert np.allclose(d1, d2)

    def test_different_seed_different_audio(self, tmp_path):
        import scipy.io.wavfile as wavfile
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        engine = AudioInferenceEngine(config)
        asyncio.run(engine.initialize())
        req1 = GenerationRequest(prompt="hello", conditioning={"speaker": "s1"}, seed=1, duration_seconds=0.5)
        req2 = GenerationRequest(prompt="hello", conditioning={"speaker": "s1"}, seed=2, duration_seconds=0.5)
        r1 = asyncio.run(engine.infer(req1))
        r2 = asyncio.run(engine.infer(req2))
        sr1, d1 = wavfile.read(r1.audio_path)
        sr2, d2 = wavfile.read(r2.audio_path)
        assert not np.allclose(d1, d2)


class TestWAVValidity:
    def test_generated_wav_is_valid(self, tmp_path):
        import scipy.io.wavfile as wavfile
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        engine = AudioInferenceEngine(config)
        asyncio.run(engine.initialize())
        req = GenerationRequest(prompt="test audio", conditioning={"speaker": "s1"}, duration_seconds=1.0)
        result = asyncio.run(engine.infer(req))
        assert os.path.exists(result.audio_path)
        sr, data = wavfile.read(result.audio_path)
        assert sr == config.sample_rate
        assert data.dtype == np.int16
        assert len(data) > 0
        assert np.max(np.abs(data.astype(np.float32))) > 0
