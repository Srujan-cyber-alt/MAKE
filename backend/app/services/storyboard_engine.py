"""
Storyboard Engine for MAKE AI Video.

Generates visual storyboards with:
- scene thumbnails
- shot thumbnails
- camera direction
- character positions
- subject positions
- camera movement
- duration
- transition
- dialogue
- audio
- VFX
- notes

Supports regeneration of:
- entire storyboard
- one scene
- one shot
"""

from typing import Optional, List, Dict, Any
from app.services.creative_director import CreativeDirector, CreativeBrief, SceneStructure, ShotStructure
from app.services.previsualization_engine import PrevisualizationEngine
import uuid
import logging

logger = logging.getLogger(__name__)


class StoryboardEngine:
    @staticmethod
    def generate_storyboard(
        creative_plan: Dict[str, Any],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        storyboard_id = str(uuid.uuid4())
        scenes = creative_plan.get("story_structure", [])
        shots = creative_plan.get("shot_structure", [])
        
        storyboard_scenes = []
        for scene_data in scenes:
            scene_shots = [s for s in shots if s.get("scene_id") == scene_data.get("scene_id")]
            thumbnail = PrevisualizationEngine.generate_scene_thumbnail(scene_data, scene_shots)
            
            storyboard_scenes.append({
                "scene_id": scene_data.get("scene_id"),
                "sequence_number": scene_data.get("sequence_number"),
                "name": scene_data.get("name"),
                "description": scene_data.get("description"),
                "duration_seconds": scene_data.get("duration_seconds"),
                "thumbnail": thumbnail,
                "shots": [
                    {
                        "shot_id": shot.get("shot_id"),
                        "sequence_number": shot.get("sequence_number"),
                        "shot_type": shot.get("shot_type"),
                        "description": shot.get("description"),
                        "duration_seconds": shot.get("duration_seconds"),
                        "camera": shot.get("camera"),
                        "motion": shot.get("motion"),
                        "lighting": shot.get("lighting"),
                        "vfx": shot.get("vfx", []),
                        "audio": shot.get("audio"),
                        "notes": shot.get("notes"),
                        "thumbnail": PrevisualizationEngine.generate_shot_thumbnail(shot),
                    }
                    for shot in scene_shots
                ],
                "characters": scene_data.get("characters", []),
                "products": scene_data.get("products", []),
                "location": scene_data.get("location"),
                "lighting": scene_data.get("lighting"),
                "mood": scene_data.get("mood"),
                "transition": "cut" if scene_data.get("sequence_number", 0) < len(scenes) else "fade",
            })
        
        return {
            "storyboard_id": storyboard_id,
            "project_id": project_id,
            "title": creative_plan.get("concept", {}).get("title", "Storyboard"),
            "total_scenes": len(storyboard_scenes),
            "total_shots": len(shots),
            "total_duration": sum(s.get("duration_seconds", 0) for s in scenes),
            "scenes": storyboard_scenes,
            "export_formats": ["pdf", "json", "image_sequence"],
        }

    @staticmethod
    def regenerate_scene(storyboard: Dict[str, Any], scene_id: str, new_scene_data: Dict[str, Any]) -> Dict[str, Any]:
        scenes = storyboard.get("scenes", [])
        for i, scene in enumerate(scenes):
            if scene.get("scene_id") == scene_id:
                scenes[i] = {**scene, **new_scene_data}
                break
        storyboard["scenes"] = scenes
        return storyboard

    @staticmethod
    def regenerate_shot(storyboard: Dict[str, Any], shot_id: str, new_shot_data: Dict[str, Any]) -> Dict[str, Any]:
        for scene in storyboard.get("scenes", []):
            shots = scene.get("shots", [])
            for i, shot in enumerate(shots):
                if shot.get("shot_id") == shot_id:
                    shots[i] = {**shot, **new_shot_data}
                    scene["shots"] = shots
                    return storyboard
        return storyboard

    @staticmethod
    def regenerate_storyboard(creative_plan: Dict[str, Any], project_id: Optional[str] = None) -> Dict[str, Any]:
        return StoryboardEngine.generate_storyboard(creative_plan, project_id)
