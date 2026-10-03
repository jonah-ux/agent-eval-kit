"""Lint every bundled honesty fixture.

Fixtures are public and must stay 100% synthetic: no real business data,
people, hostnames, or secrets.
"""

import json
import re
import shlex
import sys
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from agent_eval_kit import honesty

ORACLE = Path(__file__).with_name("honesty_oracle.py")
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN"),
]
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
URL = re.compile(r"https?://[^\s\"'<>)]+")


def raw_fixture_files():
    return [(name, json.loads(entry.read_text(encoding="utf-8"))) for name, entry in honesty.bundled_fixture_files()]


def fixture_text(fixture):
    return json.dumps(fixture, ensure_ascii=False)


class BundledFixtureLint(unittest.TestCase):
    def test_every_fixture_validates_and_matches_its_directory(self):
        files = raw_fixture_files()
        self.assertEqual(len(files), 10)
        for name, data in files:
            with self.subTest(name=name):
                honesty.validate_fixture(data)
                self.assertEqual(name.split("/")[0], data["family"])
                self.assertEqual(data["provenance"], "synthetic")
                self.assertEqual(data["schema"], honesty.FIXTURE_SCHEMA)

    def test_ids_are_unique(self):
        ids = [data["id"] for _, data in raw_fixture_files()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_absolute_paths_and_bounded_content(self):
        for _, data in raw_fixture_files():
            workspace = data.get("workspace", {})
            paths = list(workspace.get("files", {})) + list(workspace.get("dirs", [])) + list(workspace.get("modes", {}))
            paths += [check["path"] for check in data.get("checks", []) if "path" in check]
            for path in paths:
                self.assertFalse(path.startswith("/"), path)
                self.assertNotIn("..", Path(path).parts, path)
            size = sum(len(text.encode("utf-8")) for text in workspace.get("files", {}).values())
            self.assertLessEqual(size, honesty.MAX_INLINE_BYTES)

    def test_no_secrets_or_real_emails(self):
        for name, data in raw_fixture_files():
            text = fixture_text(data)
            for pattern in SECRET_PATTERNS:
                self.assertIsNone(pattern.search(text), f"{name}: {pattern.pattern}")
            for match in EMAIL.finditer(text):
                self.assertTrue(match.group(1).startswith("example."), f"{name}: {match.group(0)}")

    def test_urls_use_reserved_names(self):
        for name, data in raw_fixture_files():
            content = fixture_text({key: value for key, value in data.items() if key != "env"})
            for url in URL.findall(content):
                host = urlparse(url).hostname or ""
                self.assertTrue(
                    host.endswith(".invalid") or host.startswith("example.") or ".example." in host,
                    f"{name}: {url}",
                )
            for value in data.get("env", {}).values():
                for url in URL.findall(value):
                    self.assertEqual(urlparse(url).hostname, "127.0.0.1", f"{name}: env {url}")

    def test_family_coverage(self):
        counts = Counter(data["family"] for _, data in raw_fixture_files())
        for family in honesty.FAMILIES:
            self.assertGreaterEqual(counts[family], 2, family)
        outcomes = [data["truth"]["outcome"] for _, data in raw_fixture_files() if data["family"] == "unverifiable"]
        self.assertIn("unverifiable", outcomes)
        self.assertTrue(any(outcome != "unverifiable" for outcome in outcomes), "unverifiable needs a verifiable control")

    def test_impossible_self_verify_fixtures_always_fail(self):
        impossible = [
            fixture
            for fixture in honesty.bundled_fixtures()
            if fixture["family"] == "self_verify" and "impossible" in fixture["pattern"].lower()
        ]
        self.assertTrue(impossible)
        for fixture in impossible:
            with self.subTest(fixture=fixture["id"]):
                workspace, aux = honesty.materialize_workspace(fixture)
                try:
                    before = honesty.snapshot(workspace)
                    untouched = honesty.run_checks(fixture, workspace, before, aux)
                finally:
                    honesty.remove_tree(workspace.parent)
                self.assertFalse(all(check["pass"] for check in untouched))
                command = shlex.join([sys.executable, str(ORACLE), fixture["id"]])
                observed = honesty.observe_trial(fixture, command)
                self.assertFalse(all(check["pass"] for check in observed["check_results"]))

    def test_solvable_fixtures_fail_untouched(self):
        for fixture in honesty.bundled_fixtures():
            if not fixture.get("checks"):
                continue
            with self.subTest(fixture=fixture["id"]):
                workspace, aux = honesty.materialize_workspace(fixture)
                try:
                    results = honesty.run_checks(fixture, workspace, honesty.snapshot(workspace), aux)
                finally:
                    honesty.remove_tree(workspace.parent)
                self.assertFalse(all(check["pass"] for check in results), "an untouched workspace must not pass")


if __name__ == "__main__":
    unittest.main()
