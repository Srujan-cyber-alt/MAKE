"""
iPhone-controllable HTTP control server for the MAKE image subsystem.

A tiny, dependency-light HTTP server (http.server + ThreadingMixIn) that
the user can run on a box reachable from their iPhone / iPad over LAN or
tunnel. Endpoints:

  GET  /ping            health probe
  GET  /status          JSON: model, checkpoint, sample, hardware
  GET  /samples         JSON: list of recent samples
  GET  /exports/<fn>    download a generated PNG
  POST /generate        JSON body: {prompt, seed, steps, image_size}
  POST /train           JSON body: {steps, image_size, base_channels, ...}

Auth is OPTIONAL and disabled by default. To enable, set the env var
MAKE_IMAGE_TOKEN to a secret; clients must then send `Authorization: Bearer <token>`.

This server is deliberately simple and CPU-friendly so the same machine
can serve requests while continuing to train.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from app.make_model.utils import now_iso, sha256_file, get_logger
from app.make_model.image.inference.sampler import ImageSampler, SamplerConfig
from app.make_model.image.training.trainer import ImageTrainer, TrainingConfig
from app.make_model.image.dataset.acquire import acquire_image_dataset, load_image_arrays
from app.make_model.image.registry_bridge import ImageRegistryBridge
from app.make_model.image.arch.unet import count_params, NumpyUNet, NumpyUNetConfig
from app.make_model.registry import get_registry


logger = get_logger("make_model.image.server")


TOKEN = os.environ.get("MAKE_IMAGE_TOKEN", "").strip()


def _check_auth(handler) -> bool:
    if not TOKEN:
        return True
    h = handler.headers.get("Authorization", "")
    if h.startswith("Bearer "):
        return h.split(None, 1)[1].strip() == TOKEN
    return False


def _send_json(handler, code: int, payload: dict) -> None:
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    try:
        return json.loads(raw)
    except Exception:
        return {}


class Handler(BaseHTTPRequestHandler):
    server_version = "MAKE-Image/0.1"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[make-image] {self.address_string()} {fmt % args}\n")

    def _serve(self):
        if not _check_auth(self):
            _send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        path = urlparse(self.path).path
        method = self.command
        try:
            if path == "/ping" and method == "GET":
                self._ping()
            elif path == "/status" and method == "GET":
                self._status()
            elif path == "/samples" and method == "GET":
                self._samples()
            elif path.startswith("/exports/") and method == "GET":
                self._export(path)
            elif path == "/generate" and method == "POST":
                self._generate(_read_json(self))
            elif path == "/train" and method == "POST":
                self._train(_read_json(self))
            else:
                _send_json(self, 404, {"ok": False, "error": f"no route for {method} {path}"})
        except Exception as e:
            _send_json(self, 500, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-1000:]})

    def _ping(self):
        _send_json(self, 200, {"ok": True, "subsystem": "make_image", "ts": now_iso()})

    def _status(self):
        reg = get_registry()
        s = reg.get_status()
        cps = [c for c in s["checkpoints"] if c["model_name"] == ImageRegistryBridge.IMAGE_MODEL_NAME]
        latest = sorted(cps, key=lambda c: c.get("created_at", ""))[-1] if cps else None
        sample_dir = os.path.join(os.environ.get("MAKE_MODEL_ROOT", "/tmp/make_model_artifacts"), "exports", "images")
        samples = []
        if os.path.isdir(sample_dir):
            samples = sorted([f for f in os.listdir(sample_dir) if f.endswith(".png")])
        latest_sample = os.path.join(sample_dir, samples[-1]) if samples else None
        _send_json(self, 200, {
            "ok": True,
            "overall_state": s["overall_state"],
            "model_count": s["model_count"],
            "checkpoint_count": s["checkpoint_count"],
            "training_run_count": s["training_run_count"],
            "latest_checkpoint_sha256": latest["sha256"] if latest else None,
            "latest_checkpoint_step": latest["global_step"] if latest else None,
            "latest_sample_path": latest_sample,
            "latest_sample_sha256": sha256_file(latest_sample) if latest_sample else None,
            "hardware": {
                "device": "cpu",
                "cuda_available": False,
                "pytorch_available": False,
                "cpu_count": os.cpu_count(),
            },
            "note": "Native CPU image generation. No GPU. No external AI API. "
                     "32x32 native resolution unless retrained at larger size.",
        })

    def _samples(self):
        sample_dir = os.path.join(os.environ.get("MAKE_MODEL_ROOT", "/tmp/make_model_artifacts"), "exports", "images")
        if not os.path.isdir(sample_dir):
            _send_json(self, 200, {"samples": []}); return
        items = []
        for fn in sorted(os.listdir(sample_dir), reverse=True):
            if not fn.endswith(".png"):
                continue
            full = os.path.join(sample_dir, fn)
            prov = full + ".provenance.json"
            meta = {}
            if os.path.exists(prov):
                try:
                    meta = json.load(open(prov))
                except Exception:
                    pass
            items.append({
                "filename": fn,
                "url": f"/exports/{fn}",
                "bytes": os.path.getsize(full),
                "sha256": sha256_file(full),
                "created_at": meta.get("created_at", ""),
                "seed": meta.get("seed"),
                "prompt": meta.get("prompt", ""),
                "inference_steps": meta.get("inference_steps"),
                "generation_resolution_native": meta.get("generation_resolution_native"),
            })
        _send_json(self, 200, {"samples": items})

    def _export(self, path):
        fn = path[len("/exports/"):]
        if "/" in fn or "\\" in fn or ".." in fn:
            _send_json(self, 400, {"ok": False, "error": "invalid filename"}); return
        sample_dir = os.path.join(os.environ.get("MAKE_MODEL_ROOT", "/tmp/make_model_artifacts"), "exports", "images")
        full = os.path.join(sample_dir, fn)
        if not os.path.exists(full):
            _send_json(self, 404, {"ok": False, "error": "not found"}); return
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _generate(self, body: dict):
        cp = body.get("checkpoint_path") or self._latest_checkpoint_path()
        if not cp or not os.path.exists(cp):
            _send_json(self, 409, {"ok": False, "error": "No trained checkpoint available. Train first via /train."})
            return
        sampler = ImageSampler()
        base_cfg = SamplerConfig(
            model_name=ImageRegistryBridge.IMAGE_MODEL_NAME,
            checkpoint_path=cp,
            prompt=body.get("prompt", ""),
            seed=int(body.get("seed", 0)),
            num_inference_steps=int(body.get("steps", 30)),
            image_size=int(body.get("image_size", 32)),
            output_format=body.get("output_format", "png"),
            init_image_path=body.get("init_image_path", "") or "",
            init_strength=float(body.get("init_strength", 0.6)),
        )
        outputs = []
        n = max(1, min(int(body.get("batch_size", 1)), 8))
        for i in range(n):
            cfg_i = SamplerConfig(**{**base_cfg.to_dict(), "seed": base_cfg.seed + i})
            res = sampler.sample(cfg_i)
            ImageRegistryBridge().mark_inference_ready(res.output_path, res.output_sha256)
            outputs.append({
                "output_path": res.output_path,
                "output_url": f"/exports/{os.path.basename(res.output_path)}",
                "width": res.width,
                "height": res.height,
                "sha256": res.output_sha256,
                "bytes": res.output_bytes,
                "elapsed_seconds": res.elapsed_seconds,
                "inference_steps": res.inference_steps,
                "model_name": res.model_name,
                "checkpoint_sha256": res.checkpoint_sha256,
                "generation_resolution_native": res.generation_resolution_native,
                "refinement_resolution_native": res.refinement_resolution_native,
                "interpolation_note": res.interpolation_note,
                "kind": res.kind,
                "init_image_sha256": res.init_image_sha256,
                "created_at": res.created_at,
            })
        _send_json(self, 200, {"ok": True, "outputs": outputs, "count": len(outputs)})

    def _train(self, body: dict):
        steps = int(body.get("steps", 30))
        if steps < 1 or steps > 2000:
            _send_json(self, 400, {"ok": False, "error": "steps must be 1..2000"}); return
        image_size = int(body.get("image_size", 32))
        base_channels = int(body.get("base_channels", 16))
        num_res_blocks = int(body.get("num_res_blocks", 2))
        num_timesteps = int(body.get("num_timesteps", 80))
        batch_size = int(body.get("batch_size", 4))
        learning_rate = float(body.get("learning_rate", 3e-4))
        save_every = int(body.get("save_every", 20))
        procedural_count = int(body.get("procedural_count", 128))
        seed = int(body.get("seed", 0))
        sample_after = bool(body.get("sample_after", True))
        sample_prompt = str(body.get("sample_prompt", "a structured colored gradient"))
        sample_steps = int(body.get("sample_steps", 25))

        root = os.environ.get("MAKE_MODEL_ROOT") or None
        bridge = ImageRegistryBridge()
        info = acquire_image_dataset(out_root=root, target_size=image_size,
                                     procedural_count=procedural_count, seed=seed)
        arr = load_image_arrays(info, target_size=image_size)
        ucfg = NumpyUNetConfig(image_size=image_size, base_channels=base_channels,
                               num_res_blocks=num_res_blocks, num_timesteps=num_timesteps)
        _m = NumpyUNet(ucfg, seed=seed)
        n_params = count_params(_m)
        bridge.register_model(n_params, ucfg.to_dict())
        run_id = f"img-{int(time.time())}"
        cfg = TrainingConfig(
            image_size=image_size, base_channels=base_channels,
            num_res_blocks=num_res_blocks, num_timesteps=num_timesteps,
            batch_size=batch_size, max_steps=steps, save_every=save_every,
            learning_rate=learning_rate, seed=seed,
            dataset_kind=info.kind, dataset_name=info.name,
            dataset_manifest_sha=info.sha256_manifest,
            notes=f"via /train",
        )
        bridge.register_training_run(run_id, cfg.to_dict(), info.to_dict(), steps)
        trainer = ImageTrainer(cfg, out_root=root)
        result = trainer.train(arr, info.to_dict())
        bridge.register_checkpoint(
            checkpoint_path=result.checkpoint_path, training_run_id=run_id,
            config=cfg.to_dict(), dataset_info=info.to_dict(),
            global_step=result.steps_done,
            metric_summary={"final_loss": result.final_loss, "loss_curve": result.loss_curve},
            notes=f"via /train, elapsed={result.elapsed_seconds}",
        )
        bridge.finalize_training_run(run_id, result.steps_done, result.final_loss, result.checkpoint_path)
        sample_path = None
        if sample_after:
            sampler = ImageSampler(out_root=root)
            scfg = SamplerConfig(
                model_name=bridge.IMAGE_MODEL_NAME,
                checkpoint_path=result.checkpoint_path,
                prompt=sample_prompt, seed=42,
                num_inference_steps=sample_steps, image_size=image_size,
            )
            sres = sampler.sample(scfg)
            sample_path = sres.output_path
            bridge.mark_inference_ready(sres.output_path, sres.output_sha256)
        _send_json(self, 200, {
            "ok": True,
            "steps_done": result.steps_done,
            "final_loss": result.final_loss,
            "elapsed_seconds": result.elapsed_seconds,
            "checkpoint_path": result.checkpoint_path,
            "checkpoint_sha256": result.checkpoint_sha256,
            "parameters": result.parameters,
            "dataset_kind": info.kind,
            "dataset_name": info.name,
            "sample_path": sample_path,
            "created_at": now_iso(),
        })

    def _latest_checkpoint_path(self) -> str | None:
        reg = get_registry()
        cps = reg.list_checkpoints(model_name=ImageRegistryBridge.IMAGE_MODEL_NAME)
        if not cps:
            return None
        cp = sorted(cps, key=lambda c: c.get("created_at", ""))[-1]
        return cp.get("path")

    do_GET = _serve
    do_POST = _serve
    do_PUT = _serve
    do_DELETE = _serve


class ThreadedServer(ThreadingHTTPServer):
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="iPhone-controllable MAKE image server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8421)
    args = parser.parse_args()
    print(f"MAKE image server listening on http://{args.host}:{args.port}/")
    print(f"Routes: /ping /status /samples /exports/<fn> POST /generate POST /train")
    if TOKEN:
        print(f"Auth: Bearer token required")
    else:
        print("Auth: disabled (set MAKE_IMAGE_TOKEN to enable)")
    srv = ThreadedServer((args.host, args.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()