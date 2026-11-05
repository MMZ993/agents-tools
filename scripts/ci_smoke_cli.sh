#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
PYTHONPATH="$repo_root/src" uv run python scripts/ci_smoke_cli.py
