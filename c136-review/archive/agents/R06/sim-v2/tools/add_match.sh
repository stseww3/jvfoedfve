#!/usr/bin/env bash
# add_match.sh — 把一局真局接进 sim-v2（checkpoint 的 C2 实录阶梯、verify 的真引擎指纹、真局的重复单占比都靠它）。
# 用法（在 c136-review/agents/R06 下）：bash sim-v2/tools/add_match.sh <策略版本 c110|c116-vb|c116-va|c116> <局号…> [-- 影子重演到第几拍，缺省 3700]
# 每局依次（每一步都套 timeout，node 都经 run-heavy.sh）：
#   1. scripts/replay_decode.mjs   录像解码          → out/<局>/replay_decoded.json
#   2. scripts/run_truth.sh        真引擎重放两遍     → out/<局>/sim_state.json（全体真人每 30 拍的 领土、兵力；我方席位实际执行的指令）
#   3. scripts/strat_probe.mjs     当年那版策略作影子 → out/<局>/probe.json（每个我方席位逐拍想发的指令）
#   4. tools/make_packs.py + tools/export_traces.py → sim-v2/packs/index.json、truth/<局>.json、traces/<局>.json（入库）
set -u
ver="$1"; shift
to=3700
mids=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then shift; to="$1"; shift; continue; fi
  mids+=("$1"); shift
done
for m in "${mids[@]}"; do
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/replay_decode.mjs "$m" >/dev/null 2>&1 || { echo "$m: 录像解码失败"; continue; }
  bash scripts/run_truth.sh "$m" 2>&1 | tail -1 | cut -c1-200
  HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/strat_probe.mjs "$m" --me squad --strategy "$ver" --json --to "$to" 2>&1 | grep -E "影子重演到|一致到|第一处不同" | cut -c1-200
  timeout 60 python3 sim-v2/tools/make_packs.py "$m" | head -1 | cut -c1-200
  timeout 60 python3 sim-v2/tools/export_traces.py "$m" | cut -c1-240
done
