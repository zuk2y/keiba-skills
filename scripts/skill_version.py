#!/usr/bin/env python3
"""Print a skill's metadata.version (from SKILL.md frontmatter) to stdout.

Used by the release workflow's manual (workflow_dispatch) path to derive the
release tag without a tag having been pushed first.

Usage:
    python scripts/skill_version.py <skill-name>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lint_skills import SKILLS_DIR, frontmatter, version  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    skill = sys.argv[1]
    skill_md = SKILLS_DIR / skill / "SKILL.md"
    if not skill_md.is_file():
        print(f"error: SKILL.md not found: skills/{skill}/SKILL.md", file=sys.stderr)
        return 1

    ver = version(frontmatter(skill_md))
    if not ver:
        print(f"error: could not read metadata.version from skills/{skill}/SKILL.md", file=sys.stderr)
        return 1

    print(ver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
