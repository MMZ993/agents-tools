# Agents Tools

This repository provides the portable runtime for a policy-enforcing internal MCP broker.

## Development

```bash
# Synchronize the exact locked development environment.
uv sync --frozen --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

## References

- `.agents/PRD.md`
- `.agents/RULES.md`
