from pathlib import Path

from agents_tools.tools import discover_tools

_FIXTURES = Path(__file__).parent / "fixtures"


def test_regression_fixture_tools_are_registered_without_broker_core_changes() -> None:
    tools = discover_tools(_FIXTURES / "tools")

    assert list(tools) == ["calc_add", "calc_sub", "static_text"]
    assert tools["calc_add"].input_schema["required"] == ["left", "right"]
