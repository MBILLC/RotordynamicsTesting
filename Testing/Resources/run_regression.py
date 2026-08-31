#!/usr/bin/env python3
"""
Thin wrapper around ModCheck's regression_testing.py, pre-filled for this
project's own regression_cases.yaml and ReferenceResults/.

The actual harness lives in ModCheck -- a separate, generic, sibling project
(https://github.com/hubertus65/ModCheck). This wrapper exists only so that
running the whole RotorDynamics suite is one command with no arguments:

    python3 run_regression.py                     # run every enabled case
    python3 run_regression.py --case GearMeshRatioCheck
    python3 run_regression.py --store --case GearMeshRatioCheck
    python3 run_regression.py --report-format notebook

Every flag ModCheck's regression_testing.py accepts is forwarded unchanged
(--store, --case, --model, --rtol-factor, --report-format, ...); only
--config and --ref-dir are pre-filled, and --html-report-dir defaults to this
project's own report directory for the chosen format.

Sibling wrapper: restore_reports.py, which re-renders a report from the stored
ReferenceResults/ without re-simulating anything.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../Rotordynamicsdevelopment/Testing/Resources
CONFIG = HERE / "regression_cases.yaml"
REF_DIR = HERE / "ReferenceResults"

# Usual sibling layout: local_projects/ModCheck next to this project's own checkout.
DEFAULT_MODCHECK = (HERE.parent.parent.parent / "ModCheck" / "ModCheck"
                    / "Resources" / "regression_testing.py")

# This project names its notebook report dir "Notebooks", not ModCheck's own
# default "NotebookReports" -- same convention restore_reports.py applies.
OUTPUT_DIR_NAME = {"notebook": "Notebooks", "html": "HtmlReports",
                   "html-interactive": "InteractiveReports"}


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modcheck", type=Path, default=DEFAULT_MODCHECK,
                   help=f"path to ModCheck's regression_testing.py "
                        f"(default: {DEFAULT_MODCHECK})")
    args, forwarded = p.parse_known_args()

    if not args.modcheck.exists():
        sys.exit(f"ModCheck not found at {args.modcheck} -- clone it as a sibling project "
                 f"(https://github.com/hubertus65/ModCheck), or pass "
                 f"--modcheck /path/to/regression_testing.py.")

    cmd = [sys.executable, str(args.modcheck),
           "--config", str(CONFIG), "--ref-dir", str(REF_DIR)] + forwarded

    # Pre-fill the report directory for whichever format was asked for, unless the
    # caller named one themselves.
    if "--html-report-dir" not in forwarded:
        fmt = "html"
        if "--report-format" in forwarded:
            i = forwarded.index("--report-format")
            if i + 1 < len(forwarded):
                fmt = forwarded[i + 1]
        cmd += ["--html-report-dir", str(HERE / OUTPUT_DIR_NAME.get(fmt, "HtmlReports"))]

    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
