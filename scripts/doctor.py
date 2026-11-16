#!/usr/bin/env python3
"""Read-only check of this profile's installation."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from install import REPO, START, END, locations, same_link


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--codex-home")
    p.add_argument("--skills-root")
    args = p.parse_args()
    codex, skills = locations(args)
    names = sorted(s.name for s in (REPO / "skills").iterdir() if (s / "SKILL.md").is_file())
    linked = [n for n in names if same_link(skills / n, REPO / "skills" / n)]
    agents = codex / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    result = {"codex_binary": shutil.which("codex"), "codex_home": str(codex),
              "skills_root": str(skills), "skills_expected": len(names), "skills_linked": len(linked),
              "skills_not_linked": [n for n in names if n not in linked],
              "config_exists": (codex / "config.toml").is_file(),
              "managed_instructions": START in text and END in text,
              "override_takes_precedence": (codex / "AGENTS.override.md").is_file()}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(linked) != len(names) or not result["config_exists"] or not result["managed_instructions"]:
        return 1
    print("Profile files verified. Login, model access, skill discovery and remote connectivity require the target client.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
