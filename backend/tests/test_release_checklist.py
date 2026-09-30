"""Release checklist from docs/38 must be explicit and gated."""
from pathlib import Path

from app.infrastructure.release_checklist import ITEMS, dependency_audit_command, evaluate

ROOT = Path(__file__).resolve().parents[2]


def test_release_checklist_covers_mvp_security_baseline():
    required = {
        "upload_signature",
        "safe_filenames",
        "cors_origins",
        "secrets_not_in_browser",
        "security_headers",
        "dependency_audit_command",
        "single_user_not_enterprise",
    }
    assert required <= set(ITEMS)
    status = evaluate()
    assert status["single_user_not_enterprise"] is True
    assert status["dependency_audit_command"] is True
    assert "pip-audit" in " ".join(dependency_audit_command())


def test_pyproject_declares_pip_audit_for_release_gate():
    text = (ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    assert "pip-audit" in text
