#!/usr/bin/env bash
set -euo pipefail

export TZ=Asia/Shanghai
export PATH="/home/q2635/.nvm/versions/node/v24.14.0/bin:/home/linuxbrew/.linuxbrew/bin:/usr/bin:/bin"

readonly API_ROOT="http://150.158.82.70:8080/api/v1"
readonly ACCOUNT_ID=4
readonly ACCOUNT_NAME="gpt_szh&zsm"
readonly ACCOUNT_EMAIL="siminchangtest1@shzeno.com"
readonly BROWSER_SESSION="sub2api-refresh"
readonly OPENCLI_BIN="/home/q2635/.nvm/versions/node/v24.14.0/bin/opencli"
readonly CURL_BIN="/home/linuxbrew/.linuxbrew/bin/curl"
readonly JQ_BIN="/usr/bin/jq"
readonly RESET_CREDIT_EXPIRY="2026-08-11T21:09:16.767185Z"
readonly RESET_DEADLINE_EPOCH="$(date --date='2026-08-12 05:08:30' +%s)"
readonly STATE_ROOT="${XDG_STATE_HOME:-${HOME}/.local/state}/sub2api"
readonly RESET_ATTEMPT_DIR="${STATE_ROOT}/account-4-reset-20260812.attempted"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

validate_args() {
  [[ "$ACTION" == "query" || "$ACTION" == "reset" ]] || die "action must be query or reset"
  [[ "$TARGET_EPOCH" =~ ^[0-9]+$ ]] || die "target epoch must be an integer"
  (( TARGET_EPOCH > $(date +%s) )) || die "target time must be in the future"
}

read_auth_token() {
  "$OPENCLI_BIN" browser "$BROWSER_SESSION" eval \
    "(() => localStorage.getItem('auth_token'))()" 2>/dev/null
}

fetch_account() {
  local token="$1"
  "$CURL_BIN" --silent --show-error --fail-with-body --max-time 20 \
    --header "Authorization: Bearer ${token}" \
    "${API_ROOT}/admin/accounts/${ACCOUNT_ID}?timezone=Asia%2FShanghai"
}

validate_account() {
  local account_json="$1"
  "$JQ_BIN" --exit-status --arg name "$ACCOUNT_NAME" --arg email "$ACCOUNT_EMAIL" '
    .code == 0 and .data.id == 4 and .data.name == $name and
    .data.credentials.email == $email and .data.platform == "openai" and
    .data.type == "oauth" and .data.status == "active"
  ' <<<"$account_json" >/dev/null || die "account identity or status changed"
}

validate_reset_credit() {
  local account_json="$1"
  "$JQ_BIN" --exit-status --arg expiry "$RESET_CREDIT_EXPIRY" '
    .data.extra.codex_reset_credit_snapshot.available_count > 0 and
    (.data.extra.codex_reset_credit_snapshot.credits | any(.expires_at == $expiry))
  ' <<<"$account_json" >/dev/null || die "the expected expiring reset credit is unavailable"
}

wait_until_target() {
  local delay=$((TARGET_EPOCH - $(date +%s)))
  log "armed action=${ACTION} target=$(date --date="@${TARGET_EPOCH}" '+%Y-%m-%d %H:%M:%S %Z')"
  sleep "$delay"
}

validate_wakeup() {
  local now latest
  now="$(date +%s)"
  latest=$((TARGET_EPOCH + 60))
  [[ "$ACTION" == "reset" ]] && latest="$RESET_DEADLINE_EPOCH"
  (( now >= TARGET_EPOCH && now <= latest )) || die "woke outside the allowed execution window"
}

reserve_reset_attempt() {
  mkdir -p "$STATE_ROOT"
  mkdir "$RESET_ATTEMPT_DIR" 2>/dev/null || die "reset was already attempted"
}

post_action() {
  local token="$1" endpoint="quota/refresh"
  [[ "$ACTION" == "reset" ]] && endpoint="reset-quota"
  "$CURL_BIN" --silent --show-error --fail-with-body --max-time 95 \
    --request POST --header "Authorization: Bearer ${token}" \
    "${API_ROOT}/admin/openai/accounts/${ACCOUNT_ID}/${endpoint}?timezone=Asia%2FShanghai"
}

validate_response() {
  local response="$1"
  "$JQ_BIN" --exit-status '.code == 0' <<<"$response" >/dev/null || die "API returned a failure"
  "$JQ_BIN" --compact-output \
    '{code, message, result: (.data | {windows_reset, cache_persisted, fetched_at})}' \
    <<<"$response"
}

main() {
  local token account response summary
  validate_args
  token="$(read_auth_token)" || die "could not read the browser access token"
  [[ "$token" == *.*.* ]] || die "browser access token is missing"
  account="$(fetch_account "$token")" || die "account preflight request failed"
  validate_account "$account"
  [[ "$ACTION" == "query" ]] || validate_reset_credit "$account"
  wait_until_target
  validate_wakeup
  account="$(fetch_account "$token")" || die "account execution-time check failed"
  validate_account "$account"
  [[ "$ACTION" == "query" ]] || validate_reset_credit "$account"
  [[ "$ACTION" == "query" ]] || reserve_reset_attempt
  response="$(post_action "$token")" || die "${ACTION} request failed"
  summary="$(validate_response "$response")"
  log "completed action=${ACTION} response=${summary}"
}

readonly ACTION="${1:-}"
readonly TARGET_EPOCH="${2:-}"
main
