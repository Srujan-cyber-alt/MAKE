"""Tests for dataset engine and manifest."""

import hashlib
import json
import os

import pytest

from app.make_model.audio.dataset_engine import DatasetEngine, LicenseType, ALLOWED_LICENSES
from app.make_model.audio.manifest import DatasetManifest, DatasetEntry


class TestDatasetEngine:
    def test_ingest(self, tmp_path):
        engine = DatasetEngine(str(tmp_path / "ds.json"))
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        manifest = engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.CC0)
        assert manifest.dataset_id == "ds1"
        assert manifest.license == LicenseType.CC0

    def test_manifest_persistence(self, tmp_path):
        path = str(tmp_path / "ds.json")
        engine = DatasetEngine(path)
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.CC0)
        engine2 = DatasetEngine(path)
        assert engine2.get_manifest("ds1") is not None

    def test_verify_integrity(self, tmp_path):
        engine = DatasetEngine(str(tmp_path / "ds.json"))
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.CC0)
        report = engine.verify_integrity("ds1")
        assert report["status"] == "ok"

    def test_check_license(self, tmp_path):
        engine = DatasetEngine(str(tmp_path / "ds.json"))
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.CC_BY)
        report = engine.check_license("ds1")
        assert report["license"] == "CC-BY"
        assert report["allowed"] is True

    def test_list_datasets(self, tmp_path):
        engine = DatasetEngine(str(tmp_path / "ds.json"))
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.CC0)
        assert engine.list_datasets() == ["ds1"]

    def test_unknown_license_rejected(self, tmp_path):
        engine = DatasetEngine(str(tmp_path / "ds.json"))
        data_file = tmp_path / "data.wav"
        data_file.write_bytes(b"audio-data")
        with pytest.raises(ValueError):
            engine.ingest("ds1", "Dataset 1", [str(data_file)], LicenseType.UNKNOWN)


class TestManifest:
    def test_add_entry(self):
        manifest = DatasetManifest(dataset_id="ds1", name="Dataset 1", license=LicenseType.CC0)
        entry = DatasetEntry(path="file.wav", size_bytes=100, content_hash="abc")
        manifest.add_entry(entry)
        assert manifest.num_entries == 1
        assert manifest.total_size_bytes == 100

    def test_remove_entry(self):
        manifest = DatasetManifest(dataset_id="ds1", name="Dataset 1", license=LicenseType.CC0)
        manifest.add_entry(DatasetEntry(path="file.wav", size_bytes=100))
        assert manifest.remove_entry("file.wav") is True
        assert manifest.num_entries == 0

    def test_to_dict_roundtrip(self):
        manifest = DatasetManifest(dataset_id="ds1", name="Dataset 1", license=LicenseType.CC0)
        manifest.add_entry(DatasetEntry(path="file.wav", size_bytes=100, content_hash="abc"))
        data = manifest.to_dict()
        restored = DatasetManifest.from_dict(data)
        assert restored.dataset_id == "ds1"
        assert restored.num_entries == 1

    def test_sha256_entry(self):
        entry = DatasetEntry(path="file.wav", size_bytes=100, content_hash=hashlib.sha256(b"test").hexdigest())
        assert len(entry.content_hash) == 64