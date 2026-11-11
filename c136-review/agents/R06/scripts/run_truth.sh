#!/usr/bin/env bash
# run_truth.sh <局号...> — 对每局依次：sim_prep.py（生成 out/<id>/sim_in.json）→ eng_replay.cjs（真引擎重放，写 out/<id>/sim_state.json）
# 例：bash c136-review/agents/R06/scripts/run_truth.sh B039 B038 B041
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
for m in "$@"; do
  # 两遍：第一遍重放得到「日志行 → 玩家号」的指纹；第二遍用它把捐款日志归到正确的号，再逐条做配额探针
  rm -f "$HERE/../out/$m/sim_state.json"
  timeout 60 python3 "$HERE/sim_prep.py" "$m" >/dev/null || { echo "$m: sim_prep 失败（没有录像头？）"; continue; }
  timeout 118 bash "$ROOT/c136-review/tools/run-heavy.sh" node "$HERE/eng_replay.cjs" "$m" >/dev/null 2>&1
  timeout 60 python3 "$HERE/sim_prep.py" "$m" | tail -1
  timeout 118 bash "$ROOT/c136-review/tools/run-heavy.sh" node "$HERE/eng_replay.cjs" "$m" 2>&1 | tail -4 | cut -c1-260
done
