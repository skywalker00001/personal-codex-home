#!/usr/bin/env python3
"""Generate a host-bound launcher without starting services or copying state."""
import argparse
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess


BASE = Path('/aigc/avatar/houyi')
TEMPLATE = BASE / 'vscode_h200/start_all_pretrain_f_224_worker_3.sh'
BACKUP = BASE / 'migration_backups/b200_to_h200_20261016T091927Z'


def render_launcher(host, destination):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,62}', host):
        raise ValueError('Use a short hostname containing letters, digits and hyphens, up to 63 characters.')
    text = TEMPLATE.read_text()
    state = BACKUP / ('target_' + host.replace('-', '_'))
    replacements = [
        (r'^target=[^\n]*$', 'target=' + shlex.quote(host)),
        (r'^state="\$backup/[^"\n]+"$', 'state="$backup/' + state.name + '"'),
        (r'^this_script=[^\n]*$', 'this_script=' + shlex.quote(str(destination))),
    ]
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, lambda _: replacement, text, flags=re.M)
        if count != 1:
            raise ValueError('Startup template structure changed; inspect it before adapting a target.')
    checked = subprocess.run(['bash', '-n'], input=text, text=True, capture_output=True)
    if checked.returncode:
        raise ValueError('Generated shell syntax is invalid: ' + checked.stderr.strip())
    return text, state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=socket.gethostname().split('.', 1)[0])
    parser.add_argument('--output', type=Path, help='Optional launcher location; existing different files are never overwritten.')
    parser.add_argument('--write', action='store_true', help='Write the launcher only; this does not migrate or start services.')
    args = parser.parse_args()
    # Validate before deriving any destination from untrusted host text.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,62}', args.host):
        parser.error('Invalid short hostname. Use hostname -s, without shell characters or paths.')
    destination = (args.output or BASE / 'vscode_h200/targets' / args.host / 'start_all.sh').expanduser().absolute()
    try:
        text, state = render_launcher(args.host, destination)
        mode = 'plan'
        if args.write:
            if destination.is_symlink():
                raise ValueError('Refusing to overwrite a symlink: ' + str(destination))
            if destination.exists():
                if destination.read_text() != text:
                    raise ValueError('Existing launcher differs; compare it with the current template before replacing: ' + str(destination))
                mode = 'unchanged'
            else:
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with destination.open('x') as stream:
                    stream.write(text)
                destination.chmod(0o700)
                mode = 'written'
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps({'mode': mode, 'target_host': args.host, 'template': str(TEMPLATE),
                      'launcher': str(destination), 'state_directory': str(state),
                      'start_command': 'bash ' + shlex.quote(str(destination)),
                      'status_command': 'bash ' + shlex.quote(str(destination)) + ' status',
                      'services_started': False, 'state_copied': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
