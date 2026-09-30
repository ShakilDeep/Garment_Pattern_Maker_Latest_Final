"""Validate assistant output and dispatch confirmed actions to deterministic services."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError

from app.application.assistant_context import build_context
from app.application.assistant_contracts import ActionEnvelope, AssistantFailure, ProviderProposal
from app.application.commands import execute as execute_command
from app.application.mapping_acceptance import apply as accept_mapping
from app.application.service import NotReady


def propose(service, project, provider, prompt, size, piece_id=None):
    context = build_context(project, size, piece_id)
    try:
        raw = provider.propose(prompt, size, context=context)
    except Exception:  # noqa: BLE001 -- isolate provider faults without leaking credentials or response text
        logging.getLogger("garment").warning("Assistant provider unavailable")
        raise AssistantFailure(unavailable=True) from None
    try:
        raw = ProviderProposal.model_validate(raw).model_dump()
    except ValidationError:
        raise AssistantFailure() from None
    action = ActionEnvelope.model_validate(
        {
            **raw,
            "id": str(uuid4()),
            "provenance": {"provider": provider.name, "model": provider.model, "prompt": prompt},
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    item = action.model_dump()
    project.setdefault("ai_proposals", []).append(item)
    service.repo.save(project, "assistant_proposed", {"proposal_id": item["id"], "intent": item["intent"]})
    return item


def execute(service, project, proposal_id, confirmed):
    item = next((p for p in project.get("ai_proposals", []) if p["id"] == proposal_id), None)
    if item is None:
        raise KeyError(proposal_id)
    action = ActionEnvelope.model_validate(item)
    if action.status == "EXECUTED":
        raise NotReady("This assistant proposal has already been executed")
    if action.requires_confirmation and not confirmed:
        raise NotReady("Confirm this assistant proposal before applying it")
    result = _dispatch(service, project, action)
    item["status"] = "EXECUTED"
    item["executed_at"] = datetime.now(UTC).isoformat()
    service.repo.save(project, "assistant_executed", {"proposal_id": action.id, "intent": action.intent})
    return result


def _dispatch(service, project, action):
    values = action.parameters
    if action.intent == "explain":
        return {"project": project, "answer": values["answer"], "validation": {"status": "NO_CHANGE"}}
    if action.intent == "accept_mapping":
        project = accept_mapping(project, values["source_label"], values["canonical_key"])
        return {"project": project, "validation": {"status": "NO_VALUE_CHANGE"}}
    if action.intent == "adjust_measurement":
        row = next((r for r in project["measurements"] if r["key"] == values["measurement"]), None)
        cell = row.get("values", {}).get(values["size"]) if row else None
        if not cell or not isinstance(cell.get("value"), (int, float)):
            raise NotReady("The selected measurement has no value for this size")
        current = cell["value"]
        if not 0 < current + values["delta"] <= 500:
            raise ValueError("The resulting measurement must be greater than 0 and at most 500 cm")
        project = service.update_measurements(
            project, {values["measurement"]: current + values["delta"]}, values["size"]
        )
        return {"project": project, "validation": {"status": "INPUTS_INVALIDATED"}}
    if action.intent == "set_allowance":
        project = execute_command(service, project, "allowance", values["value"])
        return {"project": project, "validation": {"status": "GEOMETRY_VALIDATED"}}
    if action.intent == "generate_pattern":
        pattern = service.generate(project, values["size"])
        return {"project": project, "pattern": pattern, "validation": {"status": "GEOMETRY_VALIDATED"}}
    marker = service.nest(project, values["size"], values["width"], values["quantity"], values["gap"])
    return {"project": project, "marker": marker, "validation": {"status": "MARKER_VALIDATED"}}
