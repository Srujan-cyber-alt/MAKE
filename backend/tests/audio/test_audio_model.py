"""Tests for Enhanced Audio Model Layer."""
import numpy as np
import pytest
from app.make_model.audio.audio_model import EnhancedAudioModel, RoomEncoder, MaterialEncoder, SpatialEncoder, DurationEncoder, PitchEncoder, StyleEncoder, train_enhanced_step
from app.make_model.audio.architecture import AudioConfig


class TestEnhancedModel:
    def test_enhanced_model_creation(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        assert model._initialized is True

    def test_forward_returns_params(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        params = model.forward("hello world", speaker_id="spk1", emotion="happy", duration=2.0, pitch_hz=150.0)
        assert isinstance(params, np.ndarray)
        assert params.ndim == 1

    def test_synthesize_produces_audio(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        audio = model.synthesize("hello", speaker_id="spk1", duration=1.0)
        assert len(audio) == int(1.0 * 16000)

    def test_determinism(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        m1 = EAM(config)
        m2 = EAM(config)
        a1 = m1.forward("test", speaker_id="s1", emotion="happy")
        a2 = m2.forward("test", speaker_id="s1", emotion="happy")
        assert np.allclose(a1, a2)

    def test_checkpoint_save_load(self, tmp_path):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        ckpt_path = str(tmp_path / "model.npz")
        model.save_checkpoint(ckpt_path)
        m2 = EAM(config)
        m2.load_checkpoint(ckpt_path)
        a1 = model.forward("test", speaker_id="s1")
        a2 = m2.forward("test", speaker_id="s1")
        assert np.allclose(a1, a2)

    def test_training_reduces_loss(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        texts = ["hello", "world", "test"]
        durs = [1.0, 1.0, 1.0]
        loss1 = train_enhanced_step(model, texts, durs, lr=0.01)
        loss2 = train_enhanced_step(model, texts, durs, lr=0.01)
        assert loss2 < loss1

    def test_parameters_returned(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        params = model.parameters()
        assert len(params) > 0

    def test_room_encoder(self):
        enc = RoomEncoder(64)
        vec = enc.forward("bathroom")
        assert vec.shape == (64,)
        vec_none = enc.forward(None)
        assert vec_none.shape == (64,)
        vec_invalid = enc.forward("nonexistent")
        assert vec_invalid.shape == (64,)
        assert len(enc.parameters()) == 1

    def test_material_encoder(self):
        enc = MaterialEncoder(64)
        vec = enc.forward("wood")
        assert vec.shape == (64,)
        vec_none = enc.forward(None)
        assert vec_none.shape == (64,)

    def test_spatial_encoder(self):
        enc = SpatialEncoder(64)
        vec = enc.forward((1.0, 2.0, 3.0))
        assert vec.shape == (64,)
        vec_none = enc.forward(None)
        assert vec_none.shape == (64,)
        assert np.all(vec_none == 0)

    def test_duration_encoder(self):
        enc = DurationEncoder(64)
        vec = enc.forward(3.5)
        assert vec.shape == (64,)
        assert len(enc.parameters()) == 0

    def test_pitch_encoder(self):
        enc = PitchEncoder(64)
        vec = enc.forward(150.0)
        assert vec.shape == (64,)
        assert len(enc.parameters()) == 0

    def test_style_encoder(self):
        enc = StyleEncoder(embed_dim=64)
        vec = enc.forward("whisper")
        assert vec.shape == (64,)
        vec_none = enc.forward(None)
        assert vec_none.shape == (64,)
        vec_invalid = enc.forward("nonexistent")
        assert vec_invalid.shape == (64,)
        assert len(enc.parameters()) == 1

    def test_all_styles_supported(self):
        enc = StyleEncoder(embed_dim=64)
        expected_styles = ["neutral", "whisper", "shout", "hesitant", "sarcastic",
                          "confident", "nervous", "intimate", "authoritative",
                          "exhausted", "crying", "laughing", "breathy", "dramatic",
                          "urgent", "calm"]
        for style in expected_styles:
            vec = enc.forward(style)
            assert vec.shape == (64,)

    def test_gradient_flow(self):
        config = AudioConfig(sample_rate=16000, latent_dim=64, hidden_dim=128)
        from app.make_model.audio.tiny_model import EnhancedAudioModel as EAM
        model = EAM(config)
        before = model.mlp.W1.copy()
        pred = model.forward("test")
        from app.make_model.audio.tiny_model import generate_synthetic_target
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
