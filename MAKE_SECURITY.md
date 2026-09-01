# MAKE SECURITY

## Authentication
- JWT-based authentication via `/api/v1/auth/token`
- Protected routes use `Depends(get_current_user)`
- 401 responses redirect to `/login`

## Authorization
- Project ownership verified before every operation
- Asset ownership tied to project
- Job isolation per user

## Upload Validation
- File type checked via `content_type`
- File size limited by infrastructure
- Path traversal blocked (storage uses UUID-prefixed paths)
- MIME type validation recommended for production

## FFmpeg Safety
- FFmpeg commands built with fixed arguments
- No user input injected into shell commands
- `apply_filter` uses parameterized filter strings

## Provider Secrets
- API keys stored server-side only in `Settings`
- Never exposed to frontend
- Never logged

## Rate Limiting
- `slowapi` with configurable limits
- Default: 1000 requests/minute general, 1000/hour generation

## Error Messages
- Internal stack traces not exposed to users
- Generic error messages returned
- Detailed errors logged server-side

## Audit Logging
- Job creation tracked
- Provider calls logged
- Errors logged with context

## CORS
- Configured in `main.py`
- Production should restrict origins

## Recommendations
1. Replace default secrets in `config.py` with strong random values
2. Restrict CORS origins in production
3. Add file hash verification for uploads
4. Implement rate limiting per-user
5. Add audit log persistence
6. Encrypt API keys at rest
