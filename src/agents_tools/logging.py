"""Structured audit logging helpers that never emit declared secrets."""

from collections.abc import Mapping
import json
import logging
import sys

_REDACTED = "[REDACTED]"
_audit_logger = logging.getLogger("agents_tools.audit")


def configure_audit_logging(level: str = "INFO") -> None:
    """Configure concise structured audit records on standard output."""
    if _audit_logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(handler)
    configured_level = getattr(logging, level.upper(), None)
    if not isinstance(configured_level, int):
        raise ValueError(f"invalid audit log level: {level}")
    _audit_logger.setLevel(configured_level)
    _audit_logger.propagate = False


def audit_debug(event: str, **fields: object) -> None:
    """Write detailed structured audit data when DEBUG is deployment-enabled."""
    _audit_logger.debug(json.dumps({"event": event, **fields}, sort_keys=True))


def audit_event(event: str, **fields: object) -> None:
    """Write one concise structured audit event to standard output logging."""
    _audit_logger.info(json.dumps({"event": event, **fields}, sort_keys=True))


def redact_arguments(
    arguments: Mapping[str, object], redact_fields: frozenset[str]
) -> dict[str, object]:
    """Copy tool-call arguments while masking the declared secret fields."""
    return {
        key: _REDACTED if key in redact_fields else value
        for key, value in arguments.items()
    }
