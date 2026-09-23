#!/usr/bin/env python3

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CARRIER_VERSION = "2.4.27"

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT_TOKEN = "$SKILL_ROOT"
PATH_ROOT_ALT = r"(?:\$SKILL_ROOT/|~/|/)"


def resolve_path_token(raw: str, base_dir: "Path | None" = None) -> Path:
    if raw.startswith(SKILL_ROOT_TOKEN + "/"):
        return SKILL_ROOT / raw[len(SKILL_ROOT_TOKEN) + 1:]
    p = Path(raw).expanduser()
    if p.is_absolute() or base_dir is None:
        return p
    return base_dir / p

PLACEHOLDER_PATTERNS: list[tuple[str, str]] = [
    ("angle-slot", r"<[^>\n]{1,120}>"),
    ("marker-TBD", r"\bTBD\b"),
    ("marker-TODO", r"\bTODO\b"),
    ("marker-FIXME", r"\bFIXME\b"),
    ("marker-待补", r"待补"),
    ("noun-占位", r"占位"),
]
MARKER_PATTERN_IDS = {"marker-TBD", "marker-TODO", "marker-FIXME", "marker-待补"}
NOUN_PATTERN_IDS = {"noun-占位"}

PHENOMENON_NOUN_RE = re.compile(r"占位符|占位|placeholder|TBD|TODO|FIXME|待补", re.IGNORECASE)
DISCUSSION_VERB_RE = re.compile(
    r"残留|不得|未替换|检查|登记|leftover|residual|unresolved|do\s+not|must\s+not"
    r"|should\s+not|check|register",
    re.IGNORECASE,
)
VALUE_POSITION_LEFT_RE = re.compile(r"[=:\[【（(]\s*$")

SECRET_PATTERNS = [
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    r"\bsk-[A-Za-z0-9_-]{20,}\b",
    r"(?i)\b(?:access[_-]?token|api[_-]?key|password)\s*[:=]\s*[\"']?[A-Za-z0-9_./+\-=]{12,}",
]

ENUM_CLOSED_SETS: dict[str, tuple[str, ...]] = {
    "RECEIVER_MODE": ("EXECUTE_FIRST_ACTION", "AWAIT_USER_DECISION"),
    "NEXT_GATE_AUTHORIZATION": ("AUTHORIZED", "NOT_AUTHORIZED", "USER_DECISION_REQUIRED"),
    "L_CARRY": ("L0", "L1", "L2", "L3"),
    "NEXT_FLOOR": ("L0", "L1", "L2", "L3"),
}
ENUM_CHUNK_RE = re.compile(r"[A-Za-z_0-9| ]*")

DIMENSION_HINTS = {
    "summary": [r"总结", r"发生了什么", r"what happened", r"summary"],
    "technical": [r"技术路线", r"架构", r"实现", r"technical", r"architecture", r"method"],
    "state": [r"当前状态", r"\bSOT\b", r"已完成", r"current state", r"completed"],
    "task": [r"下一", r"任务", r"第一.*步", r"next session", r"first .*action", r"task"],
    "development": [r"发展方向", r"未来方向", r"后续方向", r"future direction", r"development"],
    "facts_evidence": [r"证据", r"事实", r"SHA256", r"commit", r"receipt", r"evidence", r"verified"],
}

RECEIPT_DUTY_SIGNALS = [
    r"receiver outcome receipt",
    r"outcome[_ ]receipt",
    r"回执",
]

UNSUPPORTED_SCOPE_CLAIMS = [
    r"(?i)\ball account history (?:was |has been )?scanned\b",
    r"(?i)\ball session history (?:was |has been )?scanned\b",
    r"已扫描全部账号历史",
    r"已读取全部会话历史",
]

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_SPAN_RE = re.compile(r"`+[^`]+`+")


@dataclass
class RuleRead:

    rule_id: str
    searched: list[str]
    hits: list[dict] = field(default_factory=list)
    corpus: str = ""
    decision: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "searched": self.searched,
            "hits": self.hits,
            "corpus": self.corpus,
            "decision": self.decision,
        }


def _hit(line_no: int, col: int, match: str, context: str) -> dict:
    return {"line": line_no + 1, "col": col + 1, "match": match[:80], "context": context}


def fenced_line_set(lines: list[str]) -> set[int]:
    fenced: set[int] = set()
    opener: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        if opener is None:
            m = FENCE_OPEN_RE.match(line)
            if m:
                fence = m.group(1)
                opener = (fence[0], len(fence))
                fenced.add(i)
        else:
            ch, ln = opener
            if re.match(rf"^\s*{ch}{{{ln},}}\s*$", line):
                fenced.add(i)
                opener = None
            else:
                fenced.add(i)
    return fenced


def inline_span_spans(line: str) -> list[tuple[int, int]]:
    return [m.span() for m in INLINE_SPAN_RE.finditer(line)]


def angle_span_spans(line: str) -> list[tuple[int, int]]:
    return [m.span() for m in re.finditer(PLACEHOLDER_PATTERNS[0][1], line)]


def _covered(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(a <= start and end <= b for a, b in spans)


def corpus_note(lines: list[str]) -> str:
    fenced = fenced_line_set(lines)
    has_cjk = any("\u4e00" <= ch <= "\u9fff" for line in lines for ch in line)
    lang = "CJK+latin" if has_cjk else "latin"
    return f"{len(lines)} lines, {len(fenced)} fenced lines, {lang}"


def placeholder_rule(
    lines: list[str], corpus: str
) -> tuple[list[str], RuleRead]:
    fenced = fenced_line_set(lines)
    errors: list[str] = []
    hits: list[dict] = []
    action_counts: dict[str, int] = {}

    for pid, pattern in PLACEHOLDER_PATTERNS:
        rx = re.compile(pattern, re.IGNORECASE)
        for line_no, line in enumerate(lines):
            if line_no in fenced:
                hits.extend(_hit(line_no, m.start(), m.group(0), "fenced-code-block")
                            for m in rx.finditer(line))
                continue
            spans = inline_span_spans(line)
            angles = angle_span_spans(line)
            for m in rx.finditer(line):
                start, end = m.span()
                if _covered(spans, start, end):
                    hits.append(_hit(line_no, start, m.group(0), "inline-code-span"))
                    continue
                if pid in NOUN_PATTERN_IDS:
                    if not _covered(angles, start, end):
                        left = line[:start].rstrip()
                        if not VALUE_POSITION_LEFT_RE.search(left[-2:]):
                            hits.append(_hit(line_no, start, m.group(0), "prose-mention"))
                            continue
                if pid in ("angle-slot",) or pid in NOUN_PATTERN_IDS:
                    outside = line[:start] + line[end:]
                    noun_nearby = bool(PHENOMENON_NOUN_RE.search(outside)) or (
                        pid in NOUN_PATTERN_IDS
                    )
                    if noun_nearby and DISCUSSION_VERB_RE.search(line):
                        hits.append(_hit(line_no, start, m.group(0), "discussion-line"))
                        continue
                hits.append(_hit(line_no, start, m.group(0), "action"))
                action_counts[pid] = action_counts.get(pid, 0) + 1

    for pid, pattern in PLACEHOLDER_PATTERNS:
        if action_counts.get(pid):
            errors.append(f"unresolved placeholder detected: {pattern}")

    action_total = sum(action_counts.values())
    suppressed = len(hits) - action_total
    if action_total:
        decision = (
            f"ERROR emitted: {action_total} hit(s) at value position "
            f"({', '.join(f'{pid}={n}' for pid, n in action_counts.items())})"
        )
    elif hits:
        decision = f"no ERROR: all {len(hits)} hit(s) are mentions ({suppressed} suppressed)"
    else:
        decision = "no ERROR: no hits found (searched, not seen — a read, not a pass)"

    read = RuleRead(
        rule_id="placeholder-action-vs-mention",
        searched=[f"{pid}: /{pat}/i" for pid, pat in PLACEHOLDER_PATTERNS],
        hits=hits,
        corpus=corpus + "; per-hit context classification",
        decision=decision,
    )
    return errors, read


def secret_rule(text: str, corpus: str) -> tuple[list[str], RuleRead]:
    errors: list[str] = []
    hits: list[dict] = []
    lines = text.splitlines()
    for pattern in SECRET_PATTERNS:
        rx = re.compile(pattern)
        for line_no, line in enumerate(lines):
            for m in rx.finditer(line):
                hits.append(_hit(line_no, m.start(), m.group(0), "credential-syntax"))
                errors.append(f"possible exposed secret detected: {pattern}")
    if errors:
        decision = f"ERROR emitted: {len(errors)} credential-syntax hit(s)"
    elif hits:
        decision = "no ERROR"
    else:
        decision = "no ERROR: no hits found (searched, not seen — a read, not a pass)"
    read = RuleRead(
        rule_id="exposed-secret",
        searched=[f"/{p}/" for p in SECRET_PATTERNS],
        hits=hits,
        corpus=corpus + "; value-position credential syntax, case flags per pattern",
        decision=decision,
    )
    return errors, read


def enum_rule(lines: list[str], key: str, allowed: tuple[str, ...], corpus: str) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    line_re = re.compile(rf"\b{key}\s*[=:]\s*(.*)")
    for line_no, line in enumerate(lines):
        m = line_re.search(line)
        if not m:
            continue
        chunk = ENUM_CHUNK_RE.match(m.group(1).strip()).group(0).strip()
        tokens = [t.strip() for t in chunk.split("|") if t.strip()] if chunk else []
        if not tokens:
            hits.append(_hit(line_no, m.start(1), m.group(1).strip()[:80], "empty-value"))
            warnings.append(
                f"enum field {key} has an empty value; closed set is {{{', '.join(allowed)}}}"
            )
            continue
        for token in tokens:
            in_set = token in allowed
            hits.append(_hit(line_no, m.start(1), token, "in-set" if in_set else "OUT-OF-SET"))
            if not in_set:
                warnings.append(
                    f"enum field {key} value '{token}' is outside the closed set "
                    f"{{{', '.join(allowed)}}}; review whether this is adapted wording "
                    "or an unreadable receiver mode / gate state"
                )
    if warnings:
        decision = f"WARN emitted: {len(warnings)} out-of-set/empty value(s)"
    elif hits:
        decision = f"no warning: {len(hits)} value(s), all inside the closed set"
    else:
        decision = "no warning: field absent (searched, not seen — a read, not a pass)"
    read = RuleRead(
        rule_id=f"enum-{key}",
        searched=[f"line matching /\\b{key}\\s*[=:]/ (canonical name, case-sensitive)",
                  f"closed set {{{', '.join(allowed)}}}"],
        hits=hits,
        corpus=corpus,
        decision=decision,
    )
    return warnings, read


def keyword_rule(
    rule_id: str,
    searched: list[str],
    patterns: list[str],
    lines: list[str],
    corpus: str,
    warn_if_absent: bool,
    warning: str,
) -> tuple[list[str], RuleRead]:
    hits: list[dict] = []
    present = False
    for pattern in patterns:
        rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for line_no, line in enumerate(lines):
            m = rx.search(line)
            if m:
                present = True
                hits.append(_hit(line_no, m.start(), m.group(0)[:80], f"signal /{pattern}/"))
    if warn_if_absent and not present:
        warnings = [warning]
        decision = f"WARN emitted: no signal found for any of {len(patterns)} pattern(s) (searched, not seen)"
    else:
        warnings = []
        decision = (
            f"no warning: signal present ({len(hits)} hit(s))"
            if present
            else "no warning required for this rule's direction"
        )
    read = RuleRead(rule_id=rule_id, searched=searched, hits=hits, corpus=corpus, decision=decision)
    return warnings, read



ALTITUDE_SCOPE_SIGNALS = [
    r"双通道",
    r"dual[- ]channel",
    r"\bL_CARRY\b",
    r"\bL2_MECHANISMS\b",
    r"\bNEXT_FLOOR\b",
]
ALTITUDE_LEVELS: dict[str, int] = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}

FIELD_KEY_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,}\s*[=:]")
FIELD_RECORD_LINE_RE = re.compile(
    r"^\s*(\[(?:enumerated|manual)\]|checked\s*:|not\s*checked\s*:|未检索|未查)",
    re.IGNORECASE,
)
FIELD_RECORD_LINE_RE = re.compile(
    r"^\s*(checked\s*:|not\s*checked\s*:|未检索|未查)",
    re.IGNORECASE,
)


_UNLANDED_BULLET_RE = re.compile(r"^\s*[-*]\s+\S")

def _coalesce_unlanded_entries(block):
    out, cur, mode = [], [], None
    for raw in block:
        if FIELD_RECORD_LINE_RE.match(raw):
            if mode == "entry" and cur:
                out.append(" ".join(cur))
            cur, mode = [], "record"
            continue
        if _UNLANDED_BULLET_RE.match(raw):
            if mode == "entry" and cur:
                out.append(" ".join(cur))
            cur, mode = [raw.strip()], "entry"
            continue
        if mode == "entry":
            cur.append(raw.strip())
    if mode == "entry" and cur:
        out.append(" ".join(cur))
    return out


_ENTRY_LEAD_RE = re.compile(r"^(?:M\d+|[-*\u2022]|\d+[.)])\s+\S")

def _coalesce_by_indent(block):
    out, cur, mode = [], [], None
    for raw in block:
        line = raw.strip()
        if not line:
            continue
        if FIELD_RECORD_LINE_RE.match(line):
            if mode == "entry" and cur:
                out.append(" ".join(cur))
            cur, mode = [], "record"
            continue
        if _ENTRY_LEAD_RE.match(line):
            if mode == "entry" and cur:
                out.append(" ".join(cur))
            cur, mode = [line], "entry"
            continue
        if mode == "entry":
            cur.append(line)
    if mode == "entry" and cur:
        out.append(" ".join(cur))
    return out

_ANCHOR_PATH_RUN_RE = re.compile(r"([^\s（）()【】\[\]「」|,，;；:]+)$")
_ANCHOR_PATH_LINE_RE = re.compile(r"(\S+?):(\d{1,6})$")
_UNLANDED_ANCHOR_RE = re.compile(
    r"(?P<file>[^\s@]+)\s*@\s*"
    r"(?P<ts>\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?)"
)
_UNLANDED_QUOTE_RE = re.compile(r"[「\"]([^「\"]{6,})[」\"]")
_HONEST_SCOPE_RECORD_RE = re.compile(
    r"not\s*checked|未检索|未查|未做全量|未全量|unindexed", re.IGNORECASE
)


def _field_block(lines: list[str], key: str) -> tuple[str | None, list[str]]:
    key_re = re.compile(rf"^\s*{re.escape(key)}\s*[=:]\s*(.*)$")
    for i, line in enumerate(lines):
        m = key_re.match(line)
        if not m:
            continue
        inline = m.group(1).strip()
        entries: list[str] = [inline] if inline else []
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                break
            if FENCE_OPEN_RE.match(nxt):
                break
            if FIELD_KEY_LINE_RE.match(nxt) or re.match(r"^\s*#{1,6}\s", nxt):
                break
            entries.append(nxt.strip())
        return inline, entries
    return None, []


def _level_token(lines: list[str], key: str) -> str:
    key_re = re.compile(rf"\b{re.escape(key)}\s*[=:]\s*(.*)")
    for line in lines:
        m = key_re.search(line)
        if m:
            return ENUM_CHUNK_RE.match(m.group(1).strip()).group(0).strip()
    return ""


def _resolve_anchor_target(raw: str, base_dir: Path) -> Path | None:
    candidates = [resolve_path_token(raw, base_dir)]
    for c in candidates:
        try:
            resolved = c.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _heading_in_file(target: Path, heading: str) -> bool:
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    want = heading.strip().strip("`*_").strip().lower()
    if not want:
        return False
    for ln in text.splitlines():
        m = re.match(r"^\s*#{1,6}\s+(.*?)\s*$", ln)
        if m and m.group(1).strip().lower() == want:
            return True
    return False


def _mechanism_anchor(entry: str) -> tuple[str, str, str] | None:
    line = entry.strip()
    if not line:
        return None
    if "#" in line:
        idx = line.rfind("#")
        heading = line[idx + 1:].strip().strip("`*_（）()【】「」,，.;。: ").strip()
        path_m = _ANCHOR_PATH_RUN_RE.search(line[:idx])
        if path_m and heading:
            return ("heading", path_m.group(1), heading)
        return None
    tokens = line.split()
    if not tokens:
        return None
    tok = tokens[-1].strip("()[]，,;。；.")
    tok = tokens[-1].lstrip("([（【").rstrip(")）]】，,;；.")
    m = _ANCHOR_PATH_LINE_RE.match(tok)
    if m:
        return ("line", m.group(1), m.group(2))
    return None


def altitude_scope_rule(lines: list[str], corpus: str) -> tuple[bool, RuleRead]:
    hits: list[dict] = []
    for pattern in ALTITUDE_SCOPE_SIGNALS:
        rx = re.compile(pattern, re.IGNORECASE)
        for line_no, line in enumerate(lines):
            m = rx.search(line)
            if m:
                hits.append(_hit(line_no, m.start(), m.group(0), f"scope /{pattern}/"))
    in_scope = bool(hits)
    decision = (
        f"in scope: {len(hits)} altitude signal hit(s)"
        if in_scope
        else "out of scope: no altitude signal (searched, not seen — a read, not a pass)"
    )
    read = RuleRead(
        rule_id="altitude-scope-gate",
        searched=[f"/{p}/i" for p in ALTITUDE_SCOPE_SIGNALS],
        hits=hits,
        corpus=corpus,
        decision=decision,
    )
    return in_scope, read


def altitude_fields_rule(
    lines: list[str], base_dir: Path, corpus: str, in_scope: bool
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    carry = _level_token(lines, "L_CARRY")
    floor = _level_token(lines, "NEXT_FLOOR")
    for key, value in (("L_CARRY", carry), ("NEXT_FLOOR", floor)):
        hits.append({"field": key, "value": value or "ABSENT"})
        if in_scope and not value:
            warnings.append(
                f"altitude field {key} absent; per the window-altitude protocol a window round missing the "
                "altitude trio is recorded as not closed (advisory — candidate protocol, "
                "WARN tier only)"
            )
    _, mechanism_entries = _field_block(lines, "L2_MECHANISMS")
    _mech_coalesced = _coalesce_by_indent(mechanism_entries)
    mechanism_entries = _mech_coalesced if _mech_coalesced else mechanism_entries
    hits.append({"field": "L2_MECHANISMS", "entries": len(mechanism_entries)})
    if in_scope and not mechanism_entries:
        warnings.append(
            "altitude field L2_MECHANISMS absent/empty; per the window-altitude protocol a window round missing "
            "the altitude trio is recorded as not closed (advisory — candidate protocol, "
            "WARN tier only)"
        )
    if carry in ("L2", "L3"):
        if not mechanism_entries:
            warnings.append(
                f"L_CARRY={carry} with no L2_MECHANISMS entries: an altitude claim without "
                "mechanism anchors is a bare self-report (window-altitude cross-field gate)"
            )
        else:
            for entry in mechanism_entries:
                if FIELD_RECORD_LINE_RE.match(entry):
                    continue
                anchor = _mechanism_anchor(entry)
                if anchor is None:
                    warnings.append(
                        "L2_MECHANISMS entry carries no machine-resolvable anchor; required "
                        "syntax is <path>#<markdown heading> or <path>:<line-number> — a "
                        "bare semantic event id (E5/A6b/M1) does not resolve"
                    )
                    hits.append({"entry": entry[:80], "anchor": "UNPARSEABLE"})
                    continue
                kind, raw_path, detail = anchor
                target = _resolve_anchor_target(raw_path, base_dir)
                if target is None:
                    warnings.append(
                        f"L2_MECHANISMS anchor target not resolvable from this handoff: "
                        f"{raw_path} (path must exist relative to this handoff file, or "
                        "be absolute)"
                    )
                    hits.append({"entry": entry[:80], "anchor": f"TARGET-MISSING:{raw_path}"})
                    continue
                if kind == "heading":
                    if _heading_in_file(target, detail):
                        hits.append({"entry": entry[:80], "anchor": f"heading-ok:{detail}"})
                    else:
                        warnings.append(
                            f"L2_MECHANISMS anchor heading not found in {target.name}: "
                            f"'{detail}'"
                        )
                        hits.append({"entry": entry[:80], "anchor": f"HEADING-MISSING:{detail}"})
                else:
                    line_no = int(detail)
                    total = len(
                        target.read_text(encoding="utf-8", errors="replace").splitlines()
                    )
                    if 1 <= line_no <= max(total, 1):
                        hits.append({"entry": entry[:80], "anchor": f"line-ok:{line_no}"})
                    else:
                        warnings.append(
                            f"L2_MECHANISMS anchor line out of range in {target.name}: "
                            f"{line_no} (file has {total} lines)"
                        )
                        hits.append(
                            {"entry": entry[:80], "anchor": f"LINE-OUT-OF-RANGE:{line_no}"}
                        )
    if carry in ALTITUDE_LEVELS and floor in ALTITUDE_LEVELS:
        if ALTITUDE_LEVELS[floor] > ALTITUDE_LEVELS[carry]:
            warnings.append(
                f"NEXT_FLOOR={floor} is above L_CARRY={carry}: demanding the next window "
                "start higher than what this window carried makes every next-window output "
                "a regression round by definition (window-altitude protocol)"
            )
    if warnings:
        decision = f"WARN emitted: {len(warnings)} altitude finding(s)"
    elif in_scope:
        decision = "no warning: altitude trio present and consistent"
    else:
        decision = "no warning: out of scope (scope read recorded by altitude-scope-gate)"
    read = RuleRead(
        rule_id="altitude-fields-dcmp-s8",
        searched=[
            "L_CARRY / NEXT_FLOOR tokens (enum membership via enum-L_CARRY / enum-NEXT_FLOOR)",
            "L2_MECHANISMS entry block; anchor syntax <path>#<heading> | <path>:<line>",
            "cross-field: L_CARRY>=L2 => >=1 resolvable anchor; NEXT_FLOOR<=L_CARRY",
        ],
        hits=hits,
        corpus=corpus,
        decision=decision,
    )
    return warnings, read


def landed_index_rule(
    lines: list[str], corpus: str, in_scope: bool
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    present = any(re.search(r"\bLANDED_PROTOCOLS_INDEX\s*[=:]", ln) for ln in lines)
    hits.append({"field": "LANDED_PROTOCOLS_INDEX", "present": present})
    if not present:
        if in_scope:
            warnings.append(
                "no LANDED_PROTOCOLS_INDEX field; an in-scope handoff should list what the "
                "system has already built from a mechanical enumeration source (motivating "
                "failure: the dispatcher nearly re-invented an already-landed protocol)"
            )
        decision = (
            "WARN emitted: field absent in an in-scope handoff"
            if in_scope
            else "no warning: field absent, out of scope (a read, not a pass)"
        )
    else:
        _, entries = _field_block(lines, "LANDED_PROTOCOLS_INDEX")
        content = [e for e in entries if not FIELD_RECORD_LINE_RE.match(e)]
        labeled = any(
            re.search(r"\[enumerated\]|枚举源|enumeration", e, re.IGNORECASE) for e in entries
        )
        hits.append({"entries": len(entries), "content_lines": len(content),
                     "enumeration_labeled": labeled})
        if not content:
            warnings.append(
                "LANDED_PROTOCOLS_INDEX present but empty; list the built protocols / "
                "mechanisms / task roots with pointer + when-to-read, or write NONE "
                "explicitly"
            )
        elif not labeled:
            warnings.append(
                "LANDED_PROTOCOLS_INDEX carries no enumeration-source marker ([enumerated]/"
                "[manual]); a recall-only list degenerates and cannot list unknown-unknowns "
                ""
            )
        decision = (
            f"WARN emitted: {len(warnings)} landed-index finding(s)"
            if warnings
            else f"no warning: {len(content)} content line(s) with an enumeration marker"
        )
    read = RuleRead(
        rule_id="landed-protocols-index",
        searched=[
            "LANDED_PROTOCOLS_INDEX field block",
            "[enumerated]/[manual] source markers or 枚举源",
        ],
        hits=hits,
        corpus=corpus,
        decision=decision,
    )
    return warnings, read


VOLATILE_SET_TOKENS = (
    r"恒脏",
    r"tracked\s*改动",
    r"tracked\s+changes?",
    r"未提交",
    r"uncommitted",
    r"工作区",
    r"working\s+tree",
    r"在飞",
    r"未闭项",
    r"dirty",
    r"登记面",
)

VOLATILE_ADJACENCY_MAX = 10
VOLATILE_QUOTE_PAIRS = (("\u300c", "\u300d"), ("\u300e", "\u300f"),
                        ("\u201c", "\u201d"), ("`", "`"))

COUNT_LITERAL_RE = re.compile(r"(?:[0-9]+|[一二两三四五六七八九十])\s*(?:个|类|条|项|张|份|处)")

RECOMPUTE_TOKENS = (
    r"git\s+status",
    r"git\s+log",
    r"git\s+diff",
    r"git\s+ls-files",
    r"shasum",
    r"sha256sum",
    r"grep\s+-[a-zA-Z]*c",
    r"grep\s+-[a-zA-Z]*l",
    r"wc\s+-l",
    r"\bfind\s+/",
    r"\bls\s+-",
    r"\[enumerated\]",
    r"\[manual\]",
    r"枚举源",
    r"复算",
)

VOLATILE_EXEMPTION_RADIUS = 2


def volatile_enumeration_rule(
    lines: list[str], corpus: str
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []

    set_rx = [re.compile(p, re.IGNORECASE) for p in VOLATILE_SET_TOKENS]
    recompute_rx = [re.compile(p, re.IGNORECASE) for p in RECOMPUTE_TOKENS]

    def _has_recompute(idx: int) -> bool:
        lo = max(0, idx - VOLATILE_EXEMPTION_RADIUS)
        hi = min(len(lines), idx + VOLATILE_EXEMPTION_RADIUS + 1)
        window = "\n".join(lines[lo:hi])
        return any(rx.search(window) for rx in recompute_rx)

    def _quoted(line: str, start: int, end: int) -> bool:
        for op, cl in VOLATILE_QUOTE_PAIRS:
            before = line.rfind(op, 0, start)
            if before == -1:
                continue
            closing = line.find(cl, end)
            if closing != -1:
                return True
        return False

    def _gap(a: tuple[int, int], b: tuple[int, int]) -> int:
        if a[1] <= b[0]:
            return b[0] - a[1]
        if b[1] <= a[0]:
            return a[0] - b[1]
        return 0

    for idx, line in enumerate(lines):
        matched = None
        for count_m in COUNT_LITERAL_RE.finditer(line):
            if count_m.start() > 0 and line[count_m.start() - 1] == "\u7b2c":
                continue
            if _quoted(line, count_m.start(), count_m.end()):
                continue
            for rx in set_rx:
                for set_m in rx.finditer(line):
                    if _quoted(line, set_m.start(), set_m.end()):
                        continue
                    if _gap(count_m.span(), set_m.span()) <= VOLATILE_ADJACENCY_MAX:
                        matched = (count_m, set_m)
                        break
                if matched:
                    break
            if matched:
                break
        if not matched:
            continue
        count_m, set_m = matched
        exempt = _has_recompute(idx)
        hits.append(
            _hit(idx, count_m.start(), count_m.group(0), line.strip()[:120])
            | {"set_token": set_m.group(0), "recompute_within_radius": exempt}
        )
        if not exempt:
            warnings.append(
                "volatile enumeration at line %d: '%s' counts a live object set (%s) with no "
                "recompute command within %d lines; the count is false as soon as the set "
                "changes — give the receiver the command, not the number"
                % (idx + 1, count_m.group(0), set_m.group(0), VOLATILE_EXEMPTION_RADIUS)
            )

    unexempt = sum(1 for h in hits if not h["recompute_within_radius"])
    read = RuleRead(
        rule_id="volatile-enumeration",
        searched=[
            "count literal (numeral + Chinese classifier) within %d chars of a live-object-set "
            "token, excluding ordinals and quoted counts" % VOLATILE_ADJACENCY_MAX,
            "recompute command or enumeration-source marker within +/-%d lines"
            % VOLATILE_EXEMPTION_RADIUS,
        ],
        hits=hits,
        corpus=corpus,
        decision=(
            "WARN emitted: %d counted claim(s) about a live object set with no adjacent "
            "recompute command (%d exempt)" % (unexempt, len(hits) - unexempt)
            if unexempt
            else "no WARN: %d counted claim(s) found, all with an adjacent recompute command "
            "(searched, not seen)" % len(hits)
        ),
    )
    return warnings, read


CONCRETIZATION_ENTRY_RE = re.compile(r"^\s*(新增|继承|退役)\s+([A-Z]-?\d+)\b")
CONCRETIZATION_CARRIER_RE = re.compile(r"(?:\$SKILL_ROOT/)?[~/\w.\-]+\.(?:py|sh)\b")
CONCRETIZATION_SECTION_RE = re.compile(r"METHOD_INCREMENT")
MD_HEADING_RE = re.compile(r"^(#{1,6})\s*\S")


def _method_increment_span(lines: list[str]) -> "tuple[int, int] | None":
    start = None
    for idx, line in enumerate(lines):
        if line.startswith("#") and CONCRETIZATION_SECTION_RE.search(line):
            start = idx
            break
    if start is None:
        for idx, line in enumerate(lines):
            if CONCRETIZATION_SECTION_RE.match(line.lstrip()) and "=" in line:
                start = idx
                break
    if start is None:
        return None
    head = MD_HEADING_RE.match(lines[start])
    start_level = len(head.group(1)) if head else 2
    end, closed_by = len(lines), "end-of-file"
    for idx in range(start + 1, len(lines)):
        m = MD_HEADING_RE.match(lines[idx])
        if not m or CONCRETIZATION_SECTION_RE.search(lines[idx]):
            continue
        level = len(m.group(1))
        if level <= start_level:
            end, closed_by = idx, "heading-level-%d: %s" % (level, lines[idx].strip()[:40])
            break
    return start, end, start_level, closed_by

CARRIER_STATE_ENV = "HANDOFF_ACTION_POINTS"


def _action_point_match(raw_written: str, resolved: "Path") -> str:
    patterns = os.environ.get(CARRIER_STATE_ENV, "").strip()
    if not patterns:
        return "NOT_CHECKED"
    forms = {f for f in (raw_written, str(resolved)) if f}
    basename = resolved.name
    best = "NONE"
    surfaces_seen = 0
    for pattern in patterns.split(":"):
        pattern = pattern.strip()
        if not pattern:
            continue
        expanded = glob.glob(os.path.expanduser(pattern), recursive=True)
        surfaces_seen += len(expanded)
        for surface in expanded:
            try:
                text = Path(surface).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                full = any(f in line for f in forms)
                if full and not line.strip().startswith("#"):
                    return "COMMAND"
                if full:
                    best = "COMMENT_ONLY"
                elif basename and basename in line and best == "NONE":
                    best = "BASENAME_ONLY"
    if best == "NONE" and surfaces_seen == 0:
        return "NO_SURFACE_MATCHED"
    return best


def _carrier_facts(carrier: str, base_dir: "Path | None") -> dict:
    raw = resolve_path_token(carrier)
    candidates: list[Path] = [raw] if raw.is_absolute() else []
    if not raw.is_absolute():
        if base_dir is not None:
            candidates.append(resolve_path_token(carrier, base_dir))
        candidates.append(Path.cwd() / raw)
    found = next((c for c in candidates if c.exists()), None)
    match = "NOT_CHECKED" if found is None else _action_point_match(carrier, found)
    return {
        "carrier": carrier,
        "carrier_resolved": str(found) if found is not None else None,
        "carrier_present": found is not None,
        "action_point_match": match,
        "native_event": "NOT_OBSERVED",
        "carrier_state": ("MISSING" if found is None
                          else "TEXT_REFERENCED" if match == "COMMAND"
                          else "EXISTS"),
    }


def concretization_rate_rule(
    lines: list[str], corpus: str, in_scope: bool, base_dir: "Path | None" = None
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    if not in_scope:
        return warnings, RuleRead(
            rule_id="concretization-rate",
            searched=["METHOD_INCREMENT entries (skipped: handoff not in altitude scope)"],
            hits=[], corpus=corpus, decision="SKIP: out of scope",
        )

    span = _method_increment_span(lines)
    if span is None:
        return warnings, RuleRead(
            rule_id="concretization-rate",
            searched=["METHOD_INCREMENT section marker"],
            hits=[], corpus=corpus,
            decision="SKIP: no METHOD_INCREMENT section",
        )
    start, end, _start_level, closed_by = span

    blocks: list[tuple[str, list[str]]] = []
    current_id = None
    current: list[str] = []
    for line in lines[start:end]:
        m = CONCRETIZATION_ENTRY_RE.match(line)
        if m:
            if current_id is not None:
                blocks.append((current_id, current))
            current_id = m.group(2)
            current = [line]
        elif current_id is not None:
            if line.startswith((" ", "\t")) or not line.strip():
                current.append(line)
            else:
                blocks.append((current_id, current))
                current_id = None
                current = []
    if current_id is not None:
        blocks.append((current_id, current))

    total = len(blocks)
    anchored = 0
    missing_names: list[str] = []
    wired = 0
    for entry_id, block in blocks:
        carrier = CONCRETIZATION_CARRIER_RE.search("\n".join(block))
        if not carrier:
            hits.append({"entry": entry_id, "carrier": None, "carrier_state": "NONE",
                         "carrier_resolved": None, "carrier_present": False,
                         "action_point_match": "NOT_CHECKED", "native_event": "NOT_OBSERVED"})
            continue
        anchored += 1
        facts = _carrier_facts(carrier.group(0), base_dir)
        if facts["carrier_state"] == "MISSING":
            missing_names.append(carrier.group(0))
        elif facts["carrier_state"] == "TEXT_REFERENCED":
            wired += 1
        hits.append({"entry": entry_id, **facts})
    missing = len(missing_names)

    if total == 0:
        decision = "SKIP: section present but no 新增/继承/退役 entries parsed"
    else:
        rate = anchored / total
        wiring_checked = bool(os.environ.get(CARRIER_STATE_ENV, "").strip())
        decision = (
            "carrier reference %d/%d entries name an executable carrier; of those "
            "%d MISSING, %d EXISTS, %d TEXT_REFERENCED%s"
            % (anchored, total, missing, anchored - missing - wired, wired,
               "" if wiring_checked else " (wiring not checked: %s unset)" % CARRIER_STATE_ENV)
        )
        if missing:
            warnings.append(
                "METHOD_INCREMENT: %d of %d referenced carriers do not exist on disk (%s) — "
                "a named-but-absent carrier reads as mechanized and fires nowhere. Fix the "
                "path, or record the entry as text. This is also the 'carrier disappeared' "
                "retirement trigger for the entry that names it."
                % (missing, anchored, ", ".join(missing_names[:3]))
            )
        if anchored == 0:
            warnings.append(
                "METHOD_INCREMENT: 0 of %d entries name an executable carrier (.py/.sh). "
                "Text entries are not invalid — local n>=2 measurement puts their "
                "effective-consumption rate at 47%%-83%% — but none fires on its own, so "
                "each depends on the next window actually reading it." % total
            )
        elif rate < 0.5:
            warnings.append(
                "METHOD_INCREMENT: %d of %d entries name an executable carrier; the rest "
                "are text that fires only when read. Say which of the two channels this "
                "window relied on; entry count alone is not progress." % (anchored, total)
            )

    return warnings, RuleRead(
        rule_id="concretization-rate",
        searched=[
            "METHOD_INCREMENT entry lines matching 新增|继承|退役 <ID>",
            "an executable carrier path (.py/.sh) inside each entry block",
            "each carrier resolved into independent facts: carrier_resolved / "
            "carrier_present / action_point_match / native_event, summarised conservatively "
            "as NONE/MISSING/EXISTS/TEXT_REFERENCED. native_event is always NOT_OBSERVED: "
            "no local event-registration surface exists, so wiring is never asserted "
            "(action-point text is read only when %s is set)" % CARRIER_STATE_ENV,
        ],
        hits=hits, corpus=corpus, decision=decision,
    )


STATE_BLOCK_BOUNDS = (
    ("NEW_SINCE_PREDECESSOR=", "AUTHORITY_OR_STATE_CHANGED="),
    ("UNLANDED_DIRECTIONS=", "  Checked:"),
)
STATE_ANCHOR_RE = tuple(
    re.compile(p) for p in (
        r"git\s+(?:status|log|diff|ls-files|show|check-ignore)",
        r"shasum|sha256sum",
        r"\bgrep\s+-|\brg\s+",
        r"[/\w.\-]+\.(?:py|sh)\b",
        r"[/\w.\-]+\.md\b",
        r"\b[0-9a-f]{7,}\b",
        r"--[a-z][a-z\-]{3,}",
        r"\bF-\d{4}-\d+\b",
    )
)
STATE_CLAIM_LEAD = ("·", "-", "\U0001f534")
STATE_ANCHOR_MIN_RATE = 0.5


def state_anchor_rate_rule(
    lines: list[str], corpus: str
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    total = anchored = 0

    for start_tok, end_tok in STATE_BLOCK_BOUNDS:
        inside = False
        for idx, line in enumerate(lines):
            if line.startswith(start_tok):
                inside = True
                continue
            if not inside:
                continue
            if line.startswith(end_tok) or (
                line[:1].strip() and re.match(r"^[A-Z][A-Z0-9_]*=", line)
            ):
                inside = False
                continue
            claim = line.strip()
            if not claim.startswith(STATE_CLAIM_LEAD):
                continue
            total += 1
            has_anchor = any(rx.search(line) for rx in STATE_ANCHOR_RE)
            if has_anchor:
                anchored += 1
            else:
                hits.append(_hit(idx, 0, claim[:60], claim[:120]) | {"anchored": False})

    if total == 0:
        decision = "SKIP: no NEW_SINCE_PREDECESSOR / UNLANDED_DIRECTIONS state claims parsed"
        return warnings, RuleRead(
            rule_id="state-anchor-rate",
            searched=["state claim lines inside NEW_SINCE_PREDECESSOR / UNLANDED_DIRECTIONS"],
            hits=hits, corpus=corpus, decision=decision,
        )

    rate = anchored / total
    decision = "state-anchor %d/%d claims carry a recompute anchor" % (anchored, total)
    if rate < STATE_ANCHOR_MIN_RATE:
        warnings.append(
            "state claims: only %d of %d carry a recompute anchor (path / commit / --selftest "
            "/ finding id). The rest are bare snapshots that expire silently — the receiver "
            "cannot re-derive them at consumption time. This handoff's own rule is "
            "「不登记易变读数，只给复算命令」."
            % (anchored, total)
        )

    return warnings, RuleRead(
        rule_id="state-anchor-rate",
        searched=[
            "state claim lines (leading · / - / \U0001f534) inside "
            "NEW_SINCE_PREDECESSOR and UNLANDED_DIRECTIONS",
            "a recompute anchor on each: path(.py/.sh/.md) | commit hex | --selftest | F-YYYY-N",
        ],
        hits=hits, corpus=corpus, decision=decision,
    )


ALTITUDE_CEILING = "L3"
ALTITUDE_VALUE_RE = re.compile(
    r"^[ \t]*(L_CARRY|NEXT_FLOOR)[ \t]*[=:：][ \t]*[\"'\u300c\u300e]?[ \t]*(L\d+)", re.M
)


RECURSION_PRED_RE = re.compile(r"(?m)^[ \t]*PREDECESSOR_HANDOFF_ID[ \t]*=[ \t]*(\S+)")
RECURSION_VOID = ("NOT_APPLICABLE", "NONE", "UNKNOWN", "N/A", "-")
RECURSION_INHERIT_PTR_RE = re.compile(
    r"(?m)^[ \t]*UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE[ \t]*=[ \t]*(.*)$")


CROSSREF_DIR_RE = re.compile(r"(?<![\w/~.$])(\d{2}_[A-Z][A-Z0-9_]+)/(?=[A-Za-z0-9_])")
CROSSREF_ROOTED_RE = re.compile(r"[/~$][\w./$-]*$")


MI_LANDING_ENTRY_RE = re.compile(r"^\s*(?:新增\s+|新立\s+)?([A-Z]\d{1,2})[\s\u3000]")
MI_LANDING_OUT_RE = re.compile(r"\u21d2[ \t]*(?:G\.(\d+)|NOT_LANDED[ \t]*=[ \t]*(\S))")
MI_LANDING_ENTRIES_ENV = "SESSION_HANDOFF_ENTRIES"
MI_LANDING_FLOOR = "20260920"
MI_RULING_ANCHOR_FLOOR = "20260923"


def method_increment_landing_rule(lines: list[str], corpus: str, path=None) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    rid = "method-increment-landing"
    _d = _PA_DATE_RE.search(getattr(path, "name", "") or "")
    if not _d or _d.group(1) < MI_LANDING_FLOOR:
        return warnings, RuleRead(
            rule_id=rid, searched=["METHOD_INCREMENT entries: landing declaration"], hits=[], corpus=corpus,
            decision="SKIP: below landing floor %s by filename date — 存量件不追溯（同 CHK-7）" % MI_LANDING_FLOOR)
    span = _method_increment_span(lines)
    if span is None:
        return warnings, RuleRead(
            rule_id=rid, searched=["METHOD_INCREMENT section"], hits=[], corpus=corpus,
            decision="SKIP: no METHOD_INCREMENT section in this handoff")
    s, e, _lvl, _closed = span
    entries: list[tuple[str, int, list[str]]] = []
    for i in range(s + 1, e):
        m = MI_LANDING_ENTRY_RE.match(lines[i])
        if m:
            entries.append((m.group(1), i, [lines[i]]))
        elif entries:
            entries[-1][2].append(lines[i])
    ledger = os.environ.get(MI_LANDING_ENTRIES_ENV, "").strip()
    dangling_face = "RUN" if ledger else "NOT_RUN"
    hits: list[dict] = []
    without = 0
    ruling_on = _d.group(1) >= MI_RULING_ANCHOR_FLOOR
    rulings = rulings_anchored = 0
    for label, line_no, body in entries:
        if ruling_on and label.startswith("A"):
            rulings += 1
            if _UNLANDED_ANCHOR_RE.search("\n".join(body)):
                rulings_anchored += 1
            else:
                hits.append(_hit(line_no, 0, label, "no source anchor"))
                warnings.append(
                    "METHOD_INCREMENT ruling %s carries no verbatim-source anchor (<transcript> @ <timestamp>) — "
                    "the next window can read only this producer's paraphrase, which is where the principle "
                    "behind the instance gets lost" % label)
        if MI_LANDING_OUT_RE.search("\n".join(body)):
            hits.append(_hit(line_no, 0, label, "exit declared"))
            continue
        without += 1
        hits.append(_hit(line_no, 0, label, "no exit declaration"))
        warnings.append(
            "METHOD_INCREMENT entry %s has no landing declaration — value produced this window "
            "has no exit (declare where it lands, or declare explicitly that it does not)" % label)
    if not entries:
        decision = "SKIP: section present but no entries parsed"
    else:
        decision = ("%d/%d entries carry a landing declaration; dangling-id check=%s"
                    % (len(entries) - without, len(entries), dangling_face))
        decision += ("; rulings with source anchor %d/%d" % (rulings_anchored, rulings) if ruling_on
                     else "; ruling-anchor check SKIP (below floor %s)" % MI_RULING_ANCHOR_FLOOR)
        if dangling_face == "NOT_RUN":
            decision += (" (set $%s to a registry file to enable it — "
                         "an unchecked face is reported, not silently passed)"
                         % MI_LANDING_ENTRIES_ENV)
    return warnings, RuleRead(
        rule_id=rid, searched=["METHOD_INCREMENT entries: landing declaration"],
        hits=hits, corpus=corpus, decision=decision)


EVOLUTION_KERNEL_FLOOR = "20260923"
EVOLUTION_KERNEL_MAX_ITEMS = 12
EK_HEAD_RE = re.compile(r"^\s*(?:#{1,6}\s*)?EVOLUTION_KERNEL\b")
EK_ITEM_RE = re.compile(r"^\s*(K\d{1,3})[\s:：.]")
EK_POINTER_RE = re.compile(r"(?<![\w/$])(" + PATH_ROOT_ALT + r"[\w./~-]+\.(?:py|sh))(?::[A-Za-z_][\w-]*)?")


def _ek_pointer_ok(text: str) -> bool:
    for m in EK_POINTER_RE.finditer(text):
        if resolve_path_token(m.group(1)).is_file():
            return True
    return False


def evolution_kernel_rule(lines: list[str], corpus: str, path=None) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    rid = "evolution-kernel"
    searched = ["EVOLUTION_KERNEL section; K-items; anchor = on-disk mechanism path | recompute/refutation command"]
    start = next((i for i, l in enumerate(lines) if EK_HEAD_RE.match(l)), None)
    _d = _PA_DATE_RE.search(getattr(path, "name", "") or "")
    in_floor = bool(_d) and _d.group(1) >= EVOLUTION_KERNEL_FLOOR
    if start is None:
        if in_floor:
            warnings.append(
                "EVOLUTION_KERNEL absent — this handoff carries this window's derivative (METHOD_INCREMENT) "
                "but no integral: the integrated, anchored base that the next window builds on. Without it the "
                "chain is a series of snapshots and earlier load-bearing content drops out after two windows.")
            decision = "WARN emitted: absent at/after floor %s" % EVOLUTION_KERNEL_FLOOR
        else:
            decision = "SKIP: no EVOLUTION_KERNEL section (below floor %s or undated — not required)" % EVOLUTION_KERNEL_FLOOR
        return warnings, RuleRead(rule_id=rid, searched=searched, hits=[], corpus=corpus, decision=decision)
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if MD_HEADING_RE.match(lines[j]) or s.startswith("```") or s.startswith("~~~") \
                or re.match(r"^[A-Z][A-Z0-9_]*\s*=", lines[j]):
            end = j
            break
    items: list[tuple[str, int, list[str]]] = []
    for j in range(start + 1, end):
        m = EK_ITEM_RE.match(lines[j])
        if m:
            items.append((m.group(1), j, [lines[j]]))
        elif items:
            items[-1][2].append(lines[j])
    base_dir = Path(path).parent if path else Path.cwd()
    hits: list[dict] = []
    unanchored = 0
    for label, j, body in items:
        if _pa_has_recompute(body, base_dir) or _ek_pointer_ok("\n".join(body)):
            hits.append(_hit(j, 0, label, "anchored"))
        else:
            unanchored += 1
            hits.append(_hit(j, 0, label, "no anchor"))
            warnings.append(
                "EVOLUTION_KERNEL item %s carries no mechanical anchor (an on-disk mechanism path, a recompute "
                "command, or a refutation command). An unanchored item is inherited verbatim by every later "
                "generation — if it is wrong, it is wrong forever." % label)
    if len(items) > EVOLUTION_KERNEL_MAX_ITEMS:
        warnings.append(
            "EVOLUTION_KERNEL has %d items > budget %d — integrate (merge same-logic items into one) or retire "
            "items whose mechanism has landed, before adding." % (len(items), EVOLUTION_KERNEL_MAX_ITEMS))
    decision = ("section present but no K-items parsed" if not items else
                "%d/%d items anchored · budget %d/%d" % (len(items) - unanchored, len(items), len(items),
                                                         EVOLUTION_KERNEL_MAX_ITEMS))
    return warnings, RuleRead(rule_id=rid, searched=searched, hits=hits, corpus=corpus, decision=decision)


def cross_ref_path_rule(lines: list[str], corpus: str) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    fenced = fenced_line_set(lines)
    hits: list[dict] = []
    for idx, line in enumerate(lines):
        if idx in fenced:
            continue
        for m in CROSSREF_DIR_RE.finditer(line):
            before = line[:m.start()]
            if CROSSREF_ROOTED_RE.search(before):
                continue
            hits.append(_hit(idx, m.start(), m.group(0), "unrooted-cross-ref"))
    if hits:
        warnings.append(
            f"WARN emitted: {len(hits)} unrooted cross-file reference(s) —— "
            "相对写法在多候选仓根下会解析到不存在的目录。"
            "改为绝对路径或带显式仓根前缀。"
        )
        decision = f"WARN emitted: {len(hits)} unrooted hit(s)"
    else:
        decision = "no WARN: every cross-file reference carries a root (searched, not seen — a read, not a pass)"
    return warnings, RuleRead(
        rule_id="cross-ref-absolute-path",
        searched=[CROSSREF_DIR_RE.pattern, "fenced blocks excluded (roots carried by shell vars)"],
        hits=hits, corpus=corpus, decision=decision,
    )


def method_recursion_rule(lines: list[str], corpus: str) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    text = "\n".join(lines)
    pred = RECURSION_PRED_RE.search(text)
    kinds: list[str] = []
    by_heading: dict[str, int] = {}
    span = _method_increment_span(lines)
    section_present = span is not None
    span_lines: "list[int] | None" = None
    closed_by: "str | None" = None
    if span is not None:
        _s, _e, _lvl, closed_by = span
        span_lines = [_s + 1, _e]
        heading = lines[_s].strip()[:40]
        for line in lines[_s:_e]:
            h = MD_HEADING_RE.match(line)
            if h and not CONCRETIZATION_SECTION_RE.search(line):
                heading = line.strip()[:40]
            m = CONCRETIZATION_ENTRY_RE.match(line)
            if m:
                kinds.append(m.group(1))
                by_heading[heading] = by_heading.get(heading, 0) + 1
    counts = {k: kinds.count(k) for k in ("新增", "继承", "退役")}
    hits = [{"predecessor": pred.group(1) if pred else None, **counts, "entries": len(kinds),
             "span_lines": span_lines, "span_closed_by": closed_by,
             "entries_by_heading": by_heading or None}]
    if not pred or pred.group(1).upper() in RECURSION_VOID:
        return warnings, RuleRead(
            rule_id="method-recursion", searched=[RECURSION_PRED_RE.pattern, "新增|继承|退役 <ID>"],
            hits=hits, corpus=corpus,
            decision="SKIP: no identifiable predecessor — a first window is legitimately all-新增",
        )
    if not kinds:
        decision = ("SKIP: no METHOD_INCREMENT section in this handoff"
                    if not section_present else
                    "SKIP: METHOD_INCREMENT section present (lines %s, closed by %s) but zero "
                    "新增/继承/退役 entries parsed **inside** it — entries may have fallen outside "
                    "the section boundary; check placement before reading this as 'no methods'"
                    % (span_lines, closed_by))
        return warnings, RuleRead(
            rule_id="method-recursion", searched=[RECURSION_PRED_RE.pattern, "新增|继承|退役 <ID>"],
            hits=hits, corpus=corpus, decision=decision,
        )
    linked = counts["继承"] + counts["退役"]
    ratio = linked / len(kinds)
    _ptr = RECURSION_INHERIT_PTR_RE.search(text)
    _ptr_val = _ptr.group(1).strip() if _ptr else ""
    if _ptr and not _ptr_val:
        for _l in text[_ptr.end():].splitlines():
            if not _l.strip():
                continue
            _t = _l.strip()
            if _t.startswith("```") or _t.startswith("~~~"):
                break
            if MD_HEADING_RE.match(_l) or re.match(r"^[A-Z_]{3,}\s*=", _l):
                break
            _ptr_val = _t
            break
    by_reference = bool(_ptr_val) and _ptr_val.upper() not in RECURSION_VOID
    hits[0]["inherited_by_reference"] = by_reference
    if linked == 0 and not by_reference:
        warnings.append(
            "no explicit method relation parsed: all %d entries carry the 新增 prefix, none "
            "carries 继承 or 退役, and no non-void UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE "
            "field was found, although this handoff declares predecessor %s. The contract asks for "
            "inheritance to be explicit and directional, so **please check by hand** whether this "
            "window did inherit and simply did not mark it. "
            "🔴 MEASURES: prefix distribution plus presence of one field. "
            "DOES NOT MEASURE: whether this window actually built on its predecessor, whether an "
            "inheritance is correct, or whether capability rose. Prefixes are a **proxy**, and a "
            "handoff that inherits in prose without the prefix or the field will land here as a "
            "false positive — real-corpus measurement confirms that case exists. "
            "This warning therefore does not say 'flat push' and does not say 'not a pyramid'; "
            "those are capability verdicts that prefix counting cannot support."
            % (len(kinds), pred.group(1))
        )
    return warnings, RuleRead(
        rule_id="method-recursion",
        searched=[RECURSION_PRED_RE.pattern, "新增|继承|退役 <ID> 前缀分布"],
        hits=hits, corpus=corpus,
        decision="recursion %d/%d = %.0f%% (继承 %d + 退役 %d of %d entries; counted over lines %s, "
                 "section closed by %s)%s"
                 % (linked, len(kinds), ratio * 100, counts["继承"], counts["退役"], len(kinds),
                    span_lines, closed_by,
                    "; inheritance carried by reference (UNCHANGED_CRITICAL_ANCHORS…)"
                    if by_reference else ""),
    )


def altitude_saturation_rule(
    lines: list[str], corpus: str, in_scope: bool
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    if not in_scope:
        return warnings, RuleRead(
            rule_id="altitude-saturation",
            searched=["L_CARRY / NEXT_FLOOR (skipped: not in altitude scope)"],
            hits=[], corpus=corpus, decision="SKIP: out of scope",
        )
    found: dict[str, list[str]] = {"L_CARRY": [], "NEXT_FLOOR": []}
    for key, val in ALTITUDE_VALUE_RE.findall("\n".join(lines)):
        found[key].append(val)
    vals = {k: (v[0] if v else None) for k, v in found.items()}
    ambiguous = sorted(k for k, v in found.items() if len(set(v)) > 1)
    hits = [{"L_CARRY": vals["L_CARRY"], "NEXT_FLOOR": vals["NEXT_FLOOR"],
             "ceiling": ALTITUDE_CEILING,
             "occurrences": {k: v for k, v in found.items() if v},
             "ambiguous_fields": ambiguous}]
    if ambiguous:
        warnings.append(
            "altitude field(s) %s appear with more than one distinct value in this handoff "
            "(%s). A quoted predecessor block and this window's own value are indistinguishable "
            "to a reader and to this rule; the saturation verdict below is computed from the "
            "first occurrence and may describe the wrong window. Label which block is current."
            % (", ".join(ambiguous),
               "; ".join("%s=%s" % (k, "/".join(found[k])) for k in ambiguous))
        )
    saturated = (vals["L_CARRY"] == ALTITUDE_CEILING
                 and vals["NEXT_FLOOR"] == ALTITUDE_CEILING)
    if saturated:
        warnings.append(
            "altitude axis saturated: L_CARRY=NEXT_FLOOR=%s is the top of the closed set, so "
            "the window-altitude progress test `L_CARRY(n+1) > L_CARRY(n)` is false for every future window "
            "regardless of what this line actually achieves. Reaching the top may itself be the "
            "achievement — saturation is not a defect. Report this window's progress on an axis "
            "that still discriminates (which problem class became solvable, which methods "
            "composed), or say plainly that the window held position. "
            "MEASURES: the two field values only. DOES NOT MEASURE: whether this handoff "
            "actually cites the saturated axis as progress evidence — that is the failure this "
            "text is about, and it is not mechanically decidable here; a reader must judge it."
            % ALTITUDE_CEILING
        )
        decision = "WARN emitted: axis saturated at %s (both fields)" % ALTITUDE_CEILING
    elif vals["L_CARRY"] is None:
        anchorlike = any(re.search(r"\bL_CARRY\b[\s`*]*[=:：]", ln) for ln in lines)
        decision = ("no warning: L_CARRY token present in text but not parsable by "
                    "ALTITUDE_VALUE_RE — this is 'unread', NOT 'absent'"
                    if anchorlike else
                    "no warning: no L_CARRY field anywhere (genuinely absent)")
    else:
        decision = "no warning: L_CARRY=%s NEXT_FLOOR=%s — axis still discriminates" % (
            vals["L_CARRY"], vals["NEXT_FLOOR"])
    return warnings, RuleRead(
        rule_id="altitude-saturation",
        searched=[ALTITUDE_VALUE_RE.pattern, "ceiling=" + ALTITUDE_CEILING,
                  "multi-occurrence ambiguity reported, not silently first-wins"],
        hits=hits, corpus=corpus, decision=decision,
    )


PROGRESS_AXIS_LANDING_FLOOR = "20260921"
PROGRESS_AXIS_RE = re.compile(r"(?m)^[ \t]*PROGRESS_AXIS[ \t]*=[ \t]*(\S.*)$")
_PA_DATE_RE = re.compile(r"(20\d{6})")
_PA_FIELD_RE = re.compile(r"^[ \t]*[A-Z][A-Z0-9_]{3,}[ \t]*=")
_PA_CMD_HEAD = ("python3", "python", "git", "bash", "sh", "shasum", "sha256sum",
                "grep", "rg", "find", "ls", "cat", "make", "pytest", "jq", "awk", "sed")


def _pa_block(lines: list[str], idx: int) -> list[str]:
    out = [lines[idx]]
    for ln in lines[idx + 1:]:
        if not ln.strip():
            break
        if _PA_FIELD_RE.match(ln):
            break
        out.append(ln)
    return out


def _pa_has_recompute(block: list[str], base_dir) -> bool:
    for ln in block:
        t = ln.strip().lstrip("`$ ").strip()
        if not t:
            continue
        toks = [x.strip("'\"`,;:()（）") for x in t.replace("：", " ").split()]
        if not any(x.rsplit("/", 1)[-1] in _PA_CMD_HEAD for x in toks if x):
            continue
        if any(tok.startswith("~/") or (tok.startswith("/") and len(tok) > 1)
               for tok in toks if tok):
            return True
        for tok in toks:
            if tok and "/" in tok and (base_dir / tok).exists():
                return True
    return False


def progress_axis_rule(
    lines: list[str], corpus: str, in_scope: bool, path
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    rid = "progress-axis"
    if not in_scope:
        return warnings, RuleRead(
            rule_id=rid, searched=["PROGRESS_AXIS (skipped: not in altitude scope)"],
            hits=[], corpus=corpus, decision="SKIP: out of scope")
    m = _PA_DATE_RE.search(getattr(path, "name", "") or "")
    if not m or m.group(1) < PROGRESS_AXIS_LANDING_FLOOR:
        return warnings, RuleRead(
            rid, ["filename date vs LANDING_FLOOR=" + PROGRESS_AXIS_LANDING_FLOOR],
            [{"filename_date": m.group(1) if m else None}], corpus,
            "SKIP: below landing floor — 存量件不追溯（新义务的 MUST 落在主张强制力的一方）")
    found: dict[str, list[str]] = {"L_CARRY": [], "NEXT_FLOOR": []}
    for key, val in ALTITUDE_VALUE_RE.findall("\n".join(lines)):
        found[key].append(val)
    vals = {k: (v[0] if v else None) for k, v in found.items()}
    saturated = (vals["L_CARRY"] == ALTITUDE_CEILING
                 and vals["NEXT_FLOOR"] == ALTITUDE_CEILING)
    idxs = [i for i, ln in enumerate(lines) if PROGRESS_AXIS_RE.match(ln)]
    has_axis = bool(idxs)
    has_cmd = False
    base_dir = getattr(path, "parent", None)
    if has_axis and base_dir is not None:
        has_cmd = any(_pa_has_recompute(_pa_block(lines, i), base_dir) for i in idxs)
    hits = [{"saturated": saturated, "PROGRESS_AXIS_present": has_axis,
             "recompute_command_resolvable": has_cmd,
             "floor": PROGRESS_AXIS_LANDING_FLOOR}]
    if not saturated:
        decision = "no warning: axis not saturated — this rule only applies on saturation"
    elif not has_axis:
        warnings.append(
            "altitude axis is saturated and this handoff carries no PROGRESS_AXIS= section. "
            "The saturation rule's own prescription is 'report progress on an axis that still "
            "discriminates' — that prescription has no judge unless the replacement axis is "
            "written down. MEASURES: presence of a PROGRESS_AXIS= field and whether its block "
            "carries a resolvable recompute command. DOES NOT MEASURE: whether the replacement "
            "axis actually shows progress this window — not mechanically decidable.")
        decision = "WARN emitted: saturated without PROGRESS_AXIS"
    elif not has_cmd:
        warnings.append(
            "PROGRESS_AXIS= is present but its block carries no resolvable recompute command "
            "(first token in a known executable set AND an absolute or locally-resolvable path). "
            "An axis a reader cannot recompute is prose, not a measurement — the same failure the "
            "saturated altitude axis already has.")
        decision = "WARN emitted: PROGRESS_AXIS present but no resolvable recompute command"
    else:
        decision = "no warning: saturated, PROGRESS_AXIS present with a resolvable recompute command"
    return warnings, RuleRead(
        rid, [PROGRESS_AXIS_RE.pattern, "block = until blank line or next ALLCAPS= field",
              "recompute = known head token + absolute/locally-resolvable path",
              "LANDING_FLOOR=" + PROGRESS_AXIS_LANDING_FLOOR],
        hits, corpus, decision)


def unlanded_directions_rule(
    lines: list[str], base_dir: Path, corpus: str, in_scope: bool
) -> tuple[list[str], RuleRead]:
    warnings: list[str] = []
    hits: list[dict] = []
    present = any(re.search(r"\bUNLANDED_DIRECTIONS\s*[=:]", ln) for ln in lines)
    hits.append({"field": "UNLANDED_DIRECTIONS", "present": present})
    if not present:
        if in_scope:
            warnings.append(
                "no UNLANDED_DIRECTIONS field; directions raised but never landed live only "
                "in session transcripts and silently die (motivating failure: a long multi-window workstream)"
            )
        decision = (
            "WARN emitted: field absent in an in-scope handoff"
            if in_scope
            else "no warning: field absent, out of scope (a read, not a pass)"
        )
    else:
        inline, block = _field_block(lines, "UNLANDED_DIRECTIONS")
        entries = [e for e in block if not FIELD_RECORD_LINE_RE.match(e)]
        _coalesced = _coalesce_unlanded_entries(block)
        entries = _coalesced if _coalesced else entries
        has_record = any(_HONEST_SCOPE_RECORD_RE.search(ln) for ln in lines)
        hits.append({"inline": inline or "ABSENT", "entries": len(entries),
                     "honest_record": has_record})
        if not has_record:
            warnings.append(
                "UNLANDED_DIRECTIONS carries no honest retrieval record (Checked / Not "
                "checked, method §2 convention); a bare NONE is a silent disclaimer and a "
                "filled list without one overclaims the sweep"
            )
        if not ((inline or "").upper() == "NONE" and len(entries) <= 1):
            for entry in entries:
                if FIELD_RECORD_LINE_RE.match(entry):
                    continue
                m = _UNLANDED_ANCHOR_RE.search(entry)
                if not m:
                    warnings.append(
                        "UNLANDED_DIRECTIONS entry lacks a resolvable original-voice anchor "
                        "(<source-file> @ <YYYY-MM-DD[THH:MM[:SS]]>)"
                    )
                    hits.append({"entry": entry[:80], "anchor": "MISSING"})
                    continue
                raw_path, ts = m.group("file"), m.group("ts")
                target = _resolve_anchor_target(raw_path, base_dir)
                if target is None:
                    warnings.append(
                        f"UNLANDED_DIRECTIONS anchor source file not resolvable from this "
                        f"handoff: {raw_path} @ {ts}"
                    )
                    hits.append({"entry": entry[:80], "anchor": f"SOURCE-MISSING:{raw_path}"})
                    continue
                hits.append(
                    {"entry": entry[:80], "anchor": f"source-ok:{raw_path}@{ts or 'date-only'}"}
                )
                try:
                    content = target.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    content = ""
                for quote in _UNLANDED_QUOTE_RE.findall(entry):
                    escaped = json.dumps(quote, ensure_ascii=False)[1:-1]
                    if quote not in content and escaped not in content:
                        warnings.append(
                            f"UNLANDED_DIRECTIONS anchor quote not located in {target.name}: "
                            f"'{quote[:60]}' — verify or correct the anchor (best-effort check)"
                        )
                        hits.append(
                            {"entry": entry[:80], "anchor": f"QUOTE-MISSING:{quote[:40]}"}
                        )
        decision = (
            f"WARN emitted: {len(warnings)} unlanded finding(s)"
            if warnings
            else "no warning: entries anchored (or NONE with an honest record); absence "
                 "itself stays unverifiable"
        )
    read = RuleRead(
        rule_id="unlanded-directions",
        searched=[
            "UNLANDED_DIRECTIONS field block; anchor <source-file> @ <timestamp>",
            "quote-fragment containment in the anchor source file (best-effort)",
            "honest Checked/Not checked retrieval record (method §2 convention)",
        ],
        hits=hits,
        corpus=corpus,
        decision=decision,
    )
    return warnings, read


def lint(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    corpus = corpus_note(lines)
    errors: list[str] = []
    warnings: list[str] = []
    hints: list[str] = []
    err_by: list[str] = []
    warn_by: list[str] = []
    hint_by: list[str] = []

    def _take(out: list, by: list, msgs: list, rid: str) -> None:
        out.extend(msgs)
        by.extend([rid] * len(msgs))
    rule_reads: list[RuleRead] = []

    if not text.strip():
        _take(errors, err_by, ["handoff is empty"], "empty-document")
    rule_reads.append(
        RuleRead(
            rule_id="empty-document",
            searched=["non-whitespace content"],
            hits=[] if text.strip() else [{"line": 1, "col": 1, "match": "", "context": "empty"}],
            corpus=corpus,
            decision="ERROR emitted: document is empty" if not text.strip() else "no ERROR: content present",
        )
    )

    placeholder_errors, placeholder_read = placeholder_rule(lines, corpus)
    _take(errors, err_by, placeholder_errors, placeholder_read.rule_id)
    rule_reads.append(placeholder_read)

    secret_errors, secret_read = secret_rule(text, corpus)
    _take(errors, err_by, secret_errors, secret_read.rule_id)
    rule_reads.append(secret_read)

    scope_hits: list[dict] = []
    scope_present = False
    for pattern in UNSUPPORTED_SCOPE_CLAIMS:
        rx = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for line_no, line in enumerate(lines):
            m = rx.search(line)
            if m:
                scope_present = True
                scope_hits.append(_hit(line_no, m.start(), m.group(0)[:80], f"/{pattern}/"))
    if scope_present:
        _take(warnings, warn_by,
              ["possible unsupported exhaustive-history claim; state the actually accessible scope"],
              "unsupported-scope-claim")
    rule_reads.append(
        RuleRead(
            rule_id="unsupported-scope-claim",
            searched=[f"/{p}/i" for p in UNSUPPORTED_SCOPE_CLAIMS],
            hits=scope_hits,
            corpus=corpus,
            decision="WARN emitted" if scope_present else "no WARN: no hits found (searched, not seen)",
        )
    )

    dimension_presence: dict[str, bool] = {}
    for name, patterns in DIMENSION_HINTS.items():
        dim_warnings, dim_read = keyword_rule(
            f"dimension-{name}",
            [f"/{p}/i" for p in patterns],
            patterns,
            lines,
            corpus,
            warn_if_absent=True,
            warning=f"no obvious signal for dimension '{name}'; review manually if it matters for this task",
        )
        dimension_presence[name] = bool(dim_read.hits)
        _take(hints, hint_by, dim_warnings, dim_read.rule_id)
        rule_reads.append(dim_read)

    boundary_warnings, boundary_read = keyword_rule(
        "boundary-signal",
        ["允许/禁止/边界/allowed/not allowed/boundary keyword"],
        [r"允许", r"禁止", r"边界", r"allowed", r"not allowed", r"boundary"],
        lines,
        corpus,
        warn_if_absent=True,
        warning="no obvious task boundary signal",
    )
    _take(hints, hint_by, boundary_warnings, boundary_read.rule_id)
    rule_reads.append(boundary_read)

    materials_warnings, materials_read = keyword_rule(
        "required-materials",
        ["必传/必须读取/required files/required materials/upload keyword"],
        [r"必传", r"必须读取", r"required files", r"required materials", r"upload"],
        lines,
        corpus,
        warn_if_absent=True,
        warning="no obvious required-materials or upload guidance",
    )
    _take(hints, hint_by, materials_warnings, materials_read.rule_id)
    rule_reads.append(materials_read)

    opening_warnings, opening_read = keyword_rule(
        "receiver-opening",
        ["新 session 开场/copyable/opening prompt/接收端首屏/TO_NEW_SESSION/receiver mode/RECEIVER_MODE/接收方"],
        [
            r"新 session 开场", r"copyable", r"opening prompt", r"接收端首屏",
            r"TO_NEW_SESSION", r"receiver mode", r"RECEIVER_MODE", r"接收方",
        ],
        lines,
        corpus,
        warn_if_absent=True,
        warning="no obvious receiver opening or immediate brief",
    )
    _take(hints, hint_by, opening_warnings, opening_read.rule_id)
    rule_reads.append(opening_read)

    hold_patterns = [r"(?<![A-Za-z])HOLD(?![A-Za-z])", r"AWAIT_USER", r"NOT_AUTHORIZED", r"未授权", r"待命"]
    cleared_patterns = [
        r"cleared first action", r"start now", r"立即执行", r"无需再授权",
        r"EXECUTE_FIRST_ACTION", r"RECEIVER_MODE", r"receiver mode", r"FIRST_ACTION", r"首动作",
    ]
    freeze_warnings, freeze_read = keyword_rule(
        "receiver-freeze",
        ["HOLD signals"] + hold_patterns + ["cleared-action signals"] + cleared_patterns,
        hold_patterns,
        lines,
        corpus,
        warn_if_absent=False,
        warning="",
    )
    hold_present = bool(freeze_read.hits)
    cleared_warnings, cleared_read = keyword_rule(
        "receiver-cleared-action",
        ["cleared first action / receiver mode signals"],
        cleared_patterns,
        lines,
        corpus,
        warn_if_absent=False,
        warning="",
    )
    cleared_present = bool(cleared_read.hits)
    if hold_present and not cleared_present:
        freeze_warnings.append(
            "possible receiver-freeze: HOLD/await-authorization signal present without an explicit "
            "cleared first action or receiver mode; a not-yet-authorized next gate must not freeze the receiver"
        )
        freeze_read.decision = "WARN emitted: HOLD present, no cleared-action signal (searched, not seen)"
    elif hold_present:
        freeze_read.decision = f"no warning: HOLD present ({len(freeze_read.hits)} hit(s)) and cleared-action present ({len(cleared_read.hits)} hit(s))"
    else:
        freeze_read.decision = "no warning: no HOLD/await signal (searched, not seen)"
    _take(warnings, warn_by, freeze_warnings, freeze_read.rule_id)
    rule_reads.append(freeze_read)
    rule_reads.append(cleared_read)

    kernel_signals = [
        ("workstream", [r"WORKSTREAM_OR_PROJECT", r"workstream", r"项目\s*/\s*任务线", r"project / workstream"]),
        ("position", [r"CURRENT_POSITION", r"CURRENT_NODE", r"current node", r"当前节点"]),
        ("authoritative-state", [r"CURRENT_AUTHORITATIVE_STATE", r"\bSOT\b", r"authoritative state", r"当前权威"]),
        ("cleared-first-action", [r"CLEARED_FIRST_ACTION", r"cleared first action", r"第一允许动作", r"首动作"]),
        ("next-gate", [r"NEXT_GATE", r"next-gate", r"next gate", r"下一门槛"]),
    ]
    kernel_hits = 0
    kernel_hits_total = 0
    for _name, group in kernel_signals:
        _w, group_read = keyword_rule(
            "continuity-kernel", [f"/{p}/i" for p in group], group, lines, corpus,
            warn_if_absent=False, warning="",
        )
        kernel_hits += 1 if group_read.hits else 0
        kernel_hits_total += len(group_read.hits)
    if kernel_hits < len(kernel_signals):
        _take(hints, hint_by, [
            f"continuity-kernel signals incomplete ({kernel_hits}/{len(kernel_signals)}); an actionable "
            "handoff should surface workstream, current position, authoritative state/SOT, cleared first "
            "action, and next gate up front (field names may adapt)"
        ], "continuity-kernel")
    rule_reads.append(
        RuleRead(
            rule_id="continuity-kernel",
            searched=[f"{name}: {[f'/{p}/i' for p in group]}" for name, group in kernel_signals],
            hits=[{"signal_groups_hit": kernel_hits, "signal_groups_total": len(kernel_signals),
                    "keyword_hits_total": kernel_hits_total}],
            corpus=corpus,
            decision=(
                f"WARN emitted: {kernel_hits}/{len(kernel_signals)} signal groups found"
                if kernel_hits < len(kernel_signals)
                else f"no warning: all {len(kernel_signals)} signal groups found"
            ),
        )
    )

    receipt_warnings, receipt_read = keyword_rule(
        "receipt-delivery",
        [f"/{p}/i" for p in RECEIPT_DUTY_SIGNALS],
        RECEIPT_DUTY_SIGNALS,
        lines,
        corpus,
        warn_if_absent=True,
        warning=(
            "no receipt-delivery instruction; the receiving session reads only this handoff, so the "
            "opening must tell it to write a separate Receiver Outcome Receipt and where to put it"
        ),
    )
    _take(warnings, warn_by, receipt_warnings, receipt_read.rule_id)
    rule_reads.append(receipt_read)

    for key, allowed in ENUM_CLOSED_SETS.items():
        enum_warnings, enum_read = enum_rule(lines, key, allowed, corpus)
        _take(warnings, warn_by, enum_warnings, enum_read.rule_id)
        rule_reads.append(enum_read)

    altitude_in_scope, scope_read = altitude_scope_rule(lines, corpus)
    rule_reads.append(scope_read)
    altitude_warnings, altitude_read = altitude_fields_rule(
        lines, path.parent, corpus, altitude_in_scope
    )
    _take(warnings, warn_by, altitude_warnings, altitude_read.rule_id)
    rule_reads.append(altitude_read)
    index_warnings, index_read = landed_index_rule(lines, corpus, altitude_in_scope)
    _take(warnings, warn_by, index_warnings, index_read.rule_id)
    rule_reads.append(index_read)
    volatile_warnings, volatile_read = volatile_enumeration_rule(lines, corpus)
    _take(warnings, warn_by, volatile_warnings, volatile_read.rule_id)
    rule_reads.append(volatile_read)
    unlanded_warnings, unlanded_read = unlanded_directions_rule(
        lines, path.parent, corpus, altitude_in_scope
    )
    _take(warnings, warn_by, unlanded_warnings, unlanded_read.rule_id)
    rule_reads.append(unlanded_read)
    concretization_warnings, concretization_read = concretization_rate_rule(
        lines, corpus, altitude_in_scope, base_dir=path.parent
    )
    _take(warnings, warn_by, concretization_warnings, concretization_read.rule_id)
    rule_reads.append(concretization_read)
    state_warnings, state_read = state_anchor_rate_rule(lines, corpus)
    _take(warnings, warn_by, state_warnings, state_read.rule_id)
    rule_reads.append(state_read)

    saturation_warnings, saturation_read = altitude_saturation_rule(
        lines, corpus, altitude_in_scope
    )
    _take(warnings, warn_by, saturation_warnings, saturation_read.rule_id)
    rule_reads.append(saturation_read)

    progress_warnings, progress_read = progress_axis_rule(
        lines, corpus, altitude_in_scope, path
    )
    _take(warnings, warn_by, progress_warnings, progress_read.rule_id)
    rule_reads.append(progress_read)

    recursion_warnings, recursion_read = method_recursion_rule(lines, corpus)
    _take(warnings, warn_by, recursion_warnings, recursion_read.rule_id)
    rule_reads.append(recursion_read)

    landing_warnings, landing_read = method_increment_landing_rule(lines, corpus, path)
    _take(warnings, warn_by, landing_warnings, landing_read.rule_id)
    rule_reads.append(landing_read)

    kernel_warnings, kernel_read = evolution_kernel_rule(lines, corpus, path)
    _take(warnings, warn_by, kernel_warnings, kernel_read.rule_id)
    rule_reads.append(kernel_read)

    crossref_warnings, crossref_read = cross_ref_path_rule(lines, corpus)
    _take(warnings, warn_by, crossref_warnings, crossref_read.rule_id)
    rule_reads.append(crossref_read)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    status = "FAIL" if errors else ("WARN" if warnings else "CLEAN")
    return {
        "status": status,
        "path": str(path),
        "sha256": digest,
        "bytes": len(text.encode("utf-8")),
        "dimension_hints": dimension_presence,
        "errors": errors,
        "warnings": warnings,
        "hints": hints,
        "rule_reads": [r.to_dict() for r in rule_reads],
        "attribution": {"errors": err_by, "warnings": warn_by, "hints": hint_by},
        "note": "Advisory lint only; semantic receiver readiness requires model/human review.",
    }


def _print_read(read: dict) -> None:
    hits = read["hits"]
    print(f"READ [{read['rule_id']}] corpus: {read['corpus']}")
    print(f"  searched: {'; '.join(read['searched'])}")
    print(f"  hits: {len(hits)}")
    for h in hits[:12]:
        if "line" in h:
            print(f"    L{h['line']}:{h['col']} {h['context']}: {h['match']}")
        else:
            print(f"    {h}")
    if len(hits) > 12:
        print(f"    … {len(hits) - 12} more (see --json)")
    print(f"  decision: {read['decision']}")


def corpus_scan(globs: list[str]) -> dict[str, object]:
    import collections
    seen: set[str] = set()
    files: list[Path] = []
    for g in globs:
        for raw in sorted(glob.glob(os.path.expanduser(g), recursive=True)):
            f = Path(raw)
            if not f.is_file():
                continue
            key = str(f.resolve())
            if key in seen:
                continue
            seen.add(key)
            files.append(f)
    tiers = {"errors": collections.Counter(), "warnings": collections.Counter(),
             "hints": collections.Counter()}
    status = collections.Counter()
    for f in files:
        try:
            r = lint(f)
        except Exception:
            status["UNREADABLE"] += 1
            continue
        status[str(r["status"])] += 1
        for tier in ("errors", "warnings", "hints"):
            msgs, by = r.get(tier, []), r.get("attribution", {}).get(tier, [])
            if len(msgs) != len(by):
                tiers[tier]["ATTRIBUTION_LENGTH_MISMATCH"] += len(msgs)
                continue
            for rid in by:
                tiers[tier][rid] += 1
    truth = 0
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        d: dict[str, str] = {}
        for k, v in ALTITUDE_VALUE_RE.findall(txt):
            d.setdefault(k, v)
        if d.get("L_CARRY") == ALTITUDE_CEILING and d.get("NEXT_FLOOR") == ALTITUDE_CEILING:
            truth += 1
    hit = tiers["warnings"].get("altitude-saturation", 0)
    recall = {
        "rule": "altitude-saturation",
        "ground_truth_parse": ALTITUDE_VALUE_RE.pattern,
        "truly_saturated": truth,
        "reported": hit,
        "recall": "NOT_COMPUTABLE",
        "recall_withdrawn_because": "ground truth and rule share ALTITUDE_VALUE_RE; "
                                    "objects in the parser's blind spot vanish from the "
                                    "denominator, so the ratio cannot fall below 100% "
                                    "for a structural reason, not an empirical one",
        "same_parser_consistency": (f"{hit}/{truth}" if truth else "n/a"),
        "note": "召回只对存在**独立于被测规则**的真值面的规则可算。本规则不具备该面，"
                "故报 NOT_COMPUTABLE；same_parser_consistency 只是共同解析域内的自洽度，"
                "既不是召回率也不是覆盖率。要真召回须由外部提供预先标注的对象清单。",
    }
    return {
        "recall": recall,
        "recall_other_rules": "NOT_COMPUTABLE（无独立真值面）",
        "universe": globs,
        "universe_note": "按 realpath 去重；符号链接可达的同一物理文件只计一次",
        "enumerator": "python glob.glob(recursive=True) + realpath 去重；"
                      "穿符号链接（与 find -P 行为不同）；不套 .gitignore（与会套 .gitignore 的 grep 包装不同）",
        "enumerator_blind_spots": "不含未被 glob 模式覆盖的路径；不含权限不可读目录；"
                                  "不含非 HANDOFF* 命名的交接件",
        "files": len(files),
        "status": dict(status),
        "by_tier": {k: dict(v.most_common()) for k, v in tiers.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path, nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--corpus", action="append", metavar="GLOB",
        help="扫一批真语料并按 rule 报触发率（退役判据 T3 的观测面）。可重复。"
             "输出为退役**候选**，不是判决 —— 触发率 0 可能意味着该条款已被内化。",
    )
    args = parser.parse_args()

    if args.corpus:
        summary = corpus_scan(args.corpus)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print("CORPUS universe=%s files=%d status=%s"
                  % (summary["universe"], summary["files"], summary["status"]))
            rc = summary["recall"]
            print("RECALL %s = %s（⚠️ 真值面与被测规则**共用同一解析器**，故非独立召回；"
                  "该值只是共同解析域内的一致性读数。其余规则 %s）"
                  % (rc["rule"], rc["recall"], summary["recall_other_rules"]))
            print("ENUMERATOR %s" % summary["enumerator"])
            for tier in ("errors", "warnings", "hints"):
                rows = summary["by_tier"][tier]
                print("── %s ── (%d 条)" % (tier.upper(), sum(rows.values())))
                for k, v in rows.items():
                    print("  %5d  %s" % (v, k))
            print("ℹ️ 触发率 0 的规则**不会出现在上表**——缺席即 T3 退役候选，须对照规则全集读。")
            print("🔴 输出是退役**候选**，不是判决：触发率 0 可能意味着该条款已被内化"
                  "（零引用≠该退役）。退役须用户裁。")
        return 0

    if args.handoff is None:
        print("ERROR: 需要一个 handoff 路径，或用 --corpus <glob>", file=sys.stderr)
        return 2

    if not args.handoff.is_file():
        result = {"status": "FAIL", "errors": ["file not found"], "path": str(args.handoff)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    result = lint(args.handoff)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']}: {result['path']}")
        print(f"SHA256: {result['sha256']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        for hint in result.get("hints", []):
            print(f"HINT: {hint}")
        for read in result["rule_reads"]:
            _print_read(read)
        print(result["note"])

    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
