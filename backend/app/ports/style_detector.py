"""Port: Strategy that proposes style options from one garment image (T132); the user confirms them."""
from dataclasses import dataclass
from typing import Protocol

from app.domain.style_detect.proposal import StyleProposal


@dataclass(frozen=True)
class StyleImage:
    mime: str
    data: bytes


class StyleDetector(Protocol):
    name: str

    def detect(self, image: StyleImage) -> StyleProposal:
        """Untrusted options parsed against the fixed table; raises ProviderFailure."""
        ...
