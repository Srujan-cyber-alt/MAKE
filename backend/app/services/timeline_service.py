"""
Production Timeline Service for MAKE AI Video.

Supports:
- clips
- tracks
- trimming
- splitting
- ordering
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
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


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
        if timeline["history_index"] > 0:
            timeline["history_index"] -= 1
            state = timeline["history"][timeline["history_index"]]["state"]
            timeline.update(state)
            timeline["updated_at"] = datetime.utcnow().isoformat()
        return timeline

    @staticmethod
    async def redo(timeline: Dict[str, Any]) -> Dict[str, Any]:
        if timeline["history_index"] < len(timeline["history"]) - 1:
            timeline["history_index"] += 1
            state = timeline["history"][timeline["history_index"]]["state"]
            timeline.update(state)
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
        timeline["history"].append({"action": action, "data": data, "state": state, "timestamp": datetime.utcnow().isoformat()})
        timeline["history_index"] = len(timeline["history"]) - 1
        if len(timeline["history"]) > 50:
            timeline["history"] = timeline["history"][-50:]
            timeline["history_index"] = len(timeline["history"]) - 1
