"""Tests for Magic Audio Editing (semantic commands)."""
import numpy as np
import pytest
from app.make_model.audio.magic_editing import (
    MagicEditor, MagicCommandType, ParsedCommand, MagicEditResult,
)


class TestMagicEditing:
    @pytest.fixture
    def editor(self):
        return MagicEditor(sample_rate=16000)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_editor_creation(self, editor):
        assert editor.sample_rate == 16000

    def test_parse_confidence(self, editor):
        cmd = editor.parse_command("Make the voice more confident")
        assert cmd.command_type == MagicCommandType.VOICE_CONFIDENCE
        assert cmd.confidence > 0.8

    def test_parse_remove_noise(self, editor):
        cmd = editor.parse_command("Remove the background hum")
        assert cmd.command_type == MagicCommandType.REMOVE_NOISE

    def test_parse_environment_change(self, editor):
        cmd = editor.parse_command("Make this sound like it is inside a bathroom")
        assert cmd.command_type == MagicCommandType.ENVIRONMENT_CHANGE
        assert cmd.parameters.get("environment") == "bathroom"

    def test_parse_move_away(self, editor):
        cmd = editor.parse_command("Move the speaker farther away")
        assert cmd.command_type == MagicCommandType.MOVE_AWAY

    def test_parse_whisper_end(self, editor):
        cmd = editor.parse_command("Make the voice whisper the last sentence")
        assert cmd.command_type == MagicCommandType.WHISPER_END

    def test_parse_underwater(self, editor):
        cmd = editor.parse_command("Make it sound like underwater")
        assert cmd.command_type in [MagicCommandType.ENVIRONMENT_CHANGE, MagicCommandType.UNDERWATER]

    def test_parse_unknown(self, editor):
        cmd = editor.parse_command("this is not a recognized command")
        assert cmd.command_type == MagicCommandType.UNKNOWN
        assert cmd.confidence == 0.0

    def test_execute_confidence(self, editor, test_audio):
        cmd = editor.parse_command("Make the voice more confident")
        result = editor.execute_command(test_audio, cmd)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_execute_remove_noise(self, editor, test_audio):
        cmd = editor.parse_command("Remove the background hum")
        result = editor.execute_command(test_audio, cmd)
        assert len(result) == len(test_audio)
        assert np.max(np.abs(result)) <= 0.99

    def test_execute_environment(self, editor, test_audio):
        cmd = editor.parse_command("Make this sound like it is inside a bathroom")
        result = editor.execute_command(test_audio, cmd)
        assert len(result) > 0
        assert np.max(np.abs(result)) <= 0.99

    def test_execute_multiple_commands(self, editor, test_audio):
        result = editor.execute_commands(test_audio, [
            "Make the voice whisper the last sentence",
            "Remove the background hum",
            "Pan left speaker",
        ])
        assert isinstance(result, MagicEditResult)
        assert len(result.commands) == 3
        assert len(result.audio) > 0

    def test_all_command_types_executable(self, editor, test_audio):
        commands = [
            "Make the voice more confident",
            "Remove the background hum",
            "Make this sound like it is inside a bathroom",
            "Make the footsteps heavier",
            "Make the room larger",
            "Make the voice whisper the last sentence",
            "Make the voice sound older",
            "Make the voice sound younger",
            "Make it robotic",
            "Make it underwater style",
            "Make it sound telephone",
            "Make it faster",
            "Make it slower",
            "Make it louder",
            "Make it quieter",
            "Add reverb",
            "Pan left speaker",
            "Pan right speaker",
        ]
        result = editor.execute_commands(test_audio, commands)
        assert len(result.audio) > 0

    def test_parsed_command_has_provenance(self, editor, test_audio):
        result = editor.execute_commands(test_audio, [
            "Make it louder",
            "Remove the background hum",
        ])
        assert "method" in result.provenance or "command_count" in result.provenance
        assert result.provenance["command_count"] == 2
