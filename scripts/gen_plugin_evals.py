#!/usr/bin/env python3
"""Generate `claude plugin eval` cases from each skill's evals/evals.json.

evals.json (skill-creator layout, validated by lint_skills.py) is the source of
truth. This script derives the case directories the official runner reads:

  evals/<skill>/<NN-name>/prompt.md              run limits + the user prompt
  evals/<skill>/<NN-name>/graders/skill-fired.md tool_used: the skill was invoked
  evals/<skill>/<NN-name>/graders/aNN.md         one llm grader per assertion

Usage:
    python scripts/gen_plugin_evals.py            # regenerate for every skill with evals.json
    python scripts/gen_plugin_evals.py <skill>    # one skill only
    python scripts/gen_plugin_evals.py --check    # exit 1 if generated files are stale (pre-commit)

Run the suite with `claude plugin eval` (see README.md, 評価).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
EVAL_DIR = ROOT / "evals"  # `claude plugin eval` の既定 eval ディレクトリ（結果は evals/results/ に出る）

# 1 ケースの実行上限。skill は 1 頭あたり事前検索 3 種＋候補ごとの事後検索を要求するので、
# 実測（中央値 18 ターン・最大 26 ターン）に余裕を持たせる。暴走は費用上限（--max-cost-usd）で止める。
RUNS = 1  # 既定 n=1。割れるケースは `--runs 3` で個別に増やす
MAX_TURNS = 40
TIMEOUT_SECONDS = 1200
ALLOWED_TOOLS = ["Skill", "WebSearch"]  # WebSearch は実行時に `--allow-tools WebSearch` の grant も要る

# mode → --tag で選べるタグ
MODE_TAGS = {"生成": ["generate"], "品評": ["critique"], "生成→品評": ["generate", "critique"]}

# 評価プロファイル。判定や手順には触れず、トークン効率と採点対象（最終メッセージ）だけを揃える。
EVAL_PROFILE = (
    "評価用の実行条件（スキルの手順や判定は変えない）:\n"
    "- 回答は最終メッセージに全文を書く。ファイルには書き出さない。\n"
    "- 互いに独立した検索は 1 ターンにまとめて並列に発行する。検索の回数や内容を減らす指示ではない。\n"
    "- 依頼者への確認が必要なときは、確認したい内容を最終メッセージに書いて終える。"
)

CRITERIA = (
    "依頼文: {prompt}\n"
    "\n"
    "次の条件を満たしていれば PASS、満たしていなければ FAIL。\n"
    "\n"
    "条件: {assertion}\n"
    "\n"
    "判定は回答本文に書かれた内容だけを根拠にする。"
    "条件が「〜がある／〜している」型なら、その内容が本文に実際に書かれているときだけ PASS"
    "（語句の表面的な一致では PASS にしない）。"
    "条件が「〜がない／〜していない」型なら、本文に該当する記述が見当たらなければ PASS、見つかれば FAIL。\n"
)


# 主節が否定形（〜がない／〜していない）だけの条件への注意書き。小型ジャッジは「挙げられたものが本文にない」ことを
# 「記載がないので FAIL」と逆に読むことがある（実測: Haiku が 3 票とも誤判定し、この注意書きで 3 票とも正しく PASS）。
# 肯定の節を併せ持つ条件（「〜である（…していない）」「〜として扱い、〜していない」）には付けない。
NEGATIVE_END = re.compile(r"(ない|なく|せず|おらず)$")
NEGATIVE_HINT = (
    "注意: この条件は「〜がない／〜していない」ことを求める否定型。挙げられたものが本文に見当たらなければ PASS、"
    "見つかれば FAIL。挙げられたものが本文に無いことを「記載がない」という理由で FAIL にしてはいけない。\n"
)


def negative_only(assertion: str) -> bool:
    """主節が否定形で終わり、肯定の節を併せ持たない条件か（括弧書きは補足として除いて見る）。"""
    main = re.sub(r"（[^（）]*）", "", assertion.strip()).rstrip("。")
    return "、" not in main and NEGATIVE_END.search(main) is not None


def yq(value: object) -> str:
    """YAML flow scalar/sequence として安全な表現（JSON は YAML のサブセット）。"""
    return json.dumps(value, ensure_ascii=False)


def case_dir_name(case: dict) -> str:
    return f"{int(case['id']):02d}-{case['name']}"


def render_case(skill: str, case: dict) -> dict[str, str]:
    """1 ケースぶんの {相対パス: 内容} を返す。"""
    mode = case.get("mode", "")
    if mode not in MODE_TAGS:
        raise ValueError(f"{skill} evals #{case.get('id')}: mode が未知: {mode!r}（{'/'.join(MODE_TAGS)}）")
    if case.get("files"):
        raise ValueError(f"{skill} evals #{case.get('id')}: files は未対応（case.yaml の context.add_dirs を検討）")

    desc = f"{mode}｜{case.get('target', '')}"
    band = case.get("target_grade_band")
    if band:
        desc += f"｜期待帯 {band}"

    prompt_md = (
        "---\n"
        f"description: {yq(desc)}\n"
        f"expected_outcome: {yq(case['expected_output'])}\n"
        f"tags: {yq(MODE_TAGS[mode])}\n"
        f"runs: {RUNS}\n"
        f"max_turns: {MAX_TURNS}\n"
        f"timeout_seconds: {TIMEOUT_SECONDS}\n"
        f"allowed_tools: {yq(ALLOWED_TOOLS)}\n"
        f"append_system_prompt: {yq(EVAL_PROFILE)}\n"
        "---\n"
        f"{case['prompt'].rstrip()}\n"
    )
    files = {"prompt.md": prompt_md}

    # スキルが発火したか（`plugin:skill` の名前空間付きでも一致）。
    skill_call = r'"skill"\s*:\s*"(?:[\w-]+:)?' + skill + '"'
    files["graders/skill-fired.md"] = f"---\ntype: tool_used\ntool: Skill\ninput_match: {yq(skill_call)}\n---\n"
    for i, assertion in enumerate(case["assertions"], start=1):
        body = CRITERIA.format(prompt=case["prompt"].strip(), assertion=assertion)
        if negative_only(assertion):
            body += "\n" + NEGATIVE_HINT
        files[f"graders/a{i:02d}.md"] = "---\ntype: llm\n---\n" + body
    return files


def render_skill(skill_dir: Path) -> dict[str, str]:
    """スキル 1 つぶんの {evals/<skill>/ からの相対パス: 内容}。"""
    data = json.loads((skill_dir / "evals" / "evals.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for case in data["evals"]:
        prefix = case_dir_name(case)
        for rel, content in render_case(skill_dir.name, case).items():
            out[f"{prefix}/{rel}"] = content
    return out


def on_disk(skill_eval_dir: Path) -> dict[str, str]:
    if not skill_eval_dir.is_dir():
        return {}
    return {
        p.relative_to(skill_eval_dir).as_posix(): p.read_text(encoding="utf-8")
        for p in skill_eval_dir.rglob("*")
        if p.is_file()
    }


def sync(skill_eval_dir: Path, desired: dict[str, str]) -> int:
    """生成物をディスクに反映し、消えたケースのディレクトリを片付ける。書き換えた数を返す。"""
    current = on_disk(skill_eval_dir)
    changed = 0
    for rel, content in desired.items():
        if current.get(rel) != content:
            path = skill_eval_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            changed += 1
    keep_dirs = {rel.split("/", 1)[0] for rel in desired}
    for child in skill_eval_dir.iterdir() if skill_eval_dir.is_dir() else []:
        if child.is_dir() and child.name not in keep_dirs:
            shutil.rmtree(child)
            changed += 1
    for rel in current:
        if rel not in desired and (skill_eval_dir / rel).exists():
            (skill_eval_dir / rel).unlink()
            changed += 1
    return changed


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if a != "--check"]
    target = args[0] if args else None

    stale: list[str] = []
    count = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not (skill_dir / "evals" / "evals.json").is_file():
            continue
        if target and skill_dir.name != target:
            continue
        count += 1
        skill_eval_dir = EVAL_DIR / skill_dir.name
        try:
            desired = render_skill(skill_dir)
        except (ValueError, KeyError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        if check:
            current = on_disk(skill_eval_dir)
            stale += sorted(f"{skill_dir.name}/{rel}" for rel in set(desired) ^ set(current))
            changed = (rel for rel in desired if rel in current and current[rel] != desired[rel])
            stale += sorted(f"{skill_dir.name}/{rel}" for rel in changed)
        else:
            n = sync(skill_eval_dir, desired)
            where = skill_eval_dir.relative_to(ROOT).as_posix()
            print(f"{skill_dir.name}: {len(desired)} files ({n} updated) -> {where}/")

    if target and count == 0:
        print(f"error: skill not found or has no evals.json: {target}", file=sys.stderr)
        return 1
    if stale:
        print("plugin eval cases are stale; run `python3 scripts/gen_plugin_evals.py`:", file=sys.stderr)
        for s in stale[:20]:
            print(f"  - evals/{s}", file=sys.stderr)
        if len(stale) > 20:
            print(f"  ... and {len(stale) - 20} more", file=sys.stderr)
        return 1
    if check:
        print(f"ok: plugin eval cases up to date ({count} skill(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
