---
name: session-handoff
description: Write an evidence-grounded, capability-elevating session handoff (context handoff, 会话交接 / 交接件) that lets a fresh AI agent session inherit the previous session's understanding, technical direction, current state, ongoing task, and future development path — so it does not lose context, re-ask settled questions, repeat corrected mistakes, or act on stale state — and start from a higher baseline because lessons, corrected errors, and methods travel forward as reusable capability. Use at a session boundary, context-pressure point, phase transition, model/agent transfer, or before continuing work in a fresh session. Also use when a workstream keeps persistent status outside the conversation — a status file, SOT, charter, decision log, or task register — and it is ambiguous whether a material state change has to be recorded there.
---

# Session Handoff

<!--
CONTRACT_VERSION = 2.3
CARRIER_VERSION  = 2.4.28
PROGRESS_AXIS_RULE=$SKILL_ROOT/scripts/lint_handoff.py:progress_axis_rule
METHOD_INCREMENT_LANDING=$SKILL_ROOT/scripts/lint_handoff.py:method_increment_landing_rule
RETIREMENT_OBSERVER=$SKILL_ROOT/scripts/lint_handoff.py:concretization_rate_rule
CLAIM_LEDGER =
  COMMITS = 30e9819
-->

A session handoff is a **capability-elevating transfer of understanding and work** — the next window should start higher than this one ended — not a minimal state packet, a chat summary, a fixed form, or an execution authorization.

Its purpose is to let a fresh session inherit enough of the previous session to understand the work, continue it correctly, avoid rediscovery, and preserve valuable future directions.

Write in the user's language unless the user asks otherwise.

## Entry points

Two different situations reach this skill, and they are not the same job:

- **A — a session boundary.** A fresh session, model, agent, or reviewer has to continue this workstream. Produce a handoff: everything below applies.
- **B — a persistent status decision.** A material state change has occurred and it is ambiguous whether the workstream's persistent status has to record it. Go to *Persistent status updates*. B does not require producing a full handoff.

B frequently fires inside A: a session that ends with the persistent status still describing the previous node has already broken the continuity the handoff is trying to preserve. Handle B in its own terms, then return to A.

## Six core dimensions

Every substantial handoff should recover these dimensions in the proportion required by the actual task. They are content lenses, not mandatory headings.

1. **Summary** — what happened, what changed, what was learned, and why the session ended at this point.
2. **Technical** — technical route, architecture or method, iterations, problems found, solutions tried, key implementation details, and reasons for the current approach.
3. **State** — current SOT, completed/executed/verified work, incomplete or unverified work, blockers, decisions, closed routes, and unresolved conflicts.
4. **Task** — what the next session must solve, why it matters now, the first practical steps, required inputs, expected outputs, completion criteria, and stop conditions.
5. **Development** — valuable future directions, open questions, likely next branches, capability or product opportunities, limits of the current approach, and conditions for reopening a closed route.
6. **Facts and evidence** — factual basis, user own-voice decisions, files, paths, versions, hashes, commits, receipts, commands, results, source limits, and explicit unknowns.

Safety, lineage, authorization, and execution continuity protect these dimensions when relevant; they do not replace or dominate them.

## Required outcome

A fresh receiver that sees only the handoff and the explicitly listed materials should be able to:

- explain the project, current node, and why the work reached this state;
- recover the technical route and its important evolution;
- distinguish facts, user decisions, execution, verification, recommendations, inferences, and unknowns;
- explicitly distinguish user matters that are **adjudicated, authorized, not authorized, or rejected**; a handoff missing this authority layer is not receiver-ready;
- know what is complete, what remains, and what must not be repeated or silently revived;
- locate the materials needed to continue;
- start the next session's first work cycle without asking for information already available;
- understand both the immediate task and the meaningful development horizon;
- know, from the brief alone, what it may do right now versus what needs new authorization.

## Operationally self-contained; evidence resolved on demand

`Self-contained` means **operationally startable**, not "everything copied in":

> The handoff must be self-contained enough that the receiver can begin its first work cycle without the user restating background, task, or known boundaries; deeper evidence should load on demand through unique, resolvable SOT or evidence pointers rather than by copying all history, full evidence packages, or every unchanged anchor.

Therefore:

- current node, cleared first action, done/stop conditions, authority boundaries, and required inputs must be present **in** the handoff;
- deeper proof may point to a uniquely accessible file, path, hash, receipt, closeout, or SOT;
- a pointer must be enough to resolve identity, purpose, and verification state;
- never copy the whole history "to be self-contained" and exhaust the receiver's attention;
- never omit facts or boundaries needed to start the first work cycle on the grounds that "evidence can be read on demand".

## Receiver activation and two authority axes

A precise state translation still fails if the receiver stalls (the classic "received; please give me the task" freeze). Encode these three elements in the immediate brief, in the task's own words — not as a rigid schema:

1. **Cleared first action, stated first.** Open with the single action the receiver may run immediately, its done-condition, and its stop-condition. Tell the receiver to begin it, not to wait for the task to be re-specified. A handoff that opens with caution flags trains the receiver to freeze.
2. **Two authority axes, kept separate.**
   - *Receiver mode* — what the receiver is cleared to do right now (`EXECUTE_FIRST_ACTION` | `AWAIT_USER_DECISION`).
   - *Next-gate authorization* — whether the next mutation or stage is authorized (`AUTHORIZED` | `NOT_AUTHORIZED` | `USER_DECISION_REQUIRED`).
   A not-yet-authorized next gate must never freeze the receiver when a cleared first action exists. Collapsing both into a single "HOLD" is the classic receiver-freeze failure.
   These two axes state what the receiver may do right now. They complement — and never replace — the authority record above: which user matters are adjudicated, authorized, not authorized, or rejected. The axes answer "what may I do"; the record answers "what has been decided, and what was rejected".
3. **Ship the activation with the handoff.** For a fresh receiver, or one on a different model or host, include the copyable opening from `assets/handoff-outline.md` that puts it in receiver mode. A document delivered with no activating instruction defaults to passive acknowledgement.
4. **Carry the method-use instruction on the handoff, not in this file.** The receiver reads the
   handoff; it does not necessarily read this skill. So the opening must itself say, in one line:
   *before a relevant action, pick one method from the increment (or from a cross-workstream knowledge
   base) that has a source, and judge whether it applies here — refusing an inapplicable method
   is a correct outcome; after acting, record which method, which opportunity, which action, what
   result, and the cost comparison if there is one; if no opportunity arose, write 待复用.*
   Short prose is fine. No new field, no ledger, no database.
   ⚠️ 这是 2.4.11 的短闭环缺的那一半：生成端写了触发点与记法，**接收端没有取用出口** ——
   于是「本窗修正」到不了「下窗动作不同」。修的是出口，不是又加一套机制。
   MEASURES: 该指令在不在开场白里（机械可判）。DOES NOT MEASURE: 接收方有没有真的照做、
   照做了有没有收益 —— 那要看下一窗的回执正文，本 skill 不观测它，也不得由本条推出。

4. **Carry the receipt duty in the activation.** The receiving session reads the handoff, not this skill, so a duty recorded only here never crosses the session boundary. The opening must tell the receiver to write a separate Receiver Outcome Receipt when its first work cycle ends or stops, and must name the destination path. The opening must also ask the receiver to restate one or two load-bearing points of this handoff before it starts, and to record the outcome in the receipt's `OBSERVED_FAILURE_OR_GAIN`: a receiver that cannot restate them has found a defect in this document, not in itself.Without this line the receipt is never written and the contract's own evidence channel is silently dead.

For a file-persisted workstream, the immediate brief may point to a persistent SOT or charter file for the global objective, milestones, and accumulated value, and note where this session's value should be appended. Point to it; do not copy it wholesale, and do not turn the handoff itself into a ledger.

### Continuity Kernel

At the very top of any actionable handoff — before or as the first part of the immediate brief — answer these semantic slots in roughly eight lines:

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

- These are semantic requirements; field names may adapt to the project's language and receiving role.
- A plain summary need not emit key-values mechanically, but a handoff meant to be continued must make these answers visible at a glance.
- `CURRENT_POSITION` compresses the current node, route position, or transition state; it does not establish a second state database.
- Do not introduce a single-valued `SYSTEM_MODE` that overrides receiver mode, action mode, and next-gate authorization.
- If a slot is absent or undeterminable, write `NONE`, `UNKNOWN`, or `CONFLICT` explicitly; never silently autofill.

### Delta from Predecessor

When an identifiable predecessor handoff exists, state the delta first:

```text
PREDECESSOR_HANDOFF_ID=
NEW_SINCE_PREDECESSOR=
AUTHORITY_OR_STATE_CHANGED=
SUPERSEDED_OR_CORRECTED=
UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=
```

- Show the receiver what changed, then let it read unchanged history on demand.
- Reference only a predecessor that is actually accessible and uniquely identified.
- With no predecessor, write `NOT_APPLICABLE`; never fabricate lineage.
- Unchanged load-bearing anchors may be inherited by unique pointer instead of full copy.
- Changes in user rulings, SOT, authorization, task state, or evidence identity must be written out — "everything else unchanged" alone is not enough.

### Revalidation Boundary

For long projects, repeat-audit risk, or an already stable evidence chain, state where re-verification is and is not required:

```text
REVALIDATE_NOW=
CARRY_FORWARD_AS_ACCEPTED=
DO_NOT_REOPEN_UNLESS_TRIGGERED=
REOPEN_TRIGGERS=
```

- `REVALIDATE_NOW` lists only the fresh verification the current first work cycle genuinely needs.
- `CARRY_FORWARD_AS_ACCEPTED` means inherited as accepted **within the current task's scope** — not "never questionable" and not "still a fresh live fact".
- `DO_NOT_REOPEN_UNLESS_TRIGGERED` applies to closed, rejected, or adequately sealed routes.
- Typical reopen triggers: identity/SHA mismatch, an updated user decision, new conflicting evidence, expired live state, more than one current SOT, or the current task genuinely depending on that object.
- When new evidence or stronger authority triggers revalidation, this boundary must never be used to block necessary verification.

### Window altitude, landed assets, and unlanded directions (candidate, advisory)

Scope signal: the handoff itself carries dual-channel or altitude semantics. For those
handoffs the contract adds three field families. The window-altitude protocol is a candidate,
so the lint checks them at **WARN tier only** (never ERROR). The re-discussion trigger is bound
to events, not a calendar: when the protocol reaches its 3rd independent empirical and its
channel-count correction lands, re-adjudicate whether these may rise to ERROR.

```text
L_CARRY         本窗口收口时抵达的层级（L0–L3）
L2_MECHANISMS   本窗口已自主形成的 L2 机制清单（一行一条，每行末尾带可解析锚）
NEXT_FLOOR      下一窗口的**起步下限**——新窗口不得在此级以下重新论证
LANDED_PROTOCOLS_INDEX=   系统**已经建成**什么，绑定到机械枚举源，[enumerated] / [manual] 分标
UNLANDED_DIRECTIONS=      已提出但从未落盘的方向，每条带原声锚 + Checked / Not checked 记录
```

Anchor syntax, the mechanical-enumeration requirement, the honesty record that makes a bare
`NONE` illegal, and the **saturation rule** (`L_CARRY=NEXT_FLOOR=L3` means the protocol's progress
test has stopped discriminating — report progress on an axis that still does) are in
`references/window-altitude-and-method-increment.md` §1.

## Method increment and cross-window self-evolution

For a multi-window line, a handoff that transfers conclusions but not **method** forces the
next window to rediscover how the work should be done — typically by being corrected, or by
an external audit finding the same thing again. Carry a short method increment beside the
altitude fields.

```text
METHOD_INCREMENT=
  A 本窗新立的常设裁定（每条：原话 + 原则级抽象（不只写落地实例）+ 机械判据 + 怎么用 + 原声锚 `<会话记录> @ <时间>`）
  B 本窗**验证有效**的工作法（每条是一个可直接复用的动作序列，不是原则）
  C 本窗**证明无效或不足**的做法（负向；写清它失败在哪一步；同类错第 2 次出现时写**类级**修法 ——
    唯一定义 · 登记 × 形态 · 结构守卫 · 翻色对照；一条证伪读数只锁住已知实例）
```

**本窗内的短闭环 —— 这一节在关窗前就要用，不是关窗时才填。**
上面三栏是**出口**：它把方法交给下一窗。但一个方法真正省下的第一笔成本发生在**本窗** ——
你刚被证伪一次假设、刚被纠正一次方向，而本窗后面还会再遇到同类动作。出口不管那一段。
缺了它的后果已实测：一条方法写进了前窗的方法栏，新任务换了个入口进来，那一栏从没被读过。

```text
触发点（三选一发生即记，不等关窗）
  E1 一个假设被证伪            E2 一次被纠正方向或前提     E3 同一类操作连续失败
记什么（一行，不写成散文）
  触发点 → 当时的做法 → 换成什么做法 → 判据（下次怎么认出该用它）
立即复用
  本窗此后遇到同类动作时，先答「E1/E2/E3 里记过的那条适用吗」。
  用了 ⇒ 在回执的 OBSERVED_FAILURE_OR_GAIN 里写清用在哪一步、结果是什么。
  本窗没再遇到机会 ⇒ 标 **待复用**，不要写成「已验证有效」——
  一次也没再用过的方法，其有效性在本窗是未观测，不是成立。
```

**写这三栏时的七条规则（内联，因为这是它们被用到的那一刻）**

```text
R1 A 不是规则堆 —— 只收**常设**裁定（管得住后面的窗），每条带使它可机械适用的判据。
   没有判据的裁定是口号，不进这一栏。
R2 B 必须是**动作序列**不是原则 ——「先验证再声称」是原则（且已在别处）；
   「先手算基线，再与检查器输出对差，不一致则二者必有一错」是动作序列。
   判据：接收方照着这行**能不能直接执行**；不能就重写。
R3 C 写清它**失败在哪一步**，不是只写失败了 —— 复利在这一栏。
R4 与另两栏分清：`L2_MECHANISMS` 记**系统是什么**；producer error model 记**本起草方的个人缺陷**；
   本节记**这条线该怎么干活**。重叠可以，混成一栏不行 —— 它们在不同时刻被取用。
R5 继承是显式有向的：可扩展 / 纠正 / 退役前任条目，**不得静默从零重启**。
   退役某条时要说**哪条证据**退役了它。
R6 晋升到跨线知识库须**两个都要**：① 候选理由四选一（R-a 失败纠正 / R-b 成功方法 /
   R-c 组合突破 / R-d 成本下降，各自带证据与边界）② 库内无等价物的检索结论。
   🔴 关键词零命中**只产候选、不构成证明**（同义表述/不同粒度/已有通用方法的特例都可能零命中，
   且检索面会被工具静默收窄）。检索覆盖不足记 UNKNOWN，不记「无等价」。晋升由用户裁。
R7 Delta-only：不重述继承来的未变条目，指向前任件即可。
   **逐窗单调增长的方法增量是症状，不是进展。**
```

📖 要**理由**（这七条各自的由来、被撤回过什么、真语料读数）或**要改本节条款本身**时，
读 `references/window-altitude-and-method-increment.md` §2。**这是建议，不是 MUST** ——
按本 skill 自己的规矩，不可机械判定者不得写成 MUST（见上方旁注的由来）。

⚠️ 判据边界：本节**机械不可判**（「有没有在下一个相关动作里正确取用」需要读内容），
故不为它设 WARN —— 按本体系「不可机械判定者不得写成 MUST」。它靠的是上面那条动作点指令，
和回执里那一栏的正文质量。检查器不承诺覆盖它，`CLEAN` 不代表这一节做到了。

Delta-only: do not restate inherited entries that did not change. The column rules, the
carrier-state semantics (`NONE` / `MISSING` / `EXISTS` / `TEXT_REFERENCED`, a conservative
summary of four independent facts — and why **none** of them answers "will the next window
get this method even if it never opens this file"; `WIRED` was retired),
and the section's own falsifiability criterion are in the same reference file, §2.

## Evolution kernel —— 跨窗的积分

`METHOD_INCREMENT` 是**导数**：只写本窗新增，不重述（上文 Delta-only 仍成立）。只有导数的交接链是一串
增量快照 —— 两窗之后，前面的承重内容就掉了。金字塔还要**积分**：一个逐代继承、逐代整合的底座。
（由本 skill 的机制在交接件本体内跨窗实现，不另建库。）

错误转成能力点**按类，不按例**：一条证伪读数只锁住已知实例；同类第 2 次出现时，核里记的应是类级机制
（唯一定义 · 登记 × 形态 · 结构守卫 · 翻色对照），使下一个实例在出现那一刻就翻红。用户的纠偏进核时写**原则**，
不只写这一窗的落地实例，并带原声锚 —— 转述是有损压缩，原则最先丢。

```text
EVOLUTION_KERNEL=
  K1 一条整合过的承重内容（教训 / 由错误转成的能力 / 技术发现 / 协作中形成的常设裁定）
     锚：在盘的机制路径（可带 :标识符）或 一条复算命令 或 一条证伪命令
  K2 …
```

每一代的义务 —— 前三条由 lint 机械判定，第四条尚未实装：

```text
1 带锚准入  每条须有机器可执行或可解析的锚。无锚的内容不进核：核会被此后每一代原样继承，
            一条错的进了核，就按代放大。机制路径须在盘上（悬空指针不算锚）。
2 预算      条数上限见 lint 常量 EVOLUTION_KERNEL_MAX_ITEMS；满了只能先整合或退役，再加。
3 生效地板  文件名日期不早于 lint 常量 EVOLUTION_KERNEL_FLOOR 的交接件须有本段（存量件不追溯）；
            段一旦出现，不论日期都受 1、2 约束。
4 继承可追溯（v2，未实装）前代每条须在本代「保留 / 整合进某条 / 已落成机制而退出」三选一。
            实装前靠写的人自觉 —— CLEAN 不代表这一条做到了。
```

整合优先于追加：同一逻辑的多条合成一条更抽象的；已落成代码机制的条目**退出核**（它活在机制里了，
再留在文本里就是重复）。判据实现：
$SKILL_ROOT/scripts/lint_handoff.py:evolution_kernel_rule

## Workflow

1. **Lock the workstream.** Identify the exact project, task line, current node, intended receiver, and reason for the session transition. Do not mix adjacent projects merely because they are recent or important.
2. **Recover before writing.** Read the currently visible conversation and, when accessible, same-workstream history, uploads, handoffs, checkpoints, closeouts, receipts, tool results, and user rulings. Record only the scope actually checked. Never claim account-wide or exhaustive retrieval unless it truly occurred.
3. **Identify the predecessor and the current delta.** If a predecessor handoff exists, verify its identity and workstream, compare current SOT / user authority / task state / technical route / key evidence, extract what actually changed, and decide which unchanged content only needs a pointer. If the predecessor cannot be uniquely identified, mark `UNKNOWN / CONFLICT`; never treat a similarly named document as lineage. With no predecessor, recover normally and do not manufacture a fake delta.
4. **Reconcile authority and time.** Prefer current re-verification and first-hand evidence for facts; prefer the latest explicit user instruction for decisions. Do not turn a model recommendation into user adoption, an execution event into broader authorization, or a report into independent verification.
5. **Reconstruct the story of the work.** Identify the original problem, important iterations, discoveries, failed approaches, decisions, current route, and why the present node exists. Preserve technical causality that prevents rediscovery.
6. **Synthesize through the six dimensions.** First restore the complete useful picture; then remove repetition, raw-log noise, obsolete detail, and unrelated history. Do not begin with a word budget or fixed schema.
7. **Write delta-first to prevent bloat.** By default lead with: the current node; what changed since the predecessor; the technical causality that changes the next action; current authority and authorization boundaries; current evidence gaps; and the unique pointers needed to receive the work. By default do **not** restate in full: an unchanged mission, the complete unchanged route, detailed history of closed nodes, settled role rules, long explanations of the same governing source, or a full evidence table that already exists uniquely in an accessible source. Re-expand unchanged content only when it is indispensable to the first work cycle, an authority judgement, or risk control. Do not impose a universal hard line/token cap across projects.
8. **Write receiver-first.** Open with the Continuity Kernel and a compact immediate brief that tells the receiver where it is, what happened, what the current task is, what to read, and how to begin. State the single cleared first action and the receiver's current mode (see *Receiver activation and two authority axes*). Put metadata and risk detail later unless the user explicitly wants them first.
9. **Provide an execution map, not an isolated ticket.** State one current task, the first 1–3 ordered actions, expected outputs, completion/stop conditions, and the next stage or branch that follows. Keep the receiver's cleared first action distinct from the next-gate authorization.
10. **Ground facts and evidence.** Make important claims traceable. Give resolvable paths, identities, commands, receipts, or source descriptions when available. State unavailable or unverified items explicitly instead of inventing them.
11. **Add conditional controls only when triggered.** For deletion, permissions, production, accounts, payment, secrets, security, or other irreversible work, add the high-risk continuity appendix from `references/handoff-method.md`.
12. **Perform a receiver review.** Use `assets/handoff-outline.md` as an adaptive checklist and ask whether a new agent can understand, continue, and develop the work. The optional lint script checks only mechanical hazards; it is not a quality verdict.
13. **Deliver the finished handoff.** When file output is supported, provide the file and SHA256, and mark version and status clearly. Do not execute the handoff's next task unless the user separately asks for execution.

## Writing principles

- “Complete” means enough to preserve understanding, technical causality, current state, task continuity, and future direction. It does not mean copying the full transcript.
- “Concise” means removing duplication and irrelevant detail. It does not mean deleting context that would force rediscovery.
- Use natural, task-specific structure. Omit irrelevant sections; never fill a template with “none” merely for compliance.
- Prefer a clear current task plus ordered immediate steps over “exactly one isolated action.”
- Preserve the user's terminology, priorities, constraints, and own-voice decisions.
- Separate the hot receiver brief from deeper evidence and background so both fast entry and full inheritance are possible.
- Adapt the opening and expected output to the receiving role (for example a planner, reviewer, executor, or research agent) while preserving the same factual base.
- A handoff must be self-contained enough to use without the producer Skill, hidden memory, or private reasoning; `self-contained` means operationally startable, with deeper evidence loaded on demand through unique resolvable pointers.
- With a predecessor, default to delta-first: write the changes, then reference unchanged anchors. Without one, do not invent lineage.
- Compression must never remove the current node, load-bearing causality, user authority, evidence gaps, or materials required for the first work cycle.
- Do not treat word count, section count, mechanical lint passage, or formal symmetry as proof of quality.

## Facts and evidence discipline

Facts and evidence are a cross-cutting property of load-bearing claims in every dimension. Attach a resolvable source, identity, and verification state where needed; do not satisfy this discipline by creating a separate evidence section while leaving material claims in the main narrative unsupported.

Distinguish volatile assertions from sealed ones. For an object whose value can change after this handoff is written — an authority-head revision, a gate or acceptance state, a count, a version, a pending external input — do not write the value. Write the object's nature, a resolvable entry point, and the command the receiver runs to read it at consumption time. If that command fails, or returns something this handoff does not account for, treat it as a defect in this handoff and record it in the receipt's `OBSERVED_FAILURE_OR_GAIN`. This includes the pass count of a live check (an acceptance or test reading such as N/M): write the command that produces the reading, not the reading. No rule flags a bare fraction — it cannot be told apart from a sealed historical citation — so this one rests on the producer.

Sealed objects — a frozen hash, a closed route, an archived receipt — are exempt: carry their values directly under `CARRY_FORWARD_AS_ACCEPTED`.

Never write a bare count. Give every count its universe and its carrier: `N (universe: X; carrier: Y)`. A count whose universe is unstated cannot be recomputed, and a claim that cannot be recomputed cannot be falsified.

When a predecessor chain carries assertions forward by reference, rebase from the authoritative sources instead of inheriting on any of: a predecessor anchor that fails re-verification; a source or carrier migration; a change in authority; conflicting current evidence; or the current task depending on an inherited claim. Do not set a fixed rebase period.

Use explicit wording where ambiguity matters:

- **Confirmed fact** — supported by current or identified evidence.
- **User decision / authorization** — explicitly stated or clearly adopted by the user.
- **Executed** — an action occurred; name its exact scope and evidence.
- **Verified** — independently or directly checked; name how.
- **Reported** — relayed by a model, tool, person, or document but not independently rechecked here.
- **Inference / working assumption** — useful reasoning that still needs confirmation.
- **Unknown / missing** — unavailable, conflicting, or not checked.
- **Not authorized** — the action or next gate has no user authorization.
- **Rejected** — the user vetoed it; it must not be silently restarted.

For every material count or set, state its universe when confusion is possible. A tracked subset must not be presented as the complete governing set.

## Negative orientation and producer error model

For a multi-round line, carry two short columns the receiver would otherwise have to discover by being wrong. Omit both for a one-off handoff.

- **What you would otherwise wrongly believe.** Write only priors a reasonable receiver would actually form from what it can see — a file name, a version number, an adjacent project, an inherited memory. Do not catalogue imagined misunderstandings. Give each prior a way to check it: *if you doubt this, verify X*.
- **Where this producer was wrong.** The defects this session's producer committed and what each cost downstream. Keep defects and upgrades apart: a reviewer raising your output a level is the chain working, not a defect. Merging the two corrupts the record of where the blind spots actually are.

## Decision and authorization precedence

```text
latest explicit user own-voice instruction
→ active durable user rule
→ earlier user decision
→ model recommendation
```

**Safety-red-line note:** this precedence chain governs *ordinary* decisions only. It does not override the safety red lines in the host's global instruction files (secrets, privilege escalation, production destruction, data deletion, irreversible version-control operations). A later user instruction still requires the second confirmation those red lines mandate.

## Receiver Outcome Receipt

This receipt is **not** embedded in the handoff the producer writes, and the producer's self-assessment cannot substitute for it. It is generated as a separate lightweight record after a new session has actually used the handoff and completed or stopped its first work cycle:

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

- The receipt evaluates actual receiving behaviour; it does not re-summarize the project.
- `AUTHORITY_DRIFT=YES` covers historical authorization spilling into new scope, a recommendation treated as a ruling, or a next gate executed without approval.
- `UNNECESSARY_REVALIDATION=YES` means re-verifying stable facts with no trigger — not verification required by new evidence, live-state expiry, or SOT conflict.
- A receipt must never retroactively edit the handoff, approve a mutation, or override user authority.
- While v2.3 is a candidate, preserve receipts where possible. A missing receipt is an evidence gap for version evaluation; it does not by itself fail an individual handoff.

Receipts are an input, not an archive. When an iteration window on this skill opens, read the whole standing set of receipts in one pass and admit a finding as a change candidate only if it recurs independently at least twice, or is a single critical failure. Do not create a register for this: the receipts and the workstream's existing status surface are the record. If three consecutive iteration windows yield no actionable finding, reassess whether the receipt itself is worth producing.

**Delivery.** A receipt that nobody is instructed to write does not get written. The duty must be stated in the handoff's copyable opening, with a concrete destination — see item 4 under *Receiver activation and two authority axes*. Default destination for a file-persisted workstream: a `receipts/` directory beside that workstream's SOT, one file per receipt, named for the handoff it evaluates. The producer names the actual path; do not leave it implicit.

## HOLD rules

HOLD only the action or field that genuinely cannot proceed safely — for example a non-unique critical SOT, unresolvable conflicting load-bearing evidence, an inaccessible required file, a high-risk action lacking explicit authorization, unclear scope or restore duties, or broken executor continuity that risks double-writes.

Do not reduce an entire handoff to one global HOLD. When a read-only or already-authorized first action still exists:

```text
Receiver mode = EXECUTE_FIRST_ACTION
Next-gate authorization = NOT_AUTHORIZED | USER_DECISION_REQUIRED
```

Run the first action, then stop at the real gate.

### Reporting vs adjudicating a governance HOLD

Entering a HOLD and releasing one are different authorities, and a receiver must keep them separate.

- Any receiver — including an execution agent — may detect, report, or enter a HOLD when blocking evidence, an authority conflict, or a missing authorization stops continuation. Reporting a HOLD is honest state transfer, not receiver failure, and must not be suppressed to look unblocked.
- A **governance HOLD** — one raised over authority, user policy, or execution authorization rather than a purely technical fix — is not self-released by the agent that reported it. Releasing one is an adjudication:
  - technical and architectural adjudication of the HOLD belongs to the architecture role;
  - final authority over user decisions, policy choices, and execution authorization remains with the user;
  - the reporting agent resumes only when the adjudicated outcome reaches it through the handoff or the workstream's persistent status; a self-declared "resolved" carries no authority.
- State the HOLD through the fields this contract already defines: the HOLD reason, the blocking evidence, the adjudication awaited, the adjudication authority, the next gate (`NEXT_GATE`), its authorization state (`NEXT_GATE_AUTHORIZATION`), and any action still cleared to run now (`CLEARED_FIRST_ACTION`, receiver mode). No new schema, tracker, or recovery structure is introduced — an unadjudicated governance HOLD is reported, never worked around.

## Persistent status updates

Some workstreams keep status outside the conversation — a status file, SOT, charter, decision log, task register, or ticket. This section answers one question: **does the change that just happened have to be written there?** It does not make this skill the owner of that status, does not require a project to keep one, and prescribes no filename, directory, format, or commit policy.

It applies when all three hold:

1. a material persistent project or workstream state change has occurred;
2. downstream continuity — a later session, another agent, or the user — depends on that change being recorded rather than remembered;
3. whether to record it is genuinely ambiguous.

**Under that ambiguity, prefer an explicit update over silent omission.** The asymmetry is the whole reason for the bias: an unrecorded change leaves a stale status that the next receiver will read as current, while an unnecessary update costs a few lines. Ambiguity means "it is unclear whether this belongs in the record" — not "no persistent status exists" and not "the user did not ask".

Usually material — record it:

- the current node, phase, active task, or owner changed;
- work became blocked, unblocked, or was abandoned;
- the next action or the entry point a fresh session should start from changed;
- an authority state changed: newly adjudicated, authorized, not authorized, or rejected;
- the current authoritative source itself moved, split, or was superseded;
- something the status currently asserts is now wrong, stale, or no longer unique.

Usually not material — do not manufacture an update:

- wording, formatting, or typo repair;
- read-only inspection, diagnosis, or review that changed no state;
- routine steps inside an already-recorded task that did not move it;
- exploratory or proposed work the user has not adopted.

When an update is warranted, do it in the project's own terms:

- resolve the project's current status/authority source first; if more than one claims to be current, or none can be identified, treat that as the HOLD condition it is and let the user resolve it rather than guessing a target;
- read the current content before writing, and fold the change into the existing structure — never append a duplicate record or start a second one;
- write only the delta and its consequence for the next action; the record is not a session log;
- keep the same evidence discipline as the rest of this skill: executed, verified, reported, decided, inferred, and unknown stay distinguishable;
- if the current task's write surface does not cover that file, or the update needs authorization the task does not have, state the update that is needed and hand the decision back instead of silently widening scope.

An update records what happened. It never grants authorization, closes a gate, or substitutes for the verification the change itself required.

## Advisory lint

When scripts are available, run:

```bash
python3 scripts/lint_handoff.py <handoff.md>
```

Three output tiers, and they do not mean the same thing:

- `ERROR` — a hazard: an exposed secret, an unresolved placeholder that is an action rather
  than a mention. Repair before delivering.
- `WARN` — mechanically decidable defects (unresolvable anchors, bare counts of live object
  sets, a named carrier absent from disk, a value outside a closed enum) plus three
  retained heuristics whose firing rate carries information. Read each one.
- `HINT` — keyword heuristics for the six dimensions and the kernel signals. These are
  prompts for human/model review. A hint is not a defect, and an absent hint is not a pass.

Nothing here is a quality verdict. **It must not depend on anyone remembering to run it:**
the host calls `lint()` once at session end against the handoffs that session wrote, and a
paused guard still leaves a trace, so "paused" and "wrote no handoff" never look the same.

Execution, delivery and adoption are three independent facts; register per tier only what was
measured on the host in use. A model and its host are two layers — measure by host, not by
model name. The design assumes the receiver has a filesystem: on a host without one,
pointer-style inheritance fails silently (a pointer simply does not resolve), so inline the
load-bearing content there.

```

Because the host calls `lint()` rather than importing individual rules, any mechanical rule
added later is **executed** the moment it lands — no edit to the hook, no second copy of the
criterion. Whether its output **reaches** anyone is a separate question, answered per tier by
measurement on that host. Retirement of that arrangement: if the Stop channel is ever observed to fire
on a file the producer had already fixed, or to stay silent on a file lint flags when run by
hand, the single-call design is unsound and reverts to per-rule selection.

## Exclusions

Do not turn this Skill into a project-management system, permanent memory database, governance platform, fixed state machine, mandatory ledger, background monitor, or universal rigid schema.

Do not optimize for validator passage, minimum character count, or formal symmetry at the expense of receiver understanding and task continuity.

Never, in a handoff: invent paths, hashes, dates, commands, results, or verifications; expose secrets; describe inaccessible history as checked; record an unadopted recommendation as a decision; reintroduce a rejected route in new packaging; freeze an already-cleared read-only first action because the next mutation is unauthorized; or auto-execute the handoff's next task.
