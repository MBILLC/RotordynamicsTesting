#!/bin/bash
# Copyright © 2026 Model Based Innovation LLC. All rights reserved.
# Baseline runner: ONE CASE PER PROCESS, resumable via _done.txt.
# Lives on the HOME volume, NOT the session scratchpad -- the scratchpad is wiped
# when the code-server container restarts, which is exactly what killed the
# previous runner mid-run.
R=/home/jovyan/impact/local_projects/Rotordynamicsdevelopment/Testing/Resources
RD=$R/HtmlReports_before
J=/home/jovyan/impact/local_projects/ModCheck/ModCheck/Resources/CronLogs/memory_watch_vscode.jsonl
DONE=$R/_done.txt; touch "$DONE"; mkdir -p "$RD"
while read -r c; do
  [ -z "$c" ] && continue
  grep -qx "$c" "$DONE" && continue
  n0=$(wc -l < "$J" 2>/dev/null || echo 0); t0=$(date +%s)
  env -u MODELON_IMPACT_CLIENT_API_KEY python3 -u "$R/run_regression.py" \
      --case "$c" --error-log "$R/batch2_errors.log" \
      --html-report-dir "$RD" > "$R/case_$c.log" 2>&1
  rc=$?; dt=$(( $(date +%s) - t0 ))
  pk=$(python3 - "$J" "$n0" <<'PY'
import json,sys
try: rows=[json.loads(l) for l in open(sys.argv[1])][int(sys.argv[2]):]
except Exception: rows=[]
rows=[r for r in rows if "current" in r]
if rows:
    p=max(r["current"] for r in rows)/2**30
    h=max((q["rss"] for r in rows for q in r.get("top",[]) if "regression_test" in q["cmd"]),default=0)/2**20
    print(f"peak {p:.2f} GiB, harness {h:.0f} MiB")
else: print("peak n/a")
PY
)
  v=$(grep -E "checks passed" "$R/case_$c.log" | tail -1)
  f=$(grep -cE "\bFAIL\b" "$R/case_$c.log")
  echo "=== $c | ${dt}s | $pk | ${v:-NO VERDICT} | FAIL lines=$f | rc=$rc"
  echo "$c | ${dt}s | $pk | ${v:-NO VERDICT} | FAIL lines=$f" >> "$R/before_refactor.log"
  [ -n "$v" ] && echo "$c" >> "$DONE"
done < "$R/_remaining.txt"
echo "=== BASELINE COMPLETE $(date +%H:%M:%S) — $(wc -l < "$DONE") done ==="
