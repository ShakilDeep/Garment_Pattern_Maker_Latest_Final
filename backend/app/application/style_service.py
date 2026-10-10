"""Use-case facade for style detection (T132): prepare the image, ask the detector, record the user's choice."""
from collections.abc import Callable

from app.application.style_detection import confirm_style, detect_style
from app.ports.style_detector import StyleDetector, StyleImage

ImagePrep = Callable[[bytes, int], StyleImage]


class StyleDetectService:
    def __init__(self, service, detector: StyleDetector, prepare: ImagePrep):
        self._service, self._detector, self._prepare = service, detector, prepare

    def _active(self, pid: str) -> dict:
        project = self._service.repo.get(pid)
        self._service._ensure_active(project)
        return project

    def detect(self, pid: str, data: bytes, page: int) -> dict:
        project = self._active(pid)
        found = detect_style(project, self._prepare(data, page), self._detector, data, page)
        proposal = found["proposal"]
        self._service.repo.save(project, "style_detected", {key: proposal[key] for key in
                                                            ("provider", "model", "prompt_version")})
        return found

    def confirm(self, pid: str, garment: str, fit: str, options: dict[str, str]) -> dict:
        project = self._active(pid)
        changed = confirm_style(project, garment, fit, options)
        return self._service.repo.save(project, "style_confirmed", {"garment": garment, "changed": changed})
