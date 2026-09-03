"""MAKE World Model X — Evaluation harness.

Two parts:

1. EVALUATION_PROMPTS: 100+ carefully designed prompts across 20
   categories, all matching the same resolution, duration, fps, and
   seed conventions. They are designed to be IDENTICAL INPUT tests.

2. EvaluationHarness: a class that:
   - takes a MakeWorldInferenceEngine
   - takes a list of prompts
   - runs each prompt and records per-prompt metrics
   - produces a JSON summary

The harness will refuse to run with a placeholder model. It returns
a structured "BLOCKED: model is untrained" result for every prompt
until a real MAKE checkpoint exists.

Reuses existing MAKE quality systems via direct call (no
duplication). Does not implement new scoring.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence

from app.make_model.world.inference import (
    MakeWorldInferenceEngine,
    MakeWorldInferenceRequest,
)


# ----------------------------------------------------------------------
# 100+ evaluation prompts
# ----------------------------------------------------------------------


EVALUATION_PROMPTS: List[Dict[str, Any]] = [
    # 1 basic motion
    {"id": "e001", "category": "basic_motion", "prompt": "a single leaf falling in slow motion against a clear sky"},
    {"id": "e002", "category": "basic_motion", "prompt": "a candle flame flickering in a dark room"},
    {"id": "e003", "category": "basic_motion", "prompt": "smoke rising from a cup of coffee"},
    {"id": "e004", "category": "basic_motion", "prompt": "a balloon drifting upward into a clear blue sky"},
    {"id": "e005", "category": "basic_motion", "prompt": "a flag waving gently in the wind"},
    # 2 complex motion
    {"id": "e006", "category": "complex_motion", "prompt": "a gymnast performing a backflip on a balance beam"},
    {"id": "e007", "category": "complex_motion", "prompt": "a ballet dancer spinning on a stage under warm light"},
    {"id": "e008", "category": "complex_motion", "prompt": "a Formula 1 car drifting around a corner"},
    {"id": "e009", "category": "complex_motion", "prompt": "a cheetah sprinting across the savannah"},
    {"id": "e010", "category": "complex_motion", "prompt": "a skateboarder doing a kickflip down a flight of stairs"},
    # 3 humans
    {"id": "e011", "category": "humans", "prompt": "an elderly man reading a book by a window at golden hour"},
    {"id": "e012", "category": "humans", "prompt": "a child laughing while chasing bubbles in a park"},
    {"id": "e013", "category": "humans", "prompt": "a woman in a red dress walking down a rainy city street at night"},
    {"id": "e014", "category": "humans", "prompt": "a chef plating a dish in a busy kitchen"},
    {"id": "e015", "category": "humans", "prompt": "two friends laughing while sharing coffee at a cafe"},
    # 4 animals
    {"id": "e016", "category": "animals", "prompt": "a dog running through shallow water on a beach"},
    {"id": "e017", "category": "animals", "prompt": "a cat playing with a ball of yarn on a sofa"},
    {"id": "e018", "category": "animals", "prompt": "an eagle soaring over snow-capped mountains"},
    {"id": "e019", "category": "animals", "prompt": "a school of fish moving through a coral reef"},
    {"id": "e020", "category": "animals", "prompt": "a horse galloping across an open field at sunset"},
    # 5 vehicles
    {"id": "e021", "category": "vehicles", "prompt": "a vintage motorcycle cruising on a coastal highway"},
    {"id": "e022", "category": "vehicles", "prompt": "a yellow taxi driving through Times Square at night"},
    {"id": "e023", "category": "vehicles", "prompt": "a sailboat crossing a calm sea at golden hour"},
    {"id": "e024", "category": "vehicles", "prompt": "a steam locomotive emerging from a tunnel"},
    {"id": "e025", "category": "vehicles", "prompt": "a futuristic spacecraft lifting off from a launch pad"},
    # 6 products
    {"id": "e026", "category": "products", "prompt": "a luxury watch rotating on a velvet display under soft light"},
    {"id": "e027", "category": "products", "prompt": "a perfume bottle being sprayed with droplets catching the light"},
    {"id": "e028", "category": "products", "prompt": "a sneaker rotating 360 degrees on a white studio background"},
    {"id": "e029", "category": "products", "prompt": "a coffee machine brewing espresso with steam rising"},
    {"id": "e030", "category": "products", "prompt": "a smartphone lying on a wooden table with morning sunlight"},
    # 7 environments
    {"id": "e031", "category": "environments", "prompt": "a misty forest at dawn with sunbeams cutting through the trees"},
    {"id": "e032", "category": "environments", "prompt": "a desert sandstorm approaching a distant village"},
    {"id": "e033", "category": "environments", "prompt": "a snowy mountain peak above the clouds at sunrise"},
    {"id": "e034", "category": "environments", "prompt": "a bustling Tokyo intersection at night with neon signs"},
    {"id": "e035", "category": "environments", "prompt": "a quiet library with dust particles floating in the light"},
    # 8 camera control
    {"id": "e036", "category": "camera_control", "prompt": "static wide shot: a lone lighthouse on a cliff at sunset"},
    {"id": "e037", "category": "camera_control", "prompt": "slow dolly push-in toward a violinist mid-performance"},
    {"id": "e038", "category": "camera_control", "prompt": "low angle tilt up: a skyscraper against a stormy sky"},
    {"id": "e039", "category": "camera_control", "prompt": "orbiting shot around a dancer in a spotlight"},
    {"id": "e040", "category": "camera_control", "prompt": "FPV drone shot flying through an abandoned warehouse"},
    # 9 lighting
    {"id": "e041", "category": "lighting", "prompt": "a portrait lit only by candlelight"},
    {"id": "e042", "category": "lighting", "prompt": "a streetlamp illuminating falling snow at night"},
    {"id": "e043", "category": "lighting", "prompt": "high-key studio lighting on a fashion model"},
    {"id": "e044", "category": "lighting", "prompt": "rim lighting on a dancer silhouetted against a sunset"},
    {"id": "e045", "category": "lighting", "prompt": "neon signs reflecting on a wet pavement after rain"},
    # 10 weather
    {"id": "e046", "category": "weather", "prompt": "a thunderstorm approaching a prairie with dramatic clouds"},
    {"id": "e047", "category": "weather", "prompt": "a heavy snowfall in a mountain village at dusk"},
    {"id": "e048", "category": "weather", "prompt": "a tornado forming over a flat plain"},
    {"id": "e049", "category": "weather", "prompt": "a foggy morning over a calm lake"},
    {"id": "e050", "category": "weather", "prompt": "a sand dune lit by a setting sun under a clear sky"},
    # 11 interactions
    {"id": "e051", "category": "interactions", "prompt": "a person handing a flower to another person"},
    {"id": "e052", "category": "interactions", "prompt": "a child reaching out to pet a friendly dog"},
    {"id": "e053", "category": "interactions", "prompt": "a person pouring wine into a glass"},
    {"id": "e054", "category": "interactions", "prompt": "a carpenter hammering a nail into wood"},
    {"id": "e055", "category": "interactions", "prompt": "two fencers engaged in a duel"},
    # 12 identity
    {"id": "e056", "category": "identity", "prompt": "the same elderly man with white hair and round glasses, reading a book"},
    {"id": "e057", "category": "identity", "prompt": "the same woman with long black hair in a yellow coat, smiling at the camera"},
    {"id": "e058", "category": "identity", "prompt": "the same child with curly red hair, drawing with crayons"},
    {"id": "e059", "category": "identity", "prompt": "the same bearded chef in a white apron, tasting soup"},
    {"id": "e060", "category": "identity", "prompt": "the same ballerina in a white tutu, mid-leap"},
    # 13 product fidelity
    {"id": "e061", "category": "product_fidelity", "prompt": "a black ceramic coffee mug with a matte finish on a wooden table"},
    {"id": "e062", "category": "product_fidelity", "prompt": "a glass perfume bottle with a gold cap on a marble counter"},
    {"id": "e063", "category": "product_fidelity", "prompt": "a leather wallet with visible stitching on a fabric background"},
    {"id": "e064", "category": "product_fidelity", "prompt": "a stainless steel watch with a blue dial on a velvet cushion"},
    {"id": "e065", "category": "product_fidelity", "prompt": "a matte black wireless earbuds case rotating slowly"},
    # 14 long temporal consistency
    {"id": "e066", "category": "long_temporal", "prompt": "a flower blooming over 10 seconds in time-lapse"},
    {"id": "e067", "category": "long_temporal", "prompt": "a person jogging continuously along a forest path"},
    {"id": "e068", "category": "long_temporal", "prompt": "a candle burning down slowly over time"},
    {"id": "e069", "category": "long_temporal", "prompt": "clouds drifting continuously across a mountain landscape"},
    {"id": "e070", "category": "long_temporal", "prompt": "a person turning the pages of a book one by one"},
    # 15 difficult prompts
    {"id": "e071", "category": "difficult_prompts", "prompt": "a reflection of a city skyline in a puddle on a rainy night"},
    {"id": "e072", "category": "difficult_prompts", "prompt": "a transparent glass sphere refracting a forest behind it"},
    {"id": "e073", "category": "difficult_prompts", "prompt": "a room with mirrors on three walls and a person inside"},
    {"id": "e074", "category": "difficult_prompts", "prompt": "an astronaut floating weightlessly inside a space station"},
    {"id": "e075", "category": "difficult_prompts", "prompt": "a person wearing a mask that perfectly matches their face paint"},
    # 16 compositional prompts
    {"id": "e076", "category": "compositional", "prompt": "a cat sitting on a windowsill with rain visible outside"},
    {"id": "e077", "category": "compositional", "prompt": "a person playing a piano in a candlelit room"},
    {"id": "e078", "category": "compositional", "prompt": "a child holding a red balloon in a crowd"},
    {"id": "e079", "category": "compositional", "prompt": "a vase of sunflowers on a kitchen table with morning light"},
    {"id": "e080", "category": "compositional", "prompt": "a vintage car parked under a streetlamp in the rain"},
    # 17 cinematic prompts
    {"id": "e081", "category": "cinematic", "prompt": "anamorphic widescreen: a man walking toward the camera in a dark alley"},
    {"id": "e082", "category": "cinematic", "prompt": "an extreme close-up of an eye with a reflection of a city"},
    {"id": "e083", "category": "cinematic", "prompt": "a slow dolly shot revealing a vast alien landscape"},
    {"id": "e084", "category": "cinematic", "prompt": "a film noir scene with a woman in a trench coat under a streetlamp"},
    {"id": "e085", "category": "cinematic", "prompt": "a fight scene in slow motion with debris flying"},
    # 18 physics-sensitive
    {"id": "e086", "category": "physics", "prompt": "a glass vase falling off a table and shattering on the floor"},
    {"id": "e087", "category": "physics", "prompt": "a ball being thrown into a pond, creating ripples"},
    {"id": "e088", "category": "physics", "prompt": "a person jumping over a puddle and landing on dry ground"},
    {"id": "e089", "category": "physics", "prompt": "smoke billowing from a chimney in a strong wind"},
    {"id": "e090", "category": "physics", "prompt": "a soap bubble being formed and floating away"},
    # 19 reference conditioning
    {"id": "e091", "category": "reference", "prompt": "a man resembling the provided reference, walking through a market"},
    {"id": "e092", "category": "reference", "prompt": "a product resembling the provided reference, displayed on a turntable"},
    {"id": "e093", "category": "reference", "prompt": "a character resembling the provided reference, in a dramatic scene"},
    {"id": "e094", "category": "reference", "prompt": "a building resembling the provided reference, at sunset"},
    {"id": "e095", "category": "reference", "prompt": "a vehicle resembling the provided reference, in motion"},
    # 20 adversarial prompts
    {"id": "e096", "category": "adversarial", "prompt": "a three-headed dog playing chess with a cat"},
    {"id": "e097", "category": "adversarial", "prompt": "a person made entirely of water walking on land"},
    {"id": "e098", "category": "adversarial", "prompt": "an impossible Escher staircase with people walking on it"},
    {"id": "e099", "category": "adversarial", "prompt": "text reading 'MAKE' written in smoke against a dark sky"},
    {"id": "e100", "category": "adversarial", "prompt": "a chameleon that is simultaneously red, blue, and green"},
    {"id": "e101", "category": "adversarial", "prompt": "a clock running backwards in a quiet room"},
    {"id": "e102", "category": "adversarial", "prompt": "a transparent human walking down a busy street"},
    {"id": "e103", "category": "adversarial", "prompt": "two suns setting simultaneously over a calm ocean"},
    {"id": "e104", "category": "adversarial", "prompt": "a book whose pages turn forward and backward at the same time"},
    {"id": "e105", "category": "adversarial", "prompt": "a person whose shadow is a different person"},
]


@dataclass
class EvaluationRow:
    prompt_id: str
    category: str
    prompt: str
    ok: bool
    code: str
    message: str
    output_path: Optional[str]
    elapsed_seconds: float
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationSummary:
    total: int
    passed: int
    failed: int
    blocked: int
    elapsed_seconds: float
    rows: List[EvaluationRow]

    def by_category(self) -> Dict[str, Dict[str, int]]:
        out: Dict[str, Dict[str, int]] = {}
        for r in self.rows:
            d = out.setdefault(r.category, {"total": 0, "ok": 0, "failed": 0, "blocked": 0})
            d["total"] += 1
            if r.code == "MAKE_MODEL_X_UNTRAINED":
                d["blocked"] += 1
            elif r.ok:
                d["ok"] += 1
            else:
                d["failed"] += 1
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "blocked": self.blocked,
            "elapsed_seconds": self.elapsed_seconds,
            "by_category": self.by_category(),
            "rows": [asdict(r) for r in self.rows],
        }


class EvaluationHarness:
    def __init__(self, engine: MakeWorldInferenceEngine) -> None:
        self.engine = engine

    def run(
        self,
        prompts: Sequence[Dict[str, Any]] = None,
        model_name: str = "make-world-tiny",
        seed: int = 0,
        frames: int = 8,
        short_side: int = 64,
        fps: float = 8.0,
        steps: int = 4,
    ) -> EvaluationSummary:
        prompts = prompts or EVALUATION_PROMPTS
        rows: List[EvaluationRow] = []
        passed = 0
        failed = 0
        blocked = 0
        t0 = time.time()
        for p in prompts:
            req = MakeWorldInferenceRequest(
                prompt=p["prompt"],
                model_name=model_name,
                seed=seed,
                frames=frames,
                short_side=short_side,
                fps=fps,
                num_inference_steps=steps,
            )
            t_r0 = time.time()
            res = self.engine.run(req)
            elapsed = time.time() - t_r0
            if res.code == "MAKE_MODEL_X_UNTRAINED":
                blocked += 1
            elif res.ok:
                passed += 1
            else:
                failed += 1
            rows.append(
                EvaluationRow(
                    prompt_id=p["id"],
                    category=p["category"],
                    prompt=p["prompt"],
                    ok=res.ok,
                    code=res.code,
                    message=res.message,
                    output_path=res.output_path,
                    elapsed_seconds=elapsed,
                )
            )
        return EvaluationSummary(
            total=len(rows),
            passed=passed,
            failed=failed,
            blocked=blocked,
            elapsed_seconds=time.time() - t0,
            rows=rows,
        )


__all__ = [
    "EVALUATION_PROMPTS",
    "EvaluationRow",
    "EvaluationSummary",
    "EvaluationHarness",
]
