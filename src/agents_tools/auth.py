"""Bearer-token authentication for broker principals."""

from collections.abc import Mapping
from secrets import compare_digest


def authenticate(token: str, principal_tokens: Mapping[str, str]) -> str | None:
    """Return the matching principal using constant-time token comparison."""
    for principal, expected_token in principal_tokens.items():
        if compare_digest(token, expected_token):
            return principal
    return None
