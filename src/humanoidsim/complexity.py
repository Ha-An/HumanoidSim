from __future__ import annotations

from collections import Counter
from typing import Any

from .catalog import TaskCatalog, load_task_catalog
from .execution import expand_task_steps
from .task_schema import TaskLevel, TaskSpec


def primitive_difficulty_weight(primitive: TaskSpec | str, *, catalog: TaskCatalog | None = None) -> float:
    """Return the OTC primitive difficulty weight for a primitive definition."""
    if isinstance(primitive, TaskSpec):
        spec = primitive
    else:
        loaded = catalog or load_task_catalog()
        spec = loaded.primitives[str(primitive).strip().upper()]
    payload = spec.metadata.get("operational_complexity", {}) if isinstance(spec.metadata, dict) else {}
    return float(payload.get("difficulty_weight", 0.0) or 0.0)


def task_complexity(task_code: str, args: dict[str, Any] | None = None, *, catalog: TaskCatalog | None = None) -> dict[str, Any]:
    """Compute single-task complexity as the weighted sum of primitive leaves.

    The formula follows C_task(t) = sum_k a_{t,k} d_k, where a_{t,k} is the
    number of leaf primitive occurrences in the expanded HumanoidSim task and
    d_k is the static primitive difficulty weight.
    """
    loaded = catalog or load_task_catalog()
    normalized_code = str(task_code).strip().upper()
    rows = expand_task_steps(normalized_code, dict(args or {}), catalog=loaded)
    primitive_counts: Counter[str] = Counter(
        str(row.get("call_code", "")).strip().upper()
        for row in rows
        if str(row.get("call_level", "")) == TaskLevel.PRIMITIVE_SKILL.value
    )
    primitive_counts = Counter({code: count for code, count in primitive_counts.items() if code})

    weights: dict[str, float] = {}
    contributions: dict[str, float] = {}
    missing_weights: list[str] = []
    total = 0.0
    for primitive_code, count in sorted(primitive_counts.items()):
        spec = loaded.primitives.get(primitive_code)
        if spec is None:
            missing_weights.append(primitive_code)
            weight = 0.0
        else:
            weight = primitive_difficulty_weight(spec)
        contribution = float(count) * weight
        weights[primitive_code] = round(weight, 3)
        contributions[primitive_code] = round(contribution, 3)
        total += contribution

    return {
        "task_code": normalized_code,
        "complexity": round(total, 3),
        "primitive_count": int(sum(primitive_counts.values())),
        "primitive_counts": dict(sorted(primitive_counts.items())),
        "primitive_weights": weights,
        "primitive_contributions": contributions,
        "missing_weights": missing_weights,
        "formula": "C_task(t)=sum_k a_tk*d_k",
    }


def task_complexity_index(*, catalog: TaskCatalog | None = None) -> dict[str, dict[str, Any]]:
    """Compute static complexity for every registered HumanoidSim task."""
    loaded = catalog or load_task_catalog()
    return {
        task_code: task_complexity(task_code, catalog=loaded)
        for task_code in sorted(loaded.tasks)
    }

