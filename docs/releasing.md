# Releasing

This repository does not publish a release as part of normal development. A
maintainer performs a release only after review and explicit authorization.

## Verify a candidate

From a clean checkout and a Python 3.11 or newer environment:

```text
python -m unittest discover -s tests -v
python -m build
python -m venv /tmp/agent-eval-kit-release-check
/tmp/agent-eval-kit-release-check/bin/python -m pip install dist/agent_eval_kit-*.whl
/tmp/agent-eval-kit-release-check/bin/agent-eval demo --output /tmp/agent-eval-kit-demo
/tmp/agent-eval-kit-release-check/bin/python -m pip install dist/agent_eval_kit-*.tar.gz
```

Confirm that the wheel and sdist contain the same source version, that the demo
returns zero, and that `events.jsonl`, `scorecard.json`, and `junit.xml` are
created. Build artifacts must not be committed.

## Candidate checklist

- [ ] CI is green on Ubuntu and macOS for Python 3.11 and 3.12.
- [ ] `CHANGELOG.md` has a dated entry.
- [ ] `README.md` installation and command examples work from a fresh install.
- [ ] The exact commit being released is identified.
- [ ] A maintainer has approved the release and selected the distribution channel.
- [ ] Credentials and generated artifacts were not added to the repository.

The project uses a public repository and MIT license. Do not create a GitHub release,
tag, or package upload from an ordinary feature branch.
