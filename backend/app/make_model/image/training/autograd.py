"""
Tiny autograd (NumPy only).

Implements a Tensor-like wrapper with reverse-mode autodiff. We
restrict ourselves to the operations our UNet needs:

  - relu
  - conv2d (3x3, stride 1, padding)
  - group_norm (groups=1 for simplicity)
  - add
  - mul (with broadcastable constant per (B, C))
  - mean
  - concat (along channel axis)
  - average-pool 2x2 (downsample)
  - nearest upsample 2x2

This is enough for a small FiLM-conditioned UNet. The trainer calls
`Tensor.run_forward(model, x, t)` to compute (loss, cache) and then
`cache.backward(grad_out)` to populate parameter gradients.
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Tuple, Optional, Any


class Tensor:
    """A tiny autodiff tensor. Stores data and an optional backward fn."""

    __slots__ = ("data", "requires_grad", "_backward", "_parents", "name")

    def __init__(self, data: np.ndarray, requires_grad: bool = False,
                 _backward=None, _parents: tuple = (), name: str = ""):
        self.data = data.astype(np.float32, copy=False)
        self.requires_grad = requires_grad
        self._backward = _backward
        self._parents = _parents
        self.name = name

    def backward(self, grad: np.ndarray, grad_map: Optional[Dict[str, np.ndarray]] = None) -> None:
        """Run backprop. `grad_map` is unused (Params accumulate their own grads)."""
        if self._backward is None:
            return
        self._backward(grad, grad_map if grad_map is not None else {})

    # ---- ops ----
    def relu(self):
        x = self.data
        mask = (x > 0).astype(np.float32)
        out = Tensor(x * mask, requires_grad=self.requires_grad, name=f"{self.name}.relu")

        def _bwd(g, gm):
            self.backward(g * mask, gm)

        out._backward = _bwd
        out._parents = (self,)
        return out

    def add(self, other):
        a, b = self.data, other.data
        out = Tensor(a + b, requires_grad=self.requires_grad or other.requires_grad, name=f"{self.name}+{other.name}")

        def _bwd(g, gm):
            self.backward(g, gm)
            other.backward(g, gm)

        out._backward = _bwd
        out._parents = (self, other)
        return out

    def mul_const(self, c: float):
        out = Tensor(self.data * c, requires_grad=self.requires_grad, name=f"{self.name}*{c}")

        def _bwd(g, gm):
            self.backward(g * c, gm)

        out._backward = _bwd
        out._parents = (self,)
        return out

    def concat(self, other, axis: int = 1):
        out = Tensor(np.concatenate([self.data, other.data], axis=axis),
                     requires_grad=self.requires_grad or other.requires_grad,
                     name=f"cat({self.name},{other.name})")

        def _bwd(g, gm):
            B = self.data.shape[axis]
            sl = [slice(None)] * self.data.ndim
            sl[axis] = slice(0, B)
            self.backward(g[tuple(sl)], gm)
            sl2 = [slice(None)] * self.data.ndim
            sl2[axis] = slice(B, B + other.data.shape[axis])
            other.backward(g[tuple(sl2)], gm)

        out._backward = _bwd
        out._parents = (self, other)
        return out

    def avgpool_2x2(self):
        x = self.data
        B, C, H, W = x.shape
        out = Tensor(x.reshape(B, C, H // 2, 2, W // 2, 2).mean(axis=(3, 5)),
                     requires_grad=self.requires_grad, name=f"{self.name}.avgpool")

        def _bwd(g, gm):
            grad = np.zeros_like(x)
            r = grad.reshape(B, C, H // 2, 2, W // 2, 2)
            r[:, :, :, 0, :, 0] += g * 0.25
            r[:, :, :, 1, :, 0] += g * 0.25
            r[:, :, :, 0, :, 1] += g * 0.25
            r[:, :, :, 1, :, 1] += g * 0.25
            self.backward(grad, gm)

        out._backward = _bwd
        out._parents = (self,)
        return out

    def upsample_2x2(self):
        x = self.data
        B, C, H, W = x.shape
        out = Tensor(np.repeat(np.repeat(x, 2, axis=2), 2, axis=3) * 0.25,
                     requires_grad=self.requires_grad, name=f"{self.name}.upsample")

        def _bwd(g, gm):
            grad = (g[:, :, ::2, ::2] + g[:, :, 1::2, ::2] + g[:, :, ::2, 1::2] + g[:, :, 1::2, 1::2]) * 0.25
            self.backward(grad, gm)

        out._backward = _bwd
        out._parents = (self,)
        return out


# ---------------------------------------------------------------------------
# Parameter containers
# ---------------------------------------------------------------------------


class Param:
    """A learnable parameter. data is a numpy array. name is global."""

    __slots__ = ("data", "name", "grad")

    def __init__(self, data: np.ndarray, name: str):
        self.data = data.astype(np.float32)
        self.name = name
        self.grad = np.zeros_like(self.data)

    def tensor(self, requires_grad: bool = True) -> Tensor:
        t = Tensor(self.data, requires_grad=requires_grad, name=self.name)

        def _bwd(g, gm):
            self.grad += g

        t._backward = _bwd
        t._parents = ()
        return t


# ---------------------------------------------------------------------------
# Conv2d via im2col
# ---------------------------------------------------------------------------


def conv2d(x: Tensor, w: Param, b: Param, pad: int = 1) -> Tensor:
    from app.make_model.image.arch.unet import _im2col, _col2im
    B, _, H, W = x.data.shape
    C_out = w.data.shape[0]
    kh, kw = w.data.shape[2], w.data.shape[3]
    if pad > 0:
        xp = np.pad(x.data, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode="constant")
    else:
        xp = x.data
    cols = _im2col(xp, kh, kw, pad=0)
    w_flat = w.data.reshape(C_out, -1)
    out = (w_flat @ cols) + b.data[:, None]
    out_h = xp.shape[2] - kh + 1
    out_w_d = xp.shape[3] - kw + 1
    out = out.reshape(B, C_out, out_h, out_w_d)
    out_t = Tensor(out, requires_grad=True, name=f"conv({w.name})")

    def _bwd(g, gm):
        g2 = g.reshape(B, C_out, -1)
        # grad w
        gw = np.zeros_like(w.data)
        for i in range(B):
            gw += (g2[i] @ cols[i].T).reshape(w.data.shape)
        w.grad += gw
        # grad b
        b.grad += g.sum(axis=(0, 2, 3))
        # grad cols
        grad_cols = np.zeros_like(cols)
        for i in range(B):
            grad_cols[i] = w_flat.T @ g2[i]
        # grad xp via col2im
        grad_xp = _col2im(grad_cols, (B, w.data.shape[1], xp.shape[2], xp.shape[3]),
                           kh, kw, pad=0)
        if pad > 0:
            grad_x = grad_xp[:, :, pad:pad + H, pad:pad + W]
        else:
            grad_x = grad_xp
        x.backward(grad_x, gm)

    out_t._backward = _bwd
    out_t._parents = (x,)
    return out_t


def group_norm(x: Tensor, gamma: Param, beta: Param, eps: float = 1e-5) -> Tensor:
    B, C, H, W = x.data.shape
    mean = x.data.mean(axis=(1, 2, 3), keepdims=True)
    var = x.data.var(axis=(1, 2, 3), keepdims=True)
    inv_std = 1.0 / np.sqrt(var + eps)
    x_hat = (x.data - mean) * inv_std
    out = x_hat * gamma.data.reshape(1, C, 1, 1) + beta.data.reshape(1, C, 1, 1)
    out_t = Tensor(out, requires_grad=True, name=f"gn({gamma.name})")

    def _bwd(g, gm):
        Ng = C * H * W
        grad_gamma = (g * x_hat).sum(axis=(0, 2, 3))
        grad_beta = g.sum(axis=(0, 2, 3))
        gamma.grad += grad_gamma
        beta.grad += grad_beta
        grad_x_hat = g * gamma.data.reshape(1, C, 1, 1)
        grad_var = (grad_x_hat * (x.data - mean) * -0.5 * inv_std ** 3).sum(axis=(1, 2, 3), keepdims=True)
        grad_mean = grad_x_hat.sum(axis=(1, 2, 3), keepdims=True) / Ng
        grad_x = grad_x_hat * inv_std
        grad_x += 2.0 * (x.data - mean) * grad_var / Ng
        grad_x -= grad_mean
        x.backward(grad_x, gm)

    out_t._backward = _bwd
    out_t._parents = (x,)
    return out_t


def film(x: Tensor, scale: np.ndarray, shift: np.ndarray) -> Tensor:
    out = x.data * (1.0 + scale[:, :, None, None]) + shift[:, :, None, None]
    out_t = Tensor(out, requires_grad=x.requires_grad, name="film")
    # film has no learnable params; we just pass gradient through.
    out_t._backward = lambda g, gm: x.backward(g, gm)
    out_t._parents = (x,)
    return out_t