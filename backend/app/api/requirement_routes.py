from fastapi import APIRouter

from app.api.schemas import ListResponse, ObjectResponse, ReadinessCheck, Resolve, Size
from app.application.readiness import check_operation
from app.application.requirement_queue import guided_queue
from app.application.requirements import requirements, resolve
from app.application.state import transition


def requirement_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.get("/projects/{pid}/requirements", response_model=ObjectResponse)
    def check(pid: str, size: Size = "L"):
        return requirements(repo.get(pid), size)

    @routes.post("/projects/{pid}/requirements/{key}/resolve", response_model=ObjectResponse)
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

    @routes.post("/projects/{pid}/requirements/check", response_model=ObjectResponse)
    def readiness(pid: str, body: ReadinessCheck):
        return check_operation(repo.get(pid), **body.model_dump())

    @routes.get("/projects/{pid}/requirements/blocking", response_model=ListResponse)
    def blocking(pid: str, size: Size = "L"):
        return requirements(repo.get(pid), size)["blockers"]

    @routes.get("/projects/{pid}/requirements/queue", response_model=ObjectResponse)
    def queue(pid: str, size: Size = "L"):
        return guided_queue(repo.get(pid), size)

    return routes
