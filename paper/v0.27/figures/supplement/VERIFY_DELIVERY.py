"""Verify the maintained checkout, including byte-preserving figure-pack renames."""

from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[4]
checker = root / "scripts/check_v027_checkout.py"
if not checker.is_file():
    raise SystemExit("Run this verifier inside a complete AIDRBench checkout.")
raise SystemExit(subprocess.run([sys.executable, str(checker), "--hashes"], cwd=root).returncode)
