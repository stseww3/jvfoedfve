#!/usr/bin/env bash
# heavy_seq.sh — 重计算槽位难排的时候用：排到一个槽位以后，把任务清单里还没做的任务按顺序一条一条跑
#   （串行，同一时刻只有一个 node 在重放），剩下的时间不够下一条的估时就停。每条任务到 DEADLINE 前 2 秒还没跑完就杀掉、下次重跑。
# 用法（重活，套 run-heavy；DEADLINE = 这条命令必须结束的时刻，秒）：
#   DEADLINE=$(( $(date +%s) + 116 )) HEAVY_QUEUE=85 HEAVY_TIMEOUT=110 timeout 119 bash ../../tools/run-heavy.sh bash scripts/heavy_seq.sh [任务清单]
# 任务清单（默认 tmp/heavy_tasks.txt）每行三列，用制表符隔开：估时（秒）、输出文件、命令（在 agents/R04/ 下执行，标准输出写进输出文件）。
#   输出文件已经存在的任务跳过（先写 <输出文件>.part，命令退出码为 0 才改名），# 开头的行跳过。
cd "$(dirname "$0")/.." || exit 2
list=${1:-tmp/heavy_tasks.txt}
[ -f "$list" ] || { echo "## 没有任务清单 $list"; exit 2; }
ran=0; pend=0
while IFS=$'\t' read -r est out cmd; do
  case "$est" in ''|\#*) continue;; esac
  [ -s "$out" ] && continue
  now=$(date +%s); left=$(( ${DEADLINE:-$((now + 100))} - now ))
  if [ "$left" -lt $(( est + 3 )) ]; then pend=$((pend + 1)); continue; fi
  mkdir -p "$(dirname "$out")"
  t0=$now
  if timeout "$(( left - 2 ))" bash -c "$cmd" > "$out.part" 2>&1; then
    mv "$out.part" "$out"; ran=$((ran + 1))
    echo "## 完成 $out（$(( $(date +%s) - t0 )) 秒）"
  else
    echo "## 失败或超时 $out（$(( $(date +%s) - t0 )) 秒；见 $out.part 的末行：$(tail -1 "$out.part" | cut -c1-160)）"
    pend=$((pend + 1))
  fi
done < "$list"
echo "## 这一次跑完 $ran 条，还剩 $pend 条"
[ "$pend" = 0 ] || exit 75
