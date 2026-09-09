#!/usr/bin/env python3
"""
MAKE Audio V2 Performance Benchmarks.

Measures actual CPU-first performance for all engines.
No third-party AI APIs used.
"""

from __future__ import annotations

import json
import time
import tempfile
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from app.make_model.audio.tiny_model import TinyAudioModel, train_step
from app.make_model.audio.config_loader import get_default_config
from app.make_model.audio.voice import VoiceGenomeEngine
from app.make_model.audio.emotion import EmotionEngine
from app.make_model.audio.dialogue import DialogueEngine
from app.make_model.audio.foley import FoleyEngine
from app.make_model.audio.music import MusicIntelligence
from app.make_model.audio.soundscape import SoundscapeEngine
from app.make_model.audio.spatial import SpatialAudioDirector
from app.make_model.audio.acoustics import RoomAcousticsEngine
from app.make_model.audio.enhancement import AudioEnhancementEngine
from app.make_model.audio.repair import AudioRepairEngine
from app.make_model.audio.editing import AudioEditingEngine
from app.make_model.audio.quality import AudioQualityEvaluator
from app.make_model.audio.audio_forensics import AudioForensics
from app.make_model.audio.source_separator import SourceSeparator, SeparationMethod
from app.make_model.audio.quantizer import Quantizer, QuantizeDtype


@dataclass
class BenchmarkResult:
    engine: str
    operation: str
    latency_ms: float
    memory_mb: float
    input_size: int
    output_size: int
    status: str = "success"
    error: Optional[str] = None


def _make_wav(path: str, sr: int = 16000, duration: float = 2.0, freq: float = 220.0):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * freq * t)
    wavfile.write(path, sr, (audio * 32767).astype(np.int16))


async def run_benchmarks() -> List[BenchmarkResult]:
    results: List[BenchmarkResult] = []
    config = get_default_config("tiny")
    tmpdir = tempfile.mkdtemp()

    # Tiny Model forward
    model = TinyAudioModel(config, seed=42)
    t0 = time.perf_counter()
    params = model.forward("benchmark test", "v1", "neutral")
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("tiny_model", "forward", latency, 0.0, 0, 0))

    # Tiny Model training step
    t0 = time.perf_counter()
    loss = train_step(model, ["training"], [0.1], lr=1e-4)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("tiny_model", "train_step", latency, 0.0, 0, 0))

    # Voice synthesis
    voice = VoiceGenomeEngine()
    await voice.initialize(config)
    t0 = time.perf_counter()
    result = await voice.synthesize("benchmark", "v1", "neutral")
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("voice", "synthesize", latency, 0.0, 0, result.duration_seconds))

    # Emotion apply
    emotion = EmotionEngine()
    await emotion.initialize(config)
    wav_path = str(Path(tmpdir) / "input.wav")
    _make_wav(wav_path)
    t0 = time.perf_counter()
    result = await emotion.apply_emotion(wav_path, "happy", 0.8)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("emotion", "apply", latency, 0.0, 0, result.duration_seconds))

    # Foley generation
    foley = FoleyEngine()
    await foley.initialize(config)
    t0 = time.perf_counter()
    result = await foley.generate_foley("footstep", 0.5, {"material": "wood"})
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("foley", "generate", latency, 0.0, 0, result.duration_seconds))

    # Soundscape
    soundscape = SoundscapeEngine()
    await soundscape.initialize(config)
    t0 = time.perf_counter()
    result = await soundscape.generate_soundscape("wind", 10.0, {"intensity": 0.5})
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("soundscape", "generate", latency, 0.0, 0, result.duration_seconds))

    # Music
    music = MusicIntelligence()
    await music.initialize(config)
    t0 = time.perf_counter()
    result = await music.generate_music("ambient pad", 10.0, "ambient")
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("music", "generate", latency, 0.0, 0, result.duration_seconds))

    # Spatial
    spatial = SpatialAudioDirector()
    await spatial.initialize(config)
    t0 = time.perf_counter()
    result = await spatial.spatialize(wav_path, {"x": 5.0, "y": 3.0, "z": 0.0})
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("spatial", "spatialize", latency, 0.0, 0, result.duration_seconds))

    # Enhancement
    enhancement = AudioEnhancementEngine()
    await enhancement.initialize(config)
    t0 = time.perf_counter()
    result = await enhancement.enhance(wav_path, {})
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("enhancement", "enhance", latency, 0.0, 0, result.duration_seconds))

    # Repair (noise)
    repair = AudioRepairEngine()
    await repair.initialize(config)
    t0 = time.perf_counter()
    result = await repair.remove_noise(wav_path)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("repair", "remove_noise", latency, 0.0, 0, result.duration_seconds))

    # Quality evaluation
    evaluator = AudioQualityEvaluator()
    t0 = time.perf_counter()
    report = await evaluator.evaluate(wav_path)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("quality", "evaluate", latency, 0.0, 0, report.overall_score))

    # Forensics
    t0 = time.perf_counter()
    report = AudioForensics.analyze(wav_path)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("forensics", "analyze", latency, 0.0, report.file_size_bytes, 0))

    # Source separation
    sep = SourceSeparator(method=SeparationMethod.SPECTRAL_SUBTRACTION)
    sr, data = wavfile.read(wav_path)
    audio = data.astype(np.float32) / 32768.0
    t0 = time.perf_counter()
    sources = sep.separate(audio, num_sources=2)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("separator", "separate", latency, 0.0, len(audio), sum(len(s) for s in sources)))

    # Quantization
    quantizer = Quantizer()
    sr, data = wavfile.read(wav_path)
    audio = data.astype(np.float32) / 32768.0
    t0 = time.perf_counter()
    quantized_result = quantizer.quantize(audio, QuantizeDtype.INT8)
    latency = (time.perf_counter() - t0) * 1000
    results.append(BenchmarkResult("quantizer", "quantize_int8", latency, 0.0, len(audio), quantized_result.quantized_size_bytes))

    import resource
    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results[0].memory_mb = mem_kb / 1024.0

    return results


def main():
    import asyncio
    results = asyncio.run(run_benchmarks())

    print("\n" + "=" * 60)
    print("MAKE Audio V2 Performance Benchmarks")
    print("=" * 60)
    print(f"{'Engine':<20} {'Operation':<20} {'Latency (ms)':>15} {'Status':>10}")
    print("-" * 60)
    for r in results:
        print(f"{r.engine:<20} {r.operation:<20} {r.latency_ms:>15.2f} {r.status:>10}")
    print("-" * 60)

    total_time = sum(r.latency_ms for r in results)
    print(f"\nTotal benchmark time: {total_time:.2f} ms")
    print(f"Memory (baseline): {results[0].memory_mb:.2f} MB")

    summary = {
        "timestamp": time.time(),
        "results": [asdict(r) for r in results],
        "total_latency_ms": total_time,
        "memory_mb": results[0].memory_mb,
        "note": "All measurements are CPU-only (numpy/scipy). No GPU or external API used.",
    }

    output_path = Path("benchmarks/audio_benchmarks_v2.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
