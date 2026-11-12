#!/usr/bin/env bash
# profile_check.sh — 对手模型的参数文件 sim-v2/calib/human-profile.json 从录像从头重算一遍，与入库的那份逐字节比。
# 做法：tools/human_profile.mjs 把核心 20 局的录像各重放一遍（只放录像，不挂策略）。一次重计算槽位里算不完，
# 所以每次算到时间预算为止、按局缓存在一个新的临时目录里（不用 sim-v2/_cache/ 里已有的缓存），再排下一次接着算。
# 结果：sim-v2/calib/human-profile-check.json = { matches: 局数, same: 是否逐字节相同 }
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/profile_check.sh
set -u
cd "$(dirname "$0")/../.." || exit 2
M=$(grep -v '^#' sim-v2/tools/arena_calib_list20.txt | awk 'NF {print $1}' | paste -sd, -)
N=$(echo "$M" | tr ',' '\n' | grep -c .)
C=${PROFILE_CHECK_DIR:-/tmp/r06-profile-check}
mkdir -p "$C"
export HEAVY_TIMEOUT=110
export HEAVY_SLOTS=2    # 统筹广播 0006 定的上限；写死在这里，不跟着 run-heavy.sh 里的缺省值走
export HEAVY_QUEUE=900
done_=0
crowded=0
for i in $(seq 1 90); do
  # --min-share / --hard-ms：机器太挤（这个进程分不到 15% 的 CPU）时这一次不算，不白占槽位；连着 12 次都太挤就先停，过后重排
  r=$(bash ../../tools/run-heavy.sh timeout 120 node --max-old-space-size=700 sim-v2/tools/human_profile.mjs --matches "$M" --cache-dir "$C/cache" --budget-ms 60000 --min-share 0.15 --hard-ms 100000 --out "$C/human-profile.json" 2>&1 | tail -1 | cut -c1-200)
  case "$r" in
    *"已写"*) done_=1; break ;;
    *"时间预算到了"*) echo "$(date -u +%H:%M:%S) $r"; crowded=0 ;;
    *"机器太挤"*) echo "$(date -u +%H:%M:%S) $r"; crowded=$((crowded + 1)) ;;
  esac
  if [ "$crowded" -ge 12 ]; then echo "连着 12 次机器都太挤，这一阶段先停（已算的局留在缓存里，过后重排接着算）"; exit 1; fi
done
if [ $done_ -ne 1 ]; then echo "排了 90 次还没算完，停"; exit 1; fi
if cmp -s "$C/human-profile.json" sim-v2/calib/human-profile.json; then same=true; else same=false; fi
printf '{ "matches": %s, "same": %s }\n' "$N" "$same" > sim-v2/calib/human-profile-check.json
cat sim-v2/calib/human-profile-check.json
