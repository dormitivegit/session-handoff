# Handoff Method

Contract version 2.3. This reference supports the `session-handoff` Skill. It describes how to recover and transfer a session without reducing the result to a mechanical state interface.

## 1. Begin with the receiver

Before drafting, answer privately:

1. Who receives this handoff?
2. What must that receiver understand in the first minute?
3. What mistake is most likely if the receiver sees only a compressed state list?
4. What technical history prevents rediscovery?
5. What evidence must be locatable?
6. What must the receiver do in its first work cycle?
7. What future direction would be lost if only the immediate action were preserved?

These questions determine emphasis and length.

## 2. Source recovery and workstream control

Use all relevant sources that are actually accessible:

- current conversation;
- same-workstream historical sessions;
- uploaded or library files;
- prior handoffs and opening prompts;
- current-status or SOT documents;
- checkpoints, closeouts, receipts, tool output, commits, hashes, and command results;
- explicit user decisions and later corrections.

Search broadly enough to find the task line, then narrow to that workstream. Recent unrelated projects are not successor routes.

### Predecessor identification

If a predecessor handoff exists for this workstream:

1. verify its identity and that it governs the same workstream;
2. compare current SOT, user authority, task state, technical route, and key evidence;
3. extract what actually changed first, then decide which unchanged content only needs a pointer;
4. if the predecessor cannot be uniquely identified, mark it `UNKNOWN` / `CONFLICT` — a similarly named document is not lineage.

With no predecessor, recover normally and do not manufacture a delta to satisfy the format.

Record retrieval honestly:

```text
Checked: current conversation, named project sessions, and listed files.
Not checked: deleted, unavailable, unindexed, or inaccessible account history.
```

Never write “all history was scanned” merely because search was attempted.

### Current-window transcript sweep at closure (unlanded directions)

At window closure, before filling `UNLANDED_DIRECTIONS`, run one bounded sweep: search **this window's own session transcript** (the current session's transcript file — not account history) for directions that were raised in conversation but never landed in any file. Keyword search for a known direction is feasible; the class "raised but not landed" is open recall, so:

- record the keywords actually swept and what they hit;
- record everything not swept as `Not checked` — same convention as above; an exhaustive-transcript claim is never honest, and the lint cannot verify absence;
- give each entry an original-voice anchor the lint can check: `<source-file> @ <timestamp>` plus a verbatim quote fragment.

## 3. Evidence and precedence

### Facts

Use this practical order:

```text
current direct re-verification
→ first-hand file/tool evidence
→ verified receipt/checkpoint/closeout
→ identified source document
→ relayed report
→ inference
```

A newer statement does not automatically override stronger evidence; resolve the field that actually changed.

### Decisions and authorization

Use:

```text
latest explicit user own-voice instruction
→ active durable user rule
→ earlier user decision
→ model recommendation
```

A recommendation is not adopted merely because it appears in a plan. Execution proves an event occurred; it does not automatically authorize a broader mechanism, future continuation, permission change, privilege escalation, or scope expansion.

### Conflicts

When sources conflict:

1. name the conflicting claims;
2. identify dates, roles, and evidence strength;
3. resolve only when the stronger/current source is clear;
4. otherwise mark the exact field unknown or HOLD the affected high-risk action;
5. do not discard the entire handoff because one bounded detail is unresolved.

## 4. The six dimensions in practice

### Summary

Capture the session's meaningful arc:

- initial problem;
- important turning points;
- decisive discoveries;
- what was achieved;
- why the session stops or transitions now.

Avoid a message-by-message chronology unless the order itself is essential.

### Technical

Preserve:

- architecture, method, design, or operational route;
- how it evolved and why;
- important alternatives and why they failed or were rejected;
- implementation details needed for continuation;
- tooling, environment, files, versions, paths, commands, commits, and hashes;
- technical debt, limitations, and known residuals.

Technical causality is often more valuable than a short status list.

### State

Distinguish:

- current SOT;
- complete;
- executed;
- verified;
- reported but unverified;
- incomplete;
- blocked;
- deferred;
- superseded or closed;
- unresolved.

Do not flatten different artifact roles. A handoff, SOT, closeout, execution receipt, and proposal may all be valid but serve different purposes.

### Task

Give a practical map:

```text
current task
→ first 1–3 actions
→ expected output/evidence
→ completion condition
→ stop/escalation condition
→ next stage
```

A complex handoff may contain multiple later stages, but the receiver should still know the immediate task and starting order.

### Development

Carry forward:

- promising future research or product directions;
- possible branches and their trigger conditions;
- limits of the current approach;
- unresolved strategic questions;
- capabilities or reusable methods discovered;
- what should be revisited later and why.

Separate “current task” from “future direction” so exploration does not derail execution.

### Facts and evidence

For load-bearing claims, provide:

- source and role;
- path or stable identifier;
- version, commit, hash, receipt, date, or command;
- whether it was directly verified in the producing session;
- why the receiver needs it.

A filename without location, identity, or purpose may not be a usable anchor.

## 5. Receiver-first structure

A strong opening usually answers:

- Project / workstream
- Current node
- What this session completed
- Why the session is transitioning
- Current authoritative state
- Current task for the next session
- First 1–3 actions
- What is allowed / not allowed
- Core files to read or upload

Do not force YAML or protocol vocabulary ahead of this brief.

### Activation and two authority axes

The opening must *activate* the receiver, not merely inform it. Three elements:

- **Cleared first action, stated first.** The single action the receiver may start immediately, with its done- and stop-condition. Tell it to begin, not to wait for the task to be re-specified.
- **Two authority axes, separated.** *Receiver mode* = what the receiver may do right now; *next-gate authorization* = whether the next mutation is approved. A not-yet-authorized next gate must not freeze the receiver when a cleared first action exists.
- **Copyable activation shipped with the handoff.** A document delivered with no activating instruction defaults to passive acknowledgement.
- **Receipt duty carried in the activation.** The opening must tell the receiver to write a separate Receiver Outcome Receipt when its first work cycle ends or stops, and name the destination. The receiving session reads the handoff, never this file, so a duty recorded only here does not cross the session boundary — the same failure class as a ruling that never reached the next session.

Regression anchor that motivates this (keep as a test case, not prose to repeat): a heavy, precise handoff opened with `authority: HOLD` plus reconstructed/relayed caution flags and buried its one authorized read-only action in the middle. The single-axis HOLD was read as "the receiver is on hold," so the receiver replied "received; please give me the task" and executed nothing. The fix is the two axes plus an action-first opening — the read-only action could have run immediately while the next mutation stayed user-gated. Fixture: `tests/fixtures/receiver-freeze-fail.md`.

For a file-persisted workstream, point the brief at the persistent SOT/charter file for global objective, milestones, and accumulated value, and note where this session's value appends. Point to it; do not inline the ledger.

After the opening, use the task's natural structure. The outline in `assets/handoff-outline.md` is a menu, not a form.

## 6. Compression without amnesia

First restore, then compress.

Keep a detail when removing it would materially increase the chance of:

- misunderstanding the current node;
- losing technical causality;
- repeating completed work;
- reviving a failed or closed route;
- crossing a user boundary;
- being unable to locate evidence;
- asking the user for known information;
- losing a valuable development direction.

Remove:

- repeated discussion;
- raw logs already represented by a result and anchor;
- obsolete detail with no future effect;
- unrelated project history;
- rhetorical debate after a decision is settled.

For long workstreams, separate a concise receiver brief from deeper technical and evidence sections instead of deleting the deeper content.

### Delta-first (anti-bloat)

The failure this addresses is real and observed: a handoff used as a per-step archive grows into a permanent ledger, and the receiver drowns in unchanged history.

Lead by default with:

- the current node;
- what changed since the predecessor;
- the technical causality that changes the next action;
- current authority and authorization boundaries;
- current evidence gaps;
- the unique pointers needed to receive the work.

Do **not** restate in full by default:

- an unchanged global mission;
- the complete unchanged route;
- detailed history of closed nodes;
- settled role rules;
- long explanations of the same governing source;
- a full evidence table that already exists uniquely in an accessible source.

Re-expand unchanged content only when it is indispensable to the first work cycle, an authority judgement, or risk control. Do not impose a universal hard line or token cap across projects — the test is necessity, not length.

### Revalidation boundary

For long projects or repeat-audit risk, say explicitly what needs fresh verification now (`REVALIDATE_NOW`), what is inherited as accepted within this task's scope (`CARRY_FORWARD_AS_ACCEPTED`), and what must not be reopened absent a trigger (`DO_NOT_REOPEN_UNLESS_TRIGGERED`, with its `REOPEN_TRIGGERS`).

`CARRY_FORWARD_AS_ACCEPTED` never means "permanently unquestionable" or "still a fresh live fact". Typical reopen triggers: identity/SHA mismatch, an updated user decision, new conflicting evidence, expired live state, more than one current SOT, or the current task genuinely depending on that object. The boundary must never block verification that new evidence or stronger authority demands.

## 7. Role adaptation

Preserve one factual base, then adapt the entry contract.

- **Planner:** emphasize state, technical reasoning, open problems, and next-session synthesis.
- **Reviewer:** emphasize review object, authority, evidence package, unresolved rulings, and required verdict.
- **Executor:** emphasize repository/work-root, exact files, current implementation state, allowed mutation, checks, and required receipts.
- **Research agent:** emphasize research question, existing findings, source boundaries, gaps, and expected synthesis.

Do not give an executor a reviewer-only handoff or reuse a model-specific opening without adaptation.

## 8. Upload and source manifest

When files matter, divide them into:

1. **Required** — the receiver cannot correctly start without them.
2. **As needed** — useful for deeper verification or later stages.
3. **Do not upload / superseded** — stale, duplicative, sensitive, or likely to re-anchor the receiver incorrectly.

Explain the purpose of each required item.

## 9. Conditional high-risk continuity appendix

Add this only when the next work involves deletion, permissions, production, accounts, payments, secrets, security, irreversible mutation, or a controlled mutable chain.

Cover:

- original user-authorized scope;
- exact operational scope already executed;
- remaining scope and blocker;
- new authorization not granted;
- affected-set universes;
- protected objects and restore/rollback duties;
- required executor/session/work-root or attempt order;
- parallel-writer prohibition or handover requirements;
- evidence conflict and HOLD conditions.

This appendix is a safety layer. It must not consume the entire handoff or replace the technical and task narrative.

## 10. Receiver-readiness review

Before delivery, test the artifact as if the receiver has no conversation history.

Can the receiver answer:

1. What is this project and node?
2. What happened and why?
3. What is the current technical route?
4. What is the current authoritative state?
5. Which statements are facts, decisions, execution, verification, inference, or unknown?
6. What files or sources are required and where are they?
7. What should be done first, second, and third?
8. What work is already complete or closed?
9. What must not be repeated or revived?
10. What are the meaningful future directions?
11. What would require a user decision or HOLD?
12. Can work start without asking for information already present?
13. Are load-bearing claims supported *in place* (AX-1), not only by an isolated evidence appendix?
14. Are user matters separated into ADJUDICATED / AUTHORIZED / NOT_AUTHORIZED / REJECTED (AX-2)?
15. Are the current receiver mode and next-gate authorization both stated, and kept separate?
16. Is the cleared first action at the front, with done- and stop-conditions?
17. Is a copyable activation opening shipped with the handoff?
17a. Does that opening instruct the receiver to write a Receiver Outcome Receipt, and name where it goes?
18. Is the actual retrieval scope — and the inaccessible scope — stated honestly?
19. Are secrets, tokens, cookies, passwords, and sensitive identity material absent?
20. Is the handoff *operationally* self-contained — can the receiver start without the user restating anything?
21. Is deeper evidence loaded on demand via unique resolvable pointers rather than copied indiscriminately?
22. If a predecessor exists, is the real delta, authority change, and supersession stated first?
23. Are unchanged mission, full route, closed-node history, and settled role rules kept out of the restatement?

If not, revise the content, not merely the formatting.
