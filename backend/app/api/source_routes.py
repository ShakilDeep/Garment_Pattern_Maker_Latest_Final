from pathlib import PurePath

from fastapi import APIRouter, HTTPException, UploadFile

from app.api.models.project import Project
from app.api.models.source import Document, ParseStatus, SourceComparison
from app.api.pagination import DEFAULT_PAGE_SIZE, Limit, Offset, Page, paginate


def source_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.post("/projects/{pid}/documents", response_model=Project)
    async def upload(pid: str, file: UploadFile, replace: bool = False):
        p = repo.get(pid)
        filename = PurePath((file.filename or "").replace("\\", "/")).name
        allowed = {
            ".pdf": ["application/pdf"],
            ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        }
        ext = PurePath(filename).suffix.lower()
        if ext not in allowed or file.content_type not in [*allowed[ext], "application/octet-stream"]:
            raise HTTPException(415, "Upload an XLSX workbook or PDF tech pack")
        data = await file.read(10_000_001)
        await file.close()
        if len(data) > 10_000_000:
            raise HTTPException(413, "Maximum upload size is 10 MB")
        signatures = {".pdf": b"%PDF-", ".xlsx": b"PK\x03\x04"}
        if not data.startswith(signatures[ext]):
            raise HTTPException(415, f"File signature does not match {ext} content")
        try:
            service.import_data(p, filename, data, replace=replace)
        except (ValueError, KeyError):
            raise
        except Exception as exc:
            raise ValueError(
                "This document could not be parsed. Check that the file is a valid, unencrypted XLSX or searchable PDF."
            ) from exc
        return repo.save(p, "document_imported", filename)

    @routes.get("/projects/{pid}/parse", response_model=ParseStatus, operation_id="parse_project_get")
    @routes.post("/projects/{pid}/parse", response_model=ParseStatus, operation_id="parse_project_post")
    def parse_project(pid: str):
        p = repo.get(pid)
        return {
            "project_id": pid,
            "status": "complete" if p.get("measurements") or p.get("techpack") else "empty",
            "documents": p.get("documents", []),
            "measurements": len(p.get("measurements", [])),
            "techpack": bool(p.get("techpack")),
            "techpack_confidence": (p.get("techpack") or {}).get("confidence"),
            "issues": [
                cell.get("issue")
                for row in p.get("measurements", [])
                for cell in row.get("values", {}).values()
                if cell.get("issue")
            ] + [
                f"{item['key']}: {item['why']}"
                for item in (p.get("techpack") or {}).get("issues", [])
            ],
        }

    @routes.get("/projects/{pid}/documents", response_model=Page[Document])
    def documents(pid: str, limit: Limit = DEFAULT_PAGE_SIZE, offset: Offset = 0):
        return paginate(repo.get(pid).get("documents", []), limit, offset)

    @routes.post("/projects/{pid}/sources/clear", response_model=Project)
    def clear_sources(pid: str):
        return service.clear_sources(repo.get(pid))

    @routes.get("/projects/{pid}/documents/compare", response_model=SourceComparison)
    def compare_documents(pid: str):
        project = repo.get(pid)
        docs = project.get("documents", [])
        return {
            "documents": docs,
            "same_content": len({d["sha256"] for d in docs}) < 2,
            "active": [d for d in docs if d.get("active", True)],
            "measurement_versions": project.get("measurement_versions", []),
            "techpack_versions": project.get("techpack_versions", []),
        }

    return routes
