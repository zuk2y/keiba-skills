#!/usr/bin/env python3
"""Build distributable zips for skills under skills/.

Each zip contains the skill folder (SKILL.md + bundled LICENSE/NOTICE/CHANGELOG),
ready to upload to skill-aware AI chats (e.g. Claude apps).

Usage:
    python scripts/build.py              # build every skill
    python scripts/build.py <skill-name> # build only that skill
"""

from __future__ import annotations

import fnmatch
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"

# 配布 zip から除外するパターン（公式 skill-creator の package_skill.py に準拠）。
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store"}
# スキルのルート直下でのみ除外するディレクトリ（eval 資材はオーサリング用で配布しない）。
ROOT_EXCLUDE_DIRS = {"evals"}


def should_exclude(rel_path: Path) -> bool:
    """rel_path は SKILLS_DIR からの相対パス（parts[0] がスキル名）。"""
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, pat) for pat in EXCLUDE_GLOBS)


def build(skill_dir: Path) -> Path:
    zip_path = DIST_DIR / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(SKILLS_DIR)
            if should_exclude(rel):
                continue
            zf.write(path, rel.as_posix())
    return zip_path


def main(argv: list[str]) -> int:
    target = argv[0] if argv else None

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    built = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        if target and skill_dir.name != target:
            continue
        zip_path = build(skill_dir)
        print(f"built {zip_path.relative_to(ROOT).as_posix()}")
        built += 1

    if target and built == 0:
        print(f"error: skill not found: {target}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
