"""Bounded Prometheus metrics for broker audit outcomes."""

from prometheus_client import CollectorRegistry, Counter, REGISTRY

_AUTHENTICATION_COUNTERS: dict[int, Counter] = {}
_INVOCATION_COUNTERS: dict[int, Counter] = {}


def record_authentication(
    principal: str, outcome: str, *, registry: CollectorRegistry = REGISTRY
) -> None:
    """Record one authentication decision with bounded labels only."""
    counter = _AUTHENTICATION_COUNTERS.get(id(registry))
    if counter is None:
        counter = Counter(
            "agents_tools_authentication",
            "Broker authentication decisions.",
            ("principal", "outcome"),
            registry=registry,
        )
        _AUTHENTICATION_COUNTERS[id(registry)] = counter
    counter.labels(principal=principal, outcome=outcome).inc()


def record_invocation(
    principal: str, tool: str, outcome: str, *, registry: CollectorRegistry = REGISTRY
) -> None:
    """Record one tool outcome with bounded principal, tool, and outcome labels."""
    counter = _INVOCATION_COUNTERS.get(id(registry))
    if counter is None:
        counter = Counter(
            "agents_tools_invocation",
            "Broker tool invocation outcomes.",
            ("principal", "tool", "outcome"),
            registry=registry,
        )
        _INVOCATION_COUNTERS[id(registry)] = counter
    counter.labels(principal=principal, tool=tool, outcome=outcome).inc()
