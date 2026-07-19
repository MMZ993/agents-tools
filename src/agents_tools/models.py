"""Typed definitions shared by the broker and externally deployed tools."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
import inspect
import re

from jsonschema import Draft202012Validator, SchemaError

ToolHandler = Callable[[dict[str, object]], Awaitable[object]]
_TOOL_ID_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """One externally deployed MCP tool registered during broker startup."""

    tool_id: str
    description: str
    input_schema: Mapping[str, object]
    handler: ToolHandler
    redact_fields: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not _TOOL_ID_PATTERN.fullmatch(self.tool_id):
            msg = f"invalid tool ID: {self.tool_id!r}"
            raise ValueError(msg)
        if not isinstance(self.description, str):
            raise TypeError("tool description must be a string")
        if not self.description:
            raise ValueError("tool description must not be empty")
        if (
            not isinstance(self.input_schema, Mapping)
            or self.input_schema.get("type") != "object"
        ):
            raise TypeError("tool input_schema must be an object schema")
        try:
            Draft202012Validator.check_schema(dict(self.input_schema))
        except SchemaError as error:
            raise ValueError("tool input_schema is invalid") from error
        if not isinstance(self.redact_fields, frozenset) or not all(
            isinstance(field_name, str) for field_name in self.redact_fields
        ):
            raise TypeError("tool redact_fields must be frozenset[str]")
        properties = self.input_schema.get("properties", {})
        if not isinstance(properties, Mapping) or not self.redact_fields.issubset(
            properties
        ):
            raise ValueError(
                "tool redact_fields must name declared top-level properties"
            )
        if self.input_schema.get("additionalProperties") is not False or not all(
            _is_flat_argument_schema(property_schema)
            for property_schema in properties.values()
        ):
            raise ValueError("tool input_schema must define flat top-level arguments")
        if not inspect.iscoroutinefunction(self.handler):
            raise TypeError("tool handler must be asynchronous")


def _is_flat_argument_schema(schema: object) -> bool:
    return isinstance(schema, Mapping) and schema.get("type") in {
        "boolean",
        "integer",
        "null",
        "number",
        "string",
    }
