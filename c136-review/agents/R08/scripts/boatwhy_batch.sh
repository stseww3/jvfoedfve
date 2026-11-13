#!/usr/bin/env bash
# boatwhy_batch.sh — boatwhy.mjs 的批处理：局单里全部录像各跑一遍（数每艘船发出时航线有几个点）。
# 局单和 fid_batch.sh 用同一份（out/_run/fidabl_list.json）；一次只起一个 node 进程，套 run-heavy.sh（排队等空槽），
# 进程里一份一份串行做；已有输出的跳过。跑完打印 BOATWHY-BATCH-DONE。
# 被时间上限杀掉的录像会留下 .started 标记，重跑以前先删掉。
#
#   bash c136-review/agents/R08/scripts/boatwhy_batch.sh
#   → out/_run/boatwhy/<局>.json；汇总见 boatwhy.py
set -u
# 统筹 0006 号广播：重计算最多 2 个槽
export HEAVY_SLOTS=2
export HEAVY_TIMEOUT=${BOATWHY_TIMEOUT:-900}
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
[ -s "$A/out/_run/fidabl_list.json" ] || PYTHONDONTWRITEBYTECODE=1 python3 "$A/scripts/fidlist.py" >/dev/null

remaining() {
  PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import json, os
A = 'c136-review/agents/R08/out/_run'
out = []
for mid, H, cohort in json.load(open(f'{A}/fidabl_list.json', encoding='utf-8')):
    if os.path.exists(f'{A}/boatwhy/{mid}.json') or os.path.exists(f'{A}/boatwhy/{mid}.started'):
        continue
    out.append(mid)
print(' '.join(out))
EOF
}

stuck=0
last=-1
while :; do
  LIST=$(remaining)
  [ -z "$LIST" ] && break
  n=$(echo "$LIST" | wc -w)
  if [ "$n" -eq "$last" ]; then stuck=$((stuck + 1)); else stuck=0; fi
  [ "$stuck" -ge 3 ] && { echo "【boatwhy_batch】连续 3 批没有进展，停在 $n 局：$LIST"; break; }
  last=$n
  bash c136-review/tools/run-heavy.sh node "$A/scripts/boatwhy.mjs" --budget 240 $LIST
  [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
done
echo "BOATWHY-BATCH-PASS 剩 $(remaining | wc -w) 局"
echo "BOATWHY-BATCH-DONE"
