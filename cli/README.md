# agents-tools CLI

Go CLI for the agents-tools MCP broker. Single static binary, no runtime dependencies. Speaks MCP streamable HTTP over the broker's `/mcp/` endpoint.

## Installation

Build from source (requires Go 1.26+):

```bash
cd cli/
make build           # linux/amd64 → dist/agents-tools
make build-all       # cross-compile linux/amd64 + linux/arm64
```

```bash
cp dist/agents-tools /usr/local/bin/agents-tools
```

## Configuration

Set environment variables before running. No config file needed.

| Variable | Required | Default | Description |
|---|---|---|---|
| `AGENTS_TOOLS_MCP_ADMIN_TOKEN` | yes | — | Bearer token; sent as `Authorization: Bearer <token>`. The broker selects the principal from the token. |
| `AGENTS_TOOLS_URL` | no | `https://agents-tools.mmz.sh` | Broker base URL |
| `AGENTS_TOOLS_TIMEOUT` | no | `30` | HTTP timeout in seconds |

```bash
export AGENTS_TOOLS_MCP_ADMIN_TOKEN=...
```

### Scoped access via bash functions

The broker authenticates a single principal per invocation from the supplied token. Reuse the binary for a different principal by pinning its token in a bash function:

```bash
agents_admin()    { AGENTS_TOOLS_MCP_ADMIN_TOKEN=admin_token    agents-tools "$@"; }
agents_openclaw() { AGENTS_TOOLS_MCP_ADMIN_TOKEN=openclaw_token agents-tools "$@"; }
```

## Output

- **Default**: compact JSON (agent/pipe-friendly)
- **`--pretty` / `-p`**: indented JSON

`tools call` emits the complete MCP tool result, including every `content` item, `structuredContent`, and `isError`. This preserves text, images, audio, embedded resources, and resource links.

All errors go to stderr with exit code 1. Success goes to stdout with exit code 0. A tool call that returns `isError: true` (policy deny, invalid arguments, tool failure) also exits 1.

## Commands

### tools

```bash
agents-tools tools list [--pretty]
agents-tools tools schema <name> [--pretty]
agents-tools tools call <name> [--arg key=value]... [--json '{}'] [--pretty]
```

`--arg` values are coerced: `true`/`false` → bool, integers → int, otherwise string. `--json` takes a full JSON object and is applied first, with `--arg` overrides on top.

### health

```bash
agents-tools health [--pretty]     # GET /healthz, no authentication
```

## Examples

```bash
# Discover available tools for this principal
agents-tools tools list --pretty

# Inspect one tool's input schema to learn how to call it
agents-tools tools schema spotify_search --pretty

# Read-only call with no arguments
agents-tools tools call spotify_get_devices --pretty

# Call with an integer argument (coerced to int to match the tool schema)
agents-tools tools call mail_list --arg limit=5 --pretty

# Full control over argument types via a JSON object
agents-tools tools call spotify_search --json '{"query":"daft punk","type":"artist","limit":3}' --pretty
```

## How it works

Each invocation runs a fresh MCP session: `initialize` (captures the `Mcp-Session-Id` header) → `notifications/initialized` → `tools/list` or `tools/call`. The broker returns plain JSON (`json_response=True`), so no SSE parsing is required.

## Project layout

```
cli/
├── cmd/              # cobra commands (root, tools, health)
├── internal/
│   └── client/       # MCP streamable-HTTP client (JSON-RPC)
├── main.go
├── go.mod
└── Makefile
```

## References

- `docs/RUNTIME.md`
- `docs/PRINCIPALS.md`
- `docs/TOOLS.md`
