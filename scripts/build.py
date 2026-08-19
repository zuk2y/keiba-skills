#!/usr/bin/env python3
"""Build distributable zips for skills under skills/.

Each zip contains the skill folder (SKILL.md + bundled LICENSE/NOTICE/CHANGELOG),
ready to upload to skill-aware AI chats (e.g. Claude apps).

Usage:
    python scripts/build.py              # build every skill
    python scripts/build.py <skill-name> # build only that skill
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"


def build(skill_dir: Path) -> Path:
    zip_path = DIST_DIR / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                zf.write(path, path.relative_to(SKILLS_DIR).as_posix())
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
