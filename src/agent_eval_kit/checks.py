from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def redact(value: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        try:
            value = re.sub(pattern, "[REDACTED]", value)
        except re.error as exc:
            raise ValueError(f"invalid redaction pattern {pattern!r}: {exc}") from exc
    return value


def _json_subset(actual: Any, expected: Any, path: str = "$") -> list[str]:
    """Return deterministic mismatch descriptions for an expected JSON subset."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        failures: list[str] = []
        for key in sorted(expected):
            if key not in actual:
                failures.append(f"{path}.{key}: missing")
            else:
                failures.extend(_json_subset(actual[key], expected[key], f"{path}.{key}"))
        return failures
    if isinstance(expected, list):
        if actual != expected:
            return [f"{path}: expected {expected!r}, got {actual!r}"]
        return []
    if actual != expected:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def check_file(root: Path, expectation: Any) -> dict[str, Any]:
    path = root / expectation.path
    exists = path.is_file()
    passed = exists == expectation.exists
    detail = f"{expectation.path}: {'present' if exists else 'missing'}"
    if expectation.exists and exists:
        text = path.read_text(encoding="utf-8")
        missing = [value for value in expectation.contains if value not in text]
        if missing:
            passed = False
            detail += f"; missing text {missing!r}"
        if expectation.json is not None:
            try:
                actual = json.loads(text)
            except json.JSONDecodeError as exc:
                passed = False
                detail += f"; invalid JSON ({exc.msg})"
            else:
                failures = _json_subset(actual, expectation.json)
                if failures:
                    passed = False
                    detail += "; " + "; ".join(failures)
    elif not passed:
        detail += "; unexpected file state"
    return {"name": f"file:{expectation.path}", "passed": passed, "detail": detail}


def check_text(name: str, actual: str, expected: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "name": f"{name}:{value}",
            "passed": value in actual,
            "detail": f"{name} contains {value!r}",
        }
        for value in expected
    ]
