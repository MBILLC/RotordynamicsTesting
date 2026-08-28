#!/usr/bin/env python3
"""
Regenerate Notebooks/ (the notebook-format regression report) from the
committed ReferenceResults/ baselines, if it doesn't already exist on disk.

Notebooks/ is gitignored -- it's reproducible report output (executed
.ipynb files + raw funnel-comparison trace data), not stored data, so a
fresh clone of this repo won't have it. This re-simulates every case in
regression_cases.yaml through ModCheck's harness and rebuilds the report by
comparing against ReferenceResults/, which IS committed here -- so this only
needs Modelon Impact access, nothing else to restore first.

Usage:
    python3 restore_notebooks.py                # skip if Notebooks/index.ipynb already exists
    python3 restore_notebooks.py --force         # regenerate even if it exists
    python3 restore_notebooks.py --harness PATH  # explicit path to regression_testing.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../Rotordynamicsdevelopment/Testing/Resources
CONFIG = HERE / "regression_cases.yaml"
NOTEBOOKS_DIR = HERE / "Notebooks"
INDEX_NB = NOTEBOOKS_DIR / "index.ipynb"

# ModCheck is a sibling project (separate repo), not part of this one -- see
# its own HOWTO.md for what regression_testing.py needs. Default assumes the
# usual sibling layout (local_projects/ModCheck next to this repo's own
# local_projects/<...> checkout); pass --harness if yours differs.
DEFAULT_HARNESS = (HERE.parent.parent.parent / "ModCheck" / "ModCheck" / "Resources"
                   / "regression_testing.py")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--force", action="store_true",
                   help="regenerate even if Notebooks/index.ipynb already exists")
    p.add_argument("--harness", type=Path, default=DEFAULT_HARNESS,
                   help=f"path to ModCheck's regression_testing.py (default: {DEFAULT_HARNESS})")
    args = p.parse_args()

    if INDEX_NB.exists() and not args.force:
        print(f"{INDEX_NB} already exists -- nothing to do (pass --force to regenerate).")
        return 0

    if not args.harness.exists():
        sys.exit(f"Harness not found at {args.harness} -- clone ModCheck as a sibling "
                  f"project (https://github.com/hubertus65/ModCheck), or pass "
                  f"--harness /path/to/regression_testing.py.")

    cmd = [sys.executable, str(args.harness),
           "--config", str(CONFIG),
           "--report-format", "notebook",
           "--html-report-dir", str(NOTEBOOKS_DIR)]
    print(f"Restoring {NOTEBOOKS_DIR} from {CONFIG.name}'s ReferenceResults/ ...")
    print(" ", " ".join(cmd))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
