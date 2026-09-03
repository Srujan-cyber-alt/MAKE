"""
MAKE model CLI.

  python -m app.make_model.cli hardware
  python -m app.make_model.cli status
  python -m app.make_model.cli model-inspect
  python -m app.make_model.cli dataset prepare --config ...
  python -m app.make_model.cli dataset validate --manifest ...
  python -m app.make_model.cli train validate --config ...
  python -m app.make_model.cli train run --config ...
  python -m app.make_model.cli checkpoint verify --path ...
  python -m app.make_model.cli inference validate
  python -m app.make_model.cli inference run --config ...
  python -m app.make_model.cli audit
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from typing import Any

from app.make_model.utils import get_logger, load_json, load_yaml


logger = get_logger("make_model.cli")


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def _load(path: str) -> Any:
    if path.endswith((".yaml", ".yml")):
        return load_yaml(path)
    return load_json(path)


def cmd_hardware(_: argparse.Namespace) -> int:
    from app.make_model.training import detect_hardware
    _print(detect_hardware().to_dict())
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    from app.make_model.registry import get_registry
    _print(get_registry().get_status())
    return 0


def cmd_model_inspect(_: argparse.Namespace) -> int:
    from app.make_model.arch import (
        MakeModelConfig, architecture_smoke_test, list_arch_versions, create_model
    )
    cfg = MakeModelConfig()
    info = architecture_smoke_test(cfg)
    _print({
        "arch_versions": list_arch_versions(),
        "smoke_test": info,
        "config": cfg.to_dict(),
    })
    return 0 if info.get("ok") or info.get("reason") else 1


def cmd_dataset_prepare(args: argparse.Namespace) -> int:
    from app.make_model.dataset import DatasetConfig, prepare_dataset
    cfg = DatasetConfig.from_dict(_load(args.config))
    result = prepare_dataset(cfg)
    _print(result)
    return 0


def cmd_dataset_validate(args: argparse.Namespace) -> int:
    from app.make_model.dataset import load_manifest, validate_dataset
    m = load_manifest(args.manifest)
    report = validate_dataset(m, require_caption=args.require_caption)
    _print(report)
    return 0 if report["error_count"] == 0 else 1


def cmd_train_validate(args: argparse.Namespace) -> int:
    from app.make_model.training import TrainingConfig, validate_training_readiness
    cfg = TrainingConfig.from_dict(_load(args.config))
    _print(validate_training_readiness(cfg, dataset_manifest_path=args.dataset_manifest or ""))
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from app.make_model.training import TrainingConfig, TrainingRun
    cfg = TrainingConfig.from_dict(_load(args.config))
    dataset_manifest = None
    if cfg.dataset_manifest and os.path.exists(cfg.dataset_manifest):
        dataset_manifest = load_json(cfg.dataset_manifest)
    run = TrainingRun(cfg, cfg.arch_config)
    summary = run.run(dataset_manifest=dataset_manifest)
    _print(summary)
    return 0


def cmd_checkpoint_verify(args: argparse.Namespace) -> int:
    from app.make_model.training import CheckpointManager
    _print(CheckpointManager(".").verify(args.path))
    return 0


def cmd_inference_validate(_: argparse.Namespace) -> int:
    from app.make_model.inference import inference_availability
    _print(inference_availability())
    return 0


def cmd_inference_run(args: argparse.Namespace) -> int:
    from app.make_model.inference import MakeInferenceEngine, MakeInferenceRequest
    cfg = MakeInferenceRequest(**load_json(args.config))
    engine = MakeInferenceEngine()
    result = engine.run(cfg)
    _print(result.to_dict())
    return 0 if result.ok else 1


def cmd_audit(_: argparse.Namespace) -> int:
    from app.make_model.audit import run_ownership_audit
    _print(run_ownership_audit())
    return 0


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser("make_model")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hardware").set_defaults(func=cmd_hardware)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("model-inspect").set_defaults(func=cmd_model_inspect)

    p = sub.add_parser("dataset")
    ssub = p.add_subparsers(dest="subcmd", required=True)
    s1 = ssub.add_parser("prepare"); s1.add_argument("--config", required=True); s1.set_defaults(func=cmd_dataset_prepare)
    s2 = ssub.add_parser("validate"); s2.add_argument("--manifest", required=True)
    s2.add_argument("--require-caption", action="store_true"); s2.set_defaults(func=cmd_dataset_validate)

    p = sub.add_parser("train")
    ssub = p.add_subparsers(dest="subcmd", required=True)
    s1 = ssub.add_parser("validate"); s1.add_argument("--config", required=True)
    s1.add_argument("--dataset-manifest", default=""); s1.set_defaults(func=cmd_train_validate)
    s2 = ssub.add_parser("run"); s2.add_argument("--config", required=True); s2.set_defaults(func=cmd_train)

    p = sub.add_parser("checkpoint")
    ssub = p.add_subparsers(dest="subcmd", required=True)
    s1 = ssub.add_parser("verify"); s1.add_argument("--path", required=True); s1.set_defaults(func=cmd_checkpoint_verify)

    p = sub.add_parser("inference")
    ssub = p.add_subparsers(dest="subcmd", required=True)
    ssub.add_parser("validate").set_defaults(func=cmd_inference_validate)
    s1 = ssub.add_parser("run"); s1.add_argument("--config", required=True); s1.set_defaults(func=cmd_inference_run)

    sub.add_parser("audit").set_defaults(func=cmd_audit)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
