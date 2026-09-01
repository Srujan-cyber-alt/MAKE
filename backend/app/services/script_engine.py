"""
AI Story + Script Engine for MAKE AI Video.

Generates:
- hooks
- scripts
- dialogue
- narration
- scene descriptions
- shot descriptions
- CTAs
- alternate endings

Supports:
- commercial
- social media
- music video
- short film
- product demo
- UGC
- cinematic trailer
- documentary
- explainer
- fashion
- automotive
- real estate
- gaming
- sports
- education
"""

from typing import Optional, List, Dict, Any
from app.services.creative_director import Genre, Tone, CreativeBrief
import uuid
import logging

logger = logging.getLogger(__name__)


class ScriptEngine:
    @staticmethod
    def generate_script(
        creative_plan: Dict[str, Any],
        genre: Genre,
        tone: Tone,
        duration_seconds: int = 30,
    ) -> Dict[str, Any]:
        script_id = str(uuid.uuid4())
        concept = creative_plan.get("concept", {})
        scenes = creative_plan.get("story_structure", [])
        
        hook = ScriptEngine._generate_hook(concept, genre, tone)
        script_segments = ScriptEngine._generate_script_segments(scenes, genre, tone)
        dialogue = ScriptEngine._generate_dialogue(genre, tone)
        narration = ScriptEngine._generate_narration(concept, genre, tone)
        cta = concept.get("cta") or ScriptEngine._generate_cta(genre)
        alternate_endings = ScriptEngine._generate_alternate_endings(genre, tone)
        
        return {
            "script_id": script_id,
            "title": concept.get("title", "Untitled"),
            "hook": hook,
            "segments": script_segments,
            "dialogue": dialogue,
            "narration": narration,
            "cta": cta,
            "alternate_endings": alternate_endings,
            "word_count": sum(len(s.get("text", "").split()) for s in script_segments),
            "estimated_duration_seconds": duration_seconds,
        }

    @staticmethod
    def _generate_hook(concept: Dict[str, Any], genre: Genre, tone: Tone) -> str:
        if genre == Genre.COMMERCIAL:
            return f"Introducing {concept.get('title', 'something new')} — the future of innovation."
        elif genre == Genre.SOCIAL_MEDIA:
            return f"Wait for it... {concept.get('title', 'you need to see this')}."
        elif genre == Genre.FASHION:
            return f"This season, {concept.get('title', 'style')} redefines elegance."
        return f"Discover {concept.get('title', 'the extraordinary')}."

    @staticmethod
    def _generate_script_segments(scenes: List[Dict[str, Any]], genre: Genre, tone: Tone) -> List[Dict[str, Any]]:
        segments = []
        for scene in scenes:
            segment = {
                "scene_id": scene.get("scene_id"),
                "scene_name": scene.get("name"),
                "text": ScriptEngine._generate_scene_text(scene, genre, tone),
                "duration_seconds": scene.get("duration_seconds", 5),
                "delivery": ScriptEngine._get_delivery_style(genre, tone),
            }
            segments.append(segment)
        return segments

    @staticmethod
    def _generate_scene_text(scene: Dict[str, Any], genre: Genre, tone: Tone) -> str:
        scene_type = scene.get("name", "").lower()
        if "hook" in scene_type:
            return "The moment you've been waiting for."
        elif "reveal" in scene_type:
            return "Introducing the next evolution."
        elif "cta" in scene_type or "call" in scene_type:
            return "Get yours today."
        return scene.get("description", "")

    @staticmethod
    def _get_delivery_style(genre: Genre, tone: Tone) -> str:
        if tone == Tone.LUXURY:
            return "confident, slow, authoritative"
        elif tone == Tone.PLAYFUL:
            return "energetic, upbeat, friendly"
        elif tone == Tone.DRAMATIC:
            return "intense, deliberate, powerful"
        return "neutral, professional"

    @staticmethod
    def _generate_dialogue(genre: Genre, tone: Tone) -> List[Dict[str, Any]]:
        return [
            {
                "character": "Narrator",
                "line": "Welcome to the future.",
                "emotion": "inspired",
            }
        ]

    @staticmethod
    def _generate_narration(concept: Dict[str, Any], genre: Genre, tone: Tone) -> str:
        return f"Experience {concept.get('title', 'something new')} like never before."

    @staticmethod
    def _generate_cta(genre: Genre) -> str:
        if genre == Genre.COMMERCIAL:
            return "Order now at example.com"
        elif genre == Genre.SOCIAL_MEDIA:
            return "Follow for more"
        return "Learn more"

    @staticmethod
    def _generate_alternate_endings(genre: Genre, tone: Tone) -> List[Dict[str, Any]]:
        return [
            {
                "ending_id": str(uuid.uuid4()),
                "description": "Fade to black with logo",
                "duration_seconds": 3,
            },
            {
                "ending_id": str(uuid.uuid4()),
                "description": "End on product close-up",
                "duration_seconds": 2,
            },
        ]
