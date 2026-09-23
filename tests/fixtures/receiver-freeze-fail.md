# Permission-HOLD Node — Session Handoff

authority: HOLD
context_basis: RECONSTRUCTED
validation_mode: MODEL_ONLY

This handoff is the only continuation authority for the current permission-HOLD node. It only produces a state-transfer artifact; its Next Action has not been executed. The receiver must re-verify all anchors locally before trusting anything here.

## Mission
Retire the frozen exact whitelist substrate without losing any protected audit asset, then produce a verifiable closeout.

## Current Effective State
State is HOLD_PERMISSION_NORMALIZATION_NOT_AUTHORIZED. 12 of 551 roots were permanently deleted; 539 stopped because some required parent directories are mode 0555. No new permission mutation is authorized. All reported PASS counts are relayed and must be reverified.

## Boundaries
Deletion must be exact-path only. No permission change, no privilege escalation, no parallel writer. Any owner-write proposal must first form an exact plan and wait for the user.

## Next Action
In the same executor session, run a read-only revalidation of the deletion receipt, residual inventory, and bound whitelist; then produce a per-directory permission plan. Do not chmod, delete, or escalate. Stop after producing the plan and submit for explicit user authorization.

## Receiver Start
1. Verify the evidence anchors before formal execution.
2. Restate the SOT, boundaries, and the single next action.
3. If any anchor conflicts or is unavailable, mark HOLD and report the mismatch.
