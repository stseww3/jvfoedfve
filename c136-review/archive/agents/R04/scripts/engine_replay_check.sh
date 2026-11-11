#!/usr/bin/env bash
# 逐局用线上客户端原文重放，并与 [HL-TICK] 快照对账；结果写 out/engine-replay-check.txt
# 用法：bash scripts/engine_replay_check.sh [局号…]（默认我的 13 局）；每局单独过 run-heavy.sh
cd "$(dirname "$0")/.." || exit 1
M=("$@"); [ ${#M[@]} -eq 0 ] && M=(A022 A038 A029 A073 A047 A083 A099 A078 A015 A081 A086 A013 B034)
for m in "${M[@]}"; do
  HEAVY_QUEUE=90 timeout 115 bash ../../tools/run-heavy.sh node scripts/engine_replay.cjs "$m" --quiet 2>&1 | grep '^#' | grep -v '用时'
done
