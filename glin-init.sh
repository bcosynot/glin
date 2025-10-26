#!/usr/bin/env bash
# glin-init.sh — Initialize local storage dir and write XDG config for Glin
#
# This script creates a directory to hold your SQLite database and Markdown
# worklog, and writes a friendly glin.toml config file under your XDG config
# path (default: ~/.config/glin/glin.toml). It is safe to run multiple times;
# existing config will be backed up with a timestamp.
#
# Usage:
#   ./glin-init.sh [options] <target_dir>
#   If <target_dir> or options are omitted, the script will prompt for each;
#   press Enter to accept defaults or leave optional fields blank.
#
# Options:
#   -e, --emails CSV       Comma-separated emails to track (e.g. a@b.com,b@c.com).
#                          If omitted, example emails will be written as guidance.
#   -r, --repos CSV        Comma-separated repositories to track (paths or owner/repo).
#                          If omitted, an example list is written.
#   -m, --md NAME          Markdown filename to create in target_dir (default: WORKLOG.md)
#   -d, --db NAME          DB filename to create in target_dir (default: glin.sqlite3)
#   -y, --yes              Non-interactive; accept defaults and create as needed.
#   -h, --help             Show this help and exit.
#
# Examples:
#   ./glin-init.sh ~/glin-data
#   ./glin-init.sh -e "me@ex.com" -r "owner/repo,~/code/that-repo" ~/glin-data
#
# Notes:
# - You can override at runtime via env vars used by Glin:
#     SEEV_DB_PATH, SEEV_MD_PATH, SEEV_TRACK_EMAILS, SEEV_TRACK_REPOSITORIES
# - Config keys written here are read by glin/config.py.
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
DB_NAME="glin.sqlite3"
EMAILS=""
REPOS=""
ASSUME_YES=0

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

DEFAULT_TARGET_DIR="$HOME/.local/share/glin"

if [[ ${#ARGS[@]} -lt 1 ]]; then
  if [[ ${ASSUME_YES:-0} -eq 1 ]]; then
    TARGET_DIR="$DEFAULT_TARGET_DIR"
  else
    TARGET_DIR=$(prompt_with_default "Enter target directory for Glin data" "$DEFAULT_TARGET_DIR")
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
  if [[ -z "$DB_NAME" || "$DB_NAME" == "glin.sqlite3" ]]; then
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
SEEV_CONFIG_DIR="$XDG_ROOT/glin"
SEEV_CONFIG_FILE="$SEEV_CONFIG_DIR/glin.toml"

# Create storage directory
mkdir -p "$TARGET_DIR"

MD_PATH="$TARGET_DIR/$MD_NAME"
DB_PATH="$TARGET_DIR/$DB_NAME"

# Create placeholder files if absent
if [[ ! -e "$MD_PATH" ]]; then
  echo "# Glin Worklog" > "$MD_PATH"
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

# Write glin.toml
cat > "$SEEV_CONFIG_FILE" <<TOML
# Glin Configuration
# This file was generated by glin-init.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
#
# Emails to track when querying git history
track_emails = $EMAILS_TOML

# Repositories to include in worklogs (paths or owner/repo or full git URLs)
track_repositories = $REPOS_TOML

# Paths to your local data files
# You can override these at runtime via SEEV_DB_PATH and SEEV_MD_PATH
# Note: ~ is accepted by Glin and will be expanded by your shell if you export
#       the env vars directly.
db_path = "${DB_PATH/#$HOME/~}"
markdown_path = "${MD_PATH/#$HOME/~}"
TOML

cat <<MSG

Done!

Created or verified:
  - Directory: $TARGET_DIR
  - Markdown:  $MD_PATH
  - Database:  $DB_PATH
  - Config:    $SEEV_CONFIG_FILE

Next steps:
  - You can edit $SEEV_CONFIG_FILE to adjust emails/repos.

Tip: You can also set env vars temporarily, e.g.:
  export SEEV_DB_PATH="$DB_PATH"
  export SEEV_MD_PATH="$MD_PATH"
  export SEEV_TRACK_EMAILS=$(echo $EMAILS_TOML | tr -d '[]' | tr -d '"')
  export SEEV_TRACK_REPOSITORIES=$(echo $REPOS_TOML | tr -d '[]' | tr -d '"')

MSG
