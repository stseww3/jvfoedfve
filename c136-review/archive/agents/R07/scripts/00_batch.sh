#!/usr/bin/env bash
# 00_batch.sh — R07：在 run-heavy.sh 的同一个槽位里，把同一局的几条重计算命令一条接一条串行跑（同一时刻只有一个进程）。
#
# 机器排队长的时候，每条 node 命令单独排一次队，120 秒的本地超时大半耗在排队上。这个脚本让一次排到的槽位
# 连着跑同一局的后面几步；被超时打断也没关系——跑完的步骤记在 <stepfile>.done 里，下次接着跑没做完的。
#
# 用法（在工作区根目录）：
#   timeout 120 bash c136-review/tools/run-heavy.sh bash c136-review/agents/R07/scripts/00_batch.sh <stepfile>
# stepfile：每行一条命令；以 node 开头的自动加 --max-old-space-size=700（和 run-heavy.sh 对单条 node 命令的处理一样）；
#           空行和 # 开头的行跳过。输出追加到 <stepfile>.log；每步结束打印一行「步骤号 退出码 秒数」。
# 一步失败（退出码非 0）就停，不往下跑。
set -u
STEPS=${1:?用法：00_batch.sh <stepfile>}
DONE="$STEPS.done"
LOG="$STEPS.log"
touch "$DONE"
n=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  n=$((n + 1))
  key=$(printf '%s' "$line" | md5sum | cut -d' ' -f1)
  if grep -q "^$key\$" "$DONE"; then
    echo "步骤 $n 已做过，跳过"
    continue
  fi
  case "$line" in node\ *) cmd="node --max-old-space-size=700 ${line#node }" ;; *) cmd="$line" ;; esac
  s=$(date +%s)
  echo "### $(date -u +%H:%M:%S) 步骤 $n：$line" >> "$LOG"
  bash -c "$cmd" >> "$LOG" 2>&1
  rc=$?
  echo "步骤 $n 退出码 $rc 用时 $(( $(date +%s) - s )) 秒：${line:0:110}"
  if [ $rc -ne 0 ]; then
    tail -5 "$LOG"
    exit $rc
  fi
  echo "$key" >> "$DONE"
done < "$STEPS"
echo "全部 $n 步做完"
