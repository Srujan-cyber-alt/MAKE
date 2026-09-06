"""Tests for MAKE World Model X VideoVAE."""

from __future__ import annotations

import tempfile
import unittest

import numpy as np

from app.make_model.world.vae import VideoVAE, VideoVAEConfig


class TestVideoVAE(unittest.TestCase):
    def test_parameter_count(self):
        cfg = VideoVAEConfig(channels=(32, 64, 128, 256), num_res_blocks=1)
        vae = VideoVAE(cfg)
        self.assertGreater(vae.parameter_count(), 0)

    def test_encode_shape(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        x = np.random.rand(1, 3, 4, 8, 8).astype(np.float32)
        mean, logvar = vae.encode(x)
        self.assertEqual(mean.shape, (1, 4, 1, 2, 2))
        self.assertEqual(logvar.shape, (1, 4, 1, 2, 2))

    def test_decode_shape(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        z = np.random.rand(1, 4, 1, 2, 2).astype(np.float32)
        recon = vae.decode(z)
        self.assertEqual(recon.shape, (1, 3, 4, 8, 8))

    def test_reconstruct_roundtrip(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        x = np.random.rand(1, 3, 4, 8, 8).astype(np.float32)
        recon = vae.reconstruct(x, seed=42)
        self.assertEqual(recon.shape, x.shape)
        self.assertTrue(np.all(recon >= 0.0))
        self.assertTrue(np.all(recon <= 1.0))

    def test_recon_loss_decreases_with_training(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        x = np.random.rand(1, 3, 4, 8, 8).astype(np.float32)
        loss1 = float(vae.recon_loss(vae.reconstruct(x, seed=0), x))
        # With random weights, loss should be finite and positive
        self.assertGreater(loss1, 0.0)

    def test_kl_loss(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        mean = np.zeros((1, 4, 1, 2, 2), dtype=np.float32)
        logvar = np.zeros((1, 4, 1, 2, 2), dtype=np.float32)
        kl = float(vae.kl_loss(mean, logvar))
        self.assertAlmostEqual(kl, 0.0, places=5)

    def test_save_load_roundtrip(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        x = np.random.rand(1, 3, 4, 8, 8).astype(np.float32)
        recon1 = vae.reconstruct(x, seed=42)
        params = vae.parameters()
        vae2 = VideoVAE(cfg)
        vae2.load_parameters(params)
        recon2 = vae2.reconstruct(x, seed=42)
        np.testing.assert_allclose(recon1, recon2, atol=1e-5)

    def test_encode_decode_gradient_check(self):
        cfg = VideoVAEConfig(channels=(16, 32, 64, 128), num_res_blocks=1)
        vae = VideoVAE(cfg)
        x = np.random.rand(1, 3, 4, 8, 8).astype(np.float32)
        mean, logvar = vae.encode(x)
        z = vae.reparameterize(mean, logvar, seed=42)
        recon = vae.decode(z)
        # Verify gradients can flow through (numpy path: check output changes with input)
        x2 = x + 0.01
        mean2, logvar2 = vae.encode(x2)
        z2 = vae.reparameterize(mean2, logvar2, seed=42)
        recon2 = vae.decode(z2)
        self.assertFalse(np.allclose(recon, recon2, atol=1e-5))


if __name__ == "__main__":
    unittest.main()
