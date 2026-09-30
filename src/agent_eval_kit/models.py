from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FileExpectation:
    """An expected file and optional content or JSON assertions."""

    path: str
    exists: bool = True
    contains: tuple[str, ...] = ()
    json: Any = None


@dataclass(frozen=True)
class EvaluationConfig:
    """Configuration for one or more fixture tasks."""

    command: tuple[str, ...]
    tasks: tuple[str, ...] = ("demo",)
    timeout: float = 30.0
    expected_exit: int = 0
    expected_files: tuple[FileExpectation, ...] = ()
    expected_stdout: tuple[str, ...] = ()
    expected_stderr: tuple[str, ...] = ()
    redactions: tuple[str, ...] = ()
    sandbox: str | None = None
    working_directory: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "EvaluationConfig":
        files = tuple(
            FileExpectation(
                path=str(item["path"]),
                exists=bool(item.get("exists", True)),
                contains=tuple(str(x) for x in item.get("contains", [])),
                json=item.get("json"),
            )
            for item in value.get("expected_files", [])
        )
        command = value.get("command")
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) for part in command
        ):
            raise ValueError("command must be a non-empty list of strings")
        timeout = float(value.get("timeout", 30.0))
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        tasks = value.get("tasks", ["demo"])
        if not isinstance(tasks, list) or not all(isinstance(task, str) for task in tasks):
            raise ValueError("tasks must be a list of strings")
        redactions = value.get("redactions", [])
        if not isinstance(redactions, list) or not all(
            isinstance(pattern, str) for pattern in redactions
        ):
            raise ValueError("redactions must be a list of regular-expression strings")
        return cls(
            command=tuple(command),
            tasks=tuple(tasks),
            timeout=timeout,
            expected_exit=int(value.get("expected_exit", 0)),
            expected_files=files,
            expected_stdout=tuple(str(x) for x in value.get("expected_stdout", [])),
            expected_stderr=tuple(str(x) for x in value.get("expected_stderr", [])),
            redactions=tuple(redactions),
            sandbox=value.get("sandbox"),
            working_directory=value.get("working_directory"),
        )


@dataclass
class FixtureResult:
    task: str
    command: list[str]
    returncode: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(bool(check["passed"]) for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "command": self.command,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "checks": self.checks,
            "passed": self.passed,
        }


@dataclass
class EvaluationResult:
    results: list[FixtureResult]
    started_at: str
    finished_at: str

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)

    @property
    def score(self) -> int:
        total = sum(len(result.checks) for result in self.results)
        passed = sum(
            1
            for result in self.results
            for check in result.checks
            if check["passed"]
        )
        return round((passed / total) * 100) if total else 0

    def to_dict(self) -> dict[str, Any]:
        """Return the deterministic scorecard representation."""
        return {
            "passed": self.passed,
            "score": self.score,
            "total_tasks": len(self.results),
            "passed_tasks": sum(result.passed for result in self.results),
            "results": [result.to_dict() for result in self.results],
        }
