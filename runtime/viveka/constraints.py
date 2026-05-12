"""
Constraint Validation — Deterministic hard gate for user-declared constraints.

Extracted from v0.5.0 evaluator.py. No LLM calls.

Validates proposed actions or strategies against user-declared hard constraints
using keyword-based pattern matching. This is a safety gate the LLM cannot
override — if a strategy violates "threading primitives only", the keyword
matcher catches "SQLite" in the proposal and rejects it.

Usage:
    violations = validate_against_constraints(
        text="Use SQLite for persistence with thread-safe WAL mode",
        constraints=["threading primitives only", "no external dependencies"],
    )
    # → ["Constraint 'threading primitives only' violated: option uses SQLite"]
"""

from __future__ import annotations


def validate_against_constraints(
    text: str,
    constraints: list[str],
) -> list[str]:
    """
    Check text against hard constraints. Returns list of violations (empty = valid).
    Deterministic keyword matching — not a substitute for LLM understanding,
    but a hard gate that catches obvious violations.
    """
    violations = []
    text_lower = text.lower()

    for constraint in constraints:
        c_lower = constraint.lower()

        if " only" in c_lower:
            allowed = c_lower.split(" only")[0].strip()
            exclusion_indicators = _infer_exclusions(allowed, text_lower)
            if exclusion_indicators:
                violations.append(
                    f"Constraint '{constraint}' violated: "
                    f"option uses {', '.join(exclusion_indicators)}"
                )

        for neg_pattern in [
            "no ", "without ", "must not use ", "do not use ",
            "cannot use ", "don't use ", "must not require ",
        ]:
            if neg_pattern in c_lower:
                excluded = c_lower.split(neg_pattern, 1)[1].strip().rstrip(".")
                if _text_mentions(text_lower, excluded):
                    violations.append(
                        f"Constraint '{constraint}' violated: "
                        f"option references '{excluded}'"
                    )

    return violations


def filter_by_constraints(
    items: list[dict],
    constraints: list[str],
    text_key: str = "description",
) -> tuple[list[dict], list[dict]]:
    """
    Filter a list of dicts by constraint compliance.

    Each item's text is extracted via text_key (or concatenated from
    multiple keys if text_key is a comma-separated list).

    Returns: (valid_items, rejection_log)
    """
    if not constraints:
        return items, []

    valid = []
    rejections = []

    for item in items:
        keys = [k.strip() for k in text_key.split(",")]
        searchable = " ".join(str(item.get(k, "")) for k in keys)
        violations = validate_against_constraints(searchable, constraints)
        if violations:
            rejections.append({
                "item": item.get("id", item.get("name", str(item)[:50])),
                "violations": violations,
            })
        else:
            valid.append(item)

    return valid, rejections


_PERSISTENCE_ALTERNATIVES = {
    "sqlite": "SQLite",
    "database": "database",
    "redis": "Redis",
    "file-based": "file-based storage",
    "filesystem": "filesystem storage",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "memcached": "memcached",
    "dynamodb": "DynamoDB",
    "environment variable": "environment variables",
}

_THREADING_TERMS = {
    "threading", "thread", "lock", "mutex", "condition",
    "semaphore", "barrier", "event", "rlock",
}


def _infer_exclusions(allowed: str, text: str) -> list[str]:
    """Given an 'X only' constraint, detect text that uses non-X approaches."""
    found = []

    if any(t in allowed for t in _THREADING_TERMS):
        for term, label in _PERSISTENCE_ALTERNATIVES.items():
            if term in text:
                found.append(label)

    return found


_EXTERNAL_DEPENDENCY_TERMS = {
    "redis": "Redis", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mysql": "MySQL", "mongodb": "MongoDB", "mongo": "MongoDB",
    "dynamodb": "DynamoDB", "elasticsearch": "Elasticsearch",
    "rabbitmq": "RabbitMQ", "kafka": "Kafka", "memcached": "memcached",
    "docker": "Docker", "kubernetes": "Kubernetes",
    "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "sqlite": "SQLite", "celery": "Celery",
    "nginx": "nginx", "apache": "Apache",
}

_EXCLUSION_EXPANSIONS = {
    "external dependencies": _EXTERNAL_DEPENDENCY_TERMS,
    "external services": _EXTERNAL_DEPENDENCY_TERMS,
    "third-party": _EXTERNAL_DEPENDENCY_TERMS,
    "third party": _EXTERNAL_DEPENDENCY_TERMS,
}


def _text_mentions(text: str, excluded: str) -> bool:
    """Check if text mentions the excluded concept (fuzzy keyword match)."""
    if excluded in text:
        return True

    expansion = _EXCLUSION_EXPANSIONS.get(excluded)
    if expansion:
        for term in expansion:
            if term in text:
                return True

    words = excluded.split()
    if len(words) >= 2:
        return all(w in text for w in words if len(w) > 3)
    return False
