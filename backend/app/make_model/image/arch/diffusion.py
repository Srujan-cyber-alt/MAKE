"""
GaussianDiffusion: standard DDPM forward and reverse process.

Linear beta schedule, identical to Ho et al. (2020) defaults (T=200,
beta_start=1e-4, beta_end=2e-2). Forward adds Gaussian noise to a
clean image x0. Reverse takes a noisy xt and a predicted noise from
the UNet, returning the predicted clean x0 and the next xt-1.
"""

from __future__ import annotations

import numpy as np


def make_beta_schedule(num_timesteps: int,
                       beta_start: float = 1e-4,
                       beta_end: float = 2e-2) -> np.ndarray:
    return np.linspace(beta_start, beta_end, num_timesteps, dtype=np.float32)


class GaussianDiffusion:
    def __init__(self, num_timesteps: int = 200,
                 beta_start: float = 1e-4,
                 beta_end: float = 2e-2):
        self.T = int(num_timesteps)
        self.betas = make_beta_schedule(self.T, beta_start, beta_end)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = np.cumprod(self.alphas).astype(np.float32)
        self.sqrt_alpha_bars = np.sqrt(self.alpha_bars).astype(np.float32)
        self.sqrt_one_minus_alpha_bars = np.sqrt(1.0 - self.alpha_bars).astype(np.float32)

    def q_sample(self, x0: np.ndarray, t: np.ndarray, noise: np.ndarray) -> np.ndarray:
        """Forward sample: x_t = sqrt(alpha_bar_t) * x0 + sqrt(1-alpha_bar_t) * noise."""
        sab = self.sqrt_alpha_bars[t][:, None, None, None]
        somab = self.sqrt_one_minus_alpha_bars[t][:, None, None, None]
        return sab * x0 + somab * noise

    def predict_x0_from_eps(self, xt: np.ndarray, t: np.ndarray, eps: np.ndarray) -> np.ndarray:
        sab = self.sqrt_alpha_bars[t][:, None, None, None]
        somab = self.sqrt_one_minus_alpha_bars[t][:, None, None, None]
        return (xt - somab * eps) / np.maximum(sab, 1e-3)

    def p_sample(self, xt: np.ndarray, t: int, eps_pred: np.ndarray) -> np.ndarray:
        """One reverse step. t is the current integer timestep, returns x_{t-1}."""
        beta_t = float(self.betas[t])
        alpha_t = float(self.alphas[t])
        alpha_bar_t = float(self.alpha_bars[t])
        sab = np.sqrt(alpha_bar_t)
        somab = np.sqrt(1.0 - alpha_bar_t)
        # predicted x0
        x0_pred = (xt - somab * eps_pred) / max(sab, 1e-3)
        # mean of posterior q(x_{t-1} | x_t, x0)
        mean = (np.sqrt(alpha_t) * (1.0 - self.alpha_bars[t - 1]) / max(1.0 - alpha_bar_t, 1e-6)) * x0_pred \
               + (np.sqrt(self.alpha_bars[t - 1]) * beta_t / max(1.0 - alpha_bar_t, 1e-6)) * xt
        if t == 0:
            return mean
        var = beta_t * (1.0 - self.alpha_bars[t - 1]) / max(1.0 - alpha_bar_t, 1e-6)
        noise = np.random.standard_normal(xt.shape).astype(np.float32)
        return mean + np.sqrt(var) * noise