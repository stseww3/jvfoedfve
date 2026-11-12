#!/usr/bin/env bash
# old_vs_new.sh — 拆掉候选臂之前（提交 d498ddc4，旧版工具）入库的运行结果，对现在这版工具重跑出来的同名结果。
# 把 d498ddc4 里的 sim-v2/calib/{verify,g0,arena-acc20} 取到临时目录，用 tools/same_result.mjs --common 逐字段核对
#（只比两边都有的字段：新版多记了几个字段；计时字段除外），结果写 sim-v2/calib/old-vs-new.json（g0_report.mjs 读它）。
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/old_vs_new.sh
set -u
cd "$(dirname "$0")/../.." || exit 2
REF=${1:-d498ddc4}
TMP=$(mktemp -d /tmp/r06-oldcalib.XXXXXX)
top=$(git rev-parse --show-toplevel)
rel=${PWD#"$top"/}
out=sim-v2/calib/old-vs-new.json
echo "{" > "$out.tmp"
echo " \"ref\": \"$REF\"," >> "$out.tmp"
first=1
for d in verify g0 arena-acc20; do
  ( cd "$top" && timeout 100 git archive "$REF" "$rel/sim-v2/calib/$d" 2>/dev/null | tar -x -C "$TMP" ) || true
  old="$TMP/$rel/sim-v2/calib/$d"
  line=$(timeout 100 node sim-v2/tools/same_result.mjs --common "$old" "sim-v2/calib/$d" | tail -1)
  echo "$d：$line"
  n=$(echo "$line" | sed -E 's/^核对 ([0-9]+) 个.*/\1/')
  same=$(echo "$line" | sed -E 's/^核对 [0-9]+ 个同名结果：([0-9]+) 个.*/\1/')
  nold=$(ls "$old" 2>/dev/null | grep -c '\.json$')
  [ $first -eq 1 ] || echo "," >> "$out.tmp"
  first=0
  printf ' "%s": { "old": %s, "both": %s, "same": %s }' "$d" "${nold:-0}" "${n:-0}" "${same:-0}" >> "$out.tmp"
done
printf '\n}\n' >> "$out.tmp"
mv "$out.tmp" "$out"
rm -rf "$TMP"
cat "$out"
