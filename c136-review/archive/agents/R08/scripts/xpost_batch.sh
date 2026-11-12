#!/usr/bin/env bash
# xpost_batch.sh — 逐批跑 xpost.mjs（真引擎重演到 3000 拍）。一次只起一个 node 进程，每个进程都套 run-heavy.sh（110 秒上限）。
#
#   bash c136-review/agents/R08/scripts/xpost_batch.sh            # 跑 xtruth.json 里「own 对得上、录像到 1800 拍以后」的局；已有输出的跳过
#   bash c136-review/agents/R08/scripts/xpost_batch.sh B029 B034   # 只跑指定的局
#
# 人数 ≥75 的局单独一批，其余两局一批（一局 15~45 秒）。跑完打印 XPOST-BATCH-DONE。
set -u
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
OUT="$A/out/_run/xpost"
mkdir -p "$OUT"
if [ $# -gt 0 ]; then
  LIST=$(for m in "$@"; do echo "$m 0"; done)
else
  LIST=$(PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import json
X = json.load(open('c136-review/agents/R08/out/_cross/xtruth.json', encoding='utf-8'))
for m in X['matches']:
    if m.get('valid') and m.get('endTick', 0) >= 1800 and (m.get('size') or {}).get('own', 0) >= 3:
        print(m['matchId'], m['H'])
EOF
)
fi
batch=()
flush() {
  [ ${#batch[@]} -eq 0 ] && return
  bash c136-review/tools/run-heavy.sh node "$A/scripts/xpost.mjs" "${batch[@]}"
  batch=()
}
while read -r mid h; do
  [ -z "$mid" ] && continue
  [ -s "$OUT/$mid.json" ] && continue
  if [ "$h" -ge 75 ]; then
    flush
    batch=("$mid"); flush
  else
    batch+=("$mid")
    [ ${#batch[@]} -ge 2 ] && flush
  fi
done <<< "$LIST"
flush
echo "XPOST-BATCH-DONE $(ls "$OUT" | wc -l) 个输出"
