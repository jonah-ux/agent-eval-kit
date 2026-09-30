# Contributing

Thanks for improving agent-eval-kit. Small, focused pull requests are easiest to
review.

## Development

The project supports Python 3.11 and 3.12 and has no runtime dependencies. A
standard-library test run is enough for local development:

```text
python3.11 -m venv .venv
. .venv/bin/activate
python -m unittest discover -s tests -v
python -m build
```

The repository's CI also checks both supported Python versions on Ubuntu and macOS.
Keep tests deterministic and avoid network calls, wall-clock assertions, or provider-
specific APIs.

## Pull requests

1. Explain the user-visible behavior and include a focused test or fixture.
2. Update `CHANGELOG.md` for user-facing changes.
3. Keep captured output and reports free of credentials; add a redaction regression
   test when output handling changes.
4. Run the checks in `docs/releasing.md` when packaging behavior changes.
5. Use a clear commit subject and reference the tracking card when one exists.

Do not commit generated build directories, virtual environments, credentials, or
real customer data. Do not add a runtime dependency without documenting why the
standard library cannot provide the behavior.

## Code of conduct

Be precise, kind, and constructive. Maintainers may reject changes that weaken
least-privilege behavior, reproducibility, or failure reporting.
