#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
token_file=$(mktemp)
log_file=$(mktemp)
broker_pid=""
port=$(uv run python -c 'import socket; sock = socket.socket(); sock.bind(("127.0.0.1", 0)); print(sock.getsockname()[1]); sock.close()')
base_url="http://127.0.0.1:${port}"

cleanup() {
  if [ -n "$broker_pid" ]; then
    kill "$broker_pid" 2>/dev/null || true
    wait "$broker_pid" 2>/dev/null || true
  fi
  rm -f "$token_file" "$log_file"
}
trap cleanup EXIT

cat >"$token_file" <<'EOF'
principals:
  calculator: calculator-token
  reader: reader-token
EOF

AGENTS_TOOLS_DIRECTORY="$repo_root/tests/fixtures/tools" \
AGENTS_POLICIES_DIRECTORY="$repo_root/tests/fixtures/policies" \
AGENTS_TOKENS_FILE="$token_file" \
PYTHONPATH="$repo_root/src" \
uv run uvicorn agents_tools.main:app --host 127.0.0.1 --port "$port" >"$log_file" 2>&1 &
broker_pid=$!

for _ in $(seq 1 30); do
  if uv run python -c "from urllib.request import urlopen; urlopen(\"${base_url}/healthz\")" 2>/dev/null; then
    break
  fi
  sleep 1
done

if ! kill -0 "$broker_pid" 2>/dev/null; then
  cat "$log_file" >&2
  exit 1
fi

AGENTS_TOOLS_URL="$base_url" \
  "$repo_root/cli/dist/agents-tools" health | grep -q '"status":"ok"'
AGENTS_TOOLS_URL="$base_url" \
AGENTS_TOOLS_MCP_ADMIN_TOKEN=calculator-token \
  "$repo_root/cli/dist/agents-tools" tools list | grep -q '"name":"calc_add"'
AGENTS_TOOLS_URL="$base_url" \
AGENTS_TOOLS_MCP_ADMIN_TOKEN=calculator-token \
  "$repo_root/cli/dist/agents-tools" tools call calc_add --arg left=1 --arg right=2 | grep -q '"isError":false'
