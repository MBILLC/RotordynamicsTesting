#!/usr/bin/env bash
# Canonical single entry point for this project's regression suite.
#
# Mirrors ModCheck's own run_regression.sh (see that repo's HOWTO.md section 7)
# one level up: this wraps run_regression.py, this project's own thin wrapper
# around ModCheck's generic regression_testing.py, pre-filled for
# regression_cases.yaml/ReferenceResults/ in this repo. Every other way of
# invoking run_regression.py (bare `python3 run_regression.py`, a call from a
# notebook, the nightly cron daemon -- see nightly_regression_cron.py) still
# works exactly as documented; this wrapper exists so there is exactly ONE
# stable command a human, CI job, or scheduler can point at regardless of
# caller cwd -- it resolves paths relative to this script's own location, not
# the caller's.
#
# ONLY runs the regression suite -- never touches RotorDynamics_Credibility.ipynb
# (a different repo entirely, Rotordynamics/Resources/Notebooks/) or generates a
# notebook-format regression report unless explicitly asked with
# --report-format notebook.
#
# Usage (any run_regression.py / regression_testing.py flag forwards through):
#   ./run_regression.sh                 # regression run, default config, exit 0/1
#   ./run_regression.sh --store         # (re-)establish reference results
#   ./run_regression.sh --case GearMeshRatioCheck
#
# Exit code mirrors run_regression.py itself: 0 = all PASS, 1 = at least one FAIL.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
exec python3 "$SCRIPT_DIR/run_regression.py" "$@"
