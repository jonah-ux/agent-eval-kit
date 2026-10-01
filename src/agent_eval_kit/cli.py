import argparse
import json

from .runner import evaluate_fixture, evaluate_matrix, evaluate_receipt


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
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.action == "run":
        with open(args.fixture, encoding="utf-8") as handle:
            fixture = json.load(handle)
        output = evaluate_fixture(fixture, args.cmd)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if output["ok"] else 1

    if args.action == "receipt":
        with open(args.path, encoding="utf-8") as handle:
            receipt = json.load(handle)
        output = evaluate_receipt(
            receipt,
            expected_exit=args.expect_exit,
            expected_stdout=args.expect_stdout,
            require_integrity=args.require_integrity,
        )
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if output["ok"] else 1

    with open(args.plan, encoding="utf-8") as handle:
        plan = json.load(handle)
    output = evaluate_matrix(plan)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["ok"] else 1
