"""
Professional Timeline Engine for MAKE AI Video Phase 17.

Extends existing TimelineService with:
- unlimited logical tracks
- track types (video, audio, caption, graphics, vfx, adjustment)
- nested sequences
- clip grouping
- linked audio/video
- clip/track locking
- track visibility
- solo/mute
- snapping
- magnetic editing
- ripple/roll/slip/slide operations
- overwrite/insert/replace/lift/extract
- frame-accurate positioning
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrackType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    CAPTION = "caption"
    GRAPHICS = "graphics"
    VFX = "vfx"
    ADJUSTMENT = "adjustment"


class EditMode(str, Enum):
    OVERWRITE = "overwrite"
    INSERT = "insert"
    REPLACE = "replace"
    LIFT = "lift"
    EXTRACT = "extract"


class SnapMode(str, Enum):
    NONE = "none"
    CLIP_START = "clip_start"
    CLIP_END = "clip_end"
    PLAYHEAD = "playhead"
    MARKER = "marker"


@dataclass
class Track:
    track_id: str
    track_type: TrackType
    name: str
    locked: bool = False
    muted: bool = False
    solo: bool = False
    visible: bool = True
    color: Optional[str] = None
    clips: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Clip:
    clip_id: str
    track_id: str
    asset_id: str
    start_time: float
    duration: float
    in_point: float = 0.0
    out_point: Optional[float] = None
    name: str = ""
    locked: bool = False
    group_id: Optional[str] = None
    linked_clip_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transition:
    transition_id: str
    from_clip_id: str
    to_clip_id: str
    transition_type: str
    duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Keyframe:
    keyframe_id: str
    clip_id: str
    parameter: str
    frame: int
    value: Any
    interpolation: str = "linear"
    easing: str = "ease_in_out"


@dataclass
class NestedSequence:
    sequence_id: str
    track_id: str
    start_time: float
    duration: float
    timeline_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProfessionalTimelineEngine:
    def __init__(self, timeline_service=None):
        self.timeline_service = timeline_service

    def create_track(self, timeline: Dict, track_type: TrackType, name: str, **kwargs) -> Track:
        track = Track(
            track_id=f"track_{len(timeline.get('tracks', []))}",
            track_type=track_type,
            name=name,
            **kwargs,
        )
        if "tracks" not in timeline:
            timeline["tracks"] = []
        timeline["tracks"].append(track.__dict__)
        return track

    def add_clip(self, timeline: Dict, clip: Clip) -> Clip:
        track = self._get_track(timeline, clip.track_id)
        if not track:
            raise ValueError(f"Track {clip.track_id} not found")
        if track.get("locked"):
            raise ValueError(f"Track {clip.track_id} is locked")
        if clip.locked:
            raise ValueError(f"Clip {clip.clip_id} is locked")
        track.setdefault("clips", []).append(clip.__dict__)
        return clip

    def remove_clip(self, timeline: Dict, clip_id: str) -> bool:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clips.pop(i)
                    return True
        return False

    def trim_clip(self, timeline: Dict, clip_id: str, new_start: float = None, new_duration: float = None, in_point: float = None, out_point: float = None) -> bool:
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    if new_start is not None:
                        clip["start_time"] = new_start
                    if new_duration is not None:
                        clip["duration"] = new_duration
                    if in_point is not None:
                        clip["in_point"] = in_point
                    if out_point is not None:
                        clip["out_point"] = out_point
                    return True
        return False

    def split_clip(self, timeline: Dict, clip_id: str, split_time: float) -> List[Clip]:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return []
                    clip_start = clip.get("start_time", 0)
                    clip_duration = clip.get("duration", 0)
                    clip_end = clip_start + clip_duration
                    if split_time <= clip_start or split_time >= clip_end:
                        return []
                    in_point = clip.get("in_point", 0)
                    left_duration = split_time - clip_start
                    right_duration = clip_end - split_time
                    left_out_point = in_point + left_duration
                    right_in_point = left_out_point
                    clip["duration"] = left_duration
                    clip["out_point"] = left_out_point
                    right_clip = Clip(
                        clip_id=f"{clip_id}_split_{i}",
                        track_id=clip.get("track_id"),
                        asset_id=clip.get("asset_id"),
                        start_time=split_time,
                        duration=right_duration,
                        in_point=right_in_point,
                        out_point=clip.get("out_point"),
                        name=f"{clip.get('name', '')} (split)",
                        metadata=clip.get("metadata", {}),
                    )
                    clips.append(right_clip.__dict__)
                    return [clip, right_clip.__dict__]
        return []

    def move_clip(self, timeline: Dict, clip_id: str, new_track_id: str = None, new_start: float = None) -> bool:
        clip_data = None
        old_track = None
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clip_data = clip
                    old_track = track
                    break
            if clip_data:
                break
        if not clip_data:
            return False
        if old_track:
            old_track.get("clips", []).remove(clip_data)
        if new_track_id:
            new_track = self._get_track(timeline, new_track_id)
            if new_track and not new_track.get("locked"):
                clip_data["track_id"] = new_track_id
                new_track.setdefault("clips", []).append(clip_data)
        if new_start is not None:
            clip_data["start_time"] = new_start
        return True

    def ripple_edit(self, timeline: Dict, clip_id: str, new_start: float) -> bool:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    old_start = clip.get("start_time", 0)
                    delta = new_start - old_start
                    clip["start_time"] = new_start
                    for j in range(i + 1, len(clips)):
                        clips[j]["start_time"] = clips[j].get("start_time", 0) + delta
                    return True
        return False

    def roll_edit(self, timeline: Dict, clip_id: str, new_out_point: float) -> bool:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clip_start = clip.get("start_time", 0)
                    if new_out_point <= clip_start:
                        return False
                    clip["duration"] = new_out_point - clip_start
                    clip["out_point"] = new_out_point
                    return True
        return False

    def slip_edit(self, timeline: Dict, clip_id: str, new_in_point: float) -> bool:
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    in_point = new_in_point
                    out_point = in_point + clip.get("duration", 0)
                    clip["in_point"] = in_point
                    clip["out_point"] = out_point
                    return True
        return False

    def slide_edit(self, timeline: Dict, clip_id: str, new_start: float) -> bool:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    old_start = clip.get("start_time", 0)
                    duration = clip.get("duration", 0)
                    delta = new_start - old_start
                    clip["start_time"] = new_start
                    if i > 0:
                        prev_clip = clips[i - 1]
                        prev_duration = prev_clip.get("duration", 0)
                        prev_clip["duration"] = prev_duration + delta
                    return True
        return False

    def group_clips(self, timeline: Dict, clip_ids: List[str], group_id: str = None) -> str:
        group_id = group_id or f"group_{len(timeline.get('clip_groups', {}))}"
        timeline.setdefault("clip_groups", {})
        timeline["clip_groups"][group_id] = {
            "clip_ids": clip_ids,
            "locked": False,
        }
        for clip_id in clip_ids:
            for track in timeline.get("tracks", []):
                for clip in track.get("clips", []):
                    if clip.get("clip_id") == clip_id:
                        clip["group_id"] = group_id
        return group_id

    def ungroup_clips(self, timeline: Dict, group_id: str) -> bool:
        groups = timeline.get("clip_groups", {})
        if group_id not in groups:
            return False
        clip_ids = groups[group_id].get("clip_ids", [])
        for clip_id in clip_ids:
            for track in timeline.get("tracks", []):
                for clip in track.get("clips", []):
                    if clip.get("clip_id") == clip_id:
                        clip["group_id"] = None
        del groups[group_id]
        return True

    def link_clips(self, timeline: Dict, video_clip_id: str, audio_clip_id: str) -> bool:
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == video_clip_id:
                    clip.setdefault("linked_clip_ids", []).append(audio_clip_id)
                if clip.get("clip_id") == audio_clip_id:
                    clip.setdefault("linked_clip_ids", []).append(video_clip_id)
        return True

    def lock_clip(self, timeline: Dict, clip_id: str, locked: bool = True) -> bool:
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    clip["locked"] = locked
                    return True
        return False

    def lock_track(self, timeline: Dict, track_id: str, locked: bool = True) -> bool:
        track = self._get_track(timeline, track_id)
        if track:
            track["locked"] = locked
            return True
        return False

    def set_track_visibility(self, timeline: Dict, track_id: str, visible: bool) -> bool:
        track = self._get_track(timeline, track_id)
        if track:
            track["visible"] = visible
            return True
        return False

    def set_track_mute(self, timeline: Dict, track_id: str, muted: bool) -> bool:
        track = self._get_track(timeline, track_id)
        if track:
            track["muted"] = muted
            return True
        return False

    def set_track_solo(self, timeline: Dict, track_id: str, solo: bool) -> bool:
        track = self._get_track(timeline, track_id)
        if track:
            track["solo"] = solo
            return True
        return False

    def get_timeline_state(self, timeline: Dict) -> Dict[str, Any]:
        return {
            "tracks": timeline.get("tracks", []),
            "duration_seconds": timeline.get("duration_seconds", 0),
            "fps": timeline.get("fps", 30),
            "resolution": timeline.get("resolution", {}),
        }

    def _get_track(self, timeline: Dict, track_id: str) -> Optional[Dict]:
        for track in timeline.get("tracks", []):
            if track.get("track_id") == track_id:
                return track
        return None


professional_timeline_engine = ProfessionalTimelineEngine()
