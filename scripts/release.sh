#!/usr/bin/env bash
# Local release: no CI service involved.
#
#   scripts/release.sh vX.Y.Z            build, verify, and publish a GitHub prerelease
#   DRY_RUN=1 scripts/release.sh vX.Y.Z  everything except publishing
#
# Preconditions: a clean checkout whose HEAD is the commit an annotated tag
# vX.Y.Z points to, and that tag already on origin. Assets: wheel, sdist,
# SHA256SUMS. Both distributions are installed into fresh virtualenvs and
# their console script is run before anything is published.
set -euo pipefail

tag="${1:?usage: scripts/release.sh vMAJOR.MINOR.PATCH}"
root="$(git rev-parse --show-toplevel)"
cd "$root"
python="${PYTHON:-python3}"

[[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] \
  || { echo "release tag must be vMAJOR.MINOR.PATCH" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "working tree is not clean" >&2; exit 1; }

version="$("$python" -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
[ "$tag" = "v$version" ] || { echo "tag $tag does not match project version $version" >&2; exit 1; }

git fetch --quiet --force origin "refs/tags/$tag:refs/tags/$tag" \
  || { echo "tag $tag is not on origin" >&2; exit 1; }
[ "$(git cat-file -t "refs/tags/$tag")" = "tag" ] || { echo "release tag must be annotated" >&2; exit 1; }
[ "$(git rev-parse "refs/tags/$tag^{}")" = "$(git rev-parse HEAD)" ] \
  || { echo "release tag does not identify the checked-out HEAD" >&2; exit 1; }
echo "Release identity verified: $tag -> $(git rev-parse HEAD)"

script="$("$python" -c 'import tomllib;print(next(iter(tomllib.load(open("pyproject.toml","rb"))["project"]["scripts"])))')"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
rm -rf dist

"$python" -m venv "$work/build"
"$work/build/bin/python" -m pip install --quiet --upgrade build
"$work/build/bin/python" -m build --sdist --wheel --outdir dist
if command -v sha256sum >/dev/null; then
  (cd dist && sha256sum ./*.whl ./*.tar.gz | sed 's# \./# #' > SHA256SUMS)
else
  (cd dist && shasum -a 256 ./*.whl ./*.tar.gz | sed 's# \./# #' > SHA256SUMS)
fi
cat dist/SHA256SUMS

for kind in whl tar.gz; do
  "$python" -m venv "$work/consumer-$kind"
  "$work/consumer-$kind/bin/python" -m pip install --quiet dist/*."$kind"
  "$work/consumer-$kind/bin/$script" --help >/dev/null
  echo "Verified installed $kind consumer: $script --help"
done

if [ -n "${DRY_RUN:-}" ]; then
  echo "DRY_RUN set: built and verified $tag; not publishing."
  exit 0
fi

repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
gh release create "$tag" dist/*.whl dist/*.tar.gz dist/SHA256SUMS \
  --repo "$repo" --verify-tag --title "$repo $tag" --generate-notes --prerelease
echo "Published $repo $tag"
