# Changelog

## 0.4.0 - Unreleased

- add `agent-eval honesty list|show|run|selftest`: a claim-integrity suite that compares an agent's machine-readable claim block with the actual workspace diff and checks
- add ten synthetic fixtures across five families (`side_effect`, `change_scope`, `citation`, `unverifiable`, `self_verify`), shipped as package data
- add deterministic per-trial labels, `agent-eval/honesty/report/v1` reports with Wilson intervals, fixture-level rates, compliance, a conservative upper bound, and an always-present limits block
- add task-agnostic calibration agents (`python -m agent_eval_kit.honesty_calibration claim-done|abstain|silent`) with known answers
- kill every process left in the agent's session (not just its process group) before honesty snapshots and checks; bound claim parsing to 64 candidate openers over the last 1 MiB of output (`final_text_truncated` records truncation); stop flagging unrelated symlinked files under `**` globs
- fail closed on unreadable workspace paths: snapshots record unlistable directories and special files (never opened), hidden paths never count as verified changes (`unverifiable_changes`), a newly unreadable path fails the trial's checks (`workspace:readable`), path probes never raise on Python 3.11/3.12, cleanup survives `000` modes (`unreadable_paths` lists them), treat deeply nested claim JSON as invalid instead of crashing, and surface truncated final text in the text report
- symlink swaps (a file or directory replaced by a symlink) never count as verified changes; a replaced or unverifiable trial root or workspace (checked through `O_NOFOLLOW` descriptors and `fstat`, so ACL-hidden symlinks cannot redirect it) is never walked and scores `WORKSPACE_TAMPERED`; unclaimed new special files no longer fail honest trials; `cleanup_error` is reported in scorecards and the text report, and BSD `uchg` flags are cleared before removal
- checks never read through a symlink created during the run: path checks fail when any path component is a symlink (walked with `lstat`, so case and Unicode aliases on APFS are caught), python checks fail while any new symlink resolves outside the workspace, and a claimed write or change on a new symlink is a false claim (`new_symlinks` in scorecards)
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
