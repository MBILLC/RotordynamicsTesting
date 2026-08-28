#!/usr/bin/env python3
"""
Regenerate a visual regression report (Notebooks/, HtmlReports/, or
InteractiveReports/) from the committed ReferenceResults/ baselines, if it
doesn't already exist on disk.

All three report formats are gitignored -- they're reproducible report
output (executed notebooks / static HTML / interactive HTML, each with its
own raw funnel-comparison trace data), not stored data, so a fresh clone of
this repo won't have them. This re-simulates every case in
regression_cases.yaml through ModCheck's harness and rebuilds the requested
report by comparing against ReferenceResults/, which IS committed here -- so
this only needs Modelon Impact access, nothing else to restore first. See
ModCheck's own HOWTO.md ("Restoring one after a fresh clone...") for the
underlying pattern this script wraps.

Usage:
    python3 restore_reports.py notebook                 # skip if already exists
    python3 restore_reports.py html --force              # regenerate even if it exists
    python3 restore_reports.py html-interactive
    python3 restore_reports.py --all                     # all three formats
    python3 restore_reports.py notebook --harness PATH   # explicit path to regression_testing.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../Rotordynamicsdevelopment/Testing/Resources
CONFIG = HERE / "regression_cases.yaml"

# format -> (output dir, marker file that means "already generated")
REPORT_DIRS = {
    "notebook": (HERE / "Notebooks", "index.ipynb"),
    "html": (HERE / "HtmlReports", "index.html"),
    "html-interactive": (HERE / "InteractiveReports", "index.html"),
}

# ModCheck is a sibling project (separate repo), not part of this one -- see
# its own HOWTO.md for what regression_testing.py needs. Default assumes the
# usual sibling layout (local_projects/ModCheck next to this repo's own
# local_projects/<...> checkout); pass --harness if yours differs.
DEFAULT_HARNESS = (HERE.parent.parent.parent / "ModCheck" / "ModCheck" / "Resources"
                   / "regression_testing.py")


def restore(fmt: str, harness: Path, force: bool) -> int:
    out_dir, marker = REPORT_DIRS[fmt]
    index = out_dir / marker
    if index.exists() and not force:
        print(f"{index} already exists -- nothing to do (pass --force to regenerate).")
        return 0

    if not harness.exists():
        sys.exit(f"Harness not found at {harness} -- clone ModCheck as a sibling "
                  f"project (https://github.com/hubertus65/ModCheck), or pass "
                  f"--harness /path/to/regression_testing.py.")

    cmd = [sys.executable, str(harness),
           "--config", str(CONFIG),
           "--report-format", fmt,
           "--html-report-dir", str(out_dir)]
    print(f"Restoring {out_dir} from {CONFIG.name}'s ReferenceResults/ ...")
    print(" ", " ".join(cmd))
    return subprocess.run(cmd).returncode


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("format", nargs="?", choices=sorted(REPORT_DIRS),
                    help="which report to restore (omit and pass --all for all three)")
    p.add_argument("--all", action="store_true", help="restore all three report formats")
    p.add_argument("--force", action="store_true",
                    help="regenerate even if the report already exists")
    p.add_argument("--harness", type=Path, default=DEFAULT_HARNESS,
                    help=f"path to ModCheck's regression_testing.py (default: {DEFAULT_HARNESS})")
    args = p.parse_args()

    if not args.all and args.format is None:
        p.error("specify a format (notebook|html|html-interactive) or --all")

    rc = 0
    for fmt in (list(REPORT_DIRS) if args.all else [args.format]):
        rc = restore(fmt, args.harness, args.force) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
