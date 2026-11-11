#!/usr/bin/env bash
# shadow_refresh.sh — 用带「发送函数出口计数」的新版 shadow.mjs 把一批局的影子 JSON 重跑一遍，然后重算依赖它的三张表：
#   shadow.mjs <局> --quiet --tc 600:1500 --json   （ps/ss/nfs 字段、sendExits、baseSendExits、nfsAt）
#   → delay_account.py（延迟硬账；影子决策不变时结果应与旧表逐项相同）
#   → tick_attrib.py --by-bot --exits（三层归因 + 「有目标没发」按源码行拆分）
#   → quota_guard.py（isNoFullSend 置位拍、Policy.send 拒发次数）
# 新的影子 JSON 先写到 <局>-shadow.new.json，跑成功才替换旧文件；旧的延迟表留一份 <局>-delay.prev.json 供对比。
# 每个 node 步骤都套 run-heavy.sh（全机排队）。日志：/tmp/c136-r05/work/shadow-refresh.log（每步一行：局、步骤、退出码、秒数）。
# 用法（在 c136-review/agents/R05 下）：HT=170 HQ=3000 bash scripts/shadow_refresh.sh A014 A021 …
set -u
cd "$(dirname "$0")/.." || exit 2
W=/tmp/c136-r05/work
LOG=$W/shadow-refresh.log
HT=${HT:-170}
for mid in "$@"; do
  t0=$(date +%s)
  rm -f "$W/$mid-shadow.new.json"
  HEAVY_TIMEOUT=$HT HEAVY_QUEUE=${HQ:-3000} bash ../../tools/run-heavy.sh node scripts/shadow.mjs "$mid" --quiet --tc 600:1500 --json "$W/$mid-shadow.new.json" > "$W/$mid-shadow.out2" 2>> "$W/$mid-refresh.err"
  rc=$?
  echo "$(date +%T) $mid shadow rc=$rc $(( $(date +%s) - t0 ))s" >> "$LOG"
  if [ $rc -ne 0 ] || [ ! -s "$W/$mid-shadow.new.json" ]; then echo "$(date +%T) $mid SKIP" >> "$LOG"; continue; fi
  mv "$W/$mid-shadow.new.json" "$W/$mid-shadow.json"
  cp -f "$W/$mid-delay.json" "$W/$mid-delay.prev.json" 2>/dev/null
  timeout 110 python3 scripts/delay_account.py "$mid" --json "$W/$mid-delay.json" --list-batches > "$W/$mid-delay.txt" 2>> "$W/$mid-refresh.err"
  echo "$(date +%T) $mid delay rc=$?" >> "$LOG"
  timeout 110 python3 scripts/tick_attrib.py "$mid" --json "$W/$mid-attrib.json" --by-bot --exits > "$W/$mid-attrib.txt" 2>> "$W/$mid-refresh.err"
  echo "$(date +%T) $mid attrib rc=$?" >> "$LOG"
  timeout 110 python3 scripts/quota_guard.py "$mid" --json "$W/$mid-quota.json" --by-bot > "$W/$mid-quota.txt" 2>> "$W/$mid-refresh.err"
  echo "$(date +%T) $mid quota rc=$?" >> "$LOG"
  echo "$(date +%T) $mid DONE" >> "$LOG"
done
echo "$(date +%T) ALL-DONE $*" >> "$LOG"
