# Agent Eval Kit

![agent fixture evaluator workflow](docs/header.svg)

**Run tiny reproducible agent tasks and turn their results into a scorecard.**

[![CI](https://github.com/jonah-ux/agent-eval-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/jonah-ux/agent-eval-kit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

Agent Eval Kit keeps a small task fixture beside the command it evaluates. The result is
deterministic JSON with the command, expected exit code, required stdout, stderr, and duration.
It is deliberately tiny enough to understand before putting it in an agent loop or CI job.

## Try it in 30 seconds

```bash
python -m pip install git+https://github.com/jonah-ux/agent-eval-kit.git@main
python demos/demo.py
```

The demo runs one fixture and prints an `agent-eval/v1` scorecard. For a real fixture:

```json
{"task":"hello","expect_stdout":["hello"],"timeout":10}
```

```bash
agent-eval run fixture.json --command 'printf {task}'
```

## What it checks

- The command exits with the expected status.
- Required stdout fragments are present.
- stderr and elapsed time stay visible to the caller.
- A failed expectation returns exit code `1` for CI and agents.

## Development

```bash
python -m unittest discover -s tests
python -m build --sdist --wheel
python demos/demo.py
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding fixtures. This tool evaluates a command;
it does not claim to sandbox or secure that command.

MIT licensed.
