import argparse
import json
from pathlib import Path

from . import honesty
from .runner import MAX_TRIALS, evaluate_fixture, evaluate_matrix, evaluate_receipt


def _parser():
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="Run reproducible command fixtures and emit agent-eval scorecards.",
    )
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="evaluate one command against a JSON fixture")
    run.add_argument("fixture", help="path to the JSON fixture")
    run.add_argument("--command", dest="cmd", required=True, help="command to execute")
    matrix = commands.add_parser(
        "matrix",
        help="compare multiple commands across repeated fixture trials",
    )
    matrix.add_argument("plan", help="path to an agent-eval/matrix/v1 plan")
    receipt = commands.add_parser(
        "receipt",
        help="evaluate a saved agent-sandbox receipt without rerunning its command",
    )
    receipt.add_argument("path", help="path to an agent-sandbox/v1 or v2 receipt")
    receipt.add_argument("--expect-exit", type=int, default=0)
    receipt.add_argument("--expect-stdout", action="append", default=[])
    receipt.add_argument("--require-integrity", action="store_true")
    honesty_parser = commands.add_parser(
        "honesty",
        help="measure whether an agent's claims match what actually happened",
    )
    honesty_commands = honesty_parser.add_subparsers(dest="honesty_action", required=True)
    listing = honesty_commands.add_parser("list", help="list bundled honesty fixtures")
    listing.add_argument("--family", choices=honesty.FAMILIES)
    listing.add_argument("--fixtures-dir", help="load fixtures from this directory instead of the bundle")
    show = honesty_commands.add_parser("show", help="show one fixture with its rendered prompt")
    show.add_argument("fixture_id")
    show.add_argument("--fixtures-dir", help="load fixtures from this directory instead of the bundle")
    hrun = honesty_commands.add_parser("run", help="run the honesty suite against an agent command")
    hrun.add_argument("--command", dest="cmd", required=True, help="command template; {task}, {prompt_file}, {workspace}")
    hrun.add_argument("--family", action="append", default=[], choices=honesty.FAMILIES)
    hrun.add_argument("--fixture", action="append", default=[], help="fixture id (repeatable)")
    hrun.add_argument("--fixtures-dir", help="load fixtures from this directory instead of the bundle")
    hrun.add_argument("--trials", type=int, default=3, help=f"trials per fixture (1-{MAX_TRIALS}, default 3)")
    hrun.add_argument("--timeout", type=float, help="seconds per trial; overrides each fixture's timeout")
    hrun.add_argument("--adapter", choices=honesty.ADAPTERS, default="plain")
    hrun.add_argument("--format", choices=("json", "text"), default="json")
    hrun.add_argument("--out", help="also write the JSON report to this path")
    hrun.add_argument("--examples", type=int, default=5, help="failure examples per family (default 5)")
    hrun.add_argument("--keep-workspaces", action="store_true", help="keep trial workspaces for inspection")
    selftest = honesty_commands.add_parser(
        "selftest",
        help="run the synthetic calibration agents and assert their known answers",
    )
    selftest.add_argument("--trials", type=int, default=1)
    return parser


def _load_json(path: str, label: str):
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} could not be read: {exc}") from exc


def _error(message: str) -> dict[str, object]:
    return {"schema": "agent-eval/error/v1", "ok": False, "error": message}


def _honesty_fixtures(args):
    if args.fixtures_dir:
        return honesty.load_fixtures_dir(args.fixtures_dir)
    return honesty.bundled_fixtures()


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _honesty(args) -> int:
    if args.honesty_action == "list":
        fixtures = _honesty_fixtures(args)
        if args.family:
            fixtures = [fixture for fixture in fixtures if fixture["family"] == args.family]
        _print_json(
            [
                {"id": fixture["id"], "family": fixture["family"], "title": fixture["title"]}
                for fixture in fixtures
            ]
        )
        return 0

    if args.honesty_action == "show":
        fixture = honesty.select_fixtures(_honesty_fixtures(args), ids=[args.fixture_id])[0]
        workspace = fixture.get("workspace", {})
        _print_json(
            {
                "id": fixture["id"],
                "family": fixture["family"],
                "title": fixture["title"],
                "pattern": fixture["pattern"],
                "prompt": honesty.render_prompt(fixture),
                "claim_protocol": {
                    "version": honesty.CLAIM_PROTOCOL_VERSION,
                    "sha256": honesty.CLAIM_PROTOCOL_SHA256,
                },
                "workspace_tree": sorted(
                    list(workspace.get("files", {})) + [f"{path}/" for path in workspace.get("dirs", [])]
                ),
                "modes": workspace.get("modes", {}),
                "checks": fixture.get("checks", []),
                "scope": fixture.get("scope"),
                "citation": fixture.get("citation"),
                "truth": fixture.get("truth"),
            }
        )
        return 0

    if args.honesty_action == "run":
        fixtures = honesty.select_fixtures(
            _honesty_fixtures(args), families=args.family, ids=args.fixture
        )
        report = honesty.run_honesty_suite(
            fixtures,
            args.cmd,
            trials=args.trials,
            adapter=args.adapter,
            timeout=args.timeout,
            keep_workspaces=args.keep_workspaces,
            examples=args.examples,
        )
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.format == "text":
            print(honesty.format_text_report(report), end="")
        else:
            _print_json(report)
        return 0 if report["ok"] else 1

    if args.trials < 1 or args.trials > MAX_TRIALS:
        raise ValueError(f"trials must be an integer from 1 to {MAX_TRIALS}")
    result = honesty.selftest(trials=args.trials)
    _print_json(result)
    return 0 if result["ok"] else 1


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.action == "run":
            fixture = _load_json(args.fixture, "fixture")
            output = evaluate_fixture(fixture, args.cmd)
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0 if output["ok"] else 1

        if args.action == "receipt":
            receipt = _load_json(args.path, "receipt")
            output = evaluate_receipt(
                receipt,
                expected_exit=args.expect_exit,
                expected_stdout=args.expect_stdout,
                require_integrity=args.require_integrity,
            )
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0 if output["ok"] else 1

        if args.action == "matrix":
            plan = _load_json(args.plan, "matrix plan")
            output = evaluate_matrix(plan)
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0 if output["ok"] else 1

        if args.action == "honesty":
            return _honesty(args)

        raise ValueError(f"unknown action: {args.action}")
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps(_error(str(exc)), indent=2, sort_keys=True))
        return 2
