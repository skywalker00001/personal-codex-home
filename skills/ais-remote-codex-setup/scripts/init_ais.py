#!/usr/bin/env python3
"""Inspect Houyi's AIS initializer; apply only missing settings, with local backups."""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

REVIEWED = {
 'restart_all_commands.sh': '233511be3bc474cbd4e19f5fe7c816570f96d9920071232f89de03a6faf6f2ea',
 'install_package.sh': 'dd65b68c2a8a7da137f22237b5fb98eb9f6e8fc93fab15556663fe0e3bac82a1',
 'configurate_bashrc_and_vscode_debug.sh': '44a1e7e8bbba440a40b7c101bd79e388fc6a5817662f428b3becdd7865c3d8be',
 'mount_datasets.sh': '8c60e43266b1b957c175f6d2446fcc0fcbc2a7eb223f3eb9151e686639f95539',
}
PACKAGES = ['tmux','gawk','net-tools','zip','unzip','ffmpeg','parallel',
            'iputils-ping','aria2','yt-dlp','ripgrep','rclone','python3-venv']
PATH_BLOCK = '# ais-remote-codex-setup:path\nexport PATH="$HOME/.local/bin:$PATH"\n'
MARKER = '# ais-remote-codex-setup:interactive-profile'


def reviewed_source(source):
    texts = {}
    for name, expected in REVIEWED.items():
        p = source / 'restart_commands' / name
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Initializer changed; review before applying: ' + name)
        texts[name] = data.decode()
    return texts


class Merge:
    def __init__(self, home, apply=False):
        self.home, self.apply = Path(home), apply
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.backups = self.home / '.local/state/ais-remote-codex-setup/backups' / stamp
        self.changes = 0

    def note(self, action, path):
        print(action, Path(path).relative_to(self.home))

    def linked_target(self, path):
        # Never descend through a linked destination directory such as ~/.ssh.
        current = path
        while current != self.home:
            if current.is_symlink():
                return True
            if current == current.parent:
                raise ValueError('Target is outside the selected home')
            current = current.parent
        return False

    def backup(self, path):
        if path.exists():
            target = self.backups / path.relative_to(self.home)
            if self.linked_target(target):
                raise ValueError('Backup directory contains a symlink; inspect before applying')
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(path, target, follow_symlinks=False)
            target.chmod(0o600)

    def text(self, path, text):
        if self.linked_target(path):
            self.note('PRESERVE_SYMLINK', path)
            return
        old = path.read_text() if path.exists() else None
        if old == text:
            return
        self.note('UPDATE' if old is not None else 'ADD', path)
        self.changes += 1
        if self.apply:
            self.backup(path)
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_text(text)
            path.chmod(0o600)

    def copy_missing(self, src, dst, private=False):
        if src.is_symlink():
            print('SKIP_SOURCE_SYMLINK', src.name)
            return
        if not src.exists():
            print('SOURCE_MISSING', src.name)
            return
        if self.linked_target(dst):
            self.note('PRESERVE_SYMLINK', dst)
            return
        if src.is_dir():
            if dst.exists() and not dst.is_dir():
                self.note('PRESERVE_CONFLICT', dst)
                return
            if self.apply:
                dst.mkdir(parents=True, exist_ok=True, mode=0o700)
            for child in sorted(src.iterdir()):
                # authorized_keys is handled as a union before walking .ssh.
                if private and dst == self.home / '.ssh' and child.name == 'authorized_keys':
                    continue
                self.copy_missing(child, dst / child.name, private)
            return
        if not src.is_file():
            print('SKIP_NONREGULAR_SOURCE', src.name)
            return
        if dst.exists():
            if dst.is_file() and src.read_bytes() == dst.read_bytes():
                return
            self.note('PRESERVE_CONFLICT', dst)
            return
        self.note('COPY_MISSING', dst)
        self.changes += 1
        if self.apply:
            dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(src, dst)
            dst.chmod(0o600 if private else 0o644)

    def configure(self, source):
        bashrc = self.home / '.bashrc'
        old = bashrc.read_text() if bashrc.exists() else ''
        new = old
        if '# ais-remote-codex-setup:path' not in new:
            new = PATH_BLOCK + new
        profile = source / '.bashrc'
        if profile.is_file() and MARKER not in new and not (bashrc.is_symlink() and bashrc.resolve() == profile.resolve()):
            quoted = shlex.quote(str(profile))
            contents = profile.read_text().strip()
            already_imported = bool(contents) and contents in old
            new += ('\n' + MARKER + '\ncase $- in\n  *i*)\n'
                    + ('' if already_imported else '    if [ -r ' + quoted + ' ]; then . ' + quoted + '; fi\n')
                    + '    export PATH="$HOME/.local/bin:$PATH"\n  ;;\nesac\n')
        # Syntax-check in memory BEFORE updating the live shell profile.
        subprocess.run(['bash','-n'], input=new, text=True, capture_output=True, check=True)
        self.text(bashrc, new)
        # Bash reads the first existing login profile, not necessarily .profile.
        login_names = ['.profile'] + [name for name in ('.bash_profile','.bash_login')
                                      if os.path.lexists(self.home/name)]
        for name in login_names:
            login = self.home/name
            if self.linked_target(login):
                self.note('PRESERVE_SYMLINK', login)
                continue
            old_login = login.read_text() if login.exists() else ''
            marker = '# ais-remote-codex-setup:login-path'
            if marker not in old_login:
                # Append after user PATH assignments in the active login file.
                login_text = old_login + '\n' + marker + '\nexport PATH="$HOME/.local/bin:$PATH"\n'
                subprocess.run(['bash','-n'], input=login_text, text=True, capture_output=True, check=True)
                self.text(login, login_text)

        auth_src = source / '.ssh/authorized_keys'
        auth_dst = self.home / '.ssh/authorized_keys'
        if auth_src.is_file() and not auth_src.is_symlink() and not (source/'.ssh').is_symlink():
            if self.linked_target(auth_dst):
                self.note('PRESERVE_SYMLINK', auth_dst)
            else:
                current = auth_dst.read_text() if auth_dst.exists() else ''
                # Retain every existing authorization and append complete source lines.
                lines = set(current.splitlines())
                extra = [line for line in auth_src.read_text().splitlines() if line.strip() and line not in lines]
                if extra:
                    self.text(auth_dst, current.rstrip('\n') + '\n' + '\n'.join(extra) + '\n')
        for name in ['.ssh', '.bypy', '.git-credentials']:
            self.copy_missing(source/name, self.home/name, private=True)
        for name in ['.vscode/launch.json','pyrightconfig.json']:
            self.copy_missing(source/name, self.home/name)
        cursor = self.home / '.cursorignore'
        if (source/'.cursorignore').is_file() and not os.path.lexists(cursor):
            self.note('LINK_MISSING', cursor)
            self.changes += 1
            if self.apply:
                cursor.symlink_to(source/'.cursorignore')
        return self.changes


def git_identity(text, apply):
    for line in text.splitlines():
        words = shlex.split(line, comments=True)
        if len(words) != 5 or words[:3] != ['git','config','--global'] or words[3] not in ('user.name','user.email'):
            continue
        check = subprocess.run(['git','config','--global','--get',words[3]], capture_output=True, text=True)
        if check.returncode == 0 and check.stdout.strip():
            print('GIT_IDENTITY_PRESENT',words[3])
        else:
            print('GIT_IDENTITY_MISSING',words[3])
            if apply:
                subprocess.run(words, check=True, capture_output=True)


def install_packages(apply):
    missing=[]
    for pkg in PACKAGES:
        r=subprocess.run(['dpkg-query','-W','-f=${Status}',pkg],capture_output=True,text=True)
        if r.returncode or r.stdout.strip()!='install ok installed':
            missing.append(pkg)
    print('PACKAGES_MISSING', ','.join(missing) or 'none')
    if apply and missing:
        admin=[] if os.geteuid()==0 else ['sudo','-n']
        subprocess.run(admin+['apt-get','update','-qq'],check=True)
        subprocess.run(admin+['env','DEBIAN_FRONTEND=noninteractive','apt-get','install','-y','--no-install-recommends',*missing],check=True)


def ais_login(source, text, apply):
    commands=[]
    for line in text.splitlines():
        words=shlex.split(line,comments=True)
        if words[:2]==['ais','login']:
            commands.append(words)
    if len(commands)!=1:
        raise ValueError('Expected exactly one reviewed AIS login command')
    words=commands[0]
    # Never expose raw argv/stdout/stderr or exceptions containing login arguments.
    options={}
    it=iter(words[2:])
    for flag in it:
        if '=' in flag:
            k,v=flag.split('=',1)
        else:
            k,v=flag,next(it)
        if k not in ('--email','--host','--token') or k in options:
            raise ValueError('Unsupported AIS login flags; inspect source privately')
        options[k]=v
    if set(options)!= {'--email','--host','--token'}:
        raise ValueError('Missing AIS login options')
    print('AIS_LOGIN_ACCOUNT',options['--email'],'HOST',options['--host'])
    candidates=[source/'miniforge3/envs/turbodiffusion/bin/ais',source/'miniforge3/bin/ais',Path.home()/'.local/bin/ais']
    found=shutil.which('ais')
    if found:
        candidates.insert(0,Path(found))
    cli=next((p for p in candidates if p.is_file() and os.access(p,os.X_OK)),None)
    print('AIS_CLI',str(cli) if cli else 'missing; isolated venv required')
    if not apply:
        return
    if cli is None:
        venv=Path.home()/'.local/share/ais-remote-codex-setup/ais-venv'
        # Installing python3-venv, if missing, is handled explicitly before this stage.
        r=subprocess.run([sys.executable,'-m','venv',str(venv)],capture_output=True)
        if r.returncode:
            raise ValueError('Cannot create AIS venv; install python3-venv and retry')
        r=subprocess.run([str(venv/'bin/python'),'-m','pip','install','shopee-ais','-i','https://pypi.garenanow.com/simple/'],capture_output=True)
        if r.returncode:
            raise ValueError('AIS CLI installation failed; inspect private pip output interactively')
        cli=venv/'bin/ais'
        dst=Path.home()/'.local/bin/ais'
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not os.path.lexists(dst):
            dst.symlink_to(cli)
    try:
        r=subprocess.run([str(cli),*words[1:]],capture_output=True,timeout=120)
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError('AIS login failed to finish; retry account login interactively') from None
    if r.returncode:
        raise ValueError('AIS login failed; use current personal AIS credentials interactively')
    print('AIS_LOGIN_OK; dataset mounts were not executed')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('/home/work/houyi'))
    p.add_argument('--apply',action='store_true')
    p.add_argument('--packages',action='store_true')
    p.add_argument('--ais-login',action='store_true')
    a=p.parse_args()
    if sys.platform!='linux' or Path.home()!=Path('/home/work') or os.getuid()==0:
        raise ValueError('Run on the AIS Notebook as work with HOME=/home/work')
    texts=reviewed_source(a.source)
    print('SOURCE_REVIEW_OK; mode=', 'APPLY' if a.apply else 'PLAN')
    merge=Merge(Path.home(),a.apply)
    merge.configure(a.source)
    git_identity(texts['restart_all_commands.sh'],a.apply)
    install_packages(a.apply and a.packages)
    # Plan also reports the source account and CLI without invoking authentication.
    ais_login(a.source,texts['mount_datasets.sh'],a.apply and a.ais_login)
    print('CONFIG_CHANGES',merge.changes)
    if a.apply:
        print('BACKUP_DIRECTORY',merge.backups)
    print('INIT_COMPLETE; validate login shell, SSH, Codex and any requested mounts separately')


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        # No subprocess argv, login token, copied file contents, or traceback in logs.
        print('INIT_FAILED:',str(exc) if isinstance(exc,ValueError) else type(exc).__name__,file=sys.stderr)
        sys.exit(1)
