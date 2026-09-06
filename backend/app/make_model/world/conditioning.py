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
    text_emb: Optional[Any] = None
    image_emb: Optional[Any] = None
    video_emb: Optional[Any] = None
    identity_emb: Optional[Any] = None
    product_emb: Optional[Any] = None
    style_emb: Optional[Any] = None
    lighting_emb: Optional[Any] = None
    pose_emb: Optional[Any] = None
    depth_emb: Optional[Any] = None
    segmentation_emb: Optional[Any] = None
    mask_emb: Optional[Any] = None
    audio_emb: Optional[Any] = None
    motion_emb: Optional[Any] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "has_text": self.text_tokens is not None,
            "has_first_frame": self.first_frame is not None,
            "has_last_frame": self.last_frame is not None,
            "has_ref_slots": self.ref_slots is not None,
            "has_camera": self.camera is not None,
            "has_motion": self.motion is not None,
            "has_world": self.world is not None,
            "has_text_emb": self.text_emb is not None,
            "has_image_emb": self.image_emb is not None,
            "has_video_emb": self.video_emb is not None,
            "has_identity_emb": self.identity_emb is not None,
            "has_product_emb": self.product_emb is not None,
            "has_style_emb": self.style_emb is not None,
            "has_lighting_emb": self.lighting_emb is not None,
            "has_pose_emb": self.pose_emb is not None,
            "has_depth_emb": self.depth_emb is not None,
            "has_segmentation_emb": self.segmentation_emb is not None,
            "has_mask_emb": self.mask_emb is not None,
            "has_audio_emb": self.audio_emb is not None,
            "has_motion_emb": self.motion_emb is not None,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for f in [
            "text_emb", "text_tokens", "image_emb", "first_frame", "last_frame",
            "video_emb", "reference_emb", "identity_emb", "product_emb", "world_emb",
            "camera_emb", "motion_emb", "pose_emb", "style_emb", "lighting_emb",
            "depth_emb", "segmentation_emb", "mask_emb", "audio_emb",
        ]:
            val = getattr(self, f, None)
            if val is not None:
                d[f] = val
        if self.ref_slots is not None:
            d["reference_emb"] = self.ref_slots
        if self.camera is not None:
            d["camera_emb"] = self.camera
        if self.motion is not None:
            d["motion_emb"] = self.motion
        if self.world is not None:
            d["world_emb"] = self.world
        return d


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
