"""Startup-only discovery of explicitly registered external tools."""

import hashlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from agents_tools.models import ToolDefinition


class ToolRegistrationError(RuntimeError):
    """Raised when an external tool module cannot be registered safely."""


def discover_tools(tools_directory: Path) -> dict[str, ToolDefinition]:
    """Load registered tools from sorted ``tools/<name>/tool.py`` modules."""
    if not tools_directory.is_dir():
        msg = f"tools directory is not readable: {tools_directory}"
        raise ToolRegistrationError(msg)

    registered_tools: dict[str, ToolDefinition] = {}
    for tool_file in sorted(tools_directory.glob("*/tool.py")):
        for definition in _load_registrations(tool_file):
            if definition.tool_id in registered_tools:
                msg = f"duplicate tool ID: {definition.tool_id}"
                raise ToolRegistrationError(msg)
            registered_tools[definition.tool_id] = definition
    return dict(sorted(registered_tools.items()))


def _load_registrations(tool_file: Path) -> list[ToolDefinition]:
    module = _load_module(tool_file)
    register = getattr(module, "register", None)
    if not callable(register):
        msg = f"tool module {tool_file} must expose register()"
        raise ToolRegistrationError(msg)

    try:
        registrations = register()
    except Exception as error:
        msg = f"tool module {tool_file} register() failed"
        raise ToolRegistrationError(msg) from error

    if not isinstance(registrations, list) or not all(
        isinstance(definition, ToolDefinition) for definition in registrations
    ):
        msg = f"tool module {tool_file} register() must return list[ToolDefinition]"
        raise ToolRegistrationError(msg)
    return registrations


def _load_module(tool_file: Path) -> ModuleType:
    module_digest = hashlib.sha256(str(tool_file.resolve()).encode()).hexdigest()
    module_name = f"agents_tools.external_tool_{module_digest}"
    spec = importlib.util.spec_from_file_location(module_name, tool_file)
    if spec is None or spec.loader is None:
        msg = f"cannot load tool module: {tool_file}"
        raise ToolRegistrationError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(module_name, None)
        msg = f"tool module import failed: {tool_file}"
        raise ToolRegistrationError(msg) from error
    return module
