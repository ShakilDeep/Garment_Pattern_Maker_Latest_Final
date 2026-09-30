"""Untrusted provider envelopes validated against dispatch policy."""
from typing import Any, Literal

from pydantic import Field, model_validator

from app.application.assistant_policy import POLICY, StrictModel


class ProviderProposal(StrictModel):
    intent: Literal[
        "explain", "adjust_measurement", "set_allowance", "generate_pattern",
        "optimize_marker", "accept_mapping",
    ]
    target: str = Field(min_length=1, max_length=100)
    parameters: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    requires_confirmation: bool
    deterministic_service: Literal[
        "none", "measurements", "cad_commands", "pattern_generation", "marker", "requirements",
    ]
    post_action_validation: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_policy(self):
        schema, target, service, confirmation = POLICY[self.intent]
        self.parameters = schema.model_validate(self.parameters).model_dump()
        expected_target = target or self.parameters["measurement"]
        if (self.target, self.deterministic_service, self.requires_confirmation) != (
            expected_target, service, confirmation,
        ):
            raise ValueError("Proposal does not match application dispatch policy")
        return self


class Provenance(StrictModel):
    provider: str
    model: str
    prompt: str


class ActionEnvelope(ProviderProposal):
    id: str
    provenance: Provenance
    status: Literal["PROPOSED", "EXECUTED"] = "PROPOSED"
    created_at: str
    executed_at: str | None = None


class AssistantFailure(Exception):
    def __init__(self, unavailable=False):
        self.status_code = 503 if unavailable else 502
        self.code = "AI_UNAVAILABLE" if unavailable else "AI_OUTPUT_INVALID"
        super().__init__(
            "The assistant is unavailable. Retry or continue with manual controls."
            if unavailable
            else "The assistant returned an invalid proposal. No changes were made."
        )
