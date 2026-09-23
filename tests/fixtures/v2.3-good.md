# Example Migration — Session Handoff

## Continuity Kernel

```text
WORKSTREAM_OR_PROJECT=Example migration — staged cutover line
CURRENT_POSITION=Stage 1 patch plan returned; stage 1 not applied
CURRENT_AUTHORITATIVE_STATE_OR_SOT=/project/sot/CURRENT_MIGRATION_SOT.md
CLEARED_FIRST_ACTION=Re-verify the two required anchors, then run the stage-1 test suite (READ_ONLY)
RECEIVER_MODE=EXECUTE_FIRST_ACTION
NEXT_GATE=Apply the stage-1 patch to the test environment
NEXT_GATE_AUTHORIZATION=NOT_AUTHORIZED
FINAL_AUTHORITY=user
```

## Receiver Immediate Brief

- **To the new session:** you are the receiver. Verify the anchors below, then start the cleared first action. Do not stop to ask for the task.
- **Cleared first action (start now):** run the stage-1 test suite read-only and report which of the 14 checks currently fail.
- **Done when:** the 14 check results are recorded with their exit codes.
- **Stop if:** the SOT path resolves to more than one file, or the design hash does not match the value below.
- **Receiver mode:** EXECUTE_FIRST_ACTION
- **Next-gate authorization:** NOT_AUTHORIZED — applying the patch needs a separate user decision.
- **Project / workstream:** Example migration, staged cutover line.
- **Current node:** Stage 1 patch plan returned and reviewed; nothing applied.
- **What this session completed:** mapped design v3 to 9 source files and produced the stage-1 patch plan.
- **Why the session is transitioning now:** the plan is complete and execution belongs in a fresh executor session.
- **Current authoritative state / SOT:** `/project/sot/CURRENT_MIGRATION_SOT.md` — production unchanged.
- **Current task for the next session:** establish the failing-check baseline before any patch is applied.
- **Allowed:** read, run the read-only test suite, report results.
- **Not allowed / do not repeat:** deploying to production; re-litigating the direct-cutover route, which the user rejected.
- **Required files or sources:** `/project/design-v3.md`, `/project/test-plan.md`.

## Delta from Predecessor

```text
PREDECESSOR_HANDOFF_ID=EXAMPLE_MIGRATION_SESSION_HANDOFF_20260801.md
NEW_SINCE_PREDECESSOR=Design v3 mapped to 9 source files; stage-1 patch plan produced
AUTHORITY_OR_STATE_CHANGED=Next gate moved from design approval to patch application, still NOT_AUTHORIZED
SUPERSEDED_OR_CORRECTED=The predecessor's estimate of 6 affected files was corrected to 9
UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=Mission, staged-cutover route, and rejected direct-cutover route — see the SOT
```

## Revalidation Boundary

```text
REVALIDATE_NOW=The design-v3 hash and the uniqueness of the SOT path
CARRY_FORWARD_AS_ACCEPTED=The 9-file affected set and the staged-cutover route decision
DO_NOT_REOPEN_UNLESS_TRIGGERED=The direct-cutover route, rejected by the user
REOPEN_TRIGGERS=Design hash mismatch, a newer user ruling, or rollback isolation proving unattainable
```

## What Happened and Why

The session moved from a direct cutover to a staged migration after testing showed rollback risk. This session then translated the approved design into a concrete file-level plan.

## Technical Route and Evolution

The current technical route uses a compatibility layer, a test migration, verification, and only then production cutover. The direct route was rejected because it lacked rollback isolation. The architecture keeps the compatibility layer removable so stage 3 can drop it without a second migration.

## Current State

Design is complete and user-approved. The stage-1 patch plan is written but not applied. Production is unchanged. The failing-check baseline is not yet established, which is why it is the first action.

## User Decisions, Authority, Priorities, and Boundaries

- ADJUDICATED: staged migration replaces direct cutover.
- AUTHORIZED: read-only inspection and test execution.
- NOT_AUTHORIZED: applying any patch, and any production change.
- REJECTED: direct cutover — it must not return repackaged as an optimization.

## Facts and Evidence

| Claim | Source | Identity | Verification status |
|---|---|---|---|
| Design v3 approved | user message 2026-08-01 | own-voice ruling | Confirmed fact |
| Affected set is 9 files | `/project/design-v3.md` mapping | SHA256 `0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef` | Verified this session |
| Main branch is clean | executor report | commit `abc1234` | Reported, not reverified here |

Checked: the current conversation, the two required files, and the SOT. Not checked: CI history and the deployment logs, which were not accessible.

## Problems, Failed Approaches, and Lessons

Direct cutover failed on rollback isolation: once the schema changed there was no path back without data loss. The lesson is that the compatibility layer is what buys reversibility, so it must not be optimized away early.

## Current Problem and Next-Session Task Map

Establish which of the 14 checks already fail, so that post-patch failures can be attributed. First run the suite read-only, then record exit codes, then report. Completion criterion is 14 recorded results. Stop before applying any patch.

## Development Directions

Later stages may automate compatibility verification and turn the migration checks into a reusable workflow. That work should not start before stage 1 has a clean baseline.

## Materials and Upload Plan

### Required
- `/project/design-v3.md` — the approved design the patch plan maps to.
- `/project/test-plan.md` — defines the 14 checks the first action runs.

### As needed
- `/project/sot/CURRENT_MIGRATION_SOT.md` — for milestone and value history.

### Do not upload / superseded
- `/project/design-v2.md` — superseded; it would re-anchor the receiver to the rejected direct cutover.

## Risks, Conflicts, and Unknowns

If the design hash does not match, the affected-set count is unreliable and the mapping must be redone before any patch. No other conflict is currently known.

## Copyable New-Session Opening

Continue the Example migration at the stage-1 baseline node. This is a handoff to act on, not reference material. Verify the design-v3 hash and that the SOT path is unique, then run the stage-1 test suite read-only and report the 14 check results with exit codes. Do not apply the patch and do not touch production; applying the patch is a separate user decision. Return HOLD only if an anchor fails or the SOT is not unique. Do not reply asking for the task.

When that first work cycle ends or stops, write a separate Receiver Outcome Receipt to `/project/sot/receipts/example-migration-stage1.md`. It records how this handoff was actually received; do not embed it here and do not let it edit this document.
