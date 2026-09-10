"""
Music intelligence - rhythm, harmony, melody, instrumentation, arrangement.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import MusicModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class MusicIntelligence(MusicModelInterface):
    model_type = "music"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
        self._genre_presets = {
            "ambient": {"tempo": 60, "key": "C", "scale": "major"},
            "electronic": {"tempo": 120, "key": "A", "scale": "minor"},
            "orchestral": {"tempo": 90, "key": "D", "scale": "major"},
            "jazz": {"tempo": 100, "key": "Bb", "scale": "blues"},
            "rock": {"tempo": 130, "key": "E", "scale": "minor"},
            "classical": {"tempo": 80, "key": "G", "scale": "major"},
        }
        self._model: Optional[TinyAudioModel] = None
        self._vocoder: Optional[TinyVocoder] = None

    async def initialize(self, config: AudioConfig) -> None:
        self.config = config
        self._model = TinyAudioModel(config, seed=config.training.get("seed", 42))
        self._vocoder = TinyVocoder(sample_rate=config.sample_rate)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            audio_path="",
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=request.seed,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"type": "music_placeholder"},
        )

    async def generate_music(self, prompt: str, duration: float, genre: str) -> GenerationResult:
        if genre not in self._genre_presets:
            genre = "ambient"
        preset = self._genre_presets[genre]
        if not self._model or not self._vocoder:
            raise RuntimeError("MusicIntelligence not initialized")
        params = self._model.forward(prompt, "music", genre)
        audio = self._vocoder.synthesize(params, duration)
        output_path = f"/tmp/music_{genre}_{int(time.time())}.wav"
        wavfile.write(output_path, self.config.sample_rate, (audio * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=duration,
            seed=None,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={
                "prompt": prompt,
                "genre": genre,
                "preset": preset,
                "type": "music_generation",
                "model": "tiny_numpy",
            },
        )

    async def arrange_music(self, stems: Dict[str, str], structure: Dict[str, Any]) -> GenerationResult:
        output_path = f"/tmp/music_arranged_{int(time.time())}.wav"
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"stems": list(stems.keys()), "structure": structure, "type": "music_arrangement"},
        )

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        import json
        from pathlib import Path
        data = self.get_provenance()
        data["checkpoint_type"] = "stateless_dsp"
        data["timestamp"] = time.time()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    async def load_checkpoint(self, path: str) -> None:
        import json
        from pathlib import Path
        if Path(path).exists():
            with open(path, "r") as f:
                _data = json.load(f)

    def get_provenance(self) -> Dict[str, Any]:
        return {"model_type": "music", "genres": list(self._genre_presets.keys())}
