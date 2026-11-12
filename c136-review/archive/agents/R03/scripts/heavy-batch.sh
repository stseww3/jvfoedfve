#!/usr/bin/env bash
# heavy-batch.sh — 在「已经拿到的一个重计算槽」里顺序跑几条短的 node 命令，省得每条都重新排一次队。
#
#   （由 heavy-queue.sh 调用）bash scripts/heavy-batch.sh <步骤文件>
#   步骤文件每行：<输出文件，相对 agents/R03>|<命令…>      # 开头的行、空行跳过
#
# 机器忙的时候排一次队要十几分钟，而一条消融只跑十几秒到一百多秒；把几条并成一批，一批占槽不超过 heavy-queue.sh
# 给的 Q_TIMEOUT。每一步单独限时 B_STEP 秒（默认 240），输出先写 .tmp，成功才改名；已经有输出文件的步骤跳过，
# 所以一批被整体超时杀掉之后重新排队会从没做完的那一步接着做。node 一律加 --max-old-space-size=700。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/.." || exit 1
steps=${1:?用法：heavy-batch.sh <步骤文件>}
fail=0
while IFS='|' read -r out cmd <&3; do
  case "$out" in ''|'#'*) continue ;; esac
  if [ -s "$out" ]; then echo "SKIP $out"; continue; fi
  mkdir -p "$(dirname "$out")"
  s=$(date +%s)
  # shellcheck disable=SC2086
  timeout "${B_STEP:-240}" ${cmd/#node /node --max-old-space-size=700 } > "$out.tmp" 2> "$out.err" < /dev/null
  rc=$?
  if [ $rc -eq 0 ]; then mv "$out.tmp" "$out"; rm -f "$out.err"; else rm -f "$out.tmp"; fail=1; fi
  echo "STEP $out rc=$rc secs=$(( $(date +%s) - s ))"
done 3< "$steps"
exit $fail
