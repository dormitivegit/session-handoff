# Session Handoff — L2 mechanisms with unresolvable anchors (fail fixture, WARN tier)

This fixture declares `L_CARRY=L3` but its `L2_MECHANISMS` anchors use the real-world failure shapes: a bare semantic event id (E5) and a path that does not exist. The cross-field gate must flag both as WARN — it validates resolvability, never truth (§3.9 ruling 2026-09-05).

## Continuity Kernel

```text
WORKSTREAM_OR_PROJECT=session-handoff contract, anchor-gate demo
CURRENT_POSITION=cross-field gate regression fixture
CURRENT_AUTHORITATIVE_STATE_OR_SOT=00_SOT/DUAL_CHANNEL_MERGE_PROTOCOL_20260901.md
CLEARED_FIRST_ACTION=run the advisory lint on this fixture — read-only
RECEIVER_MODE=EXECUTE_FIRST_ACTION
NEXT_GATE=NONE
NEXT_GATE_AUTHORIZATION=NOT_AUTHORIZED
FINAL_AUTHORITY=USER
```

## Window Altitude (the window-altitude protocol)

```text
L_CARRY=L3
L2_MECHANISMS=
  - 检查器读什么决定它能抓什么 — E5
  - 交接缺高度字段 ⇒ 重述成本被误当推进成本 — ../../references/nonexistent-target.md#Some Heading
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
