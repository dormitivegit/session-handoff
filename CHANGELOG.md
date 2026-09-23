# Changelog

Versions follow `CARRIER_VERSION`. Earlier versions were developed in a private working copy; this repository
begins at 2.4.24. Every release here has passed the acceptance run described in `README.md`.

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
