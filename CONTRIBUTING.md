# Contributing

Create a focused issue, add a fixture, run `python -m unittest discover -s tests`, and include a reproducible CLI example.

Honesty fixtures must be 100% synthetic (no real business data, people, hostnames or secrets), set `"provenance": "synthetic"`, and pass `tests/test_honesty_fixtures.py`.
