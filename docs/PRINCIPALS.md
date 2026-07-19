# Principal and Policy Contract

This document defines deployment-time principal authentication and least-privilege policy configuration.

## Token mapping

Before starting or restarting the broker container, deployment automation renders a root-owned `0600` token file at `/run/secrets/tokens.yml`:

```yaml
principals:
  calculator: injected-bearer-token
  reader: injected-bearer-token
```

Every principal has a distinct bearer token. Inject tokens from a secret manager; never commit them, place them in policy files, or pass them to tool handlers. Agents authenticate with `Authorization: Bearer <token>`.

## Policy files

Mount one non-secret YAML file per principal at `/policies/<principal>.yaml` before container startup or restart:

```yaml
principal: calculator
allow:
  - calc_*
deny:
  - calc_sub
```

The `principal` value must match the filename stem. Policy files are read-only to the broker.

## Evaluation

Policies are default-deny and order-independent:

1. Any matching `deny` rule denies access.
2. Otherwise, any matching `allow` rule grants access.
3. Otherwise, access is denied.

Rules accept exact tool IDs, `*`, and shell-style globs such as `calc_*`. Regular expressions, time windows, rates, and generic argument conditions are unsupported.

## References

- [RUNTIME.md](RUNTIME.md)
- [TOOLS.md](TOOLS.md)
