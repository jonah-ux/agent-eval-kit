from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, TextIO

from .checks import check_file, check_text, redact
from .models import EvaluationConfig, EvaluationResult, FixtureResult

EventWriter = Callable[[dict[str, Any]], None]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _command(config: EvaluationConfig, task: str) -> list[str]:
    return [part.replace("{task}", task) for part in config.command]


def _sandbox_command(command: list[str], sandbox: str | None, root: Path) -> list[str]:
    if sandbox is None:
        return command
    if sandbox == "bwrap":
        return [
            "bwrap",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--bind",
            str(root),
            "/work",
            "--chdir",
            "/work",
            "--unshare-net",
            "--",
            *command,
        ]
    if sandbox == "sandbox-exec":
        profile = "(version 1) (allow process*) (allow file-read*) (allow file-write* (subpath \"%s\"))" % root
        return ["sandbox-exec", "-p", profile, *command]
    raise ValueError("sandbox must be one of: bwrap, sandbox-exec")


def _decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def run_fixture(
    config: EvaluationConfig,
    task: str,
    *,
    root: Path | None = None,
    emit: EventWriter | None = None,
) -> FixtureResult:
    """Run one task in a temporary/fresh workspace and evaluate its evidence."""
    command = _command(config, task)
    temporary = root is None
    if root is None:
        root_path = Path(tempfile.mkdtemp(prefix="agent-eval-"))
    else:
        root_path = root
        root_path.mkdir(parents=True, exist_ok=True)
    if emit:
        emit({"event": "task_started", "task": task, "command": command, "timestamp": _now()})
    started = time.monotonic()
    returncode: int | None = None
    timed_out = False
    launch_error = False
    stdout = ""
    stderr = ""
    try:
        env = os.environ.copy()
        env["AGENT_EVAL_TASK"] = task
        env["AGENT_EVAL_WORKSPACE"] = str(root_path)
        run_command = _sandbox_command(command, config.sandbox, root_path)
        try:
            process = subprocess.Popen(
                run_command,
                cwd=(Path(config.working_directory).expanduser().resolve() if config.working_directory else root_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=(os.name == "posix"),
            )
            try:
                raw_stdout, raw_stderr = process.communicate(timeout=config.timeout)
                returncode = process.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                raw_stdout, raw_stderr = process.communicate()
                raw_stdout = raw_stdout or exc.stdout
                raw_stderr = raw_stderr or exc.stderr
                returncode = process.returncode
            stdout = _decode_output(raw_stdout)
            stderr = _decode_output(raw_stderr)
        except OSError as exc:
            launch_error = True
            stderr = str(exc)
    finally:
        duration_ms = round((time.monotonic() - started) * 1000)
    stdout = redact(stdout, config.redactions)
    stderr = redact(stderr, config.redactions)
    checks: list[dict[str, Any]] = [
        {
            "name": "exit_code",
            "passed": not timed_out and not launch_error and returncode == config.expected_exit,
            "detail": f"expected {config.expected_exit}, got {'timeout' if timed_out else ('launch error' if launch_error else returncode)}",
        },
        *check_text("stdout", stdout, config.expected_stdout),
        *check_text("stderr", stderr, config.expected_stderr),
    ]
    checks.extend(check_file(root_path, expectation) for expectation in config.expected_files)
    result = FixtureResult(
        task=task,
        command=command,
        returncode=returncode,
        timed_out=timed_out,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr,
        checks=checks,
    )
    if emit:
        emit(
            {
                "event": "task_finished",
                "task": task,
                "passed": result.passed,
                "score": round(sum(check["passed"] for check in checks) / len(checks) * 100) if checks else 0,
                "stdout": stdout,
                "stderr": stderr,
                "timestamp": _now(),
            }
        )
    if temporary:
        # The temporary directory is intentionally retained only for the process;
        # reports contain the observable evidence and no path-dependent assertions.
        import shutil

        shutil.rmtree(root_path, ignore_errors=True)
    return result


def run_config(config: EvaluationConfig, *, emit: EventWriter | None = None) -> EvaluationResult:
    started_at = _now()
    results = [run_fixture(config, task, emit=emit) for task in config.tasks]
    return EvaluationResult(results=results, started_at=started_at, finished_at=_now())


def write_jsonl_event(writer: TextIO, event: dict[str, Any]) -> None:
    writer.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    writer.flush()
