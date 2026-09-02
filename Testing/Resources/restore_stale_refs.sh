#!/bin/bash
# Copyright © 2026 Model Based Innovation LLC. All rights reserved.
# Re-store the references of cases that STILL FAIL at --rtol-factor 1, i.e. whose
# stored trajectories no longer match intended behaviour. User confirmed
# 2026-09-02 that GearMesh's unilateral-contact rewrite (4df1a4b, 2026-09-01
# 21:16) is physically correct, so those references are stale, not the model.
#
# Deliberately NOT "every reference older than that commit": a stale reference
# that still PASSES is a valid baseline (HelicalThrustLocatedShaftCheck: stale,
# 14/14 at rtol 1). Re-storing those would overwrite good baselines and bake in
# whatever the model does today.
#
# Waits for the rtol-1 pass and the baseline finisher: one Impact compiler worker.
R=/home/jovyan/impact/local_projects/Rotordynamicsdevelopment/Testing/Resources
OUT=$R/restore_refs.log
BAK=$R/ReferenceResults_backup_20260902
while pgrep -f 'rerun_rtol1\.sh|finish_baseline\.sh' > /dev/null; do sleep 20; done
# TWO conditions, both required:
#   1. still fails at --rtol-factor 1  -> not a tolerance artifact
#   2. reference predates GearMesh.mo's rewrite (4df1a4b, 2026-09-01 21:16)
#      -> the stored trajectories are from before the intended physics change
# Condition 2 matters: PlanetarySequentialSidebandCheck fails at rtol 1 on
# ringAmp[4] (6.3e-11 against a 6.5e-08 amplitude -- noise floor) but its
# reference was stored AFTER the change, so re-storing it would bake in today's
# noise rather than fix staleness. It needs a tolerance/exclusion decision, not
# a new baseline.
CUTOFF=$(date -d '2026-09-01 21:16' '+%s')
failing=$(grep "^=== " "$R/rtol1.log" \
        | awk -F'|' '$4 ~ /FAIL lines=[1-9]/ {gsub(/^=== /,"",$1); gsub(/ +$/,"",$1); print $1}' \
        | sort -u)
cases=""
for c in $failing; do
  f="$R/ReferenceResults/$c.npz"
  [ -f "$f" ] || continue
  if [ "$(stat -c %Y "$f")" -lt "$CUTOFF" ]; then
    cases="$cases $c"
  else
    echo "  SKIP $c -- fails at rtol 1 but its reference postdates the GearMesh change; needs a tolerance decision, not a re-store" >> "$OUT"
  fi
done
echo "=== re-store pass $(date +%H:%M:%S) ===" >> "$OUT"
echo "cases still failing at rtol-factor 1: $(echo "$cases" | grep -c .)" >> "$OUT"
mkdir -p "$BAK"
for c in $cases; do
  # keep the old baseline: re-storing is destructive and this is the only copy
  cp -n "$R/ReferenceResults/$c.npz" "$BAK/$c.npz" 2>/dev/null
  t0=$(date +%s)
  env -u MODELON_IMPACT_CLIENT_API_KEY python3 -u "$R/run_regression.py" \
      --store --case "$c" > "$R/store_$c.log" 2>&1
  rc=$?; dt=$(( $(date +%s) - t0 ))
  s=$(grep -E "^stored " "$R/store_$c.log" | tail -1)
  echo "=== $c | ${dt}s | rc=$rc | ${s:-NO STORE LINE}" >> "$OUT"
done
echo "=== now re-checking the re-stored cases ===" >> "$OUT"
for c in $cases; do
  env -u MODELON_IMPACT_CLIENT_API_KEY python3 -u "$R/run_regression.py" \
      --case "$c" --html-report-dir "$R/HtmlReports_verify" > "$R/verify_$c.log" 2>&1
  v=$(grep -E "checks passed" "$R/verify_$c.log" | tail -1)
  echo "=== VERIFY $c | ${v:-NO VERDICT}" >> "$OUT"
done
echo "=== RE-STORE PASS COMPLETE $(date +%H:%M:%S) ===" >> "$OUT"
