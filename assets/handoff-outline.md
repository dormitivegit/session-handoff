# Adaptive Handoff Outline

Contract version 2.3. Use this as a content and receiver-readiness guide. It is **not** a mandatory fixed template. Rename, combine, reorder, or omit sections to fit the task. Never output empty sections.

# <Project / Workstream> — Session Handoff

## Continuity Kernel

For any handoff the receiver must continue, put this first. Field names may adapt; the semantics may not be dropped. Write `NONE` / `UNKNOWN` / `CONFLICT` rather than silently autofilling.

```text
WORKSTREAM_OR_PROJECT=
CURRENT_POSITION=
CURRENT_AUTHORITATIVE_STATE_OR_SOT=
CLEARED_FIRST_ACTION=
RECEIVER_MODE=
NEXT_GATE=
NEXT_GATE_AUTHORIZATION=
FINAL_AUTHORITY=
```

## Receiver Immediate Brief

Lead with what to do, not what to avoid. Recommended compact shape:

- **To the new session:** you are the receiver — verify the anchors, then start the cleared first action below; do not stop to ask for the task.
- **Cleared first action (start now):** <single runnable action; mark "read-only / already authorized" when it is>
- **Done when / Stop if:**
- **Receiver mode:** EXECUTE_FIRST_ACTION | AWAIT_USER_DECISION
- **Next-gate authorization:** AUTHORIZED | NOT_AUTHORIZED | USER_DECISION_REQUIRED
- **Project / workstream:**
- **Current node:**
- **What this session completed:**
- **Why the session is transitioning now:**
- **Current authoritative state / SOT:** <state> — persistent SOT/charter file: <path or NONE>
- **Current task for the next session:**
- **Allowed / Not allowed / do not repeat:**
- **Required files or sources:**

## Delta from Predecessor (when a predecessor exists)

```text
PREDECESSOR_HANDOFF_ID=
NEW_SINCE_PREDECESSOR=
AUTHORITY_OR_STATE_CHANGED=
SUPERSEDED_OR_CORRECTED=
UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=
```

With no predecessor, omit this section or write `NOT_APPLICABLE`. Never emit an empty shell table, and never treat a similarly named document as lineage.

## Revalidation Boundary (long projects, or where repeat-verification risk exists)

```text
REVALIDATE_NOW=
CARRY_FORWARD_AS_ACCEPTED=
DO_NOT_REOPEN_UNLESS_TRIGGERED=
REOPEN_TRIGGERS=
```

This boundary must never block verification demanded by new evidence, an updated user ruling, or a current-SOT conflict.

## Window Altitude (candidate protocol, advisory)

For a dual-channel / multi-window handoff, fill at window closure — a round missing these is recorded as not closed (definitions verbatim from the window-altitude protocol):

```text

L_CARRY        本窗口收口时抵达的层级（L0–L3）
L2_MECHANISMS  本窗口已自主形成的 L2 机制清单（一行一条，可回锚）
NEXT_FLOOR     下一窗口的**起步下限**——新窗口不得在此级以下重新论证
```

Each `L2_MECHANISMS` entry line ends with a machine-resolvable anchor — `<path>#<markdown heading>` or `<path>:<line-number>`, path absolute, relative to this handoff file, or `$SKILL_ROOT/`-rooted (resolved to this skill's own directory, so the anchor survives relocation). A bare semantic event id (`E5`, `A6b`, `M1`) is not an anchor: no path, no machine resolution. Filled example:

```text
L_CARRY=L2
L2_MECHANISMS=
  - 检查器能抓到什么由它读什么决定 — $SKILL_ROOT/SKILL.md#Advisory lint
  - 交接面缺高度字段 ⇒ 重述成本被误当推进成本 — $SKILL_ROOT/references/handoff-method.md:1
NEXT_FLOOR=L2
```

Cross-window progress (protocol verbatim): 进度 = L_CARRY(n+1) > L_CARRY(n)；相等 ⇒ 原地踏步，如实登记，不粉饰为「巩固」「夯实」；低于 NEXT_FLOOR 的产出除非推翻该级结论，否则记为**回退轮**。

The advisory lint warns — WARN tier only (re-adjudicate the ERROR tier when the protocol reaches its 3rd independent empirical and its §1 channel-count correction lands) — on missing fields in an altitude-scope handoff, out-of-set values, `NEXT_FLOOR` above `L_CARRY`, and `L_CARRY ≥ L2` without resolvable mechanism anchors.

## Landed Protocols Index

Distinct from `CURRENT_AUTHORITATIVE_STATE_OR_SOT` (current authoritative **state**): this carries what the system has **already built** — protocols, mechanisms, task roots — one line each with pointer + when-to-read. Bind it to a **mechanical enumeration source**; a recall-only list cannot list what the author does not know exists (named `LANDED_PROTOCOLS_INDEX` to avoid the asset-library `ASSET_INDEX` name collision):

```text
LANDED_PROTOCOLS_INDEX=
  [enumerated] lines from the mechanical source — e.g. `ls <workstream-root>/00_SOT/`;
               for system-level protocols, the reading guide of the cross-workstream knowledge base
               (structural anchor: that guide's own entry heading)
  [manual] lines the enumeration cannot see yet, each with a reason
```

Keep the two labels separate. Point, don't dump (progressive disclosure).

## Unlanded Directions

Directions **raised but never landed** in any file. Distinct from Development Directions (§9): a development direction is forward-looking; an unlanded direction was already said — original-voice anchor required — and never reached disk. A non-anchored future idea belongs in §9, not here.

```text
UNLANDED_DIRECTIONS=
  - <direction> — <source-file> @ <YYYY-MM-DD[THH:MM[:SS]]> — quote: "<verbatim fragment>"
  Checked: <what was actually searched — the current window's transcript, the keywords used>
  Not checked: <the unindexed or unsearched remainder>
```

The judgment surface must include the current window's session transcript (closure sweep step in `references/handoff-method.md` §2). `NONE` is legal only with the Checked / Not checked record — a bare `NONE` is a silent disclaimer and the lint warns on it; absence of entries itself is never verifiable.

## 1. Mission and Success Standard

Explain the project goal, this workstream's purpose, and what success ultimately means.

## 2. What Happened and Why

Summarize the meaningful session arc, turning points, discoveries, and reason for the current node.

## 3. Technical Route and Evolution

Describe the current technical route, how it evolved, important implementation details, alternatives tried, problems found, and why the present approach was chosen.

## 4. Current State

Separate as relevant:

- confirmed complete;
- executed;
- verified;
- reported but not reverified;
- incomplete;
- blocked;
- deferred;
- closed or superseded;
- unknown or conflicting.

State the current SOT and authority sources.

## 5. User Decisions, Authority, Priorities, and Boundaries

List, where applicable: **ADJUDICATED**, **AUTHORIZED**, **NOT_AUTHORIZED**, **REJECTED**, plus user priorities and durable boundaries.

Preserve important own-voice decisions and explain which model proposals were not adopted.

## 6. Facts and Evidence

For each load-bearing claim, give a resolvable source when available:

| Claim / purpose | Source or path | Identity / result | Verification status |
|---|---|---|---|

### Recompute block (whenever this handoff carries volatile readings)

State plainly that the values in the text are stale by default, then list the commands that regenerate each one:

> Values below are as-of-writing. Do not inherit them. Recompute with the commands in this block; if a command fails or returns something unaccounted for, that is a defect in this handoff.

```bash
one command per volatile reading
```

Sealed identities — frozen hashes, closed routes — are exempt; carry those values directly.

Also state the actual history/files checked and the inaccessible scope.

## 7. Problems, Failed Approaches, and Lessons

Keep only failures and lessons that affect future work. Explain failure cause and prevention, not merely that an attempt failed.

## 8. Current Problems and Next-Session Task Map

- Current problem to solve
- Why it matters now
- First work cycle: read/check/do/output
- Completion criteria
- Stop, HOLD, or decision conditions
- Next stage after completion

## 9. Development Directions

Separate future directions from current execution:

- promising branches;
- research or product opportunities;
- limits of the current route;
- trigger conditions for reopening closed routes;
- capabilities worth generalizing.

## 10. Materials and Upload Plan

### Required
- <file/source> — <purpose>

### As needed
- <file/source> — <purpose>

### Do not upload / superseded
- <file/source> — <why it should not anchor the receiver>

## 11. Risks, Conflicts, and Unknowns

Explain impact and recovery path. Do not manufacture risks for symmetry.

## 12. Copyable New-Session Opening (ship this with the handoff)

Write a self-contained opening prompt tailored to the receiving role. It must put the receiver in receiver mode: *this is a handoff to act on, not reference material — verify the anchors, then run the cleared first action; return a HOLD/CONFLICT only if an anchor fails or the SOT is not unique; do not reply "please give me the task."* It should also state the task, current state, boundaries, cleared first action, required output, and whether the receiver must first report intake gaps.

It must also carry the **receipt duty**: one line telling the receiver to write a separate Receiver Outcome Receipt (see below) when its first work cycle ends or stops, naming the destination path. The receiving session reads this handoff and nothing else from this skill — a duty left in the skill files never reaches it.

It must also carry the **method-use instruction** — same reason, same mechanism: *before a relevant action, pick one method with a source (from `METHOD_INCREMENT` or a cross-workstream knowledge base) and judge whether it applies here; refusing an inapplicable method is a correct outcome. After acting, record method → opportunity → action → result, plus a cost comparison if one exists. If no opportunity arose, write `待复用` rather than claiming the method worked.* Short prose is fine; do not add a field, a ledger, or a database.

## Conditional Appendix — High-Risk / Irreversible Continuity

Include only when triggered:

- original authorized scope;
- exact executed scope and evidence;
- remaining scope and blocker;
- additional authorization not granted;
- affected-set universes;
- preserve / restore / rollback duties;
- executor/session/work-root continuity;
- parallel-writer or handover rule;
- HOLD conditions.

---

## Separate artifact — Receiver Outcome Receipt

**Do not embed this in the handoff.** The receiving session writes it after it has actually run or stopped the first work cycle. The producer's self-assessment cannot substitute for it.

```text
HANDOFF_ID=
RECEIVER_SESSION_OR_ROLE=
STARTED_CORRECT_FIRST_ACTION=YES|NO
REASKED_KNOWN_INFORMATION=YES|NO
AUTHORITY_DRIFT=YES|NO
SOT_CONFLICT=YES|NO
UNNECESSARY_REVALIDATION=YES|NO
CONTEXT_OVERLOAD=YES|NO
OBSERVED_FAILURE_OR_GAIN=
```

A receipt evaluates receiving behaviour only. It must never retroactively edit the handoff, approve a mutation, or override user authority.

**Where it goes.** The producer names a concrete destination in the copyable opening (§12). Default for a file-persisted workstream: a `receipts/` directory beside that workstream's SOT, one file per receipt, named for the handoff it evaluates. An unnamed destination means no receipt.
