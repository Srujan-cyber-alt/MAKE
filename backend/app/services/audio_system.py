"""
Advanced Audio Director for MAKE AI Video Phase 17.

Supports:
- voiceover
- dialogue
- music
- ambient
- Foley
- SFX
- transitions
- ducking
- loudness normalization
- timing synchronization
- audio mixing
- crossfade
- audio cleanup architecture
"""

from typing import Optional, List, Dict, Any
from app.schemas.phase9 import AudioTrack
from app.services.video_processing import video_processing_service
import asyncio
import logging

logger = logging.getLogger(__name__)


class AudioSystem:
    @staticmethod
    async def create_track(
        track_id: str,
        track_type: str,
        source: Optional[str] = None,
        volume: float = 1.0,
        fade_in: Optional[float] = None,
        fade_out: Optional[float] = None,
        ducking: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> AudioTrack:
        return AudioTrack(
            track_id=track_id,
            track_type=track_type,
            source=source,
            volume=volume,
            fade_in=fade_in,
            fade_out=fade_out,
            ducking=ducking,
            parameters=parameters or {},
        )

    @staticmethod
    async def create_audio_plan(script_segments: List[Dict[str, Any]], shot_durations: List[float]) -> Dict[str, Any]:
        tracks = []
        current_time = 0.0
        
        for i, segment in enumerate(script_segments):
            duration = shot_durations[i] if i < len(shot_durations) else 5.0
            
            if segment.get("delivery") and "voiceover" in segment.get("delivery", ""):
                tracks.append({
                    "track_type": "voiceover",
                    "start_time": current_time,
                    "duration_seconds": duration,
                    "text": segment.get("text", ""),
                    "fade_in": 0.5,
                    "fade_out": 0.5,
                    "volume": 1.0,
                })
            elif segment.get("dialogue"):
                tracks.append({
                    "track_type": "dialogue",
                    "start_time": current_time,
                    "duration_seconds": duration,
                    "text": segment.get("dialogue", [{}])[0].get("line", ""),
                    "character": segment.get("dialogue", [{}])[0].get("character", "Narrator"),
                    "fade_in": 0.2,
                    "fade_out": 0.2,
                    "volume": 1.0,
                })
            
            current_time += duration
        
        music_track = {
            "track_type": "music",
            "start_time": 0.0,
            "duration_seconds": sum(shot_durations),
            "fade_in": 2.0,
            "fade_out": 3.0,
            "volume": 0.6,
            "ducking": True,
            "duck_trigger": "dialogue",
        }
        tracks.append(music_track)
        
        ambient_track = {
            "track_type": "ambient",
            "start_time": 0.0,
            "duration_seconds": sum(shot_durations),
            "volume": 0.4,
        }
        tracks.append(ambient_track)
        
        return {
            "audio_plan_id": str(__import__("uuid").uuid4()),
            "total_tracks": len(tracks),
            "tracks": tracks,
            "timeline_aligned": True,
            "ducking_enabled": True,
        }

    @staticmethod
    async def mix_tracks(tracks: List[AudioTrack], output_path: str) -> Dict[str, Any]:
        if not tracks:
            return {"error": "No tracks provided"}

        if not video_processing_service._check_ffmpeg():
            return {"error": "ffmpeg not available"}

        inputs = []
        filter_parts = []
        for i, track in enumerate(tracks):
            if track.source:
                inputs.extend(["-i", track.source])
            volume = track.volume if not track.ducking else track.volume * 0.3
            fade_in = f"afade=t=in:st=0:d={track.fade_in}" if track.fade_in else ""
            fade_out = f"afade=t=out:st={track.duration_seconds - track.fade_out}:d={track.fade_out}" if track.fade_out and track.duration_seconds else ""
            vol = f"volume={volume}"
            parts = [p for p in [vol, fade_in, fade_out] if p]
            filter_parts.append(f"[{i}:a]{','.join(parts)}[a{i}]")

        mix_inputs = "".join([f"[a{i}]" for i in range(len(tracks))])
        mix_filter = f"{mix_inputs}amix=inputs={len(tracks)}:duration=longest:dropout_transition=3[out]"
        full_filter = ";".join(filter_parts) + ";" + mix_filter if filter_parts else mix_filter

        cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", full_filter, "-map", "[out]", "-c:a", "aac", "-b:a", "192k", output_path]
        try:
            await video_processing_service._run_ffmpeg(cmd, output_path)
            return {
                "output_path": output_path,
                "tracks_mixed": len(tracks),
                "status": "completed",
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    @staticmethod
    async def apply_ducking(tracks: List[AudioTrack], trigger_track_id: str) -> List[AudioTrack]:
        result = []
        for track in tracks:
            if track.track_id == trigger_track_id:
                track.ducking = False
                track.volume = 1.0
            else:
                track.ducking = True
                track.volume = 0.3
            result.append(track)
        return result

    @staticmethod
    async def normalize_audio(source_path: str, output_path: str) -> Dict[str, Any]:
        if not video_processing_service._check_ffmpeg():
            return {"error": "ffmpeg not available"}
        try:
            cmd = [
                "ffmpeg", "-y", "-i", source_path,
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:a", "aac", "-b:a", "192k", output_path,
            ]
            await video_processing_service._run_ffmpeg(cmd, output_path)
            return {"output_path": output_path, "status": "completed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    @staticmethod
    async def align_audio_to_shots(audio_plan: Dict[str, Any], shot_boundaries: List[float]) -> Dict[str, Any]:
        aligned_tracks = []
        for track in audio_plan.get("tracks", []):
            aligned_track = dict(track)
            current_start = 0.0
            for boundary in shot_boundaries:
                if track.get("start_time", 0) < boundary:
                    aligned_track["shot_boundary"] = boundary
                    aligned_track["aligned_start"] = current_start
                    break
                current_start = boundary
            aligned_tracks.append(aligned_track)
        return {"aligned_tracks": aligned_tracks, "total_aligned": len(aligned_tracks)}

    @staticmethod
    async def synchronize_event_sound(events: List[Dict[str, Any]], audio_tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
        synchronized = []
        for event in events:
            event_time = event.get("time", 0)
            event_type = event.get("type", "impact")
            matching_track = {
                "event_time": event_time,
                "event_type": event_type,
                "sound_type": AudioSystem._match_sound_type(event_type),
                "volume": 0.8,
                "fade_in": 0.05,
                "fade_out": 0.1,
            }
            synchronized.append(matching_track)
        return {"synchronized_events": synchronized, "total_events": len(synchronized)}

    @staticmethod
    def _match_sound_type(event_type: str) -> str:
        sound_map = {
            "impact": "impact_heavy",
            "footstep": "footstep",
            "door": "door_close",
            "glass": "glass_break",
            "car": "car_pass",
            "rain": "rain_ambient",
            "explosion": "explosion",
            "whoosh": "whoosh",
        }
        return sound_map.get(event_type, "generic_impact")

    @staticmethod
    async def detect_silence(audio_path: str, threshold_db: float = -50.0, min_duration: float = 0.5) -> List[Dict[str, float]]:
        if not video_processing_service._check_ffmpeg():
            return []
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                silence_file = f.name
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-af", f"silencedetect=n={threshold_db}dB:d={min_duration}",
                "-f", "null", "-"
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            stderr_text = stderr.decode()
            silences = []
            lines = stderr_text.splitlines()
            for i, line in enumerate(lines):
                if "silence_start:" in line:
                    start = float(line.split("silence_start:")[1].strip())
                    end_line = lines[i + 1] if i + 1 < len(lines) else ""
                    if "silence_end:" in end_line:
                        end = float(end_line.split("silence_end:")[1].split()[0])
                        silences.append({"start": start, "end": end, "duration": end - start})
            return silences
        except Exception:
            return []

    @staticmethod
    async def apply_crossfade(audio_path1: str, audio_path2: str, output_path: str, crossfade_duration: float = 1.0) -> Dict[str, Any]:
        if not video_processing_service._check_ffmpeg():
            return {"error": "ffmpeg not available"}
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path1, "-i", audio_path2,
                "-filter_complex", f"[0:a][1:a]acrossfade=d={crossfade_duration}:c1=tri:c2=tri[out]",
                "-map", "[out]", "-c:a", "aac", "-b:a", "192k", output_path,
            ]
            await video_processing_service._run_ffmpeg(cmd, output_path)
            return {"output_path": output_path, "status": "completed"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
