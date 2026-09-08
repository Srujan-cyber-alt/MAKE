"""Tests for MAKE Autonomous Agent Core V2 — Real Process Crash Recovery."""

import pytest
import subprocess
import sys
import os

from uuid import UUID


class TestRealProcessCrashRecovery:
    def test_real_process_crash_recovery(self):
        db_path = "test_real_crash.db"
        script = os.path.join(os.path.dirname(__file__), "recovery_script.py")
        python = sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "..") + os.pathsep + env.get("PYTHONPATH", "")
        create_proc = subprocess.run(
            [python, script, "create", db_path],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            env=env
        )
        assert create_proc.returncode == 0, f"Create failed: {create_proc.stderr}"
        parts = create_proc.stdout.strip().split()
        assert parts[0] == "CREATED"
        job_id, execution_id = parts[1], parts[2]
        recover_proc = subprocess.run(
            [python, script, "recover", db_path, job_id, execution_id],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
            env=env
        )
        assert recover_proc.returncode == 0, f"Recover failed: {recover_proc.stderr}"
        assert "RECOVERED" in recover_proc.stdout
