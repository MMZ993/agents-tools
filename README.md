# Agents Tools

Bespoke private software, created using LLM agent-assisted coding. Intended to run in a private homelab.
Deployment and tools configuration are handled by separate private repos.

Hosted on local GitLab; a public mirror is available on GitHub.

## Overview

This repository provides the portable runtime for a policy-enforcing internal MCP broker over HTTP. Traefik terminates HTTPS in deployment.

The broker loads deployment-provided Python tools and per-principal policies at startup. This repository builds the runtime Docker image. Separate deployment repositories manage the broker deployment. Production tool and policy artifacts can be deployed separately without image changes; deployment automation synchronizes those artifacts and restarts the broker.

The broker has no hot reload or database by design. It is intentionally minimal and provides basic functionality.

The service provides Prometheus metrics and structured logs.

## Purpose

The broker provides a unified entry point through which agents access tools, primarily API integrations.

It keeps provider authentication material—API keys, personal access tokens (PATs), and other credentials—out of agent environments. Gateway ACLs protect the broker host and prohibit external access; a leaked broker bearer token does not bypass those network controls or directly expose the third-party APIs available through the broker.

MCP was chosen as an emerging standard for agent-to-tool communication.

## Status

This is an internal project released publicly as-is. Deployment-specific tools, policies, credentials, and infrastructure configuration are maintained separately and are not included.

## Development

```bash
# Synchronize the exact locked development environment.
uv sync --frozen --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```
