"""
World Sound Intelligence - complete acoustic environment model.

Represents rooms with dimensions, materials, objects, surfaces,
doors, windows, walls, ceiling, floor.

Reasons about how sound changes based on environment.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import math


@dataclass
class Surface:
    name: str
    material: str
    area: float
    absorption: float
    reflection: float


@dataclass
class Door:
    position: Tuple[float, float, float]
    width: float
    height: float
    open: bool = True
    material: str = "wood"


@dataclass
class Window:
    position: Tuple[float, float, float]
    width: float
    height: float
    transparent: bool = True
    material: str = "glass"


@dataclass
class RoomObject:
    name: str
    position: Tuple[float, float, float]
    material: str
    size: float


@dataclass
class AcousticProperties:
    rt60_125: float
    rt60_250: float
    rt60_500: float
    rt60_1000: float
    rt60_2000: float
    rt60_4000: float
    reverb_time: float
    clarity: float
    definition: float
    center_time: float


@dataclass
class WorldSoundModel:
    name: str
    dimensions: Tuple[float, float, float]
    surfaces: List[Surface] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    objects: List[RoomObject] = field(default_factory=list)
    floor_material: str = "wood"
    wall_material: str = "concrete"
    ceiling_material: str = "drywall"
    acoustic_props: Optional[AcousticProperties] = None


MATERIAL_ABSORPTION: Dict[str, float] = {
    "wood": 0.15, "metal": 0.05, "glass": 0.10, "plastic": 0.25,
    "stone": 0.10, "concrete": 0.15, "ceramic": 0.10, "rubber": 0.50,
    "fabric": 0.45, "water": 0.30, "ice": 0.15, "paper": 0.35,
    "leather": 0.20, "sand": 0.60, "dirt": 0.55, "foliage": 0.65,
    "snow": 0.80, "mud": 0.75, "drywall": 0.25, "carpet": 0.40,
}


class WorldSoundIntelligence:
    def __init__(self):
        self.rooms: Dict[str, WorldSoundModel] = {}
        self._create_default_rooms()

    def _create_default_rooms(self) -> None:
        bedroom = WorldSoundModel(
            name="bedroom",
            dimensions=(4.0, 3.0, 2.5),
            floor_material="carpet",
            wall_material="drywall",
            ceiling_material="drywall",
        )
        bedroom.acoustic_props = WorldSoundIntelligence._compute_acoustic_properties(bedroom)
        bedroom.surfaces = [
            Surface("north_wall", "drywall", 12.0, 0.25, 0.75),
            Surface("south_wall", "drywall", 12.0, 0.25, 0.75),
            Surface("west_wall", "drywall", 7.5, 0.25, 0.75),
            Surface("east_wall", "drywall", 7.5, 0.25, 0.75),
            Surface("floor", "carpet", 12.0, 0.4, 0.6),
            Surface("ceiling", "drywall", 12.0, 0.25, 0.75),
        ]
        self.rooms["bedroom"] = bedroom

        bathroom = WorldSoundModel(
            name="bathroom",
            dimensions=(2.5, 2.0, 2.5),
            floor_material="ceramic",
            wall_material="ceramic",
            ceiling_material="drywall",
        )
        bathroom.acoustic_props = WorldSoundIntelligence._compute_acoustic_properties(bathroom)
        bathroom.surfaces = [
            Surface("north_wall", "ceramic", 6.25, 0.1, 0.9),
            Surface("south_wall", "ceramic", 6.25, 0.1, 0.9),
            Surface("west_wall", "ceramic", 5.0, 0.1, 0.9),
            Surface("east_wall", "ceramic", 5.0, 0.1, 0.9),
            Surface("floor", "ceramic", 5.0, 0.1, 0.9),
            Surface("ceiling", "drywall", 5.0, 0.25, 0.75),
        ]
        self.rooms["bathroom"] = bathroom

        cave = WorldSoundModel(
            name="cave",
            dimensions=(30.0, 30.0, 20.0),
            floor_material="stone",
            wall_material="stone",
            ceiling_material="stone",
        )
        cave.acoustic_props = WorldSoundIntelligence._compute_acoustic_properties(cave)
        cave.surfaces = [
            Surface("floor", "stone", 30.0, 0.15, 0.85),
            Surface("wall_north", "stone", 600.0, 0.15, 0.85),
            Surface("wall_south", "stone", 600.0, 0.15, 0.85),
            Surface("ceiling", "stone", 900.0, 0.15, 0.85),
        ]
        self.rooms["cave"] = cave

        studio = WorldSoundModel(
            name="studio",
            dimensions=(5.0, 4.0, 3.0),
            floor_material="carpet",
            wall_material="drywall",
            ceiling_material="drywall",
        )
        studio.acoustic_props = WorldSoundIntelligence._compute_acoustic_properties(studio)
        studio.surfaces = [
            Surface("walls_and_floor", "acoustic_panel", 38.0, 0.6, 0.4),
        ]
        self.rooms["studio"] = studio

    def create_room(
        self, name: str, dimensions: Tuple[float, float, float],
        floor_material: str, wall_material: str, ceiling_material: str,
        objects: Optional[List[RoomObject]] = None,
        doors: Optional[List[Door]] = None,
        windows: Optional[List[Window]] = None,
    ) -> WorldSoundModel:
        room = WorldSoundModel(
            name=name,
            dimensions=dimensions,
            floor_material=floor_material,
            wall_material=wall_material,
            ceiling_material=ceiling_material,
        )
        lx, ly, lz = dimensions
        room.surfaces = [
            Surface("floor", floor_material, lx * ly, MATERIAL_ABSORPTION.get(floor_material, 0.15), 1.0),
            Surface("ceiling", ceiling_material, lx * ly, MATERIAL_ABSORPTION.get(ceiling_material, 0.15), 1.0),
            Surface("wall_1", wall_material, lx * lz, MATERIAL_ABSORPTION.get(wall_material, 0.15), 1.0),
            Surface("wall_2", wall_material, lx * lz, MATERIAL_ABSORPTION.get(wall_material, 0.15), 1.0),
            Surface("wall_3", wall_material, ly * lz, MATERIAL_ABSORPTION.get(wall_material, 0.15), 1.0),
            Surface("wall_4", wall_material, ly * lz, MATERIAL_ABSORPTION.get(wall_material, 0.15), 1.0),
        ]
        room.objects = objects or []
        room.doors = doors or []
        room.windows = windows or []
        room.acoustic_props = WorldSoundIntelligence._compute_acoustic_properties(room)
        self.rooms[name] = room
        return room

    @staticmethod
    def _compute_acoustic_properties(room: WorldSoundModel) -> AcousticProperties:
        total_area = sum(s.area for s in room.surfaces)
        avg_absorption = sum(s.area * s.absorption for s in room.surfaces) / max(total_area, 0.001)
        volume = room.dimensions[0] * room.dimensions[1] * room.dimensions[2]
        rt60 = (0.16 * volume) / max(0.001, total_area * avg_absorption) if total_area > 0 else 0.5
        rt60 = min(rt60, 5.0)
        clarity = 1.0 - min(rt60 * 0.2, 0.8)
        definition = 1.0 - min(rt60 * 0.15, 0.7)
        return AcousticProperties(
            rt60_125=rt60, rt60_250=rt60 * 0.95, rt60_500=rt60 * 0.9,
            rt60_1000=rt60 * 0.85, rt60_2000=rt60 * 0.8, rt60_4000=rt60 * 0.75,
            reverb_time=rt60, clarity=clarity, definition=definition,
            center_time=rt60 * 0.3,
        )

    def get_room(self, name: str) -> Optional[WorldSoundModel]:
        return self.rooms.get(name)

    def reason_about_sound(self, sound: np.ndarray, material: str, room_name: str, distance: float = 1.0) -> Dict[str, Any]:
        room = self.get_room(room_name)
        results: Dict[str, Any] = {
            "original_rms": float(np.sqrt(np.mean(sound ** 2))),
            "material": material,
            "room": room_name,
            "distance": distance,
        }
        if room is None:
            results["error"] = "Room not found"
            return results
        absorption = MATERIAL_ABSORPTION.get(material, 0.15)
        distance_attn = 1.0 / max(distance, 0.1)
        room_attenuation = 1.0
        material_filter = 1.0 - (absorption * 0.3)
        room_attenuation = 1.0
        if room.acoustic_props and room.acoustic_props.reverb_time is not None:
            room_attenuation = 1.0 - (room.acoustic_props.reverb_time * 0.1)
        combined_attenuation = distance_attn * material_filter * room_attenuation
        results["attenuation"] = float(combined_attenuation)
        results["expected_reverb_time"] = float(room.acoustic_props.reverb_time)
        results["clarity"] = float(room.acoustic_props.clarity)
        results["definition"] = float(room.acoustic_props.definition)
        results["center_time"] = float(room.acoustic_props.center_time)
        freq_mult = 1.0 - (absorption * distance * 0.1)
        results["frequency_response_multiplier"] = float(freq_mult)
        return results

    def footstep_on_material(self, material: str, force: float = 1.0) -> Dict[str, Any]:
        absorption = MATERIAL_ABSORPTION.get(material, 0.15)
        resonance_map = {
            "wood": 0.4, "metal": 0.9, "glass": 0.85, "stone": 0.7,
            "concrete": 0.5, "ceramic": 0.8, "rubber": 0.1, "fabric": 0.1,
            "ice": 0.75, "snow": 0.2, "mud": 0.15,
        }
        resonance = resonance_map.get(material, 0.5)
        loudness = force * (1.0 - absorption * 0.5)
        sharpness = 1.0 - absorption * 0.5
        duration_mult = 1.0 + absorption * 0.5
        return {
            "material": material,
            "resonance": float(resonance),
            "loudness": float(loudness),
            "sharpness": float(sharpness),
            "duration_multiplier": float(duration_mult),
            "absorption": float(absorption),
        }

    def apply_room_acoustics(self, audio: np.ndarray, room_name: str, distance: float = 1.0) -> np.ndarray:
        room = self.get_room(room_name)
        if room is None or room.acoustic_props is None:
            return audio.copy()
        rt60 = room.acoustic_props.reverb_time
        result = audio.copy()
        result = result * (1.0 / max(distance, 0.1))
        if rt60 > 0.1:
            decay = math.exp(-1.0 / (rt60 * len(audio) / 16000))
            reverb_buf = audio.copy()
            for i in range(len(result)):
                if i < len(reverb_buf):
                    reverb_buf[i] *= decay
                    result[i] += reverb_buf[i] * rt60 * 0.1 * room.acoustic_props.clarity
        return np.clip(result, -0.99, 0.99)

    def simulate_material_interactions(self, materials: List[str]) -> Dict[str, Dict[str, Any]]:
        results = {}
        for mat in materials:
            results[mat] = self.footstep_on_material(mat, 1.0)
        contrast_ratios = {}
        for i, m1 in enumerate(materials):
            for m2 in materials[i + 1:]:
                contrast = abs(results[m1]["resonance"] - results[m2]["resonance"])
                contrast_ratios[f"{m1}_vs_{m2}"] = float(contrast)
        results["contrast_ratios"] = contrast_ratios
        return results


def self_sample_rate_default() -> int:
    return 16000
