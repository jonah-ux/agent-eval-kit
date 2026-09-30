import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_eval_kit.cli import main


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


if __name__=="__main__": unittest.main()
