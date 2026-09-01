# MAKE AI VIDEO — TESTING
## Test Suite Documentation

============================================================
BACKEND TESTS
============================================================

**Location:** `backend/tests/`

**Test Files:**
- `test_api.py` — API integration tests (16 test classes, 30+ test cases)
- `test_providers.py` — Provider abstraction tests (6 test classes, 15+ test cases)

**Run:**
```bash
cd backend
pytest -v
```

**Coverage Areas:**
- Health endpoints
- Authentication (register, login, duplicate email, invalid password)
- Projects (CRUD, not found, ownership)
- Assets (upload, list, delete)
- Jobs (create, list, cancel)
- Providers (list, health, capabilities, registry)
- Versions (create, list, restore)
- References (add, list)
- Context (update, get)
- Timelines (create, list)
- Security (cross-user access, unauthorized access)
- Generation workflow (validation, provider/model selection)
- Provider registry (register, get, get_all, get_by_capability, get_provider_model)
- Model discovery (limits, capabilities)
- Command interpreter (remove, replace, action, captions, extension, unknown)

**Test Database:**
- SQLite in-memory (`sqlite+aiosqlite:///./test.db`)
- Automatic schema creation/teardown
- No external dependencies required

============================================================
FRONTEND TESTS
============================================================

**Location:** `frontend/src/__tests__/`

**Test Files:**
- `Login.test.tsx` — Login form rendering
- `Dashboard.test.tsx` — Dashboard rendering

**Run:**
```bash
cd frontend
npm test
```

============================================================
TEST PROVIDER
============================================================

`TestVideoProvider` (`app/providers/test_provider.py`) provides deterministic behavior for automated tests:
- Simulates generation accepted → processing → completed
- Configurable failure simulation
- No external API calls
- Never exposed as production model

============================================================
INTEGRATION TEST WORKFLOW
============================================================

The following end-to-end workflow is tested:
1. Register user
2. Login
3. Create project
4. Upload asset
5. Create generation job with provider/model
6. Verify job queued with correct provider/model
7. Create timeline
8. Add reference asset
9. Update project context
10. Create version
11. Verify cross-user access denied

============================================================
MANUAL VERIFICATION CHECKLIST
============================================================

- [ ] Backend starts without errors
- [ ] Frontend builds without errors
- [ ] Database migrations apply cleanly
- [ ] User registration works
- [ ] User login works
- [ ] Project creation works
- [ ] Asset upload works
- [ ] Job creation works
- [ ] Provider list returns data
- [ ] Version creation works
- [ ] Reference management works
- [ ] Timeline CRUD works
- [ ] File serving works
- [ ] Rate limiting returns 429
- [ ] Cross-user access denied
- [ ] Invalid JWT rejected
