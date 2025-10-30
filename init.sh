#!/usr/bin/env bash
# init.sh — Your one-minute Seev setup
#
# What you get
# - A ready-to-use folder that holds your personal Seev data:
#   • A Markdown worklog you can open and edit anywhere
#   • A local SQLite database Seev uses to store insights
# - A friendly seev.toml written to your XDG config (default: ~/.config/seev/seev.toml)
# - Safe re-runs: if a config exists, we back it up with a timestamp and explain what changed
#
# Why run this?
# - Start capturing worklogs and Git insights immediately, with sensible defaults
# - Keep your data in one place so Seev’s CLI and MCP tools “just work”
# - Customize later — you can edit the config or use env vars without re-running the script
#
# Quick start
#   ./init.sh [options] <target_dir>
#   If you omit <target_dir> or options, we’ll ask a few quick questions.
#   Press Enter to accept defaults — you can tweak things any time.
#
# Options
#   -e, --emails CSV  People to attribute commits to (e.g., a@b.com,b@c.com).
#                     Used to filter Git history so your reports reflect your work.
#                     Skip it for now — we’ll write examples you can edit later.
#   -r, --repos  CSV  Repositories to include (paths or owner/repo). Examples added if blank.
#   -m, --md     NAME Markdown filename to create in <target_dir> (default: WORKLOG.md).
#   -d, --db     NAME Database filename to create in <target_dir> (default: seev.sqlite3).
#   -y, --yes         Non-interactive; accept defaults and create what’s needed.
#   -h, --help        Show this help and exit.
#
# Examples
#   Minimal (accept prompts and defaults):
#     ./init.sh ~/seev-data
#   Pre-configure emails and repos (no prompts):
#     ./init.sh -y -e "me@ex.com" -r "owner/repo,~/code/that-repo" ~/seev-data
#
# Tips
# - You can override settings at runtime via env vars (great for experiments):
#     SEEV_DB_PATH, SEEV_MD_PATH, SEEV_TRACK_EMAILS, SEEV_TRACK_REPOSITORIES
# - The config keys written here are read by seev/config.py and used across the tools.
set -euo pipefail

print_help() {
  sed -n '1,60p' "$0" | sed 's/^# \{0,1\}//'
}

confirm() {
  # confirm <prompt>
  local prompt=${1:-Are you sure?}
  if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " reply || true
  case ${reply:-} in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

# Defaults
MD_NAME="WORKLOG.md"
DB_NAME="seev.sqlite3"
EMAILS=""
REPOS=""
ASSUME_YES=0

# Predeclare config status vars to avoid 'set -u' unbound variable errors
JUNIE_CFG=""
CURSOR_CFG=""
VSCODE_CFG=""
CLAUDE_CFG=""
# Also predeclare instruction strings used when CLI setup fails or is unavailable
VSCODE_INSTR=""
CLAUDE_INSTR=""

# Parse args
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) print_help; exit 0 ;;
    -y|--yes) ASSUME_YES=1; shift ;;
    -e|--emails) EMAILS="$2"; shift 2 ;;
    -r|--repos) REPOS="$2"; shift 2 ;;
    -m|--md) MD_NAME="$2"; shift 2 ;;
    -d|--db) DB_NAME="$2"; shift 2 ;;
    --) shift; break ;;
    -*) echo "Error: unknown option: $1" >&2; echo; print_help; exit 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

# Interactive prompts for missing values when not assuming yes
prompt_with_default() {
  # prompt_with_default <prompt> <default>
  local prompt="$1"
  local def="$2"
  local input
  read -r -p "$prompt${def:+ [$def]}: " input || true
  if [[ -z "$input" ]]; then
    echo "$def"
  else
    echo "$input"
  fi
}

DEFAULT_TARGET_DIR="$HOME/.local/share/seev"

if [[ ${#ARGS[@]} -lt 1 ]]; then
  if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
    TARGET_DIR="$DEFAULT_TARGET_DIR"
  else
    TARGET_DIR=$(prompt_with_default "Enter target directory for Seev data" "$DEFAULT_TARGET_DIR")
  fi
else
  TARGET_DIR=${ARGS[0]}
fi

# Expand ~ in paths
TARGET_DIR=$(eval echo "$TARGET_DIR")

# If not assuming yes, prompt for other missing options
if [[ ${ASSUME_YES:-0} -eq 0 ]]; then
  if [[ -z "$MD_NAME" || "$MD_NAME" == "WORKLOG.md" ]]; then
    MD_NAME=$(prompt_with_default "Markdown filename" "$MD_NAME")
  fi
  if [[ -z "$DB_NAME" || "$DB_NAME" == "seev.sqlite3" ]]; then
    DB_NAME=$(prompt_with_default "Database filename" "$DB_NAME")
  fi
  if [[ -z "$EMAILS" ]]; then
    read -r -p "Comma-separated emails to track (optional): " EMAILS || true
  fi
  if [[ -z "$REPOS" ]]; then
    read -r -p "Comma-separated repositories to track (optional): " REPOS || true
  fi
fi

# Resolve XDG config path
XDG_CONFIG_HOME_DEFAULT="$HOME/.config"
XDG_ROOT="${XDG_CONFIG_HOME:-$XDG_CONFIG_HOME_DEFAULT}"
SEEV_CONFIG_DIR="$XDG_ROOT/seev"
SEEV_CONFIG_FILE="$SEEV_CONFIG_DIR/seev.toml"

# Create storage directory
mkdir -p "$TARGET_DIR"

MD_PATH="$TARGET_DIR/$MD_NAME"
DB_PATH="$TARGET_DIR/$DB_NAME"

# Create placeholder files if absent
if [[ ! -e "$MD_PATH" ]]; then
  echo "# Seev Worklog" > "$MD_PATH"
  echo >> "$MD_PATH"
  echo "Initialized on $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$MD_PATH"
fi

if [[ ! -e "$DB_PATH" ]]; then
  # Prefer creating an empty file; SQLite will initialize it on first open
  : > "$DB_PATH"
fi

# Prepare config directory
mkdir -p "$SEEV_CONFIG_DIR"

# Backup existing config if present
if [[ -f "$SEEV_CONFIG_FILE" ]]; then
  TS=$(date +%Y%m%d-%H%M%S)
  BAK="$SEEV_CONFIG_FILE.$TS.bak"
  echo "Found existing config: $SEEV_CONFIG_FILE"
  if confirm "Back up existing to $BAK and overwrite?"; then
    cp "$SEEV_CONFIG_FILE" "$BAK"
  else
    echo "Aborted by user."; exit 3
  fi
fi

# Normalize CSV helpers -> TOML arrays
csv_to_toml_array() {
  # input: CSV string; output: TOML array literal
  local csv="$1"
  # Trim spaces around commas and entries
  local IFS=','
  local out=()
  for item in $csv; do
    item=$(echo "$item" | sed 's/^\s\+//;s/\s\+$//')
    if [[ -n "$item" ]]; then
      out+=("\"$item\"")
    fi
  done
  if [[ ${#out[@]} -eq 0 ]]; then
    echo "[]"
  else
    local joined=$(printf ", %s" "${out[@]}")
    echo "[${joined:2}]"
  fi
}

EMAILS_TOML=""
REPOS_TOML=""

if [[ -n "$EMAILS" ]]; then
  EMAILS_TOML=$(csv_to_toml_array "$EMAILS")
else
  # Friendly examples; user can edit later
  EMAILS_TOML='["user1@example.com", "user2@example.com"]'
fi

if [[ -n "$REPOS" ]]; then
  REPOS_TOML=$(csv_to_toml_array "$REPOS")
else
  REPOS_TOML='["owner/repo", "~/code/some/local/repo"]'
fi

# Write seev.toml
cat > "$SEEV_CONFIG_FILE" <<TOML
# Seev Configuration
# This file was generated by seev-init.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
#
# Emails to track when querying git history
track_emails = $EMAILS_TOML

# Repositories to include in worklogs (paths or owner/repo or full git URLs)
track_repositories = $REPOS_TOML

# Paths to your local data files
# You can override these at runtime via SEEV_DB_PATH and SEEV_MD_PATH
# Note: ~ is accepted by Seev and will be expanded by your shell if you export
#       the env vars directly.
db_path = "${DB_PATH/#$HOME/~}"
markdown_path = "${MD_PATH/#$HOME/~}"
TOML

# === Optional: Configure MCP clients to use the Seev server ===
# We support: Junie (JetBrains), Cursor, Claude Code/Desktop, VS Code
# Defaults: transport=stdio, command=uvx, args=(--from git+https://github.com/bcosynot/seev.git seev)

have_cmd() { command -v "$1" >/dev/null 2>&1; }

# Ensure `uv` is installed (Seev uses `uvx` to run/install its CLI and tools)
# - We ask for confirmation first (unless --yes was passed)
# - We print the official docs link so the user knows what is being installed
ensure_uv() {
  # If either `uvx` or `uv` exists, we're good
  if have_cmd uvx || have_cmd uv; then
    return 0
  fi

  echo
  echo "uv is not installed on this system."
  echo "Why uv: Seev uses uv to quickly and reproducibly install and run (via 'uvx')," \
       "and some optional setup in this script expects 'uvx' to be available."
  echo "Learn more about uv: https://docs.astral.sh/uv/"

  local DO_INSTALL=0
  if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
    DO_INSTALL=1
  else
    if confirm "Install uv now? (see https://docs.astral.sh/uv/ for details)"; then
      DO_INSTALL=1
    else
      echo "Skipping uv installation at your request."
      echo "Note: 'uvx' commands and MCP client auto-configuration in this script may not work until uv is installed."
      return 0
    fi
  fi

  if [[ $DO_INSTALL -eq 1 ]]; then
    echo "Installing uv using the official installer..."
    if have_cmd curl; then
      if ! sh -c "$(curl -fsSL https://astral.sh/uv/install.sh)"; then
        echo "uv installation failed via curl. You can install manually from https://docs.astral.sh/uv/."
        return 0
      fi
    elif have_cmd wget; then
      if ! sh -c "$(wget -qO- https://astral.sh/uv/install.sh)"; then
        echo "uv installation failed via wget. You can install manually from https://docs.astral.sh/uv/."
        return 0
      fi
    else
      echo "Neither curl nor wget is available, cannot auto-install uv."
      echo "Please see https://docs.astral.sh/uv/ for manual installation instructions."
      return 0
    fi

    # Try to make uv available in the current session (common install location)
    export PATH="$HOME/.local/bin:$PATH"

    if have_cmd uvx || have_cmd uv; then
      echo "uv installed successfully. If commands are still not found, restart your shell so PATH updates apply."
    else
      echo "uv installation completed but the 'uv' command is not yet available on PATH."
      echo "You may need to restart your terminal or add ~/.local/bin to PATH. See https://docs.astral.sh/uv/."
    fi
  fi
}

# Perform the check early so subsequent steps (like MCP setup) can rely on 'uvx'
ensure_uv

json_upsert_server() {
  # json_upsert_server <file> <name> <command> <args_json>
  local file="$1" name="$2" cmd="$3" args_json="$4"
  local dir
  dir=$(dirname "$file")
  mkdir -p "$dir"
  local ts
  ts=$(date +%Y%m%d-%H%M%S)
  if [[ -f "$file" ]]; then
    cp "$file" "$file.$ts.bak"
  fi
  if have_cmd jq; then
    local tmp
    tmp=$(mktemp)
    # Start with existing JSON or an empty object
    if [[ -s "$file" ]]; then
      cat "$file" > "$tmp"
    else
      echo '{}' > "$tmp"
    fi
    # Ensure .mcpServers exists and upsert entry (Junie/Cursor schema)
    local updated
    updated=$(jq \
      --arg name "$name" \
      --arg cmd "$cmd" \
      --argjson args "$args_json" \
      '.mcpServers = (.mcpServers // {})
       | .mcpServers[$name] = {command: $cmd, args: $args}' "$tmp")
    echo "$updated" > "$file"
    rm -f "$tmp"
    echo "Updated $file → mcpServers['$name']"
  else
    # Fallback: merge using Python if available; otherwise write minimal file with warning.
    if command -v python3 >/dev/null 2>&1; then
      python3 - "$file" "$name" "$cmd" "$args_json" <<'PY'
import json, os, sys, tempfile, shutil
path, name, cmd, args_json = sys.argv[1:]
# Load existing JSON if present
obj = {}
if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
    except Exception:
        # If unreadable, start fresh but keep a backup
        pass
# Ensure mcpServers exists; support object or array forms
servers = obj.get('mcpServers')
if isinstance(servers, dict):
    pass
elif isinstance(servers, list):
    # Convert list entries with name keys into a dict for reliable upsert
    new_dict = {}
    for item in servers:
        if isinstance(item, dict) and 'name' in item:
            new_dict[item['name']] = {k: v for k, v in item.items() if k != 'name'}
    servers = new_dict
else:
    servers = {}
# Parse args/env JSON
try:
    args = json.loads(args_json)
except Exception:
    args = []
env = {}
# Build server entry
entry = { 'command': cmd, 'args': args }
if env:
    entry['env'] = env
# Upsert
servers[name] = entry
# Prefer object form going forward
obj['mcpServers'] = servers
# Atomic write with backup
backup = None
if os.path.exists(path):
    backup = f"{path}.{__import__('time').strftime('%Y%m%d-%H%M%S')}.bak"
    try:
        shutil.copy2(path, backup)
    except Exception:
        backup = None
fd, tmp = tempfile.mkstemp(prefix='mcp.', suffix='.json', dir=os.path.dirname(path) or None)
os.close(fd)
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(obj, f, indent=2, ensure_ascii=False)
    f.write('\n')
shutil.move(tmp, path)
print(f"Updated {path} → mcpServers['{name}'] (python fallback)")
PY
    else
      # Last-resort fallback: write a minimal file (no merge). Warn user.
      cat > "$file" <<JSON
{
  "mcpServers": {
    "$name": {
      "command": "$cmd",
      "args": $(echo "$args_json")
    }
  }
}
JSON
      echo "Wrote $file without merging (jq and python3 not found). Existing entries may be overwritten."
    fi
  fi
}

configure_junie() {
  local path="$HOME/.junie/mcp.json"
  json_upsert_server "$path" "seev" "uvx" '["--from","git+https://github.com/bcosynot/seev.git","seev"]'
  JUNIE_CFG="$path"
}

configure_cursor() {
  local path="$HOME/.cursor/mcp.json"
  json_upsert_server "$path" "seev" "uvx" '["--from","git+https://github.com/bcosynot/seev.git","seev"]'
  CURSOR_CFG="$path"
}

configure_vscode() {
  local json
  json='{"name":"seev","command":"uvx","args":["--from","git+https://github.com/bcosynot/seev.git","seev"]}'
  if have_cmd code; then
    if code --version >/dev/null 2>&1; then
      if code --add-mcp "$json" >/dev/null 2>&1; then
        VSCODE_CFG="user-profile"
        echo "VS Code: added Seev MCP server to user profile via --add-mcp."
      else
        VSCODE_INSTR="$json"
        echo "VS Code: failed to add via CLI. Will print manual command below."
      fi
    fi
  else
    VSCODE_INSTR="$json"
    echo "VS Code CLI ('code') not found. Will print manual command below."
  fi
}

configure_claude() {
  # Prefer user scope. Falls back to instructions if CLI missing.
  local cmd=(claude mcp add --transport stdio --scope user --name seev -- uvx --from git+https://github.com/bcosynot/seev.git seev)
  if have_cmd claude; then
    if "${cmd[@]}" >/dev/null 2>&1; then
      CLAUDE_CFG="user-scope"
      echo "Claude: added Seev MCP server to user scope."
    else
      CLAUDE_INSTR="${cmd[*]}"
      echo "Claude: failed to add via CLI. Will print manual command below."
    fi
  else
    CLAUDE_INSTR="${cmd[*]}"
    echo "Claude CLI not found. Will print manual command below."
  fi
}

# Decide whether to set up MCP now
DO_MCP=0
if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
  DO_MCP=1
else
  if confirm "Also set up the Seev MCP server in your coding assistants now?"; then
    DO_MCP=1
  fi
fi

CONFIGURED=()
if [[ $DO_MCP -eq 1 ]]; then
  # Prompt for assistants (CSV of keys or names)
  if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
    SELECTION="junie,cursor,claude,vscode"
  else
    echo "Select assistants to configure (comma-separated):"
    echo "  1) Junie (JetBrains)   => 'junie'"
    echo "  2) Cursor              => 'cursor'"
    echo "  3) Claude Code/Desktop => 'claude'"
    echo "  4) VS Code             => 'vscode'"
    read -r -p "Your choice [junie,cursor,claude,vscode]: " SELECTION || true
    SELECTION=${SELECTION:-junie,cursor,claude,vscode}
  fi
  # Normalize: to lowercase, split commas, map digits to names
  norm=$(echo "$SELECTION" | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]//g')
  IFS=',' read -r -a items <<< "$norm"
  # Deduplicate while preserving order
  seen=""
  choices=()
  for it in "${items[@]}"; do
    case "$it" in
      1|junie) key="junie" ;;
      2|cursor) key="cursor" ;;
      3|claude|claude-code|claude-desktop) key="claude" ;;
      4|vscode|code|visual-studio-code) key="vscode" ;;
      *) key="" ;;
    esac
    if [[ -n "$key" && ",$seen," != *",$key,"* ]]; then
      choices+=("$key"); seen="$seen,$key"
    fi
  done
  for c in "${choices[@]}"; do
    case "$c" in
      junie) configure_junie; CONFIGURED+=("junie:$JUNIE_CFG") ;;
      cursor) configure_cursor; CONFIGURED+=("cursor:$CURSOR_CFG") ;;
      vscode) configure_vscode; CONFIGURED+=("vscode:$VSCODE_CFG") ;;
      claude) configure_claude; CONFIGURED+=("claude:$CLAUDE_CFG") ;;
    esac
  done
fi

cat <<MSG

Done!

Created or verified:
  - Directory: $TARGET_DIR
  - Markdown:  $MD_PATH
  - Database:  $DB_PATH
  - Config:    $SEEV_CONFIG_FILE

MCP setup:
$(
  if [[ ${#CONFIGURED[@]} -gt 0 ]]; then
    for item in "${CONFIGURED[@]}"; do
      name="${item%%:*}"; loc="${item#*:}";
      case "$name" in
        junie) echo "  - Junie:    ~/.junie/mcp.json (${loc:-updated})" ;;
        cursor) echo "  - Cursor:   ~/.cursor/mcp.json (${loc:-updated})" ;;
        vscode) echo "  - VS Code:  user profile (code --add-mcp), status: ${loc:-attempted}" ;;
        claude) echo "  - Claude:   user scope (claude mcp add), status: ${loc:-attempted}" ;;
      esac
    done
  else
    echo "  - Skipped (you can run this script again to add MCP configs)."
  fi
)

Next steps:
  - You can edit $SEEV_CONFIG_FILE to adjust emails/repos.
  - If any MCP client wasn’t auto-configured, run the corresponding manual command:
$(
  [[ -n "$VSCODE_INSTR" ]] && echo "    • VS Code: code --add-mcp '$VSCODE_INSTR'"
  [[ -n "$CLAUDE_INSTR" ]] && echo "    • Claude:  $CLAUDE_INSTR"
  true
)

Tip: You can also set env vars temporarily, e.g.:
  export SEEV_DB_PATH="$DB_PATH"
  export SEEV_MD_PATH="$MD_PATH"
  export SEEV_TRACK_EMAILS=$(echo $EMAILS_TOML | tr -d '[]' | tr -d '"')
  export SEEV_TRACK_REPOSITORIES=$(echo $REPOS_TOML | tr -d '[]' | tr -d '"')

Locations reference:
  - Junie MCP file:   ~/.junie/mcp.json
  - Cursor MCP file:  ~/.cursor/mcp.json
  - VS Code (CLI):    code --add-mcp '{"name":"seev","command":"uvx","args":["--from","git+https://github.com/bcosynot/seev.git","seev"]}'
  - Claude (CLI):     claude mcp add --transport stdio --scope user --name seev -- \
                      uvx --from git+https://github.com/bcosynot/seev.git seev

MSG
