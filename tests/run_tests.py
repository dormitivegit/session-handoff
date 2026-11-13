#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import json
import os
import subprocess
import pathlib
import re
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
LINT = SKILL_DIR / "scripts" / "lint_handoff.py"


def _load_lint_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_handoff_under_test", LINT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


LH = _load_lint_module()

HERMETIC_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT")
_HERMETIC_DIR = tempfile.TemporaryDirectory(prefix="sh_hermetic_home_")
HERMETIC_HOME = Path(_HERMETIC_DIR.name)


def hermetic_env(home: Path, extra: "dict | None" = None) -> dict:
    env = {k: os.environ[k] for k in HERMETIC_ENV_KEEP if k in os.environ}
    env.update({"HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(extra or {})
    return env

CARRIER_VERSION = "2.6.1"
FIXTURES = TESTS_DIR / "fixtures"

EXPECTATIONS: dict[str, dict[str, object]] = {
    "readout-block-edited-20261113-warn.md": {
        "status": "WARN",
        "note": "2.6.1: v2.3 baseline plus a pasted READOUT_SIZE whose text_sha does not match the file — readout_block_rule must warn.",
    },
    "cold-read-missing-20261026-warn.md": {
        "status": "WARN",
        "note": "2.4.31: the v2.3 baseline renamed past COLD_READ_FLOOR with no COLD_READ record — the cold-read judge must warn.",
    },
    "v2.3-good.md": {
        "status": "CLEAN",
        "note": "v2.3 contract baseline: continuity kernel, predecessor delta, revalidation boundary.",
    },
    "comprehensive-good.md": {
        "status": "WARN",
        "note": "v2.2-era good fixture; was CLEAN under v2.2. Warns under v2.3 because it predates "
                "the continuity kernel. Expected, not a regression.",
    },
    "ruling-anchor-20260923-warn.md": {
        "status": "WARN",
        "note": "A-column ruling without a verbatim-source anchor (A1) next to one with it (A2) and a method entry (B1).",
    },
    "release-window-good.md": {
        "status": "WARN",
        "note": "v2.2-era good fixture; same continuity-kernel gap as comprehensive-good.md.",
    },
    "placeholder-secret-fail.md": {
        "status": "FAIL",
        "note": "Mechanical hazards: unresolved placeholders and exposed secrets.",
    },
    "receiver-freeze-fail.md": {
        "status": "WARN",
        "note": "Single-axis HOLD with no cleared first action — the classic receiver freeze.",
    },
    "schema-light-warning.md": {
        "status": "WARN",
        "note": "Too thin to carry the six dimensions.",
    },
    "altitude-good.md": {
        "status": "CLEAN",
        "note": "Altitude trio + landed index + unlanded directions all present, legal, "
                "and anchored — proves the new rules do not fire on a compliant handoff.",
    },
    "altitude-missing-lcarry-warn.md": {
        "status": "WARN",
        "note": "Altitude-scope handoff without L_CARRY / L2_MECHANISMS — window-altitude protocol 'missing "
                "means the round is not closed', mechanized at WARN tier only.",
    },
    "altitude-bad-anchor-warn.md": {
        "status": "WARN",
        "note": "L_CARRY=L3 whose L2_MECHANISMS anchors do not machine-resolve (bare event "
                "id E5; dead path) — the window-altitude cross-field gate.",
    },
    "altitude-saturated-20260922-warn.md": {
        "status": "WARN",
        "note": "Altitude family: axis at ceiling (L3/L3) with no PROGRESS_AXIS; scope-index fields absent. "
                "Lights altitude_saturation / progress_axis / landed_index / unlanded_directions.",
    },
    "claim-anchor-warn.md": {
        "status": "WARN",
        "note": "Claim-anchor family: counted claim, state claim, cross-file reference and enum value "
                "each lack the anchor their kind requires. Lights volatile_enumeration / state_anchor_rate / "
                "cross_ref_path / enum.",
    },
    "evolution-kernel-warn.md": {
        "status": "WARN",
        "note": "Evolution kernel: K1 anchored by a recompute command, K2 unanchored and must be reported.",
    },
    "method-increment-landing-20260922-warn.md": {
        "status": "WARN",
        "note": "METHOD_INCREMENT entry A2 carries no landing declaration; A1 does. "
                "Positive control for the in-tree METHOD_INCREMENT_LANDING judge.",
    },
}

SELF_CHECK_SAMPLE_FIXTURE = "placeholder-secret-fail.md"
SELF_CHECK_EXPECT_STATUS = "FAIL"
SELF_CHECK_EXPECT_SUBSTRINGS = ["placeholder", "secret"]
SELF_CHECK_EXPECT_WARNING_SUBSTRINGS = ["receipt"]

CORPUS_ENV = "SESSION_HANDOFF_CORPUS"
CORPUS_FILE = TESTS_DIR / "corpus.txt"


def resolve_corpus() -> tuple[list[str], str]:
    raw = os.environ.get(CORPUS_ENV, "").strip()
    if raw:
        return [p for p in (x.strip() for x in raw.split(":")) if p], CORPUS_ENV
    if CORPUS_FILE.is_file():
        lines = [
            x.strip() for x in CORPUS_FILE.read_text(encoding="utf-8").splitlines()
        ]
        return [x for x in lines if x and not x.startswith("#")], str(CORPUS_FILE)
    return [], "none"


REGRESSION_ASSERTION = "no ERROR caused by an in-discussion placeholder (mention misread as action)"


def run_lint(path: Path) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, str(LINT), str(path), "--json"],
        capture_output=True,
        text=True,
        env=hermetic_env(HERMETIC_HOME),
        cwd=HERMETIC_HOME,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"lint exited {proc.returncode} on {path.name}\nstderr: {proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"lint produced unparseable output for {path.name}: {exc}\nstdout: {proc.stdout[:400]}"
        ) from exc


def self_check() -> tuple[bool, str]:
    sample = FIXTURES / SELF_CHECK_SAMPLE_FIXTURE
    if not sample.is_file():
        raise RuntimeError(
            f"self-check sample fixture missing: {sample} —— 反向自检没有样本即无法证明 "
            f"lint 还在工作；绝不读作通过")
    result = run_lint(sample)

    if result["status"] != SELF_CHECK_EXPECT_STATUS:
        return False, f"expected {SELF_CHECK_EXPECT_STATUS}, got {result['status']}"

    joined = " ".join(str(e) for e in result["errors"]).lower()
    missing = [s for s in SELF_CHECK_EXPECT_SUBSTRINGS if s not in joined]
    if missing:
        return False, f"lint did not report: {', '.join(missing)}"

    joined_warnings = " ".join(str(w) for w in result["warnings"]).lower()
    missing_warnings = [s for s in SELF_CHECK_EXPECT_WARNING_SUBSTRINGS if s not in joined_warnings]
    if missing_warnings:
        return False, f"lint did not warn about: {', '.join(missing_warnings)}"

    return True, "lint detects placeholders, secrets, and a missing receipt duty in a known-bad sample"


def real_file_regression() -> tuple[bool, list[dict[str, object]]]:
    corpus, source = resolve_corpus()
    rows: list[dict[str, object]] = []
    ok = True
    if not corpus:
        return True, [], f"NOT_RUN corpus empty (source={source}; set ${CORPUS_ENV} or fill {CORPUS_FILE})"
    for raw in corpus:
        path = Path(raw).expanduser()
        if not path.is_file():
            ok = False
            rows.append({
                "path": raw,
                "state": "MISSING",
                "note": "live external file absent — assertion not runnable; reported, not silenced",
            })
            continue
        result = run_lint(path)
        placeholder_class = [e for e in result["errors"] if "placeholder" in str(e).lower()]
        other_errors = [e for e in result["errors"] if "placeholder" not in str(e).lower()]
        passed = not placeholder_class
        ok = ok and passed
        rows.append({
            "path": raw,
            "state": "PASS" if passed else "FAIL",
            "placeholder_class_errors": placeholder_class,
            "other_errors": other_errors,
            "warnings": len(result["warnings"]),
            "sha256_runtime_provenance": result["sha256"],
        })
    return ok, rows, f"RUN {len(corpus)} file(s) from {source}"


ANCHOR_RE = re.compile(r"(?<![\w/$])((?:\$SKILL_ROOT/|~/|\.{0,2}/)?[\w.][\w./~-]*\.(?:md|py|sh))(?:#|:(\d+|[A-Za-z_][\w-]*))")


def anchor_problem(target: str, ident: "str | None") -> "str | None":
    root = SKILL_DIR.resolve()
    tok = LH.SKILL_ROOT_TOKEN + "/"
    if not (target.startswith(tok) or target.startswith("~") or target.startswith("/")):
        return (f"锚用了相对路径 {target!r} —— 示例会被照抄，"
                f"照抄出的件其锚基准是交接件自身目录，必然解析不到")
    f = LH.resolve_path_token(target)
    if not f.is_file():
        return f"锚 {target!r} 在盘上不存在 —— 本检查名为「可解析」，若只判首字符就只是在判「相对性」"
    if ident and not ident.isdigit() and ident not in f.read_text(errors="replace"):
        return f"标识符锚 {target}:{ident} —— 文件在，但字节内不含该标识符（悬空锚）"
    inside = str(f.resolve()).startswith(str(root) + "/")
    if target.startswith(tok):
        return None if inside else f"树内锚 {target!r} 解析到了树外"
    if inside:
        return (f"绝对锚 {target!r} 指向本树内 —— 树内自引用须写 "
                f"$SKILL_ROOT/{f.resolve().relative_to(root)}（位置无关，不必重基）")
    return (f"绝对锚 {target!r} 在盘上，但**落在本 skill 树外**（树根 {SKILL_DIR}）—— "
            f"剥离后它会继续指回原树，在原树仍在的机器上永远测不出来")


def self_anchor_check() -> tuple[bool, list[str]]:
    problems: list[str] = []
    for rel in ("SKILL.md", "VERSION_LEDGER.md", "assets/handoff-outline.md", "references/handoff-method.md",
                "references/window-altitude-and-method-increment.md"):
        f = SKILL_DIR / rel
        if not f.is_file():
            problems.append(f"{rel}: 契约面文件缺失")
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in ANCHOR_RE.finditer(line):
                p = anchor_problem(m.group(1), m.group(2))
                if p:
                    problems.append(f"{rel}:{n} {p}")
    return (not problems), problems



RULE_DEF_RE = re.compile(r"^def (\w*_rule)\(", re.M)
RULE_FACE_MARK = 'if __name__ == "__main__":'
RULE_FACE_UNOBSERVED: frozenset[str] = frozenset()

RULE_FACE_GATES: frozenset[str] = frozenset({"altitude_scope_rule"})


def _rule_face_gates(source: str) -> set[str]:
    out = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name.endswith("_rule") and node.returns is not None:
            r = node.returns
            if isinstance(r, ast.Subscript) and isinstance(r.slice, ast.Tuple) and r.slice.elts:
                first = r.slice.elts[0]
                is_list = isinstance(first, ast.Subscript) and getattr(first.value, "id", "") == "list"
                if not is_list:
                    out.add(node.name)
    return out


FROZEN_FACES = (
    ("MATRIX_REGISTERED_IDS", "no_shrink",
     "判面扩张未登记 —— 新增判官须显式登记，否则下次它消失时无人知道它来过",
     "判面收缩 —— 判官已从 DISCRIMINATION_MATRIX 消失，而 N/N 读数对此免疫"),
    ("RULE_FACE_UNOBSERVED", "no_grow",
     "新造了一个哑判官 —— 整条停产而读数不变，且未登记",
     "现在可观测了（或已从 lint 消失）—— 从名单删掉，棘轮只能往下拧"),
    ("RULE_FACE_GATES", "no_grow",
     "新出现门控分类 —— 须显式登记（防把 findings 规则的返回注解改成 bool 以逃闸）",
     "登记的门控已不再是门控 —— 从名单删掉"),
    ("SELF_CHECK_EXPECT_SUBSTRINGS", "no_shrink", "", ""),
    ("SELF_CHECK_EXPECT_WARNING_SUBSTRINGS", "no_shrink", "", ""),
    ("EXPECTATIONS", "no_shrink", "", ""),
)

FACE_RENAMES: "dict[str, dict[str, str]]" = {}


def _expect_status(source: "str | None", key: str) -> "str | None":
    if source is None:
        return None
    for node in ast.parse(source).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(tgt, ast.Name) and tgt.id == "EXPECTATIONS" and isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Dict):
                        for kk, vv in zip(v.keys, v.values):
                            if isinstance(kk, ast.Constant) and kk.value == "status" and isinstance(vv, ast.Constant):
                                return vv.value
    return None


def _frozen_face_members(source: str, name: str) -> "set[str] | None":
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        tgt = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
        if isinstance(tgt, ast.Name) and tgt.id == name:
            if isinstance(node.value, ast.Dict):
                return {k.value for k in node.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            return {n.value for n in ast.walk(node.value)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return None


def _head_source() -> "tuple[str | None, str]":
    rel = str(Path(__file__).resolve().relative_to(SKILL_DIR.resolve()))
    try:
        top = subprocess.run(["git", "-C", str(SKILL_DIR), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=20)
        if top.returncode != 0:
            return None, "不在 git 工作树内（无工件之外的真相面可比）"
        root = Path(top.stdout.strip())
        prefix = str(SKILL_DIR.resolve().relative_to(root.resolve()))
        prev = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{prefix}/{rel}"],
                              capture_output=True, text=True, timeout=20)
        if prev.returncode != 0:
            return None, "本文件在 HEAD 上不存在（首次落地）"
        return prev.stdout, ""
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError("判面引擎取 HEAD 失败（%s）—— 装置失效，绝不读作通过" % type(e).__name__)


def face_engine(computed: dict) -> tuple[bool, list[str]]:
    cur = Path(__file__).read_text(encoding="utf-8")
    prev, why_not = _head_source()
    ok, lines = True, []
    for name, direction, extra_msg, missing_msg in FROZEN_FACES:
        lit = _frozen_face_members(cur, name)
        if lit is None:
            ok = False
            lines.append(f"🔴 face[{name}] 取不到字面集 —— 装置失效，绝不读作通过")
            continue
        comp = computed.get(name)
        seg = f"face[{name}] literal={len(lit)} computed={len(comp) if comp is not None else '—'}"
        if comp is not None:
            for bad, msg in ((sorted(set(comp) - lit), extra_msg), (sorted(lit - set(comp)), missing_msg)):
                if bad:
                    ok = False
                    lines.append(f"🔴 face[{name}] {', '.join(bad)}：{msg}")
        if prev is None:
            seg += f" · HEAD NOT_RUN（{why_not}）"
        else:
            was = _frozen_face_members(prev, name)
            if was is None:
                seg += " · HEAD NOT_RUN（本面是新增的）"
            else:
                renames = FACE_RENAMES.get(name, {})
                live = {o: n for o, n in renames.items() if o in was}
                for o, n in live.items():
                    bad = [why for cond, why in ((o in lit, "旧名仍在"), (n not in lit, "新名不在"),
                                                 (n in was, "新名在 HEAD 已存在（会掩盖一次删除）"),
                                                 (name == "EXPECTATIONS" and _expect_status(prev, o) != _expect_status(cur, n),
                                                  "新旧期望状态不同")) if cond]
                    if bad:
                        ok = False
                        lines.append(f"🔴 face[{name}] 更名 {o}→{n} 不成立：{'、'.join(bad)}")
                inert = sorted(set(renames) - set(live))
                was = {live.get(x, x) for x in was}
                widened = sorted(was - lit) if direction == "no_shrink" else sorted(lit - was)
                if widened:
                    ok = False
                    lines.append(f"🔴 棘轮反向 {name}（{direction}）：{', '.join(widened)} —— 判面不得放宽。"
                                 f"**两边一起改也没用**：真相面是 git HEAD，在工件之外")
                seg += f" · HEAD {len(was)}→{len(lit)} {'FAIL' if widened else 'OK'} ({direction})"
                if live or inert:
                    seg += f" · renamed {len(live)}" + (f" · {len(inert)} inert rename entr(ies) — delete" if inert else "")
        lines.append(seg)
    return ok, lines


def _rule_face_readings(source, probes, tmp, tag):
    lint_copy = tmp / ("lint_rf_%s.py" % tag)
    lint_copy.write_text(source, encoding="utf-8")
    env = hermetic_env(tmp, {"SESSION_HANDOFF_READOUT": str(READOUT)})
    out = []
    for f in probes:
        proc = subprocess.run([sys.executable, "-B", str(lint_copy), str(f), "--json"],
                              capture_output=True, text=True, env=env, cwd=tmp)
        if proc.returncode not in (0, 1):
            raise RuntimeError("lint exited %d on rule-face probe %s: %s"
                               % (proc.returncode, f.name, proc.stderr[:200]))
        j = json.loads(proc.stdout)
        out.append((j["status"],
                    tuple(sorted(str(x)[:90] for x in j["errors"])),
                    tuple(sorted(str(x)[:90] for x in j["warnings"]))))
    lint_copy.unlink(missing_ok=True)
    return tuple(out)


def rule_face_check() -> tuple[list[str], dict]:
    source = LINT.read_text(encoding="utf-8")
    all_rules = sorted(set(RULE_DEF_RE.findall(source)))
    gates = _rule_face_gates(source)
    rules = [r for r in all_rules if r not in gates]
    if source.count(RULE_FACE_MARK) != 1:
        raise RuntimeError("rule-face 变异锚 %r 不唯一 —— 装置失效，绝不读作通过" % RULE_FACE_MARK)
    gate_probes = sorted(FIXTURES.glob("*.md"))
    corpus, _src = resolve_corpus()
    bonus_probes = gate_probes + [p for p in (Path(x).expanduser() for x in corpus) if p.is_file()]

    def _neuter(r):
        ov = ("\n_rf_orig_%s = %s\ndef %s(*a, **k):\n"
              "    _x = _rf_orig_%s(*a, **k)\n"
              "    return ([],) + tuple(_x[1:]) if isinstance(_x, tuple) and _x "
              "and isinstance(_x[0], list) else _x\n" % (r, r, r, r))
        return source.replace(RULE_FACE_MARK, ov + "\n" + RULE_FACE_MARK, 1)

    def _unobserved(which, probes, tmp, ns):
        base = _rule_face_readings(source, probes, tmp, ns + "base")
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(_rule_face_readings, _neuter(r), probes, tmp, ns + r): r
                    for r in which}
            return sorted(r for f, r in futs.items() if f.result() == base)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        unobserved = _unobserved(rules, gate_probes, tmp, "g_")
        bonus = (_unobserved(unobserved, bonus_probes, tmp, "b_")
                 if len(bonus_probes) > len(gate_probes) else unobserved)
    head = (f"rule face: {len(rules) - len(unobserved)}/{len(rules)} rules observable "
            f"on {len(gate_probes)} fixture(s) · {len(unobserved)} unobserved (gate)")
    lines = [head, f"  gates excluded (return type is not a findings list): {', '.join(sorted(gates)) or '—'}"]
    if len(bonus_probes) > len(gate_probes):
        lines.append(f"  + corpus bonus: {len(rules) - len(bonus)}/{len(rules)} observable "
                     f"on {len(bonus_probes)} probe(s) —— 真语料让 "
                     f"{len(unobserved) - len(bonus)} 条规则从不可观测变为可观测"
                     f"（C-4 第二断言方的可量化价值；删掉它即退化）")
    detail = {"rules": rules, "unobserved": sorted(unobserved),
              "unobserved_with_corpus": sorted(bonus),
              "registered_unobserved": sorted(RULE_FACE_UNOBSERVED),
              "gate_probes": len(gate_probes), "bonus_probes": len(bonus_probes),
              "gates": sorted(gates)}
    return lines, detail


ELEVATION_FACE_DECLS = ("PROGRESS_AXIS_RULE", "METHOD_INCREMENT_LANDING", "RETIREMENT_OBSERVER")
ELEVATION_RE = re.compile(
    r"^(" + "|".join(ELEVATION_FACE_DECLS) + r")=(" + LH.PATH_ROOT_ALT + r"\S+?):([\w.\-]+)\s*$", re.M)


def elevation_face_check(matrix_rows) -> tuple[bool, list[str]]:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    found = {m.group(1): (m.group(2), m.group(3)) for m in ELEVATION_RE.finditer(skill)}
    judged = {r["rule"] for r in matrix_rows if r["status"] == "PASS"}
    root = str(SKILL_DIR.resolve()) + "/"
    lines: list[str] = []
    ok = True
    on_disk = with_reading = not_run = 0
    for name in ELEVATION_FACE_DECLS:
        if name not in found:
            lines.append(f"🔴 {name} 未在 SKILL.md 头块声明 —— 抬升面少一条即能力退化")
            ok = False
            continue
        path, ident = found[name]
        f = LH.resolve_path_token(path)
        if not f.is_file():
            lines.append(f"🔴 {name} 的判官 {path} 不在盘上 ⇒ 悬空声明，按头块自述判不成立")
            ok = False
            continue
        on_disk += 1
        if ident not in f.read_text(encoding="utf-8", errors="replace"):
            lines.append(f"🔴 {name} 的判官在盘上，但其字节内不含判据 ID {ident!r} ⇒ 悬空声明")
            ok = False
            continue
        if not str(f.resolve()).startswith(root):
            not_run += 1
            lines.append(
                f"NOT_RUN {name} 的判官 {ident} 在**本 skill 树外**（{path}）—— "
                f"本树无法证伪它，剥离后该声明在新环境自判不成立。"
                f"这是显式降级读数，不是通过")
            continue
        if ident not in judged:
            lines.append(
                f"🔴 {name} 的判官 {ident} 在树内，却没有任何登记的证伪读数 "
                f"（判别力矩阵 rule 列无 status=PASS 的行）⇒ 声明了一个没人测的判官")
            ok = False
            continue
        with_reading += 1
    head = (f"elevation face: {len(found)}/{len(ELEVATION_FACE_DECLS)} declared · "
            f"{on_disk} on disk · {with_reading} with falsifying reading · {not_run} NOT_RUN")
    return ok, [head] + lines



DISCRIMINATION_MATRIX = [
    {
        "id": "S1.form_command",
        "fix": "动作点面里的真命令行判 COMMAND",
        "expect": "COMMAND",
        "mutate": [('                if full and not line.strip().startswith("#"):\n'
                    '                    return "COMMAND"',
                    '                if full and not line.strip().startswith("#"):\n'
                    '                    return "NONE"  # MUTANT')],
        "probe": "form_command",
        "read": "action_point_match",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "S1.form_comment",
        "fix": "被注释停用的引用判 COMMENT_ONLY —— 不是 COMMAND（已停用不是接线），也不是 BASENAME_ONLY",
        "expect": "COMMENT_ONLY",
        "mutate": [('                    best = "COMMENT_ONLY"', '                    best = "NONE"  # MUTANT')],
        "probe": "form_comment",
        "read": "action_point_match",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "S1.form_same_basename",
        "fix": "异目录同名文件判 BASENAME_ONLY —— 那是另一个目标，不是这个载体",
        "expect": "BASENAME_ONLY",
        "mutate": [('                    best = "BASENAME_ONLY"', '                    best = "NONE"  # MUTANT')],
        "probe": "form_same_basename",
        "read": "action_point_match",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "S1.wired_retired",
        "fix": "WIRED 永不产出（接线须原生事件证据，宿主不提供该面时不得判接线）",
        "mutate": [('else "TEXT_REFERENCED" if match == "COMMAND"',
                    'else "WIRED" if match == "COMMAND"  # MUTANT')],
        "probe": "action_point",
        "read": "carrier_state",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "S3.home_path",
        "fix": "载体正则接受 ~ 开头的 home 路径（否则被从 / 处截断误报 MISSING）",
        "mutate": [('CONCRETIZATION_CARRIER_RE = re.compile(r"(?:\\$SKILL_ROOT/)?[~/\\w.\\-]+\\.(?:py|sh)\\b")',
                    'CONCRETIZATION_CARRIER_RE = re.compile(r"(?:\\$SKILL_ROOT/)?[/\\w.\\-]+\\.(?:py|sh)\\b")  # MUTANT')],
        "probe": "home_carrier",
        "read": "carrier_state",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "S2.section_scope",
        "fix": "递归统计的判面收窄到 METHOD_INCREMENT 段内（段外历史摘录不得计入）",
        "mutate": [('    span = _method_increment_span(lines)\n'
                    '    section_present = span is not None',
                    '    span = (0, len(lines), 2, "MUTANT")  # MUTANT\n'
                    '    section_present = span is not None')],
        "probe": "history_appendix",
        "read": "counts",
        "rule": "method_recursion_rule",
    },
    {
        "id": "S2.boundary_is_structural",
        "fix": "段尾封口按 markdown 标题**层级**判，不按 `## ` 字面前缀（否则 `##历史附录` 不封口）",
        "mutate": [('        if level <= start_level:',
                    '        if level <= start_level and lines[idx].startswith("## "):  # MUTANT')],
        "probe": "no_space_heading",
        "read": "counts",
        "rule": "method_recursion_rule",
    },
    {
        "id": "S2.skip_disambiguated",
        "fix": "「无方法节」与「有节但条目落在段外」两种 SKIP 的文案必须不同",
        "mutate": [('        decision = ("SKIP: no METHOD_INCREMENT section in this handoff"\n'
                    '                    if not section_present else',
                    '        decision = ("SKIP: no METHOD_INCREMENT section in this handoff"\n'
                    '                    if True else  # MUTANT')],
        "probe": "entries_outside_section",
        "read": "decision",
        "rule": "method_recursion_rule",
    },
    {
        "id": "ST4.fence_is_boundary",
        "fix": "空的按引用继承字段不得把 Markdown 结束围栏吸收成「值」（否则伪造出已识别引用）",
        "mutate": [('            if _t.startswith("```") or _t.startswith("~~~"):',
                    '            if False:')],
        "probe": "empty_field_then_fence",
        "read": "restart_warning",
        "rule": "method_recursion_rule",
    },
    {
        "id": "N3.empty_glob_distinguished",
        "fix": "动作点面 glob 展开为空集须报 NO_SURFACE_MATCHED，不得与「面内未出现」同形",
        "mutate": [('    if best == "NONE" and surfaces_seen == 0:',
                    '    if False:  # MUTANT')],
        "probe": "empty_glob",
        "read": "action_point_match",
        "rule": "concretization_rate_rule",
    },
    {
        "id": "P1.by_reference",
        "fix": "显式按引用继承的件不判「从零重启」",
        "mutate": [('    if linked == 0 and not by_reference:',
                    '    if linked == 0:  # MUTANT')],
        "probe": "by_reference",
        "read": "restart_warning",
        "rule": "method_recursion_rule",
    },
    {
        "id": "PA1.saturation_gate",
        "fix": "高度轴饱和且无 PROGRESS_AXIS= 时必须 WARN（饱和处方从文案变判据）",
        "expect": "WARN emitted: saturated without PROGRESS_AXIS",
        "mutate": [("    if not saturated:", "    if not saturated or True:  # MUTANT")],
        "probe": "progress_axis_20260921",
        "read": "progress_axis_decision",
        "rule": "progress_axis_rule",
    },
    {
        "id": "CR1.unrooted_cross_ref",
        "fix": "正文里无仓根的跨件引用判 WARN（绝对/~/围栏内三种写法不得误报）",
        "expect": 1,
        "mutate": [("            if CROSSREF_ROOTED_RE.search(before):",
                    "            if True:  # MUTANT")],
        "probe": "crossref_unrooted",
        "read": "crossref_hits",
        "rule": "cross_ref_path_rule",
    },
    {
        "id": "PH1.html_comment_not_slot",
        "fix": "HTML 注释（单行与跨行）里的尖括号不是未填槽位（注释不渲染）",
        "mutate": [('                if _covered(comments.get(line_no, []), start, end):',
                    '                if False:')],
        "probe": "html_comment_slot",
        "read": "placeholder_actions",
        "rule": "placeholder_rule",
    },
    {
        "id": "RA1.ruling_source_anchor",
        "fix": "A 栏常设裁定须带原声锚 <会话记录> @ <时间>（转述丢原则；锚让下一窗直接读原话）",
        "mutate": [('        if ruling_on and label.startswith("A"):',
                    '        if False:')],
        "probe": "ruling_anchor_20260923",
        "read": "ruling_unanchored",
        "rule": "method_increment_landing_rule",
    },
    {
        "id": "ML1.same_line_exit",
        "fix": "出口声明须同行成立：NOT_LANDED= 行尾空着不得被下一行补齐",
        "expect": 1,
        "mutate": [('NOT_LANDED[ \\t]*=[ \\t]*(\\S))")',
                    'NOT_LANDED\\s*=\\s*(\\S))")  # MUTANT')],
        "probe": "landing_crossline_20260922",
        "read": "landing_missing",
        "rule": "method_increment_landing_rule",
    },
    {
        "id": "ML2.landing_floor",
        "fix": "地板之前的存量件不追溯：无出口条目在历史件上不报",
        "expect": 0,
        "mutate": [("    if not _d or _d.group(1) < MI_LANDING_FLOOR:",
                    "    if False:  # MUTANT")],
        "probe": "landing_below_floor_20260901",
        "read": "landing_missing",
        "rule": "method_increment_landing_rule",
    },
    {
        "id": "CR2.pre_fence_line",
        "fix": "紧贴围栏开头的上一行照常扫描，报告行号等于物理行号",
        "expect": (2,),
        "mutate": [("    for idx, line in enumerate(lines):\n        if idx in fenced:\n            continue\n"
                    "        for m in CROSSREF_DIR_RE.finditer(line):",
                    "    for idx, line in enumerate(lines, 1):  # MUTANT\n        if idx in fenced:\n            continue\n"
                    "        for m in CROSSREF_DIR_RE.finditer(line):")],
        "probe": "crossref_pre_fence",
        "read": "crossref_hit_lines",
        "rule": "cross_ref_path_rule",
    },
    {
        "id": "SAT1.prose_is_not_field",
        "fix": "散文里提到 L_CARRY 不算字段在场，读数应为真缺席",
        "expect": "no warning: no L_CARRY field anywhere (genuinely absent)",
        "mutate": [('        anchorlike = any(re.search(r"\\bL_CARRY\\b[\\s`*]*[=:：]", ln) for ln in lines)',
                    '        anchorlike = any("L_CARRY" in ln for ln in lines)  # MUTANT')],
        "probe": "saturation_prose_only",
        "read": "saturation_decision",
        "rule": "altitude_saturation_rule",
    },
    {
        "id": "EK1.kernel_item_needs_anchor",
        "fix": "进化核每条须带机械锚（在盘机制路径 / 复算命令 / 证伪命令），无锚即报",
        "expect": 1,
        "mutate": [('        if _pa_has_recompute(body, base_dir) or _ek_pointer_ok("\\n".join(body)):',
                    "        if True:  # MUTANT")],
        "probe": "kernel_unanchored",
        "read": "kernel_unanchored",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK2.fenced_items_parsed",
        "fix": "标题形态的进化核按标题层级封口，围栏内的 K 条目照常解析与判锚",
        "expect": 1,
        "mutate": [("    fenced: set[int] = set()\n    if head:",
                    "    fenced: set[int] = set()\n    if False:  # MUTANT")],
        "probe": "kernel_heading_fenced_20261018",
        "read": "kernel_unanchored",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK3.by_reference_warns",
        "fix": "进化核只以引用继承（Kx–Ky 同前代）而不写出条目时报 WARN，并给出继承数",
        "expect": True,
        "mutate": [("    if integral_on and by_ref:", "    if False and by_ref:  # MUTANT")],
        "probe": "kernel_by_reference_20261018",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK4.integral_floor",
        "fix": "引用继承 / 零条目两条新 WARN 不追溯存量件（文件名日期早于 EK_INTEGRAL_FLOOR 只出读数）",
        "expect": False,
        "mutate": [("    integral_on = (not _d) or _d.group(1) >= EK_INTEGRAL_FLOOR",
                    "    integral_on = True  # MUTANT")],
        "probe": "kernel_by_reference_20261017",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK8.midline_range_not_carry",
        "fix": "引用继承只认行首 K 区间；「整合 K3–K5 进 K10，保留其判据」这类行中区间不报",
        "expect": False,
        "mutate": [('EK_RANGE_LINE_RE = re.compile(r"^\\s*(?:[-*+]\\s*)?K(\\d+)',
                    'EK_RANGE_LINE_RE = re.compile(r"^.*?(?:[-*+]\\s*)?K(\\d+)')],
        "probe": "kernel_midline_range_20261018",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK9.word_range_separator",
        "fix": "区间符号含「到 / 至」，文字写法的引用继承照样计入并报 WARN",
        "expect": True,
        "mutate": [("(?:[–—~～-]|到|至|", "(?:[–—~～-]|")],
        "probe": "kernel_word_range_20261018",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK10.undated_in_scope",
        "fix": "文件名无日期的交接件，引用继承 / 零条目照常报 WARN；地板只豁免带日期的存量件",
        "expect": True,
        "mutate": [("    integral_on = (not _d) or _d.group(1) >= EK_INTEGRAL_FLOOR",
                    "    integral_on = bool(_d) and _d.group(1) >= EK_INTEGRAL_FLOOR  # MUTANT")],
        "probe": "kernel_by_reference_nodate",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK11.materialized_not_counted",
        "fix": "引用继承数只计区间内本件未写出的编号；区间内条目全部写出时不报",
        "expect": False,
        "mutate": [("            by_ref += len(set(range(lo, hi + 1)) - written)",
                    "            by_ref += hi - lo + 1  # MUTANT")],
        "probe": "kernel_range_materialized_20261018",
        "read": "kernel_by_reference_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK7.fenced_stock_read_only",
        "fix": "标题形态围栏内的条目在落地日之前的件上不报无锚 / 超预算（读数照出）",
        "expect": 0,
        "mutate": [("    pre_floor = {j for _l, j, _b in items if j in fenced} if not integral_on else set()",
                    "    pre_floor = set()  # MUTANT")],
        "probe": "kernel_heading_fenced_20261001",
        "read": "kernel_unanchored",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK5.empty_section_warns",
        "fix": "进化核段在场但解析 0 条时报 WARN（落地日之后的件）",
        "expect": True,
        "mutate": [("    elif integral_on and not items:", "    elif False:  # MUTANT")],
        "probe": "kernel_empty_20261018",
        "read": "kernel_empty_warn",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "EK6.unbounded_kernel_id",
        "fix": "K 编号不设位宽，随代增长的编号不撑破判官",
        "expect": 1,
        "mutate": [('EK_ITEM_RE = re.compile(r"^\\s*(K\\d+)[\\s:：.]")',
                    'EK_ITEM_RE = re.compile(r"^\\s*(K\\d{1,3})[\\s:：.]")  # MUTANT')],
        "probe": "kernel_four_digit",
        "read": "kernel_unanchored",
        "rule": "evolution_kernel_rule",
    },
    {
        "id": "ML3.unbounded_entry_id",
        "fix": "METHOD_INCREMENT 条目编号不设位宽，三位及以上的号照常判出口",
        "expect": 1,
        "mutate": [('?([A-Z]\\d+)[\\s\\u3000]")', '?([A-Z]\\d{1,2})[\\s\\u3000]")  # MUTANT')],
        "probe": "landing_three_digit_20261018",
        "read": "landing_missing",
        "rule": "method_increment_landing_rule",
    },
    {
        "id": "CRD1.missing_record_warns",
        "fix": "地板之后的交接件缺 COLD_READ 记录时报 WARN（写件时未做冷读校验）",
        "expect": True,
        "mutate": [("        if in_scope:\n            warnings.append(\n                \"WARN emitted: no COLD_READ record",
                    "        if False:\n            warnings.append(\n                \"WARN emitted: no COLD_READ record")],
        "probe": "cold_read_missing_20261026",
        "read": "cold_read_missing_warn",
        "rule": "cold_read_rule",
    },
    {
        "id": "CRD2.remaining_warns",
        "fix": "COLD_READ 记录 CRITICAL_AFTER > 0 时报 WARN（承重缺口留给下一窗）",
        "expect": True,
        "mutate": [("            if left > 0 and in_scope:", "            if False and in_scope:  # MUTANT")],
        "probe": "cold_read_remaining_20261026",
        "read": "cold_read_remaining_warn",
        "rule": "cold_read_rule",
    },
    {
        "id": "CRD3.floor_read_only",
        "fix": "文件名日期早于 COLD_READ_FLOOR 或无日期的件缺 COLD_READ 只出读数、不报",
        "expect": False,
        "mutate": [("    in_scope = bool(_d) and _d.group(1) >= COLD_READ_FLOOR", "    in_scope = True  # MUTANT")],
        "probe": "cold_read_missing_20261025",
        "read": "cold_read_missing_warn",
        "rule": "cold_read_rule",
    },
    {
        "id": "ML4.ledger_dangling_checked",
        "fix": "SESSION_HANDOFF_ENTRIES 给出台账时，入库声明的 G.N 不在台账标题里 ⇒ 记悬空",
        "expect": 1,
        "mutate": [("            if known_ids is not None:", "            if False:  # MUTANT")],
        "probe": "landing_ledger_dangling_20261112",
        "read": "landing_dangling",
        "rule": "method_increment_landing_rule",
    },
    {
        "id": "ML5.unopened_not_run",
        "fix": "台账未能打开时不得报 RUN（判官报的状态不得强于实际执行）",
        "expect": "NOT_RUN(unreadable)",
        "mutate": [('            dangling_face = "NOT_RUN(unreadable)"', '            dangling_face = "RUN"  # MUTANT')],
        "probe": "landing_ledger_absent_20261112",
        "read": "landing_face",
        "rule": "method_increment_landing_rule",
    },
]

MATRIX_REGISTERED_IDS = frozenset({
    "S1.form_command", "S1.form_comment", "S1.form_same_basename", "S1.wired_retired",
    "S3.home_path", "S2.section_scope", "S2.boundary_is_structural", "S2.skip_disambiguated",
    "ST4.fence_is_boundary", "N3.empty_glob_distinguished", "P1.by_reference",
    "PA1.saturation_gate", "CR1.unrooted_cross_ref",
    "ML1.same_line_exit",
    "ML2.landing_floor",
    "CR2.pre_fence_line",
    "PH1.html_comment_not_slot",
    "RA1.ruling_source_anchor",
    "SAT1.prose_is_not_field",
    "EK1.kernel_item_needs_anchor",
    "EK2.fenced_items_parsed", "EK3.by_reference_warns", "EK4.integral_floor",
    "EK5.empty_section_warns", "EK6.unbounded_kernel_id", "ML3.unbounded_entry_id", "EK7.fenced_stock_read_only",
    "EK8.midline_range_not_carry", "EK9.word_range_separator", "EK10.undated_in_scope",
    "EK11.materialized_not_counted",
    "CRD1.missing_record_warns", "CRD2.remaining_warns", "CRD3.floor_read_only",
    "ML4.ledger_dangling_checked", "ML5.unopened_not_run",
})


def _probe_inputs(kind, tmp):
    duty = "receiver outcome receipt required.\n"
    method = str(tmp / "method.py")
    action = str(tmp / "action.sh")
    if kind == "action_point":
        return ("dual-channel\n## METHOD_INCREMENT\n新增 B1：载体 " + method + "\n" + duty,
                {method: "pass\n", action: "python3 " + method + "\n"},
                {"HANDOFF_ACTION_POINTS": action})
    if kind == "home_carrier":
        return ("dual-channel\n## METHOD_INCREMENT\n新增 B1：载体 ~/home_carrier.py\n" + duty,
                {str(tmp / "home_carrier.py"): "pass\n"}, {"HOME": str(tmp)})
    if kind == "history_appendix":
        return ("PREDECESSOR_HANDOFF_ID=H_PREV\n## METHOD_INCREMENT\n新增 B3：本窗新方法\n"
                "\n## 历史附录\n继承 B9：前窗摘录，不是本窗条目\n" + duty, {}, {})
    if kind in ("form_command", "form_comment", "form_same_basename"):
        body = {"form_command": "python3 " + method,
                "form_comment": "# disabled: python3 " + method,
                "form_same_basename": "python3 " + str(tmp / "other" / "method.py")}[kind]
        return ("dual-channel\n## METHOD_INCREMENT\n新增 B1：载体 " + method + "\n" + duty,
                {method: "pass\n", action: body + "\n"},
                {"HANDOFF_ACTION_POINTS": action})
    if kind == "empty_field_then_fence":
        return ("PREDECESSOR_HANDOFF_ID=H_PREV\nUNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=\n"
                "```\n\n## METHOD_INCREMENT\n新增 B3：本窗新方法\n" + duty, {}, {})
    if kind == "no_space_heading":
        return ("PREDECESSOR_HANDOFF_ID=H_PREV\n## METHOD_INCREMENT\n新增 B3：本窗新方法\n"
                "\n##历史附录\n继承 B9：前窗摘录，不是本窗条目\n" + duty, {}, {})
    if kind == "entries_outside_section":
        return ("PREDECESSOR_HANDOFF_ID=H_PREV\n## METHOD_INCREMENT\n\n## 其他小节\n"
                "新增 B3：条目落在段外\n" + duty, {}, {})
    if kind == "empty_glob":
        return ("dual-channel\n## METHOD_INCREMENT\n新增 B1：载体 " + method + "\n" + duty,
                {method: "pass\n"},
                {"HANDOFF_ACTION_POINTS": str(tmp / "no_such_dir_*/nothing.sh")})
    if kind == "progress_axis_20260921":
        return ("dual-channel\nL_CARRY=L3\nNEXT_FLOOR=L3\n## METHOD_INCREMENT\n"
                "新增 B1：本窗新方法 ⇒ NOT_LANDED=探针夹具\n" + duty, {}, {})
    if kind in ("kernel_heading_fenced_20261018", "kernel_heading_fenced_20261001"):
        return ("## EVOLUTION_KERNEL\n\n```text\nK1 有锚：复算 ls /tmp\nK2 无锚的一条\n```\n\n## 下一节\n正文\n"
                + duty, {}, {})
    if kind in ("kernel_by_reference_20261018", "kernel_by_reference_20261017"):
        return ("## EVOLUTION_KERNEL\n\nK1–K85 同前代。本窗新增：\n\n```text\nK86 有锚：复算 ls /tmp\n```\n"
                + duty, {}, {})
    if kind == "kernel_midline_range_20261018":
        return ("## EVOLUTION_KERNEL\n\n```text\nK10 合并后的一条：复算 ls /tmp\n```\n整合 K3–K5 进 K10，保留其判据。\n"
                + duty, {}, {})
    if kind == "kernel_word_range_20261018":
        return ("## EVOLUTION_KERNEL\n\nK1 到 K100 同前代。\n\n```text\nK101 有锚：复算 ls /tmp\n```\n" + duty, {}, {})
    if kind == "kernel_range_materialized_20261018":
        return ("## EVOLUTION_KERNEL\n\nK1–K2 同前代，整合后全部写出如下：\n\n```text\nK1 一条：复算 ls /tmp\nK2 一条：复算 ls /tmp\n```\n"
                + duty, {}, {})
    if kind == "kernel_by_reference_nodate":
        return ("## EVOLUTION_KERNEL\n\nK1–K40 同前代。\n" + duty, {}, {})
    if kind == "kernel_empty_20261018":
        return ("## EVOLUTION_KERNEL\n\n本窗无条目。\n\n## 下一节\n正文\n" + duty, {}, {})
    if kind in ("cold_read_missing_20261026", "cold_read_missing_20261025"):
        return ("## 交接件\n\n首动作：跑一次 ls /tmp。\n" + duty, {}, {})
    if kind == "cold_read_remaining_20261026":
        return ("## 交接件\n\n```text\nCOLD_READ=READER 探针 · CRITICAL_BEFORE 2 · CRITICAL_AFTER 1 · REMAINING 一条用户原话指代未解析\n```\n"
                + duty, {}, {})
    if kind == "kernel_four_digit":
        return ("EVOLUTION_KERNEL=\n  K1000 无锚的一条\n" + duty, {}, {})
    if kind == "landing_three_digit_20261018":
        return ("## METHOD_INCREMENT\n新增 B144 本窗方法，两种出口都没写\n" + duty, {}, {})
    if kind == "kernel_unanchored":
        return ("EVOLUTION_KERNEL=\n  K1 有锚：复算 ls /tmp\n  K2 无锚的一条\n" + duty, {}, {})
    if kind == "saturation_prose_only":
        return ("dual-channel\n本件没有写 L_CARRY 字段，只在这句散文里提到它。\n" + duty, {}, {})
    if kind == "crossref_pre_fence":
        return ("# probe\n见 30_SESSIONS/ARCHIVE_X/ 下。\n```text\n30_SESSIONS/ARCHIVE_Y/ 在围栏内\n```\n"
                + duty, {}, {})
    if kind == "html_comment_slot":
        return ("## Note\n<!-- 单行旁注 -->\n<!-- 跨行旁注：路径写成\n     <workstream-root>/docs 这样 -->\n"
                "NEXT_GATE=<fill-me>\n" + duty, {}, {})
    if kind == "ruling_anchor_20260923":
        return ("## METHOD_INCREMENT\n新立 A1 常设裁定：一次性换处境不防回归 \u21d2 NOT_LANDED=探针\n"
                "新立 A2 常设裁定：先全局梳理再动局部 \u21d2 NOT_LANDED=探针\n"
                "   原声锚 transcripts/s.jsonl @ 2026-09-22T09:44\n"
                "新增 B1 等价预言 \u21d2 NOT_LANDED=探针\n" + duty, {}, {})
    if kind == "landing_below_floor_20260901":
        return ("## METHOD_INCREMENT\n新增 A1 本窗方法，两种出口都没写\n" + duty, {}, {})
    if kind == "landing_crossline_20260922":
        return ("## METHOD_INCREMENT\n新增 A1 本窗方法 \u21d2 NOT_LANDED=\n"
                "   \u21d2 下一行的箭头不得补齐上一行的空理由\n" + duty, {}, {})
    if kind == "crossref_unrooted":
        return ("dual-channel\n归档件在 30_SESSIONS/SESSION_ARCHIVE_20260919/ 下。\n"
                "另一份在 /opt/proj/X/20_EVIDENCE/Y/ 下。\n"
                "还有 ~/SYSTEM_ROOT/30_LEDGERS/LEDGER.md。\n"
                "```bash\nS=/opt/system\npython3 $S/30_LEDGERS/x.py\n```\n"
                "## METHOD_INCREMENT\n新增 B1：本窗新方法 ⇒ NOT_LANDED=探针夹具\n" + duty, {}, {})
    if kind in ("landing_ledger_dangling_20261112", "landing_ledger_absent_20261112"):
        ledger = tmp / "entries.md"
        target = ledger if kind == "landing_ledger_dangling_20261112" else tmp / "absent.md"
        return ("## METHOD_INCREMENT\n新增 B1 reusable action ⇒ G.999999\n" + duty,
                {str(ledger): "### G.1000 Existing entry\n"}, {"SESSION_HANDOFF_ENTRIES": str(target)})
    if kind == "by_reference":
        return ("PREDECESSOR_HANDOFF_ID=H_PREV\n"
                "UNCHANGED_CRITICAL_ANCHORS_CARRIED_BY_REFERENCE=H_PREV#METHOD_INCREMENT，B1/B2 已继承\n"
                "## METHOD_INCREMENT\n新增 B3：组合前窗 B1 与 B2\n" + duty, {}, {})
    raise RuntimeError("unknown probe kind: " + kind)


def _extract(result, what):
    if what == "restart_warning":
        return any("no explicit method relation parsed" in str(w) for w in result.get("warnings", []))
    reads = {r["rule_id"]: r for r in result.get("rule_reads", [])}
    if what in ("carrier_state", "action_point_match"):
        hits = reads["concretization-rate"]["hits"]
        if len(hits) != 1:
            raise RuntimeError("carrier probe did not produce exactly one hit")
        return hits[0].get(what, "<field absent>")
    if what == "progress_axis_decision":
        return str(reads["progress-axis"]["decision"])[:110]
    if what == "crossref_hits":
        return len(reads["cross-ref-absolute-path"]["hits"])
    if what == "counts":
        hits = reads["method-recursion"]["hits"]
        return {k: hits[0][k] for k in ("新增", "继承", "退役", "entries")}
    if what == "decision":
        return str(reads["method-recursion"]["decision"])[:110]
    if what == "kernel_by_reference_warn":
        return any("only by reference" in str(w) for w in result.get("warnings", []))
    if what == "cold_read_missing_warn":
        return any("no COLD_READ record" in str(w) for w in result.get("warnings", []))
    if what == "cold_read_remaining_warn":
        return any("could not resolve remain" in str(w) for w in result.get("warnings", []))
    if what == "kernel_empty_warn":
        return any("no K-item was parsed" in str(w) for w in result.get("warnings", []))
    if what == "kernel_unanchored":
        return sum(1 for h in reads["evolution-kernel"]["hits"] if h.get("context") == "no anchor")
    if what == "saturation_decision":
        return str(reads["altitude-saturation"]["decision"])[:60]
    if what == "crossref_hit_lines":
        return tuple(h["line"] for h in reads["cross-ref-absolute-path"]["hits"])
    if what == "placeholder_actions":
        return sum(1 for h in reads["placeholder-action-vs-mention"]["hits"] if h.get("context") == "action")
    if what == "ruling_unanchored":
        return sum(1 for h in reads["method-increment-landing"]["hits"]
                   if h.get("context") == "no source anchor")
    if what == "landing_dangling":
        return sum(1 for h in reads["method-increment-landing"]["hits"]
                   if h.get("context") == "dangling ledger id")
    if what == "landing_face":
        m = re.search(r"dangling-id check=([^;\s]+)", str(reads["method-increment-landing"]["decision"]))
        if not m:
            raise RuntimeError("landing decision carries no dangling-id state")
        return m.group(1)
    if what == "landing_missing":
        return sum(1 for h in reads["method-increment-landing"]["hits"]
                   if h.get("context") == "no exit declaration")
    raise RuntimeError("unknown reading: " + what)


def _run_source(source, kind, tmp):
    lint_copy = tmp / "lint_under_test.py"
    lint_copy.write_text(source, encoding="utf-8")
    text, extra, env_extra = _probe_inputs(kind, tmp)
    for path, body in extra.items():
        Path(path).write_text(body, encoding="utf-8")
    handoff = tmp / ("probe_" + kind + ".md")
    handoff.write_text(text, encoding="utf-8")
    env = hermetic_env(tmp, env_extra)
    proc = subprocess.run([sys.executable, "-B", str(lint_copy), str(handoff), "--json"],
                          capture_output=True, text=True, env=env, cwd=tmp)
    if proc.returncode not in (0, 1):
        raise RuntimeError("lint exited %d on probe %s: %s" % (proc.returncode, kind, proc.stderr[:300]))
    return json.loads(proc.stdout)


def _code_only(src: str) -> str:
    import io, tokenize
    lines = src.split("\n")
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT and not (tok.start[0] == 1 and tok.string.startswith("#!")):
            r, c = tok.start
            lines[r - 1] = lines[r - 1][:c].rstrip()
    return "\n".join(lines)


def discrimination_matrix() -> tuple[bool, list[dict[str, object]]]:
    source = LINT.read_text(encoding="utf-8")
    rows: list[dict[str, object]] = []
    all_ok = True
    for spec in DISCRIMINATION_MATRIX:
        row: dict[str, object] = {"id": spec["id"], "fix": spec["fix"], "read": spec["read"],
                                  "rule": spec.get("rule")}
        mutated = source
        missing = []
        for old, new in spec["mutate"]:
            if mutated.count(old) != 1:
                missing.append(old.strip().splitlines()[0][:60])
                continue
            if _code_only(source).count(old) != 1:
                missing.append("锚含注释（剥注释后失配）：" + old.strip().splitlines()[0][:50])
                continue
            mutated = mutated.replace(old, new, 1)
        if missing:
            row.update(status="FAIL", reason="变异锚点不唯一或已消失：" + " | ".join(missing))
            all_ok = False
            rows.append(row)
            continue
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                control = _extract(_run_source(source, spec["probe"], tmp), spec["read"])
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                mutant = _extract(_run_source(mutated, spec["probe"], tmp), spec["read"])
        except Exception as exc:
            row.update(status="FAIL", reason="矩阵装置错误：%r" % (exc,))
            all_ok = False
            rows.append(row)
            continue
        row.update(control=control, mutant=mutant)
        expect = spec.get("expect")
        if expect is not None and control != expect:
            row.update(status="FAIL",
                       reason="未变异实现的读数 %r 不等于登记预期 %r ⇒ 该档当前判错" % (control, expect))
            all_ok = False
            rows.append(row)
            continue
        if control == mutant:
            row.update(status="FAIL",
                       reason="撤掉该修复后读数未变 ⇒ 这处修复没有判别力测试，改回去不会被发现")
            all_ok = False
        else:
            row.update(status="PASS")
        rows.append(row)
    return all_ok, rows


DIFFERENTIAL_PROTOCOL = "differential-manifest/1"


def differential_manifest() -> tuple[bool, dict]:
    ok, rows = discrimination_matrix()
    out = []
    for r in rows:
        out.append({"id": r["id"], "rule": r.get("rule"), "kind": "mutation",
                    "reads": {"with_fix": r.get("control"), "without_fix": r.get("mutant")},
                    "status": r["status"], "why": "" if r["status"] == "PASS" else r.get("reason", "")})
    return ok, {"protocol": DIFFERENTIAL_PROTOCOL, "checker": str(LINT), "rows": out}


PATH_FORMS = ("$SKILL_ROOT/", "~/", "/opt/x/")
PATH_CAPTURE_REGISTRY = {
    "ANCHOR_RE": ("tests", "见 {P}scripts/lint_handoff.py:lint 一节"),
    "ELEVATION_RE": ("tests", "PROGRESS_AXIS_RULE={P}scripts/lint_handoff.py:progress_axis_rule"),
    "CONCRETIZATION_CARRIER_RE": ("lint", "新增 B1：载体 {P}scripts/lint_handoff.py 已落"),
    "EK_POINTER_RE": ("lint", "K1 锚 {P}scripts/lint_handoff.py:lint"),
    "HOST_REF_RE": ("tests", "见 {P}scripts/lint_handoff.py 一行"),
}
RESOLVE_EXEMPT = {("lint", "resolve_path_token"), ("lint", "_action_point_match"), ("lint", "corpus_scan"),
                  ("tests", "real_file_regression"), ("tests", "rule_face_check")}


def _captures(rx, text: str, P: str) -> bool:
    m = rx.search(text)
    return bool(m) and any((g or "").startswith(P) for g in (m.groups() or (m.group(0),)))


def _own_nodes(fn):
    stack = list(fn.body)
    while stack:
        n = stack.pop()
        yield n
        stack.extend(c for c in ast.iter_child_nodes(n) if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)))


def path_grammar_check() -> tuple[bool, list[str]]:
    problems: list[str] = []
    conf = 0
    for name, (where, tpl) in PATH_CAPTURE_REGISTRY.items():
        rx = getattr(LH, name, None) if where == "lint" else globals().get(name)
        if rx is None:
            problems.append(f"登记的捕获正则 {name} 不存在")
            continue
        for P in PATH_FORMS:
            if _captures(rx, tpl.format(P=P), P):
                conf += 1
            else:
                problems.append(f"{name} 捕获不到 {P}… —— 解析侧收、捕获侧不收（本类缺陷的原形）")
    unreg, stray = [], []
    for where, src in (("lint", LINT), ("tests", Path(__file__))):
        tree = ast.parse(src.read_text(encoding="utf-8"))
        for node in tree.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Call) and getattr(node.value.func, "attr", "") == "compile"):
                sub = list(ast.walk(node.value))
                has_home = any(isinstance(n, ast.Constant) and isinstance(n.value, str) and "~/" in n.value for n in sub)
                has_alt = any((isinstance(n, ast.Name) and n.id == "PATH_ROOT_ALT")
                              or (isinstance(n, ast.Attribute) and n.attr == "PATH_ROOT_ALT") for n in sub)
                if (has_home or has_alt) and node.targets[0].id not in PATH_CAPTURE_REGISTRY:
                    unreg.append(f"{where}:{node.targets[0].id}")
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for c in _own_nodes(fn):
                    if (isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "expanduser"
                            and (where, fn.name) not in RESOLVE_EXEMPT):
                        stray.append(f"{where}:{fn.name}:L{c.lineno}")
    problems += [f"捕获路径的正则 {u} 未登记 —— 新正则须进 PATH_CAPTURE_REGISTRY 受三形态检验" for u in unreg]
    problems += [f"{s} 直接 expanduser —— 文档路径须走 resolve_path_token（或登记豁免并写明理由）" for s in stray]
    ctrl = []
    mutant = re.compile(r"(?<![\w/])(/[\w./-]+\.py)")
    ctrl.append(not _captures(mutant, "载体 ~/x/y.py", "~/"))
    inside_abs = str(SKILL_DIR.resolve() / "scripts" / "lint_handoff.py")
    ctrl.append(anchor_problem("$SKILL_ROOT/scripts/lint_handoff.py", "lint") is None)
    ctrl.append(anchor_problem(inside_abs, "lint") is not None)
    ctrl.append(anchor_problem("scripts/lint_handoff.py", "lint") is not None)
    ctrl.append(anchor_problem("$SKILL_ROOT/scripts/lint_handoff.py", "no_such_ident_zz9") is not None)
    if not all(ctrl):
        problems.append(f"对照失败 {ctrl} —— 装置不翻色，本面的「全过」不可信")
    tot = len(PATH_CAPTURE_REGISTRY) * len(PATH_FORMS)
    head = (f"path grammar face: {conf}/{tot} capture×form · {len(unreg)} unregistered · "
            f"{len(stray)} resolve bypass · controls {sum(ctrl)}/{len(ctrl)} flip")
    return (not problems), [head] + [f"  🔴 {p}" for p in problems]


HOST_REF_RE = re.compile(r"(?<![\w/$])(" + LH.PATH_ROOT_ALT + r"[\w./~-]+)")


def hermetic_input_check() -> tuple[bool, list[str]]:
    hits: list[str] = []
    texts = [(f"fixtures/{p.name}", p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.md"))]
    with tempfile.TemporaryDirectory(prefix="sh_hermetic_scan_") as td:
        tmp = Path(td).resolve()
        for kind in sorted({spec["probe"] for spec in DISCRIMINATION_MATRIX if spec.get("probe")}):
            text, extra, env = _probe_inputs(kind, tmp)
            texts.append((f"probe:{kind}", "\n".join([text, *extra.values(), *env.values()])))
        home = Path.home()
        for label, text in texts:
            for m in HOST_REF_RE.finditer(text):
                tok = m.group(1)
                if tok.startswith(LH.SKILL_ROOT_TOKEN + "/"):
                    continue
                p = home / tok[2:] if tok.startswith("~/") else Path(tok)
                try:
                    rp = p.resolve()
                except OSError:
                    continue
                if str(rp).startswith(str(tmp)) or str(rp).startswith(str(SKILL_DIR.resolve()) + "/"):
                    continue
                if rp.is_file():
                    hits.append(f"{label}: {tok}")
    head = (f"hermetic face: {len(texts)} test input(s) scanned (fixtures + probes) · "
            f"{len(hits)} reference(s) to files that exist on this host (must be 0) · subprocess env sealed")
    return (not hits), [head] + [f"  🔴 {h}" for h in hits]


def text_mode_check():
    bad = []
    files = sorted(FIXTURES.glob("*.md"))
    with tempfile.TemporaryDirectory() as td:
        env = hermetic_env(Path(td))
        for f in files:
            proc = subprocess.run([sys.executable, "-B", str(LINT), str(f)],
                                  capture_output=True, text=True, env=env, cwd=td)
            if proc.returncode not in (0, 1) or "Traceback" in proc.stderr:
                last = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1][:120]
                bad.append(f"{f.name}: rc={proc.returncode} {last}")
    head = f"text-mode face: {len(files)} fixture(s) linted without --json · {len(bad)} crash(es) (must be 0)"
    return (not bad and bool(files)), [head] + [f"  🔴 {b}" for b in bad]


LEDGER_SIX_CELLS = {
    ("off_empty", "1000"): ("NOT_RUN", 0, 0),
    ("off_empty", "999999"): ("NOT_RUN", 0, 0),
    ("real_registry", "1000"): ("RUN", 0, 0),
    ("real_registry", "999999"): ("RUN", 1, 1),
    ("nonexistent_registry", "1000"): ("NOT_RUN(unreadable)", 0, 1),
    ("nonexistent_registry", "999999"): ("NOT_RUN(unreadable)", 0, 1),
}


def ledger_six_cell_check():
    bad, lines = [], []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = tmp / "entries.md"
        ledger.write_text("### G.1000 Existing test entry\n", encoding="utf-8")
        for (envcase, ident), exp in LEDGER_SIX_CELLS.items():
            f = tmp / ("HANDOFF_%s_%s_20261112.md" % (envcase, ident))
            f.write_text("## METHOD_INCREMENT\n新增 B1 reusable action ⇒ G.%s\n" % ident, encoding="utf-8")
            extra = {"SESSION_HANDOFF_ENTRIES": ""} if envcase == "off_empty" else {
                "SESSION_HANDOFF_ENTRIES": str(ledger if envcase == "real_registry" else tmp / "absent.md")}
            proc = subprocess.run([sys.executable, "-B", str(LINT), str(f), "--json"], capture_output=True,
                                  text=True, env=hermetic_env(tmp, extra), cwd=td)
            if proc.returncode not in (0, 1):
                bad.append("%s×G.%s: lint rc=%d" % (envcase, ident, proc.returncode))
                continue
            d = json.loads(proc.stdout)
            r = {x["rule_id"]: x for x in d["rule_reads"]}["method-increment-landing"]
            m = re.search(r"dangling-id check=([^;\s]+)", str(r["decision"]))
            got = (m.group(1) if m else None,
                   sum(1 for h in r["hits"] if h.get("context") == "dangling ledger id"),
                   sum(1 for by in d["attribution"]["warnings"] if by == "method-increment-landing"))
            ok = got == exp
            lines.append("  %s %-21s G.%-7s got=%r expect=%r" % ("PASS" if ok else "FAIL", envcase, ident, got, exp))
            if not ok:
                bad.append("%s×G.%s" % (envcase, ident))
        import importlib.util as _ilu
        _sp = _ilu.spec_from_file_location("lint_for_default", LINT); _lm = _ilu.module_from_spec(_sp)
        sys.modules["lint_for_default"] = _lm; _sp.loader.exec_module(_lm)
        dflt = _lm.MI_LANDING_ENTRIES_DEFAULT
        want = "RUN" if dflt and Path(dflt).is_file() and _lm.MI_LEDGER_ID_RE.search(Path(dflt).read_text(encoding="utf-8", errors="replace")) else "NOT_RUN"
        f = tmp / "HANDOFF_absent_default_20261113.md"
        f.write_text("## METHOD_INCREMENT\n新增 B1 reusable action ⇒ NOT_LANDED=test\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", str(LINT), str(f), "--json"], capture_output=True, text=True,
                              env=hermetic_env(tmp), cwd=td)
        r = {x["rule_id"]: x for x in json.loads(proc.stdout)["rule_reads"]}["method-increment-landing"]
        m = re.search(r"dangling-id check=([^;\s]+)", str(r["decision"]))
        got = m.group(1) if m else None
        lines.append("  %s %-21s default=%s got=%r expect=%r" % ("PASS" if got == want else "FAIL", "absent", "set" if dflt else "empty", got, want))
        if got != want:
            bad.append("absent×default")
    head = "ledger six-cell face (negative control, six cells + absent-default cell): %d/%d cells met expectation" % (
        len(LEDGER_SIX_CELLS) + 1 - len(bad), len(LEDGER_SIX_CELLS) + 1)
    return (not bad), [head] + lines


READOUT = SKILL_DIR / "scripts" / "handoff_readout.py"


def _readout_session(tmp: Path, handoff: Path) -> Path:
    def a(i, ts, name, inp, mid):
        return {"type": "assistant", "isSidechain": False, "timestamp": ts,
                "message": {"id": mid, "usage": {"output_tokens": 100},
                            "content": [{"type": "tool_use", "id": "t%d" % i, "name": name, "input": inp}]}}
    recv = tmp / "HANDOFF_PREV_20261111_RUN11.md"
    recv.write_text("prev\n", encoding="utf-8")
    def env(ts, wd, frm=None):
        r = {"type": "attachment", "isSidechain": False, "timestamp": ts,
             "attachment": {"type": "environment", "snapshot": {"workingDirectory": wd}}}
        if frm is not None:
            r["attachment"]["changes"] = [{"field": "workingDirectory", "from": frm}]
        return r
    rows = [
        env("2026-11-11T23:59:59Z", "/home/probe"),
        {"type": "user", "isSidechain": False, "timestamp": "2026-11-12T00:00:00Z",
         "message": {"content": "你接手交接。唯一来源：" + str(recv)}},
        a(1, "2026-11-12T00:00:01Z", "Bash", {"command": "shasum -a 256 " + str(recv)}, "m1"),
        a(2, "2026-11-12T00:00:02Z", "Bash", {"command": "cat " + str(recv)}, "m2"),
        env("2026-11-12T00:00:02.5Z", "/home/probe/proj", "/home/probe"),
        env("2026-11-12T00:00:02.6Z", "/home/probe", "/home/probe/proj"),
        a(3, "2026-11-12T00:00:03Z", "Bash", {"command": "mkdir -p $TMPDIR/x && rm -rf $TMPDIR/x"}, "m3"),
        a(4, "2026-11-12T00:00:04Z", "Bash", {"command": "grep -c foo " + str(recv)}, "m4"),
        {"type": "user", "isSidechain": False, "timestamp": "2026-11-12T00:00:05Z",
         "message": {"content": "写交接件，切窗"}},
        a(5, "2026-11-12T00:00:06Z", "Skill", {"skill": "session-handoff"}, "m5"),
        a(6, "2026-11-12T00:00:07Z", "Write", {"file_path": str(handoff), "content": "x"}, "m6"),
    ]
    s = tmp / "00000000-0000-4000-8000-000000000000.jsonl"
    s.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return s


def readout_face_check():
    import importlib.util, shutil
    bad = []
    spec = importlib.util.spec_from_file_location("readout_under_test", READOUT)
    ro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ro)
    lp = ro.LP
    v = ro.validity(lp)
    if v:
        bad.append("validity on shipped table: " + v)
    for p in lp.PATTERNS:
        pos = sum(1 for _c, e in p["canary"] if e); neg = sum(1 for _c, e in p["canary"] if not e)
        if pos < 3 or neg < 3:
            bad.append("%s canary pos=%d neg=%d (need >=3 each)" % (p["id"], pos, neg))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        handoff = tmp / "HANDOFF_PROBE_20261112_RUN11.md"
        handoff.write_text("L_CARRY=L3\nNEXT_FLOOR=L3\n## 正文\n内容\n", encoding="utf-8")
        sess = _readout_session(tmp, handoff)
        cmd = [sys.executable, "-B", str(READOUT), "--session", str(sess), "--handoff", str(handoff), "--prior", ","]
        env = hermetic_env(tmp)
        r1 = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=td)
        r2 = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=td)
        out = r1.stdout.splitlines()
        if r1.returncode != 0:
            bad.append("readout rc=%d %s" % (r1.returncode, r1.stderr.strip()[-120:]))
        if r1.stdout != r2.stdout:
            bad.append("rerun not byte-identical")
        if not (1 <= len(out) <= 10):
            bad.append("output lines=%d (need 1..10)" % len(out))
        head = out[0] if out else ""
        if not (head.startswith("READOUT_SNAPSHOT ") and all(k in head for k in (" path=", " n=", " sha256=", " AS_OF=", " tool="))):
            bad.append("first line is not the I1 snapshot: " + head[:80])
        body = "\n".join(out)
        wants = ["touch=1@0 body=1@1", "switch=有", "READOUT_RECOMPUTE python3 "]
        wants += (["命令带删除 1/4", "裸grep计数 1/1", "cwd外移 1/4", "READOUT_E3 E3b ", " 未测="] if lp.PATTERNS
                  else ["READOUT_PATTERNS 无登记模式"])
        for want in wants:
            if want not in body:
                bad.append("missing reading: " + want)
        if "E3a" in body:
            bad.append("E3a still in the block (2.6.1: removed, prereg §4 per-class only)")
        size_before = next((x for x in out if x.startswith("READOUT_SIZE")), "")
        h2 = tmp / "HANDOFF_PROBE_20261112_RUN12.md"
        h2.write_text(handoff.read_text(encoding="utf-8") + "\n```text\nPROGRESS_AXIS=handoff_readout output (verbatim)\n"
                      + r1.stdout + "```\n", encoding="utf-8")
        h1 = tmp / "HANDOFF_PROBE_20261112_RUN13.md"
        h1.write_text(handoff.read_text(encoding="utf-8"), encoding="utf-8")
        s_f = [subprocess.run(cmd[:5] + ["--handoff", str(h)] + cmd[7:], capture_output=True, text=True, env=env, cwd=td).stdout
               for h in (h1, h2)]
        sz = [next((x.split(" text_sha=")[0] + " " + x.split(" text_sha=")[1] for x in o.splitlines() if x.startswith("READOUT_SIZE")), "")
              for o in s_f]
        if sz[0] != sz[1]:
            bad.append("SIZE changed after a fenced paste: %r vs %r" % (sz[0][:60], sz[1][:60]))
        h3 = tmp / "HANDOFF_PROBE_20261112_RUN14.md"
        h3.write_text(handoff.read_text(encoding="utf-8") + "\nPROGRESS_AXIS=handoff_readout output (verbatim)\n```text\n"
                      + r1.stdout + "```\n", encoding="utf-8")
        s3 = subprocess.run(cmd[:5] + ["--handoff", str(h3)] + cmd[7:], capture_output=True, text=True, env=env, cwd=td).stdout
        z3 = next((x.split(" text_sha=")[0] + " " + x.split(" text_sha=")[1] for x in s3.splitlines() if x.startswith("READOUT_SIZE")), "")
        if z3 != sz[0]:
            bad.append("SIZE changed when the fence sits between PROGRESS_AXIS= and the block: %r vs %r" % (z3[:60], sz[0][:60]))
        handoff.write_text(handoff.read_text(encoding="utf-8") + "\nPROGRESS_AXIS=handoff_readout output (verbatim)\n"
                           + r1.stdout + "\n", encoding="utf-8")
        r3 = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=td)
        if next((x for x in r3.stdout.splitlines() if x.startswith("READOUT_SIZE")), None) != size_before:
            bad.append("SIZE line changed after pasting the block into the handoff")
        lr = subprocess.run([sys.executable, "-B", str(LINT), str(handoff), "--json"], capture_output=True, text=True,
                            env=env, cwd=td)
        dec = next((x["decision"] for x in json.loads(lr.stdout)["rule_reads"] if x["rule_id"] == "progress-axis"), "")
        if not dec.startswith("no warning: saturated, PROGRESS_AXIS present with a resolvable recompute command"):
            bad.append("pasted block does not satisfy progress_axis_rule: " + dec[:80])
        rb = next((x["decision"] for x in json.loads(lr.stdout)["rule_reads"] if x["rule_id"] == "readout-block"), "")
        if not rb.startswith("no warning: text_sha matches"):
            bad.append("readout-block on an untouched paste: " + rb[:80])
        edited = tmp / "HANDOFF_PROBE_20261112_RUN15.md"
        edited.write_text(handoff.read_text(encoding="utf-8") + "\n事后补的一句\n", encoding="utf-8")
        le = subprocess.run([sys.executable, "-B", str(LINT), str(edited), "--json"], capture_output=True, text=True, env=env, cwd=td)
        rb2 = next((x["decision"] for x in json.loads(le.stdout)["rule_reads"] if x["rule_id"] == "readout-block"), "")
        if not rb2.startswith("WARN emitted"):
            bad.append("readout-block missed an edit after paste: " + rb2[:80])
        mut = tmp / "mut"
        if not lp.PATTERNS:
            bad_note = "negative control skipped: no registered patterns in this install"
            return (not bad), ["readout face (round-2 instrument I1–I5): %d problem(s) (must be 0) · %s" % (len(bad), bad_note)] \
                + ["  🔴 " + b for b in bad]
        shutil.copytree(SKILL_DIR / "scripts", mut, ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
        src = (mut / "lesson_detectors.py").read_text(encoding="utf-8")
        (mut / "lesson_detectors.py").write_text(src.replace('"rm", "rmdir", "unlink"', '"rmdir", "unlink"'), encoding="utf-8")
        rm_ = subprocess.run([sys.executable, "-B", str(mut / "handoff_readout.py"), "--session", str(sess), "--prior", ","],
                             capture_output=True, text=True, env=env, cwd=td)
        if "未过效度门" not in rm_.stdout or "命令带删除" in rm_.stdout:
            bad.append("tampered detector was not refused (negative control)")
    head_line = "readout face (round-2 instrument I1–I5): %d problem(s) (must be 0)" % len(bad)
    return (not bad), [head_line] + ["  🔴 " + b for b in bad]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--differential-json", action="store_true",
                        help="只跑判别力矩阵，按 differential-manifest/1 输出")
    args = parser.parse_args()

    if not LINT.is_file():
        print(f"RUNNER ERROR: lint not found at {LINT}", file=sys.stderr)
        return 2

    if args.differential_json:
        try:
            ok, manifest = differential_manifest()
        except Exception as exc:
            print(json.dumps({"protocol": DIFFERENTIAL_PROTOCOL, "checker": str(LINT),
                              "rows": [], "harness_error": repr(exc)}, ensure_ascii=False))
            return 2
        print(json.dumps(manifest, ensure_ascii=False, indent=1))
        return 0 if (manifest["rows"] and ok) else 1

    try:
        ok, detail = self_check()
    except RuntimeError as exc:
        print(f"RUNNER ERROR: self-check could not run: {exc}", file=sys.stderr)
        return 2
    if not ok:
        print(f"SELF-CHECK FAILED: {detail}", file=sys.stderr)
        print("The lint is not detecting known hazards; fixture results are meaningless.", file=sys.stderr)
        return 2

    anchor_ok, anchor_problems = self_anchor_check()
    if not anchor_ok:
        print("CONTRACT-FACE ANCHOR CHECK FAILED —— 本 skill 自己的文档违反了它自己的锚规则：",
              file=sys.stderr)
        for line in anchor_problems:
            print("  " + line, file=sys.stderr)
        return 2

    on_disk = {p.name for p in FIXTURES.glob("*.md")}
    expected_names = set(EXPECTATIONS)
    if on_disk != expected_names:
        for name in sorted(expected_names - on_disk):
            print(f"RUNNER ERROR: expected fixture missing from disk: {name}", file=sys.stderr)
        for name in sorted(on_disk - expected_names):
            print(f"RUNNER ERROR: fixture on disk has no expectation: {name}", file=sys.stderr)
        return 2

    results: dict[str, object] = {}
    failures = 0
    for name in sorted(EXPECTATIONS):
        expected = EXPECTATIONS[name]["status"]
        try:
            result = run_lint(FIXTURES / name)
        except RuntimeError as exc:
            print(f"RUNNER ERROR: {exc}", file=sys.stderr)
            return 2
        actual = result["status"]
        _attr = result.get("attribution") or {}
        _mis = [t for t in ("errors", "warnings", "hints")
                if len(_attr.get(t, [])) != len(result.get(t, []))]
        passed = actual == expected and not _mis
        if _mis:
            print(f"ATTRIBUTION MISALIGNED in {name}: {_mis} —— 有发现绕过了按构造归因", file=sys.stderr)
        failures += 0 if passed else 1
        results[name] = {
            "expected": expected,
            "actual": actual,
            "pass": passed,
            "warnings": len(result["warnings"]),
            "errors": len(result["errors"]),
            "sha256": result["sha256"],
            "note": EXPECTATIONS[name]["note"],
        }

    try:
        reg_ok, reg_rows, reg_state = real_file_regression()
    except RuntimeError as exc:
        print(f"RUNNER ERROR: real-file regression could not run: {exc}", file=sys.stderr)
        return 2

    try:
        matrix_ok, matrix_rows = discrimination_matrix()
    except Exception as exc:
        print(f"RUNNER ERROR: discrimination matrix could not run: {exc}", file=sys.stderr)
        return 2

    elev_ok, elev_lines = elevation_face_check(matrix_rows)
    grammar_ok, grammar_lines = path_grammar_check()
    herm_ok, herm_lines = hermetic_input_check()
    text_ok, text_lines = text_mode_check()
    six_ok, six_lines = ledger_six_cell_check()
    ro_ok, ro_lines = readout_face_check()
    try:
        rule_lines, rule_detail = rule_face_check()
        face_ok, face_lines = face_engine({
            "MATRIX_REGISTERED_IDS": {r["id"] for r in matrix_rows},
            "RULE_FACE_UNOBSERVED": set(rule_detail["unobserved"]),
            "RULE_FACE_GATES": set(rule_detail["gates"]),
        })
    except Exception as exc:
        print(f"RUNNER ERROR: judge-face check could not run: {exc}", file=sys.stderr)
        return 2

    summary = {
        "contract_version": "2.3",
        "self_check": detail,
        "all_pass": failures == 0 and reg_ok and matrix_ok and face_ok and elev_ok and grammar_ok and herm_ok and text_ok and six_ok and ro_ok,
        "fixtures": results,
        "real_file_regression": {
            "assertion": REGRESSION_ASSERTION,
            "all_pass": reg_ok,
            "state": reg_state,
            "files": reg_rows,
        },
        "rule_face": {
            "assertion": "blanking any single rule's findings must change a public reading "
                         "(a different axis from the matrix: 'stopped emitting', not 'classified differently')",
            "lines": rule_lines,
            **rule_detail,
        },
        "elevation_face": {
            "assertion": "each declared elevation-face judge must exist, carry its ID, "
                         "and (if in-tree) have a registered falsifying reading",
            "all_pass": elev_ok,
            "lines": elev_lines,
        },
        "path_grammar_face": {
            "assertion": "every path-capturing regex accepts all rooted forms; none unregistered; no resolve bypass",
            "all_pass": grammar_ok,
            "lines": grammar_lines,
        },
        "hermetic_face": {
            "assertion": "no test input references a file that exists on the host; subprocess env is sealed",
            "all_pass": herm_ok,
            "lines": herm_lines,
        },
        "text_mode_face": {
            "assertion": "every fixture lints in text mode (no --json) without a crash",
            "all_pass": text_ok,
            "lines": text_lines,
        },
        "ledger_six_cell_face": {
            "assertion": "the dangling-id check reports RUN only when the registry was opened and parsed",
            "all_pass": six_ok,
            "lines": six_lines,
        },
        "readout_face": {
            "assertion": "the progress-axis readout reruns byte-identically, fits 10 lines, and refuses a tampered detector",
            "all_pass": ro_ok,
            "lines": ro_lines,
        },
        "discrimination_matrix": {
            "assertion": "removing any registered fix must change a public reading",
            "all_pass": matrix_ok,
            "sites": matrix_rows,
        },
        "judge_faces": {
            "assertion": "every frozen face equals its computed set and does not widen against git HEAD",
            "all_pass": face_ok,
            "lines": face_lines,
        },
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"self-check OK: {detail}\n")
        for name, r in results.items():
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"{mark}  {name:<28} expected={r['expected']:<5} actual={r['actual']:<5} "
                  f"(errors={r['errors']}, warnings={r['warnings']})")
        print(f"\n{len(results) - failures}/{len(results)} fixtures met expectation")
        reg = summary["real_file_regression"]
        print(f"\nreal-file regression (C-4 second assertor): {reg['assertion']}")
        print(f"  C-4 face: {reg['state']}")
        for row in reg["files"]:
            print(f"  {row['state']:<7} {row['path']}")
            for err in row.get("placeholder_class_errors", []):
                print(f"          placeholder-class ERROR: {err}")
            for err in row.get("other_errors", []):
                print(f"          other ERROR (not asserted, surfaced): {err}")
        mx = summary["discrimination_matrix"]
        print(f"\ndiscrimination matrix (negative control): {mx['assertion']}")
        for row in mx["sites"]:
            print(f"  {row['status']:<5} {row['id']:<26} read={row['read']}")
            if row["status"] == "PASS":
                print(f"          control={row['control']!r}  mutant={row['mutant']!r}")
            else:
                print(f"          🔴 {row['reason']}")
        n_ok = sum(1 for r in mx["sites"] if r["status"] == "PASS")
        print(f"  {n_ok}/{len(mx['sites'])} registered fixes have a falsifying reading")
        print()
        for line in summary["elevation_face"]["lines"]:
            print(f"  {line}")
        for line in (summary["path_grammar_face"]["lines"] + summary["hermetic_face"]["lines"]
                     + summary["text_mode_face"]["lines"] + summary["ledger_six_cell_face"]["lines"]
                     + summary["readout_face"]["lines"]):
            print(f"  {line}")
        print()
        for line in summary["rule_face"]["lines"]:
            print(f"  {line}")
        _rules = summary["rule_face"]["rules"]
        _cov = sorted({r["rule"] for r in summary["discrimination_matrix"]["sites"]
                       if r["status"] == "PASS" and r.get("rule")} & set(_rules))
        print(f"    bound: observable ≠ correct —— 有登记证伪读数的规则 {len(_cov)}/{len(_rules)}；"
              f"其余 {len(_rules) - len(_cov)} 条只证明「在干活」，未证明「判得对」")
        if summary["rule_face"]["unobserved"]:
            n, tot = len(summary["rule_face"]["unobserved"]), len(summary["rule_face"]["rules"])
            print(f"          ⚠️ 本闸通过 ≠ 判面完整：{n}/{tot} 条规则整条停产仍零信号，"
                  f"且这条基线是起草方自冻的（外部约束只有 ratchet 的单调性）")
            print("          未观测规则（欠债清单 —— 加夹具或退役，两条路都会让它变短）：")
            for r in summary["rule_face"]["unobserved"]:
                print(f"            ⬜ {r}")

        if not args.json:
            print("\njudge faces (frozen literal ↔ computed ↔ git HEAD):")
            for line in summary["judge_faces"]["lines"]:
                print(f"  {line}")

    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
