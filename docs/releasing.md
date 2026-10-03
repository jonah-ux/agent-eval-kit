# Releasing

Releases are cut locally. No CI service is involved.

1. Run the full test suite on the minimum supported Python (3.11) and on a current one:
   `python3.11 -m unittest discover -s tests` and `python3 -m unittest discover -s tests`.
2. Bump `version` in `pyproject.toml` and `src/agent_eval_kit/__init__.py`, update `CHANGELOG.md`, and merge.
3. Create an annotated tag `vX.Y.Z` on that exact commit and push it to `origin`.
4. From a clean checkout of that commit, run `DRY_RUN=1 scripts/release.sh vX.Y.Z`, then `scripts/release.sh vX.Y.Z`.

`scripts/release.sh` refuses to run unless the tag is annotated, matches the package version, and
points at the checked-out `HEAD`. It builds the wheel and sdist, writes `SHA256SUMS`, installs each
distribution into a fresh virtualenv and runs its console script, and only then publishes a GitHub
prerelease with those three assets.

To verify a download, compare it against `SHA256SUMS` from the same release:
`shasum -a 256 -c SHA256SUMS` (macOS) or `sha256sum -c SHA256SUMS` (Linux).
