import re
from typing import Optional, List, Dict, Any
from app.schemas.director import IntentExtraction


class IntentAnalyzer:
    CONTENT_TYPES = {
        "commercial": ["commercial", "ad", "advertisement", "product", "brand", "promotion", "ad for", "advert"],
        "cinematic": ["cinematic", "film", "movie", "scene", "short", "cinematography"],
        "social": ["social", "tiktok", "reel", "short", "viral", "story", "instagram post"],
        "music_video": ["music", "mv", "video", "music video"],
        "explainer": ["explainer", "tutorial", "how to", "guide", "demonstrate", "demonstration"],
        "trailer": ["trailer", "teaser", "promo", "promotional"],
        "ugc": ["ugc", "user generated", "authentic", "natural", "organic"],
        "documentary": ["documentary", "real", "interview", "footage", "documentary style"],
        "storytelling": ["story", "narrative", "tale", "journey"],
    }

    TONE_KEYWORDS = {
        "premium": ["luxury", "premium", "elegant", "sophisticated", "high-end", "luxurious", "upscale"],
        "energetic": ["fun", "energetic", "vibrant", "playful", "exciting", "dynamic", "bold"],
        "professional": ["professional", "corporate", "business", "formal", "enterprise"],
        "dramatic": ["dramatic", "intense", "dark", "moody", "epic", "powerful"],
        "calm": ["calm", "peaceful", "serene", "relaxing", "soothing", "tranquil"],
        "inspiring": ["inspiring", "motivational", "uplifting", "hopeful"],
        "humorous": ["funny", "humorous", "comedy", "comedic", "witty"],
        "nostalgic": ["nostalgic", "retro", "vintage", "classic", "throwback"],
    }

    STYLE_KEYWORDS = {
        "cinematic": ["cinematic", "film", "movie-like", "filmic"],
        "minimalist": ["minimalist", "clean", "simple", "minimal"],
        "vintage": ["vintage", "retro", "old-school", "nostalgic"],
        "futuristic": ["futuristic", "sci-fi", "cyberpunk", "futuristic", "tech"],
        "documentary": ["documentary", "realistic", "raw", "authentic"],
        "animation": ["animated", "animation", "cartoon", "motion graphics"],
        "editorial": ["editorial", "magazine", "fashion", "high-fashion"],
        "street": ["street", "urban", "grunge", "streetwear"],
    }

    PLATFORM_KEYWORDS = {
        "youtube": ["youtube", "yt"],
        "instagram": ["instagram", "ig", "reel", "instagram reel"],
        "tiktok": ["tiktok", "tk", "tiktok video"],
        "twitter": ["twitter", "x", "tweet"],
        "linkedin": ["linkedin"],
        "facebook": ["facebook", "fb"],
        "vimeo": ["vimeo"],
    }

    AUDIO_KEYWORDS = {
        "voiceover": ["voiceover", "voice over", "narrator", "narrated", "narration"],
        "music": ["music", "soundtrack", "score", "bgm", "background music"],
        "sfx": ["sound effect", "sfx", "sound effects"],
        "ambient": ["ambient", "ambience", "atmosphere"],
        "dialogue": ["dialogue", "conversation", "speaking", "talking"],
    }

    CTA_KEYWORDS = [
        "buy now", "shop now", "learn more", "sign up", "subscribe", "download",
        "visit", "check out", "get started", "try now", "join now", "contact us"
    ]

    def analyze(self, prompt: str, references: List[str], preferences: Dict[str, Any]) -> IntentExtraction:
        prompt_lower = prompt.lower()
        references = references or []

        content_type = self._detect_content_type(prompt_lower)
        tone = self._detect_tone(prompt_lower)
        style = self._detect_style(prompt_lower)
        platform = self._detect_platform(prompt_lower, preferences)
        duration = self._extract_duration(prompt)
        aspect_ratio = self._extract_aspect_ratio(prompt_lower, platform, preferences)
        resolution = preferences.get("resolution", "1080p")
        subject = self._extract_subject(prompt_lower)
        audience = self._extract_audience(prompt_lower)
        characters = self._extract_characters(prompt_lower)
        products = self._extract_products(prompt_lower)
        locations = self._extract_locations(prompt)
        audio = self._extract_audio(prompt_lower)
        voiceover = "voiceover" in audio or "voice over" in audio
        music = "music" in audio
        captions = self._detect_captions(prompt_lower)
        cta = self._extract_cta(prompt_lower)

        return IntentExtraction(
            objective=prompt[:200],
            content_type=content_type,
            subject=subject,
            audience=audience,
            tone=tone,
            style=style,
            story=prompt,
            total_duration_seconds=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            platform=platform,
            references=references,
            characters=characters,
            products=products,
            locations=locations,
            audio=audio,
            voiceover=voiceover,
            music=music,
            captions=captions,
            cta=cta,
        )

    def _detect_content_type(self, prompt: str) -> str:
        for ctype, keywords in self.CONTENT_TYPES.items():
            if any(kw in prompt for kw in keywords):
                return ctype
        return "cinematic"

    def _detect_tone(self, prompt: str) -> str:
        for tone, keywords in self.TONE_KEYWORDS.items():
            if any(kw in prompt for kw in keywords):
                return tone
        return "professional"

    def _detect_style(self, prompt: str) -> Optional[str]:
        for style, keywords in self.STYLE_KEYWORDS.items():
            if any(kw in prompt for kw in keywords):
                return style
        return None

    def _detect_platform(self, prompt: str, preferences: Dict[str, Any]) -> Optional[str]:
        platform = preferences.get("platform")
        if platform:
            return platform.lower()
        for platform, keywords in self.PLATFORM_KEYWORDS.items():
            if any(kw in prompt for kw in keywords):
                return platform
        return None

    def _extract_duration(self, prompt: str) -> int:
        match = re.search(r'(\d+)\s*(?:second|sec|s)\b', prompt, re.IGNORECASE)
        if match:
            duration = int(match.group(1))
            if duration < 5:
                return 5
            if duration > 120:
                return 120
            return duration
        return 30

    def _extract_aspect_ratio(self, prompt: str, platform: Optional[str], preferences: Dict[str, Any]) -> str:
        aspect = preferences.get("aspect_ratio")
        if aspect:
            return aspect

        if "vertical" in prompt or "9:16" in prompt or platform in ["tiktok", "instagram"]:
            return "9:16"
        if "square" in prompt or "1:1" in prompt or platform == "instagram":
            return "1:1"
        if "wide" in prompt or "16:9" in prompt or platform == "youtube":
            return "16:9"
        return "16:9"

    def _extract_subject(self, prompt: str) -> Optional[str]:
        subjects = [
            "watch", "product", "person", "car", "dog", "cat", "building", "city",
            "nature", "food", "shoe", "phone", "laptop", "dress", "jewelry", "watch",
            "camera", "drone", "house", "apartment", "beach", "mountain", "forest"
        ]
        for subj in subjects:
            if subj in prompt:
                return subj
        return None

    def _extract_audience(self, prompt: str) -> Optional[str]:
        audiences = {
            "consumer": ["consumer", "mass market", "everyday", "general public"],
            "business": ["business", "enterprise", "b2b", "corporate"],
            "young adults": ["young", "gen z", "millennial", "teen", "youth"],
            "adults": ["adult", "mature"],
            "luxury": ["luxury", "high-end", "premium", "upscale"],
        }
        for aud, keywords in audiences.items():
            if any(kw in prompt for kw in keywords):
                return aud
        return None

    def _extract_characters(self, prompt: str) -> List[str]:
        characters = []
        if re.search(r'\b(person|people|man|woman|actor|model|character|guy|girl|kid|child)\b', prompt, re.IGNORECASE):
            characters.append("person")
        return characters

    def _extract_products(self, prompt: str) -> List[str]:
        products = []
        if re.search(r'\b(watch|shoe|phone|laptop|car|product|dress|jewelry|camera|drone|bag|perfume)\b', prompt, re.IGNORECASE):
            products.append("product")
        return products

    def _extract_locations(self, prompt: str) -> List[str]:
        locations = []
        location_patterns = [
            r'\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b(city|beach|forest|desert|office|store|home|studio|street|rooftop|park|restaurant|showroom|mall)\b',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, prompt)
            locations.extend(matches)
        return list(dict.fromkeys(locations))[:5]

    def _extract_audio(self, prompt: str) -> Dict[str, Any]:
        audio = {}
        for audio_type, keywords in self.AUDIO_KEYWORDS.items():
            if any(kw in prompt for kw in keywords):
                audio[audio_type] = True
        return audio

    def _detect_captions(self, prompt: str) -> bool:
        return bool(re.search(r'\b(caption|subtitle|text overlay|on-screen text)\b', prompt, re.IGNORECASE))

    def _extract_cta(self, prompt: str) -> Optional[str]:
        for cta in self.CTA_KEYWORDS:
            if cta in prompt.lower():
                return cta
        return None
