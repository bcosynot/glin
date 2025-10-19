# Plan: Execute Git commands in the caller's workspace (not the MCP server directory)

Last updated: 2025-10-19 02:27 (local)
Owner: Junie (JetBrains)

## Problem
When the MCP server executes Git operations, subprocess calls run in the server process working directory. For coding assistants, the intended behavior is to run Git in the caller's current workspace (the repo where the user is working). This mismatch causes wrong repo context, empty results, or errors when the server code directory is not a Git repo or is a different repo.

## Goals
- Ensure every Git subprocess runs in the user's workspace root directory (the assistant's invocation context), not the server code directory.
- Provide an explicit, testable, and overrideable mechanism to determine the effective working directory (EWD) for Git.
- Maintain backward compatibility for existing tool APIs and tests.
- Keep behavior deterministic and hermetic in unit tests.

## Non-goals
- Changing high-level tool APIs beyond an optional configuration tool to set the workspace directory.
- Introducing remote execution or network access.

## Constraints and context
- Current calls are scattered across:
  - glin/config.py (git config lookups)
  - glin/git_tools/*.py: analysis.py, branches.py, commits.py, config_tools.py, diffs.py, files.py, remotes.py, sessions.py
- All use subprocess.run([...]) without cwd, implicitly using the server process CWD.
- Tests patch subprocess or high-level helpers; they should remain stable with a small shim.

## Proposed solution
Introduce a single source of truth for the working directory and a tiny execution wrapper.

1) Workspace directory resolution
   Implement get_effective_cwd() with this precedence:
   1. Environment variable GLIN_WORKDIR (absolute path). Primary mechanism for clients.
   2. Session-scoped value set via a new MCP tool configure_workspace_root(path: str). Stored in-process (e.g., glin.git_tools.sessions or a new module-level holder). This covers transports that can send an initial setup call.
   3. Fallback: process CWD (Path.cwd()). Used only if (1) and (2) are absent — still works for simple CLIs/tests.

   Validation rules:
   - Expand ~, resolve symlinks, and require the path to exist and be a directory.
   - Optionally detect the repo root by running `git rev-parse --show-toplevel` in that directory and using the result if successful; otherwise keep the provided path.
   - Provide a helper: get_effective_repo_root() that returns either the repo root (if found) or the EWD for use by Git calls.

2) Centralized subprocess wrapper for Git
   Add a small helper in glin/git_tools/utils.py (new) or glin/git_tools/__init__.py:

   def run_git(args: list[str], *, check: bool = True, text: bool = True, capture_output: bool = True, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
       """Run a git command in the effective workspace directory unless cwd is provided."""
       if cwd is None:
           cwd = str(get_effective_repo_root())
       return subprocess.run(["git", *args], check=check, text=text, capture_output=capture_output, cwd=cwd)

   - Replace scattered subprocess.run(["git", ...]) with run_git([...]).
   - For rare cases that currently call `git` multiple times in a row, keep using run_git; it is cheap and consistent.

3) Minimal invasive refactor
   - Update only call sites that invoke git; do not change higher-level function signatures.
   - Where commands are built as full lists starting with "git", normalize to run_git([...]) without the initial "git" token.
   - Leave non-git subprocess usage (if any) untouched.

4) MCP configuration tool (optional but recommended)
   - Add a small MCP tool `configure_workspace_root(path: str)` in glin/git_tools/config_tools.py or sessions.py that validates and stores the path (module-level variable or a lightweight singleton). Return a summary of the active workspace path.
   - Clients (assistants) should call this tool once when establishing a session, passing their workspace root. For HTTP transport this can be part of the initial handshake; for stdio, the client calls it after connection.

5) Logging and diagnostics
   - Introduce a DEBUG log in run_git that logs the cwd and the command (respecting redaction policy if needed). Controlled by GLIN_LOG_LEVEL.
   - Add a troubleshooting MCP tool `get_workspace_info` that returns the resolved cwd, whether it’s a Git repo, and the detected toplevel path.

## Rollout plan
- Phase 1 (PR 1): Introduce get_effective_cwd/get_effective_repo_root + run_git helper; wire in config/env/session plumbing; add MCP tools `configure_workspace_root` and `get_workspace_info`.
- Phase 2 (PR 2): Mechanical replacement of subprocess.run([...]) git call sites with run_git([...]) across:
  - glin/config.py (2 spots)
  - glin/git_tools/analysis.py
  - glin/git_tools/branches.py
  - glin/git_tools/commits.py
  - glin/git_tools/config_tools.py
  - glin/git_tools/diffs.py
  - glin/git_tools/files.py
  - glin/git_tools/remotes.py
- Phase 3: Update docs (README.md, GUIDELINES) to mention GLIN_WORKDIR and the MCP configuration tool.

## Testing strategy
- Unit tests (pytest):
  - Patch GLIN_WORKDIR and verify that run_git uses it (by asserting cwd received by mocked subprocess.run).
  - Add tests for configure_workspace_root and get_workspace_info; ensure invalid paths are rejected.
  - Ensure existing tests remain hermetic by monkeypatching get_effective_cwd/_repo_root to tmp_path as needed.
  - For functions that previously returned mocked outputs, keep existing mocks but validate they are called with cwd=expected.
- Integration smoke (optional):
  - In a temporary git repo under tmp_path, set GLIN_WORKDIR to that path and run a few tools end-to-end via the MCP server (using the test client), asserting results are from the temp repo.

## Risks and mitigations
- Risk: Breaking existing tests that assume default CWD.
  - Mitigation: Default fallback preserves CWD; tests should explicitly set GLIN_WORKDIR or patch the resolver.
- Risk: Clients forget to set GLIN_WORKDIR or call the config tool.
  - Mitigation: Clear error/warning message from tools when git returns "not a git repository", including a hint to set GLIN_WORKDIR or call configure_workspace_root.

## Acceptance criteria
- All Git subprocess calls in the codebase ultimately run with cwd equal to the caller’s workspace (via env or session), verified by tests.
- A user can point the MCP server to any valid workspace by setting GLIN_WORKDIR or calling configure_workspace_root.
- No regression in existing unit tests; new tests cover the resolver and wrapper.

## Implementation checklist
- [ ] Add resolver utilities: get_effective_cwd(), get_effective_repo_root().
- [ ] Add run_git wrapper with logging.
- [ ] Add session storage + MCP tools: configure_workspace_root, get_workspace_info.
- [ ] Replace git subprocess.run usages with run_git in listed modules.
- [ ] Update tests to assert cwd usage; add new tests for resolver and MCP tools.
- [ ] Update README/GUIDELINES for GLIN_WORKDIR and configuration tool.
- [ ] Verify Ruff format/lint and run full pytest.

## Backward compatibility
- Keep all public tool function signatures the same; only internal execution context changes.
- The compatibility shim glin/git_tools.py remains unaffected.

## Estimated effort
- Dev: ~2–4 hours (mechanical replacements + tests).
- Review/QA: ~1 hour.
