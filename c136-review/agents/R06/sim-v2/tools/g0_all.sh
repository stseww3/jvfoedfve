#!/usr/bin/env bash
# g0_all.sh — 保真度验收报告（reports/SIM-V2-CALIBRATION-G0.md）要用的全部运行，按顺序排成一条队。
# 一次只跑一个 node，每个都套 run-heavy.sh + timeout 120；一个 node 里连着跑一批运行（tools/g0_batch.mjs：排一次重计算槽位跑一批，
# 每批不超过闸门的 110 秒）。已有结果文件的跳过，所以中途断了重新执行就接着跑。闸门排队到点仍没有空槽位的，接着重排。
# 只用历史旧策略：每一局跑它当年线上那一版（清单里写的版本和局号不符时，模拟器拒绝）。
#
# 用法（在 c136-review/agents/R06 下；整条队很长，放后台）：
#   bash sim-v2/tools/g0_all.sh [阶段…]     缺省：live bands lists core plan tail delay old oldcode profile tables
# 各阶段的产物：
#   live       sim-v2/calib/live/<局>.json            全部有录像的局的实盘签名（只放录像）
#   bands      sim-v2/calib/live-bands.json           实盘区间：策略版本 × 卡顿档，各项签名的 P25 / 中位 / P75
#   lists      sim-v2/tools/{verify_list,g0_list_more,g0_list_ext,g0_list_ext_more,attr_list,attr_list_ext,attr_list_seeds,fill_list}.txt（tools/g0_lists.py）
#   core       核心 20 局的 verify 与任务卡点名的 60 次断面（后面的清单要用它们的结果：hold 清单从 C2 的结果里挑运行）
#   plan       tools/g0_plan.txt 里的全部清单，按文件里的先后排优先级：排到一次槽位就从头接着往下跑。包括——
#              verify     sim-v2/calib/verify/<局>.json          入库各局：与真引擎重放逐断面核对、clone 自检、日志快照核对
#              g0         sim-v2/calib/g0/<标签>.json            630 / 1530 两个断面 × C0 / C1 / C2 / C3（g0_list.txt 的 60 次 + 补齐的 + 新接进来的局）
#              hold       sim-v2/calib/hold/<标签>.json          C2「最后一个已知点之后」那条假定的对照：追平（缺省）换成保持落后 / 之后的指令没落地（tools/hold_list.py 挑运行）
#              arena      sim-v2/calib/arena-acc20/<局>.json     对手模型标定：核心 20 个真局房间，从第 0 拍起闭环
#              arena      sim-v2/calib/batchcheck/arena-rerun/   抽两个房间换个次序在另一批里再跑一遍（与 arena-acc20 里的同名结果核对）
#              attr       sim-v2/calib/attr/<标签>.json          通道延迟归因：0 / 630 / 1500 / 4284 四个断面（attr_list.txt 种子 1、attr_list_seeds.txt 种子 2、attr_list_ext.txt 新接进来的局）
#              fill       sim-v2/calib/fill/<标签>.json          C2 已知点之间几种补法的对照（fill_list.txt）
#              arena-rp   sim-v2/calib/arena-rp1530/<局>.json    闭环，但前 1530 拍其余真人照录像（区分「前期误差滚雪球」和「后期行为没拟合上」）
#   tail       sim-v2/calib/verify-tail.json          verify 里没有一致到最后的局：分歧之前的局面、是哪几个真人不同（tools/verify_tail.mjs）
#   delay      sim-v2/calib/opening-delay.json        不卡的局里「下令拍 → 录像执行拍」间隔的实测分布（对 C1 模型）
#   old        sim-v2/calib/old-vs-new.json           拆掉候选臂之前入库的旧结果（单独起进程逐个跑的）对现在批量重跑的同名结果，逐字段核对（tools/old_vs_new.sh）
#   oldcode    sim-v2/calib/old-code-arena.json       闭环模式：把拆掉候选臂之前的代码取出来重跑两个房间，对现在的结果逐字段核对（tools/old_code_arena.sh）
#   profile    sim-v2/calib/human-profile-check.json  对手模型的参数文件 calib/human-profile.json 从录像从头重算一遍，与入库的那份逐字节比（tools/profile_check.sh）
#   tables     sim-v2/calib/report/                   报告里的全部表和数字（tools/g0_report.mjs）
# 单独的阶段名 verify / g0 / g0x / attr / attrx / seeds / fill / hold / arena / arena-rp 也还能用（只跑那一张清单）。
set -u
cd "$(dirname "$0")/../.." || exit 2
# 重计算闸门（run-heavy.sh）管排队：全机的重计算槽位很挤，等一个槽位常常要好几分钟，所以排队交给闸门自己（最多等 HEAVY_QUEUE 秒），
# timeout 120 加在 node 命令上、从拿到槽位那一刻起算（闸门自己还有 HEAVY_TIMEOUT=110 秒的上限）。
export HEAVY_TIMEOUT=110
export HEAVY_SLOTS=2    # 统筹广播 0006 定的上限；写死在这里，不跟着 run-heavy.sh 里的缺省值走
export HEAVY_QUEUE=900
HEAVY="bash ../../tools/run-heavy.sh timeout 120 node --max-old-space-size=700"
T=sim-v2/tools
LAST=/tmp/r06-g0all-last.txt
stages="${*:-live bands lists core plan tail delay old oldcode profile tables}"
say() { echo "=== $(date -u +%H:%M:%S) $*"; }

# pre_in_slot：排到槽位之后、这一批之前，顺带在同一个槽位里做掉的小件（十几秒以内的单个 node，一个接一个，不并行）。
# 槽位很难排到，单独为一个十几秒的脚本排一次队不划算。现在只有一件：实测延迟分布（delay 阶段的产物）还没有的话先算它。
pre_in_slot() {
  [ -s sim-v2/calib/opening-delay.json ] || printf '%s' "node --max-old-space-size=700 $T/opening_delay.mjs --live-clean sim-v2/calib/live --json sim-v2/calib/opening-delay.json > /tmp/r06-g0all-delay.txt 2>&1; "
}

# batch <g0_batch.mjs 的参数…>：一批接一批，直到清单（或整份计划）跑完。BEFORE 里有命令的话，每批之前先执行一遍。
# 每批是一次槽位：timeout 120 加在槽位里的命令上；这一批的截止时刻从拿到槽位那一刻起算 104 秒（--deadline），
# 所以前面顺带做的小件占掉多少时间，这一批就少跑多少，不会顶到闸门 110 秒的上限。
batch() {
  local i r pre stuck=0 nowait=0
  for i in $(seq 1 900); do
    [ -n "${BEFORE:-}" ] && $BEFORE > /dev/null 2>&1
    pre=$(pre_in_slot)
    r=$(bash ../../tools/run-heavy.sh timeout 120 bash -c "$pre node --max-old-space-size=700 $T/g0_batch.mjs $* --deadline \$((\$(date +%s%3N) + 104000))" 2>&1 | tail -1 | cut -c1-240)
    case "$r" in
      *"[g0_batch]"*"没轮上"*) nowait=$((nowait + 1)) ;;
      *"[g0_batch]"*"还剩 0 个"*) echo "$(date -u +%H:%M:%S) $r（另有 $nowait 次没排到槽位）"; return 0 ;;
      *"[g0_batch]"*"本批跑完 0 个"*) echo "$(date -u +%H:%M:%S) $r"; stuck=$((stuck + 1)) ;;
      *"[g0_batch]"*) echo "$(date -u +%H:%M:%S) $r"; stuck=0 ;;
      *) nowait=$((nowait + 1)) ;;   # 闸门排队到点仍没有空槽位（或这一批被闸门的上限杀掉）：不算没进展，接着排
    esac
    if [ "$stuck" -ge 12 ]; then echo "连着 12 批一个都没跑完，这一阶段停下"; return 1; fi
  done
  echo "排了 900 次还没跑完，这一阶段停下"; return 1
}

# light <node 脚本及参数…>：十几秒以内的单个 node；没排到槽位就重排
light() {
  local i rc
  for i in $(seq 1 90); do
    $HEAVY "$@" > "$LAST" 2>&1; rc=$?
    if [ $rc -ne 124 ] && [ $rc -ne 75 ]; then tail -4 "$LAST" | cut -c1-300; return $rc; fi   # 75 = 排队到点没有空槽位；124 = 被时间上限杀掉
  done
  echo "排了 90 次都没排到槽位：$*"; return 124
}

for st in $stages; do
  case "$st" in
    live)
      say live
      ok=0
      for i in $(seq 1 200); do
        r=$($HEAVY sim-v2/teamgate-v2.mjs --mode live --cohort all 2>&1 | tail -1 | cut -c1-160)
        case "$r" in
          *"还剩 0 局"*) echo "$(date -u +%H:%M:%S) $r"; ok=1; break ;;
          *"[live]"*) echo "$(date -u +%H:%M:%S) $r" ;;
        esac
      done
      [ $ok -eq 1 ] || { echo "live 没跑完，停"; exit 1; } ;;
    bands)
      say bands
      light $T/live_table.mjs || { echo "实盘区间没算出来，停"; exit 1; } ;;
    lists)
      say lists
      timeout 60 python3 $T/g0_lists.py || { echo "清单没生成，停"; exit 1; } ;;
    core)
      say core
      batch verify verify $T/arena_calib_list20.txt
      batch checkpoint g0 $T/g0_list.txt ;;
    plan)
      say plan
      # hold 清单是从 C2 的结果里挑出来的，C2 的结果一边跑一边多：每批之前重新挑一遍
      BEFORE="timeout 60 python3 $T/hold_list.py" batch plan $T/g0_plan.txt ;;
    old)
      say old
      timeout 120 bash $T/old_vs_new.sh | tail -3 ;;
    oldcode)
      say oldcode
      bash $T/old_code_arena.sh | tail -3 ;;
    profile)
      say profile
      bash $T/profile_check.sh | tail -3 ;;
    verify)
      say verify
      batch verify verify $T/verify_list.txt ;;
    tail)
      say tail
      light $T/verify_tail.mjs ;;
    g0)
      say g0
      batch checkpoint g0 $T/g0_list.txt
      batch checkpoint g0 $T/g0_list_more.txt ;;
    g0x)
      say g0x
      batch checkpoint g0 $T/g0_list_ext.txt
      batch checkpoint g0 $T/g0_list_ext_more.txt ;;
    attr)
      say attr
      batch checkpoint attr $T/attr_list.txt ;;
    attrx)
      say attrx
      batch checkpoint attr $T/attr_list_ext.txt ;;
    seeds)
      say seeds
      batch checkpoint attr $T/attr_list_seeds.txt ;;
    fill)
      say fill
      batch checkpoint fill $T/fill_list.txt ;;
    hold)
      say hold
      timeout 60 python3 $T/hold_list.py && batch checkpoint hold $T/hold_list.txt ;;
    arena)
      say arena
      batch arena arena-acc20 $T/arena_calib_list20.txt --len 4300 --channel C2 --squad-fate real ;;
    arena-rp)
      say arena-rp
      batch arena arena-rp1530 $T/arena_calib_list20.txt --len 4300 --channel C2 --squad-fate real --others-replay-until 1530 ;;
    delay)
      say delay
      light $T/opening_delay.mjs --live-clean sim-v2/calib/live --json sim-v2/calib/opening-delay.json ;;
    tables)
      say tables
      light $T/g0_report.mjs ;;
    *) echo "不认识的阶段 $st" ;;
  esac
done
say done
