# session-handoff

[![tests](https://github.com/dormitivegit/session-handoff/actions/workflows/tests.yml/badge.svg)](https://github.com/dormitivegit/session-handoff/actions/workflows/tests.yml)

**Session handoffs that let the next session start higher than this one ended.**

A skill for long, multi-session work with AI agents. At a session boundary it has the agent write a handoff that
carries not just *what happened* but *what the next session may do, what is still true, and what this session
learned* — and it ships with an advisory lint and a self-verifying test suite, so the handoff's claims can be checked
instead of trusted.

## The problem

Switching sessions is where long agent work quietly loses ground:

- **The next session starts from zero.** It re-asks what was already known, or re-litigates decisions that were settled.
- **Summaries keep conclusions and drop the "how".** Methods that worked, and mistakes that were corrected, get
  rediscovered the hard way — sometimes by making the same mistake again.
- **State claims go stale.** "Tests pass", "7 of 8 checks green", "no open items" were true when written and are
  false when read. Nothing tells the reader which facts were live.
- **Authority drifts.** A recommendation is read as an approval, or an old approval is stretched over new scope.
- **Corrections are paraphrased away.** The user's own words survive only as the previous session's summary of them,
  and the principle behind a correction is the first thing a paraphrase loses.
- **None of this raises an error.** The next session simply starts lower, and nobody notices.

## What you get

- **A contract for the handoff** (`SKILL.md`): understanding, technical direction, current state, the next cleared
  action, authority boundaries and the path forward — topped by a *Continuity Kernel* so the receiver can act in the
  first minute, and a copyable opening that tells it to.
- **Live facts travel as commands, not snapshots.** Anything that can change after the handoff is written (a count,
  a gate, a version, a pass rate) is handed over as the command that re-reads it.
- **Two authority axes.** What the receiver may do now is separated from what needs a new decision; reporting a
  HOLD is separated from releasing one.
- **Capability, not just state.** A *method increment* carries what this session learned — standing rulings with a
  verbatim-source anchor, methods that worked, methods that failed and where. An *evolution kernel* carries an
  integrated, anchored base across generations, with a budget so it cannot grow without bound.
- **A feedback loop.** The receiving session writes a short *receiver outcome receipt* — did it start on the right
  action, did it have to re-ask anything — the only signal that shows whether a handoff actually worked.
- **An advisory lint** that catches what can be caught mechanically (exposed secrets, unfilled placeholders,
  unresolvable anchors, bare counts of live sets, a missing receipt duty, …) and always reports what it searched.

## Quick start

1. Copy or clone this directory into the skills folder your agent loads skills from.
2. At a session boundary, ask the agent for a handoff — it follows `SKILL.md` — or fill in `assets/handoff-outline.md`.
3. Lint it:

   ```bash
   python3 scripts/lint_handoff.py HANDOFF.md
   ```

4. Start the next session with the handoff's opening. The receiver re-runs the handoff's recompute commands, takes
   the cleared first action, and writes its receipt.

## What it looks like

The top of a handoff — the Continuity Kernel:

```text
WORKSTREAM_OR_PROJECT=billing-service migration
CURRENT_POSITION=schema migrated in staging; backfill script written, not yet run
CURRENT_AUTHORITATIVE_STATE_OR_SOT=docs/STATUS.md
CLEARED_FIRST_ACTION=re-run the staging checks listed in §2 (read-only), then compare with the table there
RECEIVER_MODE=EXECUTE_FIRST_ACTION
NEXT_GATE=run the backfill against production
NEXT_GATE_AUTHORIZATION=NOT_AUTHORIZED
FINAL_AUTHORITY=USER
```

What the lint says about a handoff that stops at an unapproved gate without clearing a first action, and never asks
for a receipt (real output on one of the test fixtures):

```text
WARN: possible receiver-freeze: HOLD/await-authorization signal present without an explicit cleared first action or receiver mode; …
WARN: no receipt-delivery instruction; the receiving session reads only this handoff, so the opening must tell it to write a separate Receiver Outcome Receipt and where …
HINT: no obvious signal for dimension 'summary'; review manually if it matters for this task
```

## When to use it

- Work that spans several sessions, or that is handed to a different model or agent.
- Before a context reset or compaction, when the session holds understanding that is not yet written down.
- When state lives in files and decisions must survive the session that made them.

It is not needed for one-shot tasks, or when the same session simply continues.

## How it compares

- **Automatic conversation summaries or compaction** keep conclusions, but drop authority boundaries, methods, and
  which facts are still live.
- **Memory notes** suit durable preferences; they are not a state transfer with a cleared next action.
- **Multi-file state trackers** put their effort into maintaining state files. This skill keeps one document per
  transfer and puts its effort into claims that can be verified and into feedback from the receiver.

## Requirements

Python 3.10 or newer (CI runs 3.12 and 3.13) and git. No third-party packages.

## Install and use

References inside the skill are written as `$SKILL_ROOT/…` and resolve to wherever the directory lives, so nothing
needs editing after a move. Lint output: `--json` for machine use; exit code 0 means clean or warnings only, 1 means
an ERROR is present, 2 means the file was not found. The lint checks form, not meaning — `CLEAN` is not a quality
verdict. So that it does not depend on anyone remembering to run it, have your host call `lint()` once at session end
on the handoffs that session wrote.

Optional environment variables. Each one, when unset, is reported as not run — an unchecked face is never read as a
pass:

| variable | effect |
|---|---|
| `SESSION_HANDOFF_CORPUS` | colon-separated real handoffs for the real-file regression tier |
| `SESSION_HANDOFF_ENTRIES` | a registry file, enabling the dangling-entry check for method increments |
| `HANDOFF_ACTION_POINTS` | colon-separated globs of your host's action-point files, enabling carrier wiring checks |

## Contents

```text
SKILL.md                                             the contract the agent follows
references/handoff-method.md                         method detail: dimensions, authority axes, receiver activation
references/window-altitude-and-method-increment.md   multi-window fields: altitude, method increment, evolution kernel
assets/handoff-outline.md                            a fill-in outline
scripts/lint_handoff.py                              advisory lint (ERROR / WARN / HINT tiers)
scripts/version_axis_check.py                        version axis: declaration sites agree; every contract-face commit is claimed
tests/run_tests.py                                   fixtures, discrimination matrix, judge faces, frozen-face ratchet
tests/fixtures/                                      test inputs
```

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
