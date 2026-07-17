#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from reproducibility.scripts.generate_artifact import cli

if __name__ == "__main__":
    cli(default_artifact_dir=Path(__file__).resolve().parents[1])
