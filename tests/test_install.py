"""Exercise real filesystem installation using only isolated temporary locations."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex profile test ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.codex = self.base / "codex home"
        self.skills = self.base / "agents skills"

    def run_install(self, *options, success=True):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"),
                            "--codex-home", str(self.codex), "--skills-root", str(self.skills), *options],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode == 0, success, r.stdout + r.stderr)
        return r

    def test_dry_run_has_no_side_effect(self):
        self.run_install("--dry-run")
        self.assertEqual(list(self.base.iterdir()), [])

    def test_fresh_install_idempotency_and_doctor(self):
        self.run_install()
        for name in EXPECTED:
            self.assertTrue((self.skills / name).is_symlink())
            self.assertEqual((self.skills / name).resolve(), ROOT / "skills" / name)
        config = (self.codex / "config.toml").read_bytes()
        agents = (self.codex / "AGENTS.md").read_bytes()
        self.run_install()
        self.assertEqual((self.codex / "config.toml").read_bytes(), config)
        self.assertEqual((self.codex / "AGENTS.md").read_bytes(), agents)
        self.assertFalse((self.codex / "profile-backups").exists())
        r = subprocess.run([sys.executable, str(ROOT / "scripts/doctor.py"), "--codex-home", str(self.codex),
                            "--skills-root", str(self.skills)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_existing_config_instructions_and_conflicting_skill_preserved(self):
        self.codex.mkdir()
        (self.codex / "config.toml").write_text('model = "my-own-model"\n')
        (self.codex / "AGENTS.md").write_text("My existing instructions.\n")
        conflict = self.skills / EXPECTED[0]
        conflict.mkdir(parents=True)
        (conflict / "personal.txt").write_text("Keep me.")
        self.run_install()
        self.assertEqual((self.codex / "config.toml").read_text(), 'model = "my-own-model"\n')
        self.assertTrue((self.codex / "AGENTS.md").read_text().startswith("My existing instructions.\n"))
        self.assertEqual((conflict / "personal.txt").read_text(), "Keep me.")
        self.run_install("--replace-skills")
        self.assertTrue(conflict.is_symlink())
        copies = list((self.codex / "profile-backups").glob("*/skills/*/personal.txt"))
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].read_text(), "Keep me.")

    def test_dangling_symlink_backup_and_replacement(self):
        self.skills.mkdir()
        conflict = self.skills / EXPECTED[0]
        conflict.symlink_to(self.base / "gone")
        self.run_install()
        self.assertEqual(conflict.readlink(), self.base / "gone")
        self.run_install("--replace-skills")
        report = json.loads((self.codex / "personal-profile-install.json").read_text())
        backup = Path(report["backups"][0])
        self.assertTrue(backup.is_symlink())
        self.assertEqual(backup.readlink(), self.base / "gone")

    def test_malformed_marker_fails_before_writes(self):
        self.codex.mkdir()
        agents = self.codex / "AGENTS.md"
        old = "User text\n<!-- personal-codex-home:begin -->\n"
        agents.write_text(old)
        self.run_install(success=False)
        self.assertEqual(agents.read_text(), old)
        self.assertFalse(self.skills.exists())

    def test_symlinked_instructions_target_not_changed(self):
        target = self.base / "shared-instructions.md"
        target.write_text("Shared instructions.\n")
        self.codex.mkdir()
        (self.codex / "AGENTS.md").symlink_to(target)
        self.run_install()
        self.assertEqual(target.read_text(), "Shared instructions.\n")
        self.assertFalse((self.codex / "AGENTS.md").is_symlink())
        self.assertIn("Shared instructions.", (self.codex / "AGENTS.md").read_text())


if __name__ == "__main__":
    unittest.main()
