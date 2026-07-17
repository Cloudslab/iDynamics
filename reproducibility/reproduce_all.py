#!/usr/bin/env python3
"""Regenerate reproducibility artifacts from committed curated data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS_DIR = ROOT / "reproducibility" / "items"
sys.path.insert(0, str(ROOT))

from reproducibility.scripts.generate_artifact import generate


def item_dirs() -> list[Path]:
    return sorted(path for path in ITEMS_DIR.iterdir() if (path / "manifest.yaml").exists())


def load_manifest(path: Path) -> dict[str, object]:
    return json.loads((path / "manifest.yaml").read_text(encoding="utf-8"))


def selected_items(names: list[str] | None) -> list[Path]:
    items = item_dirs()
    if not names:
        return items
    wanted = set(names)
    selected = []
    for path in items:
        manifest = load_manifest(path)
        if path.name in wanted or manifest["item_id"] in wanted or manifest["manuscript_ref"] in wanted:
            selected.append(path)
    missing = wanted - {path.name for path in selected} - {str(load_manifest(path)["item_id"]) for path in selected}
    if missing:
        raise SystemExit(f"unknown artifact selection: {', '.join(sorted(missing))}")
    return selected


def print_full_cluster_plan(paths: list[Path]) -> None:
    for path in paths:
        manifest = load_manifest(path)
        print(f"{manifest['item_id']} ({manifest['manuscript_ref']}): {manifest['title']}")
        plans = manifest.get("full_cluster_rerun", [])
        if not plans:
            print("  No live-cluster rerun path is required for this artifact.")
            continue
        for plan in plans:
            print(f"  {plan['description']}")
            for command in plan.get("commands", []):
                print(f"    {command}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", action="append", help="Item id, manuscript ref, or artifact folder name to regenerate")
    parser.add_argument("--output-root", type=Path, help="Directory for regenerated outputs; defaults to each artifact's generated/ folder")
    parser.add_argument("--mode", choices=["data-only", "full-cluster-plan"], default="data-only")
    args = parser.parse_args()

    paths = selected_items(args.artifact)
    if args.mode == "full-cluster-plan":
        print_full_cluster_plan(paths)
        return

    for path in paths:
        output_dir = args.output_root / path.name if args.output_root else path / "generated"
        generated = generate(path, output_dir)
        manifest = load_manifest(path)
        print(f"{manifest['item_id']}: {generated.relative_to(ROOT) if generated.is_relative_to(ROOT) else generated}")


if __name__ == "__main__":
    main()
