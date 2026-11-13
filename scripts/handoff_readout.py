#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
TRANSCRIPT_ROOTS: list = []


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LD = _load("lesson_detectors")
LP = _load("lesson_patterns")

SWITCH = re.compile(r'切窗|落盘\s*handoff|落\s*handoff|写交接|落盘交接|冷启动词|启动词|写\s*handoff|生成\s*handoff', re.I)
RESTATE = re.compile(r'我说过|说了很多次|说过很多|提醒过|讲过|还是那句话|之前.{0,6}(提|说|讲|告知)过|不再重复|反复提醒|我已经.{0,8}告知|多次提及|多次和你')
HANDOFF_NAME = re.compile(r'HANDOFF_[A-Za-z0-9_.\-]+?\.md(?![.\w])')
BODY_HEADS = ("cat", "sed", "head", "tail", "awk", "nl", "less", "more")
E3B_MIN_OPP = 20
NOT_HUMAN_PREFIX = ('<local-command', '<command-name>', '<system-reminder>', '<task-notification', '<bash-', 'Caveat:')


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot(path: Path, n: "int | None"):
    raw = path.read_bytes().split(b"\n")
    complete = raw[:-1]
    n = len(complete) if n is None else min(n, len(complete))
    body = b"".join(x + b"\n" for x in complete[:n])
    recs = []
    for x in complete[:n]:
        try:
            recs.append(json.loads(x))
        except Exception:
            continue
    return n, hashlib.sha256(body).hexdigest(), recs


class Window:
    def __init__(self, recs):
        self.first = next((r.get("timestamp") for r in recs if r.get("timestamp")), "")
        self.as_of = ""
        self.tools = []
        self.recs = []
        self.humans = []
        self.start = ""
        self.cwd_moves = []
        self.env_seen = False
        for r in recs:
            if r.get("timestamp"):
                self.as_of = r["timestamp"]
            side = bool(r.get("isSidechain"))
            at = r.get("attachment") or {}
            if r.get("type") == "attachment" and not side and at.get("type") == "environment":
                wd = (at.get("snapshot") or {}).get("workingDirectory") or ""
                ch = [c for c in at.get("changes") or [] if c.get("field") == "workingDirectory"]
                if not self.env_seen:
                    self.start = (ch[0].get("from") if ch else wd) or wd
                self.env_seen = True
                if ch and wd:
                    self.cwd_moves.append(wd)
            t = r.get("type")
            if t == "assistant" and not side:
                m = r.get("message") or {}
                tus = [b for b in (m.get("content") or []) if isinstance(b, dict) and b.get("type") == "tool_use"]
                self.recs.append((m.get("id"), (m.get("usage") or {}).get("output_tokens") or 0,
                                  [(b.get("name"), json.dumps(b.get("input"), ensure_ascii=False)) for b in tus]))
                for b in tus:
                    self.tools.append((r.get("timestamp") or "", b.get("name"), b.get("input") or {}))
            elif t == "user" and not side and not r.get("isMeta"):
                c = (r.get("message") or {}).get("content")
                if isinstance(c, str):
                    txt, tr = c, False
                else:
                    txt, tr = "", False
                    for b in c or []:
                        if isinstance(b, dict) and b.get("type") == "text":
                            txt += b.get("text") or ""
                        elif isinstance(b, dict) and b.get("type") == "tool_result":
                            tr = True
                if not tr and txt and not txt.lstrip().startswith(NOT_HUMAN_PREFIX):
                    self.humans.append((r.get("timestamp") or "", txt))
        self.bash = [i.get("command") or "" for _ts, nm, i in self.tools if nm == "Bash"]


def pattern_counts(win: Window, pats):
    out = {}
    for p in pats:
        if p["id"] in LD.WINDOW_DETECTORS:
            o, v = LD.WINDOW_DETECTORS[p["id"]](win)
            out[p["id"]] = (v, o)
            continue
        f = LD.DETECTORS[p["id"]]
        o = v = 0
        for c in win.bash:
            a, b = f(c)
            o += a; v += b
        out[p["id"]] = (v, o)
    return out


def canary_hit(pid, case) -> bool:
    if pid in LD.WINDOW_DETECTORS:
        w = SimpleNamespace(start=case["start"], cwd_moves=list(case["moves"]), bash=["true"])
        return LD.WINDOW_DETECTORS[pid](w)[1] > 0
    return LD.DETECTORS[pid](case)[1] > 0


def validity(lp):
    for fn, want in lp.DETECTOR_SHA.items():
        f = Path(fn) if fn.startswith("/") else HERE / fn
        got = sha256_file(f) if f.is_file() else "missing"
        if got != want:
            return "sha:" + Path(fn).name
    for p in lp.PATTERNS:
        if p["id"] not in LD.DETECTORS and p["id"] not in LD.WINDOW_DETECTORS:
            return "detector:" + p["id"]
        for case, exp in p["canary"]:
            if canary_hit(p["id"], case) != exp:
                return "canary:" + p["id"]
    return None


def receive(win: Window):
    hs = win.humans[:3]
    name = None; hts = None
    for ts, txt in hs:
        m = HANDOFF_NAME.search(txt)
        if m:
            name, hts = m.group(0), ts; break
    if not name:
        return "handoff=NONE"
    after = [(nm, i) for ts, nm, i in win.tools if ts >= hts][:3]
    touch = body = None
    for k, (nm, i) in enumerate(after):
        s = json.dumps(i, ensure_ascii=False)
        if touch is None and ((nm == "Read" and name in str(i.get("file_path"))) or (nm == "Bash" and name in s)):
            touch = k
        if body is None:
            if nm == "Read" and name in str(i.get("file_path")):
                body = k
            elif nm == "Bash":
                for _k, _sep, _seg, stages in LD._walk(i.get("command") or ""):
                    if any(LD._base(t[0]) in BODY_HEADS and any(name in a for a in t[1:]) for t in stages):
                        body = k; break
    f = lambda x: "0" if x is None else "1@%d" % x
    return "handoff=%s touch=%s body=%s (前3调)" % (name, f(touch), f(body))


def human(win: Window):
    short = [t for _ts, t in win.humans if len(t) <= 600]
    sw = "有" if any(SWITCH.search(t) for t in short) else "无"
    return "switch=%s restate=%d/%d" % (sw, sum(1 for t in short if RESTATE.search(t)), len(win.humans))


def _is_handoff_skill(s: str) -> bool:
    try:
        k = str(json.loads(s).get("skill") or "")
    except Exception:
        return False
    return k == "session-handoff" or k.endswith(":session-handoff")


def cost(win: Window, names):
    start = end = None
    for i, (_mid, _ot, tus) in enumerate(win.recs):
        for n, s in tus:
            if start is None and ((n == "Skill" and _is_handoff_skill(s)) or (n == "Write" and any(x in s for x in names))):
                start = i
            if start is not None and (any(x in s for x in names) or "lint_handoff" in s or "cold-read" in s or "冷读" in s):
                end = i
    if start is None or end is None:
        return "segment=NONE"

    def tok(seg):
        seen = {}
        for mid, ot, _tus in seg:
            seen[mid] = max(seen.get(mid, 0), ot)
        return sum(seen.values())
    seg = win.recs[start:end + 1]
    tt, ht = tok(win.recs), tok(seg)
    return "tok_share=%.3f seg_tok=%d all_tok=%d seg_tools=%d" % (
        ht / max(1, tt), ht, tt, sum(len(x[2]) for x in seg))


def size(handoff: "Path | None"):
    if handoff is None or not handoff.is_file():
        return "handoff=NONE"
    lines = handoff.read_text(encoding="utf-8", errors="replace").split("\n")
    is_blk = lambda ln: ln.strip().startswith(("READOUT_", "PROGRESS_AXIS="))
    is_fence = lambda ln: ln.strip().startswith("```")
    drop, i, n = set(), 0, len(lines)
    while i < n:
        if not is_blk(lines[i]):
            i += 1; continue
        lo = hi = i; j = i + 1
        while j < n and (is_blk(lines[j]) or is_fence(lines[j]) or not lines[j].strip()):
            if is_blk(lines[j]):
                hi = j
            j += 1
        seg = {k for k in range(lo, hi + 1) if is_blk(lines[k]) or is_fence(lines[k])}
        inner = [k for k in seg if is_fence(lines[k])]
        if len(inner) % 2 == 1 and hi + 1 < n and lines[hi + 1].strip() == "```":
            seg.add(hi + 1)
        elif not inner and lo > 0 and hi + 1 < n and is_fence(lines[lo - 1]) and lines[hi + 1].strip() == "```":
            seg |= {lo - 1, hi + 1}
        drop |= seg; i = hi + 1
    t = "\n".join(ln for k, ln in enumerate(lines) if k not in drop)
    t = re.sub(r"\n[ \t]*(?:\n[ \t]*)+\n", "\n\n", t).strip("\n") + "\n"
    op = re.search(r'给接收方的开场.*?\n```[a-z]*\n(.*?)\n```', t, re.S)
    m = re.search(r'(?:^|\n)(?:#{1,3}\s*)?EVOLUTION_KERNEL[^\n]*\n(.*?)(?=\n#{1,3} |\Z)', t, re.S)
    kc = 0
    if m:
        parts = re.split(r'^\s*(K\d+)\s+', m.group(1), flags=re.M)
        kc = sum(len(re.sub(r'\s+', ' ', parts[i + 1].split('\n```')[0]).strip()) for i in range(1, len(parts) - 1, 2))
    return "handoff=%d opening=%s kernel=%d text_sha=%s" % (
        len(t), len(op.group(1)) if op else "NONE", kc, hashlib.sha256(t.encode("utf-8")).hexdigest()[:12])


def written_handoffs(win: Window):
    return sorted({Path(i.get("file_path")).name for _ts, nm, i in win.tools
                   if nm == "Write" and re.search(r'/HANDOFF_[^/]*\.md$', str(i.get("file_path"))) and "/receipts/" not in str(i.get("file_path"))})


def find_own_session(handoff: Path) -> "Path | None":
    roots = [Path(x) for x in os.environ.get("HANDOFF_TRANSCRIPT_ROOT", "").split(os.pathsep) if x] or TRANSCRIPT_ROOTS
    best = None
    now = time.time()
    for p in (q for r in roots for q in r.glob("*/*.jsonl")):
        try:
            if now - p.stat().st_mtime > 3 * 86400:
                continue
            fh = open(p, errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if handoff.name not in line or '"Write"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") != "assistant" or o.get("isSidechain"):
                    continue
                for b in (o.get("message") or {}).get("content") or []:
                    if (isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Write"
                            and (b.get("input") or {}).get("file_path") == str(handoff)):
                        ts = o.get("timestamp") or ""
                        key = (ts, _line_count(p))
                        if best is None or key > best[0]:
                            best = (key, p)
    return best[1] if best else None


def _line_count(p: Path) -> int:
    with open(p, "rb") as fh:
        return sum(1 for _ in fh)


def pick_prior(session: Path, first: str, k: int = 5):
    cands = []
    for p in session.parent.glob("*.jsonl"):
        if p == session:
            continue
        ft = ""
        try:
            with open(p, errors="replace") as fh:
                for i, line in enumerate(fh):
                    if i > 200:
                        break
                    try:
                        ft = json.loads(line).get("timestamp") or ""
                    except Exception:
                        continue
                    if ft:
                        break
        except OSError:
            continue
        if ft and ft < first:
            cands.append((ft, p))
    out = []
    for ft, p in sorted(cands, reverse=True):
        n, _sha, recs = snapshot(p, None)
        if len(Window(recs).bash) >= 15:
            out.append((p, n))
        if len(out) == k:
            break
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="handoff progress-axis readout (round 2)")
    ap.add_argument("--session", required=True, help="会话 jsonl 绝对路径，或 auto（需 --handoff）")
    ap.add_argument("--n", type=int, default=None, help="截断行数（默认 = 当前完整行数）")
    ap.add_argument("--handoff", default=None, help="本窗交接件绝对路径")
    ap.add_argument("--prior", default=None, help="前五窗钉住：path:n,path:n,…（默认自动选取并钉当前行数）")
    a = ap.parse_args(argv)
    handoff = Path(a.handoff).expanduser().resolve() if a.handoff else None
    if a.session == "auto":
        if handoff is None:
            print("READOUT_SNAPSHOT ERROR --session auto requires --handoff"); return 2
        s = find_own_session(handoff)
        if s is None:
            print("READOUT_SNAPSHOT ERROR no session with a main-line Write to %s in the last 3 days "
                  "(pass --session, or set HANDOFF_TRANSCRIPT_ROOT)" % handoff); return 2
        session = s
    else:
        session = Path(a.session).expanduser().resolve()
    n, sha, recs = snapshot(session, a.n)
    win = Window(recs)
    if not win.first:
        print("READOUT_SNAPSHOT path=%s n=%d sha256=%s AS_OF=NONE UNSUPPORTED (no supported transcript records)" % (session, n, sha))
        return 2
    tool = "%s/%s" % (sha256_file(Path(__file__).resolve())[:12], sha256_file(HERE / "lesson_patterns.py")[:12])
    print("READOUT_SNAPSHOT path=%s n=%d sha256=%s AS_OF=%s tool=%s" % (session, n, sha, win.as_of, tool))
    if a.prior:
        prior = [(Path(x.rsplit(":", 1)[0]), int(x.rsplit(":", 1)[1])) for x in a.prior.split(",") if x]
    else:
        prior = pick_prior(session, win.first)
    bad = validity(LP)
    pats = [] if bad else list(LP.PATTERNS)
    cur = pattern_counts(win, pats)
    prior_counts = [pattern_counts(Window(snapshot(p, pn)[2]), pats) for p, pn in prior]
    if not LP.PATTERNS:
        print("READOUT_PATTERNS 无登记模式（本安装未带教训模式表）")
        print("READOUT_E3 无登记模式")
    elif bad:
        print("READOUT_PATTERNS 未过效度门（%s）—— 全部模式不出数" % bad)
        print("READOUT_E3 未过效度门")
    else:
        items = []
        for p in pats:
            v, o = cur[p["id"]]
            V = sum(pc[p["id"]][0] for pc in prior_counts); O = sum(pc[p["id"]][1] for pc in prior_counts)
            items.append("%s %d/%d（前%d %d/%d）" % (p["short"], v, o, len(prior), V, O))
        print("READOUT_PATTERNS " + " · ".join(items[:3]))
        print("READOUT_PATTERNS " + " · ".join(items[3:]))
        z5 = untested = 0
        for p in pats:
            five = [cur[p["id"]]] + [pc[p["id"]] for pc in prior_counts[:4]]
            if len(five) < 5 or sum(o for _v, o in five) < E3B_MIN_OPP:
                untested += 1
            elif all(v == 0 for v, _o in five):
                z5 += 1
        print("READOUT_E3 E3b 连续5窗为零=%d/%d · 未测=%d（五窗机会 <%d）（不判机制在位）" % (z5, len(pats), untested, E3B_MIN_OPP))
    print("READOUT_RECEIVE " + receive(win))
    print("READOUT_HUMAN " + human(win))
    names = written_handoffs(win)
    if handoff is not None and handoff.name not in names:
        names.append(handoff.name)
    print("READOUT_COST " + cost(win, names))
    print("READOUT_SIZE " + size(handoff))
    pin = ",".join("%s:%d" % (p, pn) for p, pn in prior)
    print("READOUT_RECOMPUTE python3 %s --session %s --n %d%s --prior %s" % (
        Path(__file__).resolve(), session, n, (" --handoff %s" % handoff) if handoff else "", pin or ","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
