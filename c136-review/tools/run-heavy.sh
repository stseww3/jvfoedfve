#!/usr/bin/env bash
# run-heavy.sh — 重计算闸。所有 node 进程、以及预计超过 10 秒或 300 MB 的脚本，都套这一层：
#
#   bash c136-review/tools/run-heavy.sh node some-replay-script.mjs …
#   HEAVY_TIMEOUT=600 bash c136-review/tools/run-heavy.sh python3 scan.py     # 更长的任务要放后台跑
#
# 这台机器只有 4 核 15 G，两个复盘组二十多个 agent 共用。本脚本和 c135 组的 tools/c135/run.sh
# 用同一组锁文件（/tmp/c135-slots），所以全机同一时刻最多 3 个重计算进程，槽位满了自动排队。
#   - nice -n 19；node 自动加 --max-old-space-size=700
#   - 默认超时 110 秒（HEAVY_TIMEOUT 可调）
#   - 排队最多等 HEAVY_QUEUE 秒（默认 900），等不到就退出码 75
set -u
SLOTS=${HEAVY_SLOTS:-3}
LIMIT=${HEAVY_TIMEOUT:-110}
QUEUE=${HEAVY_QUEUE:-900}
DIR=${HEAVY_DIR:-/tmp/c135-slots}
mkdir -p "$DIR" 2>/dev/null && chmod 1777 "$DIR" 2>/dev/null
if [ $# -eq 0 ]; then
  echo "用法：bash c136-review/tools/run-heavy.sh <命令…>" >&2
  exit 2
fi
if [ "$1" = node ]; then
  shift
  set -- node --max-old-space-size=700 "$@"
fi

run_locked() {
  nice -n 19 timeout "$LIMIT" "$@" 9>&-
  rc=$?
  [ $rc -eq 124 ] && echo "【run-heavy】超时 ${LIMIT}s 被杀。更长的任务：HEAVY_TIMEOUT=1800 且放后台跑。" >&2
  exit $rc
}

start=$(date +%s)
turn=$(( ($$ % SLOTS) + 1 ))
while :; do
  for k in $(seq 1 "$SLOTS"); do
    exec 9>>"$DIR/slot$k.lock"
    flock -n 9 && run_locked "$@"
    exec 9>&-
  done
  # 槽位全满：在其中一个槽上阻塞等几秒，再轮下一个
  exec 9>>"$DIR/slot$turn.lock"
  flock -w 5 9 && run_locked "$@"
  exec 9>&-
  turn=$(( turn % SLOTS + 1 ))
  if [ $(( $(date +%s) - start )) -ge "$QUEUE" ]; then
    echo "【run-heavy】排队 ${QUEUE}s 仍无空槽，放弃。稍后再试。" >&2
    exit 75
  fi
done
