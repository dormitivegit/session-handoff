# Window altitude and method increment — detail

> 本文件是 `SKILL.md` 两节的细则面。lint 覆盖这两节的**字段与形态**，**不覆盖语义**：
> 产生、修改、消费方法增量时必须读本文件 §2。`CLEAN` 不是质量裁决。字段骨架与触发条件仍在 `SKILL.md`。

### Window altitude, landed assets, and unlanded directions (candidate, advisory)

For a dual-channel / multi-window workstream handoff — scope signal: the handoff itself carries dual-channel or altitude semantics — the contract adds three field families. The window-altitude protocol is a candidate (non-clause): for in-scope handoffs these are template fields, and the lint checks them at **WARN tier only** (never ERROR). The re-discussion trigger is bound to events, not a calendar: when the protocol reaches its **3rd independent empirical** and its **§1 channel-count correction** has landed, re-adjudicate whether these rules may rise to the ERROR tier. Until then WARN is the ceiling.

**Window altitude — fill at window closure; a round missing them is recorded as not closed** (definitions verbatim from the window-altitude protocol):

```text
L_CARRY        本窗口收口时抵达的层级（L0–L3）
L2_MECHANISMS  本窗口已自主形成的 L2 机制清单（一行一条，可回锚）
NEXT_FLOOR     下一窗口的**起步下限**——新窗口不得在此级以下重新论证
```

- **Anchor syntax** — the only machine-resolvable forms; a bare semantic event id such as `E5`, `A6b`, `M1` carries no path and does not resolve. Each `L2_MECHANISMS` entry line ends with either `<path>#<markdown heading>` or `<path>:<line-number>`, where `<path>` is absolute, relative to this handoff file, or `$SKILL_ROOT/`-rooted (resolved to this skill's own directory), the heading occurs in that file as a Markdown heading, and the line number is within the file. Example: `$SKILL_ROOT/assets/handoff-outline.md#Continuity Kernel`.
- The lint validates anchor **resolvability**, never anchor **truth**: `L_CARRY=L3` with empty or fabricated mechanisms that lint cannot expose stays a residual risk — record it, never claim it closed.
- Cross-window progress, verbatim from the window-altitude protocol:

```text
进度 = L_CARRY(n+1) > L_CARRY(n)
相等 ⇒ 该窗口**原地踏步**，如实登记，不粉饰为「巩固」「夯实」。
低于 NEXT_FLOOR 的产出，除非**推翻**了那一级的结论，否则记为**回退轮**。
```

**Saturation.** `L_CARRY` is a closed set ending at `L3`, so the test above stops
discriminating the moment a line reaches the top: from then on it reads `相等 ⇒ 原地踏步`
for every window, including windows that solved something the line had never been able to
solve. This is not hypothetical — seven consecutive window handoffs on one workstream all
carried `L_CARRY=L3`. The lint reports saturation (`L_CARRY=NEXT_FLOOR=L3`) at WARN tier.

Reaching the ceiling may itself be the achievement; the defect is citing a saturated axis as
progress evidence. When saturated, report progress on an axis that still discriminates —
which class of problem became solvable, which methods composed, which prior conclusion was
overturned — or state plainly that the window held position. Do **not** invent `L4`: adding
levels postpones the same failure one window at a time, and the level numbers belong to the window-altitude
protocol, not to this contract, so this skill may not redefine them.

**Landed protocols index** — what the system has **already built**. Distinct from `CURRENT_AUTHORITATIVE_STATE_OR_SOT`, which carries the current authoritative **state**: this field carries the protocols, mechanisms, and task roots that exist, each with a pointer and a when-to-read trigger. It must be bound to a **mechanical enumeration source** — the motivating failure is the author not knowing an asset exists, and a recall-only list cannot list what the author does not know exists (named `LANDED_PROTOCOLS_INDEX` to avoid colliding with the asset-library `ASSET_INDEX` family):

```text
LANDED_PROTOCOLS_INDEX=
  [enumerated] lines from the mechanical source — e.g. `ls <workstream-root>/00_SOT/`;
               for system-level protocols, the reading guide of the cross-workstream knowledge base
               (structural anchor: that guide's own entry heading)
  [manual] lines the enumeration cannot see yet, each with a reason
```

Keep `[enumerated]` and `[manual]` separately labeled. Point, do not dump: path + when-to-read, progressive disclosure.

**Unlanded directions** — directions **raised but never landed** in any file. Distinct from *Development directions*: a development direction is forward-looking; an unlanded direction was already said, never reached disk, and carries an **original-voice anchor** (`<source-file> @ <YYYY-MM-DD[THH:MM[:SS]]>` plus a verbatim quote fragment). A non-anchored future idea belongs in Development, not here.

```text
UNLANDED_DIRECTIONS=
  - <direction one-liner> — <source-file> @ <timestamp> — quote: "<verbatim fragment>"
  Checked: <what was actually searched — the current window's transcript, the keywords used>
  Not checked: <the unindexed or unsearched remainder>
```

- The judgment surface **must include the current window's session transcript**: at closure, search this window's transcript (not all history) for directions raised but not landed — the step is in `references/handoff-method.md` §2.
- `NONE` is legal only together with the Checked / Not checked record; a bare `NONE` is a silent disclaimer, and the lint warns on it.
- Open-recall honesty: "raised but not landed" has no closed keyword set. Never claim an exhaustive transcript sweep — the lint cannot verify absence, and neither may the author claim it.

## Method increment and cross-window self-evolution

For a multi-window line, a handoff that transfers conclusions but not **method** forces the next window to rediscover how the work should be done — typically by being corrected, or by an external audit finding the same thing again. Carry a short method increment beside the altitude fields.

```text
METHOD_INCREMENT=
  A 本窗新立的常设裁定（每条：原话 + 原则级抽象（不只写落地实例）+ 机械判据 + 怎么用 + 原声锚 `<会话记录> @ <时间>`）
  B 本窗**验证有效**的工作法（每条是一个可直接复用的动作序列，不是原则）
  C 本窗**证明无效或不足**的做法（负向；写清它失败在哪一步；同类错第 2 次出现时写**类级**修法 ——
    唯一定义 · 登记 × 形态 · 结构守卫 · 翻色对照；一条证伪读数只锁住已知实例）
```

- **A is not a rules dump.** Only rulings that are standing (they govern later windows), each with the criterion that makes it mechanically applicable. A ruling with no criterion is a slogan and does not belong here.
- **B must be an action sequence, not a principle.** "Verify before claiming" is a principle and is already elsewhere; "hand-compute the baseline first, then diff it against the checker's output — if they disagree one of them is wrong" is an action sequence. If the receiver cannot execute the line as written, rewrite it.
- **C is where the compounding actually is.** A method proven ineffective this window costs the next window nothing only if it is written down. State the step at which it failed, not merely that it failed.
- **Distinguish this from `L2_MECHANISMS` and from the producer error model.** `L2_MECHANISMS` carries *what is true about the system*; the producer error model carries *this producer's individual defects*; this section carries *how to work on this line*. Overlap is acceptable; collapsing them is not — they are consumed at different moments.
- **Inheritance is explicit and directional.** *(Mechanized —
  `method_recursion_rule`: the entry prefixes 新增 / 继承 / 退役 already **are** the
  relationship type, so no new field was added. The rule **records** the prefix distribution
  and whether an explicit by-reference pointer is present; it does **not** adjudicate whether
  inheritance actually happened or whether capability rose. A predecessor-declaring handoff
  whose entries are 100% 新增 and which carries no explicit pointer gets a *please check by
  hand* prompt — not a verdict of "restarted from zero".

  MEASURES the prefix distribution only; whether an inheritance is correct or a retirement
  justified still needs a reader.)* The receiving window starts from the previous increment: it may extend, correct, or retire entries, but it may not silently restart the method from zero. Where an entry is retired, say which evidence retired it.
- **Falsifiability.** The section's own criterion: *if the next window still needs the user or an external audit to surface something this section already states, the section failed for that item.* Record such a failure in the receipt's `OBSERVED_FAILURE_OR_GAIN` — that is the section's only feedback channel, and without it the section degrades into another write-only artifact.
- **Concretization is what makes this section evolve — and it is measured by carrier state,
  not by entry count and not by the word "carrier" appearing in the text.** An entry that
  names no executable carrier stays text; an entry whose named carrier actually runs fires
  on its own at that carrier's action point, which is the same criterion the workstream
  applies elsewhere (*reachable = embedded in a required action, not the existence of a
  pointer*). **Mechanized**: `scripts/lint_handoff.py`'s `concretization_rate_rule` resolves
  every named carrier against disk and reports one of four states per entry —
  `NONE` (no carrier named) / `MISSING` (named, absent from disk) / `EXISTS` (present) /
  `TEXT_REFERENCED` (present, and its full path appears on a non-comment line of a declared
  action-point surface, only when the host sets `HANDOFF_ACTION_POINTS`). Those tokens are a
  conservative summary of four **independent** facts the rule now reports separately:
  `carrier_resolved` / `carrier_present` / `action_point_match` / `native_event`.
  `MISSING` is the load-bearing one and is the only state this rule can prove: absence is
  mechanically checkable, presence is not proof of firing.
  Document-only anchors are not carriers — a document has no action point of its own.
  **Do not read `EXISTS` as concretized, and do not read an all-text section as failure:**
  local n>=2 measurement puts the effective-consumption rate of text methods at 47%-83%,
  so text is a weaker channel, not an invalid one.
- **Bypass survival is the question that matters — and no state this rule emits answers it.**
  A method entry travels to the next window through the handoff. When the next task does not
  enter through this handoff — a different entry point, a fresh session on another line —
  every `NONE` and `EXISTS` entry becomes invisible. The motivating failure is on record: a
  defect already carried in a predecessor's method column recurred because the new task
  entered by a different door and the column was never read. That question is real and stays.

  So read the tokens as what they are, and read `native_event` as the honest answer:
  `NONE` = text, arrives only if read · `EXISTS` = a carrier exists on disk, arrives only if
  someone runs it · `TEXT_REFERENCED` = its path is written at a declared action point,
  which is stronger evidence of intent but **still not** evidence of registration ·
  `native_event=NOT_OBSERVED` = this host provides no surface on which firing could be seen.
  A line cannot claim bypass survival from this rule at all. It can only report that the
  question is unanswered here, and say which channel it actually relied on.

- **Two channels, and this section is only one of them.** Method knowledge travels on two
  surfaces with different reach, and confusing them is what makes this section look either
  useless or indispensable depending on which experiment you run:

```text
本节（METHOD_INCREMENT）  沿**交接件入口**传递 —— 线内、下一窗、读了本件才拿得到
跨线知识库（+ 派单路由块）  沿**动作点**传递 —— 跨窗、跨线、跨 agent，不读本件也拿得到
```

- **Promotion to the library is criterion-based, not taste-based.** A method entry that is
  reusable beyond this line belongs in the cross-workstream knowledge base, where it becomes
  reachable without this handoff. Nomination needs **两个都要**：一条**候选理由**（四选一），
  外加**库内无等价物的检索结论**（下面的信号一，已降级为候选筛而非证明）。

```text
候选理由（四选一，各自带自己的证据与边界）
  R-a 失败纠正   问题台账有同族复发：≥2 条同形态记录，或 1 条最高级别记录
  R-b 成功方法   一次**可复算**的有效做法：给出复算命令与它当时替代掉的做法
  R-c 组合突破   组合既有方法解决了此前无法解决的问题类别：给出问题类别与前后对照
  R-d 成本下降   显著减少返工/调用/阅读成本：给出前后读数与测量方法

信号一  库内无等价物 —— 用该方法的关键词族检索知识库
        🔴 零命中**只产候选，不构成证明**
```

  两件事相互独立：候选理由说「它值不值得跨线复用」，信号一说「库里是不是已经有了」。
  只有候选理由而库内已有等价 ⇒ 是消费问题不是登记问题，去修可达性，不要再立一条。
  只有信号一（检索不到）而给不出四类理由之一 ⇒ 可能是从未发生过的预防型条目，留在件内即可。
  **晋升由用户裁；检查器与本节只产候选**（AI_LAST）。

- **Anti-bloat.** This section is delta-only. Do not restate inherited entries that did not change; point at the predecessor handoff for them. A method increment that grows monotonically every window is a symptom, not progress.
