"""
Audio Teleportation - transform any sound into a new acoustic world.

14 environments with procedural reverb/filtering:
bedroom, bathroom, studio, theater, tunnel, cave, street,
forest, underwater, warehouse, church, metal_room,
concrete_bunker, spaceship.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


class EnvironmentType(Enum):
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    STUDIO = "studio"
    THEATER = "theater"
    TUNNEL = "tunnel"
    CAVE = "cave"
    STREET = "street"
    FOREST = "forest"
    UNDERWATER = "underwater"
    WAREHOUSE = "warehouse"
    CHURCH = "church"
    METAL_ROOM = "metal_room"
    CONCRETE_BUNKER = "concrete_bunker"
    SPACESHIP = "spaceship"


@dataclass
class EnvironmentPreset:
    name: str
    room_size: float
    rt60: float
    absorption: float
    reflection_strength: float
    diffusion: float
    lowpass_cutoff: float
    highpass_cutoff: float
    distance_attenuation: float
    early_reflection_count: int
    late_reverb_gain: float
    water_reverb: float = 0.0
    air_absorption: float = 0.0
    echo_delay: Optional[float] = None
    echo_feedback: float = 0.0


ENVIRONMENT_PRESETS: Dict[str, EnvironmentPreset] = {
    "bedroom": EnvironmentPreset("bedroom", 0.3, 0.4, 0.75, 0.3, 0.5, 8000, 100, 0.8, 5, 0.4),
    "bathroom": EnvironmentPreset("bathroom", 0.25, 0.6, 0.9, 0.6, 0.3, 6000, 80, 0.9, 8, 0.5, echo_delay=0.02, echo_feedback=0.3),
    "studio": EnvironmentPreset("studio", 0.4, 0.25, 0.85, 0.15, 0.7, 12000, 50, 0.7, 4, 0.2),
    "theater": EnvironmentPreset("theater", 0.5, 0.8, 0.55, 0.4, 0.6, 10000, 80, 0.6, 10, 0.45),
    "tunnel": EnvironmentPreset("tunnel", 0.6, 1.2, 0.3, 0.5, 0.2, 4000, 100, 0.4, 12, 0.5, echo_delay=0.05, echo_feedback=0.5),
    "cave": EnvironmentPreset("cave", 0.7, 2.5, 0.2, 0.7, 0.4, 3000, 50, 0.3, 15, 0.6, echo_delay=0.08, echo_feedback=0.4),
    "street": EnvironmentPreset("street", 0.5, 0.3, 0.6, 0.2, 0.4, 7000, 100, 0.5, 3, 0.25),
    "forest": EnvironmentPreset("forest", 0.8, 0.5, 0.65, 0.25, 0.8, 6000, 100, 0.6, 6, 0.35, air_absorption=0.02),
    "underwater": EnvironmentPreset("underwater", 0.9, 0.9, 0.95, 0.3, 0.3, 2000, 200, 0.2, 8, 0.4, water_reverb=0.8),
    "warehouse": EnvironmentPreset("warehouse", 0.8, 1.5, 0.35, 0.5, 0.5, 5000, 80, 0.4, 10, 0.55, echo_delay=0.06, echo_feedback=0.45),
    "church": EnvironmentPreset("church", 1.0, 3.5, 0.2, 0.8, 0.6, 4000, 60, 0.3, 20, 0.65, echo_delay=0.12, echo_feedback=0.6),
    "metal_room": EnvironmentPreset("metal_room", 0.4, 0.9, 0.9, 0.7, 0.2, 8000, 100, 0.7, 8, 0.5, echo_delay=0.03, echo_feedback=0.4),
    "concrete_bunker": EnvironmentPreset("concrete_bunker", 0.6, 1.8, 0.15, 0.6, 0.3, 3500, 80, 0.3, 12, 0.6, echo_delay=0.07, echo_feedback=0.5),
    "spaceship": EnvironmentPreset("spaceship", 0.5, 0.4, 0.7, 0.4, 0.5, 9000, 100, 0.8, 6, 0.35, air_absorption=0.05),
}


class AudioTeleporter:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.presets = ENVIRONMENT_PRESETS

    def teleport(
        self,
        audio: np.ndarray,
        environment: str,
        distance: float = 3.0,
        custom_preset: Optional[EnvironmentPreset] = None,
    ) -> np.ndarray:
        preset = custom_preset or self.presets.get(environment, self.presets["studio"])
        result = audio.copy()
        result = self._apply_distance_attenuation(result, distance, preset)
        if preset.water_reverb > 0:
            result = self._apply_water_reverb(result, preset)
        if preset.air_absorption > 0:
            result = self._apply_air_absorption(result, distance, preset)
        result = self._apply_echos(result, preset)
        result = self._apply_reverb(result, preset)
        result = self._apply_filters(result, preset)
        result = self._apply_diffusion(result, preset)
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def _apply_distance_attenuation(self, audio: np.ndarray, distance: float, preset: EnvironmentPreset) -> np.ndarray:
        attenuation = preset.distance_attenuation * (1.0 / max(1.0, np.sqrt(distance)))
        return audio * attenuation

    def _apply_water_reverb(self, audio: np.ndarray, preset: EnvironmentPreset) -> np.ndarray:
        binaural = np.stack([audio, audio])
        for ch in range(2):
            delay_samples = int(0.01 * self.sample_rate)
            echo_count = 5
            for i in range(echo_count):
                delayed = np.zeros_like(audio)
                actual_delay = delay_samples * (i + 1)
                if actual_delay < len(delayed):
                    delayed[actual_delay:] = audio[:-actual_delay]
                    binaural[ch] += delayed * preset.water_reverb * (0.5 ** (i + 1))
        return binaural.mean(axis=0)

    def _apply_air_absorption(self, audio: np.ndarray, distance: float, preset: EnvironmentPreset) -> np.ndarray:
        abs_factor = np.exp(-preset.air_absorption * distance)
        return audio * abs_factor

    def _apply_echos(self, audio: np.ndarray, preset: EnvironmentPreset) -> np.ndarray:
        if preset.echo_delay is None:
            return audio
        delay_samples = int(preset.echo_delay * self.sample_rate)
        if delay_samples <= 0 or delay_samples >= len(audio):
            return audio
        result = audio.copy()
        echo = audio.copy()
        for _ in range(3):
            shifted = np.zeros_like(audio)
            shifted[delay_samples:] = echo[:-delay_samples]
            result += shifted * preset.echo_feedback
            echo = shifted * preset.echo_feedback
            if np.max(np.abs(echo)) < 1e-6:
                break
        return result

    def _apply_reverb(self, audio: np.ndarray, preset: EnvironmentPreset) -> np.ndarray:
        n_taps = preset.early_reflection_count
        late_gain = preset.late_reverb_gain
        rt60 = preset.rt60
        result = audio.copy()
        rng = np.random.RandomState(42)
        tap_positions = rng.uniform(0.001, 0.05, n_taps)
        for pos in tap_positions:
            delay = int(pos * self.sample_rate)
            if delay < len(result):
                early_refl = np.zeros_like(audio)
                early_refl[delay:] = audio[:-delay] * preset.reflection_strength * 0.3
                result += early_refl
        decay_rate = np.exp(-1.0 / (rt60 * self.sample_rate / 10))
        reverb_buffer = audio.copy()
        for i in range(len(result)):
            if i < len(reverb_buffer):
                reverb_buffer[i] *= decay_rate
                if reverb_buffer[i] > 0.0001:
                    result[i] += reverb_buffer[i] * late_gain
        return result

    def _apply_filters(self, audio: np.ndarray, preset: EnvironmentPreset) -> np.ndarray:
        from scipy import signal as scipy_signal
        nyq = self.sample_rate / 2
        if preset.lowpass_cutoff < nyq:
            b, a = scipy_signal.butter(4, preset.lowpass_cutoff / nyq, btype='low')
            audio = scipy_signal.filtfilt(b, a, audio)
        if preset.highpass_cutoff > 0 and preset.highpass_cutoff < nyq:
            b, a = scipy_signal.butter(4, preset.highpass_cutoff / nyq, btype='high')
            audio = scipy_signal.filtfilt(b, a, audio)
        return audio

    def _apply_diffusion(self, audio: np.ndarray, preset: EnvironmentPreset) -> np.ndarray:
        if preset.diffusion < 0.01:
            return audio
        n = len(audio)
        result = audio.copy()
        delays = [int(0.005 * self.sample_rate), int(0.007 * self.sample_rate), int(0.009 * self.sample_rate)]
        gains = [preset.diffusion * 0.25, preset.diffusion * 0.2, preset.diffusion * 0.3]
        for d, g in zip(delays, gains):
            if d < n:
                diffused = np.zeros_like(audio)
                diffused[d:] = audio[:-d] * g
                result = np.convolve(result, diffused[:min(n, len(diffused))], mode='same')
                result = np.clip(result, -0.99, 0.99)
        return result

    def get_environment_names(self) -> List[str]:
        return list(self.presets.keys())

    def get_preset(self, environment: str) -> Optional[EnvironmentPreset]:
        return self.presets.get(environment)

    def teleport_stereo(self, audio: np.ndarray, environment: str, distance: float = 3.0) -> np.ndarray:
        if audio.ndim == 1:
            result = self.teleport(audio, environment, distance)
            return np.stack([result, result]).T
        elif audio.ndim == 2:
            left = self.teleport(audio[:, 0], environment, distance)
            right = self.teleport(audio[:, 1], environment, distance)
            return np.stack([left, right]).T
        return audio
