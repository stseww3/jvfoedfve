#!/usr/bin/env bash
# sections.sh — 把一局的全部事实表（digest / logdigest / simdigest / latency / landcap 的各段）落到 out/<id>/sec/ 下，
# 复盘里引用的数字都从这些文件里抄。每段单独一个 python 进程、各自 timeout；整组按 dig / log / sim / led 四批跑，
# 每批都在 120 秒内：
#   bash scripts/sections.sh <matchId> dig     # 对局包侧（digest.py）
#   bash scripts/sections.sh <matchId> log     # 日志侧（logdigest.py）
#   bash scripts/sections.sh <matchId> sim     # 录像真值侧（simdigest.py；没有可用录像的局跳过）
#   bash scripts/sections.sh <matchId> led     # 延迟账 + 好地账 + 核心期出口（latency.py / landcap.py / coregates.py；含 json）
#   bash scripts/sections.sh <matchId> foe     # 外人侧（simdigest.py foedon / foepct / foeled / foewho / foehabit）
set -u
mid=${1:?用法：sections.sh <matchId> dig|log|sim|led|foe}
grp=${2:?用法：sections.sh <matchId> dig|log|sim|led|foe}
here=$(cd "$(dirname "$0")" && pwd)
sec="$here/../out/$mid/sec"
mkdir -p "$sec"
run() { # run <输出文件名> <脚本> <段> [参数…]
  local out=$1; shift
  local script=$1; shift
  timeout 60 python3 "$here/$script" "$mid" "$@" > "$sec/$out" 2>&1
  local rc=$?
  [ $rc -ne 0 ] && echo "  [rc=$rc] $script $*"
  return 0
}
case "$grp" in
  dig)
    for s in roster teams timeline outsiders deaths donations drops spawn picks spawnlog slots boxed attacks lag teamwar; do run "dig_$s.txt" digest.py "$s"; done
    run dig_snap.txt digest.py snap 630 1170 1530 2070 3060 4050
    ;;
  log)
    for s in stale silent seqlag overcap drop30 wall wallms donlog cmdmix idleloss spend fireband capidle freezebound quotacap foes assists opening peace oplag issued bursts boxboats harvest crumb thinbig noeffect noefftl gaps sentchk zerodrop; do
      run "log_$s.txt" logdigest.py "$s"
    done
    run log_donval.txt logdigest.py donval
    ;;
  sim)
    for s in check boats fees nfs gaps husks poolai protbox medians teams roster dens ledger deaths don cmds probe gifts front boxed landings shadow exchange gapgrow boxedout dups crowd bursts collapse lumps top halves contact sieges pokes boatwar; do
      run "sim_$s.txt" simdigest.py "$s"
    done
    run sim_gates_600_1500.txt simdigest.py gates 600 1500
    run sim_gates_1500_3000.txt simdigest.py gates 1500 3000
    run sim_gates_3000.txt simdigest.py gates 3000 99999
    ;;
  foe)
    for s in foedon foepct foeled foewho foehabit; do run "sim_$s.txt" simdigest.py "$s"; done
    ;;
  led)
    run lat_all.txt latency.py all
    run land_all.txt landcap.py all
    timeout 60 python3 "$here/latency.py" "$mid" json | tail -1
    timeout 60 python3 "$here/landcap.py" "$mid" json | tail -1
    # 核心期出口（需要 probe.json 的 tally，且录像到 t>=1500）
    timeout 60 python3 "$here/coregates.py" "$mid" json > "$sec/coregates.txt" 2>&1 || echo "  [coregates 跳过] $(tail -1 "$sec/coregates.txt")"
    # 输血账（需要 sim_state.json）
    timeout 60 python3 "$here/donflow.py" "$mid" json > "$sec/donflow.txt" 2>&1 || echo "  [donflow 跳过] $(tail -1 "$sec/donflow.txt")"
    # 对手画像（需要 sim_state.json）
    timeout 60 python3 "$here/foeprofile.py" "$mid" json > "$sec/foeprofile.txt" 2>&1 || echo "  [foeprofile 跳过] $(tail -1 "$sec/foeprofile.txt")"
    ;;
  *) echo "未知批次 $grp"; exit 2 ;;
esac
ls "$sec" | wc -l
