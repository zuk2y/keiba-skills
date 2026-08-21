#!/usr/bin/env python3
"""Validate a skill and push its release tag (<skill>/v<version>).

Checks that the skill directory and SKILL.md exist and that the version matches
the SKILL.md frontmatter (metadata.version), then creates and pushes the tag
that triggers the release workflow.

Usage:
    python scripts/release.py <skill> [version] [--remote origin] [--dry-run]

If <version> is omitted, the frontmatter version is used.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"


def frontmatter_version(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    m = re.search(r"^\s*version:\s*['\"]?([^'\"\s]+)", parts[1], re.MULTILINE)
    return m.group(1) if m else None


def git(*args: str, capture: bool = False) -> str:
    r = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=capture
    )
    return (r.stdout or "").strip()


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate and push a skill's release tag.")
    ap.add_argument("skill")
    ap.add_argument("version", nargs="?", help="defaults to SKILL.md frontmatter version")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--dry-run", action="store_true", help="validate only; no tag/push")
    args = ap.parse_args()

    skill_dir = SKILLS_DIR / args.skill
    skill_md = skill_dir / "SKILL.md"

    # 1) existence
    if not skill_dir.is_dir():
        fail(f"skill directory not found: skills/{args.skill}")
    if not skill_md.is_file():
        fail(f"SKILL.md not found: skills/{args.skill}/SKILL.md")

    # 2) version matches frontmatter
    fm_ver = frontmatter_version(skill_md)
    if not fm_ver:
        fail("could not read metadata.version from SKILL.md frontmatter")
    version = args.version or fm_ver
    if version != fm_ver:
        fail(f"version mismatch: requested {version} but frontmatter is {fm_ver}")

    # run the skill validator (frontmatter + CHANGELOG) as a hard gate
    lint = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lint_skills.py"), args.skill], cwd=ROOT
    )
    if lint.returncode != 0:
        fail("skill validation failed (see lint_skills output above)")

    tag = f"{args.skill}/v{version}"
    if git("tag", "-l", tag, capture=True):
        fail(f"tag already exists: {tag}")

    # non-blocking warning
    if git("status", "--porcelain", "--", f"skills/{args.skill}", capture=True):
        print(
            f"warning: uncommitted changes under skills/{args.skill}; "
            "the tag points to HEAD and may not include them",
            file=sys.stderr,
        )

    print(f"skill:   {args.skill}")
    print(f"version: {version} (matches frontmatter)")
    print(f"tag:     {tag} -> {args.remote}")

    if args.dry_run:
        print("dry-run: no tag created or pushed")
        return 0

    git("tag", tag)
    git("push", args.remote, tag)
    print(f"pushed {tag} — the release workflow will publish the GitHub Release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
