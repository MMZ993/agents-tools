"""Default-deny authorization policies for broker principals."""

from dataclasses import dataclass
from fnmatch import fnmatchcase


@dataclass(frozen=True, slots=True)
class Policy:
    """The allow and deny rules assigned to one authenticated principal."""

    principal: str
    allow: tuple[str, ...]
    deny: tuple[str, ...]

    def permits(self, tool_id: str) -> bool:
        """Return whether this policy permits a registered tool ID."""
        if _matches(self.deny, tool_id):
            return False
        return _matches(self.allow, tool_id)


def _matches(patterns: tuple[str, ...], tool_id: str) -> bool:
    return any(fnmatchcase(tool_id, pattern) for pattern in patterns)
