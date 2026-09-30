"""Port: Strategy for garment/document classification from explicit text."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentClassifier(Protocol):
    def classify(self, text: str, filename: str) -> dict:
        """Return garment/document labels without inventing measurements."""
