# Acme Lite — Session Handoff

## To the new session (receiver opening)

You are the receiver, continuing the Acme Lite 07-17 release-window preparation. This is a handoff to act on, not reference material: verify the anchors, then start the cleared first action; do not reply "please give me the task."

- Receiver mode: EXECUTE_FIRST_ACTION (read-only preflight, already authorized).
- Cleared first action (start now): run the execution-card "gate 0" preflight (read-only) — check the main script SHA256 = 3da8bcd3...c6ba, the two header lines LIVE_TARGET_EPOCH=1784253600000 and TRIGGER_ADVANCE_MS=0, that no superseded build will load, and that the executor's full monitoring instruction for 07-17 is staged.
- Done when: all four checks green. Stop if: any SHA or epoch mismatch, or a superseded build would load — then HOLD and return to the user.
- Next-gate authorization: USER_DECISION_REQUIRED (the 07-17 10:00 live fire is time-gated and operated by the user).

## Summary — what happened and why

This session prepared the 07-17 window. Three clean live shots (07-12, 07-15, 07-16) showed the mechanism works as designed; preview timing was compressed from T+5.8s to T+17ms and still returned 555, so timing is ruled out as the bottleneck. The session stops here because the next signal only appears in the live window.

## Technical route and evolution

Route: official native release chain, hold-seam on onChallengeSuccess, single release at T, no this-assertion, minimal build 24.0.0. Earlier burst and finite-state-lock designs were rejected after they caused a self-inflicted miss; the route converged to a single clean shot plus observation.

## Current state / SOT

The mechanism is verified working across three shots; the bottleneck is server-side admission at T (555 = contention / load-shed), not software. The 555 cause is still unknown among pure-oversell, real-release-time, and transient-limit. Authoritative SOT file: /srv/acme/2026-07-12/outputs/ACME_SOT.md — reverify its paths and SHA before acting.

## Decisions and boundaries

Allowed: read-only preflight and monitoring. Not allowed / do not repeat: receiver identity assertion, bursts, request pools, auto-retry, auto-challenge, request rewriting, or tuning the trigger advance from a 555.

## Facts and evidence

- Verified: the 07-16 first-round diagnostic captured full timing; evidence acme-lite-hold-diagnostic-1784167212100.json.
- Reported but not reverified here: the relayed PASS counts in the SOT; the receiver must reverify.
- Main script SHA256 3da8bcd3d18cd60671acc5443ce43f6b0002865c0dbf3fb86eac6dbc8300c6ba.

## Next-session task map

First run the gate-0 preflight; then stage the executor's 09:50 full read-only monitoring; then, in the live window, fire once as a probe and let monitoring decide the 555 cause. Completion: the monitoring report answers the release-truth questions. Stop: any anchor mismatch.

## Development directions

If monitoring shows continuous shed with no available moment, close out or reframe (more capacity to raise the base rate, or judge the time not worth the cost). If a real release point appears, define a new strategy from it.

## Required files or sources

Required: ACME_SOT.md (authority); the 07-17 execution card and the executor's monitoring instruction. Superseded / do not anchor on: the earlier burst-and-lock build.
