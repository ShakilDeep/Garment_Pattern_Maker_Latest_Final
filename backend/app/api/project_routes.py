from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.api.schemas import ObjectResponse, ProjectCreate, Rename


def project_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.get("/projects")
    def projects(limit: Annotated[int | None, Query(ge=1, le=100)] = None, offset: Annotated[int, Query(ge=0)] = 0):
        rows = repo.list()
        page = rows if limit is None else rows[offset:offset + limit]
        return JSONResponse(page, headers={"X-Total-Count": str(len(rows))})

    @routes.post("/projects", response_model=ObjectResponse)
    def create(body: ProjectCreate):
        return service.create(body.name, body.demo)

    @routes.get("/projects/{pid}", response_model=ObjectResponse)
    def project(pid: str):
        return repo.get(pid)

    @routes.patch("/projects/{pid}", response_model=ObjectResponse)
    def rename(pid: str, body: Rename):
        p = repo.get(pid)
        p["name"] = body.name
        return repo.save(p, "project_renamed")

    @routes.delete("/projects/{pid}", response_model=ObjectResponse)
    def delete(pid: str):
        repo.delete(pid)
        return {"deleted": True}

    return routes
