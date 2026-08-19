#!/usr/bin/env python3
"""Print a skill's CHANGELOG.md section for a given version to stdout.

Used by the release workflow to turn the changelog entry into the Release body.

Usage:
    python scripts/release_notes.py <skill-name> <version>
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract(changelog: Path, version: str) -> str:
    head = f"## [{version}]"
    out: list[str] = []
    capturing = False
    for line in changelog.read_text(encoding="utf-8").splitlines():
        if line.startswith(head):
            capturing = True
            continue
        if capturing and line.startswith("## ["):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: release_notes.py <skill> <version>", file=sys.stderr)
        return 2
    skill, version = argv
    changelog = ROOT / "skills" / skill / "CHANGELOG.md"
    notes = extract(changelog, version) if changelog.is_file() else ""
    print(notes or f"See skills/{skill}/CHANGELOG.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
