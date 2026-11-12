#!/usr/bin/env bash
# g0_run.sh — 按清单逐个跑 checkpoint（一次只跑一个 node，每个都套 run-heavy.sh + timeout 120），结果写到 sim-v2/calib/<目录>/<标签>.json。
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/g0_run.sh <目录> <<'EOF'
#   <标签> <局> <t0> <len> <对照策略> <通道> [其余开关原样传给 teamgate-v2.mjs]
#   EOF
# 已有结果文件的标签跳过（要重跑先删文件，或设 FORCE=1）。
set -u
dir="sim-v2/calib/$1"
mkdir -p "$dir"
while read -r tag mid t0 len strat chan rest; do
  [ -z "${tag:-}" ] && continue
  case "$tag" in \#*) continue ;; esac
  out="$dir/$tag.json"
  if [ -s "$out" ] && [ "${FORCE:-0}" != "1" ]; then echo "跳过 $tag（已有）"; continue; fi
  # shellcheck disable=SC2086
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode checkpoint --match "$mid" --t0 "$t0" --len "$len" \
    --baseline "$strat" --channel "$chan" --quiet --out "$out" $rest 2>&1 | tail -2
done
