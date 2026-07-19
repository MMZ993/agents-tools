from agents_tools.auth import authenticate


def test_authenticate_returns_matching_principal() -> None:
    principal = authenticate("broker-token", {"calculator": "broker-token"})

    assert principal == "calculator"
