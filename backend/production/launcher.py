#!/usr/bin/env python3
"""MAKE Foundation 5B — iPhone-Operable Launcher.

Single entrypoint for training, inference, dataset acquisition, and status.
Designed to be invoked remotely via SSH from iOS or any terminal.

Usage:
    python production/launcher.py train
    python production/launcher.py infer --checkpoint outputs/final_model.pt
    python production/launcher.py dataset --source pixabay --max-clips 100
    python production/launcher.py status
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def cmd_train(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable, '-m', 'production.train',
        '--config', args.config,
    ]
    if args.resume:
        cmd.extend(['--resume', args.resume])
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def cmd_infer(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable, '-m', 'production.inference',
        '--checkpoint', args.checkpoint,
        '--prompt', args.prompt,
        '--frames', str(args.frames),
        '--short-side', str(args.short_side),
        '--fps', str(args.fps),
        '--steps', str(args.steps),
        '--seed', str(args.seed),
        '--cfg-scale', str(args.cfg_scale),
        '--output', args.output,
        '--resolution', str(args.resolution),
    ]
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def cmd_dataset(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable, '-m', 'production.dataset',
        '--source', args.source,
        '--max-clips', str(args.max_clips),
        '--output', args.output,
    ]
    if args.api_key:
        cmd.extend(['--api-key', args.api_key])
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def cmd_status(args: argparse.Namespace) -> int:
    status = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'python': sys.version,
        'cuda_available': False,
        'model_checkpoints': [],
        'outputs': [],
        'dataset_clips': 0,
    }
    try:
        import torch
        status['cuda_available'] = torch.cuda.is_available()
        if torch.cuda.is_available():
            status['gpu_name'] = torch.cuda.get_device_name(0)
            status['gpu_vram_gb'] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
    except ImportError:
        pass
    for f in Path('outputs').glob('*.pt'):
        status['model_checkpoints'].append(str(f))
    for f in Path('.').glob('cinematic_*.mp4'):
        status['outputs'].append(str(f))
    manifest = Path('dataset/manifest.json')
    if manifest.exists():
        try:
            with open(manifest) as fh:
                data = json.load(fh)
            status['dataset_clips'] = data.get('total_clips', 0)
        except Exception:
            pass
    print(json.dumps(status, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser("MAKE Launcher")
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_train = sub.add_parser('train')
    p_train.add_argument('--config', default='production/configs/production_5b.json')
    p_train.add_argument('--resume', default=None)

    p_infer = sub.add_parser('infer')
    p_infer.add_argument('--checkpoint', required=True)
    p_infer.add_argument('--prompt', default='cinematic video, photorealistic human, IMAX quality')
    p_infer.add_argument('--frames', type=int, default=24)
    p_infer.add_argument('--short-side', type=int, default=256)
    p_infer.add_argument('--fps', type=int, default=24)
    p_infer.add_argument('--steps', type=int, default=30)
    p_infer.add_argument('--seed', type=int, default=42)
    p_infer.add_argument('--cfg-scale', type=float, default=3.0)
    p_infer.add_argument('--output', default='cinematic_output.mp4')
    p_infer.add_argument('--resolution', type=int, default=1024)

    p_dataset = sub.add_parser('dataset')
    p_dataset.add_argument('--source', required=True, choices=['pixabay', 'pexels', 'coverr', 'videvo'])
    p_dataset.add_argument('--max-clips', type=int, default=100)
    p_dataset.add_argument('--output', default='./dataset')
    p_dataset.add_argument('--api-key', default=None)

    sub.add_parser('status').set_defaults(func=cmd_status)

    args = parser.parse_args()
    if args.cmd == 'train':
        return cmd_train(args)
    elif args.cmd == 'infer':
        return cmd_infer(args)
    elif args.cmd == 'dataset':
        return cmd_dataset(args)
    elif args.cmd == 'status':
        return cmd_status(args)
    return 1


if __name__ == '__main__':
    sys.exit(main())
