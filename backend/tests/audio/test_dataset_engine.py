"""Tests for Dataset Engine."""
import numpy as np
import json
import wave
import struct
import pytest
from app.make_model.audio.dataset_engine import DatasetEngine, DatasetItem, DatasetSplit, LicenseType


class TestDatasetEngine:
    def test_engine_creation(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        assert engine.dataset_dir.exists()

    def test_compute_sha256(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        path = str(tmp_path / "test.wav")
        test_data = b"test audio data"
        with open(path, "wb") as f:
            f.write(test_data)
        sha = engine.compute_sha256(path)
        assert len(sha) == 64
        assert isinstance(sha, str)

    def test_get_wav_info(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        path = str(tmp_path / "test.wav")
        sr = 16000
        duration_samples = sr * 2
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(struct.pack("<" + "h" * duration_samples, *np.zeros(duration_samples, dtype=np.int16)))
        retrieved_sr, channels, duration = engine.get_wav_info(path)
        assert retrieved_sr == sr
        assert channels == 1
        assert abs(duration - 2.0) < 0.1

    def test_compute_quality_score_valid(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        path = str(tmp_path / "test.wav")
        sr = 16000
        n = sr * 2
        samples = np.random.RandomState(42).normal(0, 0.3, n).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(struct.pack("<" + "h" * n, *samples))
        score = engine.compute_quality_score(path, sr, 1, 2.0)
        assert 0.0 < score <= 1.0

    def test_ingest_local_dataset(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        for i in range(3):
            path = str(tmp_path / f"sample_{i}.wav")
            n = sr
            samples = np.random.RandomState(i).normal(0, 0.2, n).astype(np.int16)
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(struct.pack("<" + "h" * n, *samples))
        license_info = {
            "license": "public_domain",
            "attribution": "test creator",
            "source": "test_dataset",
            "language": "en",
        }
        items = engine.ingest_local(license_info)
        assert len(items) == 3
        for item in items:
            assert item.sha256 is not None
            assert item.duration > 0
            assert item.sample_rate == sr
            assert item.channels == 1
            assert item.quality_score > 0
            assert item.license == LicenseType.PUBLIC_DOMAIN

    def test_ingest_deduplication(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        n = sr
        samples = np.random.RandomState(42).normal(0, 0.2, n).astype(np.int16)
        for i in range(2):
            path = str(tmp_path / f"sample_{i}.wav")
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(struct.pack("<" + "h" * n, *samples))
        license_info = {"license": "public_domain", "source": "test"}
        items = engine.ingest_local(license_info)
        assert len(items) == 1

    def test_assign_splits(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        for i in range(10):
            path = str(tmp_path / f"sample_{i}.wav")
            n = sr
            samples = np.random.RandomState(i).normal(0, 0.2, n).astype(np.int16)
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(struct.pack("<" + "h" * n, *samples))
        license_info = {"license": "public_domain", "source": "test"}
        engine.ingest_local(license_info)
        splits = engine.assign_splits(seed=42)
        assert len(splits.train) + len(splits.validation) + len(splits.test) == 10
        assert len(splits.train) > 0

    def test_save_and_load_manifest(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        n = sr
        samples = np.random.RandomState(42).normal(0, 0.2, n).astype(np.int16)
        path = str(tmp_path / "test.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(struct.pack("<" + "h" * n, *samples))
        license_info = {"license": "cc0", "source": "test", "language": "en"}
        items = engine.ingest_local(license_info)
        engine.assign_splits(seed=42)
        engine.save_manifest()
        engine2 = DatasetEngine(str(tmp_path))
        assert engine2.load_manifest()
        assert len(engine2.items) == len(items)
        assert len(engine2.splits.train) == len(engine.splits.train)

    def test_normalize_audio(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        n = sr
        samples = np.random.RandomState(42).normal(0, 0.3, n).astype(np.int16)
        path = str(tmp_path / "test.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(struct.pack("<" + "h" * n, *samples))
        result = engine.normalize_audio(path, target_sr=16000)
        assert result is not None
        assert result.dtype == np.float32
        assert len(result) > 0

    def test_get_training_batch(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        sr = 16000
        for i in range(10):
            path = str(tmp_path / f"sample_{i}.wav")
            n = sr
            samples = np.random.RandomState(i).normal(0, 0.2, n).astype(np.int16)
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(struct.pack("<" + "h" * n, *samples))
        license_info = {"license": "public_domain", "source": "test"}
        engine.ingest_local(license_info)
        engine.assign_splits(seed=42)
        batch = engine.get_training_batch("train", batch_size=4)
        assert len(batch) <= 4
        assert len(batch) > 0

    def test_reject_corrupted_file(self, tmp_path):
        engine = DatasetEngine(str(tmp_path))
        path = str(tmp_path / "corrupt.wav")
        with open(path, "wb") as f:
            f.write(b"not a wav file")
        license_info = {"license": "public_domain", "source": "test"}
        items = engine.ingest_local(license_info)
        assert len(items) == 0
