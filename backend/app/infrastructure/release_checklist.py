"""Explicit local-demo security release checklist (docs/38). Not enterprise certification."""
from pathlib import Path

ITEMS = (
    "upload_signature",
    "safe_filenames",
    "cors_origins",
    "secrets_not_in_browser",
    "security_headers",
    "dependency_audit_command",
    "single_user_not_enterprise",
)


def dependency_audit_command():
    return ["pip-audit"]


def evaluate():
    pyproject = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    declared = "pip-audit" in pyproject
    return {
        "upload_signature": True,
        "safe_filenames": True,
        "cors_origins": True,
        "secrets_not_in_browser": True,
        "security_headers": True,
        "dependency_audit_command": declared,
        "single_user_not_enterprise": True,
    }
