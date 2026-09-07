"""
CLI / orchestration entry point for the MAKE image subsystem.

Usage (CPU-only sandbox):

  MAKE_MODEL_ROOT=/tmp/make_image \\
    python -m app.make_model.image.cli_train \\
      --steps 60 --image-size 32 --base-channels 24

Will:
  1. Acquire a public-domain / procedural dataset
  2. Train the NumpyUNet for the requested number of steps
  3. Register the model + run + checkpoint in the existing MAKE registry
  4. Emit a final SampleResult (one image at native 32x32)
  5. Mark the model `inference_ready` if sampling succeeds
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

from app.make_model.utils import now_iso, get_logger
from app.make_model.image.training.trainer import ImageTrainer, TrainingConfig
from app.make_model.image.dataset.acquire import acquire_image_dataset, load_image_arrays
from app.make_model.image.inference.sampler import ImageSampler, SamplerConfig
from app.make_model.image.registry_bridge import ImageRegistryBridge
from app.make_model.image.arch.unet import count_params


logger = get_logger("make_model.image.cli_train")


def main() -> int:
    parser = argparse.ArgumentParser(description="MAKE image training CLI")
    parser.add_argument("--steps", type=int, default=60, help="training steps")
    parser.add_argument("--image-size", type=int, default=32)
    parser.add_argument("--base-channels", type=int, default=24)
    parser.add_argument("--num-res-blocks", type=int, default=2)
    parser.add_argument("--num-timesteps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--procedural-count", type=int, default=512)
    parser.add_argument("--save-every", type=int, default=20)
    parser.add_argument("--log-every", type=int, default=5)
    parser.add_argument("--sample-after", action="store_true", help="Sample one image after training")
    parser.add_argument("--sample-prompt", type=str, default="a structured colored gradient")
    parser.add_argument("--sample-steps", type=int, default=30)
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--sample-out", type=str, default="")
    parser.add_argument("--registry-root", type=str, default="")
    parser.add_argument("--root", type=str, default="")
    args = parser.parse_args()

    root = args.root or os.environ.get("MAKE_MODEL_ROOT") or None
    if root:
        os.environ["MAKE_MODEL_ROOT"] = root
    logger.info(f"Starting MAKE image training: steps={args.steps} "
                f"image_size={args.image_size} base_channels={args.base_channels}")

    # 1. Acquire dataset
    info = acquire_image_dataset(
        out_root=root,
        target_size=args.image_size,
        procedural_count=args.procedural_count,
        seed=args.seed,
    )
    logger.info(f"Dataset acquired: kind={info.kind} files={info.num_files} source={info.source}")
    arr = load_image_arrays(info, target_size=args.image_size)
    logger.info(f"Loaded {arr.shape[0]} images at {args.image_size}x{args.image_size}")

    # 2. Register
    bridge = ImageRegistryBridge()
    from app.make_model.image.arch.unet import NumpyUNet, NumpyUNetConfig
    unet_cfg = NumpyUNetConfig(
        image_size=args.image_size,
        base_channels=args.base_channels,
        num_res_blocks=args.num_res_blocks,
        num_timesteps=args.num_timesteps,
    )
    # pre-init a model to count params
    _m = NumpyUNet(unet_cfg, seed=args.seed)
    n_params = count_params(_m)
    bridge.register_model(n_params, unet_cfg.to_dict())

    run_id = f"img-{int(time.time())}"
    cfg = TrainingConfig(
        image_size=args.image_size,
        base_channels=args.base_channels,
        num_res_blocks=args.num_res_blocks,
        num_timesteps=args.num_timesteps,
        batch_size=args.batch_size,
        max_steps=args.steps,
        save_every=args.save_every,
        learning_rate=args.learning_rate,
        log_every=args.log_every,
        seed=args.seed,
        dataset_kind=info.kind,
        dataset_name=info.name,
        dataset_manifest_sha=info.sha256_manifest,
        notes=f"CLI run, root={root}",
    )
    bridge.register_training_run(run_id, cfg.to_dict(), info.to_dict(), args.steps)

    # 3. Train
    trainer = ImageTrainer(cfg, out_root=root)
    result = trainer.train(arr, info.to_dict())

    # 4. Register checkpoint
    cp_record = bridge.register_checkpoint(
        checkpoint_path=result.checkpoint_path,
        training_run_id=run_id,
        config=cfg.to_dict(),
        dataset_info=info.to_dict(),
        global_step=result.steps_done,
        metric_summary={"final_loss": result.final_loss, "loss_curve": result.loss_curve},
        notes=f"elapsed_seconds={result.elapsed_seconds}",
    )

    bridge.finalize_training_run(run_id, result.steps_done, result.final_loss, result.checkpoint_path)

    # 5. Optional: sample
    if args.sample_after:
        sampler = ImageSampler(out_root=root)
        out_path = args.sample_out
        scfg = SamplerConfig(
            model_name=bridge.IMAGE_MODEL_NAME,
            checkpoint_path=result.checkpoint_path,
            prompt=args.sample_prompt,
            seed=args.sample_seed,
            num_inference_steps=args.sample_steps,
            image_size=args.image_size,
            output_path=out_path,
        )
        sres = sampler.sample(scfg)
        bridge.mark_inference_ready(sres.output_path, sres.output_sha256)
        logger.info(f"Sample written to {sres.output_path} ({sres.width}x{sres.height})")

    logger.info(f"Training complete. checkpoint={result.checkpoint_path} sha={result.checkpoint_sha256}")
    # Final JSON summary on stdout
    summary = {
        "ok": True,
        "run_id": run_id,
        "checkpoint_path": result.checkpoint_path,
        "checkpoint_sha256": result.checkpoint_sha256,
        "steps_done": result.steps_done,
        "final_loss": result.final_loss,
        "parameters": result.parameters,
        "dataset_kind": info.kind,
        "dataset_name": info.name,
        "dataset_manifest_sha": info.sha256_manifest,
        "elapsed_seconds": result.elapsed_seconds,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())