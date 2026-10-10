"""Routes for style detection (T132): the option table, detect from an upload, confirm the user's choice."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, UploadFile

from app.api.models.project import Project
from app.api.models.style_detect import OptionSpecOut, StyleChoicesIn, StyleDetection
from app.application.style_service import StyleDetectService
from app.domain.style_detect.schema import ALL_SPECS
from app.infrastructure.image_prep import MAX_BYTES, UnsupportedImage

MAX_PDF_PAGE = 500


def style_detect_routes(styles: StyleDetectService):
    routes = APIRouter()

    @routes.get("/style/options", response_model=list[OptionSpecOut])
    def options():
        return [asdict(spec) for spec in ALL_SPECS]

    @routes.post("/projects/{pid}/style/detect", response_model=StyleDetection)
    async def detect(pid: str, file: UploadFile, page: int = Query(1, ge=1, le=MAX_PDF_PAGE)):
        data = await file.read(MAX_BYTES + 1)
        await file.close()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Maximum image size is 10 MB")
        try:
            return styles.detect(pid, data, page)
        except UnsupportedImage as unsupported:
            raise HTTPException(415, str(unsupported)) from None

    @routes.post("/projects/{pid}/style/choices", response_model=Project)
    def confirm(pid: str, body: StyleChoicesIn):
        return styles.confirm(pid, body.garment, body.fit, body.options)

    return routes
