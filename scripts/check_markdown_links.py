#!/usr/bin/env python3
"""Validate local Markdown links without requiring network access."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "build", "dist", "env", "external", "venv"}
INLINE_LINK_RE = re.compile(r"!?\[[^\]\n]*(?:\][^\[\]\n]*)?\]\(([^)\n]+)\)")
REFERENCE_DEF_RE = re.compile(r"^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(\S+)", re.MULTILINE)
REFERENCE_USE_RE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
FENCED_BLOCK_RE = re.compile(r"(^|\n)(`{3,}|~{3,}).*?(\n\2[ \t]*$)", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HEADING_RE = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)


def replacement_preserving_lines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def markdown_files(paths: list[Path]) -> list[Path]:
    if paths:
        return sorted(path.resolve() for path in paths)
    files = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return sorted(files)


def sanitize_markdown(text: str) -> str:
    text = FENCED_BLOCK_RE.sub(replacement_preserving_lines, text)
    return INLINE_CODE_RE.sub("", text)


def split_destination(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        if end != -1:
            return raw[1:end].strip()
    return raw.split()[0].strip("<>")


def is_external(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme or parsed.netloc or target.startswith("//"))


def github_anchor_slug(heading: str) -> str:
    heading = re.sub(r"<[^>]+>", "", heading)
    heading = re.sub(r"[`*_~\[\]()]",
                     "",
                     heading).strip().lower()
    heading = re.sub(r"[^\w\- ]", "", heading)
    return re.sub(r"[ \t]+", "-", heading)


def anchors_for(path: Path) -> set[str]:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return set()

    text = path.read_text(encoding="utf-8", errors="ignore")
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for match in HEADING_RE.finditer(sanitize_markdown(text)):
        base = github_anchor_slug(match.group(2))
        if not base:
            continue
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    anchors.update(re.findall(r"\{#([A-Za-z0-9_.:-]+)\}", text))
    anchors.update(re.findall(r"<a\s+(?:[^>]*\s+)?(?:id|name)=[\"']([^\"']+)[\"']", text, re.IGNORECASE))
    return anchors


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def resolve_path(source: Path, target_path: str) -> Path:
    target_path = unquote(target_path)
    if target_path.startswith("/"):
        return ROOT / target_path.lstrip("/")
    return (source.parent / target_path).resolve()


def check_target(source: Path, text: str, raw_target: str, offset: int, anchor_cache: dict[Path, set[str]]) -> list[str]:
    target = split_destination(raw_target)
    if not target or target.startswith("#") or is_external(target):
        return []

    parsed = urlparse(target)
    path = resolve_path(source, parsed.path)
    rel_source = source.relative_to(ROOT)
    location = f"{rel_source}:{line_number(text, offset)}"

    if not path.exists():
        return [f"{location}: missing target {target}"]

    fragment = unquote(parsed.fragment)
    if fragment and path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
        anchors = anchor_cache.setdefault(path, anchors_for(path))
        if fragment not in anchors:
            return [f"{location}: missing anchor #{fragment} in {path.relative_to(ROOT)}"]
    return []


def check_file(path: Path, anchor_cache: dict[Path, set[str]]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    sanitized = sanitize_markdown(text)
    errors: list[str] = []

    definitions = {match.group(1).strip().lower(): split_destination(match.group(2)) for match in REFERENCE_DEF_RE.finditer(sanitized)}

    for match in INLINE_LINK_RE.finditer(sanitized):
        errors.extend(check_target(path, text, match.group(1), match.start(1), anchor_cache))

    for match in REFERENCE_USE_RE.finditer(sanitized):
        label = (match.group(2) or match.group(1)).strip().lower()
        target = definitions.get(label)
        if target is None:
            errors.append(f"{path.relative_to(ROOT)}:{line_number(text, match.start())}: undefined reference link [{label}]")
            continue
        errors.extend(check_target(path, text, target, match.start(), anchor_cache))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown files to check; defaults to the repository")
    args = parser.parse_args()

    anchor_cache: dict[Path, set[str]] = {}
    errors: list[str] = []
    for path in markdown_files(args.paths):
        errors.extend(check_file(path, anchor_cache))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Markdown links OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
