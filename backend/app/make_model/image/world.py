"""MAKE Image Engine — World Representation.

Structured internal representation of visual worlds, scenes, objects,
humans, cameras, lighting, materials, and relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ----------------------------------------------------------------------
# Core records
# ----------------------------------------------------------------------


@dataclass
class Camera:
    position: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    focal_length: float = 50.0
    aperture: float = 2.8
    focus_distance: float = 1.0
    sensor_width: float = 36.0
    sensor_height: float = 24.0
    is_anamorphic: bool = False
    shutter_angle: float = 180.0
    frame_rate: float = 24.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "rotation": list(self.rotation),
            "focal_length": self.focal_length,
            "aperture": self.aperture,
            "focus_distance": self.focus_distance,
            "sensor_width": self.sensor_width,
            "sensor_height": self.sensor_height,
            "is_anamorphic": self.is_anamorphic,
            "shutter_angle": self.shutter_angle,
            "frame_rate": self.frame_rate,
        }


@dataclass
class Lighting:
    light_type: str = "natural"
    key_direction: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    key_intensity: float = 1.0
    key_color: Tuple[float, float, float] = (1.0, 0.95, 0.9)
    fill_intensity: float = 0.3
    fill_color: Tuple[float, float, float] = (0.9, 0.95, 1.0)
    rim_intensity: float = 0.0
    rim_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    ambient: float = 0.2
    volumetric: bool = False
    cast_shadows: bool = True
    exposure: float = 0.0
    contrast: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_type": self.light_type,
            "key_direction": list(self.key_direction),
            "key_intensity": self.key_intensity,
            "key_color": list(self.key_color),
            "fill_intensity": self.fill_intensity,
            "fill_color": list(self.fill_color),
            "rim_intensity": self.rim_intensity,
            "rim_color": list(self.rim_color),
            "ambient": self.ambient,
            "volumetric": self.volumetric,
            "cast_shadows": self.cast_shadows,
            "exposure": self.exposure,
            "contrast": self.contrast,
        }


@dataclass
class Material:
    base_color: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    metallic: float = 0.0
    roughness: float = 0.5
    specular: float = 0.5
    clearcoat: float = 0.0
    clearcoat_roughness: float = 0.0
    transmission: float = 0.0
    ior: float = 1.5
    subsurface: float = 0.0
    subsurface_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    sheen: float = 0.0
    anisotropic: float = 0.0
    tags: List[str] = field(default_factory=lambda: ["default"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_color": list(self.base_color),
            "metallic": self.metallic,
            "roughness": self.roughness,
            "specular": self.specular,
            "clearcoat": self.clearcoat,
            "clearcoat_roughness": self.clearcoat_roughness,
            "transmission": self.transmission,
            "ior": self.ior,
            "subsurface": self.subsurface,
            "subsurface_color": list(self.subsurface_color),
            "sheen": self.sheen,
            "anisotropic": self.anisotropic,
            "tags": list(self.tags),
        }


@dataclass
class Geometry:
    bbox: Tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    primitive: str = "unknown"
    mesh_path: Optional[str] = None
    vertices: Optional[np.ndarray] = None
    normals: Optional[np.ndarray] = None
    depth_map: Optional[np.ndarray] = None
    normal_map: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": list(self.bbox),
            "primitive": self.primitive,
            "mesh_path": self.mesh_path,
            "has_vertices": self.vertices is not None,
            "has_normals": self.normals is not None,
            "has_depth": self.depth_map is not None,
        }


@dataclass
class Object:
    object_id: str
    label: str = "object"
    geometry: Optional[Geometry] = None
    material: Optional[Material] = None
    pose: Optional[np.ndarray] = None
    embedding: Optional[np.ndarray] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "label": self.label,
            "geometry": self.geometry.to_dict() if self.geometry else None,
            "material": self.material.to_dict() if self.material else None,
            "attributes": dict(self.attributes),
        }


@dataclass
class Human:
    human_id: str
    identity_embedding: Optional[np.ndarray] = None
    face_bbox: Optional[Tuple[float, float, float, float]] = None
    pose: Optional[np.ndarray] = None
    expression: str = "neutral"
    gaze: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    body_proportions: Optional[np.ndarray] = None
    hairstyle: Optional[str] = None
    skin_characteristics: Optional[Dict[str, Any]] = None
    clothing: Optional[List[str]] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "human_id": self.human_id,
            "expression": self.expression,
            "gaze": list(self.gaze),
            "face_bbox": list(self.face_bbox) if self.face_bbox else None,
            "hairstyle": self.hairstyle,
            "clothing": list(self.clothing) if self.clothing else None,
            "attributes": dict(self.attributes),
        }


@dataclass
class Relationship:
    subject_id: str
    predicate: str
    object_id: str
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "predicate": self.predicate,
            "object_id": self.object_id,
            "confidence": self.confidence,
            "attributes": dict(self.attributes),
        }


@dataclass
class Scene:
    scene_id: str
    camera: Optional[Camera] = None
    lighting: Optional[Lighting] = None
    environment: Optional[str] = None
    atmosphere: Optional[str] = None
    objects: Dict[str, Object] = field(default_factory=dict)
    humans: Dict[str, Human] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    background: Optional[np.ndarray] = None
    depth_map: Optional[np.ndarray] = None
    segmentation: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_object(self, obj: Object) -> None:
        self.objects[obj.object_id] = obj

    def add_human(self, human: Human) -> None:
        self.humans[human.human_id] = human

    def add_relationship(self, rel: Relationship) -> None:
        self.relationships.append(rel)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "camera": self.camera.to_dict() if self.camera else None,
            "lighting": self.lighting.to_dict() if self.lighting else None,
            "environment": self.environment,
            "atmosphere": self.atmosphere,
            "objects": {k: v.to_dict() for k, v in self.objects.items()},
            "humans": {k: v.to_dict() for k, v in self.humans.items()},
            "relationships": [r.to_dict() for r in self.relationships],
            "metadata": dict(self.metadata),
        }


@dataclass
class WorldState:
    world_id: str
    scenes: Dict[str, Scene] = field(default_factory=dict)
    global_attributes: Dict[str, Any] = field(default_factory=dict)
    edit_history: List[Dict[str, Any]] = field(default_factory=list)

    def add_scene(self, scene: Scene) -> None:
        self.scenes[scene.scene_id] = scene

    def record_edit(self, operation: str, params: Dict[str, Any]) -> None:
        self.edit_history.append({"operation": operation, "params": params})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "scenes": {k: v.to_dict() for k, v in self.scenes.items()},
            "global_attributes": dict(self.global_attributes),
            "edit_history": list(self.edit_history),
        }


# ----------------------------------------------------------------------
# Reality DNA
# ----------------------------------------------------------------------


@dataclass
class RealityDNA:
    world_id: str
    geometry_summary: Dict[str, Any] = field(default_factory=dict)
    material_summary: Dict[str, Any] = field(default_factory=dict)
    lighting_summary: Dict[str, Any] = field(default_factory=dict)
    camera_summary: Dict[str, Any] = field(default_factory=dict)
    color_palette: List[Tuple[float, float, float]] = field(default_factory=list)
    composition_summary: Dict[str, Any] = field(default_factory=dict)
    depth_summary: Dict[str, Any] = field(default_factory=dict)
    identity_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    object_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    spatial_relationships: List[Dict[str, Any]] = field(default_factory=list)
    visual_style: str = "photographic"
    dynamic_range: str = "hdr"
    exposure: float = 0.0
    contrast: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "geometry_summary": dict(self.geometry_summary),
            "material_summary": dict(self.material_summary),
            "lighting_summary": dict(self.lighting_summary),
            "camera_summary": dict(self.camera_summary),
            "color_palette": [list(c) for c in self.color_palette],
            "composition_summary": dict(self.composition_summary),
            "depth_summary": dict(self.depth_summary),
            "identity_summaries": {k: dict(v) for k, v in self.identity_summaries.items()},
            "object_summaries": {k: dict(v) for k, v in self.object_summaries.items()},
            "spatial_relationships": [dict(r) for r in self.spatial_relationships],
            "visual_style": self.visual_style,
            "dynamic_range": self.dynamic_range,
            "exposure": self.exposure,
            "contrast": self.contrast,
        }


# ----------------------------------------------------------------------
# World operations
# ----------------------------------------------------------------------


class WorldFork:
    def __init__(self, state: WorldState):
        self.state = state

    def create_alternate(self, scene_id: str, overrides: Dict[str, Any]) -> WorldState:
        import copy
        new = copy.deepcopy(self.state)
        new.world_id = f"{new.world_id}_fork_{len(new.edit_history)}"
        if scene_id in new.scenes:
            scene = new.scenes[scene_id]
            for key, value in overrides.items():
                if hasattr(scene, key):
                    setattr(scene, key, value)
        new.record_edit("world_fork", {"scene_id": scene_id, "overrides": overrides})
        return new


class CameraTeleport:
    def __init__(self, scene: Scene):
        self.scene = scene

    def move(self, position: Tuple[float, float, float], rotation: Tuple[float, float, float], focal_length: float = 50.0) -> Camera:
        cam = self.scene.camera or Camera()
        cam.position = position
        cam.rotation = rotation
        cam.focal_length = focal_length
        self.scene.camera = cam
        return cam

    def presets(self) -> Dict[str, Camera]:
        base = self.scene.camera or Camera()
        presets = {
            "front": Camera(position=(0.0, 0.0, base.focus_distance * 2.0), rotation=(0.0, 0.0, 0.0), focal_length=base.focal_length),
            "rear": Camera(position=(0.0, 0.0, -base.focus_distance * 2.0), rotation=(0.0, 180.0, 0.0), focal_length=base.focal_length),
            "left": Camera(position=(-base.focus_distance * 2.0, 0.0, 0.0), rotation=(0.0, 90.0, 0.0), focal_length=base.focal_length),
            "right": Camera(position=(base.focus_distance * 2.0, 0.0, 0.0), rotation=(0.0, -90.0, 0.0), focal_length=base.focal_length),
            "overhead": Camera(position=(0.0, base.focus_distance * 3.0, 0.0), rotation=(-90.0, 0.0, 0.0), focal_length=base.focal_length),
            "low_angle": Camera(position=(0.0, -base.focus_distance * 2.0, base.focus_distance), rotation=(45.0, 0.0, 0.0), focal_length=base.focal_length),
            "close_up": Camera(position=(0.0, 0.0, base.focus_distance * 0.5), rotation=(0.0, 0.0, 0.0), focal_length=85.0),
            "wide": Camera(position=(0.0, 0.0, base.focus_distance * 4.0), rotation=(0.0, 0.0, 0.0), focal_length=24.0),
            "macro": Camera(position=(0.0, 0.0, base.focus_distance * 0.1), rotation=(0.0, 0.0, 0.0), focal_length=100.0),
            "portrait": Camera(position=(0.0, 0.0, base.focus_distance * 1.5), rotation=(0.0, 0.0, 0.0), focal_length=85.0),
        }
        return presets


class TimeMachine:
    def __init__(self, scene: Scene):
        self.scene = scene

    def set_time_of_day(self, time: str) -> Lighting:
        presets = {
            "sunrise": Lighting(light_type="sunlight", key_direction=(1.0, 0.1, 0.5), key_intensity=0.8, key_color=(1.0, 0.6, 0.4), ambient=0.3),
            "morning": Lighting(light_type="sunlight", key_direction=(1.0, 0.3, 0.3), key_intensity=1.0, key_color=(1.0, 0.95, 0.9), ambient=0.35),
            "noon": Lighting(light_type="sunlight", key_direction=(0.0, 1.0, 0.0), key_intensity=1.2, key_color=(1.0, 1.0, 0.95), ambient=0.4),
            "sunset": Lighting(light_type="sunlight", key_direction=(-1.0, 0.1, 0.5), key_intensity=0.9, key_color=(1.0, 0.4, 0.2), ambient=0.25),
            "night": Lighting(light_type="moonlight", key_direction=(-1.0, 0.2, -0.5), key_intensity=0.2, key_color=(0.6, 0.7, 1.0), ambient=0.15),
            "rain": Lighting(light_type="overcast", key_direction=(0.0, 1.0, 0.0), key_intensity=0.6, key_color=(0.8, 0.85, 0.9), ambient=0.5),
            "snow": Lighting(light_type="overcast", key_direction=(0.0, 1.0, 0.0), key_intensity=0.7, key_color=(0.95, 0.95, 1.0), ambient=0.45),
            "fog": Lighting(light_type="atmospheric", key_direction=(0.0, 1.0, 0.0), key_intensity=0.5, key_color=(0.9, 0.9, 0.85), ambient=0.6, volumetric=True),
            "storm": Lighting(light_type="dramatic", key_direction=(0.0, 1.0, 0.0), key_intensity=0.4, key_color=(0.7, 0.75, 0.8), ambient=0.2),
        }
        lighting = presets.get(time, Lighting())
        self.scene.lighting = lighting
        return lighting


class PersistentWorldState:
    def __init__(self, state: WorldState):
        self.state = state

    def apply_edit(self, operation: str, params: Dict[str, Any]) -> WorldState:
        import copy
        new = copy.deepcopy(self.state)
        new.record_edit(operation, params)
        return new

    def fork(self, scene_id: str, overrides: Dict[str, Any]) -> WorldState:
        return WorldFork(self.state).create_alternate(scene_id, overrides)


# ----------------------------------------------------------------------
# World representation container
# ----------------------------------------------------------------------


class WorldRepresentation:
    def __init__(self, world_id: str = "world"):
        self.state = WorldState(world_id=world_id)

    def add_scene(self, scene: Scene) -> None:
        self.state.add_scene(scene)

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        return self.state.scenes.get(scene_id)

    def extract_reality_dna(self, scene_id: str) -> RealityDNA:
        scene = self.get_scene(scene_id)
        if not scene:
            return RealityDNA(world_id=self.state.world_id)
        dna = RealityDNA(
            world_id=self.state.world_id,
            camera_summary=scene.camera.to_dict() if scene.camera else {},
            lighting_summary=scene.lighting.to_dict() if scene.lighting else {},
            object_summaries={k: v.to_dict() for k, v in scene.objects.items()},
            identity_summaries={k: v.to_dict() for k, v in scene.humans.items()},
            spatial_relationships=[r.to_dict() for r in scene.relationships],
        )
        if scene.environment:
            dna.geometry_summary["environment"] = scene.environment
        if scene.atmosphere:
            dna.lighting_summary["atmosphere"] = scene.atmosphere
        return dna

    def camera_teleport(self, scene_id: str, preset: str) -> Optional[Camera]:
        scene = self.get_scene(scene_id)
        if not scene:
            return None
        teleport = CameraTeleport(scene)
        presets = teleport.presets()
        cam = presets.get(preset)
        if cam:
            scene.camera = cam
        return cam

    def time_machine(self, scene_id: str, time: str) -> Optional[Lighting]:
        scene = self.get_scene(scene_id)
        if not scene:
            return None
        machine = TimeMachine(scene)
        lighting = machine.set_time_of_day(time)
        return lighting

    def world_fork(self, scene_id: str, overrides: Dict[str, Any]) -> WorldState:
        return WorldFork(self.state).create_alternate(scene_id, overrides)

    def to_dict(self) -> Dict[str, Any]:
        return self.state.to_dict()


__all__ = [
    "WorldRepresentation",
    "WorldState",
    "Scene",
    "Object",
    "Human",
    "Camera",
    "Lighting",
    "Material",
    "Geometry",
    "Relationship",
    "RealityDNA",
    "WorldFork",
    "CameraTeleport",
    "TimeMachine",
    "PersistentWorldState",
]
