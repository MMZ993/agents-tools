from agents_tools.logging import redact_arguments


def test_redact_arguments_masks_declared_secret_fields() -> None:
    arguments = {"recipient": "agent@example.test", "api_token": "secret-value"}

    assert redact_arguments(arguments, frozenset({"api_token"})) == {
        "recipient": "agent@example.test",
        "api_token": "[REDACTED]",
    }
