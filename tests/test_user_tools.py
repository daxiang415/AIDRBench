"""Regression checks for the public editing entry points and documentation."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = load_module("editing_launcher", "tools/aidr.py")
checker = load_module("checkout_checker", "scripts/check_v027_checkout.py")


@pytest.mark.parametrize(
    ("arguments", "tail"),
    [
        (["check", "--hashes"], ["--hashes"]),
        (["redraw", "--figures", "S3", "S9", "--tiff"],
         ["--figures", "S3", "S9", "--tiff"]),
        (["main-figures"], ["--panels-only"]),
        (["paper", "--engine", "C:/TeX Tools/xelatex.exe"],
         ["--engine", "C:/TeX Tools/xelatex.exe"]),
        (["test"], ["-m", "pytest", "-q"]),
    ],
)
def test_command_arguments(arguments, tail, tmp_path):
    args = launcher.build_parser().parse_args(arguments)
    command = launcher.command_for(args, tmp_path)
    assert command[0] == sys.executable
    assert command[-len(tail):] == tail


def test_pdf_export_is_explicit(tmp_path):
    args = launcher.build_parser().parse_args(["main-figures", "--export-pdf"])
    assert "--panels-only" not in launcher.command_for(args, tmp_path)


def test_invalid_figure_is_rejected():
    with pytest.raises(SystemExit):
        launcher.build_parser().parse_args(["redraw", "--figures", "S11"])


def test_dry_run_does_not_execute(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("A dry run must not start a subprocess")
    monkeypatch.setattr(launcher.subprocess, "run", unexpected)
    assert launcher.main(["redraw", "--figures", "S5", "--dry-run"]) == 0


def test_failure_code_and_environment_are_preserved(monkeypatch):
    def run(command, **kwargs):
        assert kwargs["cwd"] == ROOT
        assert kwargs["env"]["PYTHONUTF8"] == "1"
        assert kwargs["env"]["MPLBACKEND"] == "Agg"
        return subprocess.CompletedProcess(command, 7)
    monkeypatch.setattr(launcher.subprocess, "run", run)
    assert launcher.main(["check"]) == 7


def test_paths_cannot_escape_checkout(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        checker.within(tmp_path, "../elsewhere")


@pytest.fixture
def receipt(tmp_path):
    records = []
    for name, data in (("science.csv", b"value\n1.25\n"),
                       ("README.md", b"Original guide\n"),
                       ("reader.md", b"Historical reader\n")):
        (tmp_path / name).write_bytes(data)
        records.append({"path": name, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    manifest = tmp_path / "paper/v0.27/MANIFEST.csv"
    manifest.parent.mkdir(parents=True)
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(records)
    (tmp_path / "README.md").write_bytes(b"Current guide\n")
    (tmp_path / "reader.md").unlink()
    layout = {"baseline_manifest_git_blob": checker.git_blob(manifest.read_bytes()),
              "retired_files": ["reader.md"], "retired_prefixes": [],
              "renamed_files": {},
              "updated_git_blobs": {"README.md": checker.git_blob(b"Current guide\n")}}
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/checkout-layout.json").write_text(json.dumps(layout), encoding="utf-8")
    return tmp_path


def test_updated_docs_preserve_scientific_hash_check(receipt):
    assert checker.verify_manifest(receipt, True) == ([], 2)
    (receipt / "science.csv").write_text("value\n999\n", encoding="utf-8")
    errors, _ = checker.verify_manifest(receipt, True)
    assert "Changed release file: science.csv" in errors


def test_modified_document_is_detected(receipt):
    (receipt / "README.md").write_text("Unexpected edit", encoding="utf-8")
    errors, _ = checker.verify_manifest(receipt, True)
    assert "Changed maintained file: README.md" in errors


def test_missing_scientific_file_is_detected_without_hashes(receipt):
    (receipt / "science.csv").unlink()
    errors, _ = checker.verify_manifest(receipt, False)
    assert "Missing release file: science.csv" in errors


def test_manifest_tampering_is_detected(receipt):
    manifest = receipt / "paper/v0.27/MANIFEST.csv"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    errors, _ = checker.verify_manifest(receipt, False)
    assert "The original delivery manifest has changed." in errors


def test_byte_preserving_rename(receipt):
    layout_file = receipt / "docs/checkout-layout.json"
    layout = json.loads(layout_file.read_text(encoding="utf-8"))
    layout["renamed_files"] = {"science.csv": "renamed.csv"}
    layout_file.write_text(json.dumps(layout), encoding="utf-8")
    (receipt / "science.csv").rename(receipt / "renamed.csv")
    assert checker.verify_manifest(receipt, True) == ([], 2)
    (receipt / "renamed.csv").write_bytes(b"changed")
    assert "Changed release file: renamed.csv" in checker.verify_manifest(receipt, True)[0]


def test_public_docs_have_local_targets_and_english_text():
    paths = ["README.md", "WINDOWS_START_HERE.md", "MAINLINE_FILES.md",
             "docs/README.md", "docs/getting-started.md", "docs/figures.md",
             "docs/GITHUB_V027.md", "paper/v0.27/figures/main/README.md",
             "paper/v0.27/figures/supplement/README.md"]
    for relative in paths:
        source = ROOT / relative
        text = source.read_text(encoding="utf-8")
        assert not re.search(r"[\u3400-\u9fff]", text), relative
        targets = re.findall(r"\]\(([^\s)]+)\)", text)
        targets += re.findall(r'(?:src|href)="([^"]+)"', text)
        for target in targets:
            url = urlsplit(target)
            if not url.scheme and not url.netloc and url.path:
                assert (source.parent / unquote(url.path)).exists(), (relative, target)


def test_homepage_svgs_are_self_contained():
    for name in ("overview.svg", "workflow.svg"):
        root = ElementTree.parse(ROOT / "docs/assets" / name).getroot()
        assert root.get("viewBox")
        for element in root.iter():
            assert not element.tag.endswith("script")
            assert not element.tag.endswith("foreignObject")
            for attribute, value in element.attrib.items():
                if attribute.endswith("href"):
                    assert value.startswith("#")
