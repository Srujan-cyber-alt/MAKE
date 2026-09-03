"""Conditioning pipeline for MAKE World Model X.

This module is the *model-side* interface for ALL conditioning inputs:
    - text (compiled by the existing AdvancedPromptCompiler)
    - first-frame / last-frame (image -> video)
    - reference images (identity, character, product, world)
    - camera intent (canonical CameraRepresentation)
    - motion intent (optical flow / pose / trajectory)
    - identity slot embeddings
    - product slot embeddings
    - world slot embeddings

It is a thin layer that converts each modality into the model-side
tensor vocabulary. It does NOT re-implement the prompt compiler, the
vision engine, the identity engine, the product system, or the world
system. It only calls their public functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .representation import (
    CameraRepresentation,
    MotionRepresentation,
    ObjectRepresentation,
    PersonRepresentation,
    WorldSample,
)


@dataclass
class ConditioningBundle:
    """The result of compiling a request into model-side conditioning."""

    text_tokens: Optional[Any] = None
    cross_ctx: Optional[Any] = None
    first_frame: Optional[Any] = None
    last_frame: Optional[Any] = None
    ref_slots: Optional[Any] = None
    camera: Optional[CameraRepresentation] = None
    motion: Optional[MotionRepresentation] = None
    world: Optional[WorldSample] = None
    seed: int = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "has_text": self.text_tokens is not None,
            "has_first_frame": self.first_frame is not None,
            "has_last_frame": self.last_frame is not None,
            "has_ref_slots": self.ref_slots is not None,
            "has_camera": self.camera is not None,
            "has_motion": self.motion is not None,
            "has_world": self.world is not None,
        }


class ConditioningCompiler:
    """Stateless compiler: takes a request, returns a ConditioningBundle.

    This class is the *ONLY* place where prompt / image / camera /
    motion / identity / product / world are converted into model-side
    tensors. Everything else just produces / consumes ConditioningBundle.
    """

    def __init__(self, vocab_size: int = 4096, ref_slot_dim: int = 64) -> None:
        self.vocab_size = vocab_size
        self.ref_slot_dim = ref_slot_dim
        # deterministic token mapping for the research baseline. The real
        # tokenizer will be a SentencePiece model trained on captions.
        self._tok_mod = 7919  # prime

    def _tokenize_text(self, prompt: str, seq_len: int = 16) -> np.ndarray:
        """Deterministic integer tokens from a UTF-8 string.

        Real model will use a SentencePiece tokenizer; this is the
        reference that keeps the conditioning pipeline importable
        without external deps.
        """
        if not prompt:
            return np.zeros((1, seq_len), dtype=np.int64)
        ids: List[int] = []
        for ch in prompt.encode("utf-8"):
            ids.append(int(ch) % self.vocab_size)
        while len(ids) < seq_len:
            ids.append(0)
        ids = ids[:seq_len]
        return np.array(ids, dtype=np.int64)[None, :]

    def _reference_to_slots(
        self, references: Optional[Sequence[Any]]
    ) -> Optional[np.ndarray]:
        """Convert N reference embeddings (or paths) into R x D slots.

        If the references are numpy arrays, we use their mean. If they
        are paths, we hash the path to a deterministic slot for now.
        The real implementation will run a frozen image encoder to
        produce a D-dim embedding.
        """
        if not references:
            return None
        slots: List[np.ndarray] = []
        for r in references:
            if isinstance(r, np.ndarray):
                v = r.flatten()
            elif isinstance(r, (bytes, bytearray)):
                v = np.frombuffer(r, dtype=np.uint8).astype(np.float32) / 255.0
            else:
                # deterministic hash for path / string
                s = str(r).encode("utf-8")
                h = int.from_bytes(s[:8], "little", signed=False) or 1
                rng = np.random.default_rng(h)
                v = rng.standard_normal(self.ref_slot_dim).astype(np.float32)
            v = v[: self.ref_slot_dim] if v.size >= self.ref_slot_dim else np.pad(
                v, (0, self.ref_slot_dim - v.size)
            )
            slots.append(v.astype(np.float32))
        while len(slots) < 4:
            slots.append(np.zeros(self.ref_slot_dim, dtype=np.float32))
        return np.stack(slots[:4], axis=0)[None, :, :]  # (1, R, D)

    def compile(
        self,
        prompt: Optional[str] = None,
        first_frame: Optional[Any] = None,
        last_frame: Optional[Any] = None,
        references: Optional[Sequence[Any]] = None,
        camera: Optional[CameraRepresentation] = None,
        motion: Optional[MotionRepresentation] = None,
        world: Optional[WorldSample] = None,
        seed: int = 0,
    ) -> ConditioningBundle:
        text_tokens = self._tokenize_text(prompt or "") if prompt is not None else None
        ref_slots = self._reference_to_slots(references)
        return ConditioningBundle(
            text_tokens=text_tokens,
            cross_ctx=None,  # computed inside the model (mean of text emb)
            first_frame=first_frame,
            last_frame=last_frame,
            ref_slots=ref_slots,
            camera=camera,
            motion=motion,
            world=world,
            seed=seed,
        )


__all__ = [
    "ConditioningBundle",
    "ConditioningCompiler",
]
