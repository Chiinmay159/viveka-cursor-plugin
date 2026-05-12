"""
Trace Storage — Persistent record of every governance decision.

Every decision Viveka makes is saved as a JSON file for:
    - Audit trails
    - Pattern analysis over time
    - Replay and review
    - Training data for future improvements

Storage location: ~/.viveka/traces/
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from viveka.models.core import GovernanceDecision


TRACE_DIR = Path.home() / ".viveka" / "traces"


def _ensure_dir():
    TRACE_DIR.mkdir(parents=True, exist_ok=True)


def _decision_to_dict(decision: GovernanceDecision) -> dict:
    """Convert a GovernanceDecision to a serializable dict."""
    data = decision.model_dump(mode="json")

    # Add convenience fields for listing/searching
    data["_meta"] = {
        "schema_version": "0.3.3",
        "task": decision.context.task,
        "risk_mode": decision.risk_mode.value,
        "selected": (
            decision.selected_option.id
            if decision.selected_option
            else "escalated"
        ),
        "escalated": decision.escalated_to_human,
        "has_synthesis": decision.synthesis is not None,
        "options_count": len(decision.options_generated),
        "survivors_count": len([
            r for r in decision.stress_test_results if r.survived
        ]),
    }

    return data


def save_trace(decision: GovernanceDecision) -> Path:
    """
    Save a governance decision to disk.
    Returns the path to the saved trace file.
    """
    _ensure_dir()

    data = _decision_to_dict(decision)
    filename = f"{decision.id}.json"
    filepath = TRACE_DIR / filename

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return filepath


def load_trace(decision_id: str) -> dict | None:
    """Load a governance trace by decision ID."""
    _ensure_dir()

    filepath = TRACE_DIR / f"{decision_id}.json"
    if not filepath.exists():
        # Try partial match
        matches = list(TRACE_DIR.glob(f"*{decision_id}*.json"))
        if len(matches) == 1:
            filepath = matches[0]
        elif len(matches) > 1:
            return None  # ambiguous
        else:
            return None

    with open(filepath, "r") as f:
        data = json.load(f)

    # Version check — warn if schema has drifted
    meta = data.get("_meta", {})
    trace_version = meta.get("schema_version", "unknown")
    if trace_version not in ("0.3.0", "0.3.2", "0.3.3") and trace_version != "unknown":
        data["_version_warning"] = (
            f"Trace schema {trace_version} may not match current 0.3.3"
        )

    return data


def list_traces(n: int = 10) -> list[dict]:
    """
    List recent governance traces.
    Returns list of summary dicts, newest first.
    """
    _ensure_dir()

    trace_files = sorted(
        TRACE_DIR.glob("gov_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:n]

    summaries = []
    for filepath in trace_files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            meta = data.get("_meta", {})
            summaries.append({
                "id": data.get("id", filepath.stem),
                "timestamp": data.get("timestamp", "unknown"),
                "risk_mode": meta.get("risk_mode", data.get("risk_mode", "?")),
                "task": meta.get("task", "?"),
                "selected": meta.get("selected", "?"),
                "escalated": meta.get("escalated", False),
                "has_synthesis": meta.get("has_synthesis", False),
                "options_count": meta.get("options_count", 0),
                "survivors_count": meta.get("survivors_count", 0),
                "filepath": str(filepath),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return summaries


def get_trace_stats() -> dict:
    """
    Aggregate statistics across all traces.
    Useful for understanding governance patterns over time.
    """
    _ensure_dir()

    traces = list_traces(n=1000)
    if not traces:
        return {"total": 0}

    total = len(traces)
    escalated = sum(1 for t in traces if t.get("escalated", False))
    by_mode = {}
    for t in traces:
        mode = t.get("risk_mode", "unknown")
        by_mode[mode] = by_mode.get(mode, 0) + 1

    with_synthesis = sum(1 for t in traces if t.get("has_synthesis", False))
    avg_survivors = (
        sum(t.get("survivors_count", 0) for t in traces) / total
        if total > 0 else 0
    )

    return {
        "total": total,
        "escalated": escalated,
        "escalation_rate": escalated / total if total > 0 else 0,
        "by_risk_mode": by_mode,
        "with_synthesis": with_synthesis,
        "avg_survivors": round(avg_survivors, 2),
    }
