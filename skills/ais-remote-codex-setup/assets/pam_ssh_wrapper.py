#!/usr/bin/env python3
"""Keep SMC credentials in memory while launching the standard macOS SSH client."""

import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

SSH = "/usr/bin/ssh"
SMC = shutil.which("smc") or next((str(p) for p in (
    Path.home() / "miniforge/bin/smc", Path.home() / "miniforge3/bin/smc",
    Path.home() / ".smc/python/bin/smc", Path("/opt/homebrew/bin/smc"),
) if p.is_file() and os.access(p, os.X_OK)), "smc")


def fail(message):
    print("[AIS SSH] " + message, file=sys.stderr)
    raise SystemExit(1)


def capture_smc(arguments):
    try:
        result = subprocess.run(
            [SMC, *arguments], capture_output=True, text=True, timeout=180
        )
    except (OSError, subprocess.TimeoutExpired):
        fail("SMC authentication did not finish. Run `smc login` in Terminal and retry.")
    if result.returncode:
        # Authentication output can contain credentials; never repeat it in SSH logs.
        fail("SMC authentication failed. Run `smc login` in Terminal and retry.")
    return result.stdout.strip()


def main():
    arguments = sys.argv[1:]
    if not arguments or any(arg in ("-V", "-G", "-Q") for arg in arguments):
        os.execv(SSH, [SSH, *arguments])

    # Resolve the exact same config and flags as the real SSH invocation.
    resolved = subprocess.run(
        [SSH, "-G", *arguments], capture_output=True, text=True
    )
    if resolved.returncode:
        os.execv(SSH, [SSH, *arguments])
    pam_identity = str(Path.home() / ".smc/pam/ssh_private_key_shopee")
    target_host = next(
        (line.split(" ", 1)[1] for line in resolved.stdout.splitlines()
         if line.startswith("hostname ")), ""
    )
    uses_pam = any(
        line.startswith("identityfile ")
        and str(Path(line.split(" ", 1)[1]).expanduser()) == pam_identity
        for line in resolved.stdout.splitlines()
    )
    if not uses_pam:
        os.execv(SSH, [SSH, *arguments])

    print("[AIS SSH] Refreshing SMC/PAM authentication...", file=sys.stderr)
    environment = dict(os.environ)
    token = capture_smc(["token", "export"])
    if not token or any(character.isspace() for character in token):
        fail("SMC did not return a token. Run `smc login` in Terminal and retry.")
    try:
        user = json.loads((Path.home() / ".smc/smc_user.json").read_text())
        device = json.loads(capture_smc([
            "deviceauth", "get-svid-dpop", "--allow-registration=false",
            "--param", "target_ip=" + target_host,
        ]))
        values = {
            "SMC_USER_EMAIL": user["email"],
            "SMC_TOKEN": token,
            "SMC_DEVICE_AUTH_USER_JWT_SVID": device["svid"],
            "SMC_DEVICE_AUTH_USER_DPOP_TOKEN": device["dpop_token"],
        }
        if not all(isinstance(value, str) and value for value in values.values()):
            fail("SMC returned incomplete authentication. Run `smc login` and retry.")
    except (OSError, ValueError, KeyError, TypeError):
        fail("Cannot read SMC authentication. Run `smc login` in Terminal and retry.")
    environment.update(values)
    os.execve(SSH, [SSH, *arguments], environment)


if __name__ == "__main__":
    main()
