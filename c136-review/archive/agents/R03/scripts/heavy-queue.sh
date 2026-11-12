#!/usr/bin/env bash
# heavy-queue.sh — 把一串调试用的重计算（node scripts/dbg/*.mjs 等）排队，逐条过 run-heavy.sh 的闸。
#
#   bash scripts/heavy-queue.sh <名字> <清单文件>
#   清单文件（放在 scripts/queues/ 下）每行：<输出文件，相对 agents/R03>|<命令…>     # 开头的行、空行跳过
#   例：out/trace/A041-coast.txt|node scripts/dbg/coast.mjs A041 1500,1800,2100
#
# 机器忙的时候影子重放一遍要 100 秒上下，默认的 110 秒闸不够，所以这里单条超时 Q_TIMEOUT（默认 900 秒）、
# 排队最多等 Q_QUEUE（默认 1800 秒）。要放在 tmux 里跑；进度写 /tmp/r03-q-<名字>.log，每条一行 rc，最后一行 Q-DONE。
# 输出先写到 <输出文件>.tmp，成功才改名，失败的不留半截文件；错误输出在 /tmp/r03-q-<名字>.err。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
name=${1:?用法：heavy-queue.sh <名字> <清单文件>}
list=${2:?用法：heavy-queue.sh <名字> <清单文件>}
log=/tmp/r03-q-$name.log
echo "Q-START $name $(date +%s)" > "$log"
GATE="$HERE/../../../tools/run-heavy.sh"
while IFS='|' read -r out cmd <&3; do
  case "$out" in ''|'#'*) continue ;; esac
  s=$(date +%s)
  # shellcheck disable=SC2086
  HEAVY_QUEUE=${Q_QUEUE:-1800} HEAVY_TIMEOUT=${Q_TIMEOUT:-900} bash "$GATE" $cmd > "$out.tmp" 2> "/tmp/r03-q-$name.err" < /dev/null
  rc=$?
  if [ $rc -eq 0 ]; then mv "$out.tmp" "$out"; else rm -f "$out.tmp"; fi
  echo "$out rc=$rc secs=$(( $(date +%s) - s ))" >> "$log"
done 3< "$list"
echo "Q-DONE $(date +%s)" >> "$log"
