#!/usr/bin/env bash
# old_code_arena.sh — 拆掉候选臂之前（提交 d498ddc4）的模拟器代码原样取到临时目录，跑同样的闭环运行，
# 与现在的代码跑出来的同名结果（sim-v2/calib/arena-acc20/）逐字段核对（只比两边都有的字段；计时字段除外）。
# 为什么要它：verify 和断面两种模式，旧提交里入库的结果就是旧代码跑的，直接比结果文件就行（tools/old_vs_new.sh）；
# 闭环模式不行——旧提交里入库的那 20 个闭环结果不是那次提交的代码跑出来的（old_vs_new.sh 的 arenaOld 一项），
# 所以这里把旧代码拿出来重跑。两边相同 = 拆候选臂没有改动闭环模式下历史策略这条臂的任何数字；
# 旧代码是单独起进程一个一个跑的，现在的结果是一个进程里连着跑一批的，所以同时也核对了两种跑法。
# 只取旧提交里的 lib/、teamgate-v2.mjs 和它当时的输入（packs/、traces/、truth/、calib/human-profile.json）；地图用现在的（没有入库）。
# 旧代码只挂历史策略那一条臂（--arm baseline），和当时 tools/arena_calib.sh 的调用相同。
# 结果：sim-v2/calib/old-code-arena.json = { ref, rooms: [局号…], both: 两边都有的个数, same: 逐字段相同的个数,
#        leaves: 一共比了多少个数, onlyOld / onlyNew: 只有旧结果 / 只有新结果才有的字段（不比） }
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/old_code_arena.sh [局号…]      缺省 A018 A027
set -u
cd "$(dirname "$0")/../.." || exit 2
REF=d498ddc4
rooms="${*:-A018 A027}"
TMP=${OLD_CODE_DIR:-/tmp/r06-oldcode}
top=$(git rev-parse --show-toplevel)
rel=${PWD#"$top"/}
old="$TMP/$rel/sim-v2"
if [ ! -f "$old/teamgate-v2.mjs" ]; then
  mkdir -p "$TMP"
  ( cd "$top" && timeout 100 git archive "$REF" "$rel/sim-v2/lib" "$rel/sim-v2/teamgate-v2.mjs" "$rel/sim-v2/packs" "$rel/sim-v2/traces" "$rel/sim-v2/truth" "$rel/sim-v2/calib/human-profile.json" | tar -x -C "$TMP" ) || { echo "取不出 $REF 的代码"; exit 1; }
  ln -sfn "$PWD/sim-v2/maps" "$old/maps"
fi
mkdir -p "$TMP/out"
export HEAVY_TIMEOUT=110
export HEAVY_QUEUE=900
strat_of() { grep -h "^$1 " sim-v2/tools/arena_calib_list20.txt | awk '{print $2}'; }
for i in $(seq 1 60); do
  todo=""
  for m in $rooms; do [ -s "$TMP/out/$m.json" ] || todo="$todo $m"; done
  [ -z "$todo" ] && break
  cmd=""
  for m in $todo; do
    cmd="$cmd node --max-old-space-size=700 '$old/teamgate-v2.mjs' --mode arena --room $m --baseline $(strat_of "$m") --arm baseline --channel C2 --len 4300 --squad-fate real --quiet --out '$TMP/out/$m.json.part' && mv '$TMP/out/$m.json.part' '$TMP/out/$m.json';"
  done
  bash ../../tools/run-heavy.sh timeout 120 bash -c "$cmd" > "$TMP/last.txt" 2>&1
  tail -2 "$TMP/last.txt" | cut -c1-200
done
timeout 100 node sim-v2/tools/same_result.mjs --common "$TMP/out" sim-v2/calib/arena-acc20 | cut -c1-300 | tail -5
j=$(timeout 100 node sim-v2/tools/same_result.mjs --common --json "$TMP/out" sim-v2/calib/arena-acc20 | tail -1)
list=$(for m in $rooms; do printf '"%s",' "$m"; done | sed 's/,$//')
J="$j" REF="$REF" LIST="[$list]" timeout 60 python3 - <<'PY' > sim-v2/calib/old-code-arena.json
import json, os
j = json.loads(os.environ['J'])
out = {"ref": os.environ['REF'], "rooms": json.loads(os.environ['LIST']), "both": j["n"], "same": j["same"],
       "leaves": j["leaves"], "onlyOld": j["onlyA"], "onlyNew": j["onlyB"]}
print(json.dumps(out, ensure_ascii=False))
PY
cat sim-v2/calib/old-code-arena.json
