#!/usr/bin/env python3
"""
Audio crash recovery subprocess.

Simulates an audio generation job that gets interrupted by a process kill.
The job state is persisted to a JSON checkpoint file so it can be resumed.

Usage:
    python tests/audio/recovery_script.py --job-id <id> --checkpoint <path>
"""

import argparse
import io
import json
import os
import sys
import time
import hashlib
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path


def run_generation_step(checkpoint_path: str, job_id: str, stage: str) -> None:
    checkpoint = {
        "job_id": job_id,
        "stage": stage,
        "timestamp": time.time(),
        "checkpoint_path": checkpoint_path,
    }
    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint, f, indent=2)


def generate_audio(seed: int, duration: float = 2.0) -> bytes:
    sr = 16000
    rng = np.random.RandomState(seed)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freq = 220.0 + rng.randn() * 20
    audio = 0.3 * np.sin(2 * np.pi * freq * t)
    audio += 0.05 * rng.randn(len(t))
    audio_int = (audio * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sr, audio_int)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--kill-after", type=float, default=0.5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Phase 1: initialize
    run_generation_step(args.checkpoint, args.job_id, "initialized")

    # Phase 2: generate (may get killed here)
    time.sleep(args.kill_after)
    run_generation_step(args.checkpoint, args.job_id, "generating")

    # Phase 3: complete
    audio_data = generate_audio(args.seed)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(audio_data)

    sha = hashlib.sha256(audio_data).hexdigest()

    checkpoint = {
        "job_id": args.job_id,
        "stage": "completed",
        "timestamp": time.time(),
        "checkpoint_path": args.checkpoint,
        "output_path": args.output,
        "output_sha256": sha,
        "seed": args.seed,
    }
    with open(args.checkpoint, "w") as f:
        json.dump(checkpoint, f, indent=2)

    print(json.dumps({"status": "completed", "output": args.output, "sha256": sha}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
