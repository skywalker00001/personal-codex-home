#!/usr/bin/env python3
"""Install portable instructions without copying live state or credentials."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

REPO = Path(__file__).resolve().parents[1]
START = "<!-- personal-codex-home:begin -->"
END = "<!-- personal-codex-home:end -->"


def locations(args):
    codex = Path(args.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().absolute()
    skills = Path(args.skills_root or Path.home() / ".agents/skills").expanduser().absolute()
    return codex, skills


def atomic_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".profile-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(value)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def exists(path):
    return path.exists() or path.is_symlink()


def same_link(path, source):
    return path.is_symlink() and path.resolve() == source.resolve()


def main():
    if sys.version_info < (3, 9):
        raise SystemExit("Please use Python 3.9 or newer.")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--codex-home")
    p.add_argument("--skills-root")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--replace-skills", action="store_true", help="Back up conflicting skill entries before replacing them")
    args = p.parse_args()
    codex, skills_root = locations(args)
    sources = sorted(d for d in (REPO / "skills").iterdir() if (d / "SKILL.md").is_file())
    if skills_root.resolve() == (REPO / "skills").resolve():
        raise SystemExit("The installation destination cannot be the repository's source skills directory.")
    agents = codex / "AGENTS.md"
    old_agents = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    if old_agents.count(START) != old_agents.count(END) or old_agents.count(START) > 1:
        raise SystemExit("AGENTS.md has malformed managed markers; repair them before installation.")
    managed = (START + "\n" + (REPO / "AGENTS.md").read_text(encoding="utf-8").rstrip()
               + "\n\n个人配置仓库：`" + str(REPO) + "`。需要时阅读其中 `knowledge/`；不要把旧机器状态当作当前事实。\n" + END)
    if START in old_agents:
        begin, end = old_agents.index(START), old_agents.index(END)
        if end < begin:
            raise SystemExit("AGENTS.md has reversed managed markers.")
        new_agents = old_agents[:begin] + managed + old_agents[end + len(END):]
    else:
        new_agents = old_agents.rstrip() + ("\n\n" if old_agents.strip() else "") + managed + "\n"
    changes = []
    conflicts = []
    for source in sources:
        target = skills_root / source.name
        if same_link(target, source):
            continue
        if exists(target) and not args.replace_skills:
            conflicts.append(source.name)
        else:
            changes.append((source, target))
    print("Repository:", REPO)
    print("Codex Home:", codex)
    print("Skills root:", skills_root)
    print("Skills available:", len(sources), "new/updated links:", len(changes))
    if conflicts:
        print("Preserved conflicting skills:", ", ".join(conflicts))
        print("Use --replace-skills only if you want to back up and replace those entries.")
    if (codex / "AGENTS.override.md").is_file():
        print("NOTE: existing AGENTS.override.md takes precedence over AGENTS.md; review it yourself.")
    print("Config:", "preserve existing" if exists(codex / "config.toml") else "create portable defaults")
    print("AGENTS.md:", "update managed block" if new_agents != old_agents else "already current")
    if args.dry_run:
        print("Dry run: no files or directories were changed.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    backup = codex / "profile-backups" / stamp
    backed_up = []

    def save_existing(path, relative):
        if not exists(path):
            return
        dst = backup / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            dst.symlink_to(os.readlink(path), target_is_directory=path.is_dir())
        elif path.is_dir():
            shutil.copytree(path, dst, symlinks=True)
        else:
            shutil.copy2(path, dst)
        backed_up.append(str(dst))

    codex.mkdir(parents=True, exist_ok=True)
    skills_root.mkdir(parents=True, exist_ok=True)
    for source, target in changes:
        if exists(target):
            save_existing(target, Path("skills") / target.name)
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
        target.symlink_to(source, target_is_directory=True)
    config = codex / "config.toml"
    if not exists(config):
        atomic_text(config, (REPO / "config/config.toml").read_text(encoding="utf-8"))
    if new_agents != old_agents:
        save_existing(agents, Path("AGENTS.md"))
        # Replacing a symlink with a local file preserves its original target.
        atomic_text(agents, new_agents)
    report = {"repository": str(REPO), "codex_home": str(codex), "skills_root": str(skills_root),
              "skills": [s.name for s in sources], "conflicts_preserved": conflicts,
              "backups": backed_up, "installed_at": stamp}
    atomic_text(codex / "personal-profile-install.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Installed. Open a new Codex session and inspect /skills.")
    if backed_up:
        print("Backups:", backup)


if __name__ == "__main__":
    main()
