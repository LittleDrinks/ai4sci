#!/usr/bin/env bash
set -euo pipefail

readonly HERDR_BIN="/home/q2635/.local/bin/herdr"
readonly JQ_BIN="/usr/bin/jq"
readonly HERDR_SESSION="ai4s"
readonly CODEX_SESSION_ID="019ff189-dd82-7810-9fc4-88236948e8e9"
readonly MESSAGE="${1:-}"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

find_pane() {
  "$HERDR_BIN" --session "$HERDR_SESSION" pane list | "$JQ_BIN" --raw-output \
    --arg session "$CODEX_SESSION_ID" \
    '.result.panes[] | select(.agent_session.value == $session) | .pane_id'
}

main() {
  local pane_id
  [[ -n "$MESSAGE" ]] || die "message is required"
  pane_id="$(find_pane)"
  [[ -n "$pane_id" && "$pane_id" != *$'\n'* ]] || die "Codex pane was not uniquely resolved"
  "$HERDR_BIN" --session "$HERDR_SESSION" pane run "$pane_id" "$MESSAGE"
  printf 'message sent to %s\n' "$pane_id"
}

main
