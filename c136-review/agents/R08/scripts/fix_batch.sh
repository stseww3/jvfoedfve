#!/usr/bin/env bash
# fix_batch.sh — fixprobe.mjs 的批处理：先把走偏的 3 局五条臂都跑了（none / copy / scan / boat / both），
# 再把局单里全部录像跑 none 和 both 两条臂（看补上以后别的局有没有被带坏、两处判断在全部录像里各触发几次）。
# 局单和 fid_batch.sh 用同一份（out/_run/fidabl_list.json）；一次只起一个 node 进程，套 run-heavy.sh（排队等空槽），
# 进程里一份一份串行做；已有输出的跳过。跑完打印 FIX-BATCH-DONE。
#
#   bash c136-review/agents/R08/scripts/fix_batch.sh
#   → out/_run/fixprobe/<局>.<臂>.json；汇总见 fixprobe.py
set -u
# 统筹 0006 号广播：重计算最多 2 个槽
export HEAVY_SLOTS=2
export HEAVY_TIMEOUT=${FIX_TIMEOUT:-900}
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
[ -s "$A/out/_run/fidabl_list.json" ] || PYTHONDONTWRITEBYTECODE=1 python3 "$A/scripts/fidlist.py" >/dev/null

remaining() {
  ARMS="$1" ONLY="$2" PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import json, os
A = 'c136-review/agents/R08/out/_run'
arms = os.environ['ARMS'].split(',')
only = os.environ['ONLY'].split()
out = []
for mid, H, cohort in json.load(open(f'{A}/fidabl_list.json', encoding='utf-8')):
    if only and mid not in only:
        continue
    if all(os.path.exists(f'{A}/fixprobe/{mid}.{arm}.json') or os.path.exists(f'{A}/fixprobe/{mid}.{arm}.started') for arm in arms):
        continue
    out.append(mid)
print(' '.join(out))
EOF
}

run_pass() {
  local ARMS="$1" ONLY="$2" stuck=0 last=-1 LIST n
  while :; do
    LIST=$(remaining "$ARMS" "$ONLY")
    [ -z "$LIST" ] && break
    n=$(echo "$LIST" | wc -w)
    if [ "$n" -eq "$last" ]; then stuck=$((stuck + 1)); else stuck=0; fi
    [ "$stuck" -ge 3 ] && { echo "【fix_batch $ARMS】连续 3 批没有进展，停在 $n 局：$LIST"; break; }
    last=$n
    bash c136-review/tools/run-heavy.sh node "$A/scripts/fixprobe.mjs" --budget 240 --arms "$ARMS" $LIST
    [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
  done
  echo "FIX-BATCH-PASS $ARMS 剩 $(remaining "$ARMS" "$ONLY" | wc -w) 局"
}

run_pass none,copy,scan,boat,both "A053 A057 A001"
run_pass none,both ""
echo "FIX-BATCH-DONE"
