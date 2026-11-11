#!/usr/bin/env bash
# accounts_batch.sh — 广播 0007 的三本账流水线（延迟硬账 / 好地账 / 600–1500 决策拍三层归因），逐局串行：
#   replay_cmds.mjs → match_truth.mjs（缺才跑）→ shadow.mjs --tc 600:1500 --json → atk_fate.mjs --json
#   → delay_account.py → land_account.mjs → tick_attrib.py
# 产物都在 /tmp/c136-r05/work/<局>-{cmds.tsv,shadow.json,shadow.out,atkfate.json,delay.json,delay.txt,land.json,land.txt,attrib.json,attrib.txt}
# 每个 node 步骤都套 run-heavy.sh（全机排队）；单步超时 HT 秒（默认 115；长局放后台时可调大）。
# 已有产物的步骤跳过（--force 全部重跑）。日志追加到 /tmp/c136-r05/work/accounts-batch.log，每步一行（局、步骤、退出码、秒数）。
# 用法（在 c136-review/agents/R05 下）：bash scripts/accounts_batch.sh [--force] A014 A021 …
set -u
cd "$(dirname "$0")/.." || exit 2
W=/tmp/c136-r05/work
LOG=$W/accounts-batch.log
HT=${HT:-115}
FORCE=0
[ "${1:-}" = "--force" ] && { FORCE=1; shift; }
heavy() { HEAVY_TIMEOUT=$HT HEAVY_QUEUE=${HQ:-1800} bash ../../tools/run-heavy.sh "$@"; }
step() { # step <局> <名字> <产物> <标准输出写到哪（- = 丢弃）> <命令…>
  local mid=$1 name=$2 out=$3 so=$4; shift 4
  if [ $FORCE -eq 0 ] && [ -s "$out" ]; then echo "$(date +%T) $mid $name skip" >> "$LOG"; return 0; fi
  local t0 rc; t0=$(date +%s)
  if [ "$so" = "-" ]; then "$@" > /dev/null 2>> "$W/$mid-acc.err"; else "$@" > "$so" 2>> "$W/$mid-acc.err"; fi
  rc=$?
  echo "$(date +%T) $mid $name rc=$rc $(( $(date +%s) - t0 ))s" >> "$LOG"
  return $rc
}
has_tc() { python3 -c "import json,sys; d=json.load(open('$W/$1-shadow.json')); sys.exit(0 if d.get('tcWin') and 'drops' in d else 1)" 2>/dev/null; }
for mid in "$@"; do
  echo "$(date +%T) $mid BEGIN" >> "$LOG"
  step "$mid" cmds "$W/$mid-cmds.tsv" - node scripts/replay_cmds.mjs "$mid" --out "$W/$mid-cmds.tsv" || continue
  step "$mid" truth "/tmp/c136-r05/truth/$mid.json" - heavy node scripts/match_truth.mjs "$mid" || continue
  # 旧的 shadow.json 没有 tc / drops 字段：不算数，重跑
  has_tc "$mid" || rm -f "$W/$mid-shadow.json"
  step "$mid" shadow "$W/$mid-shadow.json" "$W/$mid-shadow.out" heavy node scripts/shadow.mjs "$mid" --quiet --tc 600:1500 --json "$W/$mid-shadow.json" || continue
  step "$mid" atkfate "$W/$mid-atkfate.json" - heavy node scripts/atk_fate.mjs "$mid" --json "$W/$mid-atkfate.json" || continue
  rm -f "$W/$mid-delay.json" "$W/$mid-attrib.json"
  step "$mid" delay "$W/$mid-delay.json" "$W/$mid-delay.txt" timeout 110 python3 scripts/delay_account.py "$mid" --json "$W/$mid-delay.json" --list-batches || continue
  step "$mid" land "$W/$mid-land.json" "$W/$mid-land.txt" heavy node scripts/land_account.mjs "$mid" --json "$W/$mid-land.json" || continue
  step "$mid" attrib "$W/$mid-attrib.json" "$W/$mid-attrib.txt" timeout 110 python3 scripts/tick_attrib.py "$mid" --json "$W/$mid-attrib.json" --by-bot || continue
  echo "$(date +%T) $mid DONE" >> "$LOG"
done
echo "$(date +%T) ALL-DONE $*" >> "$LOG"
