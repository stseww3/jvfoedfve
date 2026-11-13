#!/usr/bin/env bash
# clone0_batch.sh — cloneprobe 的 t=0 断面：出生期刚结束时克隆一份，原对象和拷贝照录像走到 630 拍（只重演这 630 拍）。
# 局单和 fid_batch.sh 用同一份（out/_run/fidabl_list.json）；一次只起一个 node 进程，套 run-heavy.sh（110 秒上限，排队等空槽），
# 每拿到一个槽在时间预算内尽量多跑几局；已有输出的跳过。跑完打印 CLONE0-BATCH-DONE。
#
#   bash c136-review/agents/R08/scripts/clone0_batch.sh
#   → out/_run/cloneprobe/<局>.t0.json；汇总见 cloneprobe.py（和 630 / 1500 / 4284 三个断面并在一张表里）
set -u
# 统筹 0006 号广播：重计算最多 2 个槽
export HEAVY_SLOTS=2
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
    if os.path.exists(f'{A}/cloneprobe/{mid}.t0.json') or os.path.exists(f'{A}/cloneprobe/{mid}.t0.started'):
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
  [ "$stuck" -ge 3 ] && { echo "【clone0_batch】连续 3 批没有进展，停在 $n 局：$LIST"; break; }
  last=$n
  bash c136-review/tools/run-heavy.sh node "$A/scripts/cloneprobe.mjs" --at 0 --until 630 --tag t0 --budget 60 $LIST
  [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
done
echo "CLONE0-BATCH-DONE 剩 $(remaining | wc -w) 局"
