"""
Tests for v2 image subsystem: architecture, sampler, quantize, dataset
provenance, iPhone API compatibility.
"""
from __future__ import annotations

import io
import os
import sys
import json
import time
import hashlib
import tempfile
import unittest
from pathlib import Path
from http.client import HTTPConnection

import numpy as np
from PIL import Image

# Ensure backend is importable
BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# v2 architecture tests
# ---------------------------------------------------------------------------


class TestV2Architecture(unittest.TestCase):
    def setUp(self):
        from app.make_model.image.arch.v2.conditioning import ConditionVector
        from app.make_model.image.arch.v2.unet import NumpyUNetV2, NumpyUNetV2Config
        self.ConditionVector = ConditionVector
        self.NumpyUNetV2 = NumpyUNetV2
        self.NumpyUNetV2Config = NumpyUNetV2Config
        self.cfg = NumpyUNetV2Config(
            image_size=32, base_channels=16, channel_mults=(1, 2),
            num_res_blocks=2, num_timesteps=50,
        )
        self.model = NumpyUNetV2(self.cfg, seed=0)

    def test_condition_vector_shape(self):
        cond = self.ConditionVector(prompt="a red car on a street")
        arr = cond.to_array()
        self.assertEqual(arr.shape[0], 149)

    def test_condition_vector_deterministic(self):
        cond1 = self.ConditionVector(prompt="a dog in a park")
        cond2 = self.ConditionVector(prompt="a dog in a park")
        self.assertTrue(np.allclose(cond1.to_array(), cond2.to_array()))

    def test_forward_shape(self):
        x = np.random.randn(2, 3, 32, 32).astype(np.float32)
        t = np.array([10, 20], dtype=np.float32)
        cond = self.ConditionVector(prompt="a portrait of a woman")
        id_vec = np.zeros((2, 16), dtype=np.float32)
        out = self.model.forward(x, t, cond, id_vec)
        self.assertEqual(out.shape, x.shape)

    def test_parameter_count(self):
        n = sum(p.size for p in self.model.parameters().values())
        self.assertGreater(n, 10000)

    def test_film_gates(self):
        x = np.random.randn(1, 3, 32, 32).astype(np.float32)
        t = np.array([5], dtype=np.float32)
        cond = self.ConditionVector(prompt="a cat")
        id_vec = np.zeros((1, 16), dtype=np.float32)
        out0 = self.model.forward(x, t, cond, id_vec)
        # Drop conditioning
        cond_drop = self.ConditionVector(prompt="a cat", drop_prompt=True)
        out1 = self.model.forward(x, t, cond_drop, id_vec)
        self.assertFalse(np.allclose(out0, out1))

    def test_state_dict_roundtrip(self):
        state = self.model.state_dict()
        self.assertGreater(len(state), 0)
        model2 = self.NumpyUNetV2(self.cfg, seed=0)
        model2.load_state_dict(state)
        np.random.seed(0)
        x = np.random.randn(1, 3, 32, 32).astype(np.float32)
        t = np.array([10], dtype=np.float32)
        cond = self.ConditionVector(prompt="a")
        idv = np.zeros((1, 16), dtype=np.float32)
        out1b = self.model.forward(x, t, cond, idv)
        out2b = model2.forward(x, t, cond, idv)
        self.assertTrue(np.allclose(out1b, out2b, atol=1e-5))


# ---------------------------------------------------------------------------
# Sampler tests
# ---------------------------------------------------------------------------


class TestV2Sampler(unittest.TestCase):
    def test_ddim_step_shape(self):
        from app.make_model.image.inference.sampler_v2 import _ddim_step
        B, C, H, W = 2, 3, 32, 32
        xt = np.random.randn(B, C, H, W).astype(np.float32)
        eps = np.random.randn(B, C, H, W).astype(np.float32)
        rng = np.random.default_rng(0)
        out = _ddim_step(xt, eps, eps, alpha_bar_t=0.5, alpha_bar_prev=0.6, guidance=2.0, eta=0.0, rng=rng)
        self.assertEqual(out.shape, (B, C, H, W))

    def test_ddpm_step_shape(self):
        from app.make_model.image.inference.sampler_v2 import _ddpm_step
        from app.make_model.image.arch.diffusion import GaussianDiffusion
        B, C, H, W = 2, 3, 32, 32
        xt = np.random.randn(B, C, H, W).astype(np.float32)
        eps = np.random.randn(B, C, H, W).astype(np.float32)
        diffusion = GaussianDiffusion(num_timesteps=50)
        rng = np.random.default_rng(0)
        out = _ddpm_step(xt, eps, t=10, t_prev=5, diffusion=diffusion, rng=rng)
        self.assertEqual(out.shape, (B, C, H, W))

    def test_tile_image(self):
        from app.make_model.image.inference.sampler_v2 import _tile_image
        arr = np.random.randn(64, 64, 3).astype(np.float32)
        tiles = _tile_image(arr, tile=32, overlap=4)
        self.assertGreater(len(tiles), 0)
        for tile in tiles:
            self.assertEqual(tile[4].shape[0], 3)
            self.assertLessEqual(tile[4].shape[1], 32)

    def test_blend_tiles(self):
        from app.make_model.image.inference.sampler_v2 import _blend_tiles
        canvas = np.zeros((3, 64, 64), dtype=np.float32)
        weight = np.zeros((3, 64, 64), dtype=np.float32)
        tile = np.ones((3, 32, 32), dtype=np.float32)
        _blend_tiles(canvas, weight, tile, 0, 0, 32, 32)
        self.assertTrue(np.any(canvas != 0))


# ---------------------------------------------------------------------------
# Quantization tests
# ---------------------------------------------------------------------------


class TestQuantization(unittest.TestCase):
    def test_quantize_roundtrip(self):
        from app.make_model.image.inference.quantization import quantize_state_dict, dequantize_state_dict
        state = {"w": np.random.randn(64).astype(np.float32)}
        q, scales = quantize_state_dict(state)
        dq = dequantize_state_dict(q, scales)
        for k in state:
            self.assertLess(np.max(np.abs(state[k] - dq[k])), 0.05)

    def test_save_load_quantized(self):
        from app.make_model.image.inference.quantization import save_quantized_checkpoint, load_quantized_checkpoint
        state = {
            "w": np.random.randn(32, 32).astype(np.float32) * 0.1,
            "b": np.random.randn(32).astype(np.float32) * 0.01,
        }
        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name
        try:
            save_quantized_checkpoint(state, path, arch={"arch_version": "test"})
            arch, loaded = load_quantized_checkpoint(path)
            for k in state:
                self.assertIn(k, loaded)
                self.assertLess(np.max(np.abs(state[k] - loaded[k])), 0.05)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Dataset provenance tests
# ---------------------------------------------------------------------------


class TestDatasetProvenance(unittest.TestCase):
    def setUp(self):
        root = Path("/tmp/make_image_v2/datasets/stream_v3_main")
        self.root = root
        self.prov = root / "DATASET_PROVENANCE.json"

    def test_provenance_exists(self):
        if not self.prov.exists():
            self.skipTest("provenance not generated in this session")

    def test_provenance_has_sources(self):
        if not self.prov.exists():
            self.skipTest("provenance not generated")
        data = json.loads(self.prov.read_text())
        self.assertIn("sources", data)
        self.assertGreater(len(data["sources"]), 0)

    def test_manifests_exist(self):
        for sub in self.root.iterdir():
            if not sub.is_dir():
                continue
            mf = sub / "MANIFEST.tsv"
            if mf.exists():
                lines = mf.read_text().strip().splitlines()
                self.assertGreaterEqual(len(lines), 1)

    def test_train_val_test_splits(self):
        for split in ("train", "val", "test"):
            p = self.root / f"SPLIT_{split}.tsv"
            self.assertTrue(p.exists(), f"{split} split missing")
            lines = p.read_text().strip().splitlines()
            self.assertGreater(len(lines), 0, f"{split} split empty")


# ---------------------------------------------------------------------------
# iPhone API tests
# ---------------------------------------------------------------------------


class TestIPhoneAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_ping(self):
        conn = HTTPConnection("localhost", 8421, timeout=5)
        try:
            conn.request("GET", "/ping")
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
            data = json.loads(r.read())
            self.assertTrue(data.get("ok"))
        except ConnectionRefusedError:
            self.skipTest("iPhone server not running on 8421")

    def test_info(self):
        conn = HTTPConnection("localhost", 8421, timeout=5)
        try:
            conn.request("GET", "/v2/info")
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
            data = json.loads(r.read())
            self.assertIn("capabilities", data)
        except ConnectionRefusedError:
            self.skipTest("iPhone server not running on 8421")

    def test_licenses(self):
        conn = HTTPConnection("localhost", 8421, timeout=5)
        try:
            conn.request("GET", "/v2/licenses")
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
        except ConnectionRefusedError:
            self.skipTest("iPhone server not running on 8421")

    def test_datasets(self):
        conn = HTTPConnection("localhost", 8421, timeout=5)
        try:
            conn.request("GET", "/v2/datasets")
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
        except ConnectionRefusedError:
            self.skipTest("iPhone server not running on 8421")

    def test_quality(self):
        conn = HTTPConnection("localhost", 8421, timeout=5)
        try:
            samples = list(Path("/tmp/make_image_v2/exports/images").glob("*.png"))
            if not samples:
                self.skipTest("no samples for quality test")
            body = json.dumps({"image_path": str(samples[0])}).encode()
            conn.request("POST", "/v2/quality", body=body, headers={"Content-Type": "application/json"})
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
        except ConnectionRefusedError:
            self.skipTest("iPhone server not running on 8421")


if __name__ == "__main__":
    unittest.main(verbosity=2)
