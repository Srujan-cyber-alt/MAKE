"""
Tests for the MAKE proprietary model foundation.

Every test that requires torch + GPU + real weights SKIPS with an
explicit reason rather than PASS-without-evidence.

Test reality rule: tests may NEVER claim neural generation if they
are exercising stubs, random tensors, synthetic data, or FFmpeg.
"""

from __future__ import annotations
import json
import os
import shutil
import tempfile
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def tmp_root(tmp_path, monkeypatch):
    """Redirect MAKE_MODEL_ROOT to a temp directory for every test."""
    monkeypatch.setenv("MAKE_MODEL_ROOT", str(tmp_path))
    import app.make_model.registry as reg_mod
    reg_mod._REGISTRY = None
    yield tmp_path
    reg_mod._REGISTRY = None


def _has_torch() -> bool:
    try:
        import torch  # noqa
        return True
    except ImportError:
        return False


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class TestState:
    def test_states_defined(self):
        from app.make_model.state import ModelState, ALLOWED_TRANSITIONS
        for s in ("untrained", "architecture_defined", "dataset_prepared",
                  "training", "checkpoint_available", "inference_ready",
                  "production_ready", "failed"):
            assert ModelState(s).value == s
        assert ModelState.UNTRAINED in ALLOWED_TRANSITIONS

    def test_illegal_transition(self):
        from app.make_model.state import ModelState, validate_transition
        with pytest.raises(ValueError):
            validate_transition(ModelState.UNTRAINED, ModelState.PRODUCTION_READY)

    def test_legal_transition(self):
        from app.make_model.state import ModelState, validate_transition
        validate_transition(ModelState.UNTRAINED, ModelState.ARCHITECTURE_DEFINED)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_default_config(self):
        from app.make_model.arch import MakeModelConfig
        c = MakeModelConfig()
        assert c.latent_channels > 0
        assert c.ch > 0
        assert len(c.ch_mult) > 0

    def test_round_trip(self):
        from app.make_model.arch import MakeModelConfig
        c = MakeModelConfig(name="foo", ch=96)
        d = c.to_dict()
        d2 = MakeModelConfig.from_dict(d).to_dict()
        assert d == d2

    def test_param_count_estimate_positive(self):
        from app.make_model.arch import MakeModelConfig
        c = MakeModelConfig()
        assert c.param_count_estimate() > 0


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

class TestArchitecture:
    def test_create_model_no_torch(self, tmp_root):
        from app.make_model.arch import create_model, MakeModelConfig
        m = create_model(MakeModelConfig())
        assert m is not None

    def test_stub_reports_itself(self, tmp_root):
        if _has_torch():
            pytest.skip("REAL_NEURAL_MODEL_NOT_AVAILABLE: torch installed; will get real model")
        from app.make_model.arch import create_model, MakeModelConfig
        m = create_model(MakeModelConfig())
        assert getattr(m, "_is_stub", False) is True
        assert "STUB" in repr(m)

    def test_real_forward_shape(self, tmp_root):
        if not _has_torch():
            pytest.skip("REAL_NEURAL_MODEL_NOT_AVAILABLE: torch not installed")
        from app.make_model.arch import architecture_smoke_test, MakeModelConfig
        info = architecture_smoke_test(MakeModelConfig())
        assert info["ok"] is True
        assert info["match"] is True
        assert info["param_count"] > 0

    def test_list_arch_versions(self):
        from app.make_model.arch import list_arch_versions
        v = list_arch_versions()
        assert len(v) >= 1
        assert v[0]["status"] == "ARCHITECTURE_DEFINED"


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

class TestHardware:
    def test_detect_runs(self):
        from app.make_model.training import detect_hardware
        hw = detect_hardware()
        d = hw.to_dict()
        assert "cpu_cores" in d
        assert "ram_gb" in d
        assert "disk_free_gb" in d
        assert "pytorch_available" in d

    def test_block_reasons_listed(self, tmp_root):
        from app.make_model.training import detect_hardware
        hw = detect_hardware()
        if not _has_torch() or not hw.cuda_available:
            assert len(hw.block_reasons) > 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_empty_status(self, tmp_root):
        import os
        from app.make_model.registry import get_registry
        from app.make_model import utils
        print("\n[DEBUG] MAKE_MODEL_ROOT:", os.environ.get("MAKE_MODEL_ROOT"))
        print("[DEBUG] paths root:", utils.paths()["root"])
        print("[DEBUG] registry path:", utils.paths()["registry"])
        reg = get_registry()
        s = reg.get_status()
        print("[DEBUG] status:", s)
        assert s["overall_state"] == "untrained"
        assert s["checkpoint_count"] == 0
        assert s["model_count"] == 0

    def test_register_model(self, tmp_root):
        from app.make_model.registry import get_registry, ModelVersion
        reg = get_registry()
        reg.register_model(ModelVersion(
            name="test-model", arch_version="0.1.0-foundation",
            created_at="2026-01-01T00:00:00Z",
        ))
        s = reg.get_status()
        assert s["model_count"] == 1
        m = reg.get_model("test-model")
        assert m["name"] == "test-model"

    def test_refuse_non_make_checkpoint(self, tmp_root):
        from app.make_model.registry import get_registry, CheckpointRecord
        reg = get_registry()
        with pytest.raises(ValueError):
            reg.register_checkpoint(CheckpointRecord(
                id="x", model_name="m", model_version="v", arch_version="a",
                owner="OTHER", created_at="t", path="p", sha256="s", bytes=0,
                training_run_id="r", global_step=0, epoch=0, config={},
                dataset_name="d", dataset_manifest_sha="", git_commit="",
                framework_version="", pytorch_version="",
            ))

    def test_verify_missing_checkpoint(self, tmp_root):
        from app.make_model.registry import get_registry
        reg = get_registry()
        r = reg.verify_checkpoint("nope")
        assert r["ok"] is False


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class TestDataset:
    def test_empty_input_fails(self, tmp_root):
        from app.make_model.dataset import DatasetConfig, prepare_dataset
        with tempfile.TemporaryDirectory() as td:
            cfg = DatasetConfig(name="t", input_dir=td, output_dir=str(tmp_root / "ds"))
            with pytest.raises(RuntimeError):
                prepare_dataset(cfg)

    def test_validate_manifest_with_no_fields(self, tmp_root):
        from app.make_model.dataset import validate_dataset
        report = validate_dataset({"name": "x", "clips": [{"id": "a"}]})
        assert report["error_count"] > 0

    def test_validate_manifest_clean(self, tmp_root):
        from app.make_model.dataset import validate_dataset
        f = tmp_root / "fake.mp4"
        f.write_bytes(b"\x00" * 100)
        m = {
            "name": "x",
            "clips": [{
                "id": "a", "clip_path": str(f), "clip_sha256": "0" * 64,
                "clip_bytes": 100, "width": 16, "height": 16,
                "frames": 8, "fps": 8.0, "duration_seconds": 1.0,
                "caption": "test",
            }],
        }
        r = validate_dataset(m, require_caption=True)
        assert r["error_count"] == 0


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

class TestTraining:
    def test_training_config_round_trip(self, tmp_root):
        from app.make_model.training import TrainingConfig
        c = TrainingConfig(model_name="m", max_steps=10)
        d = c.to_dict()
        c2 = TrainingConfig.from_dict(d)
        assert c2.model_name == "m"
        assert c2.max_steps == 10

    def test_hardware_blocks_cpu_large_model(self, tmp_root):
        from app.make_model.training import (
            TrainingConfig, detect_hardware, enforce_hardware,
        )
        hw = detect_hardware()
        if hw.cuda_available and hw.gpu_vram_gb >= 8:
            pytest.skip("GPU available; CPU block cannot be tested")
        cfg = TrainingConfig(model_name="big", max_steps=1, min_vram_gb=8.0, allow_cpu_tiny=False)
        with pytest.raises(Exception):
            enforce_hardware(cfg, hw)

    def test_hardware_allows_tiny_cpu(self, tmp_root):
        from app.make_model.training import (
            TrainingConfig, detect_hardware, enforce_hardware,
        )
        hw = detect_hardware()
        if hw.cuda_available and hw.gpu_vram_gb >= 8:
            pytest.skip("GPU available; cannot exercise CPU tiny path")
        if not _has_torch():
            pytest.skip("REAL_NEURAL_MODEL_NOT_AVAILABLE: pytorch missing")
        cfg = TrainingConfig(
            model_name="tiny", max_steps=1,
            min_vram_gb=0.1, allow_cpu_tiny=True,
            arch_config={"name": "make-research-tiny", "arch_version": "0.1.0-foundation"},
        )
        enforce_hardware(cfg, hw)

    def test_readiness_report_shape(self, tmp_root):
        from app.make_model.training import TrainingConfig, validate_training_readiness
        r = validate_training_readiness(TrainingConfig(model_name="m"))
        assert r["ready"] is False
        assert "state" in r
        assert "checks" in r


# ---------------------------------------------------------------------------
# Inference availability
# ---------------------------------------------------------------------------

class TestInferenceAvailability:
    def test_returns_dict(self, tmp_root):
        from app.make_model.inference import inference_availability
        d = inference_availability()
        assert "available" in d
        assert "overall_state" in d

    def test_untrained_returns_false(self, tmp_root):
        from app.make_model.inference import inference_availability
        d = inference_availability()
        assert d["available"] is False
        assert d["overall_state"] == "untrained"


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class TestAudit:
    def test_audit_returns_verdict(self, tmp_root):
        from app.make_model.audit import run_ownership_audit
        r = run_ownership_audit()
        assert r["verdict"] in ("YES", "PARTIAL", "NO")
        assert r["verdict"] in ("PARTIAL", "NO")

    def test_audit_never_yes_without_checkpoint(self, tmp_root):
        from app.make_model.audit import run_ownership_audit
        r = run_ownership_audit()
        assert r["verdict"] != "YES"


# ---------------------------------------------------------------------------
# LocalNeuralProvider
# ---------------------------------------------------------------------------

class TestLocalNeuralProvider:
    def test_instantiation(self, tmp_root):
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        p = MakeLocalNeuralProvider()
        assert p is not None
        assert p.name == "make_local_neural"

    def test_capabilities(self, tmp_root):
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        p = MakeLocalNeuralProvider()
        caps = p.get_capabilities()
        assert "text_to_video" in {c.value for c in caps}

    def test_health_unavailable_when_untrained(self, tmp_root):
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        p = MakeLocalNeuralProvider()
        h = p.health()
        assert h.status.value == "unavailable" or h.status == "unavailable"

    def test_list_models_does_not_fail(self, tmp_root):
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        p = MakeLocalNeuralProvider()
        models = p.list_models()
        assert isinstance(models, list)

    def test_generate_fails_when_untrained(self, tmp_root):
        from app.make_model.local_neural_provider import MakeLocalNeuralProvider
        from app.providers.base import LegacyGenerationRequest
        p = MakeLocalNeuralProvider()
        # LegacyGenerationRequest has no `model_id`; use the sync generate()
        # which defaults to "make-video-research-v0".
        req = LegacyGenerationRequest(prompt="a hobbit hole")
        r = p.generate(req)
        assert r.status == "failed"
        assert r.metadata and r.metadata.get("code") == "MAKE_MODEL_UNTRAINED"


# ---------------------------------------------------------------------------
# API router
# ---------------------------------------------------------------------------

class TestAPI:
    def test_router_imports(self, tmp_root):
        from app.make_model.api import router
        assert router is not None
        paths = {r.path for r in router.routes}
        for needed in ("/api/v1/make-model/status", "/api/v1/make-model/hardware",
                       "/api/v1/make-model/models", "/api/v1/make-model/training/runs",
                       "/api/v1/make-model/checkpoints", "/api/v1/make-model/training/validate",
                       "/api/v1/make-model/inference/validate", "/api/v1/make-model/audit"):
            assert needed in paths, f"missing endpoint: {needed}"


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class TestErrors:
    def test_error_codes_unique(self):
        from app.make_model.training import (
            MakeModelUntrainedError, MakeModelCheckpointMissing,
            MakeModelCheckpointInvalid, MakeModelArchitectureMismatch,
            MakeModelGPUUnavailable, MakeModelVRAMInsufficient,
            MakeModelDependencyMissing, MakeModelDatasetMissing,
            MakeModelTrainingBlocked, MakeModelError,
        )
        codes = set()
        for cls in (
            MakeModelUntrainedError, MakeModelCheckpointMissing,
            MakeModelCheckpointInvalid, MakeModelArchitectureMismatch,
            MakeModelGPUUnavailable, MakeModelVRAMInsufficient,
            MakeModelDependencyMissing, MakeModelDatasetMissing,
            MakeModelTrainingBlocked,
        ):
            assert issubclass(cls, MakeModelError)
            codes.add(cls.code)
        assert len(codes) == 9


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_hardware(self, tmp_root):
        from app.make_model.cli import main
        import io, sys
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["hardware"])
        assert rc == 0
        out = buf.getvalue()
        d = json.loads(out)
        assert "pytorch_available" in d

    def test_cli_status(self, tmp_root):
        from app.make_model.cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["status"])
        assert rc == 0
        d = json.loads(buf.getvalue())
        assert d["overall_state"] == "untrained"

    def test_cli_audit(self, tmp_root):
        from app.make_model.cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["audit"])
        assert rc == 0
        d = json.loads(buf.getvalue())
        assert d["verdict"] in ("YES", "PARTIAL", "NO")

    def test_cli_inference_validate(self, tmp_root):
        from app.make_model.cli import main
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["inference", "validate"])
        assert rc == 0
        d = json.loads(buf.getvalue())
        assert d["available"] is False
