"""Test conftest: ensure ffmpeg and imageio_ffmpeg are available."""

import os
import shutil
import subprocess

import pytest


def _resolve_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


@pytest.fixture(autouse=True)
def _ensure_ffmpeg_in_path(monkeypatch, tmp_path):
    ffmpeg = _resolve_ffmpeg()
    if ffmpeg and ffmpeg != "ffmpeg":
        # symlink into a temp bin dir and prepend to PATH
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir(exist_ok=True)
        link = bin_dir / "ffmpeg"
        try:
            os.symlink(ffmpeg, str(link))
        except Exception:
            pass
        env_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", env_path)
    yield
