from __future__ import annotations

import re
import shlex

SHARED_BASENAMES: tuple = ()

PREFIX = ("then", "do", "else", "elif", "command", "builtin", "time", "nohup", "exec", "!", "{")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
VAR = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def split_segments(cmd: str) -> list[tuple[str, str]]:
    out, buf, quote, esc, i = [], [], None, False, 0
    while i < len(cmd):
        c = cmd[i]
        if esc:
            buf.append(c); esc = False; i += 1; continue
        if c == "\\" and quote != "'":
            buf.append(c); esc = True; i += 1; continue
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            i += 1; continue
        if c in "'\"":
            quote = c; buf.append(c); i += 1; continue
        two = cmd[i:i + 2]
        if two in ("&&", "||"):
            out.append(("".join(buf), two)); buf = []; i += 2; continue
        if c in ";\n":
            out.append(("".join(buf), c)); buf = []; i += 1; continue
        buf.append(c); i += 1
    out.append(("".join(buf), ""))
    return out


def split_pipeline(seg: str) -> list[str]:
    out, buf, quote, esc = [], [], None, False
    for c in seg:
        if esc:
            buf.append(c); esc = False; continue
        if c == "\\" and quote != "'":
            buf.append(c); esc = True; continue
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            continue
        if c in "'\"":
            quote = c; buf.append(c); continue
        if c == "|":
            out.append("".join(buf)); buf = []; continue
        buf.append(c)
    out.append("".join(buf))
    return out


def stage_tokens(stage: str, env: dict) -> list[str]:
    try:
        tok = shlex.split(stage, posix=True)
    except ValueError:
        return []
    tok = [t.lstrip("(").rstrip(")") if t not in ("(", ")") else "" for t in tok]
    tok = [t for t in tok if t]
    while tok and (tok[0] in PREFIX or ASSIGN.match(tok[0])):
        if ASSIGN.match(tok[0]):
            k, v = tok[0].split("=", 1)
            env[k] = VAR.sub(lambda m: env.get(m.group(1), m.group(0)), v)
        tok = tok[1:]
    return [VAR.sub(lambda m: env.get(m.group(1), m.group(0)), t) for t in tok]


_HEREDOC_OP = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def strip_heredocs(cmd: str) -> str:
    out, pending = [], []
    for line in cmd.split("\n"):
        if pending:
            d, dash = pending[0]
            if (line.lstrip("\t") if dash else line) == d:
                pending.pop(0)
            continue
        out.append(line)
        for m in _HEREDOC_OP.finditer(line):
            pending.append((m.group(3), bool(m.group(1))))
    return "\n".join(out)


def _walk(cmd: str):
    env: dict = {}
    for k, (seg, sep) in enumerate(split_segments(strip_heredocs(cmd))):
        stages = [stage_tokens(s, env) for s in split_pipeline(seg)]
        yield k, sep, seg, [s for s in stages if s]


def _base(t: str) -> str:
    return t.rsplit("/", 1)[-1]


TMP_ROOTS = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")


def cwd_allowed(d: str, start: str) -> bool:
    return d == start or (d + "/").startswith(TMP_ROOTS)


def cwd_escape(win) -> tuple[int, int]:
    if not getattr(win, "env_seen", True) or not win.start:
        return 0, 0
    return len(win.bash), sum(1 for d in win.cwd_moves if not cwd_allowed(d, win.start))


_COUNT_FLAG = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$")


def bare_grep_count(cmd: str) -> tuple[int, int]:
    o = v = 0
    for _k, _sep, _seg, stages in _walk(cmd):
        for tok in stages:
            if _base(tok[0]) not in ("grep", "egrep", "fgrep"):
                continue
            if any(_COUNT_FLAG.match(t) or t == "--count" for t in tok[1:]):
                o += 1
                v += int("/" not in tok[0])
    return o, v


def delete_in_command(cmd: str) -> tuple[int, int]:
    hit = False
    for _k, _sep, _seg, stages in _walk(cmd):
        for tok in stages:
            h = _base(tok[0])
            if h in ("rm", "rmdir", "unlink"):
                hit = True
            elif h == "xargs" and any(_base(t) == "rm" for t in tok[1:] if not t.startswith("-")):
                hit = True
            elif h == "find" and "-delete" in tok:
                hit = True
            elif h == "find" and "-exec" in tok and _base((tok[tok.index("-exec") + 1:] or [""])[0]) == "rm":
                hit = True
    return 1, int(hit)


_EXIT_READ = re.compile(r"\$\?|\$\{\?\}")
FILTERS = ("tail", "head", "grep", "egrep", "fgrep", "tee", "cut", "sed", "awk", "sort", "uniq", "wc", "tr", "less", "more", "cat")


def pipe_filter_swallowed(cmd: str) -> tuple[int, int]:
    if re.search(r"pipefail|pipestatus|PIPESTATUS", cmd):
        return 0, 0
    o = v = 0
    prev = None
    for _k, sep, seg, stages in _walk(cmd):
        is_commit = any(len(t) > 1 and _base(t[0]) == "git" and "commit" in t[1:] for t in stages)
        swallow = bool(prev) and prev[1] >= 2 and prev[2] in FILTERS
        if _EXIT_READ.search(seg):
            o += 1
            if prev and prev[0] in (";", "\n") and swallow:
                v += 1
        elif is_commit and prev and prev[0] == "&&":
            o += 1
            if swallow:
                v += 1
        prev = (sep, len(stages), _base(stages[-1][0]) if stages else "")
    return o, v


_GIT_OPT_WITH_ARG = ("-C", "-c", "--git-dir", "--work-tree")


def shared_whole_file_add(cmd: str) -> tuple[int, int]:
    o = v = 0
    for _k, _sep, _seg, stages in _walk(cmd):
        for tok in stages:
            if _base(tok[0]) != "git":
                continue
            i = 1
            while i < len(tok) and tok[i].startswith("-"):
                i += 2 if tok[i] in _GIT_OPT_WITH_ARG else 1
            if i >= len(tok) or tok[i] != "add":
                continue
            o += 1
            if any(_base(t.rstrip("/")) in SHARED_BASENAMES for t in tok[i + 1:] if not t.startswith("-")):
                v += 1
    return o, v


_P_FLAG = re.compile(r"^-[A-Za-z]*P[A-Za-z]*$")


def bsd_grep_perl(cmd: str) -> tuple[int, int]:
    o = v = 0
    for _k, _sep, _seg, stages in _walk(cmd):
        for tok in stages:
            if tok[0] not in ("/usr/bin/grep", "/bin/grep"):
                continue
            o += 1
            v += int(any(_P_FLAG.match(t) or t == "--perl-regexp" for t in tok[1:]))
    return o, v


DETECTORS = {
    "bare_grep_count": bare_grep_count,
    "delete_in_command": delete_in_command,
    "pipe_filter_swallowed": pipe_filter_swallowed,
    "shared_whole_file_add": shared_whole_file_add,
    "bsd_grep_perl": bsd_grep_perl,
}
WINDOW_DETECTORS = {
    "cwd_escape": cwd_escape,
}
