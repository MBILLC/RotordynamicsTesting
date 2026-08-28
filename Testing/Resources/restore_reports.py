#!/usr/bin/env python3
"""
Thin wrapper around ModCheck's restore_reports.py, pre-filled for this
project's own regression_cases.yaml and report directory names.

The actual restore logic lives in ModCheck -- a separate, generic, sibling
project (https://github.com/hubertus65/ModCheck) -- see its restore_reports.py
and HOWTO.md ("Restoring one after a fresh clone..."). This wrapper exists
only so `python3 restore_reports.py notebook` works from here without typing
--config/--html-report-dir every time, and applies this project's own
"Notebooks" naming (not ModCheck's own default "NotebookReports") to match
the main RotorDynamics project's Resources/Notebooks/ convention.

Usage: same as ModCheck's restore_reports.py --
    python3 restore_reports.py notebook
    python3 restore_reports.py html --force
    python3 restore_reports.py html-interactive
    python3 restore_reports.py --all
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../Rotordynamicsdevelopment/Testing/Resources
CONFIG = HERE / "regression_cases.yaml"

# ModCheck is a sibling project (separate repo) holding the actual harness
# and the generic restore_reports.py this wraps. Default assumes the usual
# sibling layout (local_projects/ModCheck next to this repo's own
# local_projects/<...> checkout); pass --modcheck-restore if yours differs.
DEFAULT_MODCHECK_RESTORE = (HERE.parent.parent.parent / "ModCheck" / "ModCheck"
                            / "Resources" / "restore_reports.py")

# This project names its notebook report dir "Notebooks", not ModCheck's own
# default "NotebookReports".
OUTPUT_DIR_NAME = {"notebook": "Notebooks", "html": "HtmlReports",
                    "html-interactive": "InteractiveReports"}


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("format", nargs="?", choices=sorted(OUTPUT_DIR_NAME),
                    help="which report to restore (omit and pass --all for all three)")
    p.add_argument("--all", action="store_true", help="restore all three report formats")
    p.add_argument("--force", action="store_true",
                    help="regenerate even if the report already exists")
    p.add_argument("--modcheck-restore", type=Path, default=DEFAULT_MODCHECK_RESTORE,
                    help=f"path to ModCheck's restore_reports.py "
                         f"(default: {DEFAULT_MODCHECK_RESTORE})")
    args = p.parse_args()

    if not args.all and args.format is None:
        p.error("specify a format (notebook|html|html-interactive) or --all")

    if not args.modcheck_restore.exists():
        sys.exit(f"ModCheck not found at {args.modcheck_restore} -- clone it as a "
                  f"sibling project (https://github.com/hubertus65/ModCheck), or "
                  f"pass --modcheck-restore /path/to/restore_reports.py.")

    rc = 0
    for fmt in (list(OUTPUT_DIR_NAME) if args.all else [args.format]):
        cmd = [sys.executable, str(args.modcheck_restore), fmt,
               "--config", str(CONFIG),
               "--html-report-dir", str(HERE / OUTPUT_DIR_NAME[fmt])]
        if args.force:
            cmd.append("--force")
        rc = subprocess.run(cmd).returncode or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
