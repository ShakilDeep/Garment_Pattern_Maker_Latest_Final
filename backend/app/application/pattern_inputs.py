"""Input snapshots stored on generated pattern versions, and project views built from them."""
from copy import deepcopy

from app.application.errors import NotReady

INPUT_KEYS = ("measurements", "resolutions", "techpack")


def snapshot_inputs(p):
    """Parameter object persisted on a generated version: everything build() reads besides the size."""
    return {key: deepcopy(p.get(key)) for key in INPUT_KEYS}


def strip_inputs(version):
    """Imported geometry is untrusted: drop any client-supplied input snapshot (it becomes a legacy version)."""
    if isinstance(version, dict):
        version.pop("inputs", None)
    return version


def version_view(p, version):
    """Project view whose drafting inputs are those the version was generated from."""
    if any(grade.get("id") == version.get("id") for grade in p.get("grades", [])):
        raise ValueError("Grade from a base pattern version, not from a graded size")
    inputs = version.get("inputs")
    if not isinstance(inputs, dict) or any(key not in inputs for key in INPUT_KEYS):
        if version.get("id") == (p.get("pattern") or {}).get("id") and not version.get("stale"):
            return p
        raise NotReady("This pattern version predates stored inputs; regenerate it before grading")
    return {**p, **{key: deepcopy(inputs[key]) for key in INPUT_KEYS}}
