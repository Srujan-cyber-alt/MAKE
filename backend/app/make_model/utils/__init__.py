"""
Shared utilities for the MAKE model program.

- paths() : canonical, configurable filesystem locations
- seeding() : deterministic seed
- sha256_file() : integrity hashing for checkpoints
- now_iso() : canonical timestamp
- load_yaml() / dump_yaml() : config I/O
- get_logger() : standard project logger
"""

from __future__ import annotations
import os
import json
import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_ROOT = os.environ.get(
    "MAKE_MODEL_ROOT", "/tmp/make_model_artifacts"
)


def paths(root: Optional[str] = None) -> Dict[str, Path]:
    """Return canonical paths for the MAKE model program."""
    base = Path(root or DEFAULT_ROOT)
    return {
        "root": base,
        "checkpoints": base / "checkpoints",
        "datasets": base / "datasets",
        "runs": base / "runs",
        "exports": base / "exports",
        "logs": base / "logs",
        "registry": base / "registry.json",
    }


def ensure_dirs(root: Optional[str] = None) -> Dict[str, Path]:
    p = paths(root)
    for k, v in p.items():
        if isinstance(v, Path):
            v.mkdir(parents=True, exist_ok=True)
    return p


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def deterministic_seed(seed: Optional[int]) -> int:
    if seed is None:
        return secrets.randbits(31)
    return int(seed) & 0x7FFFFFFF


def dump_json(path: str | Path, data: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, sort_keys=True)


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_yaml(path: str | Path, data: Any) -> None:
    """Minimal YAML writer. Avoids requiring PyYAML. Good enough for flat configs."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    lines = []

    def _emit(obj: Any, indent: int = 0) -> None:
        pad = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)) and v:
                    lines.append(f"{pad}{k}:")
                    _emit(v, indent + 1)
                else:
                    lines.append(f"{pad}{k}: {_fmt_scalar(v)}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    lines.append(f"{pad}-")
                    _emit(item, indent + 1)
                else:
                    lines.append(f"{pad}- {_fmt_scalar(item)}")
        else:
            lines.append(f"{pad}{_fmt_scalar(obj)}")

    def _fmt_scalar(v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        if any(c in s for c in [":", "#", "\n", '"', "'"]):
            return json.dumps(s)
        return s

    _emit(data)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def load_yaml(path: str | Path) -> Any:
    """Minimal YAML reader. Good enough for flat configs written by dump_yaml."""
    with open(path, "r", encoding="utf-8") as f:
        return _parse_yaml(f.read())


def _parse_yaml(text: str) -> Any:
    # Conservative parser: nested mappings only. Sufficient for the configs
    # we author. NOT a general-purpose YAML parser.
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        lines.append((indent, raw.strip()))

    root: Any = {}
    stack = [(-1, root)]
    for indent, line in lines:
        if line.startswith("- "):
            value = line[2:].strip()
            parent = stack[-1][1]
            if not isinstance(parent, list):
                if isinstance(stack[-2][1], list) and stack[-1][0] == indent:
                    parent = stack[-2][1]
                else:
                    parent = []
                    stack[-2][1] = parent
            parent.append(_parse_scalar(value))
            stack.append((indent, parent[-1]))
        else:
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1]
            if val == "":
                # nested
                new = {} if ":" in _peek_child(lines, indent) else []
                if isinstance(parent, list):
                    if isinstance(parent[-1], dict):
                        parent[-1][key] = new
                    stack.append((indent, new))
                else:
                    parent[key] = new
                    stack.append((indent, new))
            else:
                if isinstance(parent, list):
                    if isinstance(parent[-1], dict):
                        parent[-1][key] = _parse_scalar(val)
                else:
                    parent[key] = _parse_scalar(val)
    return root


def _peek_child(lines, indent: int) -> str:
    for i, (ind, _) in enumerate(lines):
        if ind > indent:
            return lines[i][1]
    return ""


def _parse_scalar(s: str) -> Any:
    if s == "" or s.lower() in ("null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        if "." in s or "e" in s or "E" in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def get_logger(name: str) -> logging.Logger:
    logger_ = logging.getLogger(name)
    if not logger_.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger_.addHandler(handler)
        logger_.setLevel(logging.INFO)
    return logger_


def human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"
