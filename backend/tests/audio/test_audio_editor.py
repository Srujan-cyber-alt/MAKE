"""Tests for Audio Editor."""
import numpy as np
import pytest
from app.make_model.audio.audio_editor import (
    AudioEditor, EditOperation, AudioArtifact, EditOperationRecord,
)


class TestAudioEditor:
    @pytest.fixture
    def editor(self):
        return AudioEditor(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(16000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_editor_creation(self, editor):
        assert editor.sample_rate == 16000
        assert len(editor.artifacts) == 0

    def test_register_artifact(self, editor, test_audio):
        artifact = editor.register_artifact(test_audio, parent_id=None)
        assert isinstance(artifact, AudioArtifact)
        assert len(artifact.artifact_id) == 16
        assert len(artifact.sha256) > 0
        assert artifact.duration > 0

    def test_cut(self, editor, test_audio):
        result = editor.cut(test_audio, 0.25, 0.75)
        expected_len = int(0.5 * 16000)
        assert abs(len(result) - expected_len) <= 1

    def test_fade_in(self, editor, test_audio):
        result = editor.fade_in(test_audio, duration=0.5)
        assert len(result) == len(test_audio)
        assert result[0] <= test_audio[0] * 0.1
        assert np.max(np.abs(result)) <= 0.99

    def test_fade_out(self, editor, test_audio):
        result = editor.fade_out(test_audio, duration=0.5)
        assert result[-1] <= test_audio[-1] * 0.1
        assert np.max(np.abs(result)) <= 0.99

    def test_loop(self, editor, test_audio):
        result = editor.loop(test_audio, num_repeats=3)
        assert len(result) == len(test_audio) * 3

    def test_reverse(self, editor, test_audio):
        result = editor.reverse(test_audio)
        assert len(result) == len(test_audio)
        assert np.allclose(result, test_audio[::-1])

    def test_pitch_shift(self, editor, test_audio):
        result = editor.pitch_shift(test_audio, semitones=4.0)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_time_stretch(self, editor, test_audio):
        result = editor.time_stretch(test_audio, rate=1.5)
        assert abs(len(result) - int(len(test_audio) * 1.5)) <= 1

    def test_normalize(self, editor, test_audio):
        result = editor.normalize(test_audio, target_peak=0.99)
        assert np.max(np.abs(result)) <= 0.99

    def test_eq(self, editor, test_audio):
        result = editor.eq(test_audio, low_gain=0.5, mid_gain=1.5, high_gain=0.8)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_compress(self, editor, test_audio):
        result = editor.compress(test_audio, threshold=0.2, ratio=4.0)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_denoise(self, editor, test_audio):
        result = editor.denoise(test_audio)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_spatialize(self, editor, test_audio):
        result = editor.spatialize(test_audio, azimuth=45, elevation=10, distance=3.0)
        assert result.shape[1] == 2

    def test_reverb(self, editor, test_audio):
        result = editor.reverb(test_audio, room_size=0.7, damping=0.5, wet_mix=0.3)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_delay(self, editor, test_audio):
        result = editor.delay(test_audio, delay_time=0.1, feedback=0.3, mix=0.3)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_execute_operation(self, editor, test_audio):
        result, artifact = editor.execute_operation(
            EditOperation.FADE_IN, test_audio, parameters={"duration": 0.3}
        )
        assert len(result) == len(test_audio)
        assert len(artifact.operations) == 1
        assert artifact.operations[0].op == EditOperation.FADE_IN

    def test_execute_operation_all_types(self, editor, test_audio):
        operations = [
            EditOperation.FADE_OUT, EditOperation.LOOP, EditOperation.REVERSE,
            EditOperation.NORMALIZE, EditOperation.REVERB, EditOperation.DELAY,
        ]
        for op in operations:
            result, artifact = editor.execute_operation(op, test_audio, parameters={})
            assert len(result) > 0 or op == EditOperation.LOOP or op == EditOperation.REVERSE

    def test_provenance_chain(self, editor, test_audio):
        _, artifact1 = editor.execute_operation(
            EditOperation.FADE_IN, test_audio, parameters={"duration": 0.2}
        )
        _, artifact2 = editor.execute_operation(
            EditOperation.NORMALIZE, test_audio, parent_artifact_id=artifact1.artifact_id, parameters={"target_peak": 0.5}
        )
        chain = editor.get_provenance_chain(artifact2.artifact_id)
        assert len(chain) >= 1

    def test_save_to_file(self, editor, test_audio, tmp_path):
        save_path = str(tmp_path / "test_output.wav")
        result, artifact = editor.execute_operation(
            EditOperation.FADE_IN, test_audio, parameters={"duration": 0.2}, save_path=save_path
        )
        assert Path(save_path).exists()
        assert Path(save_path).exists()

    def test_all_operations_functional(self, editor, test_audio):
        result = editor.loop(test_audio, num_repeats=2)
        assert len(result) > 0
        result = editor.reverse(test_audio)
        assert np.allclose(result, test_audio[::-1])
        result = editor.crossfade(test_audio, test_audio * 0.5)
        assert len(result) > 0
        result, _ = editor.execute_operation(EditOperation.REPLACE, test_audio, parameters={
            "start": 0.1, "end": 0.2, "replacement": np.zeros(1600, dtype=np.float32)
        })
        assert len(result) > 0
