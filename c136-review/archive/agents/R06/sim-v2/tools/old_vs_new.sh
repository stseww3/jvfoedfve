#!/usr/bin/env bash
# old_vs_new.sh — 拆掉候选臂之前（提交 d498ddc4，旧版工具）入库的运行结果，对现在这版工具重跑出来的同名结果。
# 把 d498ddc4 里的 sim-v2/calib/{verify,g0,arena-acc20} 取到临时目录，用 tools/same_result.mjs --common 逐字段核对
#（只比两边都有的字段：新版多记了几个字段；计时字段除外），结果写 sim-v2/calib/old-vs-new.json（g0_report.mjs 读它）。
# 另外查一件事：旧的闭环结果（arena-acc20）是不是那次提交里的代码跑出来的（见下面 arenaOld）。
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
# 旧的闭环结果是不是用同一次提交里的代码跑出来的：那次提交的 lib/arena.mjs 在每个断面都写 othersBal 这个字段（对手的余额），
# 数一数旧结果文件里有几个带这个字段。一个都没有 = 那批结果是更早的代码跑的，提交时没有重跑。
codeWrites=$( (cd "$top" && timeout 60 git show "$REF:$rel/sim-v2/lib/arena.mjs" 2>/dev/null) | grep -c 'othersBal:' )
oldFiles=$(ls "$TMP/$rel/sim-v2/calib/arena-acc20" 2>/dev/null | grep -c '\.json$')
withField=$(grep -l '"othersBal"' "$TMP/$rel/sim-v2/calib/arena-acc20"/*.json 2>/dev/null | wc -l)
newWith=$(grep -l '"othersBal"' sim-v2/calib/arena-acc20/*.json 2>/dev/null | wc -l)
newFiles=$(ls sim-v2/calib/arena-acc20 2>/dev/null | grep -c '\.json$')
printf ',\n "arenaOld": { "field": "othersBal", "codeWritesIt": %s, "oldFiles": %s, "oldFilesWithIt": %s, "newFiles": %s, "newFilesWithIt": %s }' \
  "$([ "${codeWrites:-0}" -gt 0 ] && echo true || echo false)" "${oldFiles:-0}" "${withField:-0}" "${newFiles:-0}" "${newWith:-0}" >> "$out.tmp"
printf '\n}\n' >> "$out.tmp"
mv "$out.tmp" "$out"
rm -rf "$TMP"
cat "$out"
