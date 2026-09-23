# session-handoff

A skill for writing **session handoffs that let the next session start higher than this one ended** — not a chat
summary or a state dump, but a transfer of understanding, authority boundaries, current state, the next cleared
action, and the methods and corrected errors that the next session should not have to rediscover.

It ships with an advisory lint and a self-verifying test suite. Every check reports the size of what it looked at,
and a green result states what it does not prove.

## Contents

```text
SKILL.md                                             the contract the agent follows: when to use it, what a handoff carries
references/handoff-method.md                         method detail: dimensions, authority axes, receiver activation
references/window-altitude-and-method-increment.md   multi-window fields: altitude, method increment, evolution kernel
assets/handoff-outline.md                            a fill-in outline
scripts/lint_handoff.py                              advisory lint (ERROR / WARN / HINT tiers; --json for machines)
scripts/version_axis_check.py                        version axis: declaration sites agree; every contract-face commit is claimed
tests/run_tests.py                                   fixtures, discrimination matrix, judge faces, frozen-face ratchet
tests/fixtures/                                      test inputs
```

## Requirements

Python 3.10 or newer (CI runs 3.12 and 3.13) and git. No third-party packages.

## Install

Clone or copy this directory into the skills folder your agent loads skills from. References inside the skill are
written as `$SKILL_ROOT/…` and resolve to wherever the directory lives, so nothing needs editing after a move.

## Use

- The agent invokes the skill at a session boundary, before a model or agent transfer, or when continuing work in a
  fresh session. `SKILL.md` describes what the handoff must carry and how the receiver is activated.
- Lint a handoff:

  ```bash
  python3 scripts/lint_handoff.py path/to/HANDOFF.md          # human-readable
  python3 scripts/lint_handoff.py path/to/HANDOFF.md --json   # machine-readable
  ```

  Exit code 0 means clean or warnings only, 1 means an ERROR is present, 2 means the file was not found.
  The lint is advisory: it checks form, not meaning, and `CLEAN` is not a quality verdict.
- So that it does not depend on anyone remembering to run it, have your host call `lint()` once at session end on
  the handoffs that session wrote.

Optional environment variables. Each one, when unset, is reported as not run — an unchecked face is never read as
a pass:

| variable | effect |
|---|---|
| `SESSION_HANDOFF_CORPUS` | colon-separated real handoffs for the real-file regression tier |
| `SESSION_HANDOFF_ENTRIES` | a registry file, enabling the dangling-entry check for method increments |
| `HANDOFF_ACTION_POINTS` | colon-separated globs of your host's action-point files, enabling carrier wiring checks |

## Verify

```bash
python3 -B tests/run_tests.py                     # must exit 0
python3 -B scripts/version_axis_check.py          # must print ...=PASS
python3 -B scripts/version_axis_check.py --self-test
```

What the suite checks:

- **fixtures** — each fixture reaches its expected status
- **discrimination matrix** — removing any registered fix must change a public reading
- **rule face** — blanking any single rule's findings must change a reading; a standing line reports how many rules
  also have a falsifying reading (observable is not the same as correct)
- **path-grammar face** — every path-capturing pattern accepts all rooted forms, none is unregistered, and no path
  resolution bypasses the single resolver
- **hermetic face** — test subprocesses run in a sealed environment, and no test input references a file that exists
  on the machine running the tests
- **frozen-face ratchet** — frozen sets are compared with `git HEAD`, so a check cannot be removed by editing the
  check and its registry together

## Design principles

- Judgments are made by machines, and every judgment reports its own face — how much it looked at. A face that
  shrinks turns red.
- The truth surface sits outside the object being checked: git history, and an acceptance checker outside this tree.
- Slimming is integration: rules that share one logic become one composite rule, and retained capability is shown
  by comparing outputs byte for byte before and after.
- Errors become capability: a falsified claim yields a check with a falsifying reading, at the level of the class of
  error rather than the single instance.

## How this repository is maintained

This repository is built deterministically from the maintainer's working copy of the skill. The build removes
comments and working notes; the contract text, judges and tests are carried over unchanged. Every release passes an
acceptance run outside this tree that requires, among other things:

- judge-face readings identical to the working copy,
- identical code once comments and docstrings are removed,
- a clean `HOME` and a relocated clone both passing the suite,
- no private or host-specific content.

Release notes are in `CHANGELOG.md`; the build refuses to publish a version that has no entry there.

There are two version axes: `CARRIER_VERSION` is this carrier's own version, declared in three places that must
agree; `CONTRACT_VERSION` marks the contract text it aligns with.

## Limits

- So far observed on one host type and on one author's handoffs. How other writers' handoffs trigger the heuristics
  is untested — issues with real examples, private content removed, are the most useful kind.
- The lint checks form, not meaning.

## License

Apache-2.0 — see `LICENSE`.
