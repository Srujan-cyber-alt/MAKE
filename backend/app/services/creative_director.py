"""
Autonomous Creative Director 2.0 for MAKE AI Video.

Reasons over:
- objective
- audience
- platform
- genre
- tone
- pacing
- narrative
- visual language
- character requirements
- product requirements
- location requirements
- camera language
- lighting
- color
- motion
- sound
- CTA
- brand requirements
- duration
- aspect ratio

Creates:
- creative concept
- story structure
- scene structure
- shot structure
- visual references
- character bible
- product bible
- location bible
- camera bible
- lighting bible
- audio bible
- continuity bible
- export plan

Adds creative quality scoring before generation.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class Genre(str, Enum):
    COMMERCIAL = "commercial"
    SOCIAL_MEDIA = "social_media"
    MUSIC_VIDEO = "music_video"
    SHORT_FILM = "short_film"
    PRODUCT_DEMO = "product_demo"
    UGC = "ugc"
    CINEMATIC_TRAILER = "cinematic_trailer"
    DOCUMENTARY = "documentary"
    EXPLAINER = "explainer"
    FASHION = "fashion"
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    GAMING = "gaming"
    SPORTS = "sports"
    EDUCATION = "education"


class Tone(str, Enum):
    CINEMATIC = "cinematic"
    MINIMAL = "minimal"
    BOLD = "bold"
    LUXURY = "luxury"
    PLAYFUL = "playful"
    DRAMATIC = "dramatic"
    EMOTIONAL = "emotional"
    ENERGETIC = "energetic"
    CORPORATE = "corporate"
    ARTISTIC = "artistic"


class ApprovalMode(str, Enum):
    AUTO = "auto"
    GUIDED = "guided"
    PRO = "pro"


@dataclass
class CreativeBrief:
    objective: str
    audience: Optional[str] = None
    platform: Optional[str] = None
    genre: Optional[Genre] = None
    tone: Optional[Tone] = None
    duration_seconds: int = 30
    aspect_ratio: str = "16:9"
    characters: List[Dict[str, Any]] = field(default_factory=list)
    products: List[Dict[str, Any]] = field(default_factory=list)
    locations: List[Dict[str, Any]] = field(default_factory=list)
    brand_dna: Optional[Dict[str, Any]] = None
    reference_assets: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class CreativeConcept:
    concept_id: str
    title: str
    logline: str
    narrative_arc: str
    visual_language: str
    emotional_arc: str
    cta: Optional[str] = None
    quality_score: float = 0.0


@dataclass
class SceneStructure:
    scene_id: str
    sequence_number: int
    name: str
    description: str
    duration_seconds: float
    shots: List[Dict[str, Any]] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    location: Optional[str] = None
    lighting: Optional[str] = None
    mood: Optional[str] = None


@dataclass
class ShotStructure:
    shot_id: str
    scene_id: str
    sequence_number: int
    shot_type: str
    description: str
    duration_seconds: float
    camera: Optional[Dict[str, Any]] = None
    motion: Optional[Dict[str, Any]] = None
    lighting: Optional[str] = None
    vfx: List[str] = field(default_factory=list)
    audio: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@dataclass
class Bible:
    bible_id: str
    type: str
    name: str
    content: Dict[str, Any]
    reference_assets: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


class CreativeDirector:
    @staticmethod
    def create_creative_director(brief: CreativeBrief, approval_mode: ApprovalMode = ApprovalMode.GUIDED) -> Dict[str, Any]:
        logger.info(f"Creating creative director plan for objective: {brief.objective}")
        
        concept = CreativeDirector._generate_concept(brief)
        story_structure = CreativeDirector._generate_story_structure(brief, concept)
        shot_structure = CreativeDirector._generate_shot_structure(story_structure, brief)
        
        character_bibles = CreativeDirector._build_character_bibles(brief)
        product_bibles = CreativeDirector._build_product_bibles(brief)
        location_bibles = CreativeDirector._build_location_bibles(brief)
        camera_bibles = CreativeDirector._build_camera_bibles(shot_structure)
        lighting_bibles = CreativeDirector._build_lighting_bibles(story_structure)
        audio_bibles = CreativeDirector._build_audio_bibles(story_structure, brief)
        continuity_bible = CreativeDirector._build_continuity_bible(story_structure, character_bibles, product_bibles, location_bibles)
        export_plan = CreativeDirector._build_export_plan(brief)
        
        creative_quality = CreativeDirector._score_creative_quality(
            concept=concept,
            story_structure=story_structure,
            shot_structure=shot_structure,
            brief=brief,
        )
        
        return {
            "concept": concept.__dict__,
            "story_structure": [s.__dict__ for s in story_structure],
            "shot_structure": [s.__dict__ for s in shot_structure],
            "bibles": {
                "characters": [c.__dict__ for c in character_bibles],
                "products": [p.__dict__ for p in product_bibles],
                "locations": [l.__dict__ for l in location_bibles],
                "camera": [c.__dict__ for c in camera_bibles],
                "lighting": [l.__dict__ for l in lighting_bibles],
                "audio": [a.__dict__ for a in audio_bibles],
                "continuity": continuity_bible.__dict__,
            },
            "export_plan": export_plan,
            "creative_quality": creative_quality,
            "approval_mode": approval_mode.value,
            "total_shots": len(shot_structure),
            "estimated_duration": sum(s.duration_seconds for s in shot_structure),
            "needs_clarification": CreativeDirector._needs_clarification(brief),
            "questions": CreativeDirector._generate_questions(brief) if approval_mode != ApprovalMode.AUTO else [],
        }

    @staticmethod
    def _generate_concept(brief: CreativeBrief) -> CreativeConcept:
        concept_id = str(uuid.uuid4())
        title = CreativeDirector._extract_title(brief.objective)
        logline = CreativeDirector._generate_logline(brief)
        narrative_arc = CreativeDirector._generate_narrative_arc(brief)
        visual_language = CreativeDirector._generate_visual_language(brief)
        emotional_arc = CreativeDirector._generate_emotional_arc(brief)
        cta = CreativeDirector._extract_cta(brief.objective)
        
        return CreativeConcept(
            concept_id=concept_id,
            title=title,
            logline=logline,
            narrative_arc=narrative_arc,
            visual_language=visual_language,
            emotional_arc=emotional_arc,
            cta=cta,
        )

    @staticmethod
    def _generate_story_structure(brief: CreativeBrief, concept: CreativeConcept) -> List[SceneStructure]:
        scenes = []
        num_scenes = max(1, min(5, brief.duration_seconds // 10))
        
        scene_names = CreativeDirector._get_scene_names(brief.genre, num_scenes)
        scene_descriptions = CreativeDirector._get_scene_descriptions(brief, num_scenes)
        
        for i in range(num_scenes):
            scene = SceneStructure(
                scene_id=str(uuid.uuid4()),
                sequence_number=i + 1,
                name=scene_names[i] if i < len(scene_names) else f"Scene {i + 1}",
                description=scene_descriptions[i] if i < len(scene_descriptions) else "",
                duration_seconds=brief.duration_seconds / num_scenes,
            )
            scenes.append(scene)
        
        return scenes

    @staticmethod
    def _generate_shot_structure(story_structure: List[SceneStructure], brief: CreativeBrief) -> List[ShotStructure]:
        shots = []
        shot_sequence = 0
        
        for scene in story_structure:
            num_shots = max(1, min(8, int(scene.duration_seconds / 3)))
            shot_types = CreativeDirector._get_shot_types(brief.genre, num_shots)
            
            for i in range(num_shots):
                shot_sequence += 1
                shot = ShotStructure(
                    shot_id=str(uuid.uuid4()),
                    scene_id=scene.scene_id,
                    sequence_number=shot_sequence,
                    shot_type=shot_types[i] if i < len(shot_types) else "medium",
                    description=CreativeDirector._generate_shot_description(scene, i, num_shots),
                    duration_seconds=scene.duration_seconds / num_shots,
                    camera=CreativeDirector._generate_camera_direction(brief, i, num_shots),
                    motion=CreativeDirector._generate_motion_direction(brief, i, num_shots),
                    lighting=CreativeDirector._generate_lighting_description(brief),
                )
                shots.append(shot)
        
        return shots

    @staticmethod
    def _build_character_bibles(brief: CreativeBrief) -> List[Bible]:
        bibles = []
        for char_data in brief.characters:
            bible = Bible(
                bible_id=str(uuid.uuid4()),
                type="character",
                name=char_data.get("name", "Character"),
                content={
                    "appearance": char_data.get("appearance", {}),
                    "personality": char_data.get("personality", ""),
                    "voice": char_data.get("voice", ""),
                    "movement": char_data.get("movement", {}),
                    "constraints": ["identity must be preserved", "face must remain consistent"],
                },
                reference_assets=char_data.get("reference_images", []),
            )
            bibles.append(bible)
        return bibles

    @staticmethod
    def _build_product_bibles(brief: CreativeBrief) -> List[Bible]:
        bibles = []
        for prod_data in brief.products:
            bible = Bible(
                bible_id=str(uuid.uuid4()),
                type="product",
                name=prod_data.get("name", "Product"),
                content={
                    "geometry": prod_data.get("shape", {}),
                    "dimensions": prod_data.get("dimensions", {}),
                    "materials": prod_data.get("materials", []),
                    "colors": prod_data.get("colors", {}),
                    "logos": prod_data.get("logos", []),
                    "constraints": ["product geometry must remain identical", "logo must be preserved", "colors must match"],
                },
                reference_assets=prod_data.get("reference_images", []),
            )
            bibles.append(bible)
        return bibles

    @staticmethod
    def _build_location_bibles(brief: CreativeBrief) -> List[Bible]:
        bibles = []
        for loc_data in brief.locations:
            bible = Bible(
                bible_id=str(uuid.uuid4()),
                type="location",
                name=loc_data.get("name", "Location"),
                content={
                    "architecture": loc_data.get("architecture", ""),
                    "geography": loc_data.get("geography", ""),
                    "lighting": loc_data.get("lighting", ""),
                    "weather": loc_data.get("weather", ""),
                    "time": loc_data.get("time", ""),
                    "colors": loc_data.get("colors", {}),
                    "materials": loc_data.get("materials", []),
                    "props": loc_data.get("props", []),
                    "atmosphere": loc_data.get("atmosphere", ""),
                    "spatial_relationships": loc_data.get("spatial_relationships", {}),
                    "constraints": ["lighting must remain consistent", "architecture must match", "atmosphere must be preserved"],
                },
                reference_assets=loc_data.get("reference_images", []),
            )
            bibles.append(bible)
        return bibles

    @staticmethod
    def _build_camera_bibles(shots: List[ShotStructure]) -> List[Bible]:
        bibles = []
        camera_plan = []
        for shot in shots:
            if shot.camera:
                camera_plan.append({
                    "shot_id": shot.shot_id,
                    "camera": shot.camera,
                    "duration": shot.duration_seconds,
                })
        bible = Bible(
            bible_id=str(uuid.uuid4()),
            type="camera",
            name="Camera Plan",
            content={"camera_moves": camera_plan, "style": "cinematic"},
        )
        bibles.append(bible)
        return bibles

    @staticmethod
    def _build_lighting_bibles(scenes: List[SceneStructure]) -> List[Bible]:
        bibles = []
        lighting_plan = []
        for scene in scenes:
            lighting_plan.append({
                "scene_id": scene.scene_id,
                "lighting": scene.lighting or "cinematic",
                "mood": scene.mood or "neutral",
            })
        bible = Bible(
            bible_id=str(uuid.uuid4()),
            type="lighting",
            name="Lighting Plan",
            content={"lighting_plan": lighting_plan},
        )
        bibles.append(bible)
        return bibles

    @staticmethod
    def _build_audio_bibles(scenes: List[SceneStructure], brief: CreativeBrief) -> List[Bible]:
        bibles = []
        audio_plan = []
        for scene in scenes:
            audio_plan.append({
                "scene_id": scene.scene_id,
                "audio": "music + ambient",
                "ducking": True,
            })
        bible = Bible(
            bible_id=str(uuid.uuid4()),
            type="audio",
            name="Audio Plan",
            content={"audio_plan": audio_plan, "voiceover": brief.objective},
        )
        bibles.append(bible)
        return bibles

    @staticmethod
    def _build_continuity_bible(scenes: List[SceneStructure], characters: List[Bible], products: List[Bible], locations: List[Bible]) -> Bible:
        return Bible(
            bible_id=str(uuid.uuid4()),
            type="continuity",
            name="Continuity Bible",
            content={
                "scenes": [s.scene_id for s in scenes],
                "characters": [c.bible_id for c in characters],
                "products": [p.bible_id for p in products],
                "locations": [l.bible_id for l in locations],
                "rules": [
                    "Character appearance must be consistent across scenes",
                    "Product appearance must be consistent across scenes",
                    "Location lighting must match time of day",
                    "Camera movement must be motivated",
                ],
            },
        )

    @staticmethod
    def _build_export_plan(brief: CreativeBrief) -> Dict[str, Any]:
        return {
            "platform": brief.platform or "youtube",
            "aspect_ratio": brief.aspect_ratio,
            "duration_seconds": brief.duration_seconds,
            "fps": 30,
            "codec": "h264",
            "bitrate": "8M",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
        }

    @staticmethod
    def _score_creative_quality(concept: CreativeConcept, story_structure: List[SceneStructure], shot_structure: List[ShotStructure], brief: CreativeBrief) -> Dict[str, Any]:
        score = 0.0
        dimensions = {}
        
        if concept.title and concept.logline:
            dimensions["concept_clarity"] = 0.9
            score += 0.9
        else:
            dimensions["concept_clarity"] = 0.3
            score += 0.3
        
        if len(story_structure) >= 2:
            dimensions["story_structure"] = 0.8
            score += 0.8
        else:
            dimensions["story_structure"] = 0.4
            score += 0.4
        
        if len(shot_structure) >= 3:
            dimensions["shot_diversity"] = 0.7
            score += 0.7
        else:
            dimensions["shot_diversity"] = 0.3
            score += 0.3
        
        if brief.characters or brief.products:
            dimensions["asset_integration"] = 0.8
            score += 0.8
        else:
            dimensions["asset_integration"] = 0.5
            score += 0.5
        
        dimensions["pacing"] = 0.7
        score += 0.7
        
        dimensions["platform_fit"] = 0.8 if brief.platform else 0.5
        score += dimensions["platform_fit"]
        
        score = score / len(dimensions)
        
        return {
            "overall": min(1.0, score),
            "dimensions": dimensions,
            "passed": score >= 0.7,
        }

    @staticmethod
    def _needs_clarification(brief: CreativeBrief) -> bool:
        if not brief.objective:
            return True
        if not brief.characters and not brief.products and not brief.locations:
            return False
        return False

    @staticmethod
    def _generate_questions(brief: CreativeBrief) -> List[str]:
        questions = []
        if not brief.genre:
            questions.append("What genre/style are you aiming for?")
        if not brief.tone:
            questions.append("What tone should the video have?")
        if not brief.audience:
            questions.append("Who is the target audience?")
        if not brief.platform:
            questions.append("Which platform will this be published on?")
        return questions

    @staticmethod
    def _extract_title(objective: str) -> str:
        words = objective.split()
        return " ".join(words[:8]) + ("..." if len(words) > 8 else "")

    @staticmethod
    def _generate_logline(brief: CreativeBrief) -> str:
        return f"A {brief.tone.value if brief.tone else 'compelling'} {brief.genre.value if brief.genre else 'video'} that {brief.objective.lower()}"

    @staticmethod
    def _generate_narrative_arc(brief: CreativeBrief) -> str:
        return "hook -> build -> climax -> resolution -> CTA"

    @staticmethod
    def _generate_visual_language(brief: CreativeBrief) -> str:
        if brief.tone == Tone.LUXURY:
            return "minimal, high-contrast, premium lighting, slow camera"
        elif brief.tone == Tone.CINEMATIC:
            return "anamorphic, deep shadows, dramatic lighting, slow push-in"
        elif brief.tone == Tone.BOLD:
            return "high saturation, dynamic angles, fast cuts, neon accents"
        return "clean, modern, professional"

    @staticmethod
    def _generate_emotional_arc(brief: CreativeBrief) -> str:
        return "curiosity -> desire -> action -> satisfaction"

    @staticmethod
    def _extract_cta(objective: str) -> Optional[str]:
        cta_keywords = ["buy", "shop", "learn more", "sign up", "download", "visit", "try"]
        for keyword in cta_keywords:
            if keyword in objective.lower():
                return keyword
        return "Learn More"

    @staticmethod
    def _get_scene_names(genre: Optional[Genre], num_scenes: int) -> List[str]:
        if genre == Genre.COMMERCIAL:
            return ["Hook", "Product Reveal", "Demonstration", "Lifestyle", "CTA"]
        elif genre == Genre.FASHION:
            return ["Opening", "Runway", "Detail", "Movement", "Finale"]
        elif genre == Genre.AUTOMOTIVE:
            return ["Exterior", "Interior", "Performance", "Lifestyle", "Reveal"]
        return [f"Scene {i + 1}" for i in range(num_scenes)]

    @staticmethod
    def _get_scene_descriptions(brief: CreativeBrief, num_scenes: int) -> List[str]:
        descriptions = []
        for i in range(num_scenes):
            descriptions.append(f"Scene {i + 1}: {brief.objective}")
        return descriptions

    @staticmethod
    def _get_shot_types(genre: Optional[Genre], num_shots: int) -> List[str]:
        shot_types = ["wide", "medium", "close-up", "detail", "overhead", "low-angle", "dutch", "tracking"]
        return shot_types[:num_shots] if num_shots <= len(shot_types) else shot_types + ["medium"] * (num_shots - len(shot_types))

    @staticmethod
    def _generate_shot_description(scene: SceneStructure, shot_index: int, total_shots: int) -> str:
        return f"{scene.name} - Shot {shot_index + 1}"

    @staticmethod
    def _generate_camera_direction(brief: CreativeBrief, shot_index: int, total_shots: int) -> Optional[Dict[str, Any]]:
        if shot_index == 0:
            return {"movement": "static", "shot_type": "wide"}
        elif shot_index == total_shots - 1:
            return {"movement": "push-in", "shot_type": "close-up"}
        return {"movement": "tracking", "shot_type": "medium"}

    @staticmethod
    def _generate_motion_direction(brief: CreativeBrief, shot_index: int, total_shots: int) -> Optional[Dict[str, Any]]:
        return {"action": "walk", "intensity": 0.7}

    @staticmethod
    def _generate_lighting_description(brief: CreativeBrief) -> str:
        if brief.tone == Tone.LUXURY:
            return "dramatic high-key with rim light"
        elif brief.tone == Tone.CINEMATIC:
            return "low-key cinematic with motivated sources"
        return "soft diffused key light"
