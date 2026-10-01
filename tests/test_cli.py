import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_eval_kit.cli import main
from agent_eval_kit.runner import evaluate_matrix, evaluate_receipt, _receipt_sha256


class Smoke(unittest.TestCase):
    def test_import(self):
        self.assertTrue(callable(main))

    def test_help_succeeds_without_required_run_arguments(self):
        with self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_run_emits_scorecard(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.json"
            fixture.write_text(
                json.dumps({"task": "hello", "expect_stdout": ["hello"]}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["run", str(fixture), "--command", "printf {task}"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["schema"], "agent-eval/v1")

    def test_matrix_compares_candidates_across_repeated_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "schema": "agent-eval/matrix/v1",
                        "trials": 2,
                        "fixtures": [
                            {"id": "greeting", "task": "hello", "expect_stdout": ["hello"]},
                            {"id": "farewell", "task": "bye", "expect_stdout": ["bye"]},
                        ],
                        "candidates": [
                            {"id": "echo", "command": "printf {task}"},
                            {"id": "wrong", "command": "printf nope"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["matrix", str(plan)])

        self.assertEqual(result, 1)
        scorecard = json.loads(output.getvalue())
        self.assertEqual(scorecard["schema"], "agent-eval/matrix/v1")
        self.assertEqual(scorecard["runs"], 8)
        self.assertEqual(scorecard["passed"], 4)
        self.assertFalse(scorecard["ok"])
        self.assertEqual(scorecard["ranking"][0]["candidate"], "echo")

    def test_run_reports_timeout_as_a_failed_scorecard(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.json"
            fixture.write_text(json.dumps({"timeout": 0.01}), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["run", str(fixture), "--command", "sleep 1"])

        self.assertEqual(result, 1)
        scorecard = json.loads(output.getvalue())
        self.assertTrue(scorecard["timed_out"])
        self.assertIsNone(scorecard["exit_code"])

    def test_matrix_plan_fingerprint_ignores_object_key_order(self):
        plan = {
            "schema": "agent-eval/matrix/v1",
            "trials": 1,
            "fixtures": [{"id": "greeting", "task": "hello", "expect_stdout": ["hello"]}],
            "candidates": [{"id": "echo", "command": "printf {task}"}],
        }
        reordered = {
            "candidates": [{"command": "printf {task}", "id": "echo"}],
            "fixtures": [{"expect_stdout": ["hello"], "task": "hello", "id": "greeting"}],
            "trials": 1,
            "schema": "agent-eval/matrix/v1",
        }

        self.assertEqual(
            evaluate_matrix(plan)["plan_sha256"],
            evaluate_matrix(reordered)["plan_sha256"],
        )

    def test_matrix_rejects_duplicate_candidate_ids(self):
        plan = {
            "schema": "agent-eval/matrix/v1",
            "fixtures": [{"id": "greeting", "task": "hello"}],
            "candidates": [
                {"id": "same", "command": "printf {task}"},
                {"id": "same", "command": "printf {task}"},
            ],
        }

        with self.assertRaisesRegex(ValueError, "duplicate candidate id"):
            evaluate_matrix(plan)

    def test_receipt_import_verifies_integrity_without_rerun(self):
        receipt = {
            "schema": "agent-sandbox/v2",
            "ok": True,
            "exit_code": 0,
            "timed_out": False,
            "stdout": "hello\n",
            "command_sha256": "a" * 64,
        }
        receipt["receipt_sha256"] = _receipt_sha256(receipt)
        result = evaluate_receipt(receipt, expected_stdout=["hello"], require_integrity=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["schema"], "agent-eval/receipt/v1")
        self.assertEqual(result["integrity"], "verified")

        receipt["stdout"] = "tampered\n"
        tampered = evaluate_receipt(receipt, expected_stdout=["hello"], require_integrity=True)
        self.assertFalse(tampered["ok"])
        self.assertEqual(tampered["integrity"], "mismatch")

    def test_receipt_cli_emits_structured_scorecard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            receipt = {
                "schema": "agent-sandbox/v2",
                "ok": True,
                "exit_code": 0,
                "timed_out": False,
                "stdout": "consumer\n",
                "command_sha256": "b" * 64,
            }
            receipt["receipt_sha256"] = _receipt_sha256(receipt)
            path.write_text(json.dumps(receipt), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["receipt", str(path), "--expect-stdout", "consumer", "--require-integrity"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["schema"], "agent-eval/receipt/v1")


if __name__=="__main__": unittest.main()
