from prometheus_client import CollectorRegistry, generate_latest

from agents_tools.metrics import record_authentication, record_invocation


def test_authentication_metric_uses_only_principal_and_outcome_labels() -> None:
    registry = CollectorRegistry()
    record_authentication("calculator", "allowed", registry=registry)

    metrics = generate_latest(registry).decode()

    assert (
        'agents_tools_authentication_total{outcome="allowed",principal="calculator"} 1.0'
        in metrics
    )


def test_invocation_metric_uses_bounded_principal_tool_and_outcome_labels() -> None:
    registry = CollectorRegistry()
    record_invocation("calculator", "calc_add", "allowed", registry=registry)
    record_invocation("reader", "unknown", "denied", registry=registry)

    metrics = generate_latest(registry).decode()

    assert (
        'agents_tools_invocation_total{outcome="allowed",principal="calculator",tool="calc_add"} 1.0'
        in metrics
    )
    assert (
        'agents_tools_invocation_total{outcome="denied",principal="reader",tool="unknown"} 1.0'
        in metrics
    )
