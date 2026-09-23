#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER_VERSION = "1.1.1"
FIELD = "SKILL_VERSION_AXIS"

CONTRACT_FACE = [
    "SKILL.md",
    "references/handoff-method.md",
    "references/window-altitude-and-method-increment.md",
    "assets/handoff-outline.md",
    "scripts/lint_handoff.py",
    "tests/run_tests.py",
    "scripts/version_axis_check.py",
]

RE_SKILL_VER = re.compile(r"^CARRIER_VERSION[ \t]*=[ \t]*(\S+)[ \t]*$", re.M)
RE_PY_VER = re.compile(r'^CARRIER_VERSION[ \t]*=[ \t]*"([^"]+)"[ \t]*$', re.M)
RE_COMMITS = re.compile(r"^[ \t]*COMMITS[ \t]*=[ \t]*(.*)$", re.M)
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
RE_SHA = re.compile(r"^[0-9a-f]{4,40}$")


class Err(Exception):
    pass


def _read(root: Path, rel: str) -> str:
    p = root / rel
    if not p.is_file():
        raise Err("契约面文件缺失：%s" % rel)
    return p.read_text(encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise Err("git 不可用：%s" % type(e).__name__)
    if r.returncode != 0:
        raise Err("git %s 退出码 %d" % (args[0], r.returncode))
    return r.stdout


def _resolve(root: Path, token: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", token + "^{commit}"],
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = r.stdout.strip()
    return out if r.returncode == 0 and len(out) == 40 else None


def check(root: Path, prefix: str = "") -> tuple[int, list[str]]:
    fails: list[str] = []
    detail: list[str] = []

    skill = _read(root, prefix + "SKILL.md" if prefix else "SKILL.md")
    base = root / prefix if prefix else root

    vers = RE_SKILL_VER.findall(skill)
    if len(vers) != 1:
        fails.append("P1 SKILL.md 的 CARRIER_VERSION 声明行 %d 条，应为 1" % len(vers))
        return 1, [_line(FIELD, "FAIL", fails, detail)] + _bullets(fails, detail)
    carrier = vers[0]

    if not RE_SEMVER.match(carrier):
        fails.append("P0 CARRIER_VERSION=%r 不是 <int>.<int>.<int>" % carrier)

    sites = {"SKILL.md": carrier}
    for rel in ("scripts/lint_handoff.py", "tests/run_tests.py"):
        found = RE_PY_VER.findall((base / rel).read_text(encoding="utf-8")
                                  if (base / rel).is_file() else "")
        if len(found) != 1:
            fails.append("P2 %s 的 CARRIER_VERSION 声明行 %d 条，应为 1" % (rel, len(found)))
            sites[rel] = None
        else:
            sites[rel] = found[0]
            if found[0] != carrier:
                fails.append("P2 %s=%s ≠ SKILL.md=%s" % (rel, found[0], carrier))

    face = [prefix + f for f in CONTRACT_FACE] if prefix else list(CONTRACT_FACE)
    log = _git(root, "log", "--format=%H", "--", *face).split()
    if not log:
        raise Err("契约面在 git 中无任何 commit（判定面为空，不得读作通过）")
    gitset = set(log)
    head = log[0]

    claimed: set[str] = set()
    unknown: list[str] = []
    for line in RE_COMMITS.findall(skill):
        for tok in line.split():
            if not RE_SHA.match(tok):
                continue
            full = _resolve(root, tok)
            if full is None:
                unknown.append("%s（无法解析为 commit）" % tok)
            elif full not in gitset:
                unknown.append("%s（该 commit 未触及契约面）" % tok)
            else:
                claimed.add(full)

    unclaimed = sorted(gitset - claimed - {head})
    if unclaimed:
        fails.append("P3' 未认领 %d 笔（HEAD 已按结构性例外豁免）" % len(unclaimed))
        for h in unclaimed[:5]:
            detail.append("UNCLAIMED %s %s" % (h[:12], _subject(root, h)))
    if unknown:
        fails.append("P3' 认领了 %d 个非契约面对象" % len(unknown))
        for t in unknown[:5]:
            detail.append("UNKNOWN   %s" % t)

    status = "FAIL" if fails else "PASS"
    head_line = "%s=%s carrier=%s sites=%d commits=%d claimed=%d unclaimed=%d unknown=%d" % (
        FIELD, status, carrier, sum(1 for v in sites.values() if v is not None),
        len(gitset), len(claimed), len(unclaimed), len(unknown),
    )
    out = [head_line] + _bullets(fails, detail)
    out.append(
        "%s_BOUND=本件位于被检工件内，同一次改动可同时弱化 P0/P1/P2；P3' 的真相面是 git "
        "历史（工件之外）故不可由改本件伪造。本件自身已列入契约面。⇒ 不得读作「版本纪律已全覆盖」。"
        % FIELD
    )
    return (1 if fails else 0), out


def _line(field: str, status: str, fails: list[str], detail: list[str]) -> str:
    return "%s=%s" % (field, status)


def _bullets(fails: list[str], detail: list[str]) -> list[str]:
    return ["  " + x for x in fails] + ["  " + x for x in detail]


def _subject(root: Path, sha: str) -> str:
    try:
        return _git(root, "log", "-1", "--format=%s", sha).strip()[:60]
    except Err:
        return ""


def self_test() -> int:
    ok = True

    def run(td: Path, label: str, want_rc: int, want_sub: str = "") -> None:
        nonlocal ok
        try:
            rc, out = check(td)
        except Err as e:
            rc, out = 70, ["ERR %s" % e]
        text = "\n".join(out)
        good = (rc == want_rc) and (want_sub in text)
        ok = ok and good
        print("  %-34s rc=%d 期望=%d %s %s"
              % (label, rc, want_rc, "PASS" if good else "FAIL",
                 ("| " + want_sub) if want_sub else ""))

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        for d in ("references", "assets", "scripts", "tests"):
            (td / d).mkdir()
        (td / "references/handoff-method.md").write_text("x\n", encoding="utf-8")
        (td / "assets/handoff-outline.md").write_text(
            "旁注 v2.3.1\n", encoding="utf-8")
        (td / "scripts/lint_handoff.py").write_text(
            '"""carrier v2.3.1 历史陈述，不得被当声明"""\nCARRIER_VERSION = "9.9.9"\n', encoding="utf-8")
        (td / "tests/run_tests.py").write_text('CARRIER_VERSION = "9.9.9"\n', encoding="utf-8")
        (td / "scripts/version_axis_check.py").write_text("# stub\n", encoding="utf-8")

        for a in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(td), *a], capture_output=True)

        def commit(msg: str) -> str:
            subprocess.run(["git", "-C", str(td), "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", str(td), "commit", "-q", "-m", msg], capture_output=True)
            return subprocess.run(["git", "-C", str(td), "rev-parse", "--short", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()

        def skillmd(ver: str, commits: list[str]) -> None:
            body = ["<!--", "CONTRACT_VERSION = 2.3", "CARRIER_VERSION = " + ver,
                    "COMMITS_CONTRACT = 判据说明行，不得被 COMMITS 判据吃掉"]
            if commits:
                body.append("  COMMITS = " + " ".join(commits))
            body += ["-->", ""]
            (td / "SKILL.md").write_text("\n".join(body), encoding="utf-8")

        skillmd("9.9.9", [])
        c1 = commit("c1")
        skillmd("9.9.9", [c1])
        c2 = commit("c2")

        print("self-test（每项都跑双向，正控制翻绿、负控制翻红才算有保护）:")
        run(td, "负控制 · 全部合规", 0, "SKILL_VERSION_AXIS=PASS")

        skillmd("9.9.9", [])
        commit("c3")
        run(td, "真阳① 漏认领一笔", 1, "UNCLAIMED")

        skillmd("9.9.9", ["deadbeef"])
        commit("c4")
        run(td, "真阳② 认领不存在的 commit", 1, "UNKNOWN")

        cur = subprocess.run(["git", "-C", str(td), "log", "--format=%h"],
                             capture_output=True, text=True).stdout.split()
        skillmd("9.9.9", cur[1:])
        run(td, "负控制 · 认领补齐后回绿", 0, "SKILL_VERSION_AXIS=PASS")

        (td / "tests/run_tests.py").write_text('CARRIER_VERSION = "8.8.8"\n', encoding="utf-8")
        run(td, "真阳③ 三处不一致", 1, "≠ SKILL.md")
        (td / "tests/run_tests.py").write_text('CARRIER_VERSION = "9.9.9"\n', encoding="utf-8")

        skillmd("9.9", cur[1:])
        run(td, "真阳④ 版本形态非法", 1, "P0")

        skillmd("9.9.9", cur[1:])
        (td / "SKILL.md").write_text(
            (td / "SKILL.md").read_text(encoding="utf-8") + "CARRIER_VERSION = 7.7.7\n",
            encoding="utf-8")
        run(td, "真阳⑤ 声明行重复", 1, "应为 1")

    print("SELF_TEST=%s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    try:
        rc, out = check(a.root)
    except Err as e:
        print("%s=ERROR %s（不得读作通过）" % (FIELD, e))
        return 70
    print("\n".join(out))
    return rc


if __name__ == "__main__":
    sys.exit(main())
