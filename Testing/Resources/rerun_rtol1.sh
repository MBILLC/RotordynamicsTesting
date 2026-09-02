#!/bin/bash
# Copyright © 2026 Model Based Innovation LLC. All rights reserved.
# Re-run every case that FAILED in the baseline at --rtol-factor 1, i.e. at the
# case's OWN rtol -- the tolerance its reference was stored at. The routine suite
# re-simulates at 100x looser rtol (REGRESSION_RTOL_FACTOR), which swamps
# near-zero residuals; this pass tells a harness artifact (passes at 1) from a
# real discrepancy (still fails at 1).
#
# Waits for the baseline runner to exit first: one Impact compiler worker, so
# overlapping runs just queue behind each other.
R=/home/jovyan/impact/local_projects/Rotordynamicsdevelopment/Testing/Resources
OUT=$R/rtol1.log
while pgrep -f 'run_baseline\.sh' > /dev/null; do sleep 20; done
echo "=== rtol-factor 1 pass, baseline finished, $(date +%H:%M:%S) ===" >> "$OUT"
cases=$(grep "^=== " "$R/baseline.log" \
        | awk -F'|' '$5 ~ /FAIL lines=[1-9]/ {gsub(/^=== /,"",$1); gsub(/ +$/,"",$1); print $1}' \
        | sort -u)
echo "cases to re-check: $(echo "$cases" | wc -l)" >> "$OUT"
for c in $cases; do
  t0=$(date +%s)
  env -u MODELON_IMPACT_CLIENT_API_KEY python3 -u "$R/run_regression.py" \
      --case "$c" --rtol-factor 1 --html-report-dir "$R/HtmlReports_rtol1" \
      > "$R/rtol1_$c.log" 2>&1
  dt=$(( $(date +%s) - t0 ))
  v=$(grep -E "checks passed" "$R/rtol1_$c.log" | tail -1)
  f=$(grep -cE "\bFAIL\b" "$R/rtol1_$c.log")
  echo "=== $c | ${dt}s | ${v:-NO VERDICT} | FAIL lines=$f" >> "$OUT"
done
echo "=== RTOL1 PASS COMPLETE $(date +%H:%M:%S) ===" >> "$OUT"
