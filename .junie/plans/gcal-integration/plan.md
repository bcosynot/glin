### Google Calendar Integration Plan (OAuth 2.0 — Installed App with loopback redirect)

Last updated: 2025-10-20 01:33 (local)

Scope
- Implement a read-only MVP that authenticates with Google via OAuth 2.0 Installed App (loopback/localhost redirect) and exposes an MCP tool to list calendar events within a date/time range for the signed-in user.
- Align with repository conventions (FastMCP tools, TypedDict returns, env/config precedence, storage in SQLite, Ruff formatting/lint).

Authoritative references (Context7)
- Google Auth Python Library (official): `/googleapis/google-auth-library-python`
  - Installed-app flows via `google-auth-oauthlib` `InstalledAppFlow.run_local_server()` (loopback redirect), automatic refresh with `google.oauth2.credentials.Credentials`.
- Google API Python Client (official): `/googleapis/google-api-python-client`
  - Calendar v3: `build("calendar", "v3", credentials=...)` and `events().list(...)`.
- Notes:
  - Loopback redirect URIs follow RFC8252 best practice: use 127.0.0.1 with a random port; `InstalledAppFlow.run_local_server(port=0)` manages spinning up a temporary local HTTP server and exchanges authorization code for tokens.

High-level design
- New package: `glin/calendar_tools/`
  - `auth.py` — loopback OAuth helper using `google-auth-oauthlib` with token load/refresh/store.
  - `google.py` — thin client around Calendar API v3 with retry/backoff and types.
  - `mcp.py` — MCP-exposed tools that call `google.py` and return JSON-friendly TypedDicts.
- Storage: add `oauth_tokens` table to SQLite for provider-scoped refresh tokens and metadata (migration in `glin/storage/db.py`).
- Config: env vars and `glin.toml` keys for client credentials, auth method, scopes (mirrors `glin.config` patterns).
- MVP tools (read-only):
  - `google_calendar_list_calendars()`
  - `google_calendar_list_events(calendar_id: str, start: str, end: str, time_zone?: str)`
  - `google_calendar_auth_start(method: "loopback")` and `google_calendar_revoke()` (optional for MVP; nice-to-have)

Detailed plan
1) Dependencies and versions
- Add (runtime):
  - `google-auth>=2.0.0`
  - `google-auth-oauthlib>=1.2.0`
  - `google-api-python-client>=2.0.0`
- Add (dev): none beyond existing.
- Wire into `pyproject.toml` and `uv.lock` via `uv sync --group dev`.

2) Configuration keys and resolution (mirror glin.config precedence)
- Env vars (highest priority):
  - `GLIN_GOOGLE_CLIENT_ID`
  - `GLIN_GOOGLE_CLIENT_SECRET`
  - `GLIN_GOOGLE_AUTH_METHOD` = `loopback` | `device` (default `loopback` for this plan)
  - `GLIN_GOOGLE_SCOPES` (space-separated; default `https://www.googleapis.com/auth/calendar.readonly`)
- glin.toml (fallback):
  ```toml
  [google]
  auth_method = "loopback"
  client_id = "..."
  client_secret = "..."
  scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
  ```
- Helpers (in a new `glin/calendar_tools/config.py` or folded into `glin/config.py`):
  - `get_google_oauth_config() -> GoogleOAuthConfig` (TypedDict/dataclass) resolving with env > file.

3) OAuth consent setup in Google Cloud Console
- Create an OAuth client of type "Desktop app" (best for loopback). For iOS native, a separate iOS client may be created later (not needed for MCP server).
- Scopes: start with read-only `calendar.readonly`.
- Loopback redirect URIs: Desktop client type automatically supports `http://127.0.0.1` with random ports when using InstalledAppFlow; no manual URI entries required for Desktop.

4) Token storage schema (SQLite)
- Add table `oauth_tokens` (migration in `glin/storage/db.py`):
  - `id` INTEGER PK
  - `provider` TEXT NOT NULL (e.g., "google")
  - `subject` TEXT NOT NULL (Google account email or `sub`)
  - `scopes` TEXT NOT NULL (space-separated)
  - `refresh_token` TEXT NOT NULL
  - `token_type` TEXT NOT NULL DEFAULT "Bearer"
  - `expires_at` TEXT NULL (UTC ISO for last access token expiry if stored)
  - `created_at` TEXT NOT NULL
  - `updated_at` TEXT NOT NULL
  - `meta_json` TEXT NULL (e.g., `id_token` claims snapshot)
  - UNIQUE(provider, subject)
- Consider storing only refresh token; compute access token on demand via refresh.
- Add CRUD helpers in `glin/storage/tokens.py`:
  - `get_provider_token(provider: str, subject?: str | None) -> OAuthTokenRow | None`
  - `upsert_provider_token(row: OAuthTokenRowInput) -> None`
  - `delete_provider_tokens(provider: str, subject?: str | None) -> int`

5) Auth implementation (loopback)
- `glin/calendar_tools/auth.py`:
  - `SCOPES_DEFAULT = ["https://www.googleapis.com/auth/calendar.readonly"]`
  - `get_credentials_via_loopback(config: GoogleOAuthConfig, scopes: list[str]) -> Credentials`
    - Use `InstalledAppFlow.from_client_config({...}, scopes=scopes)` with `redirect_uris` including `http://127.0.0.1`.
    - Call `flow.run_local_server(port=0, authorization_prompt_message=None, success_message="Authentication complete. You may close this window.", open_browser=True)`.
    - On success, extract `creds.refresh_token`, `creds.id_token`, `creds.expiry` and subject (decode `id_token` or call `userinfo` endpoint if necessary), then persist via storage helpers.
  - `load_credentials() -> Credentials | None` that reconstructs credentials from stored refresh token using `Credentials.from_authorized_user_info`-like pattern:
    ```python
    Credentials(
      token=None,
      refresh_token=row.refresh_token,
      token_uri="https://oauth2.googleapis.com/token",
      client_id=config.client_id,
      client_secret=config.client_secret,
      scopes=scopes,
    )
    ```
  - `ensure_credentials(scopes: list[str]) -> Credentials | ErrorResponse` loading/refreshing and triggering auth if missing or revoked (returns structured error instructing the caller to run the auth tool).
  - `revoke_and_clear()` hitting `https://oauth2.googleapis.com/revoke` for the refresh token then deleting the row.

6) Google Calendar client wrapper
- `glin/calendar_tools/google.py`:
  - Types:
    ```python
    class GCalCalendar(TypedDict):
        id: str
        summary: str
        primary: bool

    class TimeRange(TypedDict):
        start: str  # RFC3339
        end: str    # RFC3339

    class GCalEvent(TypedDict, total=False):
        id: str
        summary: str
        description: str
        start: dict  # {"dateTime": ..., "timeZone": ...}
        end: dict
        htmlLink: str

    class ErrorResponse(TypedDict):
        error: str
        retry_after: float
    ```
  - `build_service(creds: Credentials)` → `googleapiclient.discovery.build("calendar", "v3", credentials=creds, cache_discovery=False)`
  - `list_calendars(creds) -> list[GCalCalendar] | ErrorResponse`
  - `list_events(creds, calendar_id, start, end, time_zone=None, page_token=None, page_size=2500) -> list[GCalEvent] | ErrorResponse`
  - Add simple retry/backoff for HTTP 429/5xx with jitter.

7) MCP tools
- `glin/calendar_tools/mcp.py` (imported by `glin/mcp_app.py`):
  - `@mcp.tool(name="google_calendar_list_calendars", ...) -> list[GCalCalendar] | ErrorResponse`
  - `@mcp.tool(name="google_calendar_list_events", ...) -> list[GCalEvent] | ErrorResponse`
  - Optional:
    - `@mcp.tool(name="google_calendar_auth_start", ...)` to force auth flow and store tokens.
    - `@mcp.tool(name="google_calendar_revoke", ...)` to revoke/clear tokens.
- Follow logging/Context patterns used in `glin/git_tools/commits.py` (ctx.info/ctx.log/ctx.error). Redact secrets.

8) Error handling and UX
- If no OAuth config is present, return `{"error": "Missing Google OAuth client credentials"}` with a concise remediation hint.
- If no stored token, return `{"error": "Not authenticated. Run google_calendar_auth_start."}`.
- On 401/invalid_grant, attempt one automatic refresh; if still failing, clear stored access token (retain refresh token if valid) or prompt re-auth.

9) Testing strategy
- No live network. Patch:
  - OAuth: monkeypatch `InstalledAppFlow.run_local_server` to return a fake `Credentials` with a refresh token.
  - Calendar API: monkeypatch `googleapiclient.discovery.build` and its `events().list(...).execute()` chain to return deterministic dicts.
- Storage migration test: create DB in tmp, apply migration adding `oauth_tokens`, CRUD roundtrip via `glin/storage/tokens.py`.
- MCP tool tests: validate shapes, error surfaces, and that secrets are not logged.
- Use `pytest` with existing repo patterns (see `tests/test_git_tools.py` for patching style).

10) Security and privacy
- Minimal scopes by default (`calendar.readonly`).
- Never log `access_token` or `refresh_token`. Redact headers and responses in logs.
- Provide `revoke` tool to clean up tokens.
- File permissions: ensure SQLite path remains user-readable only (inherit repo defaults). Consider future OS keyring integration.

11) Rollout plan (MVP → next)
- MVP (this task): list calendars + list events via loopback auth, read-only.
- Next:
  - Device Flow alternative for headless contexts.
  - Create/update/delete events (scoped accordingly) and optional worklog export.
  - Domain/workspace service accounts (advanced/optional).

12) Developer workflow
- Setup:
  - `uv sync --group dev`
  - Set env vars for client credentials or add them to `glin.toml`.
  - Run `make run-stdio` and call `google_calendar_auth_start` tool to complete consent in a browser (auto-callback to localhost).
- Query events:
  - Call `google_calendar_list_calendars` to pick a calendar.
  - Call `google_calendar_list_events(calendar_id, start, end)` with RFC3339 timestamps.

Appendix: Example code snippets (illustrative)
- Auth (loopback):
  ```python
  from google.oauth2.credentials import Credentials
  from google_auth_oauthlib.flow import InstalledAppFlow

  def get_credentials_via_loopback(client_id: str, client_secret: str, scopes: list[str]):
      flow = InstalledAppFlow.from_client_config(
          {
              "installed": {
                  "client_id": client_id,
                  "client_secret": client_secret,
                  "redirect_uris": ["http://127.0.0.1"],
                  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                  "token_uri": "https://oauth2.googleapis.com/token",
              }
          },
          scopes=scopes,
      )
      creds = flow.run_local_server(port=0)
      return creds
  ```
- Calendar list:
  ```python
  from googleapiclient.discovery import build

  def list_calendars(creds):
      svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
      res = svc.calendarList().list().execute()
      return [
          {
              "id": it["id"],
              "summary": it.get("summary", ""),
              "primary": bool(it.get("primary")),
          }
          for it in res.get("items", [])
      ]
  ```
- Events list:
  ```python
  def list_events(creds, calendar_id: str, start: str, end: str, time_zone: str | None = None):
      svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
      kwargs = {"calendarId": calendar_id, "timeMin": start, "timeMax": end, "singleEvents": True, "orderBy": "startTime"}
      if time_zone:
          kwargs["timeZone"] = time_zone
      res = svc.events().list(**kwargs).execute()
      return res.get("items", [])
  ```
