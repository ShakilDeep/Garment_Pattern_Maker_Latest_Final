from fastapi import APIRouter
from fastapi.responses import Response

from app.api.schemas import Generate, Grade, ListResponse, Nest, ObjectResponse
from app.application.calibration import calibration_request
from app.application.marker_compare import compare_markers
from app.application.readiness import check_operation


def pattern_routes(service):
    routes = APIRouter()
    repo = service.repo

    def pattern_version(pid: str, pattern_set_id: str):
        p = repo.get(pid)
        for candidate in [p.get("pattern"), *p.get("pattern_history", []), *p.get("grades", [])]:
            if candidate and candidate.get("id") == pattern_set_id:
                return candidate
        raise KeyError(pattern_set_id)

    @routes.post("/projects/{pid}/patterns/generate", response_model=ObjectResponse)
    def generate(pid: str, body: Generate):
        check_operation(repo.get(pid), "generate", body.size)
        return service.generate(repo.get(pid), body.size, body.allowance)

    @routes.post("/projects/{pid}/patterns/clear", response_model=ObjectResponse)
    def clear(pid: str):
        return service.clear_pattern(repo.get(pid))

    @routes.get("/projects/{pid}/patterns/{pattern_set_id}", response_model=ObjectResponse)
    def get_pattern(pid: str, pattern_set_id: str):
        return pattern_version(pid, pattern_set_id)

    @routes.post("/projects/{pid}/patterns/{pattern_set_id}/validate", response_model=ListResponse)
    def validate_version(pid: str, pattern_set_id: str):
        from app.infrastructure.validation import validate
        return validate(pattern_version(pid, pattern_set_id))

    @routes.post("/projects/{pid}/patterns/{pattern_set_id}/grade", response_model=ListResponse)
    def grade_version(pid: str, pattern_set_id: str, body: Grade):
        pattern = pattern_version(pid, pattern_set_id)
        return service.grade(repo.get(pid), body.sizes, pattern.get("seam_allowance", 0))

    @routes.post("/projects/{pid}/validate", response_model=ListResponse)
    def validate(pid: str):
        from app.infrastructure.geometry_adapter import validate as validate_geometry
        p = repo.get(pid)
        if not p["pattern"]:
            raise ValueError("Generate a pattern before validation")
        p["pattern"]["validation"] = validate_geometry(p["pattern"])
        repo.save(p, "validation_run")
        return p["pattern"]["validation"]

    @routes.post("/projects/{pid}/grade", response_model=ListResponse)
    def grade(pid: str, body: Grade):
        for selected in body.sizes:
            check_operation(repo.get(pid), "generate", selected)
        return service.grade(repo.get(pid), body.sizes)

    @routes.post("/projects/{pid}/markers/generate", response_model=ObjectResponse)
    def nest(pid: str, body: Nest):
        return service.nest(
            repo.get(pid), body.size, body.width, body.quantity, body.gap, body.quantities,
            body.seed, body.time_budget_ms, body.iterations, body.grain_policy,
        )

    @routes.get("/projects/{pid}/markers/compare", response_model=ObjectResponse)
    def compare(pid: str):
        project = repo.get(pid)
        return compare_markers(project.get("marker"), project.get("previous_marker"))

    @routes.get("/projects/{pid}/calibration-request")
    def calibration(pid: str):
        return Response(
            calibration_request(repo.get(pid)),
            media_type="text/plain",
            headers={"Content-Disposition": 'attachment; filename="production-calibration-request.txt"'},
        )

    return routes
