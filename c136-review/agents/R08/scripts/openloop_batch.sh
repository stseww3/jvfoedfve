#!/usr/bin/env bash
# openloop_batch.sh — openloop.mjs 的批处理：先带拷贝跑一遍（四个断面 × 三条臂），再不放拷贝跑一遍（只算参照重演的校验和，核对用）。
# 局单和 fid_batch.sh 用同一份（out/_run/fidabl_list.json）；一次只起一个 node 进程，套 run-heavy.sh（排队等空槽），
# 进程里一局一局串行做，每拿到一个槽在时间预算内尽量多做几局；已有输出的跳过。跑完打印 OPENLOOP-BATCH-DONE。
#
#   bash c136-review/agents/R08/scripts/openloop_batch.sh
#   → out/_run/openloop/<局>.json、<局>.plain.json；汇总见 openloop.py
set -u
# 统筹 0006 号广播：重计算最多 2 个槽
export HEAVY_SLOTS=2
export HEAVY_TIMEOUT=300
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
[ -s "$A/out/_run/fidabl_list.json" ] || PYTHONDONTWRITEBYTECODE=1 python3 "$A/scripts/fidlist.py" >/dev/null

remaining() {
  SUF="$1" PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import json, os
A = 'c136-review/agents/R08/out/_run'
suf = os.environ['SUF']
out = []
for mid, H, cohort in json.load(open(f'{A}/fidabl_list.json', encoding='utf-8')):
    if os.path.exists(f'{A}/openloop/{mid}{suf}.json') or os.path.exists(f'{A}/openloop/{mid}{suf}.started'):
        continue
    out.append(mid)
print(' '.join(out))
EOF
}

for PASS in full plain; do
  if [ "$PASS" = plain ]; then SUF=.plain; FLAG=--plain; else SUF=; FLAG=; fi
  stuck=0
  last=-1
  while :; do
    LIST=$(remaining "$SUF")
    [ -z "$LIST" ] && break
    n=$(echo "$LIST" | wc -w)
    if [ "$n" -eq "$last" ]; then stuck=$((stuck + 1)); else stuck=0; fi
    [ "$stuck" -ge 3 ] && { echo "【openloop_batch $PASS】连续 3 批没有进展，停在 $n 局：$LIST"; break; }
    last=$n
    bash c136-review/tools/run-heavy.sh node "$A/scripts/openloop.mjs" --budget 150 $FLAG $LIST
    [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
  done
  echo "OPENLOOP-BATCH-PASS $PASS 剩 $(remaining "$SUF" | wc -w) 局"
done
echo "OPENLOOP-BATCH-DONE"
