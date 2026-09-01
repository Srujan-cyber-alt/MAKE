from app.schemas.director import IntentExtraction, ExportRequirement


class ExportPlanner:
    FPS_MAP = {
        "tiktok": 30,
        "instagram": 30,
        "youtube": 60,
        "youtube_shorts": 60,
        "twitter": 30,
        "linkedin": 30,
        "facebook": 30,
        "vimeo": 24,
    }

    def plan_export(self, intent: IntentExtraction) -> ExportRequirement:
        fps = self.FPS_MAP.get(intent.platform, 24)

        return ExportRequirement(
            id="export-1",
            aspect_ratio=intent.aspect_ratio,
            resolution=intent.resolution,
            fps=fps,
            format="mp4",
            platform=intent.platform,
            duration_seconds=float(intent.total_duration_seconds),
        )
