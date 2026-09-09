"""Tests for audio-to-audio transformations."""
from __future__ import annotations
import numpy as np, pytest, scipy.io.wavfile as wavfile, tempfile, os
from app.make_model.audio.audio_transforms import VoiceTransformer, AudioEffect

def _make_wav(path, sr=16000, duration=1.0, freq=220.0):
    t = np.linspace(0, duration, int(sr*duration), endpoint=False)
    audio = 0.3 * np.sin(2*np.pi*freq*t)
    wavfile.write(path, sr, (audio*32767).astype(np.int16))
    return path

class TestVoiceTransformer:
    @pytest.fixture
    def wav(self, tmp_path):
        path = str(tmp_path / "test.wav")
        _make_wav(path)
        return path

    def test_age_older(self, wav, tmp_path):
        out = str(tmp_path / "aged.wav")
        result = VoiceTransformer.age_voice(wav, "older", out)
        assert os.path.exists(result)

    def test_age_younger(self, wav, tmp_path):
        out = str(tmp_path / "young.wav")
        result = VoiceTransformer.age_voice(wav, "younger", out)
        assert os.path.exists(result)

    def test_age_child(self, wav, tmp_path):
        out = str(tmp_path / "child.wav")
        result = VoiceTransformer.age_voice(wav, "child", out)
        assert os.path.exists(result)

    def test_change_gender(self, wav, tmp_path):
        out = str(tmp_path / "gender.wav")
        result = VoiceTransformer.change_gender(wav, 1.3, out)
        assert os.path.exists(result)

    def test_auto_output_path(self, wav):
        result = VoiceTransformer.age_voice(wav, "older")
        assert os.path.exists(result)


class TestAudioEffects:
    @pytest.fixture
    def wav(self, tmp_path):
        path = str(tmp_path / "test.wav")
        _make_wav(path)
        return path

    @pytest.mark.parametrize("effect", ["telephone", "radio", "robot", "underwater", "alien"])
    def test_all_effects(self, wav, tmp_path, effect):
        out = str(tmp_path / f"{effect}.wav")
        result = AudioEffect.apply_effect(wav, effect, output_path=out)
        assert os.path.exists(result)

    def test_unknown_effect(self, wav):
        with pytest.raises(ValueError, match="Unknown effect"):
            AudioEffect.apply_effect(wav, "nonexistent")

    def test_deterministic(self, wav, tmp_path):
        out1 = str(tmp_path / "radio1.wav")
        out2 = str(tmp_path / "radio2.wav")
        r1 = AudioEffect.radio(wav, out1)
        r2 = AudioEffect.radio(wav, out2)
        sr1, d1 = wavfile.read(r1)
        sr2, d2 = wavfile.read(r2)
        np.testing.assert_array_equal(d1, d2)
