#!/usr/bin/env python3
"""Check publishable contents, local links, the bundled archive and SHA256 files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/files.sha256.json"
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
SECRET_PATTERNS = {
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{25,}"),
    "github-fine-grained-token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}"),
    "openai-key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}"),
    "credential-url": re.compile(r"https?://[^\s/:@]+:[^\s/@]+@"),
}
FORBIDDEN_NAMES = {"auth.json", "history.jsonl", "session_index.jsonl", ".git-credentials",
                   "id_rsa", "id_ed25519", "kubeconfig", "deploy.env", ".env"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def files():
    return sorted(p for p in ROOT.rglob("*") if not any(x in SKIP_DIRS for x in p.relative_to(ROOT).parts)
                  and p.is_file() and p != MANIFEST)


def check_text(name, data, errors):
    text = data.decode("utf-8", errors="replace")
    for label, pat in SECRET_PATTERNS.items():
        if pat.search(text):
            # Report only the file and classification, never the matching credential.
            errors.append(name + ": possible " + label)


def check_archive(path, errors):
    with tarfile.open(path, "r:gz") as archive:
        content = {}
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or not name.parts or name.parts[0] != "clawbot-feishu":
                errors.append("Unsafe archive path: " + member.name)
                continue
            if not member.isfile():
                errors.append("Unexpected non-file archive entry: " + member.name)
                continue
            if member.size > 2_000_000:
                errors.append("Oversized archive entry: " + member.name)
                continue
            data = archive.extractfile(member).read()
            content[str(name.relative_to("clawbot-feishu"))] = data
            if name.name in FORBIDDEN_NAMES or name.suffix in {".sqlite", ".db", ".key", ".pem"}:
                errors.append("Forbidden private archive file: " + member.name)
            check_text(member.name, data, errors)
        sums = content.get("SHA256SUMS")
        if sums is None:
            errors.append("Source archive has no SHA256SUMS")
        else:
            covered = set()
            for line in sums.decode().splitlines():
                sha, filename = line.split(maxsplit=1)
                filename = filename.lstrip("*")
                if filename.startswith("./"):
                    filename = filename[2:]
                covered.add(filename)
                if filename not in content or digest(content[filename]) != sha:
                    errors.append("Archive checksum mismatch: " + filename)
            unchecked = set(content) - covered - {"SHA256SUMS"}
            if unchecked:
                errors.append("Archive files missing checksums: " + ", ".join(sorted(unchecked)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    errors = []
    actual = {}
    for path in files():
        name = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            errors.append("Repository contains a symlink: " + name)
        if path.name in FORBIDDEN_NAMES or path.suffix in {".sqlite", ".db", ".pem", ".key"}:
            errors.append("Forbidden private file: " + name)
        if path.stat().st_size > 2_000_000:
            errors.append("Unexpected large file: " + name)
        data = path.read_bytes()
        actual[name] = digest(data)
        if path.name.endswith(".tar.gz"):
            check_archive(path, errors)
        else:
            check_text(name, data, errors)
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", data.decode("utf-8")):
                target = target.strip("<>").split("#", 1)[0]
                if not target or target.startswith(("https://", "http://", "mailto:", "/")):
                    continue
                # Code examples and prose references need not be actual files.
                if any(c in target for c in [" ", "$", "{", "<", ">"]):
                    continue
                if not (path.parent / target).exists():
                    errors.append(name + ": missing relative reference " + target)
    if errors:
        print(json.dumps({"passed": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    if args.write_manifest:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif not MANIFEST.exists():
        errors.append("Missing manifest; run with --write-manifest after reviewing changes.")
    elif json.loads(MANIFEST.read_text(encoding="utf-8")) != actual:
        expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
        changed = sorted(n for n in set(expected) | set(actual) if expected.get(n) != actual.get(n))
        errors.append("Manifest differs: " + ", ".join(changed))
    print(json.dumps({"passed": not errors, "files_checked": len(actual), "skills": len(list((ROOT / 'skills').glob('*/SKILL.md'))),
                      "payload_bytes": sum(p.stat().st_size for p in files()), "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
