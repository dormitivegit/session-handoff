# Session Handoff — dual-channel scope without L_CARRY (fail fixture, WARN tier)

This fixture carries dual-channel semantics, so the altitude scope gate applies. It deliberately omits `L_CARRY` (and `L2_MECHANISMS`) while keeping every other field legal, to prove the the window-altitude protocol "missing means the round is not closed" rule fires as a WARN — never an ERROR (§3.9 ruling 2026-09-05).

## Continuity Kernel

```text
WORKSTREAM_OR_PROJECT=session-handoff contract, altitude scope demo
CURRENT_POSITION=altitude scope reached without the altitude trio
CURRENT_AUTHORITATIVE_STATE_OR_SOT=00_SOT/DUAL_CHANNEL_MERGE_PROTOCOL_20260901.md
CLEARED_FIRST_ACTION=run the advisory lint on this fixture — read-only
RECEIVER_MODE=EXECUTE_FIRST_ACTION
NEXT_GATE=NONE
NEXT_GATE_AUTHORIZATION=NOT_AUTHORIZED
FINAL_AUTHORITY=USER
```

## Window Altitude (the window-altitude protocol) — deliberately incomplete

```text
NEXT_FLOOR=L2
```

## Landed Protocols Index

```text
LANDED_PROTOCOLS_INDEX=
  [enumerated] session-handoff contract tree: SKILL.md, scripts/lint_handoff.py — read when editing the contract
  [manual] NONE
```

## Unlanded Directions

```text
UNLANDED_DIRECTIONS=
  Checked: current window transcript swept for this window's keywords
  Not checked: full corpus (unindexed) — no exhaustive sweep claimed
```
