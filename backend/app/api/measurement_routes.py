from fastapi import APIRouter

from app.api.schemas import ListResponse, Measurements, ObjectResponse
from app.application.measurement_write import bound_changes, scoped_changes


def measurement_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.get("/projects/{pid}/measurements", response_model=ListResponse)
    def measurements(pid: str):
        return repo.get(pid)["measurements"]

    @routes.patch("/projects/{pid}/measurements", response_model=ObjectResponse)
    def update(pid: str, body: Measurements):
        return service.update_measurements(repo.get(pid), bound_changes(body.changes), body.size)

    @routes.patch("/projects/{pid}/measurements/{measurement_id}", response_model=ObjectResponse)
    def update_measurement(pid: str, measurement_id: str, body: Measurements):
        if measurement_id not in {row["key"] for row in repo.get(pid)["measurements"]}:
            raise KeyError(measurement_id)
        return service.update_measurements(
            repo.get(pid), scoped_changes(measurement_id, body.changes), body.size
        )

    @routes.post("/projects/{pid}/history/{direction}", response_model=ObjectResponse)
    def history(pid: str, direction: str):
        if direction not in ("undo", "redo"):
            raise ValueError("Choose undo or redo")
        return service.history(repo.get(pid), direction)

    return routes
