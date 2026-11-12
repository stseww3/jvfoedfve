#!/usr/bin/env bash
# 102_cp_batch.sh — R07：按清单跑 100_checkpoint.mjs（每次都套重计算闸、限时 120 秒；已有输出的跳过）。
# 用法：bash 102_cp_batch.sh <清单文件> [日志文件]
#   清单每行：<局> <名字> <100_checkpoint.mjs 的其余参数>（102_cp_plan.py 生成）
# 这台机器的重计算槽位是全机共用的，这里一次只占一个：
#   · 每次取清单里还没有输出的前 CP_GROUP 条（默认 8），占到槽位后在同一个进程里连跑；进程自己看时间预算，
#     跑不完的留给下一次；分到的 CPU 太少（机器被别的进程占满，不足 CP_MIN_SHARE，默认 3%）就立刻让出槽位，连续 10 次就停。
#   · 排队每次最多等 12 秒（重计算闸自己的排队），等不到就重新排；总时长上限 CP_MAX_HOURS（默认 10 小时）。
#   · 同一条连续 6 次占到槽位都没跑出来，就先放到最后。
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
PLAN="$1"
LOG="${2:-$HERE/../out/_cache/cp/batch.log}"
GROUP="${CP_GROUP:-8}"
MAXS=$(( ${CP_MAX_HOURS:-10} * 3600 ))
CP="$HERE/../out/_cache/cp"
mkdir -p "$(dirname "$LOG")"
start=$(date +%s)
declare -A tries=()
got=0; noslot=0; starved=0
echo "$(date +%H:%M:%S) START plan=$PLAN" >> "$LOG"
while :; do
  if [ $(( $(date +%s) - start )) -ge "$MAXS" ]; then echo "$(date +%H:%M:%S) STOP 到总时长上限" >> "$LOG"; break; fi
  pend=(); late=(); total=0; done_n=0
  while read -r mid tag rest; do
    [ -z "${mid:-}" ] && continue
    total=$((total+1))
    if [ -s "$CP/$mid/$tag.json" ]; then done_n=$((done_n+1)); continue; fi
    if [ "${tries[$mid/$tag]:-0}" -ge 6 ]; then late+=("$mid --tag $tag $rest"); else pend+=("$mid --tag $tag $rest"); fi
  done < "$PLAN"
  if [ "${#pend[@]}" -eq 0 ]; then
    [ "${#late[@]}" -eq 0 ] && break
    # 只剩反复没跑出来的：清掉计数再试一轮；这一轮还是一条都没出来就停
    if [ "${lastchance:-0}" -eq 1 ]; then echo "$(date +%H:%M:%S) STOP 剩 ${#late[@]} 条反复跑不出来" >> "$LOG"; break; fi
    lastchance=1; tries=(); continue
  fi
  argv=(); heads=()
  k=0
  while [ "$k" -lt "$GROUP" ] && [ "$k" -lt "${#pend[@]}" ]; do
    # shellcheck disable=SC2206
    w=(${pend[$k]})
    argv+=("${w[@]}" +++); heads+=("${w[0]}/${w[2]}")
    k=$((k+1))
  done
  out="$(cd "$ROOT" && HEAVY_QUEUE=12 CP_MIN_SHARE="${CP_MIN_SHARE:-0.03}" CP_DEADLINE_MS=$(( $(date +%s%3N) + 114000 )) timeout 120 bash c136-review/tools/run-heavy.sh node "$HERE/100_checkpoint.mjs" "${argv[@]}" 2>&1)"
  rc=$?
  if [ "$rc" -eq 75 ]; then noslot=$((noslot+1)); continue; fi
  got=$((got+1))
  if [ "$rc" -eq 76 ]; then
    starved=$((starved+1)); streak=$(( ${streak:-0} + 1 ))
    # 连续 10 次占到槽位都因为 CPU 不足让出：停下来，不空转
    if [ "$streak" -ge 10 ]; then echo "$(date +%H:%M:%S) STOP 连续 $streak 次 CPU 不足，稍后重新启动本脚本" >> "$LOG"; break; fi
  else streak=0; fi
  printf '%s\n' "$out" | grep -E '^[A-Z][0-9]+ |^FAIL|^LATER|^STARVED|run-heavy' | cut -c1-420 | while IFS= read -r line; do echo "$(date +%H:%M:%S) $line"; done >> "$LOG"
  n_new=0
  for h in "${heads[@]}"; do [ -s "$CP/$h.json" ] && n_new=$((n_new+1)); done
  if [ "$n_new" -eq 0 ]; then tries[${heads[0]}]=$(( ${tries[${heads[0]}]:-0} + 1 )); else lastchance=0; fi
  echo "$(date +%H:%M:%S) GROUP rc=$rc new=$n_new done=$((done_n+n_new))/$total 占到槽位 $got 次（其中 CPU 不足让出 $starved 次），排不到 $noslot 次" >> "$LOG"
done
echo "$(date +%H:%M:%S) DONE plan=$PLAN" >> "$LOG"
