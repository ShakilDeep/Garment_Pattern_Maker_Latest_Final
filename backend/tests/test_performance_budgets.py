from time import perf_counter

from app.application.service import Service
from app.infrastructure.repository import Repository


def elapsed(operation):
    started = perf_counter()
    result = operation()
    return perf_counter() - started, result


def test_deterministic_operation_budgets(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/performance.db"))
    project = service.create("Performance", True)
    project["resolutions"] = {
        "units": "cm",
        "review": "confirmed",
        "profile": "demo_v1",
        "placket": "workbook",
    }
    generation_time, _ = elapsed(lambda: service.generate(project, "L"))
    validation_time, _ = elapsed(lambda: service.build(project, "L"))
    marker_time, _ = elapsed(lambda: service.nest(project, "L", 150, 2, 0.5))
    assert generation_time < 2
    assert validation_time < 1
    assert marker_time < 5
