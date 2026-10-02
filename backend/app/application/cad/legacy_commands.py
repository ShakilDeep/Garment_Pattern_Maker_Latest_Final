"""The V5 commands (allowance, fold, notch) as registered Commands over a V5 snapshot (PM-05, Strangler Fig).

Their rules and messages are V5's, unchanged. A snapshot is {pattern, measurements, resolutions}; `apply`
edits a deep copy, never the caller's state.
"""

from copy import deepcopy
from dataclasses import dataclass, field

from app.application.cad.command import Params, require_params
from app.application.cad.registry import Registry
from app.infrastructure.geometry_adapter import apply_allowance

LEGACY_PARAMS = ("value", "piece_id")
MAX_ALLOWANCE_CM = 3
FOLD_PIECES = ("Back", "Yoke")
Snapshot = dict


def _piece(state: Snapshot, piece_id: object) -> dict:
    piece = next((p for p in state["pattern"]["pieces"] if p["id"] == piece_id), None)
    if piece is None:
        raise ValueError("Select a generated piece")
    return piece


@dataclass(frozen=True)
class SetAllowance:
    value: float
    name: str = field(default="allowance", init=False)

    def apply(self, state: Snapshot) -> Snapshot:
        edited = deepcopy(state)
        apply_allowance(edited["pattern"], self.value)
        return edited


@dataclass(frozen=True)
class SetFold:
    piece_id: object
    on_fold: bool
    name: str = field(default="fold", init=False)

    def apply(self, state: Snapshot) -> Snapshot:
        edited = deepcopy(state)
        piece = _piece(edited, self.piece_id)
        if piece["name"] not in FOLD_PIECES:
            raise ValueError("Fold annotation is supported only for Back and Yoke")
        piece["cut_on_fold"] = self.on_fold
        return edited


@dataclass(frozen=True)
class PlaceNotch:
    piece_id: object
    fraction: float
    name: str = field(default="notch", init=False)

    def apply(self, state: Snapshot) -> Snapshot:
        edited = deepcopy(state)
        piece = _piece(edited, self.piece_id)
        points = piece["points"]
        piece["notches"] = [points[int(self.fraction * (len(points) - 1))]]
        return edited


def allowance(params: Params) -> SetAllowance:
    require_params(params, LEGACY_PARAMS)
    value = params["value"]
    if not isinstance(value, (int, float)) or not 0 <= value <= MAX_ALLOWANCE_CM:
        raise ValueError(f"Seam allowance must be between 0 and {MAX_ALLOWANCE_CM} cm")
    return SetAllowance(value)


def fold(params: Params) -> SetFold:
    require_params(params, LEGACY_PARAMS)
    if params["value"] not in (0, 1):
        raise ValueError("Fold annotation is supported only for Back and Yoke")
    return SetFold(params["piece_id"], bool(params["value"]))


def notch(params: Params) -> PlaceNotch:
    require_params(params, LEGACY_PARAMS)
    value = params["value"]
    if not isinstance(value, (int, float)) or not 0 <= value < 1:
        raise ValueError("Notch position must be a fraction from 0 to below 1")
    return PlaceNotch(params["piece_id"], value)


def legacy_registry() -> Registry[Snapshot]:
    registry: Registry[Snapshot] = Registry()
    for name, factory in (("allowance", allowance), ("fold", fold), ("notch", notch)):
        registry.register(name, factory)
    return registry
