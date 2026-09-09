"""
MAKE Material Sound Lab.

Extended acoustic material profiles with physics parameters.
Allows users to create fictional materials and derive consistent acoustic signatures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json
from pathlib import Path


@dataclass
class MaterialProfile:
    name: str
    density: float = 1.0
    hardness: float = 0.5
    resonance: float = 0.5
    damping: float = 0.5
    brightness: float = 0.5
    transient_sharpness: float = 0.5
    sustain: float = 0.5
    roughness: float = 0.5
    spectral_distribution: float = 0.5
    reflection: float = 0.5
    absorption: float = 0.5
    color: str = "#808080"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    _hash: str = field(default="", init=False)

    def __post_init__(self):
        self._hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = {
            "name": self.name,
            "density": self.density,
            "hardness": self.hardness,
            "resonance": self.resonance,
            "damping": self.damping,
            "brightness": self.brightness,
            "transient_sharpness": self.transient_sharpness,
            "sustain": self.sustain,
            "roughness": self.roughness,
            "spectral_distribution": self.spectral_distribution,
            "reflection": self.reflection,
            "absorption": self.absorption,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    @property
    def hash(self) -> str:
        return self._hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "density": self.density,
            "hardness": self.hardness,
            "resonance": self.resonance,
            "damping": self.damping,
            "brightness": self.brightness,
            "transient_sharpness": self.transient_sharpness,
            "sustain": self.sustain,
            "roughness": self.roughness,
            "spectral_distribution": self.spectral_distribution,
            "reflection": self.reflection,
            "absorption": self.absorption,
            "color": self.color,
            "description": self.description,
            "tags": list(self.tags),
            "hash": self._hash,
        }

    def to_acoustic_params(self) -> Dict[str, float]:
        return {
            "density": self.density,
            "hardness": self.hardness,
            "resonance": self.resonance,
            "damping": self.damping,
            "brightness": self.brightness,
            "transient_sharpness": self.transient_sharpness,
            "sustain": self.sustain,
            "roughness": self.roughness,
            "spectral_distribution": self.spectral_distribution,
            "reflection": self.reflection,
            "absorption": self.absorption,
        }


class MaterialSoundLab:
    PRESETS: Dict[str, MaterialProfile] = {}

    def __init__(self):
        self._profiles: Dict[str, MaterialProfile] = {}
        self._init_presets()

    def _init_presets(self):
        presets = {
            "wood": MaterialProfile(
                name="wood", density=0.7, hardness=0.4, resonance=0.6,
                damping=0.7, brightness=0.5, transient_sharpness=0.4,
                sustain=0.6, roughness=0.3, spectral_distribution=0.4,
                reflection=0.3, absorption=0.6, color="#8B4513",
                description="Hardwood like oak or maple", tags=["solid", "organic"],
            ),
            "metal": MaterialProfile(
                name="metal", density=7.8, hardness=0.9, resonance=0.9,
                damping=0.1, brightness=0.9, transient_sharpness=0.9,
                sustain=0.8, roughness=0.4, spectral_distribution=0.9,
                reflection=0.9, absorption=0.1, color="#C0C0C0",
                description="Steel or aluminum", tags=["hard", "reflective"],
            ),
            "glass": MaterialProfile(
                name="glass", density=2.5, hardness=0.8, resonance=0.8,
                damping=0.3, brightness=0.9, transient_sharpness=0.8,
                sustain=0.5, roughness=0.2, spectral_distribution=0.8,
                reflection=0.8, absorption=0.3, color="#87CEEB",
                description="Window glass or crystal", tags=["brittle", "transparent"],
            ),
            "ceramic": MaterialProfile(
                name="ceramic", density=2.4, hardness=0.85, resonance=0.7,
                damping=0.4, brightness=0.8, transient_sharpness=0.8,
                sustain=0.4, roughness=0.3, spectral_distribution=0.7,
                reflection=0.7, absorption=0.4, color="#F5F5DC",
                description="Pottery or porcelain", tags=["brittle", "hard"],
            ),
            "concrete": MaterialProfile(
                name="concrete", density=2.4, hardness=0.9, resonance=0.2,
                damping=0.8, brightness=0.2, transient_sharpness=0.2,
                sustain=0.1, roughness=0.6, spectral_distribution=0.2,
                reflection=0.2, absorption=0.8, color="#808080",
                description="Building concrete", tags=["dense", "dull"],
            ),
            "fabric": MaterialProfile(
                name="fabric", density=0.3, hardness=0.1, resonance=0.1,
                damping=0.9, brightness=0.3, transient_sharpness=0.1,
                sustain=0.2, roughness=0.5, spectral_distribution=0.3,
                reflection=0.1, absorption=0.9, color="#4B0082",
                description="Cotton or wool fabric", tags=["soft", "absorptive"],
            ),
            "leather": MaterialProfile(
                name="leather", density=0.9, hardness=0.3, resonance=0.3,
                damping=0.7, brightness=0.4, transient_sharpness=0.3,
                sustain=0.3, roughness=0.6, spectral_distribution=0.4,
                reflection=0.2, absorption=0.7, color="#8B4513",
                description="Leather hide", tags=["flexible", "organic"],
            ),
            "plastic": MaterialProfile(
                name="plastic", density=0.9, hardness=0.5, resonance=0.4,
                damping=0.6, brightness=0.6, transient_sharpness=0.5,
                sustain=0.3, roughness=0.3, spectral_distribution=0.5,
                reflection=0.3, absorption=0.6, color="#00FF00",
                description="ABS or polyethylene", tags=["synthetic", "light"],
            ),
            "rubber": MaterialProfile(
                name="rubber", density=1.1, hardness=0.4, resonance=0.2,
                damping=0.8, brightness=0.3, transient_sharpness=0.2,
                sustain=0.1, roughness=0.7, spectral_distribution=0.3,
                reflection=0.1, absorption=0.8, color="#000000",
                description="Natural or synthetic rubber", tags=["elastic", "damping"],
            ),
            "paper": MaterialProfile(
                name="paper", density=0.8, hardness=0.2, resonance=0.1,
                damping=0.8, brightness=0.4, transient_sharpness=0.3,
                sustain=0.1, roughness=0.4, spectral_distribution=0.3,
                reflection=0.2, absorption=0.7, color="#FFFFFF",
                description="Paper or cardboard", tags=["thin", "brittle"],
            ),
            "water": MaterialProfile(
                name="water", density=1.0, hardness=0.0, resonance=0.6,
                damping=0.2, brightness=0.7, transient_sharpness=0.6,
                sustain=0.5, roughness=0.3, spectral_distribution=0.8,
                reflection=0.0, absorption=0.2, color="#4169E1",
                description="Liquid water", tags=["liquid", "fluid"],
            ),
            "stone": MaterialProfile(
                name="stone", density=2.7, hardness=0.9, resonance=0.3,
                damping=0.7, brightness=0.3, transient_sharpness=0.4,
                sustain=0.3, roughness=0.5, spectral_distribution=0.3,
                reflection=0.4, absorption=0.6, color="#696969",
                description="Granite or marble", tags=["dense", "hard"],
            ),
            "sand": MaterialProfile(
                name="sand", density=1.6, hardness=0.3, resonance=0.1,
                damping=0.9, brightness=0.2, transient_sharpness=0.1,
                sustain=0.1, roughness=0.9, spectral_distribution=0.2,
                reflection=0.1, absorption=0.9, color="#F4A460",
                description="Fine sand", tags=["granular", "damping"],
            ),
            "snow": MaterialProfile(
                name="snow", density=0.3, hardness=0.1, resonance=0.1,
                damping=0.9, brightness=0.8, transient_sharpness=0.1,
                sustain=0.1, roughness=0.7, spectral_distribution=0.6,
                reflection=0.8, absorption=0.9, color="#FFFFFF",
                description="Fresh snow", tags=["soft", "cold"],
            ),
            "ice": MaterialProfile(
                name="ice", density=0.9, hardness=0.7, resonance=0.8,
                damping=0.2, brightness=0.8, transient_sharpness=0.7,
                sustain=0.6, roughness=0.2, spectral_distribution=0.8,
                reflection=0.8, absorption=0.2, color="#B0E0E6",
                description="Frozen water", tags=["slippery", "hard"],
            ),
        }
        self._profiles = dict(presets)
        MaterialSoundLab.PRESETS = dict(presets)

    def get(self, name: str) -> Optional[MaterialProfile]:
        return self._profiles.get(name.lower())

    def create(self, name: str, **params: float) -> MaterialProfile:
        profile = MaterialProfile(name=name, **params)
        self._profiles[name.lower()] = profile
        return profile

    def create_fictional(self, name: str, inspiration: str, modifications: Dict[str, float]) -> MaterialProfile:
        base = self._profiles.get(inspiration.lower())
        if base is None:
            base = MaterialProfile(name=inspiration, description=f"Based on {inspiration}")
        base_dict = base.to_dict()
        for key, val in modifications.items():
            if key in base_dict and isinstance(base_dict[key], (int, float)):
                base_dict[key] = val
        base_dict["name"] = name
        base_dict["description"] = f"Fictional material '{name}' based on '{inspiration}'"
        return MaterialProfile(**{k: v for k, v in base_dict.items() if k in MaterialProfile.__dataclass_fields__})

    def list_materials(self) -> List[str]:
        return list(self._profiles.keys())

    def interaction_sound(
        self, material_a: str, material_b: str, impact_force: float = 1.0,
        velocity: float = 1.0, mass: float = 1.0,
    ) -> Dict[str, Any]:
        ma = self._profiles.get(material_a.lower())
        mb = self._profiles.get(material_b.lower())
        if ma is None or mb is None:
            return {}
        combined_hardness = (ma.hardness + mb.hardness) / 2.0
        combined_density = (ma.density + mb.density) / 2.0
        combined_resonance = max(ma.resonance, mb.resonance)
        combined_damping = (ma.damping + mb.damping) / 2.0
        sharpness = combined_hardness * impact_force * velocity
        brightness = (ma.brightness + mb.brightness) / 2.0
        return {
            "material_a": material_a,
            "material_b": material_b,
            "combined_hardness": combined_hardness,
            "combined_density": combined_density,
            "combined_resonance": combined_resonance,
            "combined_damping": combined_damping,
            "sharpness": sharpness,
            "brightness": brightness,
            "mass_effect": min(1.0, mass / 10.0),
            "impact_force": impact_force,
            "velocity": velocity,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {name: p.to_dict() for name, p in self._profiles.items()}

    def save(self, path: str) -> None:
        data = {
            "version": "1.0",
            "materials": self.to_dict(),
            "count": len(self._profiles),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "MaterialSoundLab":
        instance = cls()
        if Path(path).exists():
            with open(path, "r") as f:
                data = json.load(f)
            for name, pdata in data.get("materials", {}).items():
                known = {k: v for k, v in pdata.items() if k in MaterialProfile.__dataclass_fields__}
                profile = MaterialProfile(**known)
                instance._profiles[name.lower()] = profile
        return instance
