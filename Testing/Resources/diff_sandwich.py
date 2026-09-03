# Copyright © 2026 Model Based Innovation LLC. All rights reserved.
"""Diff the 4.27.4 sandwich: before_refactor.log vs after_refactor.log.

Both logs are append-only across resumed runs, so a case can appear several times.
The LAST line for a case is its verdict -- earlier ones are aborted attempts
(container restarts, the pyfunnel memory work), and treating those as results is
how a clean run gets read as a regression.

Cases 0-23 of the BEFORE run were executed in two batches whose per-case verdicts
were never broken out (only "125/125 checks passed" / "73/73 checks passed" for the
batch). Those are reported as PASSED-IN-BATCH: pass/fail is comparable, the
per-check count is not.
"""
import pathlib
import re
import sys

R = pathlib.Path(__file__).resolve().parent
BATCH_PASSED = {"JeffcottValidation", "InhomogeneousRotorWhirl", "BearingFaultDemo",
                "IshibashiRotorKit", "CouplingReactionTorque", "TorsionalOscillation",
                "TorsionShaftBending", "BearingAndShafts", "CantileverGravityDirection",
                "VerticalShaftNoSag", "MixedAxisGravity", "MultiBodyMountEquivalence",
                "MultiBodyMountKinematics", "MultiBodyMountReaction", "BrakeDemo",
                "RotorInitModes", "InhomogeneousRotorInitModes", "VerticalShaftThrustPath",
                "VerticalThrustChain", "VerticalHousingReaction", "MomentLeverArm",
                "EccentricBrakeCoupling", "PlainBearingFriction",
                "HydrodynamicBearingIsotropyCheck"}

VERDICT = re.compile(r"(\d+)/(\d+) checks passed")
CASE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load(path):
    """Last verdict per case wins.

    The two logs do not share a column order -- the before log went through three
    runner revisions -- so the only reliable parse is: field 0 is the case name,
    and the verdict is whatever "N/M checks passed" appears anywhere on the line.
    Lines with NO VERDICT are aborted attempts (container restarts), not results,
    and lines with no case name are batch totals.
    """
    out = {}
    for line in path.read_text().splitlines():
        parts = [f.strip() for f in line.strip().split("|")]
        if len(parts) < 2 or not CASE.match(parts[0]):
            continue
        if "NO VERDICT" in line:
            continue
        v = VERDICT.search(line)
        if v:
            out[parts[0]] = (int(v.group(1)), int(v.group(2)))
    return out


def fmt(v):
    if v is None:
        return "?"
    return "%d/%d" % v


before = load(R / "before_refactor.log")
after = load(R / "after_refactor.log")

print("%-38s %-12s %-12s %s" % ("case", "before", "after", "verdict"))
print("-" * 78)
regressions = 0
for case in sorted(after):
    a = after[case]
    if case in before:
        b, note = before[case], ""
    elif case in BATCH_PASSED:
        b, note = None, "  (before: passed in batch, count not broken out)"
    else:
        b, note = None, "  (no before verdict)"

    a_all = a is not None and a[0] == a[1]
    if b is not None:
        ok = a == b
        verdict = "SAME" if ok else "*** CHANGED ***"
    else:
        ok = a_all
        verdict = "PASS (as before)" if ok else "*** NOW FAILING ***"
    if not ok:
        regressions += 1
    print("%-38s %-12s %-12s %s%s" % (case, fmt(b), fmt(a), verdict, note))

missing = [c for c in (R / "_after_cases.txt").read_text().split()
           if c and c not in after]
print("-" * 78)
if missing:
    print("NOT RUN: %s" % ", ".join(missing))
print("%d of %d cases differ from their before-verdict" % (regressions, len(after)))
sys.exit(1 if (regressions or missing) else 0)
