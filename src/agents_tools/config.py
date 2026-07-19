"""Safe loading of deployment-provided broker configuration."""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver

from agents_tools.policy import Policy


class ConfigurationError(RuntimeError):
    """Raised when required deployment configuration is malformed or unavailable."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def load_policies(policies_directory: Path) -> dict[str, Policy]:
    """Load one valid principal policy from each YAML file in a directory."""
    if not policies_directory.is_dir():
        msg = f"policies directory is not readable: {policies_directory}"
        raise ConfigurationError(msg)

    policies: dict[str, Policy] = {}
    for policy_file in sorted(policies_directory.glob("*.yaml")):
        policy = _parse_policy(policy_file)
        if policy.principal != policy_file.stem:
            msg = f"policy principal must match filename: {policy_file}"
            raise ConfigurationError(msg)
        if policy.principal in policies:
            msg = f"duplicate policy principal: {policy.principal}"
            raise ConfigurationError(msg)
        policies[policy.principal] = policy
    return policies


def validate_principals(
    principal_tokens: Mapping[str, str], policies: Mapping[str, Policy]
) -> None:
    """Require exactly one policy for every authenticated principal."""
    if set(principal_tokens) != set(policies):
        msg = "token and policy principal sets must match"
        raise ConfigurationError(msg)


def load_principal_tokens(token_file: Path) -> dict[str, str]:
    """Load the Vault-rendered principal-to-bearer-token mapping."""
    contents = _load_yaml_mapping(token_file)
    principals = contents.get("principals")
    if not isinstance(principals, Mapping) or not all(
        isinstance(principal, str) and isinstance(token, str) and token
        for principal, token in principals.items()
    ):
        msg = f"token file {token_file} must contain non-empty principals mapping"
        raise ConfigurationError(msg)
    token_mapping = {
        cast(str, principal): cast(str, token)
        for principal, token in principals.items()
    }
    if len(set(token_mapping.values())) != len(token_mapping):
        msg = "token file must not assign one bearer token to multiple principals"
        raise ConfigurationError(msg)
    return token_mapping


def _parse_policy(policy_file: Path) -> Policy:
    contents = _load_yaml_mapping(policy_file)
    allowed_keys = {"principal", "allow", "deny"}
    if any(key not in allowed_keys for key in contents):
        msg = f"policy {policy_file} has unknown keys"
        raise ConfigurationError(msg)
    principal = contents.get("principal")
    allow = _parse_patterns(contents.get("allow"), "allow", policy_file)
    deny = _parse_patterns(contents.get("deny"), "deny", policy_file)
    if not isinstance(principal, str) or not principal:
        msg = f"policy {policy_file} must contain a non-empty principal"
        raise ConfigurationError(msg)
    return Policy(principal=principal, allow=allow, deny=deny)


def _parse_patterns(
    value: object, field_name: str, policy_file: Path
) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(pattern, str) for pattern in value
    ):
        msg = f"policy {policy_file} {field_name} must be a list of strings"
        raise ConfigurationError(msg)
    return tuple(cast(str, pattern) for pattern in value)


def _load_yaml_mapping(path: Path) -> Mapping[str, object]:
    try:
        with path.open(encoding="utf-8") as stream:
            contents = yaml.load(stream, Loader=_UniqueKeySafeLoader)
    except (OSError, yaml.YAMLError) as error:
        msg = f"cannot load YAML configuration: {path}"
        raise ConfigurationError(msg) from error
    if not isinstance(contents, Mapping):
        msg = f"YAML configuration must be a mapping: {path}"
        raise ConfigurationError(msg)
    return contents
