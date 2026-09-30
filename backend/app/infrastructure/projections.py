"""Normalized, transactionally synchronized storage alongside compatibility snapshots."""
from app.infrastructure.projection_patterns import sync_patterns
from app.infrastructure.projection_sources import sync_sources
from app.infrastructure.projection_sql import encoded, put
from app.infrastructure.projection_workflow import sync_workflow

__all__ = ["encoded", "put", "sync_project"]


def sync_project(c, p):
    sync_sources(c, p)
    sync_patterns(c, p)
    sync_workflow(c, p)
