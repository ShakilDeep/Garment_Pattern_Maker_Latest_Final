"""Strategy: try deterministic marker pack variants within a time budget."""
from __future__ import annotations

import time
from copy import deepcopy

from app.infrastructure.marker_pack import pack_instances


def _permute(instances: list[dict], seed: int, round_index: int) -> list[dict]:
    items = deepcopy(instances)
    offset = (seed * 31 + round_index * 17) % max(len(items), 1)
    rotated = items[offset:] + items[:offset]
    rotated.sort(key=lambda p: (-p["height"] - (round_index % 3), -p["width"], p["name"], p["size"], p["instance"]))
    return rotated


def search_marker(
    instances: list[dict],
    width: float,
    gap: float,
    quantities: dict[str, int],
    ordered_sizes: list[str],
    patterns: dict,
    seed: int = 0,
    time_budget_ms: int = 250,
    iterations: int = 1,
    grain_policy: str = "vertical",
) -> dict:
    deadline = time.perf_counter() + max(time_budget_ms, 1) / 1000
    best: dict | None = None
    runs = 0
    for index in range(max(1, iterations)):
        if runs > 0 and time.perf_counter() >= deadline:
            break
        candidate = pack_instances(_permute(instances, seed, index), width, gap)
        runs += 1
        if best is None or candidate["utilization"] > best["utilization"]:
            best = candidate
    assert best is not None
    return {
        **best,
        "quantity": sum(quantities.values()),
        "quantities": {size: quantities[size] for size in ordered_sizes},
        "size": ordered_sizes[0] if len(ordered_sizes) == 1 else "Mixed",
        "strategy": "first_fit_decreasing_v2",
        "grain_policy": grain_policy,
        "pattern_id": patterns[ordered_sizes[0]]["id"] if len(ordered_sizes) == 1 else None,
        "pattern_ids": {size: patterns[size]["id"] for size in ordered_sizes},
        "seed": seed,
        "iterations": iterations,
        "iterations_run": runs,
        "time_budget_ms": time_budget_ms,
        "objective": round(best["utilization"], 6),
        "algorithm_version": "first_fit_decreasing_v2",
    }
