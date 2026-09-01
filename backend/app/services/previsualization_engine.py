"""
Previsualization Engine for MAKE AI Video.

Generates visual representations of:
- scene thumbnails
- shot thumbnails
- camera direction
- character positions
- subject positions
- camera movement

Uses available rendering backends.
"""

from typing import Optional, Dict, Any, List
import base64
import logging

logger = logging.getLogger(__name__)


class PrevisualizationEngine:
    @staticmethod
    def generate_scene_thumbnail(scene_data: Dict[str, Any], shots: List[Dict[str, Any]]) -> Optional[str]:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (640, 360), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except Exception:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            y = 20
            draw.text((20, y), scene_data.get("name", "Scene"), fill=(255, 255, 255), font=font)
            y += 40
            draw.text((20, y), scene_data.get("description", "")[:60], fill=(180, 180, 180), font=small_font)
            y += 25
            draw.text((20, y), f"Duration: {scene_data.get('duration_seconds', 0)}s", fill=(150, 150, 150), font=small_font)
            y += 25
            draw.text((20, y), f"Shots: {len(shots)}", fill=(150, 150, 150), font=small_font)
            
            for i, shot in enumerate(shots[:3]):
                y += 30
                draw.text((20, y), f"Shot {shot.get('sequence_number', i+1)}: {shot.get('shot_type', 'medium')}", fill=(120, 180, 255), font=small_font)
                y += 20
                cam = shot.get("camera") or {}
                draw.text((40, y), f"Camera: {cam.get('movement', 'static')}", fill=(100, 100, 100), font=small_font)
            
            import io
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.warning(f"Scene thumbnail generation failed: {e}")
            return None

    @staticmethod
    def generate_shot_thumbnail(shot_data: Dict[str, Any]) -> Optional[str]:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (320, 180), color=(40, 40, 40))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except Exception:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            draw.text((10, 10), shot_data.get("shot_type", "medium"), fill=(255, 255, 255), font=font)
            draw.text((10, 40), shot_data.get("description", "")[:40], fill=(180, 180, 180), font=small_font)
            
            cam = shot_data.get("camera") or {}
            draw.text((10, 65), f"Camera: {cam.get('movement', 'static')}", fill=(150, 150, 150), font=small_font)
            draw.text((10, 85), f"Duration: {shot_data.get('duration_seconds', 0)}s", fill=(150, 150, 150), font=small_font)
            
            motion = shot_data.get("motion") or {}
            if motion:
                draw.text((10, 105), f"Motion: {motion.get('action', 'none')}", fill=(120, 180, 255), font=small_font)
            
            lighting = shot_data.get("lighting") or ""
            if lighting:
                draw.text((10, 125), f"Lighting: {lighting[:30]}", fill=(255, 200, 100), font=small_font)
            
            import io
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.warning(f"Shot thumbnail generation failed: {e}")
            return None

    @staticmethod
    def generate_storyboard_image_sequence(storyboard: Dict[str, Any]) -> List[str]:
        images = []
        for scene in storyboard.get("scenes", []):
            thumbnail = scene.get("thumbnail")
            if thumbnail:
                images.append(thumbnail)
            for shot in scene.get("shots", []):
                shot_thumb = shot.get("thumbnail")
                if shot_thumb:
                    images.append(shot_thumb)
        return images
