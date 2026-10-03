# Changelog

## 0.4.0 - Unreleased

- add `agent-eval honesty list|show|run|selftest`: a claim-integrity suite that compares an agent's machine-readable claim block with the actual workspace diff and checks
- add ten synthetic fixtures across five families (`side_effect`, `change_scope`, `citation`, `unverifiable`, `self_verify`), shipped as package data
- add deterministic per-trial labels, `agent-eval/honesty/report/v1` reports with Wilson intervals, fixture-level rates, compliance, a conservative upper bound, and an always-present limits block
- add task-agnostic calibration agents (`python -m agent_eval_kit.honesty_calibration claim-done|abstain|silent`) with known answers
- extract the runner's command execution into a shared helper with optional working directory, environment and stdin; `agent-eval/v1` scorecards are unchanged

## 0.3.0 - Unreleased

- add `agent-eval/receipt/v1` scoring for integrity-bound `agent-sandbox/v2` receipts without rerunning commands
- add receipt tamper refusal, CLI coverage, and interoperability docs

- add `agent-eval/matrix/v1` plans for repeated candidate and fixture comparisons
- emit canonical plan fingerprints, per-trial scorecards, behavior fingerprints, pass rates, latency summaries, and stable tie-break rankings
- report command timeouts as failed scorecards instead of raising an unstructured exception
- terminate the full evaluator process group on timeout while preserving the `agent-eval/v1` scorecard
- return stable `agent-eval/error/v1` envelopes for unreadable or malformed input files and plans

## 0.1.0 - 2026-09-30

Initial focused release with a stable CLI contract and synthetic demo.
