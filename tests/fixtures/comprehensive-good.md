# Example Project — Session Handoff

## Receiver Immediate Brief

- **Project / workstream:** Example migration
- **Current node:** Design approved; implementation not started
- **What this session completed:** Compared two designs and selected staged migration
- **Why the session is transitioning now:** Context is long; implementation should begin in a fresh executor session
- **Current authoritative state / SOT:** Design v3 is user-approved; no production changes occurred
- **Current task for the next session:** Implement stage 1 in the test environment
- **First 1–3 actions:** Read the design and test plan; inspect the repository; return an implementation plan
- **Allowed:** Read and prepare a patch
- **Not allowed:** Deploy or modify production
- **Required files or sources:** `/project/design-v3.md`, `/project/test-plan.md`

## What Happened and Why

The session moved from a direct cutover to a staged migration after testing showed rollback risk.

## Technical Route and Evolution

The current technical route uses a compatibility layer, test migration, verification, and only then production cutover. The direct route was rejected because it lacked rollback isolation.

## Current State

Design is complete and user-approved. Repository inspection and implementation are incomplete. Production is unchanged.

## Facts and Evidence

- Confirmed fact: design v3 was approved by the user.
- Verified: test result is recorded in `/project/test-plan.md`, SHA256 `0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef`.
- Reported but not reverified here: repository main branch is clean.

## Current Problems and Next-Session Task Map

First inspect the repository and map design v3 to files. Then return a patch plan and test commands. Stop before production deployment.

## Development Directions

Later stages may automate compatibility verification and convert the migration checks into a reusable workflow.

## Copyable New-Session Opening

Continue the Example migration at the approved design-v3 node. Read the two required files, inspect the repository, and return the stage-1 patch plan. Do not deploy or change production.
