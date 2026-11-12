#!/usr/bin/env bash
# arena_calib.sh — 对手模型的验收：在真局房间里把其余真人全部换成闭环原型（从第 0 拍起），我方挂当年那一版策略，
# 各断面的走势对着同一局的录像（其余真人人均地、在场占比、兵密度、内置 AI 占陆地、我方人均地 ÷ 其余真人人均地）。
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/arena_calib.sh <目录> <拍数> <通道> [其余开关] < 局号清单（每行：局号 策略）
# 一次只跑一个 node，每个都套 run-heavy.sh + timeout 120；结果写 sim-v2/calib/<目录>/<局号>.json。
set -u
dir="sim-v2/calib/$1"; len="$2"; chan="$3"; shift 3
mkdir -p "$dir"
while read -r mid strat rest; do
  [ -z "${mid:-}" ] && continue
  case "$mid" in \#*) continue ;; esac
  out="$dir/$mid.json"
  if [ -s "$out" ] && [ "${FORCE:-0}" != "1" ]; then echo "跳过 $mid（已有）"; continue; fi
  # shellcheck disable=SC2086
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node sim-v2/teamgate-v2.mjs --mode arena --room "$mid" --baseline "$strat" --arm baseline \
    --channel "$chan" --len "$len" --quiet --out "$out" "$@" $rest 2>&1 | tail -1
done
