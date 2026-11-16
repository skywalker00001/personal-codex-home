#!/usr/bin/env python3
"""Render a public-key-only Notebook bootstrap isolated from the interactive shell."""
import argparse
import base64
import ipaddress
from pathlib import Path
import re
import shlex


def render(ip, user, public_key):
    ipaddress.IPv4Address(ip)
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', user):
        raise ValueError('Invalid SSH user')
    parts = public_key.strip().split()
    if len(parts) < 2 or parts[0] != 'ssh-ed25519':
        raise ValueError('Expected an ed25519 PUBLIC key')
    blob = base64.b64decode(parts[1], validate=True)
    if len(blob) != 51 or blob[:19] != b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20':
        raise ValueError('Invalid ed25519 public key')
    key = ' '.join(parts)
    body = (Path(__file__).resolve().parent.parent / 'assets/notebook_sshd.sh').read_text()
    return (shlex.join(['bash','-s','--',ip,user,key]) + " <<'CODEX_AIS_NOTEBOOK_BOOTSTRAP'\n"
            + body + 'CODEX_AIS_NOTEBOOK_BOOTSTRAP\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ip',required=True)
    p.add_argument('--user',default='work')
    p.add_argument('--public-key',type=Path,default=Path.home()/'.ssh/id_ed25519_ais.pub')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    text=render(a.ip,a.user,a.public_key.read_text())
    if a.output:
        a.output.write_text(text)
        a.output.chmod(0o700)
        print('Public-key bootstrap written:',a.output)
    else:
        print(text,end='')


if __name__=='__main__':
    main()
