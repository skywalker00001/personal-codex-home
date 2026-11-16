#!/usr/bin/env bash
set -euo pipefail
profile_repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$profile_repo_dir/scripts/install.py" "$@"
