from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from agent_eval_kit.checks import _json_subset, redact
from agent_eval_kit.models import EvaluationConfig, FileExpectation
from agent_eval_kit.runner import run_config, run_fixture

FIXTURES = Path(__file__).parents[1] / "fixtures"


class ModelTests(unittest.TestCase):
    def test_mapping_validation_and_json_subset(self) -> None:
        config = EvaluationConfig.from_mapping(
            {"command": ["python", "{task}"], "tasks": ["one"], "timeout": 2}
        )
        self.assertEqual(config.command, ("python", "{task}"))
        self.assertEqual(_json_subset({"a": {"b": 2}}, {"a": {"b": 2}}), [])
        self.assertTrue(_json_subset({"a": 1}, {"a": 2}))

    def test_redaction(self) -> None:
        self.assertEqual(redact("token=abc", (r"token=\S+",)), "[REDACTED]")


class RunnerTests(unittest.TestCase):
    def test_passing_fixture_checks_files_and_captures_output(self) -> None:
        config = EvaluationConfig(
            command=(sys.executable, str(FIXTURES / "demo_agent.py"), "{task}"),
            tasks=("one", "two"),
            timeout=3,
            expected_files=(FileExpectation("result.json", json={"status": "ok"}),),
            expected_stdout=("task=",),
            redactions=(r"secret=\S+",),
        )
        result = run_config(config)
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 100)
        self.assertEqual(len(result.results), 2)
        self.assertNotIn("secret=secret=do-not-leak", result.results[0].stdout)
        self.assertIn("[REDACTED]", result.results[0].stdout)

    def test_failing_fixture_is_reported_without_raising(self) -> None:
        config = EvaluationConfig(
            command=(sys.executable, str(FIXTURES / "failing_agent.py"), "{task}"),
            tasks=("bad",),
            timeout=3,
            expected_exit=0,
            expected_stdout=("never-present",),
        )
        result = run_config(config)
        self.assertFalse(result.passed)
        self.assertEqual(result.results[0].returncode, 7)
        self.assertEqual(result.score, 0)

    def test_timeout_is_bounded(self) -> None:
        config = EvaluationConfig(
            command=(sys.executable, "-c", "import time; print('before'); time.sleep(2)"),
            tasks=("slow",),
            timeout=0.05,
        )
        result = run_config(config)
        self.assertFalse(result.passed)
        self.assertTrue(result.results[0].timed_out)

    def test_jsonl_events_are_emitted_in_order(self) -> None:
        events: list[dict[str, object]] = []
        config = EvaluationConfig(
            command=(sys.executable, "-c", "print('ok')"),
            tasks=("event",),
        )
        result = run_config(config, emit=events.append)
        self.assertTrue(result.passed)
        self.assertEqual([event["event"] for event in events], ["task_started", "task_finished"])

    def test_scorecard_is_stable_across_runs(self) -> None:
        config = EvaluationConfig(command=(sys.executable, "-c", "print('stable')"))
        self.assertEqual(run_config(config).to_dict(), run_config(config).to_dict())


if __name__ == "__main__":
    unittest.main()
