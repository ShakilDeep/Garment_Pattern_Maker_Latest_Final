from fastapi import APIRouter

from app.api.models.project import Project
from app.api.models.source import Measurement
from app.api.pagination import DEFAULT_PAGE_SIZE, Limit, Offset, Page, paginate
from app.api.schemas import Measurements
from app.application.measurement_write import scoped_changes


def measurement_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.get("/projects/{pid}/measurements", response_model=Page[Measurement])
    def measurements(pid: str, limit: Limit = DEFAULT_PAGE_SIZE, offset: Offset = 0):
        return paginate(repo.get(pid)["measurements"], limit, offset)

    @routes.patch("/projects/{pid}/measurements", response_model=Project)
    def update(pid: str, body: Measurements):
        return service.update_measurements(repo.get(pid), body.changes, body.size)

    @routes.patch("/projects/{pid}/measurements/{measurement_id}", response_model=Project)
    def update_measurement(pid: str, measurement_id: str, body: Measurements):
        if measurement_id not in {row["key"] for row in repo.get(pid)["measurements"]}:
            raise KeyError(measurement_id)
        return service.update_measurements(
            repo.get(pid), scoped_changes(measurement_id, body.changes), body.size
        )

    @routes.post("/projects/{pid}/history/{direction}", response_model=Project)
    def history(pid: str, direction: str):
        if direction not in ("undo", "redo"):
            raise ValueError("Choose undo or redo")
        return service.history(repo.get(pid), direction)

    return routes
