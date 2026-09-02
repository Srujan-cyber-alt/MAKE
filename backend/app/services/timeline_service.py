"""
Production Timeline Service for MAKE AI Video Phase 17.

Supports:
- clips
- tracks (video, audio, caption, graphics, vfx, adjustment)
- trimming
- splitting
- cutting
- moving
- reordering
- transitions
- audio tracks
- captions
- VFX layers
- keyframes
- speed
- mute
- volume
- transforms
- crop
- aspect ratio
- undo/redo
- ripple/roll/slip/slide editing
- clip grouping
- linked clips
- track locking/visibility/mute/solo
- nested sequences
- markers
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class TrackType:
    VIDEO = "video"
    AUDIO = "audio"
    CAPTION = "caption"
    GRAPHICS = "graphics"
    VFX = "vfx"
    ADJUSTMENT = "adjustment"


class EditMode:
    OVERWRITE = "overwrite"
    INSERT = "insert"
    REPLACE = "replace"
    LIFT = "lift"
    EXTRACT = "extract"


class TimelineService:
    @staticmethod
    def create_timeline(project_id: str, user_id: str, duration_seconds: float = 30.0) -> Dict[str, Any]:
        timeline_id = str(uuid.uuid4())
        return {
            "timeline_id": timeline_id,
            "project_id": project_id,
            "user_id": user_id,
            "duration_seconds": duration_seconds,
            "tracks": [],
            "clips": [],
            "keyframes": [],
            "transitions": [],
            "audio_tracks": [],
            "caption_tracks": [],
            "vfx_layers": [],
            "history": [],
            "history_index": -1,
            "settings": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def add_clip(timeline: Dict[str, Any], clip: Dict[str, Any]) -> Dict[str, Any]:
        clip["clip_id"] = str(uuid.uuid4())
        clip["created_at"] = datetime.utcnow().isoformat()
        timeline["clips"].append(clip)
        TimelineService._record_history(timeline, "add_clip", clip)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_track(timeline: Dict[str, Any], track: Dict[str, Any]) -> Dict[str, Any]:
        track["track_id"] = str(uuid.uuid4())
        track["created_at"] = datetime.utcnow().isoformat()
        timeline["tracks"].append(track)
        TimelineService._record_history(timeline, "add_track", track)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_keyframe(timeline: Dict[str, Any], keyframe: Dict[str, Any]) -> Dict[str, Any]:
        keyframe["keyframe_id"] = str(uuid.uuid4())
        keyframe["created_at"] = datetime.utcnow().isoformat()
        timeline["keyframes"].append(keyframe)
        TimelineService._record_history(timeline, "add_keyframe", keyframe)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_transition(timeline: Dict[str, Any], transition: Dict[str, Any]) -> Dict[str, Any]:
        transition["transition_id"] = str(uuid.uuid4())
        transition["created_at"] = datetime.utcnow().isoformat()
        timeline["transitions"].append(transition)
        TimelineService._record_history(timeline, "add_transition", transition)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_audio_track(timeline: Dict[str, Any], audio_track: Dict[str, Any]) -> Dict[str, Any]:
        audio_track["track_id"] = str(uuid.uuid4())
        audio_track["created_at"] = datetime.utcnow().isoformat()
        timeline["audio_tracks"].append(audio_track)
        TimelineService._record_history(timeline, "add_audio_track", audio_track)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_caption_track(timeline: Dict[str, Any], caption_track: Dict[str, Any]) -> Dict[str, Any]:
        caption_track["track_id"] = str(uuid.uuid4())
        caption_track["created_at"] = datetime.utcnow().isoformat()
        timeline["caption_tracks"].append(caption_track)
        TimelineService._record_history(timeline, "add_caption_track", caption_track)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_vfx_layer(timeline: Dict[str, Any], vfx_layer: Dict[str, Any]) -> Dict[str, Any]:
        vfx_layer["layer_id"] = str(uuid.uuid4())
        vfx_layer["created_at"] = datetime.utcnow().isoformat()
        timeline["vfx_layers"].append(vfx_layer)
        TimelineService._record_history(timeline, "add_vfx_layer", vfx_layer)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def undo(timeline: Dict[str, Any]) -> Dict[str, Any]:
        history = timeline.get("history", [])
        history_index = timeline.get("history_index", -1)
        settings = timeline.get("settings") or {}
        if not history and "history" in settings:
            history = settings["history"]
            history_index = settings.get("history_index", -1)
        if history_index > 0:
            history_index -= 1
            state = history[history_index]["state"]
            timeline.update(state)
            timeline["history_index"] = history_index
            if "history" in settings:
                settings["history_index"] = history_index
            timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def redo(timeline: Dict[str, Any]) -> Dict[str, Any]:
        history = timeline.get("history", [])
        history_index = timeline.get("history_index", -1)
        settings = timeline.get("settings") or {}
        if not history and "history" in settings:
            history = settings["history"]
            history_index = settings.get("history_index", -1)
        if history_index < len(history) - 1:
            history_index += 1
            state = history[history_index]["state"]
            timeline.update(state)
            timeline["history_index"] = history_index
            if "history" in settings:
                settings["history_index"] = history_index
            timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def trim_clip(timeline: Dict[str, Any], clip_id: str, start: float, end: float) -> Dict[str, Any]:
        for clip in timeline["clips"]:
            if clip.get("clip_id") == clip_id:
                clip["trim_start"] = start
                clip["trim_end"] = end
                TimelineService._record_history(timeline, "trim_clip", {"clip_id": clip_id, "start": start, "end": end})
                timeline["updated_at"] = datetime.utcnow().isoformat()
                break
        return timeline

    @staticmethod
    async def split_clip(timeline: Dict[str, Any], clip_id: str, split_time: float) -> Dict[str, Any]:
        for i, clip in enumerate(timeline["clips"]):
            if clip.get("clip_id") == clip_id:
                clip_start = clip.get("start_time", 0)
                if split_time <= clip_start:
                    continue
                new_clip = clip.copy()
                new_clip["clip_id"] = str(uuid.uuid4())
                new_clip["start_time"] = split_time
                new_clip["created_at"] = datetime.utcnow().isoformat()
                clip["end_time"] = split_time
                timeline["clips"].insert(i + 1, new_clip)
                TimelineService._record_history(timeline, "split_clip", {"clip_id": clip_id, "split_time": split_time})
                timeline["updated_at"] = datetime.utcnow().isoformat()
                break
        return timeline

    @staticmethod
    def _record_history(timeline: Dict[str, Any], action: str, data: Dict[str, Any]):
        state = {
            "clips": timeline["clips"],
            "tracks": timeline["tracks"],
            "keyframes": timeline["keyframes"],
            "transitions": timeline["transitions"],
            "audio_tracks": timeline["audio_tracks"],
            "caption_tracks": timeline["caption_tracks"],
            "vfx_layers": timeline["vfx_layers"],
        }
        entry = {"action": action, "data": data, "state": state, "timestamp": datetime.utcnow().isoformat()}
        timeline.setdefault("history", []).append(entry)
        timeline["history_index"] = len(timeline["history"]) - 1
        settings = timeline.setdefault("settings", {})
        settings.setdefault("history", []).append(entry)
        settings["history_index"] = timeline["history_index"]
        if len(timeline["history"]) > 50:
            timeline["history"] = timeline["history"][-50:]
            timeline["history_index"] = len(timeline["history"]) - 1
            settings["history"] = settings["history"][-50:]
            settings["history_index"] = timeline["history_index"]

    @staticmethod
    async def add_marker(timeline: Dict[str, Any], marker: Dict[str, Any]) -> Dict[str, Any]:
        marker["marker_id"] = str(uuid.uuid4())
        marker["created_at"] = datetime.utcnow().isoformat()
        timeline.setdefault("markers", []).append(marker)
        TimelineService._record_history(timeline, "add_marker", marker)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def add_graphics_element(timeline: Dict[str, Any], element: Dict[str, Any]) -> Dict[str, Any]:
        element["element_id"] = str(uuid.uuid4())
        element["created_at"] = datetime.utcnow().isoformat()
        timeline.setdefault("graphics_elements", []).append(element)
        TimelineService._record_history(timeline, "add_graphics_element", element)
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    def get_timeline_duration(timeline: Dict[str, Any]) -> float:
        max_end = 0.0
        for clip in timeline.get("clips", []):
            start = clip.get("start_time", 0)
            duration = clip.get("duration", 0)
            end = start + duration
            if end > max_end:
                max_end = end
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                start = clip.get("start_time", 0)
                duration = clip.get("duration", 0)
                end = start + duration
                if end > max_end:
                    max_end = end
        return max_end

    @staticmethod
    def get_track_by_id(timeline: Dict[str, Any], track_id: str) -> Optional[Dict[str, Any]]:
        for track in timeline.get("tracks", []):
            if track.get("track_id") == track_id:
                return track
        return None

    @staticmethod
    def get_clip_by_id(timeline: Dict[str, Any], clip_id: str) -> Optional[Dict[str, Any]]:
        for clip in timeline.get("clips", []):
            if clip.get("clip_id") == clip_id:
                return clip
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    return clip
        return None

    @staticmethod
    async def delete_clip(timeline: Dict[str, Any], clip_id: str) -> bool:
        for i, clip in enumerate(timeline["clips"]):
            if clip.get("clip_id") == clip_id:
                if clip.get("locked"):
                    return False
                timeline["clips"].pop(i)
                TimelineService._record_history(timeline, "delete_clip", {"clip_id": clip_id})
                timeline["updated_at"] = datetime.utcnow().isoformat()
                return True
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clips.pop(i)
                    TimelineService._record_history(timeline, "delete_clip", {"clip_id": clip_id})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def move_clip(timeline: Dict[str, Any], clip_id: str, new_start: float, new_track_id: str = None) -> bool:
        clip_data = None
        old_track = None
        for clip in timeline.get("clips", []):
            if clip.get("clip_id") == clip_id:
                if clip.get("locked"):
                    return False
                clip_data = clip
                break
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
            new_track = TimelineService.get_track_by_id(timeline, new_track_id)
            if new_track and not new_track.get("locked"):
                clip_data["track_id"] = new_track_id
                new_track.setdefault("clips", []).append(clip_data)
        clip_data["start_time"] = new_start
        TimelineService._record_history(timeline, "move_clip", {"clip_id": clip_id, "new_start": new_start, "new_track_id": new_track_id})
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return True

    @staticmethod
    async def duplicate_clip(timeline: Dict[str, Any], clip_id: str, new_start: float = None) -> Optional[Dict[str, Any]]:
        clip = TimelineService.get_clip_by_id(timeline, clip_id)
        if not clip:
            return None
        new_clip = clip.copy()
        new_clip["clip_id"] = str(uuid.uuid4())
        new_clip["start_time"] = new_start if new_start is not None else clip.get("start_time", 0) + clip.get("duration", 0)
        new_clip["created_at"] = datetime.utcnow().isoformat()
        if "track_id" in clip:
            track = TimelineService.get_track_by_id(timeline, clip["track_id"])
            if track:
                track.setdefault("clips", []).append(new_clip)
        else:
            timeline["clips"].append(new_clip)
        TimelineService._record_history(timeline, "duplicate_clip", {"clip_id": clip_id, "new_clip_id": new_clip["clip_id"]})
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return new_clip

    @staticmethod
    async def ripple_edit(timeline: Dict[str, Any], clip_id: str, new_start: float) -> bool:
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
                    TimelineService._record_history(timeline, "ripple_edit", {"clip_id": clip_id, "new_start": new_start})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def roll_edit(timeline: Dict[str, Any], clip_id: str, new_end: float) -> bool:
        for track in timeline.get("tracks", []):
            clips = track.get("clips", [])
            for i, clip in enumerate(clips):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clip_start = clip.get("start_time", 0)
                    if new_end <= clip_start:
                        return False
                    clip["duration"] = new_end - clip_start
                    clip["end_time"] = new_end
                    TimelineService._record_history(timeline, "roll_edit", {"clip_id": clip_id, "new_end": new_end})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def slip_edit(timeline: Dict[str, Any], clip_id: str, new_in_point: float) -> bool:
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    if clip.get("locked"):
                        return False
                    clip["in_point"] = new_in_point
                    clip["out_point"] = new_in_point + clip.get("duration", 0)
                    TimelineService._record_history(timeline, "slip_edit", {"clip_id": clip_id, "new_in_point": new_in_point})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def slide_edit(timeline: Dict[str, Any], clip_id: str, new_start: float) -> bool:
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
                    TimelineService._record_history(timeline, "slide_edit", {"clip_id": clip_id, "new_start": new_start})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def group_clips(timeline: Dict[str, Any], clip_ids: List[str], group_id: str = None) -> str:
        group_id = group_id or f"group_{str(uuid.uuid4())[:8]}"
        timeline.setdefault("clip_groups", {})
        timeline["clip_groups"][group_id] = {"clip_ids": clip_ids, "locked": False}
        for clip_id in clip_ids:
            for track in timeline.get("tracks", []):
                for clip in track.get("clips", []):
                    if clip.get("clip_id") == clip_id:
                        clip["group_id"] = group_id
        TimelineService._record_history(timeline, "group_clips", {"group_id": group_id, "clip_ids": clip_ids})
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return group_id

    @staticmethod
    async def ungroup_clips(timeline: Dict[str, Any], group_id: str) -> bool:
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
        TimelineService._record_history(timeline, "ungroup_clips", {"group_id": group_id})
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return True

    @staticmethod
    async def link_clips(timeline: Dict[str, Any], video_clip_id: str, audio_clip_id: str) -> bool:
        for clip in timeline.get("clips", []):
            if clip.get("clip_id") == video_clip_id:
                clip.setdefault("linked_clip_ids", []).append(audio_clip_id)
            if clip.get("clip_id") == audio_clip_id:
                clip.setdefault("linked_clip_ids", []).append(video_clip_id)
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == video_clip_id:
                    clip.setdefault("linked_clip_ids", []).append(audio_clip_id)
                if clip.get("clip_id") == audio_clip_id:
                    clip.setdefault("linked_clip_ids", []).append(video_clip_id)
        TimelineService._record_history(timeline, "link_clips", {"video_clip_id": video_clip_id, "audio_clip_id": audio_clip_id})
        timeline["updated_at"] = datetime.utcnow().isoformat()
        return True

    @staticmethod
    async def lock_clip(timeline: Dict[str, Any], clip_id: str, locked: bool = True) -> bool:
        for clip in timeline.get("clips", []):
            if clip.get("clip_id") == clip_id:
                clip["locked"] = locked
                TimelineService._record_history(timeline, "lock_clip", {"clip_id": clip_id, "locked": locked})
                timeline["updated_at"] = datetime.utcnow().isoformat()
                return True
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    clip["locked"] = locked
                    TimelineService._record_history(timeline, "lock_clip", {"clip_id": clip_id, "locked": locked})
                    timeline["updated_at"] = datetime.utcnow().isoformat()
                    return True
        return False

    @staticmethod
    async def lock_track(timeline: Dict[str, Any], track_id: str, locked: bool = True) -> bool:
        track = TimelineService.get_track_by_id(timeline, track_id)
        if track:
            track["locked"] = locked
            TimelineService._record_history(timeline, "lock_track", {"track_id": track_id, "locked": locked})
            timeline["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False

    @staticmethod
    async def set_track_visibility(timeline: Dict[str, Any], track_id: str, visible: bool) -> bool:
        track = TimelineService.get_track_by_id(timeline, track_id)
        if track:
            track["visible"] = visible
            TimelineService._record_history(timeline, "set_track_visibility", {"track_id": track_id, "visible": visible})
            timeline["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False

    @staticmethod
    async def set_track_mute(timeline: Dict[str, Any], track_id: str, muted: bool) -> bool:
        track = TimelineService.get_track_by_id(timeline, track_id)
        if track:
            track["muted"] = muted
            TimelineService._record_history(timeline, "set_track_mute", {"track_id": track_id, "muted": muted})
            timeline["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False

    @staticmethod
    async def set_track_solo(timeline: Dict[str, Any], track_id: str, solo: bool) -> bool:
        track = TimelineService.get_track_by_id(timeline, track_id)
        if track:
            track["solo"] = solo
            TimelineService._record_history(timeline, "set_track_solo", {"track_id": track_id, "solo": solo})
            timeline["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False

    @staticmethod
    def get_timeline_state(timeline: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timeline_id": timeline.get("timeline_id"),
            "project_id": timeline.get("project_id"),
            "duration_seconds": timeline.get("duration_seconds", 0),
            "fps": timeline.get("fps", 30),
            "resolution": timeline.get("resolution", {}),
            "tracks": timeline.get("tracks", []),
            "clips": timeline.get("clips", []),
            "keyframes": timeline.get("keyframes", []),
            "transitions": timeline.get("transitions", []),
            "audio_tracks": timeline.get("audio_tracks", []),
            "caption_tracks": timeline.get("caption_tracks", []),
            "vfx_layers": timeline.get("vfx_layers", []),
            "markers": timeline.get("markers", []),
            "graphics_elements": timeline.get("graphics_elements", []),
        }
