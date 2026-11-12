#!/usr/bin/env bash
# loop.sh — 断面归因批次的后台循环（放在 tmux 里跑）。
# 和 scripts/batch_loop.sh 一样逐轮经 run-heavy.sh 拿槽位跑 run_batch.sh，区别只是每一轮给得更长：
# 机器负载高的时候（nice 19 只分到一成多的 CPU）一条 20 秒 CPU 的步骤墙钟要两三分钟，110 秒一轮会被掐断。
#   每轮最长 LOOP_ROUND 秒（缺省 600；run-heavy.sh 允许后台长任务到 1800），开跑满 LOOP_ROUND−120 秒后不再开新的一条。
# 用法（在 agents/R01 下）：bash scripts/ckpt/loop.sh <步骤文件> <日志文件>
set -u
steps=${1:?步骤文件}; log=${2:?日志文件}
round=${LOOP_ROUND:-600}
stall=0
starve=0
: > "$log"
count_left() {
  local n=0 line
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    [ -e "${line%% *}.done" ] || n=$((n + 1))
  done < "$steps"
  echo "$n"
}
while :; do
  before=$(count_left)
  [ "$before" -eq 0 ] && break
  HEAVY_QUEUE=3000 HEAVY_TIMEOUT=$round BATCH_BUDGET=$((round - 120)) bash ../../tools/run-heavy.sh bash scripts/run_batch.sh "$steps" >> "$log" 2>&1
  rc=$?
  after=$(count_left)
  # 退出码 75 = 排队等不到槽位（机器忙），不算步骤出错；最多连续等 LOOP_STARVE 轮（缺省 8）
  if [ "$rc" -eq 75 ]; then
    starve=$((starve + 1))
    echo "LOOP-QUEUE-TIMEOUT $(date +%H:%M:%S) starve=$starve left=$after" >> "$log"
    [ "$starve" -ge "${LOOP_STARVE:-8}" ] && { echo "LOOP-STARVED left=$after" >> "$log"; break; }
    continue
  fi
  starve=0
  if [ "$after" -ge "$before" ]; then stall=$((stall + 1)); else stall=0; fi
  [ "$stall" -ge 2 ] && { echo "LOOP-STALLED left=$after" >> "$log"; break; }
done
echo "LOOP-DONE left=$(count_left)" >> "$log"
