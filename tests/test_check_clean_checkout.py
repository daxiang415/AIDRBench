"""Exercise checkout validation against real, edited Git repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("change", "expected_exit"),
    [
        ("staged_delete", 1),
        ("unstaged_delete", 1),
        ("staged_rename_stale_test", 1),
        ("staged_rename_updated_test", 0),
        ("file_to_directory", 0),
        ("directory_to_file", 0),
        ("dangling_symlink", 0),
    ],
)
def test_candidate_checkout_matches_direct_pytest(
    tmp_path: Path, change: str, expected_exit: int
) -> None:
    root = tmp_path / "source"
    root.mkdir()

    def git(*arguments: str) -> None:
        subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True)

    git("init", "--quiet")
    git("config", "user.name", "Checkout regression")
    git("config", "user.email", "checkout-test@example.invalid")
    (root / "scripts").mkdir()
    shutil.copy2(
        Path(__file__).resolve().parents[1] / "scripts/check_clean_checkout.py",
        root / "scripts/check_clean_checkout.py",
    )
    (root / ".gitignore").write_text("ignored.txt\n__pycache__/\n.pytest_cache/\n")
    (root / "ignored.txt").write_text("local production-like artifact")
    fixture = root / "required_fixture.txt"
    fixture.write_text("required")
    (root / "old_dir").mkdir()
    (root / "old_dir/child.txt").write_text("old")
    test_path = root / "test_candidate.py"
    test_path.write_text(
        "from pathlib import Path\n"
        "def test_candidate():\n"
        "    assert Path('required_fixture.txt').read_text() == 'required'\n"
    )
    git("add", ".")
    git("-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-qm", "base")

    if change == "staged_delete":
        git("rm", "required_fixture.txt")
    elif change == "unstaged_delete":
        fixture.unlink()
    elif change.startswith("staged_rename"):
        git("mv", "required_fixture.txt", "renamed.txt")
        if change == "staged_rename_updated_test":
            test_path.write_text(
                "from pathlib import Path\n"
                "def test_candidate():\n"
                "    assert not Path('required_fixture.txt').exists()\n"
                "    assert Path('renamed.txt').read_text() == 'required'\n"
            )
    elif change == "file_to_directory":
        fixture.unlink()
        fixture.mkdir()
        (fixture / "new.txt").write_text("new")
        test_path.write_text(
            "from pathlib import Path\n"
            "def test_candidate():\n"
            "    assert Path('required_fixture.txt/new.txt').read_text() == 'new'\n"
        )
    elif change == "directory_to_file":
        (root / "old_dir/child.txt").unlink()
        (root / "old_dir").rmdir()
        (root / "old_dir").write_text("replacement")
        test_path.write_text(
            "from pathlib import Path\n"
            "def test_candidate():\n"
            "    assert Path('old_dir').read_text() == 'replacement'\n"
        )
    else:
        fixture.unlink()
        fixture.symlink_to("missing-target")
        test_path.write_text(
            "from pathlib import Path\n"
            "def test_candidate():\n"
            "    path = Path('required_fixture.txt')\n"
            "    assert path.is_symlink() and not path.exists()\n"
            "    assert str(path.readlink()) == 'missing-target'\n"
        )

    environment = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    direct = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert direct.returncode == expected_exit, direct.stdout + direct.stderr
    # The ignored file exists only in the workstation copy. It must not be
    # smuggled into the checkout alongside valid tracked or untracked sources.
    with test_path.open("a") as stream:
        stream.write("    assert not Path('ignored.txt').exists()\n")
    report_path = tmp_path / "receipt.json"
    checked = subprocess.run(
        [
            sys.executable,
            "scripts/check_clean_checkout.py",
            "--include-worktree",
            "--report",
            str(report_path),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert checked.returncode == expected_exit, checked.stdout + checked.stderr
    report = json.loads(report_path.read_text())
    assert report["exit_code"] == expected_exit
    assert report["include_worktree"] is True
    assert report["source_worktree_dirty"] is True
    assert ("1 failed" if expected_exit else "1 passed") in report["stdout"]
