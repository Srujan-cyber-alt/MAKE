"""
CPU optimization utilities for audio processing.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import multiprocessing as mp

from app.make_model.audio.architecture import AudioConfig


class CPUOptimizer:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config
        self._cpu_count = max(1, mp.cpu_count() - 1)
        self._available_memory_mb = self._get_available_memory()

    def _get_available_memory(self) -> int:
        try:
            import psutil
            return int(psutil.virtual_memory().available / 1024 / 1024)
        except ImportError:
            return 4096

    def get_recommended_batch_size(self, sample_rate: int, duration_seconds: float) -> int:
        bytes_per_second = sample_rate * 2 * 2
        total_bytes = bytes_per_second * duration_seconds
        available_bytes = self._available_memory_mb * 1024 * 1024
        max_batch = max(1, available_bytes // (total_bytes * 4))
        return min(max_batch, self._cpu_count * 2)

    def get_recommended_threads(self) -> int:
        return self._cpu_count

    def optimize_config(self, config: AudioConfig) -> AudioConfig:
        config.training["batch_size"] = min(
            config.training.get("batch_size", 4),
            self.get_recommended_batch_size(config.sample_rate, config.max_duration_seconds),
        )
        config.inference["device"] = "cpu"
        return config

    def get_profile(self) -> Dict[str, Any]:
        return {
            "cpu_count": self._cpu_count,
            "available_memory_mb": self._available_memory_mb,
            "recommended_batch_size": self.get_recommended_batch_size(16000, 5.0),
            "recommended_threads": self.get_recommended_threads(),
        }
