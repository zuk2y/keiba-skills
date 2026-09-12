#!/usr/bin/env python3
"""Validate every skill under skills/.

Per skill it checks:
  - SKILL.md exists and has YAML frontmatter
  - name: present, equals the directory name, lowercase/digits/hyphen, <= 64 chars
  - description: present, <= 1024 chars
  - metadata.version: present
  - CHANGELOG.md exists and has a "## [<version>]" section
    (so release.py / the release workflow produce real notes)
  - evals/evals.json (if present): shape, and that each critique case's scoring
    metadata agrees with the grade table in SKILL.md (see EVALS section below)

Exits non-zero if any skill fails. Used by pre-commit and the lint workflow.
"""

from __future__ import annotations

import json
import re
import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def frontmatter(md: Path) -> str:
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def scalar(fm: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def version(fm: str) -> str | None:
    m = re.search(r"^\s+version:\s*['\"]?([^'\"\s]+)", fm, re.MULTILINE)
    return m.group(1) if m else None


def changelog_has(skill_dir: Path, ver: str) -> bool:
    cl = skill_dir / "CHANGELOG.md"
    return cl.is_file() and any(line.startswith(f"## [{ver}]") for line in cl.read_text(encoding="utf-8").splitlines())


# --- evals.json ---------------------------------------------------------------
# 品評ケース（mode が "品評"）は採点の意図を機械可読な形で持つ:
#   target_grade_band : 期待する総合グレード帯。"S+"/"S"/"A"/"B"/"C"/"不可"、範囲は "A〜S"
#   target_symbols    : 土台3軸の記号 {"連想": …, "言語一致": …, "背景": …}。範囲は "○〜◎"
#   target_band_shift : 副次パーフェクト昇格(+1)・制約違反による減格(-1 等)の段数（既定 0）
#   target_note       : 自由記述（そのケースの狙い・補足）
# 固定しないケースは値に null を明示する（新規ケースで書き忘れないよう3キーとも必須）。
# 記号から採点表が導く帯が target_grade_band に収まらなければエラー。採点表は SKILL.md の
# 「土台グレード」表から読むので、表を改訂すれば検証もそのまま追随する。

FOUNDATION_AXES = ("連想", "言語一致", "背景")
SYMBOLS = ("—", "△", "○", "◎", "◉")  # 低い順
BANDS = ("C", "B", "A", "S", "S+")  # 低い順
GATE = "不可"  # Mゲートの確定却下。記号評価に進まないので土台グレードを持たない
RANGE_SEP = re.compile(r"[〜～]")
TABLE_HEAD = re.compile(r"^\|\s*条件.*\|\s*土台\s*\|\s*$")
CLAUSE = re.compile(r"^(.)(?:が(?:(\d+)つ以上|(\d+)つ|1つでもある)|ゼロ)$")
CASE_KEYS = ("target_grade_band", "target_symbols", "target_note")


def foundation_table(md: Path) -> list[tuple[str, str]]:
    """SKILL.md の「土台グレード」表を (条件, 帯) の列で返す（先に一致した行が勝つ）。"""
    lines = md.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if not TABLE_HEAD.match(line):
            continue
        rows = []
        for row in lines[i + 2 :]:  # +2 で区切り行 |---|---| を飛ばす
            if not row.startswith("|"):
                break
            cells = [c.strip().strip("*").strip() for c in row.strip().strip("|").split("|")]
            if len(cells) == 2:
                rows.append((cells[0], cells[1]))
        return rows
    return []


def compile_table(rows: list[tuple[str, str]]) -> list[tuple[list[re.Match], str]]:
    """採点表の各行を (条件節の並び, 帯) に解釈する。読めない行があれば ValueError。"""
    compiled = []
    for cond, band in rows:
        clauses = []
        for clause in cond.split("＆"):  # 例「◎ゼロ＆○が1つ」
            m = CLAUSE.match(clause)
            if not m:
                raise ValueError(f"採点表の条件を解釈できない: {clause}")
            clauses.append(m)
        if band not in BANDS:
            raise ValueError(f"採点表の帯が未知: {band}")
        compiled.append((clauses, band))
    return compiled


def derive_band(symbols: list[str], table: list[tuple[list[re.Match], str]]) -> str:
    counts: dict[str, int] = {}
    for s in symbols:
        counts[s] = counts.get(s, 0) + 1

    def holds(m: re.Match) -> bool:
        n = counts.get(m.group(1), 0)
        if m.group(2):  # 「◎が2つ以上」
            return n >= int(m.group(2))
        if m.group(3):  # 「◎が1つ」
            return n == int(m.group(3))
        return n == 0 if m.group(0).endswith("ゼロ") else n >= 1  # 「◎ゼロ」「◉が1つでもある」

    for clauses, band in table:
        if all(holds(c) for c in clauses):
            return band
    raise ValueError(f"採点表のどの条件にも当てはまらない: {'/'.join(symbols)}")


def expand(token: str, scale: tuple[str, ...], label: str) -> list[str]:
    """範囲指定（例「A〜S」）を、その範囲に含まれる値の列に開く。"""
    if not isinstance(token, str):
        raise ValueError(f"{label} は文字列で書く: {token!r}")
    parts = RANGE_SEP.split(token)
    if len(parts) > 2 or any(p not in scale for p in parts):
        raise ValueError(f"{label} が不正: {token}（値は {'/'.join(scale)}、範囲は「{scale[0]}〜{scale[-1]}」形式）")
    lo, hi = scale.index(parts[0]), scale.index(parts[-1])
    if lo > hi:
        raise ValueError(f"{label} の範囲が逆順: {token}")
    return list(scale[lo : hi + 1])


def shift_band(band: str, steps: int) -> str:
    return BANDS[min(max(BANDS.index(band) + steps, 0), len(BANDS) - 1)]


def check_case(where: str, case: dict, table: list[tuple[list[re.Match], str]]) -> list[str]:
    """品評ケースの採点メタデータを検証する。"""
    errs = [f"{where}: '{k}' がない（固定しないケースは null を明示する）" for k in CASE_KEYS if k not in case]
    band, symbols = case.get("target_grade_band"), case.get("target_symbols")
    steps = case.get("target_band_shift", 0)
    if not isinstance(steps, int):
        errs.append(f"{where}: target_band_shift は整数（昇格 +1／減格 -1 等）")
        steps = 0
    if symbols is not None and (not isinstance(symbols, dict) or sorted(symbols) != sorted(FOUNDATION_AXES)):
        errs.append(f"{where}: target_symbols のキーは土台3軸（{'・'.join(FOUNDATION_AXES)}）")
        symbols = None
    if band == GATE:
        if symbols is not None or steps:
            errs.append(f"{where}: {GATE} はMゲートで採点に進まないため target_symbols・target_band_shift を持たない")
        return errs

    try:
        want = expand(band, BANDS, "target_grade_band") if band is not None else None
        if symbols is None:
            if steps:
                errs.append(f"{where}: target_band_shift は target_symbols とセットで使う")
            return errs
        axes = [expand(symbols[a], SYMBOLS, f"target_symbols['{a}']") for a in FOUNDATION_AXES]
    except ValueError as e:
        return errs + [f"{where}: {e}"]

    try:  # 範囲指定があれば、その範囲で取りうる帯をすべて出す
        got = {shift_band(derive_band(list(combo), table), steps) for combo in product(*axes)}
    except ValueError as e:
        return errs + [f"{where}: {e}"]
    if want is not None and not got <= set(want):
        shown = "・".join(f"{a}{symbols[a]}" for a in FOUNDATION_AXES)
        adj = f"（{steps:+d}段）" if steps else ""
        errs.append(
            f"{where}: 記号 {shown}{adj} から採点表が導く帯は {'〜'.join(sorted(got, key=BANDS.index))} "
            f"だが target_grade_band は {band}"
        )
    return errs


def check_evals(skill_dir: Path, md: Path) -> list[str]:
    name = skill_dir.name
    path = skill_dir / "evals" / "evals.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{name}: evals.json が JSON として読めない（{e}）"]

    errs = []
    if data.get("skill_name") != name:
        errs.append(f"{name}: evals.json の skill_name '{data.get('skill_name')}' がディレクトリ名と違う")
    cases = data.get("evals")
    if not isinstance(cases, list) or not cases:
        return errs + [f"{name}: evals.json に evals（ケースの配列）がない"]

    table: list[tuple[list[re.Match], str]] = []
    if any(c.get("mode") == "品評" for c in cases):
        rows = foundation_table(md)
        if not rows:
            errs.append(f"{name}: SKILL.md に土台グレード表がなく品評ケースを検証できない")
        try:
            table = compile_table(rows)
        except ValueError as e:
            errs.append(f"{name}: SKILL.md の土台グレード表を読めない（{e}）")

    seen = set()
    for case in cases:
        where = f"{name}: evals #{case.get('id')} ({case.get('name')})"
        key = (case.get("id"), case.get("name"))
        if None in key:
            errs.append(f"{name}: evals の各ケースには id と name が要る")
            continue
        if key[0] in seen:
            errs.append(f"{where}: id が重複している")
        seen.add(key[0])
        for field in ("mode", "prompt", "expected_output"):
            if not case.get(field):
                errs.append(f"{where}: '{field}' が空")
        if not case.get("assertions"):
            errs.append(f"{where}: assertions が空")
        for legacy in ("target_grade", "target_axis"):
            if legacy in case:
                errs.append(f"{where}: '{legacy}' は廃止（{'・'.join(CASE_KEYS)} に分離した）")
        if case.get("mode") == "品評" and table:
            errs += check_case(where, case, table)
    return errs


def check(skill_dir: Path) -> list[str]:
    name = skill_dir.name
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{name}: SKILL.md missing"]

    fm = frontmatter(md)
    if not fm:
        return [f"{name}: SKILL.md has no YAML frontmatter"]

    errs: list[str] = []

    fm_name = scalar(fm, "name")
    if not fm_name:
        errs.append(f"{name}: frontmatter 'name' missing")
    else:
        if fm_name != name:
            errs.append(f"{name}: name '{fm_name}' must equal the directory name")
        if len(fm_name) > 64 or not NAME_RE.match(fm_name):
            errs.append(f"{name}: name must be lowercase/digits/hyphen and <= 64 chars")

    desc = scalar(fm, "description")
    if not desc:
        errs.append(f"{name}: frontmatter 'description' missing")
    elif len(desc) > 1024:
        errs.append(f"{name}: description is {len(desc)} chars (max 1024)")

    ver = version(fm)
    if not ver:
        errs.append(f"{name}: metadata.version missing")
    elif not changelog_has(skill_dir, ver):
        errs.append(f"{name}: CHANGELOG.md has no '## [{ver}]' section (release notes would be empty)")

    return errs + check_evals(skill_dir, md)


def main(argv: list[str]) -> int:
    if not SKILLS_DIR.is_dir():
        print("error: skills/ not found", file=sys.stderr)
        return 1

    target = argv[0] if argv else None
    errors: list[str] = []
    count = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        # Skip eval workspaces (skill-creator convention: <skill>-workspace/,
        # excluded via .gitignore's skills/**/*-workspace/). These are transient
        # eval artifacts, not skills, and have no SKILL.md.
        if skill_dir.name.endswith("-workspace"):
            continue
        if target and skill_dir.name != target:
            continue
        count += 1
        errors += check(skill_dir)

    if target and count == 0:
        print(f"error: skill not found: {target}", file=sys.stderr)
        return 1

    if errors:
        print("skill validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"ok: {count} skill(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
