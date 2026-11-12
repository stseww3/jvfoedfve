#!/usr/bin/env bash
# 105b_fill_late.sh — R07：把 105_human_fill.mjs --late 跑完 11 局（1500 拍以后的站位基准用）。
# 每次都套重计算闸、限时 120 秒；排不到槽位就重新排（最多 CP_FILL_TRIES 次，默认 400）；已有输出的局跳过。
# 用法：bash 105b_fill_late.sh        （和 102_cp_batch.sh 不要同时跑：全机重计算槽位一次只占一个）
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
DIR="$HERE/../out/_cache/fill_late"
LOG="$DIR/batch.log"
GAMES="A007 A033 A039 A053 A061 A062 A070 A079 A082 A089 A091"
mkdir -p "$DIR"
n=0
todo=""
while [ "$n" -lt "${CP_FILL_TRIES:-400}" ]; do
  todo=""
  for g in $GAMES; do [ -s "$DIR/$g.json" ] || todo="$todo $g"; done
  [ -z "$todo" ] && break
  # shellcheck disable=SC2086
  out="$(cd "$ROOT" && HEAVY_QUEUE=12 CP_DEADLINE_MS=$(( $(date +%s%3N) + 114000 )) timeout 120 bash c136-review/tools/run-heavy.sh node "$HERE/105_human_fill.mjs" --late $todo 2>&1)"
  rc=$?
  n=$((n+1))
  [ "$rc" -eq 75 ] && continue
  echo "$(date +%H:%M:%S) rc=$rc $(printf '%s' "$out" | tr '\n' ';' | cut -c1-700)" >> "$LOG"
done
echo "$(date +%H:%M:%S) DONE 还缺：[${todo# }]（试了 $n 次）" >> "$LOG"
