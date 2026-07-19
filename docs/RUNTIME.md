# Broker Runtime

This document defines how the portable broker loads deployment-provided principals, policies, and tools at startup.

## Runtime ownership

The image contains only `src/agents_tools/` broker code. Deployment automation must mount the following paths before the container starts or restarts:

```text
/tools                 # Externally deployed tool modules
/policies              # Non-secret principal policies
/run/secrets/tokens.yml # Vault-rendered root-owned principal token mapping
```

The broker does not clone repositories, hot-reload modules, or write these mounts. Deployment automation owns production tool source, non-secret policies, and rendering `tokens.yml` from its secret manager with mode `0600`. The broker currently runs as root so it can read the root-owned token mapping; mounted tool code is therefore trusted deployment content and must remain read-only and operator-controlled.

## Principal tokens

See [PRINCIPALS.md](PRINCIPALS.md) for the principal and policy contract. `/run/secrets/tokens.yml` maps each principal to exactly one bearer token:

```yaml
principals:
  calculator: vault-rendered-token
  reader: vault-rendered-token
```

Agents send their token through `Authorization: Bearer <token>`. The broker compares tokens in constant time. Tokens never belong in Git, tool source, agent runtime configuration, logs, metrics, or policy files.

## Policies

Each `/policies/<principal>.yaml` file has a matching `principal` value:

```yaml
principal: calculator
allow:
  - calc_*
deny:
  - calc_sub
```

Evaluation is order-independent: any matching `deny` wins, otherwise any matching `allow` grants access, otherwise access is denied. Patterns are exact tool IDs, `*`, or shell-style globs such as `calc_*`.

At startup the broker creates an isolated in-memory MCP server for every authenticated principal. All servers remain behind one `/mcp/` HTTP endpoint; bearer authentication selects the internal server. A principal can discover and invoke only policy-permitted tools.

## Tool registration

See [TOOLS.md](TOOLS.md) for the external tool contract. Tools are loaded only at container startup from `/tools/<name>/tool.py`; changing a mounted tool requires a container restart. Tool IDs use lowercase underscore namespaces. Duplicate IDs, invalid definitions, broken imports, unreadable configuration, or malformed YAML fail startup.

## Endpoints and observability

```text
/mcp/     # Authenticated standard MCP streamable HTTP transport
/healthz  # Unauthenticated health response
/metrics/ # Unauthenticated Prometheus metrics
```

Network controls must restrict all endpoints to approved agent and monitoring hosts. Traefik terminates internal HTTPS; the broker remains an HTTP backend. Metrics use bounded labels only. Structured stdout audit records capture authentication and tool invocations; DEBUG logging is a temporary deployment configuration change.

## Release and deployment boundary

CI verifies the locked runtime, builds the container, and publishes an immutable image reference using the commit SHA. Only protected numeric semantic tags without leading zeroes (for example, `1.2.3`) add a matching version tag; deployments must use the immutable SHA reference. The runtime repository owns only this image. A separate deployment artifact owns production tool modules and non-secret policy YAML, mounts those artifacts read-only, renders the token mapping from its secret manager, restarts the container, and smoke-tests the mounted broker and client interoperability.


## References

- `.agents/PRD.md`
- `.agents/RULES.md`
- `tests/fixtures/`
