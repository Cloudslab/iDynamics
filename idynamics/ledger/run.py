"""Central run-ledger utility for evaluation experiments."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from idynamics.types import ExperimentLedger


REQUIRED_LEDGER_FILES = (
    "config.yaml",
    "commands.log",
    "git_sha.txt",
    "git_status.txt",
    "codex_model.txt",
    "summary.md",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root(start: Path | None = None) -> Path:
    cwd = start or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return cwd.resolve()


def _git_text(root: Path, args: list[str], fallback: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout
    except (OSError, subprocess.CalledProcessError):
        return fallback


def _write_default_config(path: Path, run_id: str, purpose: str, extra_config: Mapping[str, object] | None) -> None:
    lines = [
        f"run_id: {run_id}",
        f"created_utc: {utc_timestamp()}",
        f"purpose: {purpose}",
        "physical_scale_claim: none",
    ]
    for key, value in (extra_config or {}).items():
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n")


def init_run_ledger(
    run_id: str,
    purpose: str = "TBD",
    root: Path | None = None,
    config_path: Path | None = None,
    extra_config: Mapping[str, object] | None = None,
) -> ExperimentLedger:
    """Create a complete run ledger and return its typed descriptor."""
    project_root = root or repo_root()
    run_root = project_root / "experiments" / "runs" / run_id
    for dirname in ("env", "raw", "processed", "figures", "logs"):
        (run_root / dirname).mkdir(parents=True, exist_ok=True)

    target_config = run_root / "config.yaml"
    if config_path is not None:
        target_config.write_text(Path(config_path).read_text())
    elif not target_config.exists():
        _write_default_config(target_config, run_id, purpose, extra_config)

    (run_root / "git_sha.txt").write_text(_git_text(project_root, ["rev-parse", "HEAD"], "no-git-sha\n"))
    (run_root / "git_status.txt").write_text(_git_text(project_root, ["status", "--short", "--branch"], ""))
    (run_root / "codex_model.txt").write_text(f"{os.environ.get('CODEX_MODEL', 'codex-cli-local')}\n")
    (run_root / "commands.log").touch()
    if not (run_root / "summary.md").exists():
        (run_root / "summary.md").write_text(f"# {run_id}\n\nStatus: initialized\n\n## Purpose\n{purpose}\n")

    ledger = ExperimentLedger(
        run_id=run_id,
        root=run_root,
        config_path=target_config,
        commands_log=run_root / "commands.log",
        git_sha_path=run_root / "git_sha.txt",
        git_status_path=run_root / "git_status.txt",
        codex_model_path=run_root / "codex_model.txt",
        summary_path=run_root / "summary.md",
    )
    validate_run_ledger(ledger.root)
    return ledger


def log_command(ledger: ExperimentLedger | Path, command: str) -> None:
    run_root = ledger.root if isinstance(ledger, ExperimentLedger) else Path(ledger)
    with (run_root / "commands.log").open("a") as handle:
        handle.write(f"[{utc_timestamp()}] {command}\n")


def validate_run_ledger(run_dir: Path) -> None:
    missing = [name for name in REQUIRED_LEDGER_FILES if not (run_dir / name).exists()]
    missing_dirs = [name for name in ("env", "raw", "processed", "figures", "logs") if not (run_dir / name).is_dir()]
    if missing or missing_dirs:
        parts = []
        if missing:
            parts.append("files: " + ", ".join(missing))
        if missing_dirs:
            parts.append("directories: " + ", ".join(missing_dirs))
        raise ValueError(f"incomplete run ledger {run_dir}: {'; '.join(parts)}")
