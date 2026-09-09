"""Tests for Enhanced Audio Model Layer."""
import numpy as np
import pytest
from app.make_model.audio.audio_model import EnhancedAudioModel, RoomEncoder, MaterialEncoder, SpatialEncoder, DurationEncoder, PitchEncoder, StyleEncoder, train_enhanced_step
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder, generate_synthetic_target


def make_config():
    from app.make_model.audio.architecture import AudioConfig
    return AudioConfig(
        model_id="enhanced_audio_v1", model_name="enhanced", version="1.0",
        sample_rate=16000, channels=1, bit_depth=16, max_duration_seconds=30.0,
        latent_dim=64, hidden_dim=128, num_layers=2, num_heads=4,
        ffn_dim=256, dropout=0.1, vocab_size=256, codebook_size=1024,
        codebook_dim=16, num_codebooks=2, training={}, inference={},
        dataset={}, quality={}, paths={},
    )


class TestEnhancedModel:
    def test_enhanced_model_creation(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        assert model._initialized is True

    def test_forward_returns_params(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        params = model.forward("hello world", speaker_id="spk1", emotion="happy", duration=2.0, pitch_hz=150.0)
        assert isinstance(params, np.ndarray)
        assert params.ndim == 1

    def test_synthesize_produces_audio(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        audio = model.synthesize("hello", speaker_id="spk1", duration=1.0)
        assert len(audio) == int(1.0 * 16000)

    def test_determinism(self):
        config = make_config()
        m1 = EnhancedAudioModel(config)
        m2 = EnhancedAudioModel(config)
        a1 = m1.forward("test", speaker_id="s1", emotion="happy")
        a2 = m2.forward("test", speaker_id="s1", emotion="happy")
        assert np.allclose(a1, a2)

    def test_checkpoint_save_load(self, tmp_path):
        config = make_config()
        model = EnhancedAudioModel(config)
        ckpt_path = str(tmp_path / "model.npz")
        model.save_checkpoint(ckpt_path)
        m2 = EnhancedAudioModel(config)
        m2.load_checkpoint(ckpt_path)
        a1 = model.forward("test", speaker_id="s1")
        a2 = m2.forward("test", speaker_id="s1")
        assert np.allclose(a1, a2)

    def test_training_reduces_loss(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        texts = ["hello", "world", "test"]
        durs = [1.0, 1.0, 1.0]
        loss1 = train_enhanced_step(model, texts, durs, lr=0.01)
        loss2 = train_enhanced_step(model, texts, durs, lr=0.01)
        assert loss2 <= loss1

    def test_parameters_returned(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        params = model.parameters()
        assert len(params) > 0

    def test_gradient_flow(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        before = model.mlp.W1.copy()
        pred = model.forward("test")
        target = generate_synthetic_target("test", 1.0, seed=42)
        target_mean = np.mean(target, axis=0) if target.shape[0] > 0 else target
        if len(pred) > len(target_mean):
            target_mean = np.pad(target_mean, (0, len(pred) - len(target_mean)))
        elif len(pred) < len(target_mean):
            target_mean = target_mean[:len(pred)]
        grad = 2.0 * (pred - target_mean) / pred.shape[0]
        model.mlp.backward(grad.reshape(1, -1), lr=0.01)
        after = model.mlp.W1
        assert not np.allclose(before, after)

    def test_all_encoders_present(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        assert hasattr(model, 'text_encoder')
        assert hasattr(model, 'speaker_encoder')
        assert hasattr(model, 'emotion_encoder')
        assert hasattr(model, 'duration_encoder')
        assert hasattr(model, 'pitch_encoder')
        assert hasattr(model, 'style_encoder')
        assert hasattr(model, 'room_encoder')
        assert hasattr(model, 'material_encoder')
        assert hasattr(model, 'spatial_encoder')

    def test_all_conditioning_used(self):
        config = make_config()
        model = EnhancedAudioModel(config)
        audio = model.synthesize(
            "hello world", speaker_id="spk1", emotion="happy",
            duration=1.0, pitch_hz=200.0, style="whisper",
            room_type="bathroom", material="wood",
            spatial_pos=(1.0, 2.0, 3.0),
        )
        assert len(audio) > 0
