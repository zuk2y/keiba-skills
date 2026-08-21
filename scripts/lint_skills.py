#!/usr/bin/env python3
"""Validate every skill under skills/.

Per skill it checks:
  - SKILL.md exists and has YAML frontmatter
  - name: present, equals the directory name, lowercase/digits/hyphen, <= 64 chars
  - description: present, <= 1024 chars
  - metadata.version: present
  - CHANGELOG.md exists and has a "## [<version>]" section
    (so release.py / the release workflow produce real notes)

Exits non-zero if any skill fails. Used by pre-commit and the lint workflow.
"""

from __future__ import annotations

import re
import sys
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

    return errs


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
