"""
Int8 weight quantization for the MAKE image model.

Strategy:
  - Per-tensor symmetric quantization with per-tensor scale.
  - Storage format: `q::<name>` stores int8 array, `s::<name>` stores float32 scale.
  - The model can be saved quantized and reloaded into float32 weights for
    inference (dequantize) or kept quantized for memory-bound use cases.

This is a CPU-friendly optimization: at inference time we dequantize once
on load, then run the regular float32 forward. We do NOT do on-the-fly
quantized matmul (the v1/v2 NumPy forward doesn't support that), so this
saves DISK SPACE for storing checkpoints and LOAD TIME for transmitting
them. For long-running processes the inference cost is unchanged.
"""

from __future__ import annotations

import os
import io
import numpy as np
from typing import Dict, Any, Tuple


def quantize_state_dict(state: Dict[str, np.ndarray], per_tensor: bool = True
                        ) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """Return (quantized_int8, scales) dicts."""
    q: Dict[str, np.ndarray] = {}
    s: Dict[str, np.ndarray] = {}
    for k, arr in state.items():
        arr = np.asarray(arr, dtype=np.float32)
        # Skip tiny arrays where quantization is meaningless
        if arr.size < 16:
            q[k] = arr.astype(np.float32)
            s[k] = np.array([1.0], dtype=np.float32)
            continue
        amax = float(np.max(np.abs(arr)))
        if amax < 1e-8:
            q[k] = np.zeros_like(arr, dtype=np.int8)
            s[k] = np.array([0.0], dtype=np.float32)
            continue
        scale = amax / 127.0
        qi = np.clip(np.round(arr / scale), -127, 127).astype(np.int8)
        q[k] = qi
        s[k] = np.array([scale], dtype=np.float32)
    return q, s


def dequantize_state_dict(q: Dict[str, np.ndarray], s: Dict[str, np.ndarray]
                          ) -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    for k in q:
        scale = float(s.get(k, np.array([1.0]))[0])
        qi = q[k]
        if qi.dtype == np.int8:
            out[k] = qi.astype(np.float32) * scale
        else:
            out[k] = qi.astype(np.float32)
    return out


def save_quantized_checkpoint(state: Dict[str, np.ndarray], out_path: str,
                              arch: Dict[str, Any]) -> str:
    q, s = quantize_state_dict(state)
    payload: Dict[str, Any] = {
        "schema_version": np.int32(3),
        "owner": "MAKE",
        "quantized": np.array([1]),
    }
    for k, v in arch.items():
        if isinstance(v, (int, float, str, bool)):
            payload[f"archcfg::{k}"] = np.array(v)
        elif isinstance(v, list):
            payload[f"archcfg::{k}"] = np.array(v)
        else:
            payload[f"archcfg::{k}"] = np.array(str(v))
    for k, arr in q.items():
        payload[f"q::{k}"] = arr
    for k, arr in s.items():
        payload[f"s::{k}"] = arr
    np.savez_compressed(out_path, **payload)
    return out_path


def load_quantized_checkpoint(path: str) -> Tuple[Dict[str, Any], Dict[str, np.ndarray]]:
    with np.load(path, allow_pickle=True) as data:
        files = set(data.files)
        arch = {}
        for k in files:
            if k.startswith("archcfg::"):
                name = k[len("archcfg::"):]
                v = data[k]
                if hasattr(v, "item") and v.ndim == 0:
                    try:
                        val = v.item()
                        if isinstance(val, bytes):
                            val = val.decode("utf-8")
                        arch[name] = val
                    except Exception:
                        arch[name] = v.tolist()
                else:
                    arch[name] = v.tolist()
        q: Dict[str, np.ndarray] = {k[len("q::"):]: np.asarray(data[k]) for k in files if k.startswith("q::")}
        s: Dict[str, np.ndarray] = {k[len("s::"):]: np.asarray(data[k]) for k in files if k.startswith("s::")}
    state = dequantize_state_dict(q, s)
    return arch, state
