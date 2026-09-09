"""
Spatial Audio V3 - advanced spatial positioning.

Features:
- azimuth, elevation, distance
- ITD, ILD approximation
- occlusion, reflections
- room response
- stereo width
- source/listener movement
- HRTF abstraction (interpolation-ready, not claiming accuracy)
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
import math


@dataclass
class Source:
    azimuth: float
    elevation: float = 0.0
    distance: float = 3.0
    id: str = "source_0"


@dataclass
class Listener:
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    forward: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    up: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    head_radius: float = 0.085


@dataclass
class Room:
    dimensions: Tuple[float, float, float] = (10.0, 8.0, 3.0)
    wall_material: str = "concrete"
    absorption: float = 0.15
    rt60: float = 0.8


@dataclass
class SpatialEvent:
    source: Source
    listener: Listener
    room: Room
    movement_path: List[Tuple[float, float, float]] = field(default_factory=list)


class SpatialEngineV3:
    SPEED_OF_SOUND = 343.0
    HEAD_RADIUS = 0.085

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.listener = Listener()
        self.sources: List[Source] = []
        self.room = Room()

    def add_source(self, source: Source) -> None:
        self.sources.append(source)

    def set_listener(self, position: Tuple[float, float, float], forward: Tuple[float, float, float] = (1, 0, 0)) -> None:
        self.listener = Listener(position=position, forward=forward)

    def set_room(self, room: Room) -> None:
        self.room = room

    def compute_itd(self, azimuth: float) -> float:
        az_rad = math.radians(azimuth)
        return (self.HEAD_RADIUS * math.sin(az_rad)) / self.SPEED_OF_SOUND

    def compute_ild(self, azimuth: float, frequency_band: str = "mid") -> float:
        az_rad = math.radians(azimuth)
        freq_map = {"low": 500, "mid": 1500, "high": 4000}
        f = freq_map.get(frequency_band, 1500)
        head_shadow = 10 * math.log10(1 + (2 * math.pi * f * self.HEAD_RADIUS * (1 + math.cos(az_rad)) / (2 * self.SPEED_OF_SOUND)))
        return head_shadow

    def compute_distance_attenuation(self, distance: float) -> float:
        return 1.0 / max(distance, 0.1)

    def compute_occlusion(self, occlusion_factor: float, frequency: float = 1000) -> float:
        freq_factor = min(1.0, frequency / 4000.0)
        return 1.0 - (occlusion_factor * 0.7 * freq_factor)

    def spatialize_mono_source(
        self,
        audio: np.ndarray,
        source: Source,
        listener: Optional[Listener] = None,
        occlusion: float = 0.0,
        diffraction: float = 0.0,
    ) -> np.ndarray:
        lst = listener or self.listener
        az_rad = math.radians(source.azimuth)
        itd = self.compute_itd(source.azimuth)
        itd_samples = int(itd * self.sample_rate)
        ilow = self.compute_ild(source.azimuth, "low")
        imid = self.compute_ild(source.azimuth, "mid")
        ihigh = self.compute_ild(source.azimuth, "high")
        distance_attn = self.compute_distance_attenuation(source.distance)
        occ_gain = self.compute_occlusion(occlusion)
        left_gain = distance_attn * occ_gain * (1.0 - imid / 100.0 * 0.3)
        right_gain = distance_attn * occ_gain * (1.0 - imid / 100.0 * 0.3)
        if source.azimuth > 0:
            right_gain *= 10 ** (-imid / 20)
        else:
            left_gain *= 10 ** (-imid / 20)
        left = audio * left_gain
        right = audio * right_gain
        max_delay = min(abs(itd_samples), len(audio) - 1)
        if max_delay > 0:
            if itd_samples >= 0:
                left = np.pad(left, (0, max_delay))[:-max_delay] if len(left) > max_delay else left
                right = np.pad(right, (max_delay, 0))[max_delay:] if len(right) > max_delay else right
            else:
                left = np.pad(left, (max_delay, 0))[:-max_delay] if len(left) > max_delay else left
                right = np.pad(right, (0, max_delay))[max_delay:] if len(right) > max_delay else right
        return np.stack([left, right]).T.astype(np.float32)

    def apply_room_response(self, stereo_audio: np.ndarray) -> np.ndarray:
        rt60 = self.room.rt60
        if rt60 < 0.01:
            return stereo_audio
        decay = math.exp(-1.0 / (rt60 * self.sample_rate / 100))
        result = stereo_audio.copy()
        early_delay = int(0.01 * self.sample_rate)
        if early_delay < len(result):
            early = np.roll(stereo_audio, early_delay)
            result += early * 0.2 * self.room.absorption
        reverb_buf = stereo_audio.copy()
        for i in range(len(result)):
            if i < len(reverb_buf):
                reverb_buf[i] *= decay
                if abs(reverb_buf[i].mean()) > 0.0001:
                    result[i] += reverb_buf[i] * 0.3 * (1 - self.room.absorption)
        return np.clip(result, -0.99, 0.99)

    def apply_stereo_width(self, stereo_audio: np.ndarray, width: float = 1.0) -> np.ndarray:
        if width <= 0 or stereo_audio.shape[1] != 2:
            return stereo_audio
        mid = (stereo_audio[:, 0] + stereo_audio[:, 1]) * 0.5
        side = (stereo_audio[:, 0] - stereo_audio[:, 1]) * 0.5
        side *= width
        left = mid + side
        right = mid - side
        return np.clip(np.stack([left, right]).T, -0.99, 0.99)

    def process_source_movement(
        self,
        audio: np.ndarray,
        path: List[Tuple[float, float, float]],
        duration: float,
    ) -> np.ndarray:
        if not path or len(path) < 2:
            return self.spatialize_mono_source(audio, Source(0, 0, 3.0))
        n_segments = len(path) - 1
        seg_duration = duration / n_segments
        result = np.array([], dtype=np.float32)
        for i in range(n_segments):
            start_az = path[i][0]
            start_el = path[i][1]
            start_dist = path[i][2]
            end_az = path[i + 1][0]
            end_el = path[i + 1][1]
            end_dist = path[i + 1][2]
            seg_len = int(seg_duration * self.sample_rate)
            seg_audio = audio[min(i * seg_len, len(audio)):min((i + 1) * seg_len, len(audio))]
            if len(seg_audio) == 0:
                break
            for j in range(len(seg_audio)):
                ratio = j / max(1, len(seg_audio) - 1)
                az = start_az + (end_az - start_az) * ratio
                el = start_el + (end_el - start_el) * ratio
                dist = start_dist + (end_dist - start_dist) * ratio
                frame = seg_audio[j:j+1]
                if len(frame) > 0:
                    spatialized = self.spatialize_mono_source(frame, Source(az, el, dist))
                    if result.shape[0] == 0:
                        result = spatialized[0]
                    elif len(result) < len(spatialized):
                        result = np.pad(result, (0, 0, 0, len(spatialized) - len(result)))
            if len(seg_audio) == seg_len:
                spatialized_seg = self.spatialize_mono_source(seg_audio, Source(end_az, end_el, end_dist))
                if result.shape[0] == 0:
                    result = spatialized_seg.mean(axis=1)
                else:
                    pad_len = min(len(result), len(spatialized_seg))
                    result[:pad_len, 0] += spatialized_seg[:pad_len, 0] * 0.5
                    result[:pad_len, 1] += spatialized_seg[:pad_len, 1] * 0.5
        if result.ndim == 1 or len(result) == 0:
            return self.spatialize_mono_source(audio, Source(0, 0, 3.0))
        return np.clip(result, -0.99, 0.99)

    def process_multiple_sources(self, sources_audio: List[np.ndarray], sources: List[Source]) -> np.ndarray:
        if not sources_audio:
            return np.zeros((self.sample_rate, 2), dtype=np.float32)
        result = np.zeros((max(len(a) for a in sources_audio), 2), dtype=np.float32)
        for audio, src in zip(sources_audio, sources):
            spatialized = self.spatialize_mono_source(audio, src)
            min_len = min(len(result), len(spatialized))
            result[:min_len, 0] += spatialized[:min_len, 0]
            result[:min_len, 1] += spatialized[:min_len, 1]
        return np.clip(result, -0.99, 0.99)


class HRTFDatabase:
    """Abstraction for future HRTF integration.

    Currently uses approximated ITD/ILD.
    Does NOT claim actual HRTF accuracy.
    """

    def __init__(self):
        self._available = False
        self._hrtf_data: Dict[Tuple[int, int, int], Tuple[np.ndarray, np.ndarray]] = {}

    @property
    def available(self) -> bool:
        return self._available

    def load_hrtf(self, path: str) -> bool:
        try:
            data = np.load(path)
            self._available = True
            return True
        except Exception:
            self._available = False
            return False

    def interpolate(self, azimuth: float, elevation: float) -> Tuple[np.ndarray, np.ndarray]:
        if not self._available:
            left = np.array([1.0, 0.0, 0.0])
            right = np.array([1.0, 0.0, 0.0])
            return left, right
        return np.array([1.0]), np.array([1.0])
