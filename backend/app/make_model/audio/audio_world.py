"""
AudioWorld: rooms, materials, objects, people, weather, vehicles, crowds, machinery.

A declarative description of an acoustic environment used by the spatial and
acoustic engines.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Weather(str, Enum):
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    WIND = "wind"
    FOG = "fog"
    THUNDERSTORM = "thunderstorm"


class CrowdDensity(str, Enum):
    NONE = "none"
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    PACKED = "packed"


@dataclass
class Person:
    person_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    voice_id: Optional[str] = None
    facing: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    activity: str = "standing"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "position": list(self.position),
            "voice_id": self.voice_id,
            "facing": list(self.facing),
            "activity": self.activity,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Person":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "position" in filtered:
            filtered["position"] = tuple(filtered["position"])
        if "facing" in filtered:
            filtered["facing"] = tuple(filtered["facing"])
        return cls(**filtered)


@dataclass
class Vehicle:
    vehicle_id: str
    vehicle_type: str = "car"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: float = 0.0
    engine_state: str = "off"  # off | idling | moving
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "position": list(self.position),
            "velocity": self.velocity,
            "engine_state": self.engine_state,
            "metadata": dict(self.metadata),
        }


@dataclass
class Machinery:
    machine_id: str
    machine_type: str = "industrial"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    state: str = "off"  # off | running | malfunction
    loudness: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "machine_type": self.machine_type,
            "position": list(self.position),
            "state": self.state,
            "loudness": self.loudness,
            "metadata": dict(self.metadata),
        }


class AudioWorld:
    """Represents rooms, materials, objects, people, weather, vehicles, crowds, machinery."""

    def __init__(self, world_id: str = "") -> None:
        self.world_id = world_id or f"world_{int(time.time())}"
        self.rooms: Dict[str, "Room"] = {}
        self.materials: Dict[str, "Material"] = {}
        self.objects: Dict[str, "ObjectAcoustics"] = {}
        self.people: Dict[str, Person] = {}
        self.vehicles: Dict[str, Vehicle] = {}
        self.machinery: Dict[str, Machinery] = {}
        self.weather: Weather = Weather.CLEAR
        self.crowd_density: CrowdDensity = CrowdDensity.NONE
        self.background_noise: float = 0.1
        self.metadata: Dict[str, Any] = {"created_at": time.time()}

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def add_room(self, room: "Room") -> None:
        self.rooms[room.room_id] = room

    def add_material(self, material: "Material") -> None:
        self.materials[material.material_id] = material

    def add_object(self, obj: "ObjectAcoustics") -> None:
        self.objects[obj.object_id] = obj

    def add_person(self, person: Person) -> None:
        self.people[person.person_id] = person

    def add_vehicle(self, vehicle: Vehicle) -> None:
        self.vehicles[vehicle.vehicle_id] = vehicle

    def add_machinery(self, machine: Machinery) -> None:
        self.machinery[machine.machine_id] = machine

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_room(self, room_id: str) -> Optional["Room"]:
        return self.rooms.get(room_id)

    def get_material(self, material_id: str) -> Optional["Material"]:
        return self.materials.get(material_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "rooms": {rid: r.to_dict() for rid, r in self.rooms.items()},
            "materials": {mid: m.to_dict() for mid, m in self.materials.items()},
            "objects": {oid: o.to_dict() for oid, o in self.objects.items()},
            "people": {pid: p.to_dict() for pid, p in self.people.items()},
            "vehicles": {vid: v.to_dict() for vid, v in self.vehicles.items()},
            "machinery": {mid: m.to_dict() for mid, m in self.machinery.items()},
            "weather": self.weather.value,
            "crowd_density": self.crowd_density.value,
            "background_noise": self.background_noise,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioWorld":
        world = cls(world_id=data.get("world_id", ""))
        world.weather = Weather(data.get("weather", "clear"))
        world.crowd_density = CrowdDensity(data.get("crowd_density", "none"))
        world.background_noise = float(data.get("background_noise", 0.1))
        world.metadata = data.get("metadata", {})
        for raw in data.get("rooms", {}).values():
            world.add_room(Room.from_dict(raw))
        for raw in data.get("materials", {}).values():
            world.add_material(Material.from_dict(raw))
        for raw in data.get("objects", {}).values():
            world.add_object(ObjectAcoustics.from_dict(raw))
        for raw in data.get("people", {}).values():
            world.add_person(Person.from_dict(raw))
        for raw in data.get("vehicles", {}).values():
            world.add_vehicle(Vehicle.from_dict(raw))
        for raw in data.get("machinery", {}).values():
            world.add_machinery(Machinery.from_dict(raw))
        return world


# Avoid circular imports at module load time.
from app.make_model.audio.room import Room  # noqa: E402
from app.make_model.audio.material import Material  # noqa: E402
from app.make_model.audio.object_acoustics import ObjectAcoustics  # noqa: E402