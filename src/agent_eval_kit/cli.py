from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from .models import EvaluationConfig, EvaluationResult, FileExpectation
from .runner import run_config, write_jsonl_event


def _load_config(path: Path) -> EvaluationConfig:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON configuration: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("configuration must be a JSON object")
    return EvaluationConfig.from_mapping(value)


def _write_scorecard(result: EvaluationResult, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "scorecard.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_junit(result: EvaluationResult, output: Path) -> None:
    suite = ET.Element(
        "testsuite",
        name="agent-eval-kit",
        tests=str(sum(len(item.checks) for item in result.results)),
        failures=str(
            sum(1 for item in result.results for check in item.checks if not check["passed"])
        ),
        time=f"{sum(item.duration_ms for item in result.results) / 1000:.3f}",
    )
    for item in result.results:
        for check in item.checks:
            case = ET.SubElement(
                suite,
                "testcase",
                classname=item.task,
                name=check["name"],
            )
            if not check["passed"]:
                failure = ET.SubElement(case, "failure", message=check["detail"])
                failure.text = check["detail"]
            ET.SubElement(case, "system-out").text = item.stdout
            ET.SubElement(case, "system-err").text = item.stderr
    ET.indent(suite, space="  ")
    ET.ElementTree(suite).write(output / "junit.xml", encoding="utf-8", xml_declaration=True)


def _demo_config() -> EvaluationConfig:
    fixture = Path(__file__).resolve().with_name("demo_fixture.py")
    return EvaluationConfig(
        command=(sys.executable, str(fixture), "{task}"),
        tasks=("alpha", "beta"),
        timeout=5,
        expected_files=(
            FileExpectation(path="result.json", json={"status": "ok"}),
        ),
        expected_stdout=("task=",),
        redactions=(r"secret=\S+",),
    )


def _demo(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    events = (output / "events.jsonl").open("w", encoding="utf-8")
    try:
        result = run_config(_demo_config(), emit=lambda event: write_jsonl_event(events, event))
    finally:
        events.close()
    _write_scorecard(result, output)
    _write_junit(result, output)
    print(f"score={result.score} passed={str(result.passed).lower()} output={output}")
    return 0 if result.passed else 1


def _run(args: argparse.Namespace) -> int:
    config = _load_config(Path(args.config))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "events.jsonl").open("w", encoding="utf-8") as events:
        result = run_config(config, emit=lambda event: write_jsonl_event(events, event))
    _write_scorecard(result, output)
    _write_junit(result, output)
    print(f"score={result.score} passed={str(result.passed).lower()} output={output}")
    return 0 if result.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="Run provider-neutral command fixtures and produce deterministic reports.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    run = subparsers.add_parser("run", help="run a JSON fixture configuration")
    run.add_argument("config", help="path to a JSON configuration")
    run.add_argument("-o", "--output", default="eval-results", help="report directory")
    run.set_defaults(handler=_run)
    demo = subparsers.add_parser("demo", help="run the installed synthetic demonstration")
    demo.add_argument("-o", "--output", default="demo-results", help="report directory")
    demo.set_defaults(handler=_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
