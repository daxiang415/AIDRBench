#!/usr/bin/env bash
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"

python3 -m aidrbench project-check --root "$repo_root"
python3 -m unittest discover -s "$repo_root/tests" -p 'test_*.py' -v
