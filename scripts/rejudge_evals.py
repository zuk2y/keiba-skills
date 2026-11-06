#!/usr/bin/env python3
"""Re-judge saved `claude plugin eval` answers with one llm grader and quote each violation.

The runner keeps only the judges' votes, not the sentences they objected to. This script sends each
saved answer, together with the criterion text of one llm grader, to `claude -p` and asks for the
violating sentences labelled by type. Pointing --eval-dir at one version applies the same criterion to
the answers of every version, so old/new runs can be compared even when the bundled SKILL.md text
(SKILL_CONTEXT in gen_plugin_evals.py) differs between them.

Usage:
    python scripts/rejudge_evals.py <result.json>... [--grader aNN] [--eval-dir DIR] [--votes N]
                                    [--jobs N] [--model opus] [--out DIR]

- result.json: files written by `claude plugin eval --json` (one or more cases each).
- --grader: grader id to apply. Default: the case's llm grader whose condition starts with 「内部呼称」.
- --eval-dir: directory holding <skill>/<case>/graders/ (default: evals/ of this checkout).
- Types come from the 漏れの型 column of the table under 「## 出力の原則」 in the skill's SKILL.md.
- Each verdict is one judge call; --votes N asks N times and takes the majority. Replies are kept in
  --out (default: evals/results/rejudge-<timestamp>/) and reused when the script is run again.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_OFF = "Bash,Edit,Write,Read,Glob,Grep,WebSearch,WebFetch,Agent"


def leak_types(skill: str) -> list[str]:
    """出力の原則の表から「漏れの型」の列を読む（無ければ空）。"""
    md = ROOT / "skills" / skill / "SKILL.md"
    if not md.exists():
        return []
    section = md.read_text(encoding="utf-8").split("## 出力の原則", 1)[-1].split("\n## ", 1)[0]
    types: list[str] = []
    in_table = False
    for line in section.splitlines():
        cell = re.match(r"^\s*\|\s*([^|]+?)\s*\|", line)
        if not in_table:
            in_table = bool(cell) and cell.group(1) == "漏れの型"
        elif not cell:
            break  # 表の終わり（次の表は対象外）
        elif not set(cell.group(1)) <= {"-"}:
            types.append(cell.group(1))
    return types


def grader_body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[2]


def pick_grader(graders_dir: Path, grader: str | None) -> Path:
    if grader:
        return graders_dir / f"{grader}.md"
    for path in sorted(graders_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "type: llm" in text and re.search(r"^条件: 内部呼称", text, re.M):
            return path
    raise SystemExit(f"内部呼称の grader が見つからない: {graders_dir}")


def answer_of(run: dict) -> str:
    """回答本文は llm grader の evidence に入っている（regex/tool grader の evidence は空）。"""
    texts = [g.get("evidence") or "" for g in run.get("graders", [])]
    return max(texts, key=len).split("Sources:")[0].rstrip()


def judge(prompt: str, model: str, cache: Path) -> str:
    if cache.exists() and cache.stat().st_size:
        return cache.read_text(encoding="utf-8")
    proc = subprocess.run(
        ["claude", "-p", "--model", model, "--max-turns", "1", "--disallowedTools", TOOLS_OFF],
        input=prompt,
        capture_output=True,
        text=True,
        cwd=cache.parent,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"judge call failed ({cache.name}): {proc.stderr.strip() or proc.stdout.strip()}")
    cache.write_text(proc.stdout, encoding="utf-8")
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("results", nargs="+", type=Path)
    ap.add_argument("--grader")
    ap.add_argument("--eval-dir", type=Path, default=ROOT / "evals")
    ap.add_argument("--votes", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--model", default="opus")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or ROOT / "evals" / "results" / f"rejudge-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)

    jobs = []  # (label, prompt, cache paths)
    for result in args.results:
        data = json.loads(result.read_text(encoding="utf-8"))
        tag = result.parent.name
        for case in data["cases"]:
            skill, name = Path(case["dir"]).parent.name, Path(case["dir"]).name
            gpath = pick_grader(args.eval_dir / skill / name / "graders", args.grader)
            types = leak_types(skill) + ["その他"]
            tail = (
                "\n\n---\n以下が判定対象の回答本文。条件に反する文を本文からそのまま引用し、1行に1件、"
                f"「- [型] 「引用」」の形で挙げよ。型は次のいずれか: {'／'.join(types)}。"
                "境界例は挙げない。最後の行に PASS か FAIL だけを書け。\n\n<回答>\n"
            )
            for i, run in enumerate(case["arms"]["with"]):
                prompt = grader_body(gpath) + tail + answer_of(run) + "\n</回答>"
                label = f"{tag}/{name[:2]}/run{i}/{gpath.stem}"
                caches = [out / f"{label.replace('/', '__')}__v{v}.txt" for v in range(args.votes)]
                jobs.append((label, prompt, caches))

    def run_job(job: tuple) -> tuple[str, list[str]]:
        label, prompt, caches = job
        return label, [judge(prompt, args.model, c) for c in caches]

    with ThreadPoolExecutor(args.jobs) as ex:
        replies = list(ex.map(run_job, jobs))

    tally: Counter = Counter()
    for label, texts in replies:
        verdicts = ["PASS" if re.search(r"PASS\s*$", t.strip()) else "FAIL" for t in texts]
        verdict = Counter(verdicts).most_common(1)[0][0]
        found = sorted({ty for t in texts for ty in re.findall(r"^\s*-\s*\[([^\]]+)\]", t, re.M)})
        print(f"{label}\t{verdict}\t{'/'.join(verdicts)}\t{','.join(found)}")
        tag = label.split("/")[0]
        tally[(tag, "PASS")] += verdict == "PASS"
        for ty in found:
            tally[(tag, ty)] += 1
    print()
    for (tag, ty), n in sorted(tally.items()):
        print(f"{tag}\t{ty}\t{n}")
    print(f"\nreplies: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
