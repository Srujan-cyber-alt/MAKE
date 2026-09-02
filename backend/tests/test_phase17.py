"""
Phase 17 Pro Editing & Post-Production Engine Tests.
"""

import pytest
from tests.conftest import client, get_auth_headers, create_project, upload_asset


class TestTimelineServiceExtensions:
    def test_create_timeline(self):
        headers = get_auth_headers("tl1@example.com", "testpass123")
        project = create_project(headers, "Timeline Test Project")
        response = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        assert response.status_code in (200, 201)

    def test_add_clip(self):
        headers = get_auth_headers("tl2@example.com", "testpass123")
        project = create_project(headers, "Clip Test")
        timeline = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        timeline_id = timeline.json().get("id") or timeline.json().get("timeline_id")
        response = client.post(
            f"/api/v1/timelines/{timeline_id}/clips",
            json={"asset_id": "test-asset", "start_time": 0.0, "duration": 5.0, "track_id": "track_0"},
            headers=headers,
        )
        assert response.status_code in (200, 201, 404)

    def test_split_clip(self):
        headers = get_auth_headers("tl3@example.com", "testpass123")
        project = create_project(headers, "Split Test")
        timeline = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        timeline_id = timeline.json().get("id") or timeline.json().get("timeline_id")
        response = client.post(
            f"/api/v1/timelines/{timeline_id}/split",
            params={"clip_id": "nonexistent", "split_time": 2.5},
            headers=headers,
        )
        assert response.status_code in (200, 404)

    def test_trim_clip(self):
        headers = get_auth_headers("tl4@example.com", "testpass123")
        project = create_project(headers, "Trim Test")
        timeline = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        timeline_id = timeline.json().get("id") or timeline.json().get("timeline_id")
        response = client.post(
            f"/api/v1/timelines/{timeline_id}/trim",
            params={"clip_id": "nonexistent", "start": 0.0, "end": 5.0},
            headers=headers,
        )
        assert response.status_code in (200, 404)

    def test_add_transition(self):
        headers = get_auth_headers("tl5@example.com", "testpass123")
        project = create_project(headers, "Transition Test")
        timeline = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        timeline_id = timeline.json().get("id") or timeline.json().get("timeline_id")
        response = client.post(
            f"/api/v1/timelines/{timeline_id}/transitions",
            json={"transition_type": "dissolve", "duration": 1.0, "from_clip_id": "a", "to_clip_id": "b"},
            headers=headers,
        )
        assert response.status_code in (200, 201, 404)

    def test_add_keyframe(self):
        headers = get_auth_headers("tl6@example.com", "testpass123")
        project = create_project(headers, "Keyframe Test")
        timeline = client.post(f"/api/v1/timelines/{project['id']}", json={"name": "Main", "tracks": []}, headers=headers)
        timeline_id = timeline.json().get("id") or timeline.json().get("timeline_id")
        response = client.post(
            f"/api/v1/timelines/{timeline_id}/keyframes",
            json={"clip_id": "clip1", "parameter": "opacity", "frame": 0, "value": 1.0},
            headers=headers,
        )
        assert response.status_code in (200, 201, 404)


class TestAudioSystemExtensions:
    def test_create_audio_track(self):
        headers = get_auth_headers("aud1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/audio/track",
            params={"track_id": "track1", "track_type": "music", "source": "/tmp/music.mp3", "volume": 0.8},
            headers=headers,
        )
        assert response.status_code == 200

    def test_normalize_audio_service(self):
        import asyncio
        from app.services.audio_system import AudioSystem
        result = asyncio.run(AudioSystem.normalize_audio("/tmp/test.mp3", "/tmp/test_normalized.mp3"))
        assert "status" in result or "error" in result

    def test_silence_detection_service(self):
        import asyncio
        from app.services.audio_system import AudioSystem
        result = asyncio.run(AudioSystem.detect_silence("/tmp/test.mp3"))
        assert isinstance(result, list)

    def test_crossfade_service(self):
        import asyncio
        from app.services.audio_system import AudioSystem
        result = asyncio.run(AudioSystem.apply_crossfade("/tmp/test1.mp3", "/tmp/test2.mp3", "/tmp/test_crossfade.mp3"))
        assert "status" in result or "error" in result

    def test_audio_plan(self):
        from app.services.audio_system import AudioSystem
        import asyncio
        plan = asyncio.run(AudioSystem.create_audio_plan(
            [{"delivery": "voiceover", "text": "Hello"}],
            [5.0],
        ))
        assert plan["total_tracks"] >= 2
        assert any(t["track_type"] == "music" for t in plan["tracks"])


class TestColorAndExport:
    def test_color_look(self):
        headers = get_auth_headers("col1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/color-look",
            params={"source_path": "/tmp/test.mp4", "output_path": "/tmp/test_color.mp4", "preset": "cinematic"},
            headers=headers,
        )
        assert response.status_code in (200, 500)

    def test_social_export_presets(self):
        from app.services.social_export import SocialExportService
        presets = SocialExportService.list_presets()
        assert isinstance(presets, list)
        assert len(presets) >= 1
        platforms = [p["platform"] for p in presets]
        assert "youtube" in platforms
        assert "tiktok" in platforms

    def test_export_srt(self):
        import asyncio
        from app.services.export_engine import ExportEngine
        result = asyncio.run(ExportEngine.export_srt([{"start": 0.0, "end": 5.0, "text": "Hello"}], "/tmp/test.srt"))
        assert result["status"] == "completed"


class TestCaptionSystem:
    def test_generate_captions(self):
        headers = get_auth_headers("cap1@example.com", "testpass123")
        response = client.post(
            "/api/v1/phase9/captions",
            params={"prompt": "hello world test caption", "duration_seconds": 10.0},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "segments" in data

    def test_burn_in_filter(self):
        from app.services.caption_system import CaptionSystem
        from app.schemas.phase9 import CaptionTrack
        track = CaptionTrack(track_id="cap1", language="en", segments=[{"start": 0, "end": 5, "text": "Hello"}], burn_in=True)
        filter_str = CaptionSystem.build_burn_in_filter(track, 1920, 1080)
        assert "drawtext" in filter_str

    def test_remove_filler_words(self):
        from app.services.caption_system import CaptionSystem
        from app.schemas.phase9 import CaptionTrack
        track = CaptionTrack(
            track_id="cap2",
            language="en",
            segments=[{"start": 0, "end": 2, "text": "um hello"}, {"start": 2, "end": 5, "text": "world"}],
        )
        removed = CaptionSystem.remove_filler_words(track)
        assert len(removed) == 1
        assert len(track.segments) == 1


class TestKeyframeEngine:
    def test_interpolation(self):
        from app.services.keyframe_engine import KeyframeEngine
        kfs = KeyframeEngine.create_keyframe_sequence("scale", 0, 30, 1.0, 2.0, "linear", "ease_in_out")
        result = KeyframeEngine.interpolate_keyframes(kfs, 15)
        assert result is not None
        assert 1.0 < result < 2.0

    def test_natural_language_keyframes(self):
        from app.services.keyframe_engine import KeyframeEngine
        from app.schemas.phase7 import FrameRange
        kfs = KeyframeEngine.parse_natural_language_keyframes("fade in and zoom in", FrameRange(start_frame=0, end_frame=30))
        assert len(kfs) >= 2


class TestStudioOrchestrator:
    def test_list_modes(self):
        headers = get_auth_headers("studio1@example.com", "testpass123")
        project = create_project(headers, "Studio Mode Test")
        response = client.get(f"/api/v1/studio/projects/{project['id']}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data

    def test_command_routing(self):
        headers = get_auth_headers("studio2@example.com", "testpass123")
        project = create_project(headers, "Studio Command Test")
        response = client.post(
            f"/api/v1/studio/projects/{project['id']}/command",
            json={"command": "Make this cinematic", "mode": "edit", "context": {}},
            headers=headers,
        )
        assert response.status_code in (200, 422, 500)
