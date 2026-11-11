#!/usr/bin/env bash
# run_batch.sh — 在一个 run-heavy 槽位里顺序跑几条 node 命令（全机只有 2 个槽、二十多个 agent 排队时，省掉逐条排队）。
#
# 用法（在 agents/R01 目录下）：
#   timeout 118 bash ../../tools/run-heavy.sh bash scripts/run_batch.sh <步骤文件>
# 步骤文件每行： <输出文件> <命令…>      （# 开头的行和空行跳过）
#   - 每条命令的标准输出和错误都写进 <输出文件>；跑完且退出码 0 就在旁边留一个 <输出文件>.done
#   - 已有 .done 的行跳过，所以槽位超时被杀以后重跑同一个步骤文件会从没做完的那条接着做
#   - 开跑满 BATCH_BUDGET 秒（默认 85）以后不再开新的一条（run-heavy 的总时限是 110 秒）
# 严格串行：一条跑完才跑下一条；node 一律带 --max-old-space-size=700。
set -u
steps=${1:?用法：run_batch.sh <步骤文件>}
budget=${BATCH_BUDGET:-85}
start=$(date +%s)
n=0; ran=0; skipped=0; left=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  n=$((n + 1))
  out=${line%% *}
  cmd=${line#* }
  if [ -e "$out.done" ]; then skipped=$((skipped + 1)); continue; fi
  if [ $(( $(date +%s) - start )) -ge "$budget" ]; then left=$((left + 1)); continue; fi
  mkdir -p "$(dirname "$out")"
  case "$cmd" in node\ *) cmd="node --max-old-space-size=700 ${cmd#node }" ;; esac
  t0=$(date +%s)
  if bash -c "$cmd" > "$out" 2>&1; then
    touch "$out.done"; ran=$((ran + 1))
    echo "[batch] 完成 $(( $(date +%s) - t0 ))s  $out"
  else
    echo "[batch] 失败 rc=$? $(( $(date +%s) - t0 ))s  $out"; left=$((left + 1))
  fi
done < "$steps"
echo "[batch] 共 $n 条：这次跑完 $ran，早先已完成 $skipped，剩 $left（用时 $(( $(date +%s) - start ))s）"
