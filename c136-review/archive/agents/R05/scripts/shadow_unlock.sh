#!/usr/bin/env bash
# shadow_unlock.sh — 对照影子：每拍调用前把 isNoFullSend 清回 false（shadow.mjs --unlock），其余完全相同。
#   产物 /tmp/c136-r05/work/<局>-shadow-unlock.json；与同目录的 <局>-shadow.json（原样影子）逐拍对比用 unlock_diff.py。
#   用途：量「isNoFullSend 被误置位」改变了多少条决策（配额闸拒发 + 5000 拍后的几道门被关掉）。
# 每个 node 步骤套 run-heavy.sh。日志 /tmp/c136-r05/work/shadow-unlock.log。
# 用法（在 c136-review/agents/R05 下）：HT=170 HQ=3000 bash scripts/shadow_unlock.sh A014 A021 …   （B 组局号自动带 overlay）
set -u
cd "$(dirname "$0")/.." || exit 2
W=/tmp/c136-r05/work
LOG=$W/shadow-unlock.log
HT=${HT:-170}
for mid in "$@"; do
  t0=$(date +%s)
  out=$W/$mid-shadow-unlock.json
  if [ -s "$out" ] && [ "${FORCE:-0}" != 1 ]; then echo "$(date +%T) $mid HAVE" >> "$LOG"; continue; fi
  rm -f "$out.tmp"
  if [[ $mid == B* ]]; then export C136_DATA=/tmp/c136-r05/overlay; else unset C136_DATA; fi
  HEAVY_TIMEOUT=$HT HEAVY_QUEUE=${HQ:-3000} bash ../../tools/run-heavy.sh node scripts/shadow.mjs "$mid" --quiet --unlock --json "$out.tmp" > "$W/$mid-shadow-unlock.out" 2>> "$W/$mid-unlock.err"
  rc=$?
  echo "$(date +%T) $mid unlock rc=$rc $(( $(date +%s) - t0 ))s" >> "$LOG"
  if [ $rc -eq 0 ] && [ -s "$out.tmp" ]; then mv "$out.tmp" "$out"; else echo "$(date +%T) $mid SKIP" >> "$LOG"; fi
done
unset C136_DATA
echo "$(date +%T) ALL-DONE $*" >> "$LOG"
