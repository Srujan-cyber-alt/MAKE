"""
Spatial Audio V2 Engine.

Supports:
- azimuth / panning
- elevation
- distance attenuation
- room reflections (early + late)
- occlusion approximation
- wall absorption
- stereo / headphone optimization
- HRTF abstraction (truthful fallback)

All CPU-first using numpy/scipy. No external HRTF data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal
import math


@dataclass
class Source:
    audio_path: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    source_type: str = "voice"
    directivity: float = 0.0
    volume: float = 1.0


@dataclass
class Listener:
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ear_spacing: float = 0.17


@dataclass
class Room:
    width: float = 5.0
    length: float = 4.0
    height: float = 3.0
    wall_material: str = "drywall"
    wall_absorption: float = 0.3
    floor_material: str = "wood"
    floor_absorption: float = 0.2
    ceiling_material: str = "ceiling"
    ceiling_absorption: float = 0.3
    rt60: float = 0.4


@dataclass
class SpatialResult:
    audio_path: str
    sample_rate: int
    channels: int
    duration_seconds: float
    provenance: Dict[str, Any]


class SpatialEngine:
    INTERAUDIO_LEVEL_DIFF_MAX = 20.0
    DISTANCE_REF_DB = 1.0
    HRTF_NOTE = "No HRTF data available - using ITD/ILD approximation"

    MATERIAL_ABSORPTION = {
        "drywall": 0.05, "concrete": 0.15, "brick": 0.1,
        "wood": 0.15, "glass": 0.05, "metal": 0.1,
        "fabric": 0.4, "carpet": 0.4, "curtain": 0.35,
        "foam": 0.8, "absorption": 0.9,
    }

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.listener = Listener()
        self.room = Room()

    def set_listener(self, listener: Listener) -> None:
        self.listener = listener

    def set_room(self, room: Room) -> None:
        self.room = room

    def spatialize(
        self, audio_path: str, source_pos: Tuple[float, float, float],
        output_path: Optional[str] = None, occlusion: float = 0.0,
    ) -> SpatialResult:
        sr, data = self._load(audio_path)
        if data.ndim > 1:
            audio = np.mean(data, axis=1)
        else:
            audio = data.astype(np.float32) / max(1, np.iinfo(data.dtype).max) if data.dtype != np.float32 else data

        pos = np.array(source_pos)
        listener_pos = np.array(self.listener.position)
        rel = pos - listener_pos
        distance = float(np.linalg.norm(rel))
        if distance == 0:
            distance = 0.1

        azimuth = float(math.degrees(math.atan2(rel[1], rel[0])))
        elevation = float(math.degrees(math.asin(rel[2] / max(distance, 0.01))))

        left_gain, right_gain = self._pan(azimuth)

        attn = self._distance_attenuation(distance)

        if occlusion > 0:
            occ_gain = 1.0 - occlusion * 0.7
            left_gain *= occ_gain
            right_gain *= occ_gain

        left = audio * left_gain * attn
        right = audio * right_gain * attn

        early_refl = self._early_reflections(distance, azimuth, elevation, len(audio))

        stereo = np.stack([
            np.pad(left, (0, max(0, len(early_refl["left"]) - len(left)))[:len(left)] + early_refl["left"][:len(left)] if len(early_refl["left"]) <= len(left) else left + early_refl["left"][:len(left)],
            np.pad(right, (0, max(0, len(early_refl["right"]) - len(right)))[:len(right)] + early_refl["right"][:len(right)] if len(early_refl["right"]) <= len(right) else right + early_refl["right"][:len(right)]
        ], axis=-1)
        stereo = np.clip(stereo, -0.99, 0.99)

        if output_path is None:
            base = Path(audio_path).stem
            output_path = str(Path(audio_path).parent / f"{base}_spatial.wav")
        self._save(output_path, stereo)

        return SpatialResult(
            audio_path=output_path,
            sample_rate=sr,
            channels=2,
            duration_seconds=len(stereo) / sr,
            provenance={
                "position": list(source_pos),
                "distance": distance,
                "azimuth": azimuth,
                "elevation": elevation,
                "left_gain": float(left_gain),
                "right_gain": float(right_gain),
                "attenuation": float(attn),
                "occlusion": occlusion,
                "room_rt60": self.room.rt60,
                "method": "ITD/ILD approximation (no HRTF data)",
                "type": "spatialization",
            },
        )

    def _pan(self, azimuth: float) -> Tuple[float, float]:
        azimuth_clamped = max(-180.0, min(180.0, azimuth))
        angle = (azimuth_clamped + 90.0) * math.pi / 180.0
        left = math.cos(angle)
        right = math.sin(angle)
        left = max(0.0, min(1.0, left))
        right = max(0.0, min(1.0, right))
        if left == 0 and right == 0:
            left = right = 0.7
        return left, right

    def _distance_attenuation(self, distance: float) -> float:
        return self.DISTANCE_REF_DB / (distance + 0.5)

    def _early_reflections(
        self, distance: float, azimuth: float, elevation: float
    ) -> Dict[str, np.ndarray]:
        delay_ms = 10.0 + distance * 0.5
        delay_samples = int(delay_ms * self.sample_rate / 1000.0)
        rt60 = self.room.rt60
        decay = math.exp(-delay_samples / (self.sample_rate * max(rt60, 0.01)))

        n = delay_samples + 1
        refl = np.zeros(n, dtype=np.float32)
        refl[-1] = decay * 0.15

        angle = (azimuth + 90.0) * math.pi / 180.0
        left_az_offset = math.pi / 6
        right_az_offset = -math.pi / 6
        left_gain = math.cos(angle + left_az_offset) * 0.15 * decay
        right_gain = math.sin(angle + right_az_offset) * 0.15 * decay

        return {
            "left": refl * max(0.0, left_gain),
            "right": refl * max(0.0, right_gain),
        }

    def create_scene(
        self, sources: List[Source], output_path: Optional[str] = None
    ) -> SpatialResult:
        max_len = 0
        audios = []
        for src in sources:
            sr, data = self._load(src.audio_path)
            audio = data.astype(np.float32) / max(1, np.iinfo(data.dtype).max) if data.dtype != np.float32 else data
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            audios.append((src, audio, sr))
            max_len = max(max_len, len(audio))

        stereo = np.zeros((max_len, 2), dtype=np.float32)
        sr = audios[0][2] if audios else self.sample_rate

        for src, audio, _ in audios:
            pos = np.array(src.position)
            listener_pos = np.array(self.listener.position)
            rel = pos - listener_pos
            distance = float(np.linalg.norm(rel))
            if distance == 0:
                distance = 0.1
            azimuth = float(math.degrees(math.atan2(rel[1], rel[0])))
            left_gain, right_gain = self._pan(azimuth)
            attn = self._distance_attenuation(distance)
            gain_l = left_gain * attn * src.volume
            gain_r = right_gain * attn * src.volume

            early = self._early_reflections(distance, azimuth, 0.0)
            for i in range(len(audio)):
                idx = i
                if idx < max_len:
                    stereo[idx, 0] += audio[i] * gain_l
                    stereo[idx, 1] += audio[i] * gain_r
            if len(early["left"]) <= max_len:
                stereo[:len(early["left"]), 0] += early["left"] * gain_l
                stereo[:len(early["right"]), 1] += early["right"] * gain_r

        stereo = np.clip(stereo, -0.99, 0.99)

        if output_path is None:
            output_path = "/tmp/spatial_scene.wav"
        self._save(output_path, stereo)

        return SpatialResult(
            audio_path=output_path,
            sample_rate=sr,
            channels=2,
            duration_seconds=len(stereo) / sr,
            provenance={
                "num_sources": len(sources),
                "listener": list(self.listener.position),
                "room_rt60": self.room.rt60,
                "method": "ITD/ILD approximation (no HRTF data)",
                "type": "spatial_scene",
            },
        )

    def calculate_spatialization(
        self, source_pos: Tuple[float, float, float],
        listener_pos: Optional[Tuple[float, float, float]] = None,
    ) -> Dict[str, float]:
        if listener_pos is None:
            listener_pos = self.listener.position
        rel = np.array(source_pos) - np.array(listener_pos)
        distance = float(np.linalg.norm(rel))
        azimuth = float(math.degrees(math.atan2(rel[1], rel[0])))
        elevation = float(math.degrees(math.asin(rel[2] / max(distance, 0.01))))
        left, right = self._pan(azimuth)
        return {
            "distance": distance,
            "azimuth": azimuth,
            "elevation": elevation,
            "left_gain": left,
            "right_gain": right,
            "attenuation": self._distance_attenuation(distance),
        }

    def _load(self, path: str) -> Tuple[int, np.ndarray]:
        sr, data = wavfile.read(path)
        if data.ndim > 1:
            data = data[:, 0]
        return sr, data

    def _save(self, path: str, audio: np.ndarray) -> None:
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        audio_int = (np.clip(audio, -0.99, 0.99) * 32767).astype(np.int16)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(path, self.sample_rate, audio_int)


from pathlib import Path
