"""World representation training signals.

This module is the *model-side* representation for objects, people,
environment, motion, camera, and material. It is NOT a new vision
engine; it is a set of training targets the data engine extracts and
the model is conditioned on.

The representations are kept lightweight (numpy-compatible) so they
can be tested without GPU. The training loop reads them as tensors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ----------------------------------------------------------------------
# Object representation
# ----------------------------------------------------------------------


@dataclass
class ObjectRepresentation:
    """Training-time representation of a single object instance.

    Fields:
        id:          stable id across frames
        shape_class: one of {box, sphere, cylinder, mesh, custom, unknown}
        appearance:  RGB(A) mean of segmented region (4 floats)
        material:    one of {metal, plastic, glass, fabric, wood, skin, unknown}
        position:    (x, y, z) world coords or (cx, cy) image coords
        scale:       (sx, sy, sz)
        orientation: (roll, pitch, yaw) radians
        deformation: scalar in [0, 1] describing elastic deformation
        mask_path:   optional path to alpha mask PNG/MP4
        source:      'manual' | 'auto_segment' | 'synth'
    """

    id: str
    shape_class: str = "unknown"
    appearance: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    material: str = "unknown"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    deformation: float = 0.0
    mask_path: Optional[str] = None
    source: str = "auto_segment"


# ----------------------------------------------------------------------
# Person representation
# ----------------------------------------------------------------------


@dataclass
class PersonRepresentation:
    """Training-time representation of a person.

    Fields:
        id:                  stable id
        pose_seq:            T x J x 2 list of joint (x, y) pixels
        face_emb:            16-d face embedding (training only)
        body_emb:            16-d body embedding (training only)
        clothing_class:      list of clothing tags
        interaction_partner: id of other person/object being interacted with
    """

    id: str
    pose_seq: List[List[Tuple[float, float]]] = field(default_factory=list)
    face_emb: Optional[List[float]] = None
    body_emb: Optional[List[float]] = None
    clothing_class: List[str] = field(default_factory=list)
    interaction_partner: Optional[str] = None


# ----------------------------------------------------------------------
# Environment representation
# ----------------------------------------------------------------------


@dataclass
class EnvironmentRepresentation:
    """Training-time representation of a scene/environment.

    Fields:
        layout:     {walls, floor, ceiling, furniture} -> list of (x,y,z) anchors
        lighting:   {key_dir, fill_dir, ambient_lux, color_temp_k}
        atmosphere: {fog, rain, snow, dust, smoke}
        weather:    one of {clear, cloudy, rain, snow, fog, storm, night}
        time:       {hour, minute} 24h
    """

    layout: Dict[str, List[Tuple[float, float, float]]] = field(default_factory=dict)
    lighting: Dict[str, float] = field(default_factory=dict)
    atmosphere: Dict[str, float] = field(default_factory=dict)
    weather: str = "clear"
    time: Dict[str, int] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Motion representation
# ----------------------------------------------------------------------


@dataclass
class MotionRepresentation:
    """Training-time representation of motion in a clip.

    Fields:
        velocity:      (vx, vy, vz)
        acceleration:  (ax, ay, az)
        trajectory:    list of (x, y, z) per keyframe
        action_class:  one of a known vocabulary
        physics_violations: list of frame indices where physics flags fire
    """

    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)
    action_class: str = "unknown"
    physics_violations: List[int] = field(default_factory=list)


# ----------------------------------------------------------------------
# Camera representation
# ----------------------------------------------------------------------


@dataclass
class CameraRepresentation:
    """Training-time representation of the cinematographic camera.

    Fields:
        position:     (x, y, z) world
        orientation:  (roll, pitch, yaw) radians
        movement:     one of {static, pan, tilt, dolly, truck, crane, orbit,
                              push_in, pull_out, zoom, tracking, handheld,
                              aerial, fpv}
        focal_mm:     focal length in mm (35mm equivalent)
        sensor_w_mm:  sensor width in mm
        depth_of_field_m: in-focus distance
        composition:  list of {rule_of_thirds, leading_lines, ...}
    """

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    movement: str = "static"
    focal_mm: float = 35.0
    sensor_w_mm: float = 36.0
    depth_of_field_m: float = 5.0
    composition: List[str] = field(default_factory=list)

    @property
    def horizontal_fov_rad(self) -> float:
        return float(2.0 * math.atan(self.sensor_w_mm / (2.0 * max(self.focal_mm, 1e-3))))


# ----------------------------------------------------------------------
# Material representation
# ----------------------------------------------------------------------


@dataclass
class MaterialRepresentation:
    """Training-time representation of a surface material.

    Fields:
        roughness:     0..1
        metallic:      0..1
        transmission:  0..1 (glass)
        ior:           index of refraction
        albedo:        RGB
        normal_path:   optional path to surface normal map
    """

    roughness: float = 0.5
    metallic: float = 0.0
    transmission: float = 0.0
    ior: float = 1.5
    albedo: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    normal_path: Optional[str] = None


# ----------------------------------------------------------------------
# World sample (combined)
# ----------------------------------------------------------------------


@dataclass
class WorldSample:
    """Combined world representation for a single training clip."""

    sample_id: str
    objects: List[ObjectRepresentation] = field(default_factory=list)
    people: List[PersonRepresentation] = field(default_factory=list)
    environment: EnvironmentRepresentation = field(default_factory=EnvironmentRepresentation)
    motion: MotionRepresentation = field(default_factory=MotionRepresentation)
    camera: CameraRepresentation = field(default_factory=CameraRepresentation)
    materials: List[MaterialRepresentation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorldSample":
        objs = [ObjectRepresentation(**o) for o in d.get("objects", [])]
        people = [PersonRepresentation(**p) for p in d.get("people", [])]
        env = EnvironmentRepresentation(**d.get("environment", {}))
        motion = MotionRepresentation(**d.get("motion", {}))
        cam = CameraRepresentation(**d.get("camera", {}))
        mats = [MaterialRepresentation(**m) for m in d.get("materials", [])]
        return cls(
            sample_id=d["sample_id"],
            objects=objs,
            people=people,
            environment=env,
            motion=motion,
            camera=cam,
            materials=mats,
        )

    def encoding_dim(self) -> int:
        """Fixed-size flat encoding dim for the conditioning MLP."""
        # 8 obj slots * 32 = 256; 2 people * 32 = 64; env 16; motion 8;
        # camera 16; material 8 = ~368 (we expose a single stable dim)
        return 368


__all__ = [
    "ObjectRepresentation",
    "PersonRepresentation",
    "EnvironmentRepresentation",
    "MotionRepresentation",
    "CameraRepresentation",
    "MaterialRepresentation",
    "WorldSample",
]
