# Contributing

- Run `python3 -B tests/run_tests.py` before proposing a change; it must exit 0.
- A change to a judge (a rule in `scripts/lint_handoff.py`) should come with a falsifying reading: a fixture or a
  discrimination-matrix row whose reading changes when the fix is removed.
- Frozen sets are ratcheted against `git HEAD`. Removing a fixture, a matrix row, or a rule's observability fails the
  suite even when both sides are edited together; if a removal is intended, explain why in the pull request.
- Keep references inside the skill in the form `$SKILL_ROOT/…`.
- The most useful issues are real handoffs that trigger a false positive or slip past a real defect. Remove private
  content before posting.

This repository is built from the maintainer's working copy. Accepted changes are applied there and published again,
so a merged pull request may reappear as a release commit.
