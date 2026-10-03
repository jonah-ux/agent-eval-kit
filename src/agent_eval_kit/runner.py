"""Execution and comparison primitives for Agent Eval Kit.

The module keeps command execution intentionally small and explicit.  It does
not sandbox a command; callers are responsible for running untrusted work in
an appropriate environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from typing import Any


MATRIX_SCHEMA = "agent-eval/matrix/v1"
RECEIPT_SCHEMA = "agent-eval/receipt/v1"
MAX_TRIALS = 100


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _receipt_sha256(receipt: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return _sha256(_canonical_json(unsigned))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _expected_exit(fixture: Mapping[str, Any]) -> int:
    expected = fixture.get("expect_exit", 0)
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise ValueError("expect_exit must be an integer")
    return expected


def _timeout(fixture: Mapping[str, Any]) -> float:
    timeout = fixture.get("timeout", 30)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive number")
    return float(timeout)


def _expected_stdout(fixture: Mapping[str, Any]) -> list[str]:
    expected = fixture.get("expect_stdout", [])
    if not isinstance(expected, list) or any(not isinstance(fragment, str) for fragment in expected):
        raise ValueError("expect_stdout must be a list of strings")
    return expected


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    """Stop the shell and descendants after a fixture timeout."""

    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass


def _execute(
    rendered_command: str,
    timeout: float,
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: Any = None,
    input_text: str | None = None,
) -> dict[str, Any]:
    """Run one shell command and capture its observable behavior.

    Returns ``exit_code`` (``None`` on timeout), ``stdout``, ``stderr``,
    ``timed_out`` and ``duration_ms``.  A timeout kills the whole process
    group and is reported, not raised.  ``input_text``, when given, is written
    to the command's stdin (and overrides ``stdin``).
    """

    started = time.monotonic()
    timed_out = False
    process = subprocess.Popen(
        rendered_command,
        shell=True,
        text=True,
        stdin=subprocess.PIPE if input_text is not None else stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        cwd=cwd,
        env=None if env is None else dict(env),
    )
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout)
        exit_code: int | None = process.returncode
        stdout = _text(stdout)
        stderr = _text(stderr)
    except subprocess.TimeoutExpired as exc:
        _kill_process_group(process)
        stdout_after_kill, stderr_after_kill = process.communicate()
        timed_out = True
        exit_code = None
        stdout = _text(stdout_after_kill if stdout_after_kill is not None else exc.stdout)
        stderr = _text(stderr_after_kill if stderr_after_kill is not None else exc.stderr)

    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def _wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """Return the Wilson score interval ``[lo, hi]`` for ``k`` of ``n``.

    ``n == 0`` has no defined rate, so it returns ``None`` rather than a
    misleading ``[0, 0]``.  Bounds are rounded to four decimals.
    """

    if isinstance(k, bool) or isinstance(n, bool) or not isinstance(k, int) or not isinstance(n, int):
        raise ValueError("wilson k and n must be integers")
    if n < 0 or k < 0 or k > n:
        raise ValueError("wilson requires 0 <= k <= n")
    if n == 0:
        return None
    p_hat = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denominator
    half = z * ((p_hat * (1 - p_hat) / n + z2 / (4 * n * n)) ** 0.5) / denominator
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def evaluate_fixture(fixture: Mapping[str, Any], command: str) -> dict[str, Any]:
    """Run one command fixture and return an ``agent-eval/v1`` scorecard."""

    fixture = _require_mapping(fixture, "fixture")
    command = _require_nonempty_string(command, "command")
    task = fixture.get("task", "")
    if not isinstance(task, str):
        raise ValueError("task must be a string")
    expected = _expected_exit(fixture)
    expected_stdout = _expected_stdout(fixture)
    timeout = _timeout(fixture)
    rendered_command = command.replace("{task}", shlex.quote(task))

    execution = _execute(rendered_command, timeout)
    ok = (
        not execution["timed_out"]
        and execution["exit_code"] == expected
        and all(fragment in execution["stdout"] for fragment in expected_stdout)
    )
    return {
        "schema": "agent-eval/v1",
        "ok": ok,
        "exit_code": execution["exit_code"],
        "expected_exit": expected,
        "duration_ms": execution["duration_ms"],
        "stdout": execution["stdout"],
        "stderr": execution["stderr"],
        "timed_out": execution["timed_out"],
    }


def evaluate_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_exit: int = 0,
    expected_stdout: Sequence[str] = (),
    require_integrity: bool = False,
) -> dict[str, Any]:
    """Evaluate a saved ``agent-sandbox/v2`` receipt without rerunning a command."""

    receipt = _require_mapping(receipt, "receipt")
    source_schema = _require_nonempty_string(receipt.get("schema"), "receipt.schema")
    if source_schema not in {"agent-sandbox/v1", "agent-sandbox/v2"}:
        raise ValueError("receipt.schema must be agent-sandbox/v1 or agent-sandbox/v2")
    if isinstance(expected_exit, bool) or not isinstance(expected_exit, int):
        raise ValueError("expected_exit must be an integer")
    fragments = list(expected_stdout)
    if any(not isinstance(fragment, str) for fragment in fragments):
        raise ValueError("expected_stdout must contain only strings")

    actual_exit = receipt.get("exit_code")
    if isinstance(actual_exit, bool) or not isinstance(actual_exit, int):
        raise ValueError("receipt.exit_code must be an integer")
    stdout = _text(receipt.get("stdout", ""))
    actual_digest = receipt.get("receipt_sha256")
    if actual_digest is None:
        integrity = "unbound"
    elif isinstance(actual_digest, str) and actual_digest == _receipt_sha256(receipt):
        integrity = "verified"
    else:
        integrity = "mismatch"
    stdout_matches = all(fragment in stdout for fragment in fragments)
    ok = (
        integrity != "mismatch"
        and (not require_integrity or integrity == "verified")
        and actual_exit == expected_exit
        and stdout_matches
        and not bool(receipt.get("timed_out", False))
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "ok": ok,
        "source_schema": source_schema,
        "integrity": integrity,
        "receipt_sha256": actual_digest,
        "command_sha256": receipt.get("command_sha256"),
        "exit_code": actual_exit,
        "expected_exit": expected_exit,
        "stdout_sha256": _sha256(stdout),
        "expected_stdout": fragments,
        "stdout_matches": stdout_matches,
        "timed_out": bool(receipt.get("timed_out", False)),
    }


def _stats(durations: Sequence[int]) -> dict[str, int | float | None]:
    if not durations:
        return {"min_ms": None, "mean_ms": None, "max_ms": None}
    return {
        "min_ms": min(durations),
        "mean_ms": round(sum(durations) / len(durations), 3),
        "max_ms": max(durations),
    }


def _observation_fingerprint(scorecard: Mapping[str, Any]) -> str:
    """Hash behavior fields while excluding elapsed time."""

    observation = {
        key: scorecard[key]
        for key in ("schema", "ok", "exit_code", "expected_exit", "stdout", "stderr", "timed_out")
    }
    return _sha256(_canonical_json(observation))


def _validate_matrix_plan(plan: Mapping[str, Any]) -> tuple[int, list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    plan = _require_mapping(plan, "matrix plan")
    if plan.get("schema") != MATRIX_SCHEMA:
        raise ValueError(f"matrix plan schema must be {MATRIX_SCHEMA}")

    trials = plan.get("trials", 1)
    if isinstance(trials, bool) or not isinstance(trials, int) or not 1 <= trials <= MAX_TRIALS:
        raise ValueError(f"trials must be an integer from 1 to {MAX_TRIALS}")

    fixtures = plan.get("fixtures")
    candidates = plan.get("candidates")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixtures must be a non-empty list")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")

    fixture_items: list[Mapping[str, Any]] = []
    fixture_ids: set[str] = set()
    for index, fixture in enumerate(fixtures):
        item = _require_mapping(fixture, f"fixtures[{index}]")
        fixture_id = _require_nonempty_string(item.get("id"), f"fixtures[{index}].id")
        if fixture_id in fixture_ids:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        fixture_ids.add(fixture_id)
        fixture_items.append(item)

    candidate_items: list[Mapping[str, Any]] = []
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        item = _require_mapping(candidate, f"candidates[{index}]")
        candidate_id = _require_nonempty_string(item.get("id"), f"candidates[{index}].id")
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        _require_nonempty_string(item.get("command"), f"candidates[{index}].command")
        candidate_items.append(item)

    return trials, fixture_items, candidate_items


def evaluate_matrix(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate every candidate against every fixture for a fixed trial count.

    The plan fingerprint is derived from canonical JSON so equivalent key
    ordering produces the same identity.  Commands still run in the supplied
    order, and every individual scorecard remains visible for inspection.
    """

    plan = _require_mapping(plan, "matrix plan")
    trials, fixtures, candidates = _validate_matrix_plan(plan)
    summaries: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = str(candidate["id"])
        command = str(candidate["command"])
        case_summaries: list[dict[str, Any]] = []
        candidate_runs: list[dict[str, Any]] = []
        for fixture in fixtures:
            fixture_id = str(fixture["id"])
            runs: list[dict[str, Any]] = []
            for trial in range(1, trials + 1):
                scorecard = evaluate_fixture(fixture, command)
                run = {"trial": trial, "scorecard": scorecard}
                runs.append(run)
                candidate_runs.append(run)
                all_runs.append(
                    {
                        "candidate": candidate_id,
                        "fixture": fixture_id,
                        **run,
                    }
                )

            durations = [int(run["scorecard"]["duration_ms"]) for run in runs]
            observation_fingerprints = [
                _observation_fingerprint(run["scorecard"]) for run in runs
            ]
            passed = sum(1 for run in runs if run["scorecard"]["ok"])
            case_summaries.append(
                {
                    "id": fixture_id,
                    "runs": len(runs),
                    "passed": passed,
                    "pass_rate": round(passed / len(runs), 4),
                    "duration_ms": _stats(durations),
                    "stable": len(set(observation_fingerprints)) == 1,
                    "observations_sha256": _sha256(_canonical_json(observation_fingerprints)),
                    "results": runs,
                }
            )

        candidate_passed = sum(1 for run in candidate_runs if run["scorecard"]["ok"])
        candidate_durations = [
            int(run["scorecard"]["duration_ms"]) for run in candidate_runs
        ]
        candidate_observations = [
            _observation_fingerprint(run["scorecard"]) for run in candidate_runs
        ]
        summaries.append(
            {
                "id": candidate_id,
                "command": command,
                "runs": len(candidate_runs),
                "passed": candidate_passed,
                "pass_rate": round(candidate_passed / len(candidate_runs), 4),
                "duration_ms": _stats(candidate_durations),
                "stable": all(case["stable"] for case in case_summaries),
                "observations_sha256": _sha256(_canonical_json(candidate_observations)),
                "cases": case_summaries,
            }
        )

    ranked = sorted(
        summaries,
        key=lambda item: (
            -float(item["pass_rate"]),
            (
                float("inf")
                if item["duration_ms"]["mean_ms"] is None
                else float(item["duration_ms"]["mean_ms"])
            ),
            str(item["id"]),
        ),
    )
    ranking = [
        {
            "rank": rank,
            "candidate": item["id"],
            "pass_rate": item["pass_rate"],
            "mean_duration_ms": item["duration_ms"]["mean_ms"],
        }
        for rank, item in enumerate(ranked, start=1)
    ]
    passed_runs = sum(1 for run in all_runs if run["scorecard"]["ok"])
    return {
        "schema": MATRIX_SCHEMA,
        "ok": passed_runs == len(all_runs),
        "plan_sha256": _sha256(_canonical_json(plan)),
        "trials": trials,
        "fixture_count": len(fixtures),
        "candidate_count": len(candidates),
        "runs": len(all_runs),
        "passed": passed_runs,
        "results": summaries,
        "ranking": ranking,
    }
