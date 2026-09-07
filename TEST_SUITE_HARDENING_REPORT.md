# Test Suite Hardening Report

## 1. Goal

Bring the backend pytest suite to a clean, reproducible state — eliminating
configuration / fixture bugs that caused cascading failures and verifying that
the existing test suite actually exercises the application.

## 2. Starting state

- `pytest backend/tests/` — collection errors (no Postgres running).
- After installing deps into a usable Python 3.10 venv: **45 failed, 8 passed**.
- Two recurring root causes: (a) tests did not load `.env` from
  `backend/.env`, (b) the in-process TestClient did not initialise the
  SQLite schema.

## 3. Fixes Applied

### 3.1 `backend/tests/conftest.py`
- Load `backend/.env` into `os.environ` at conftest import time so SQLite is
  selected automatically.
- Set `TESTING=true` so `app.core.rate_limit` raises the auth/register
  rate limit from `3/hour` to `1000/hour`, allowing dozens of test users.
- Per-session fresh sqlite DB file (`make_test_<uuid>.db`) under
  `backend/` to avoid state pollution between runs.
- Autouse session fixture that calls `app.core.database.init_db()` to
  create tables on first use.
- Renamed ambiguous leading positional parameter from `_client` to
  `test_client` in `get_auth_headers`, `create_project`, `upload_asset`,
  and reordered `create_project` / `upload_asset` so `headers` is the
  first parameter (callers pass headers positionally in many places).
- `get_auth_headers` now hits `/api/v1/auth/token` with form data
  (matches the actual FastAPI route — previously used `/auth/login`
  with JSON body which returned 404).
- `upload_asset` now posts to `/api/v1/assets/upload` (the real endpoint).

### 3.2 Test-file caller fixes
Across `test_api.py`, `test_director.py`, `test_e2e.py`,
`test_phase7.py` … `test_phase22.py`, `test_studio.py`,
`test_transformation.py`:
- `get_auth_headers("email@x", "pw")` → `get_auth_headers(email="email@x", password="pw")`.
- `create_project(headers, "Name")` → `create_project(headers=headers, name="Name")`.
- `upload_asset(headers, project["id"], "x.mp4")` →
  `upload_asset(headers=headers, project_id=project["id"], name="x.mp4")`
  (or `filename="x.mp4"` for `test_transformation.py` which has a local
  helper).

### 3.3 `backend/app/make_model/world/audit.py`
`run_world_ownership_audit()` previously used `os.path.exists("app/...")`
which depends on the process CWD. When pytest was invoked from the
project root (the only way `rootdir = backend/` works), the audit
returned verdict `"NO"` instead of `"PARTIAL"`. Replaced with absolute
paths derived from `os.path.dirname(__file__)`.

### 3.4 `backend/tests/test_transformation.py`
This file defines its own local `upload_asset(headers, project_id,
filename=...)`. A test used `name=` (the conftest parameter name).
Updated call sites to use `filename=`.

## 4. Final Results

```
$ PYTHONPATH=backend:backend/.venv/lib/python3.10/site-packages \
    python3.10 backend/.venv/bin/pytest backend/tests/ -q -p no:warnings

455 passed, 12 skipped, 2 failed in 129s
```

### 4.1 Remaining failures (environment-only, not code)

| Test | Reason |
|------|--------|
| `test_local_provider::test_real_local_generation_produces_artifact` | ffmpeg lacks `drawtext` filter (libfreetype not compiled) |
| `test_local_provider::test_real_local_generation_provenance` | same |

These tests skip automatically when ffmpeg is unavailable, but the
container ffmpeg binary is the `imageio-ffmpeg` minimal build which
omits libfreetype. Not a regression — same behaviour before fixes.

### 4.2 Improvements vs baseline

| Metric | Before | After |
|--------|--------|-------|
| Passing | 8 | **455** |
| Failing | 45 | 2 (env-only) |
| Skipped | — | 12 |
| Collection errors | 13 | 0 |

## 5. Files Touched

- `backend/tests/conftest.py` (rewritten helpers)
- `backend/app/make_model/world/audit.py` (absolute paths)
- 19 test files (call-site fixes only — no behaviour change in tests)

## 6. How to run

```bash
PYTHONPATH=backend:backend/.venv/lib/python3.10/site-packages \
  /usr/bin/python3.10 backend/.venv/bin/pytest backend/tests/
```

Or, with a normal Python environment where deps are installed
system-wide and Postgres is available:

```bash
cd backend && pytest
```

## 7. Future work (out of scope for this pass)

- The 2 ffmpeg `drawtext` failures can only be resolved by rebuilding
  ffmpeg with `--enable-libfreetype` or installing the full
  `ffmpeg` package in the container.
- The `.venv/` `__pycache__` directories are tracked in git — adding
  `__pycache__/` and `*.pyc` to `.gitignore` would prevent the next
  test run from churning thousands of unrelated files.
