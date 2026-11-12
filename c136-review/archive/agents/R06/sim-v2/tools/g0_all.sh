#!/usr/bin/env bash
# g0_all.sh — 保真度验收报告（reports/SIM-V2-CALIBRATION-G0.md）要用的全部运行，按顺序排成一条队。
# 一次只跑一个 node，每个都套 run-heavy.sh + timeout 120；一个 node 里连着跑一批运行（tools/g0_batch.mjs：排一次重计算槽位跑一批，
# 每批不超过闸门的 110 秒）。已有结果文件的跳过，所以中途断了重新执行就接着跑。120 秒内没排到槽位的，接着重排。
# 只用历史旧策略：每一局跑它当年线上那一版（清单里写的版本和局号不符时，模拟器拒绝）。
#
# 用法（在 c136-review/agents/R06 下；整条队很长，放后台）：
#   bash sim-v2/tools/g0_all.sh [阶段…]     缺省全部：live bands lists g0 arena arena-rp attr delay verify g0x attrx fill hold seeds batchcheck tables
# 各阶段的产物：
#   live       sim-v2/calib/live/<局>.json            全部有录像的局的实盘签名（只放录像）
#   bands      sim-v2/calib/live-bands.json           实盘区间：策略版本 × 卡顿档，各项签名的 P25 / 中位 / P75
#   lists      sim-v2/tools/{verify_list,g0_list_more,g0_list_ext,attr_list,attr_list_ext,attr_list_seeds,fill_list}.txt（tools/g0_lists.py）
#   verify     sim-v2/calib/verify/<局>.json          入库各局：与真引擎重放逐断面核对、clone 自检、日志快照核对
#   g0         sim-v2/calib/g0/<标签>.json            核心 20 局：630 / 1530 两个断面 × C0 / C1 / C2 / C3（g0_list.txt 的 60 次 + g0_list_more.txt 补齐）
#   g0x        sim-v2/calib/g0/<标签>.json            为覆盖 Va / Vc 新接进来的局：同一张表（g0_list_ext.txt）
#   arena      sim-v2/calib/arena-acc20/<局>.json     对手模型标定：核心 20 个真局房间，从第 0 拍起闭环
#   arena-rp   sim-v2/calib/arena-rp1530/<局>.json    同上，但前 1530 拍其余真人照录像（区分「前期误差滚雪球」和「后期行为没拟合上」）
#   attr       sim-v2/calib/attr/<标签>.json          核心 20 局的通道延迟归因：0 / 630 / 1500 / 4284 四个断面（attr_list.txt，种子 1）
#   attrx      sim-v2/calib/attr/<标签>.json          新接进来的局：同上（attr_list_ext.txt）
#   fill       sim-v2/calib/fill/<标签>.json          C2 已知点之间几种补法的对照（fill_list.txt）
#   hold       sim-v2/calib/hold/<标签>.json          C2「最后一个已知点之后」那条假定的对照：追平（缺省）换成保持落后（tools/hold_list.py 挑运行）
#   delay      sim-v2/calib/opening-delay.json        不卡的局里「下令拍 → 录像执行拍」间隔的实测分布（对 C1 模型）
#   seeds      sim-v2/calib/attr/<标签>.json          核心 20 局 attr 的 C1 / C2 换种子 2、3（attr_list_seeds.txt）
#   batchcheck sim-v2/calib/batchcheck/attr-single/   抽 12 次断面运行，单独起进程各跑一遍，与批量跑的结果逐字段核对（tools/same_result.mjs）
#   tables     sim-v2/calib/report/                   报告里的全部表和数字（tools/g0_report.mjs）
set -u
cd "$(dirname "$0")/../.." || exit 2
export HEAVY_TIMEOUT=110
HEAVY="timeout 120 bash ../../tools/run-heavy.sh node"
T=sim-v2/tools
LAST=/tmp/r06-g0all-last.txt
stages="${*:-live bands lists g0 arena arena-rp attr delay verify g0x attrx fill hold seeds batchcheck tables}"
say() { echo "=== $(date -u +%H:%M:%S) $*"; }

# batch <checkpoint|arena|verify> <结果目录名> <清单> [其余开关…]：一批接一批，直到清单跑完
batch() {
  local kind="$1" dir="$2" list="$3"; shift 3
  local i r stuck=0 nowait=0
  for i in $(seq 1 900); do
    r=$($HEAVY $T/g0_batch.mjs "$kind" "$dir" "$list" --deadline $(( $(date +%s%3N) + 112000 )) "$@" 2>&1 | tail -1 | cut -c1-240)
    case "$r" in
      *"[g0_batch]"*"没轮上"*) nowait=$((nowait + 1)) ;;
      *"[g0_batch]"*"还剩 0 个"*) echo "$(date -u +%H:%M:%S) $r（另有 $nowait 次没排到槽位）"; return 0 ;;
      *"[g0_batch]"*"本批跑完 0 个"*) echo "$(date -u +%H:%M:%S) $r"; stuck=$((stuck + 1)) ;;
      *"[g0_batch]"*) echo "$(date -u +%H:%M:%S) $r"; stuck=0 ;;
      *) nowait=$((nowait + 1)) ;;   # 120 秒内没排到槽位：不算没进展，接着排
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
    if [ $rc -ne 124 ]; then tail -4 "$LAST" | cut -c1-300; return $rc; fi
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
    verify)
      say verify
      batch verify verify $T/verify_list.txt ;;
    g0)
      say g0
      batch checkpoint g0 $T/g0_list.txt
      batch checkpoint g0 $T/g0_list_more.txt ;;
    g0x)
      say g0x
      batch checkpoint g0 $T/g0_list_ext.txt ;;
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
    batchcheck)
      say batchcheck
      # attr 清单每隔 31 行抽一个标签（那些结果都是批量跑出来的），单独起进程各跑一遍（tools/g0_run.sh），再与批量跑的同名结果逐字段核对
      grep -v '^#' $T/attr_list.txt | awk 'NF && (NR % 31) == 7' | head -12 > /tmp/r06-batchcheck-attr.txt
      for i in $(seq 1 30); do
        bash $T/g0_run.sh batchcheck/attr-single < /tmp/r06-batchcheck-attr.txt | grep -v '^跳过' | cut -c1-160
        n=$(ls sim-v2/calib/batchcheck/attr-single/*.json 2>/dev/null | wc -l)
        [ "$n" -ge "$(wc -l < /tmp/r06-batchcheck-attr.txt)" ] && break
      done
      light $T/same_result.mjs sim-v2/calib/batchcheck/attr-single sim-v2/calib/attr ;;
    tables)
      say tables
      light $T/g0_report.mjs ;;
    *) echo "不认识的阶段 $st" ;;
  esac
done
say done
