"""Provider boundary for optional language assistance."""

from typing import Protocol


class AIProvider(Protocol):
    name: str
    model: str

    def propose(self, prompt: str, size: str, *, context: dict | None = None) -> dict:
        """Return an untrusted structured proposal for schema validation."""
