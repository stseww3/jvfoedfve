#!/usr/bin/env bash
# pipeline.sh — 一局的全套事实产物（R08）。只读 /agent/repos/c136-data/，只写 c136-review/agents/R08/out/<matchId>/。
#
#   bash c136-review/agents/R08/scripts/pipeline.sh <matchId> [录像来源局] [同房另一支编队的局]
#
# 例：pipeline.sh B043 A062 A062   （B043 自带录像不全，用同房 A062 的录像重演，并把 A062 的号当作同房另一支编队）
#     pipeline.sh B034              （用自带录像；没有可用的同房局）
# 步骤：facts（日志事实）→ resim（真引擎全场真值）→ truth → 影子（本编队 / 同房另一支）→ shadowcmp → harvest / top / spawncheck / donrej。
# 每一步单独限时；某一步失败不影响后面的步骤（会打印 FAIL）。
set -u
MID="$1"; RF="${2:-}"; PEER="${3:-}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
S="$ROOT/c136-review/agents/R08/scripts"
O="$ROOT/c136-review/agents/R08/out/$MID"
H="bash $ROOT/c136-review/tools/run-heavy.sh"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$O"
RA=(); [ -n "$RF" ] && RA+=(--replay-from "$RF"); [ -n "$PEER" ] && RA+=(--peer "$PEER")
step() { local name="$1"; shift; if "$@" > "$O/.step.log" 2>&1; then echo "OK   $name: $(tail -1 "$O/.step.log" | cut -c1-200)"; else echo "FAIL $name: $(tail -2 "$O/.step.log" | tr '\n' ' ' | cut -c1-300)"; fi; }
cd "$ROOT"
step facts timeout 110 python3 "$S/facts.py" "$MID" --quiet
step resim $H node "$S/resim_r08.mjs" "$MID" "${RA[@]}" --quiet
if [ ! -s "$O/resim.json" ]; then echo "没有 resim.json（录像不可用），到此为止"; rm -f "$O/.step.log"; exit 0; fi
step truth timeout 110 python3 "$S/truth.py" "$MID"
step shadow $H node "$S/shadow.mjs" "$MID" "${RA[@]}" --quiet
step shadowcmp timeout 110 python3 "$S/shadowcmp.py" "$MID" --quiet
if [ -n "$PEER" ]; then
  step shadow-peer $H node "$S/shadow.mjs" "$MID" "${RA[@]}" --side peer --quiet
  step shadowcmp-peer timeout 110 python3 "$S/shadowcmp.py" "$MID" --side peer --quiet
fi
step harvest bash -c "timeout 110 python3 '$S/harvest.py' '$MID' > '$O/harvest.txt'"
step top bash -c "timeout 110 python3 '$S/top.py' '$MID' > '$O/top.txt'"
step spawncheck timeout 110 python3 "$S/spawncheck.py" "$MID" --quiet
step donrej timeout 115 python3 "$S/donrej.py" "$MID" "${RA[@]}"
rm -f "$O/.step.log"
ls -la "$O" | awk '{print $5, $9}' | tr '\n' ' '; echo
