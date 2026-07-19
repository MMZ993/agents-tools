from agents_tools.policy import Policy


def test_deny_rule_overrides_matching_allow_rule() -> None:
    policy = Policy(principal="calculator", allow=("calc_*",), deny=("calc_sub",))

    assert not policy.permits("calc_sub")


def test_policy_defaults_to_deny_and_supports_exact_and_glob_allow_rules() -> None:
    policy = Policy(principal="calculator", allow=("calc_*", "static_text"), deny=())

    assert policy.permits("calc_add")
    assert policy.permits("static_text")
    assert not policy.permits("mail_read")
