import argparse
import json
import shlex
import subprocess
import time


def _parser():
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="Run a small command fixture and emit an agent-eval/v1 scorecard.",
    )
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="evaluate one command against a JSON fixture")
    run.add_argument("fixture", help="path to the JSON fixture")
    run.add_argument("--command", dest="cmd", required=True, help="command to execute")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    with open(args.fixture, encoding="utf-8") as handle:
        fixture = json.load(handle)

    started = time.time()
    command = args.cmd.replace("{task}", shlex.quote(fixture.get("task", "")))
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout=fixture.get("timeout", 30),
    )
    expected = fixture.get("expect_exit", 0)
    ok = result.returncode == expected and all(
        fragment in result.stdout for fragment in fixture.get("expect_stdout", [])
    )
    output = {
        "schema": "agent-eval/v1",
        "ok": ok,
        "exit_code": result.returncode,
        "expected_exit": expected,
        "duration_ms": round((time.time() - started) * 1000),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if ok else 1
