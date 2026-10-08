from fastapi import APIRouter

from app.api.models.project import Project
from app.api.models.requirement import ReadinessReport, RequirementItem, RequirementQueue, Requirements
from app.api.pagination import DEFAULT_PAGE_SIZE, Limit, Offset, Page, paginate
from app.api.schemas import ReadinessCheck, Resolve, Size
from app.application.project_sizes import require_sizes
from app.application.readiness import check_operation
from app.application.requirement_queue import guided_queue
from app.application.requirements import requirements, resolve
from app.application.state import transition


def requirement_routes(service):
    routes = APIRouter()
    repo = service.repo

    def sized(pid, size):
        project = repo.get(pid)
        require_sizes(project, [size])
        return project

    @routes.get("/projects/{pid}/requirements", response_model=Requirements)
    def check(pid: str, size: Size = "L"):
        return requirements(sized(pid, size), size)

    @routes.post("/projects/{pid}/requirements/{key}/resolve", response_model=Project)
    def resolution(pid: str, key: str, body: Resolve):
        p = resolve(repo.get(pid), key, **body.model_dump())
        if key.startswith("calibration:"):
            return repo.save(
                p, "requirement_resolved",
                {"key": key, "value": body.value, **p["resolution_metadata"][key]},
            )
        service.invalidate(p)
        target = "MEASUREMENTS_READY" if requirements(p)["ready"] else "NEEDS_INPUT"
        transition(p, target, "requirement_resolved")
        return repo.save(
            p, "requirement_resolved",
            {"key": key, "value": body.value, **p["resolution_metadata"][key]},
        )

    @routes.post("/projects/{pid}/requirements/check", response_model=ReadinessReport)
    def readiness(pid: str, body: ReadinessCheck):
        return check_operation(repo.get(pid), **body.model_dump())

    @routes.get("/projects/{pid}/requirements/blocking", response_model=Page[RequirementItem])
    def blocking(pid: str, size: Size = "L", limit: Limit = DEFAULT_PAGE_SIZE, offset: Offset = 0):
        return paginate(requirements(sized(pid, size), size)["blockers"], limit, offset)

    @routes.get("/projects/{pid}/requirements/queue", response_model=RequirementQueue)
    def queue(pid: str, size: Size = "L"):
        return guided_queue(sized(pid, size), size)

    return routes
