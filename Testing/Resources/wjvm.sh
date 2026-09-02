#!/bin/bash
# 1 Hz peak-catcher: cgroup total + java RSS, to catch a compile-JVM spike that a
# 5 s sampler misses. Each line flushed, so the log stays valid right up to a kill.
OUT=/home/jovyan/impact/local_projects/Rotordynamicsdevelopment/Testing/Resources/jvm_watch.log
while true; do
  cur=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 0)
  stats=$(ps -eo rss,args | grep "[j]ava" | awk '{s+=$1; if($1>m) m=$1} END {print s+0, m+0}')
  py=$(ps -eo rss,args | grep "[r]egression_testing" | awk '{s+=$1} END {print s+0}')
  ts=$(date +%H:%M:%S)
  echo "$cur $stats ${py:-0} $ts" | awk '{printf "%s cgroup=%.2f java=%.2f javamax=%.2f py=%.2f\n",$5,$1/1073741824,$2/1048576,$3/1048576,$4/1048576}' >> "$OUT"
  sleep 1
done
