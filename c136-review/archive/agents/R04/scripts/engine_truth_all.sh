#!/usr/bin/env bash
# 逐局生成真相表（tmp/truth/<局号>/），并把每局的自检行打印出来（留档：重定向追加到 out/engine-truth-check.txt）
# 用法：bash scripts/engine_truth_all.sh [局号…]（默认我的 13 局）
cd "$(dirname "$0")/.." || exit 1
M=("$@"); [ ${#M[@]} -eq 0 ] && M=(A022 A038 A029 A073 A047 A083 A099 A078 A015 A081 A086 A013 B034)
for m in "${M[@]}"; do
  X=""; [ "${m:0:1}" = B ] && X="--me-id"
  HEAVY_QUEUE=90 timeout 115 bash ../../tools/run-heavy.sh node scripts/engine_truth.cjs "$m" $X 2>&1 | grep '^#' | sed -E 's/，用时 [0-9.]+ 秒//'
done
