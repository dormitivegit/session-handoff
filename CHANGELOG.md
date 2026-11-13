# Changelog

Versions follow `CARRIER_VERSION`. Earlier versions were developed in a private working copy; this repository
begins at 2.4.24. Every release here has passed the acceptance run described in `README.md`.

## 2.6.1 — 2026-11-13

- Readout fixes from an independent review of 2.6.0 (all four blocking findings reproduced before fixing):
  - The working-directory lesson is now counted from what the host recorded (`environment` records whose new working
    directory is neither the start directory nor a temp directory), not by parsing command text; a transcript without
    such records reports the pattern as untested.
  - The pasted block may sit inside a fence that starts between `PROGRESS_AXIS=` and the first `READOUT_` line;
    recomputing still gives the same size line.
  - `READOUT_E3` drops the summed rate (different denominators were being added) and only counts a lesson as
    "zero for five windows" when those windows gave at least 20 opportunities; the rest are reported as untested.
- The snapshot line carries `tool=` (sha12 of the readout and of the pattern table), so two readings can be checked to
  come from the same instrument.
- The exit-status pattern only counts a read of `$?` after a pipeline whose last stage is a filter (`tail`, `head`,
  `grep`, …); renamed `pipe_filter_swallowed`.
- A failed validity check no longer calls the detectors (no traceback); `--session auto` breaks timestamp ties by the
  longer transcript.
- New lint rule `readout_block_rule`: warns when the pasted `READOUT_SIZE` text hash no longer matches the file (the
  handoff was edited after the readout ran).
- `references/readout.md`: what each readout line means and how a lesson pattern is registered. SKILL.md now gives
  `--session <path>` as the default command; `--session auto` needs `HANDOFF_TRANSCRIPT_ROOT`.

## 2.6.0 — 2026-11-12

- New `scripts/handoff_readout.py`: the handoff's progress axis is computed from the window's own transcript and
  pasted verbatim, instead of being written by hand. Output is ≤ 10 lines, starts with an input snapshot (path, line
  count, sha256, last timestamp) and ends with the exact recompute command; reruns are byte-identical.
- Lesson patterns (`scripts/lesson_patterns.py` · `scripts/lesson_detectors.py`) with canaries and a pinned detector
  hash; any mismatch makes the readout print "failed validity check" instead of numbers. A plain install ships an empty
  pattern table and says so.

## 2.5.2 — 2026-11-12

- Fix: the method-increment landing rule reported its registry cross-check as RUN whenever the registry variable was
  set, even if the file was never opened. It now reports RUN only after the registry is read and parsed, and NOT_RUN
  with the reason (and a warning) otherwise. Six-cell negative-control test.

## 2.5.1 — 2026-11-06

- Restored one load-bearing principle dropped in 2.5.0's de-duplication (a handoff must be usable without the producer's
  skill, hidden memory, or private reasoning), and a pointer for iteration windows to read receipts as a set first.

## 2.5.0 — 2026-11-06

- SKILL.md cut by about a third: version-axis and claim-ledger notes moved to `VERSION_LEDGER.md` (now part of the
  contract face), workflow first, repeated principles removed.
- The opening prompt only activates the first authorized action and points at the single `CLEARED_FIRST_ACTION`;
  it no longer copies the plan.

## 2.4.31 — 2026-10-25

- Step 12 becomes a write-time cold read: a context-free reader checks the handoff (`assets/cold-read-probe.md`) and the
  result is recorded as `COLD_READ=`; new lint rule `cold_read_rule` warns when the record is missing.
- Tests now also run every fixture through lint's text mode, so a crash outside `--json` fails the suite.

## 2.4.30 — 2026-10-18

- Evolution-kernel rule follows real writing: heading forms, entries inside fences, and inherited ranges ("K1 to K5,
  as before") are recognized; an empty kernel section warns. Entry numbers of any width are parsed (three-digit ids no
  longer drop out).

## 2.4.29 — 2026-09-23

- The placeholder rule no longer treats text inside HTML comments (single-line or multi-line) as unfilled slots:
  comments are not rendered, so an angle bracket there is not a value. New discrimination-matrix row.

## 2.4.28 — 2026-09-23

- Skill description now names the problem it solves and the terms people search for (session / context handoff), so
  agents and search can find it; the trigger sentence is unchanged.
- README states the problem, what you get, a quick start, an example, when to use it, and how it compares.

## 2.4.27 — 2026-09-22

- Standing rulings in a method increment must carry a verbatim-source anchor (`<transcript> @ <timestamp>`), so the
  next session can read the original words instead of a paraphrase. Checked by the method-increment landing rule for
  handoffs dated on or after the rule's floor; new fixture and discrimination-matrix row.
- Guidance: turn a recurring error into a class-level check — one definition, a registry tested across all forms, a
  structural guard, and a control that must flip — rather than an instance patch.
- Contract wording: a handoff is a capability-elevating transfer, not a high-fidelity copy.
- Volatile readings: write the command that produces a pass count, not the count. The contract records why no rule
  flags a bare fraction: it cannot be told apart from a sealed historical citation.

## 2.4.26 — 2026-09-22

- Neutral wording in judge messages and self-test strings.

## 2.4.25 — 2026-09-22

- Discrimination-matrix anchors must be unique in comment-stripped source; this is checked while iterating, not only
  when building.

## 2.4.24 — 2026-09-22

- Location-independent self-references (`$SKILL_ROOT/…`), with one path grammar and one resolver for every path the
  lint and the tests read; new path-grammar face.
- Sealed test environment; new hermetic face.
- Frozen-face rename register, so a renamed fixture is not mistaken for a removed one.
