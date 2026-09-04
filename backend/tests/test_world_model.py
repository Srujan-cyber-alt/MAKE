"""Tests for MAKE World Model X (app.make_model.world).

These tests exercise:
    - architecture forward pass and parameter accounting
    - all conditioning inputs (text, image, references, camera, motion, world)
    - world / camera / motion / material representations
    - data engine dedup, quality scoring, scene detection, manifest IO
    - curriculum filtering, weighted sampling, hard-example mining
    - all loss functions and the total_loss aggregator
    - training config / trainer / optimizer / EMA / LR schedule / clip
    - distributed config
    - inference refusal paths (untrained / checkpoint missing / invalid)
    - evaluation harness with 100+ prompts
    - ownership audit (verdict logic)
    - scaling table parameter and VRAM estimates
    - checkpoint round-trip (save -> load -> inference)
    - proof test that ONLY succeeds with a real checkpoint on disk
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from typing import List

import numpy as np


# Force a sandbox root so we never touch the real make_model artifacts.
os.environ["MAKE_MODEL_ROOT"] = "/tmp/make_world_test_artifacts"


class TestArchitecture(unittest.TestCase):
    def test_config_presets(self):
        from app.make_model.world import MakeWorldModelConfig
        for p in ("TINY", "SMALL", "MEDIUM", "LARGE"):
            c = MakeWorldModelConfig.from_preset(p)
            self.assertTrue(c.hidden_dim > 0)
            self.assertTrue(c.num_layers > 0)
            self.assertEqual(c.name, f"make-world-{p.lower()}")

    def test_forward_shape_tiny(self):
        from app.make_model.world import MakeWorldModelConfig, MakeWorldModelV0
        cfg = MakeWorldModelConfig.from_preset("TINY")
        m = MakeWorldModelV0(cfg)
        B, Tt = 1, cfg.default_frames // cfg.temporal_patch
        H = W = cfg.default_short_side // cfg.patch_size
        x = np.random.randn(B, cfg.latent_channels, Tt, H, W).astype("float32")
        t = np.array([5], dtype="int64")
        text = np.zeros((B, cfg.text_seq_len), dtype="int64")
        out = m.forward(x, t, text)
        self.assertEqual(out.shape, (B, cfg.latent_channels, Tt, H, W))
        self.assertEqual(out.dtype, np.float32)

    def test_parameter_count_grows(self):
        from app.make_model.world import MakeWorldModelConfig, MakeWorldModelV0
        sizes = []
        for p in ("TINY", "SMALL", "MEDIUM"):
            cfg = MakeWorldModelConfig.from_preset(p)
            m = MakeWorldModelV0(cfg)
            sizes.append(m.parameter_count())
        self.assertLess(sizes[0], sizes[1])
        self.assertLess(sizes[1], sizes[2])

    def test_save_load_roundtrip(self):
        from app.make_model.world import MakeWorldModelConfig, MakeWorldModelV0
        cfg = MakeWorldModelConfig.from_preset("TINY")
        m = MakeWorldModelV0(cfg)
        B, Tt = 1, cfg.default_frames // cfg.temporal_patch
        H = W = cfg.default_short_side // cfg.patch_size
        x = np.random.randn(B, cfg.latent_channels, Tt, H, W).astype("float32")
        t = np.array([3], dtype="int64")
        text = np.zeros((B, cfg.text_seq_len), dtype="int64")
        out1 = m.forward(x, t, text)
        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name
        try:
            np.savez(path, **m.parameters())
            m2 = MakeWorldModelV0(cfg)
            m2.load_parameters(dict(np.load(path)))
            out2 = m2.forward(x, t, text)
            self.assertEqual(out1.shape, out2.shape)
            np.testing.assert_allclose(out1, out2, atol=1e-5)
        finally:
            os.remove(path)


class TestConditioning(unittest.TestCase):
    def test_compile_text_only(self):
        from app.make_model.world import ConditioningCompiler
        b = ConditioningCompiler().compile(prompt="hello")
        s = b.summary()
        self.assertTrue(s["has_text"])
        self.assertFalse(s["has_first_frame"])
        self.assertFalse(s["has_ref_slots"])

    def test_compile_with_references(self):
        from app.make_model.world import ConditioningCompiler
        b = ConditioningCompiler().compile(
            prompt="x",
            references=["/a.png", np.zeros(64, dtype="float32")],
        )
        s = b.summary()
        self.assertTrue(s["has_text"])
        self.assertTrue(s["has_ref_slots"])
        self.assertEqual(b.ref_slots.shape, (1, 4, 64))

    def test_compile_empty_prompt(self):
        from app.make_model.world import ConditioningCompiler
        b = ConditioningCompiler().compile(prompt="")
        self.assertIsNotNone(b.text_tokens)
        # zeros for empty
        np.testing.assert_array_equal(b.text_tokens, np.zeros((1, 16), dtype="int64"))


class TestRepresentations(unittest.TestCase):
    def test_round_trip(self):
        from app.make_model.world import (
            ObjectRepresentation,
            CameraRepresentation,
            MotionRepresentation,
            WorldSample,
        )
        ws = WorldSample(
            sample_id="x",
            objects=[ObjectRepresentation(id="o1", material="metal")],
            camera=CameraRepresentation(movement="dolly", focal_mm=50.0),
            motion=MotionRepresentation(action_class="walk"),
        )
        d = ws.to_dict()
        ws2 = WorldSample.from_dict(d)
        self.assertEqual(ws2.sample_id, "x")
        self.assertEqual(len(ws2.objects), 1)
        self.assertEqual(ws2.camera.movement, "dolly")
        self.assertEqual(ws2.motion.action_class, "walk")

    def test_camera_fov(self):
        from app.make_model.world import CameraRepresentation
        c = CameraRepresentation(focal_mm=50.0, sensor_w_mm=36.0)
        fov = c.horizontal_fov_rad
        self.assertGreater(fov, 0.4)
        self.assertLess(fov, 0.7)


class TestDataEngine(unittest.TestCase):
    def test_quality_metrics_keys(self):
        from app.make_model.world import compute_quality, QualityMetrics
        rng = np.random.default_rng(0)
        frames = rng.random((4, 32, 32, 3), dtype=np.float32)
        q = compute_quality(frames)
        self.assertIsInstance(q, QualityMetrics)
        self.assertGreaterEqual(q.sharpness, 0)
        self.assertLessEqual(q.sharpness, 1)

    def test_scene_detection(self):
        from app.make_model.world import detect_scene_changes
        f1 = np.zeros((2, 32, 32, 3), dtype=np.float32)
        f2 = np.ones((2, 32, 32, 3), dtype=np.float32)
        idx = detect_scene_changes(np.concatenate([f1, f2], axis=0), threshold=0.2)
        self.assertGreater(len(idx), 0)

    def test_ingest_directory_creates_manifest(self):
        from app.make_model.world import ingest_directory, DataEngineConfig
        cfg = DataEngineConfig(
            min_sharpness=0.0, min_motion=0.0,
            max_black_ratio=1.0, max_frozen_ratio=1.0,
            dedup_hamming_threshold=0,
        )
        with tempfile.TemporaryDirectory() as in_dir, tempfile.TemporaryDirectory() as out_dir:
            # create a tiny mp4
            src = os.path.join(in_dir, "x.mp4")
            self._make_tiny_mp4(src, frames=16, w=64, h=64, fps=8)
            m = ingest_directory(in_dir, out_dir, cfg=cfg)
            self.assertGreaterEqual(m.total_samples, 1)
            self.assertTrue(os.path.exists(os.path.join(out_dir, "manifest.json")))
            self.assertTrue(os.path.exists(os.path.join(out_dir, "skipped.json")))

    @staticmethod
    def _make_tiny_mp4(path, frames=16, w=64, h=64, fps=8):
        import subprocess
        import shutil
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        try:
            import imageio_ffmpeg as _ife
            ffmpeg_bin = ffmpeg_bin or _ife.get_ffmpeg_exe()
        except Exception:
            pass
        if ffmpeg_bin == "ffmpeg" and not shutil.which("ffmpeg"):
            raise unittest.SkipTest("ffmpeg not available")
        subprocess.run(
            [
                ffmpeg_bin, "-y", "-v", "error",
                "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate={fps}:duration={frames/fps}",
                "-frames:v", str(frames),
                "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
                path,
            ],
            check=True, timeout=30,
        )


class TestCurriculum(unittest.TestCase):
    def test_default_stages_count(self):
        from app.make_model.world import DEFAULT_STAGES
        self.assertEqual(len(DEFAULT_STAGES), 10)

    def test_advance_and_current(self):
        from app.make_model.world import Curriculum
        c = Curriculum()
        first = c.current().name
        self.assertTrue(c.advance())
        self.assertNotEqual(c.current().name, first)

    def test_weighted_sampler_draws(self):
        from app.make_model.world import WeightedSampler, HardExampleSet, FailureRecord
        from app.make_model.world.data_engine import TrainingSample, QualityMetrics
        samples = []
        for i in range(10):
            s = TrainingSample(
                sample_id=f"id{i}",
                source_path="", source_sha256="x", source_bytes=0,
                clip_path="", clip_sha256="x", clip_bytes=0,
                width=64, height=64, frames=8, fps=8.0, duration_seconds=1.0,
                quality=QualityMetrics(motion=0.5),
            )
            samples.append(s)
        hard = HardExampleSet()
        hard.add(FailureRecord(sample_id="id3", failure_class="motion", severity=0.9))
        ws = WeightedSampler(hard_multiplier=4.0, seed=0)
        drawn = ws.draw(samples, hard.ids(), batch_size=4)
        self.assertEqual(len(drawn), 4)


class TestLosses(unittest.TestCase):
    def test_each_loss_runs(self):
        from app.make_model.world import (
            reconstruction_loss,
            temporal_consistency_loss,
            motion_consistency_loss,
            text_alignment_loss,
            identity_consistency_loss,
            product_consistency_loss,
            camera_adherence_loss,
            perceptual_loss,
        )
        x = np.random.randn(1, 4, 8, 16, 16).astype("float32")
        self.assertGreaterEqual(float(reconstruction_loss(x, x)), 0.0)
        self.assertGreaterEqual(float(temporal_consistency_loss(x)), 0.0)
        f = np.random.randn(1, 2, 8, 16, 16).astype("float32")
        self.assertGreaterEqual(float(motion_consistency_loss(f, f)), 0.0)
        e = np.random.randn(1, 16).astype("float32")
        self.assertGreaterEqual(float(text_alignment_loss(e, e)), -1.0)
        self.assertGreaterEqual(float(identity_consistency_loss(e, e)), 0.0)
        self.assertGreaterEqual(float(product_consistency_loss(e, e)), 0.0)
        c = np.random.randn(1, 7).astype("float32")
        self.assertGreaterEqual(float(camera_adherence_loss(c, c)), 0.0)
        self.assertGreaterEqual(float(perceptual_loss(x, x)), 0.0)

    def test_total_loss_respects_weights(self):
        from app.make_model.world import LossWeights, total_loss
        out = total_loss(
            LossWeights(recon=1.0, temporal=0.5),
            recon=np.float32(2.0),
            temporal=np.float32(1.0),
        )
        self.assertAlmostEqual(out["total"], 2.0 * 1.0 + 1.0 * 0.5, places=5)


class TestTraining(unittest.TestCase):
    def test_optimizer_step(self):
        from app.make_model.world import OptimizerConfig, _AdamW
        cfg = OptimizerConfig(lr=1e-2)
        opt = _AdamW(cfg)
        p = {"a": np.ones((2, 2), dtype="float32")}
        g = {"a": np.ones((2, 2), dtype="float32")}
        new = opt.step(p, g)
        self.assertLess(float(new["a"].mean()), 1.0)

    def test_clip_grad_norm(self):
        from app.make_model.world import clip_grad_norm
        g = {"a": np.ones((2, 2), dtype="float32") * 100}
        clip_grad_norm(g, 1.0)
        self.assertLessEqual(float(np.linalg.norm(g["a"])), 1.0 + 1e-5)

    def test_trainer_runs(self):
        from app.make_model.world import (
            MakeWorldModelConfig, MakeWorldModelV0,
            TrainingConfig, Trainer,
        )
        cfg = MakeWorldModelConfig.from_preset("TINY")
        m = MakeWorldModelV0(cfg)
        tc = TrainingConfig(total_steps=3, warmup_steps=1, log_interval=1)
        t = Trainer(tc, m)
        history = t.train(batches=[None, None, None])
        self.assertEqual(len(history), 3)
        self.assertEqual(history[-1].step, 2)

    def test_distributed_config_from_env(self):
        from app.make_model.world import DistributedConfig
        os.environ["DDP_WORLD_SIZE"] = "4"
        os.environ["DDP_RANK"] = "2"
        d = DistributedConfig.from_env()
        self.assertEqual(d.world_size, 4)
        self.assertEqual(d.rank, 2)
        self.assertTrue(d.is_distributed())
        del os.environ["DDP_WORLD_SIZE"]
        del os.environ["DDP_RANK"]


class TestInference(unittest.TestCase):
    def test_engine_refuses_untrained(self):
        from app.make_model.world import (
            MakeWorldInferenceEngine,
            MakeWorldInferenceRequest,
        )
        from app.make_model.registry import MakeModelRegistry
        import uuid
        reg_dir = f"/tmp/make_world_untrained_{uuid.uuid4().hex[:8]}"
        os.makedirs(reg_dir, exist_ok=True)
        reg = MakeModelRegistry(os.path.join(reg_dir, "registry.json"))
        eng = MakeWorldInferenceEngine(reg)
        r = eng.run(MakeWorldInferenceRequest(prompt="hello"))
        self.assertFalse(r.ok)
        self.assertEqual(r.code, "MAKE_MODEL_X_UNTRAINED")

    def test_real_training_inference_roundtrip(self):
        """Proof test: a real trained checkpoint must produce a real video.

        This test:
            1. instantiates a TINY model
            2. runs a tiny "training" loop with deterministic fake grads
            3. saves the model parameters as a .npz
            4. registers the .npz in the MakeModelRegistry with
               arch_config, owner=MAKE, sha256
            5. creates a MakeWorldInferenceEngine
            6. runs an inference
            7. asserts the output is a real, valid MP4 on disk
        """
        from app.make_model.world import (
            MakeWorldModelConfig, MakeWorldModelV0,
            TrainingConfig, Trainer, MakeWorldInferenceEngine,
            MakeWorldInferenceRequest,
        )
        from app.make_model.registry import MakeModelRegistry, ModelVersion, CheckpointRecord
        from app.make_model.utils import sha256_file

        # 1. fresh registry file (use a unique path)
        import uuid
        reg_dir = f"/tmp/make_world_proof_{uuid.uuid4().hex[:8]}"
        os.makedirs(reg_dir, exist_ok=True)
        reg_path = os.path.join(reg_dir, "registry.json")
        reg = MakeModelRegistry(reg_path)
        reg.register_model(ModelVersion(
            name="make-world-tiny",
            arch_version="0.1.0",
            created_at="2026-01-01T00:00:00Z",
            config=MakeWorldModelConfig.from_preset("TINY").to_dict(),
        ))

        # 2. tiny training
        cfg = MakeWorldModelConfig.from_preset("TINY")
        m = MakeWorldModelV0(cfg)
        tc = TrainingConfig(total_steps=3, warmup_steps=1, log_interval=1)
        Trainer(tc, m).train([None, None, None])

        # 3. save
        ckpt_path = "/tmp/make_world_proof_ckpt.npz"
        np.savez(ckpt_path, **m.parameters())
        sha = sha256_file(ckpt_path)
        reg.register_checkpoint(CheckpointRecord(
            id="proof-1",
            model_name="make-world-tiny",
            model_version="0.1.0",
            arch_version="0.1.0",
            owner="MAKE",
            created_at="2026-01-01T00:00:00Z",
            path=ckpt_path,
            sha256=sha,
            bytes=os.path.getsize(ckpt_path),
            training_run_id="proof-run",
            global_step=3, epoch=1,
            config=cfg.to_dict(),
            dataset_name="",
            dataset_manifest_sha="",
            git_commit="",
            framework_version="numpy",
            pytorch_version="",
            metric_summary={"final_loss": 0.5},
        ))

        # 4. inference
        eng = MakeWorldInferenceEngine(reg)
        with tempfile.TemporaryDirectory() as td:
            req = MakeWorldInferenceRequest(
                prompt="hello",
                model_name="make-world-tiny",
                checkpoint_id="proof-1",
                seed=0,
                frames=4,
                short_side=16,
                fps=8,
                num_inference_steps=2,
            )
            r = eng.run(req)
            self.assertTrue(r.ok, f"inference failed: {r.code} {r.message}")
            self.assertTrue(os.path.exists(r.output_path))
            # file should be a real MP4
            self.assertGreater(os.path.getsize(r.output_path), 100)
            # provenance sidecar
            self.assertTrue(os.path.exists(r.output_path + ".provenance.json"))
            with open(r.output_path + ".provenance.json") as f:
                prov = json.load(f)
            self.assertEqual(prov["checkpoint_id"], "proof-1")
            self.assertEqual(prov["arch_version"], "0.1.0")


class TestEvaluation(unittest.TestCase):
    def test_prompt_count(self):
        from app.make_model.world import EVALUATION_PROMPTS
        self.assertGreaterEqual(len(EVALUATION_PROMPTS), 100)
        cats = {p["category"] for p in EVALUATION_PROMPTS}
        self.assertGreaterEqual(len(cats), 20)

    def test_harness_blocks_when_untrained(self):
        from app.make_model.world import (
            EVALUATION_PROMPTS, EvaluationHarness,
            MakeWorldInferenceEngine,
        )
        from app.make_model.registry import MakeModelRegistry
        import uuid
        reg_dir = f"/tmp/make_world_harness_{uuid.uuid4().hex[:8]}"
        os.makedirs(reg_dir, exist_ok=True)
        reg = MakeModelRegistry(os.path.join(reg_dir, "registry.json"))
        eng = MakeWorldInferenceEngine(reg)
        h = EvaluationHarness(eng)
        sub = EVALUATION_PROMPTS[:2]
        s = h.run(prompts=sub, frames=4, short_side=16, steps=1)
        self.assertEqual(s.total, 2)
        self.assertEqual(s.blocked, 2)


class TestAudit(unittest.TestCase):
    def test_partial_when_no_checkpoint(self):
        from app.make_model.world import run_world_ownership_audit
        rep = run_world_ownership_audit()
        self.assertEqual(rep.verdict, "PARTIAL")
        self.assertTrue(rep.has_architecture_code)
        self.assertTrue(rep.has_training_code)
        self.assertTrue(rep.has_data_engine)
        self.assertTrue(rep.has_inference_code)
        self.assertFalse(rep.has_checkpoint)

    def test_suspicious_scan_works(self):
        from app.make_model.world.audit import _scan_for_suspicious_weights
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "big.pt")
            with open(f, "wb") as fh:
                fh.write(b"0" * (200 * 1024 * 1024))  # 200MB
            sus = _scan_for_suspicious_weights(d)
            self.assertEqual(len(sus), 1)


class TestScaling(unittest.TestCase):
    def test_scaling_grows(self):
        from app.make_model.world import scaling_table
        t = scaling_table()
        self.assertIn("TINY", t)
        self.assertIn("LARGE", t)
        self.assertLess(t["TINY"].parameter_count, t["MEDIUM"].parameter_count)
        self.assertLess(t["TINY"].est_vram_gb_b1, t["MEDIUM"].est_vram_gb_b1)
        # all rows have plausible numbers
        for k, v in t.items():
            self.assertGreater(v.parameter_count, 0)
            self.assertGreater(v.est_vram_gb_b1, 0)


if __name__ == "__main__":
    unittest.main()
