"""Offline StyleDetector: proposes nothing (every option ``unknown``) so the user chooses each one by hand.

It keeps style confirmation working with AI off (doc 15) without pretending to read the image.
"""
from app.domain.style_detect.proposal import StyleProposal, parse_proposal
from app.ports.style_detector import StyleImage


class LocalStyleDetector:
    name = "local"

    def detect(self, image: StyleImage) -> StyleProposal:
        return parse_proposal({}, self.name, "none")
