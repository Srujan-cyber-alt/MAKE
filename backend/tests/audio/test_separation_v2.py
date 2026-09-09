"""Tests for source separation, audio inpainting/outpainting, semantic editor."""

import numpy as np
import pytest

from app.make_model.audio.source_separator import SourceSeparator, SeparationMethod, SeparationPlan
from app.make_model.audio.audio_inpainter import AudioInpainter, InpaintMask, InpaintMethod
from app.make_model.audio.audio_outpainter import AudioOutpainter, OutpaintSpec, OutpaintMode
from app.make_model.audio.semantic_editor import SemanticEditor, SemanticCommand, SemanticEdit


class TestSourceSeparator:
    def test_plan_separation(self):
        sep = SourceSeparator()
        plan = sep.plan_separation(2, ["speech", "noise"])
        assert plan.num_sources == 2
        assert plan.source_names == ["speech", "noise"]

    def test_method_notes(self):
        sep = SourceSeparator(SeparationMethod.NMFD)
        plan = sep.plan_separation(2)
        assert "Non-negative" in plan.notes

    def test_separate_channels(self):
        sep = SourceSeparator()
        audio = np.linspace(-1.0, 1.0, 1000).astype(np.float32)
        sources = sep.separate(audio, num_sources=2)
        assert len(sources) == 2
        assert sources[0].size > 0
        assert sources[1].size > 0

    def test_to_dict(self):
        sep = SourceSeparator(SeparationMethod.BEAMFORMING)
        sep.plan_separation(3)
        data = sep.to_dict()
        assert data["method"] == "beamforming"
        assert "supported_methods" in data


class TestAudioInpainter:
    def test_linear_inpaint(self):
        inpainter = AudioInpainter()
        audio = np.linspace(0.0, 1.0, 100).astype(np.float32)
        mask = InpaintMask(start_sample=20, end_sample=40)
        result = inpainter.inpaint(audio, mask)
        assert result.size == audio.size
        assert np.all(result[20:40] >= 0.0)

    def test_cosine_inpaint(self):
        inpainter = AudioInpainter()
        audio = np.linspace(0.0, 1.0, 100).astype(np.float32)
        mask = InpaintMask(start_sample=20, end_sample=40, method=InpaintMethod.COSINE)
        result = inpainter.inpaint(audio, mask)
        assert result.size == audio.size

    def test_spline_inpaint(self):
        inpainter = AudioInpainter()
        audio = np.linspace(0.0, 1.0, 100).astype(np.float32)
        mask = InpaintMask(start_sample=20, end_sample=40, method=InpaintMethod.SPLINE)
        result = inpainter.inpaint(audio, mask)
        assert result.size == audio.size

    def test_sine_inpaint(self):
        inpainter = AudioInpainter()
        audio = np.linspace(0.0, 1.0, 100).astype(np.float32)
        mask = InpaintMask(start_sample=20, end_sample=40, method=InpaintMethod.SINE)
        result = inpainter.inpaint(audio, mask)
        assert result.size == audio.size

    def test_detect_silence(self):
        inpainter = AudioInpainter()
        audio = np.zeros(1000, dtype=np.float32)
        audio[200:400] = 0.5
        masks = inpainter.detect_silence(audio, threshold=0.1, min_length=50)
        assert len(masks) == 2

    def test_regions(self):
        inpainter = AudioInpainter()
        audio = np.linspace(0.0, 1.0, 100).astype(np.float32)
        masks = [InpaintMask(10, 20), InpaintMask(50, 60)]
        result = inpainter.inpaint_regions(audio, masks)
        assert result.size == audio.size


class TestAudioOutpainter:
    def test_extend_audio(self):
        outpainter = AudioOutpainter(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        result = outpainter.outpaint(audio, OutpaintSpec(target_duration=2.0, sample_rate=16000))
        assert result.size == 32000

    def test_loop_mode(self):
        outpainter = AudioOutpainter(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = outpainter.outpaint(audio, OutpaintSpec(target_duration=1.0, mode=OutpaintMode.LOOP, sample_rate=16000))
        assert result.size == 16000

    def test_smooth_mode(self):
        outpainter = AudioOutpainter(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = outpainter.outpaint(audio, OutpaintSpec(target_duration=1.0, mode=OutpaintMode.SMOOTH, sample_rate=16000))
        assert result.size == 16000

    def test_reverberant_mode(self):
        outpainter = AudioOutpainter(sample_rate=16000)
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)).astype(np.float32)
        result = outpainter.outpaint(audio, OutpaintSpec(target_duration=1.0, mode=OutpaintMode.REVERBERANT, sample_rate=16000))
        assert result.size == 16000


class TestSemanticEditor:
    def test_parse_remove_source(self):
        editor = SemanticEditor()
        edits = editor.parse("remove the horn")
        assert edits
        assert edits[0].command == SemanticCommand.REMOVE_SOURCE
        assert edits[0].parameters["source"] == "horn"

    def test_parse_change_emotion(self):
        editor = SemanticEditor()
        edits = editor.parse("make the voice angrier")
        assert edits
        assert edits[0].command == SemanticCommand.CHANGE_EMOTION

    def test_parse_extend_silence(self):
        editor = SemanticEditor()
        edits = editor.parse("extend silence by 2 seconds")
        assert edits
        assert edits[0].command == SemanticCommand.EXTEND_SILENCE

    def test_parse_mute_region(self):
        editor = SemanticEditor()
        edits = editor.parse("mute from 1.0 to 2.0")
        assert edits
        assert edits[0].target_region == (1.0, 2.0)

    def test_apply_mute(self):
        editor = SemanticEditor()
        audio = np.ones(16000, dtype=np.float32)
        edit = SemanticEdit(command=SemanticCommand.MUTE_REGION, target_region=(0.1, 0.2))
        result = editor.apply(audio, edit, sample_rate=16000)
        assert np.all(result[1600:3200] == 0.0)

    def test_apply_normalize(self):
        editor = SemanticEditor()
        audio = np.ones(16000, dtype=np.float32) * 0.5
        edit = SemanticEdit(command=SemanticCommand.NORMALIZE)
        result = editor.apply(audio, edit, sample_rate=16000)
        assert np.max(np.abs(result)) <= 1.0

    def test_apply_batch(self):
        editor = SemanticEditor()
        audio = np.ones(16000, dtype=np.float32)
        edits = [SemanticEdit(command=SemanticCommand.MUTE_REGION, target_region=(0.1, 0.2))]
        result = editor.apply_batch(audio, edits, sample_rate=16000)
        assert result.size == audio.size