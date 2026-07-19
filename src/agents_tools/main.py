"""Deployment entry point for the mounted broker runtime configuration."""

import os
from pathlib import Path

from agents_tools.app import create_app
from agents_tools.config import (
    load_policies,
    load_principal_tokens,
    validate_principals,
)
from agents_tools.logging import configure_audit_logging
from agents_tools.tools import discover_tools


def create_runtime_app():
    """Load required mounted configuration and create the ASGI application."""
    configure_audit_logging(os.environ.get("AGENTS_LOG_LEVEL", "INFO"))
    tools_directory = Path(os.environ.get("AGENTS_TOOLS_DIRECTORY", "/tools"))
    policies_directory = Path(os.environ.get("AGENTS_POLICIES_DIRECTORY", "/policies"))
    token_file = Path(os.environ.get("AGENTS_TOKENS_FILE", "/run/secrets/tokens.yml"))
    principal_tokens = load_principal_tokens(token_file)
    policies = load_policies(policies_directory)
    validate_principals(principal_tokens, policies)
    return create_app(
        principal_tokens=principal_tokens,
        policies=policies,
        tools=discover_tools(tools_directory),
    )


app = create_runtime_app()
