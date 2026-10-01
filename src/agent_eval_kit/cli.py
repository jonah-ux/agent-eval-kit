import argparse
import json

from .runner import evaluate_fixture, evaluate_matrix


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
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.action == "run":
        with open(args.fixture, encoding="utf-8") as handle:
            fixture = json.load(handle)
        output = evaluate_fixture(fixture, args.cmd)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if output["ok"] else 1

    with open(args.plan, encoding="utf-8") as handle:
        plan = json.load(handle)
    output = evaluate_matrix(plan)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["ok"] else 1
