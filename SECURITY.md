# Security policy

## Scope

`agent-eval-kit` runs commands that you configure. It is a local fixture runner,
not a general-purpose sandbox and not a provider gateway. Treat fixture commands,
configuration files, and task values as code that can execute with the invoking
user's permissions.

The default runner uses `subprocess` without a shell. It creates a fresh temporary
workspace for every task and bounds each process with the configured timeout. Those
choices reduce accidental coupling; they do not provide a security boundary.

For an additional OS-level boundary, install and review the policy for a local
platform tool and set `"sandbox": "bwrap"` in a JSON config on Linux or
`"sandbox": "sandbox-exec"` on macOS. Availability and policy behavior belong to
the platform tool. Never treat this optional mode as a replacement for least
privilege, network controls, or a container boundary.

Configure `redactions` (regular expressions) for tokens that may appear in command
output. Reports, JSONL events, and JUnit output apply those patterns before writing
captured output. Do not put live credentials in fixtures or commits.

## Reporting a vulnerability

Please do not open a public issue for an undisclosed vulnerability. Email the
maintainer through the address listed in the repository's GitHub profile with:

- a short description and affected version;
- a minimal reproduction that contains no real credentials; and
- the impact and any suggested mitigation.

You should receive an acknowledgement within seven days. We will coordinate a
fix, regression test, and public disclosure after a fix is available.

Supported versions and release notes are recorded in `CHANGELOG.md`.
