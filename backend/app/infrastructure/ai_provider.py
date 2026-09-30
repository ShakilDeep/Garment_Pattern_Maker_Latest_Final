"""Offline deterministic assistant provider used by the local MVP."""

import re

from app.infrastructure.assistant_explanations import explain
from app.infrastructure.measurement_suggestions import suggest


class LocalAIProvider:
    name = "local"
    model = "deterministic-intent-v1"

    def propose(self, prompt, size, *, context=None):
        text = " ".join(prompt.lower().split())
        suggestion = suggest(text, context)
        if suggestion:
            return self._action("explain", "project", {"answer": suggestion}, False,
                                "none", "Review the original measurement definition; no values changed.", .5)
        accepted = re.search(r'accept mapping (?:of )?["\'](.+?)["\'] as ([a-z0-9_]+)', text)
        if accepted:
            return self._action(
                "accept_mapping", "project",
                {"source_label": accepted.group(1), "canonical_key": accepted.group(2)},
                True, "requirements",
                "Review the source definition; no measurement values are changed.", .6,
            )
        sleeve = re.search(r"sleeve.*?(\d+(?:\.\d+)?)\s*cm\s*(shorter|longer)", text)
        allowance = re.search(r"(?:add|set).*?(\d+(?:\.\d+)?)\s*cm.*?seam allowance", text)
        generated = re.search(r"generate.*?\b(?:size\s+)?(s|m|l|xl|xxl|3xl)\b", text)
        marker = re.search(r"(?:optimize|generate).*?marker.*?(\d+(?:\.\d+)?)\s*cm", text)
        if sleeve:
            delta = float(sleeve.group(1)) * (-1 if sleeve.group(2) == "shorter" else 1)
            return self._action("adjust_measurement", "sleeve_length",
                                {"measurement": "sleeve_length", "delta": delta, "size": size},
                                True, "measurements", "Re-run input and geometry validation after regeneration.", .99)
        if allowance:
            value = float(allowance.group(1))
            return self._action("set_allowance", "pattern", {"value": value}, True,
                                "cad_commands", "Run structural geometry validation.", .99)
        if generated:
            selected = generated.group(1).upper()
            return self._action("generate_pattern", "pattern", {"size": selected}, True,
                                "pattern_generation", "Run all registered geometry validators.", .98)
        if marker:
            return self._action("optimize_marker", "marker", {"width": float(marker.group(1)),
                                "size": size, "quantity": 1, "gap": .5}, True, "marker",
                                "Check overlap, bounds, grain and utilization.", .9)
        return self._action("explain", "project", {"answer": explain(text, context) or self._explain(text)}, False,
                            "none", "No project data is changed.", .75)

    def _action(self, intent, target, parameters, confirmation, service, validation, confidence):
        return {"intent": intent, "target": target, "parameters": parameters,
                "confidence": confidence, "requires_confirmation": confirmation,
                "deterministic_service": service, "post_action_validation": validation}

    def _explain(self, text):
        if "validation" in text:
            return "Validation checks geometry, compatible seams, notches, grainlines, and demo calibration warnings."
        if "unresolved" in text or "requirement" in text:
            return "Open Requirements to review missing values, source conflicts, units, and the demo drafting profile."
        return "I can explain requirements or validation and propose sleeve, seam allowance, pattern, or marker actions."


def get_ai_provider():
    from app.infrastructure.provider_factory import get_ai_provider as factory
    return factory()
