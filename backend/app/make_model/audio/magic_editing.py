"""
Magic Audio Editing - semantic command to structured operations.

Examples:
"Make the voice more confident."
"Remove the background hum."
"Make this sound like it is inside a bathroom."
"Move the speaker farther away."
"Make the footsteps heavier."
"Make the room larger."
"Make the voice whisper the last sentence."
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import numpy as np


class MagicCommandType(Enum):
    VOICE_CONFIDENCE = "voice_confidence"
    REMOVE_NOISE = "remove_noise"
    ENVIRONMENT_CHANGE = "environment_change"
    MOVE_AWAY = "move_away"
    HEAVIER_FOOTSTEPS = "heavier_footsteps"
    ROOM_LARGER = "room_larger"
    WHISPER_END = "whisper_end"
    VOICE_OLDER = "voice_older"
    VOICE_YOUNGER = "voice_younger"
    MAKE_ROBOTIC = "make_robotic"
    UNDERWATER = "underwater"
    TELEPHONE = "telephone"
    SPEED_UP = "speed_up"
    SLOW_DOWN = "slow_down"
    LOUDER = "louder"
    QUIETER = "quieter"
    ADD_REVERB = "add_reverb"
    REMOVE_REVERB = "remove_reverb"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    command_type: MagicCommandType
    parameters: Dict[str, Any]
    original_text: str
    confidence: float


@dataclass
class MagicEditResult:
    audio: np.ndarray
    commands: List[ParsedCommand]
    provenance: Dict[str, Any]


COMMAND_PATTERNS: List[Tuple[MagicCommandType, List[str], Dict[str, Any]]] = [
    (MagicCommandType.VOICE_CONFIDENCE, ["more confident", "confidence"], {"style": "confident"}),
    (MagicCommandType.REMOVE_NOISE, ["remove the background hum", "remove noise", "denoise", "clean up"], {}),
    (MagicCommandType.ENVIRONMENT_CHANGE, ["bathroom", "cave", "tunnel", "church", "studio", "underwater", "forest", "warehouse", "street", "bedroom", "theater", "metal room", "concrete bunker", "spaceship"], {}),
    (MagicCommandType.MOVE_AWAY, ["farther away", "move away", "further away", "distant"], {"distance_mult": 1.5}),
    (MagicCommandType.HEAVIER_FOOTSTEPS, ["footsteps heavier", "heavier steps", "louder footsteps"], {}),
    (MagicCommandType.ROOM_LARGER, ["room larger", "bigger room", "larger room", "more spacious"], {"room_size_mult": 1.5}),
    (MagicCommandType.WHISPER_END, ["whisper the last", "whisper the end", "whisper last sentence"], {}),
    (MagicCommandType.VOICE_OLDER, ["older voice", "make older", "sound older", "mature"], {}),
    (MagicCommandType.VOICE_YOUNGER, ["younger voice", "make younger", "sound younger"], {}),
    (MagicCommandType.MAKE_ROBOTIC, ["robot", "robotic", "metallic"], {}),
    (MagicCommandType.UNDERWATER, ["underwater", "under water"], {}),
    (MagicCommandType.TELEPHONE, ["telephone", "phone", "cell phone"], {}),
    (MagicCommandType.SPEED_UP, ["faster", "speed up", "quicker"], {"rate_mult": 1.2}),
    (MagicCommandType.SLOW_DOWN, ["slower", "slow down", "slow motion"], {"rate_mult": 0.8}),
    (MagicCommandType.LOUDER, ["louder", "increase volume", "more volume"], {"volume_mult": 1.3}),
    (MagicCommandType.QUIETER, ["quieter", "decrease volume", "softer", "lower volume"], {"volume_mult": 0.7}),
    (MagicCommandType.ADD_REVERB, ["more reverb", "add reverb", "more echo"], {"reverb_mult": 1.5}),
    (MagicCommandType.REMOVE_REVERB, ["less reverb", "remove reverb", "dry"], {"reverb_mult": 0.3}),
    (MagicCommandType.PAN_LEFT, ["pan left", "move left"], {"pan": -1.0}),
    (MagicCommandType.PAN_RIGHT, ["pan right", "move right"], {"pan": 1.0}),
]


class MagicEditor:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def parse_command(self, text: str) -> ParsedCommand:
        text_lower = text.lower().strip()
        for cmd_type, patterns, extra_params in COMMAND_PATTERNS:
            for pattern in patterns:
                if pattern in text_lower:
                    params = dict(extra_params)
                    if cmd_type == MagicCommandType.ENVIRONMENT_CHANGE:
                        matched_env = pattern
                        for env_name in ["bathroom", "cave", "tunnel", "church", "studio", "underwater", "forest", "warehouse", "street", "bedroom", "theater", "metal room", "concrete bunker", "spaceship"]:
                            if env_name in text_lower:
                                params["environment"] = env_name
                                break
                    confidence = 0.9
                    return ParsedCommand(cmd_type, params, text, confidence)
        return ParsedCommand(MagicCommandType.UNKNOWN, {}, text, 0.0)

    def execute_command(self, audio: np.ndarray, command: ParsedCommand) -> np.ndarray:
        ct = command.command_type
        params = command.parameters
        if ct == MagicCommandType.VOICE_CONFIDENCE:
            result = audio.copy()
            return np.clip(result * 1.1, -0.99, 0.99)
        elif ct == MagicCommandType.REMOVE_NOISE:
            from scipy import signal as scipy_signal
            b, a = scipy_signal.butter(4, 0.05, btype='high')
            return np.clip(scipy_signal.filtfilt(b, a, audio), -0.99, 0.99).astype(np.float32)
        elif ct == MagicCommandType.ENVIRONMENT_CHANGE:
            from app.make_model.audio.audio_teleportation import AudioTeleporter
            env = params.get("environment", "studio")
            teleporter = AudioTeleporter(self.sample_rate)
            return teleporter.teleport(audio, env, distance=2.5)
        elif ct == MagicCommandType.MOVE_AWAY:
            from app.make_model.audio.spatial_engine_v3 import SpatialEngineV3, Source
            engine = SpatialEngineV3(self.sample_rate)
            distance = params.get("distance_mult", 1.5) * 3.0
            return engine.spatialize_mono_source(audio, Source(0, 0, distance))[:, 0]
        elif ct == MagicCommandType.HEAVIER_FOOTSTEPS:
            return np.clip(audio * 1.5, -0.99, 0.99)
        elif ct == MagicCommandType.ROOM_LARGER:
            return np.clip(audio, -0.99, 0.99)
        elif ct == MagicCommandType.WHISPER_END:
            from app.make_model.audio.acting_v2 import ActingEngine, ActingStyle
            engine = ActingEngine(self.sample_rate)
            split_point = int(len(audio) * 0.7)
            first = audio[:split_point]
            second = engine.apply_style(audio[split_point:], ActingStyle.WHISPER)
            return np.concatenate([first, second])
        elif ct == MagicCommandType.VOICE_OLDER:
            from app.make_model.audio.audio_transforms import VoiceTransformer
            engine = VoiceTransformer(self.sample_rate)
            return engine.age_voice(audio, years=20)
        elif ct == MagicCommandType.VOICE_YOUNGER:
            from app.make_model.audio.audio_transforms import VoiceTransformer
            engine = VoiceTransformer(self.sample_rate)
            return engine.age_voice(audio, years=-10)
        elif ct == MagicCommandType.MAKE_ROBOTIC:
            return self._robotic_effect(audio)
        elif ct == MagicCommandType.UNDERWATER:
            from app.make_model.audio.audio_teleportation import AudioTeleporter
            teleporter = AudioTeleporter(self.sample_rate)
            return teleporter.teleport(audio, "underwater", distance=1.0)
        elif ct == MagicCommandType.TELEPHONE:
            from app.make_model.audio.audio_transforms import AudioEffect
            fx = AudioEffect(self.sample_rate)
            return fx.telephone(audio)
        elif ct == MagicCommandType.SPEED_UP:
            rate = params.get("rate_mult", 1.2)
            n = max(1, int(len(audio) * rate))
            indices = np.linspace(0, len(audio) - 1, n)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
        elif ct == MagicCommandType.SLOW_DOWN:
            rate = params.get("rate_mult", 0.8)
            n = max(1, int(len(audio) / rate)) if rate > 0 else len(audio)
            old_indices = np.linspace(0, len(audio) - 1, n)
            return np.interp(old_indices, np.arange(len(audio)), audio).astype(np.float32)
        elif ct == MagicCommandType.LOUDER:
            return np.clip(audio * params.get("volume_mult", 1.3), -0.99, 0.99)
        elif ct == MagicCommandType.QUIETER:
            return np.clip(audio * params.get("volume_mult", 0.7), -0.99, 0.99)
        elif ct == MagicCommandType.ADD_REVERB:
            from app.make_model.audio.audio_editor import AudioEditor, EditOperation
            editor = AudioEditor(self.sample_rate)
            result, _ = editor.execute_operation(EditOperation.REVERB, audio, parameters={"room_size": 0.7, "damping": 0.5, "wet_mix": 0.3})
            return result
        elif ct == MagicCommandType.REMOVE_REVERB:
            from scipy import signal as scipy_signal
            b, a = scipy_signal.butter(4, 0.1, btype='high')
            return np.clip(scipy_signal.filtfilt(b, a, audio), -0.99, 0.99).astype(np.float32)
        elif ct == MagicCommandType.PAN_LEFT:
            result = np.zeros((len(audio), 2), dtype=np.float32)
            result[:, 0] = audio * 1.0
            result[:, 1] = audio * 0.3
            return result
        elif ct == MagicCommandType.PAN_RIGHT:
            result = np.zeros((len(audio), 2), dtype=np.float32)
            result[:, 0] = audio * 0.3
            result[:, 1] = audio * 1.0
            return result
        else:
            return audio.copy()

    def _robotic_effect(self, audio: np.ndarray) -> np.ndarray:
        from scipy import signal as scipy_signal
        b, a = scipy_signal.butter(4, 0.15, btype='low')
        low = scipy_signal.filtfilt(b, a, audio)
        b, a = scipy_signal.butter(4, 0.3, btype='high')
        high = scipy_signal.filtfilt(b, a, audio)
        mod = np.sin(2 * np.pi * 30 * np.arange(len(audio)) / self.sample_rate)
        modulated = audio * (1 + 0.3 * mod)
        return np.clip(low + high * 0.3 + modulated * 0.4, -0.99, 0.99)

    def execute_commands(self, audio: np.ndarray, commands: List[str]) -> MagicEditResult:
        result = audio.copy()
        parsed: List[ParsedCommand] = []
        for cmd_text in commands:
            cmd = self.parse_command(cmd_text)
            parsed.append(cmd)
            if cmd.confidence > 0.5:
                result = self.execute_command(result, cmd)
        return MagicEditResult(
            audio=result,
            commands=parsed,
            provenance={
                "command_count": len(commands),
                "parsed_count": len(parsed),
                "methods": [c.command_type.value for c in parsed],
            },
        )
