from pathlib import Path

import pytest

from agents_tools.config import load_policies


def test_load_policies_reads_one_principal_per_yaml_file(tmp_path: Path) -> None:
    (tmp_path / "calculator.yaml").write_text(
        "principal: calculator\nallow: [calc_*]\ndeny: [calc_sub]\n"
    )

    policies = load_policies(tmp_path)

    assert policies["calculator"].permits("calc_add")


def test_load_policies_rejects_malformed_policy(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError

    (tmp_path / "reader.yaml").write_text(
        "principal: reader\nallow: invalid\ndeny: []\n"
    )

    with pytest.raises(ConfigurationError, match="allow must be a list"):
        load_policies(tmp_path)


def test_load_policies_rejects_unknown_policy_keys(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError

    (tmp_path / "reader.yaml").write_text(
        "principal: reader\nallow: [static_text]\ndeny_tools: [static_text]\ndeny: []\n"
    )

    with pytest.raises(ConfigurationError, match="unknown keys"):
        load_policies(tmp_path)


def test_load_policies_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError

    (tmp_path / "reader.yaml").write_text(
        "principal: reader\nallow: [static_text]\nallow: [calc_add]\ndeny: []\n"
    )

    with pytest.raises(ConfigurationError, match="cannot load YAML"):
        load_policies(tmp_path)


def test_load_principal_tokens_rejects_malformed_mapping(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError, load_principal_tokens

    token_file = tmp_path / "tokens.yaml"
    token_file.write_text("principals: []\n")

    with pytest.raises(ConfigurationError):
        load_principal_tokens(token_file)


def test_load_principal_tokens_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError, load_principal_tokens

    token_file = tmp_path / "tokens.yaml"
    token_file.write_text("principals:\n  reader: first\n  reader: second\n")

    with pytest.raises(ConfigurationError, match="cannot load YAML"):
        load_principal_tokens(token_file)


def test_load_principal_tokens_rejects_duplicate_tokens(tmp_path: Path) -> None:
    from agents_tools.config import ConfigurationError, load_principal_tokens

    token_file = tmp_path / "tokens.yaml"
    token_file.write_text("principals:\n  first: duplicate\n  second: duplicate\n")

    with pytest.raises(ConfigurationError, match="must not assign"):
        load_principal_tokens(token_file)


def test_fixture_policies_prove_distinct_principal_scopes() -> None:
    policies = load_policies(Path(__file__).parent / "fixtures" / "policies")

    assert policies["calculator"].permits("calc_add")
    assert not policies["calculator"].permits("calc_sub")
    assert policies["reader"].permits("static_text")
    assert not policies["reader"].permits("calc_add")
