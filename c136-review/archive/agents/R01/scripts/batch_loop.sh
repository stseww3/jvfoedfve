#!/usr/bin/env bash
# batch_loop.sh — 后台把一个步骤文件跑完：每一轮经 run-heavy.sh 拿一个槽位跑 run_batch.sh（一轮最多 110 秒，跑完放槽、重新排队），
# 直到步骤文件里每一行都有 .done，或者连续两轮一条也没跑成（失败的行不会无限重试）。
# 用法（在 agents/R01 下，放在 tmux 里）：bash scripts/batch_loop.sh <步骤文件> <日志文件>
set -u
steps=${1:?步骤文件}; log=${2:?日志文件}
stall=0
: > "$log"
while :; do
  left=0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    [ -e "${line%% *}.done" ] || left=$((left + 1))
  done < "$steps"
  [ "$left" -eq 0 ] && break
  before=$left
  HEAVY_QUEUE=3000 bash ../../tools/run-heavy.sh bash scripts/run_batch.sh "$steps" >> "$log" 2>&1
  after=0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    [ -e "${line%% *}.done" ] || after=$((after + 1))
  done < "$steps"
  if [ "$after" -ge "$before" ]; then stall=$((stall + 1)); else stall=0; fi
  [ "$stall" -ge 2 ] && { echo "LOOP-STALLED left=$after" >> "$log"; break; }
done
echo "LOOP-DONE left=$left" >> "$log"
