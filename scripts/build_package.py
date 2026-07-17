#!/usr/bin/env python3
"""Build source and wheel distributions without the optional build frontend."""

from __future__ import annotations

import argparse
from pathlib import Path

from setuptools import build_meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("dist"), help="Directory for built distributions")
    args = parser.parse_args()

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    sdist = build_meta.build_sdist(str(outdir))
    wheel = build_meta.build_wheel(str(outdir))
    print(outdir / sdist)
    print(outdir / wheel)


if __name__ == "__main__":
    main()
