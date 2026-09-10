"""
Material Sound Lab V2 - expanded material physics profiles.

18 materials: wood, metal, glass, plastic, stone, concrete,
ceramic, rubber, fabric, water, ice, paper, leather, sand,
dirt, foliage, snow, mud.

Actions: impact, scrape, drag, drop, collision, break,
bend, stretch, roll, slide.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
import math


@dataclass
class MaterialProfile:
    name: str
    density: float
    stiffness: float
    damping: float
    roughness: float
    resonance_freq: float
    modal_freqs: List[float]
    attenuation: float
    absorption: float = 0.15
    color: str = "#FFFFFF"


@dataclass
class MaterialActionParams:
    force: float
    speed: float
    contact_size: str
    surface_area: str


MATERIAL_PROFILES: Dict[str, MaterialProfile] = {
    "wood": MaterialProfile("wood", 600, 12e9, 0.05, 0.3, 450, [120, 250, 400, 550], 0.4, 0.15, "#8B4513"),
    "metal": MaterialProfile("metal", 7800, 200e9, 0.01, 0.1, 1200, [220, 440, 660, 880], 0.1, 0.05, "#C0C0C0"),
    "glass": MaterialProfile("glass", 2500, 70e9, 0.02, 0.15, 1500, [523, 660, 784, 1047], 0.05, 0.1, "#87CEEB"),
    "plastic": MaterialProfile("plastic", 1200, 3e9, 0.08, 0.4, 300, [220, 440, 660, 880], 0.6, 0.25, "#00FF00"),
    "stone": MaterialProfile("stone", 2700, 50e9, 0.03, 0.5, 800, [110, 220, 330, 440], 0.3, 0.1, "#808080"),
    "concrete": MaterialProfile("concrete", 2400, 30e9, 0.06, 0.6, 600, [100, 200, 300, 400], 0.4, 0.15, "#A9A9A9"),
    "ceramic": MaterialProfile("ceramic", 2100, 300e9, 0.04, 0.35, 1100, [440, 660, 880, 1100], 0.2, 0.1, "#E0E0E0"),
    "rubber": MaterialProfile("rubber", 1100, 0.01e9, 0.25, 0.8, 50, [80, 160, 240, 320], 0.8, 0.5, "#FF0000"),
    "fabric": MaterialProfile("fabric", 150, 0.5e9, 0.3, 0.7, 300, [200, 400, 600, 800], 0.9, 0.45, "#4B0082"),
    "water": MaterialProfile("water", 1000, 2e9, 0.001, 0.0, 100, [60, 120, 180, 240], 0.2, 0.3, "#0000FF"),
    "ice": MaterialProfile("ice", 920, 10e9, 0.015, 0.2, 800, [440, 660, 880, 1100], 0.15, 0.15, "#E0FFFF"),
    "paper": MaterialProfile("paper", 800, 0.4e9, 0.12, 0.9, 200, [440, 880, 1320], 0.7, 0.35, "#FFFFE0"),
    "leather": MaterialProfile("leather", 900, 0.2e9, 0.15, 0.65, 250, [200, 400, 600, 800], 0.75, 0.2, "#8B0000"),
    "sand": MaterialProfile("sand", 1600, 0.1e9, 0.5, 1.0, 100, [50, 100, 150, 200], 0.95, 0.6, "#F4A460"),
    "dirt": MaterialProfile("dirt", 1400, 0.05e9, 0.6, 0.8, 80, [40, 80, 120, 160], 0.9, 0.55, "#8B4513"),
    "foliage": MaterialProfile("foliage", 400, 0.01e9, 0.4, 0.9, 200, [300, 600, 900, 1200], 0.85, 0.65, "#228B22"),
    "snow": MaterialProfile("snow", 100, 0.01e9, 0.8, 0.9, 50, [80, 160, 240, 320], 0.95, 0.8, "#FFFFFF"),
    "mud": MaterialProfile("mud", 1800, 0.02e9, 0.7, 0.85, 60, [60, 120, 180, 240], 0.9, 0.75, "#5C4033"),
}


class MaterialSoundEngine:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.materials = MATERIAL_PROFILES

    def generate_impact(
        self, material: str, force: float = 1.0, speed: float = 1.0,
        contact_size: str = "medium",
    ) -> np.ndarray:
        profile = self.materials.get(material, self.materials["wood"])
        duration = 0.3
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        f0 = profile.resonance_freq
        amp = force * 0.3 * (1.0 - profile.damping)
        decay = np.exp(-t * profile.attenuation * 20 * speed)
        audio = amp * np.sin(2 * math.pi * f0 * t + 0.3 * np.sin(2 * math.pi * f0 * t)) * decay
        for mf in profile.modal_freqs:
            audio += amp * 0.3 * np.sin(2 * math.pi * mf * t) * decay * 0.5
        noise = np.random.RandomState(42).normal(0, amp * 0.2, n)
        noise *= np.exp(-t * profile.attenuation * 30)
        audio += noise
        contact_mult = {"small": 0.7, "medium": 1.0, "large": 1.3}[contact_size]
        return np.clip(audio * contact_mult, -0.99, 0.99).astype(np.float32)

    def generate_scrape(
        self, material: str, speed: float = 1.0, force: float = 1.0,
    ) -> np.ndarray:
        profile = self.materials.get(material, self.materials["wood"])
        duration = 1.0
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        roughness_noise = np.random.RandomState(42).normal(0, 1, n)
        b, a = self._butter_bandpass(
            profile.modal_freqs[1] * 0.5, profile.modal_freqs[1] * 2,
            self.sample_rate, 4
        )
        if len(b) > 0:
            try:
                from scipy import signal as scipy_signal
                roughness_noise = scipy_signal.filtfilt(b, a, roughness_noise)
            except Exception:
                roughness_noise = np.zeros_like(roughness_noise)
        envelope = np.exp(-t * 5 * (1 - profile.roughness))
        audio = force * 0.2 * roughness_noise * envelope * (1 + profile.roughness * speed)
        mod_t = t * profile.resonance_freq
        carrier = 0.1 * np.sin(2 * math.pi * profile.resonance_freq * t) * (1 - profile.damping)
        audio += carrier * np.sin(2 * math.pi * mod_t * 0.5)
        return np.clip(audio, -0.99, 0.99).astype(np.float32)

    def _butter_bandpass(self, lowcut, highcut, fs, order):
        nyq = fs / 2
        low = lowcut / nyq
        high = highcut / nyq
        if low >= 1 or high >= 1 or low >= high:
            return np.array([1.0]), np.array([1.0])
        from scipy import signal as scipy_signal
        b, a = scipy_signal.butter(order, [low, high], btype='band')
        return b, a

    def generate_drop(
        self, material: str, height: float = 1.0,
    ) -> np.ndarray:
        impact = self.generate_impact(material, force=height * 0.5)
        bounce_count = max(1, int(material_profiles_bounces(material)))
        result = impact.copy()
        for i in range(bounce_count):
            delay = int(0.05 * self.sample_rate * (i + 1))
            bounce = impact * (0.5 ** (i + 1))
            if delay + len(bounce) <= len(result):
                result[delay:delay + len(bounce)] += bounce
            else:
                total_len = delay + len(bounce)
                if total_len > len(result):
                    result = np.pad(result, (0, total_len - len(result)))
                result[delay:delay + len(bounce)] += bounce[:len(result) - delay] 
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def generate_collision(
        self, material_a: str, material_b: str,
    ) -> np.ndarray:
        a_impact = self.generate_impact(material_a, force=0.7)
        b_impact = self.generate_impact(material_b, force=0.7)
        min_len = min(len(a_impact), len(b_impact))
        return np.clip(a_impact[:min_len] + b_impact[:min_len], -0.99, 0.99).astype(np.float32)

    def generate_drag(
        self, material: str, distance: float = 1.0,
    ) -> np.ndarray:
        profile = self.materials.get(material, self.materials["wood"])
        duration = 1.5
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        friction_noise = np.random.RandomState(42).normal(0, 0.1, n)
        b, a = self._butter_bandpass(100, profile.resonance_freq, self.sample_rate, 4)
        try:
            from scipy import signal as scipy_signal
            friction_noise = scipy_signal.filtfilt(b, a, friction_noise)
        except Exception:
            friction_noise = np.zeros_like(friction_noise)
        envelope = 1 - np.exp(-t * 3)
        audio = friction_noise * envelope * distance * (1 - profile.damping)
        return np.clip(audio, -0.99, 0.99).astype(np.float32)

    def generate_roll(
        self, material: str, speed: float = 1.0,
    ) -> np.ndarray:
        profile = self.materials.get(material, self.materials["wood"])
        duration = 1.0
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        rumble = np.random.RandomState(42).normal(0, 0.15, n)
        b, a = self._butter_bandpass(50, 500, self.sample_rate, 4)
        try:
            from scipy import signal as scipy_signal
            rumble = scipy_signal.filtfilt(b, a, rumble)
        except Exception:
            if len(b) > 0:
                rumble = np.convolve(rumble, np.ones(5)/5, mode='same')
        mod = 1 + 0.2 * np.sin(2 * math.pi * 40 * t)
        audio = rumble * mod * speed * (1 - profile.damping)
        return np.clip(audio, -0.99, 0.99).astype(np.float32)

    def generate_break(
        self, material: str, force: float = 1.0,
    ) -> np.ndarray:
        profile = self.materials.get(material, self.materials["wood"])
        duration = 0.5
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        crack_time = 0.02 + np.random.RandomState(42).uniform(0, 0.01)
        crack_sample = int(crack_time * self.sample_rate)
        pre = np.random.RandomState(42).normal(0, 0.05 * force, crack_sample)
        post = np.random.RandomState(99).normal(0, 0.4 * force, n - crack_sample)
        decay = np.exp(-t[crack_sample:] * profile.attenuation * 50)
        post *= decay
        audio = np.concatenate([pre, post])
        for mf in profile.modal_freqs[:2]:
            ring = 0.1 * np.sin(2 * math.pi * mf * t[crack_sample:]) * np.exp(-t[crack_sample:] * 30)
            audio[crack_sample:] += ring * 0.3
        return np.clip(audio, -0.99, 0.99).astype(np.float32)

    def generate_all_actions(
        self, material: str, params: Optional[MaterialActionParams] = None,
    ) -> Dict[str, np.ndarray]:
        params = params or MaterialActionParams(force=0.7, speed=1.0, contact_size="medium", surface_area="medium")
        return {
            "impact": self.generate_impact(material, params.force, params.speed, params.contact_size),
            "scrape": self.generate_scrape(material, params.speed, params.force),
            "drop": self.generate_drop(material, params.force),
            "collision": self.generate_collision(material, material),
            "drag": self.generate_drag(material, 1.0),
            "roll": self.generate_roll(material, params.speed),
            "break": self.generate_break(material, params.force),
            "bend": self.generate_impact(material, params.force * 0.5),
            "stretch": self.generate_drag(material, params.force * 0.3),
            "slide": self.generate_scrape(material, params.speed, params.force),
        }


def material_profiles_bounces(material: str) -> int:
    bounces_map = {
        "rubber": 1, "fabric": 1, "snow": 1, "mud": 1, "sand": 1,
        "water": 0, "glass": 4, "metal": 4, "ceramic": 3,
        "wood": 2, "stone": 3, "concrete": 2,
    }
    return bounces_map.get(material, 2)
