#!/usr/bin/env python3
"""Validate artifact structure, checksums, and generated expected outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS_DIR = ROOT / "reproducibility" / "items"
sys.path.insert(0, str(ROOT))

from reproducibility.scripts.generate_artifact import generate
FORBIDDEN_PUBLIC_TEXT = [
    "Co" + "dex",
    "Chat" + "GPT",
    "Open" + "AI",
    "orches" + "trator",
    "AI-" + "generated",
    "/" + "home/",
]


def item_dirs() -> list[Path]:
    return sorted(path for path in ITEMS_DIR.iterdir() if (path / "manifest.yaml").exists())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, object]:
    return json.loads((path / "manifest.yaml").read_text(encoding="utf-8"))


def check_required_files(path: Path, manifest: dict[str, object]) -> list[str]:
    errors = []
    for rel in ["manifest.yaml", "README.md", "run.sh", "checksums.sha256", "scripts/generate.py"]:
        if not (path / rel).exists():
            errors.append(f"{path.name}: missing {rel}")
    for rel in manifest.get("inputs", []):
        if not (path / rel).exists():
            errors.append(f"{path.name}: missing input {rel}")
    for rel in manifest.get("expected_outputs", []):
        if not (path / rel).exists():
            errors.append(f"{path.name}: missing expected output {rel}")
    return errors


def check_checksums(path: Path) -> list[str]:
    errors = []
    checksums = path / "checksums.sha256"
    if not checksums.exists():
        return [f"{path.name}: missing checksums.sha256"]
    for line in checksums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        rel = rel.strip()
        target = path / rel
        if not target.exists():
            errors.append(f"{path.name}: checksum target missing {rel}")
            continue
        actual = sha256(target)
        if actual != expected:
            errors.append(f"{path.name}: checksum mismatch {rel}")
    return errors


def check_public_text(path: Path) -> list[str]:
    errors = []
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".csv", ".json", ".md", ".py", ".sh", ".sha256", ".svg", ".tex", ".yaml"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN_PUBLIC_TEXT:
            if token in text:
                rel = file_path.relative_to(ROOT)
                errors.append(f"{rel}: contains forbidden public text token {token!r}")
    return errors


def check_regeneration(path: Path) -> list[str]:
    manifest = load_manifest(path)
    expected_outputs = [Path(rel) for rel in manifest.get("expected_outputs", [])]
    errors = []
    with tempfile.TemporaryDirectory(prefix="idynamics-artifact-") as tempdir:
        generated_dir = generate(path, Path(tempdir))
        for rel in expected_outputs:
            expected = path / rel
            generated = generated_dir / rel.relative_to("expected")
            if not generated.exists():
                errors.append(f"{path.name}: regenerated output missing {generated.name}")
                continue
            if expected.read_bytes() != generated.read_bytes():
                errors.append(f"{path.name}: regenerated output differs for {rel}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-regenerate", action="store_true", help="Only check files, checksums, and public text hygiene")
    args = parser.parse_args()

    errors: list[str] = []
    for path in item_dirs():
        manifest = load_manifest(path)
        errors.extend(check_required_files(path, manifest))
        errors.extend(check_checksums(path))
        errors.extend(check_public_text(path))
        if not args.skip_regenerate:
            errors.extend(check_regeneration(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"validated {len(item_dirs())} reproducibility artifacts")


if __name__ == "__main__":
    main()
