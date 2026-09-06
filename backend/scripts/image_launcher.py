#!/usr/bin/env python3
"""MAKE Image Engine — Launcher."""

from __future__ import annotations

import argparse
import sys


def cmd_train(args: argparse.Namespace) -> int:
    print("Image training launcher")
    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    from app.make_model.image.inference import ImageInferenceEngine, ImageInferenceRequest
    engine = ImageInferenceEngine()
    req = ImageInferenceRequest(prompt=args.prompt, short_side=args.short_side, seed=args.seed)
    result = engine.run(req)
    if result.ok:
        print(f"[OK] {result.output_path}")
        return 0
    print(f"[FAILED] {result.code}: {result.message}")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    print("{\"status\": \"ok\", \"service\": \"make-image\"}")
    return 0


def main():
    parser = argparse.ArgumentParser("MAKE Image Launcher")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_train = sub.add_parser("train")
    p_train.add_argument("--config", default="configs/image_tiny.json")

    p_infer = sub.add_parser("infer")
    p_infer.add_argument("--prompt", default="cinematic portrait")
    p_infer.add_argument("--short-side", type=int, default=256)
    p_infer.add_argument("--seed", type=int, default=42)

    sub.add_parser("status").set_defaults(func=cmd_status)

    args = parser.parse_args()
    if args.cmd == "train":
        return cmd_train(args)
    elif args.cmd == "infer":
        return cmd_infer(args)
    elif args.cmd == "status":
        return cmd_status(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
