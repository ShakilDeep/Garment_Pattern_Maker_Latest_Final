"""Shared setup: a demo project that drafts the client 1078375 block from its accepted reference values."""
from collections.abc import Callable

from app.application.requirement_resolve import resolve
from app.application.service import Service
from app.infrastructure.repository import Repository

BLOCK = "shirt_1078375"
ANSWERS = {"units": "cm", "review": "confirmed", "placket": "workbook", "profile": BLOCK,
           "block_reference": "accepted"}
GRADED = ["S", "M", "XL", "XXL", "3XL"]


def shirt_project(path, graded: bool = True, prepare: Callable[[dict], None] | None = None) -> tuple[Service, dict]:
    """A 1078375 project drafted at L, and graded S–3XL unless ``graded`` is False; ``prepare`` may change
    the project (e.g. add a chart row) before it is drafted."""
    service = Service(Repository(f"sqlite:///{path}/named.db"))
    project = service.create("Client shirt", True)
    for key, value in ANSWERS.items():
        resolve(project, key, value)
    if prepare is not None:
        prepare(project)
    service.generate(project, "L")
    if graded:
        service.grade(service.repo.get(project["id"]), GRADED)
    return service, service.repo.get(project["id"])
