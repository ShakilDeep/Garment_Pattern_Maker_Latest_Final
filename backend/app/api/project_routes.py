from fastapi import APIRouter

from app.api.models.project import Deleted, Project, ProjectSummary
from app.api.pagination import DEFAULT_PAGE_SIZE, Limit, Offset, Page, paginate
from app.api.schemas import ProjectCreate, Rename


def project_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.get("/projects", response_model=Page[ProjectSummary])
    def projects(limit: Limit = DEFAULT_PAGE_SIZE, offset: Offset = 0):
        return paginate(repo.list(), limit, offset)

    @routes.post("/projects", response_model=Project)
    def create(body: ProjectCreate):
        return service.create(body.name, body.demo)

    @routes.get("/projects/{pid}", response_model=Project)
    def project(pid: str):
        return repo.get(pid)

    @routes.patch("/projects/{pid}", response_model=Project)
    def rename(pid: str, body: Rename):
        p = repo.get(pid)
        p["name"] = body.name
        return repo.save(p, "project_renamed")

    @routes.delete("/projects/{pid}", response_model=Deleted)
    def delete(pid: str):
        repo.delete(pid)
        return {"deleted": True}

    return routes
