# Progress-axis readout (`scripts/handoff_readout.py`)

Read this when you paste the readout into a handoff for the first time, when a line in the block surprises you, or
when you register a new lesson pattern. You do not need it for routine handoffs.

## Running it

```text
python3 $SKILL_ROOT/scripts/handoff_readout.py --session <this window's transcript .jsonl> --handoff <this handoff's absolute path>
```

- Run it **after the last edit** to the handoff, then paste the output verbatim under one line
  `PROGRESS_AXIS=handoff_readout output (verbatim)`. Fences around or inside the pasted block are fine.
- `--session auto` searches transcript roots for the session that wrote the handoff. A plain install has no roots
  configured, so pass `--session <path>` or set `HANDOFF_TRANSCRIPT_ROOT` (one or more directories, `os.pathsep`-separated,
  each holding `*/*.jsonl`). Without either, `auto` exits 2 with an explicit message — it never guesses.
- Only the transcript format the script parses is supported (one JSON record per line: assistant `tool_use`, user, and
  `attachment` records); a transcript without such records prints `UNSUPPORTED` on the snapshot line.
- The last line, `READOUT_RECOMPUTE`, is the exact command a third party runs to get byte-identical output.

## What each line means

| Line | Meaning | Use |
|---|---|---|
| `READOUT_SNAPSHOT` | transcript path, line count `n`, sha256 of those `n` lines, last timestamp inside them, `tool=` sha12 of the readout and of the pattern table | proves which input and which instrument produced the block |
| `READOUT_PATTERNS` (two lines) | per registered lesson: violations / opportunities in this window, and the same summed over the previous five windows | a lesson that goes from 0 to >0 is the one the next window should restate |
| `READOUT_E3` | `E3b` = lessons with zero violations in this and the previous four windows **and** at least 20 opportunities over those five; lessons below that floor are counted as `未测` (untested), not as zero | never read as "mechanism in place" |
| `READOUT_RECEIVE` | whether the window's first three tool calls touched / read the body of the handoff it received | guardrail |
| `READOUT_HUMAN` | whether the user asked for a window switch; how many user messages restated something already said | report only |
| `READOUT_COST` | share of output tokens spent in the handoff-writing segment; tool calls in it | guardrail |
| `READOUT_SIZE` | characters of the handoff, its opening prompt and its evolution kernel (pasted block excluded); `text_sha` of that text | guardrail; `lint` warns when the pasted `text_sha` no longer matches the file |

If the pattern table fails its validity check (detector sha or canary mismatch) the two pattern lines and the E3 line
say `未过效度门` and print no numbers. An install whose table is empty says `无登记模式`; every other line still prints.

## Lesson patterns (`scripts/lesson_patterns.py`, `scripts/lesson_detectors.py`)

A pattern turns one recurring lesson into a count. Two kinds of detector exist:

- **command detectors** `detect(cmd) -> (opportunities, violations)` read one main-line Bash command;
- **window detectors** `detect(window) -> (opportunities, violations)` read what the host recorded, not what the
  command said. The shipped one, `cwd_escape`, counts host `environment` records whose new working directory is neither
  the session's start directory nor under a temp root. A host that writes no `environment` records yields 0 opportunities
  (untested), not 0 violations.

Each row of `PATTERNS` carries: `id` (detector name) · `short` (label in the block) · `lesson` (the rule in words) ·
`opportunity` (the denominator) · `unit` · `canary` (≥3 expected-violation and ≥3 expected-clean cases; window
detectors take `{"start": dir, "moves": [dir, …]}`) · `pos_control` / `neg_control` (a real window with >0 and one with
0) · `self_reports` / `self_report_missed`. `DETECTOR_SHA` pins the detector file; the readout re-checks it and the
canaries on every run.

Registering or changing a pattern (the row and its detector are frozen during a measurement period; change = new id):

1. Write the detector and canaries; every canary must hold.
2. Run it over a frozen corpus of real transcripts: there must be a positive-control window (>0) and a
   negative-control window (0 with opportunities).
3. Self-report check: every handoff whose "what the writer got wrong" section names this lesson must show ≥1
   violation in the writing session. For a window detector a zero there is only excused when an independent
   witness shows the described action had no effect; otherwise it is a miss.
4. Any failure ⇒ the pattern does not ship. Record the gate output and pin the detector sha in the table.
