"""Accuracy report route (T143): every drafted size against the block's client reference, as JSON."""
from fastapi import APIRouter

from app.api.models.accuracy import AccuracyReport
from app.application.accuracy.project_report import accuracy_report


def accuracy_routes(service):
    routes = APIRouter()

    @routes.get("/projects/{pid}/accuracy", response_model=AccuracyReport)
    def report(pid: str):
        return accuracy_report(service.repo.get(pid))

    return routes
