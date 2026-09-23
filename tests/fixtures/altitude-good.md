# Session Handoff — the window-altitude protocol altitude landing (good fixture)

## Continuity Kernel

```text
WORKSTREAM_OR_PROJECT=session-handoff contract, the window-altitude protocol altitude landing
CURRENT_POSITION=altitude / landed-index / unlanded fields landed at WARN tier; fixture regression green
CURRENT_AUTHORITATIVE_STATE_OR_SOT=00_SOT/DUAL_CHANNEL_MERGE_PROTOCOL_20260901.md (candidate protocol)
CLEARED_FIRST_ACTION=python3 tests/run_tests.py — read-only, already authorized
RECEIVER_MODE=EXECUTE_FIRST_ACTION
NEXT_GATE=ERROR-tier promotion of the altitude lint rules
NEXT_GATE_AUTHORIZATION=NOT_AUTHORIZED
FINAL_AUTHORITY=USER
```

## Receiver Immediate Brief

- To the new session: you are the receiver — verify the anchors, then start the cleared first action; do not stop to ask for the task.
- Cleared first action (start now): run `python3 tests/run_tests.py`; confirm 9/9 fixtures and the three-file real-file regression.
- Done when / Stop if: done when the suite exits 0; stop and report if any existing fixture regresses.
- Receiver mode: EXECUTE_FIRST_ACTION
- Next-gate authorization: NOT_AUTHORIZED (ERROR-tier promotion needs the re-discussion trigger; see Window Altitude below)
- Project / workstream: session-handoff contract, the window-altitude protocol altitude landing
- Current node: fields landed at WARN tier; re-discussion trigger recorded
- What this session completed: contract section, outline template, method sweep step, lint rules, fixtures
- Why the session is transitioning now: window closure per the window-altitude protocol
- Current authoritative state / SOT: candidate protocol landed at WARN tier — persistent SOT/charter file: $WORKSTREAM_ROOT/00_SOT/DUAL_CHANNEL_MERGE_PROTOCOL_20260901.md
- Current task for the next session: consume the outcome receipt; no new work opened
- Allowed / Not allowed / do not repeat: allowed to re-run tests; not allowed to self-promote the rules to the ERROR tier; do not re-derive the anchor syntax, it is fixed below
- Required files or sources: SKILL.md, assets/handoff-outline.md, references/handoff-method.md, scripts/lint_handoff.py, tests/run_tests.py
- Receipt duty: when the first work cycle ends, write a Receiver Outcome Receipt to receipts/altitude-good.md — one file per receipt, named for the handoff it evaluates.

## Summary — what happened

The the window-altitude protocol altitude trio, the landed-protocols index, and the unlanded-directions field were added to the contract surface at advisory WARN tier. The session closes because the window round is complete.

## Delta from Predecessor

```text
PREDECESSOR_HANDOFF_ID=HANDOFF_RULES_ITERATION_DUAL_CHANNEL_20260901
NEW_SINCE_PREDECESSOR=altitude trio, landed index, and unlanded directions landed in the contract surface
AUTHORITY_OR_STATE_CHANGED=NONE
SUPERSEDED_OR_CORRECTED=NONE
UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=the window-altitude protocol field semantics, carried verbatim
```

## Window Altitude (the window-altitude protocol)

```text
L_CARRY=L2
L2_MECHANISMS=
  - 检查器能抓到什么由它读什么决定（内部自洽的偏差必然沉默） — ../../SKILL.md#Advisory lint
  - 交接面缺高度字段，重述成本被误当推进成本（window-altitude protocol） — ../../references/handoff-method.md:1
NEXT_FLOOR=L2
```

跨窗判据（窗口高度协议逐字）：进度 = L_CARRY(n+1) > L_CARRY(n)；相等 ⇒ 原地踏步，如实登记；低于 NEXT_FLOOR 的产出除非推翻该级结论，否则记为回退轮。

## Landed Protocols Index

```text
LANDED_PROTOCOLS_INDEX=
  [enumerated] session-handoff contract tree: SKILL.md, assets/handoff-outline.md, references/handoff-method.md, scripts/lint_handoff.py, tests/run_tests.py — read each when editing the contract surface
  [enumerated] system-level: knowledge-base reading guide, structural anchor heading of that guide's entry section — read when drafting a dispatch
  [manual] NONE — this window's touch set is fully covered by the enumeration
```

## Unlanded Directions

```text
UNLANDED_DIRECTIONS=
  - demo: a direction recorded only in conversation never reaches the next window — ../../SKILL.md @ 2026-08-27 — quote: "future directions"
  Checked: current window transcript swept for the window's own direction keywords
  Not checked: older windows and the full corpus (unindexed) — no exhaustive sweep claimed
```

## Facts and Evidence

| Claim / purpose | Source or path | Identity / result | Verification status |
|---|---|---|---|
| altitude fields entered the contract | SKILL.md, Window Altitude section | contract section, verbatim the window-altitude protocol lines | verified by fixture run |
| lint stays advisory | scripts/lint_handoff.py | WARN tier only, scope-gated | verified by fixture run |
