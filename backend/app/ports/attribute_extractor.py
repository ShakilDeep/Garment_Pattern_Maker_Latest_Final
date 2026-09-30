"""Port: Strategy for tech-pack attribute extraction."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class AttributeExtractor(Protocol):
    def extract(self, pages: list, filename: str) -> tuple[list, list]:
        """Return (attributes, issues) from searchable PDF page dicts."""
