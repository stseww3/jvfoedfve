#!/usr/bin/env bash
# hub_resim_check.sh — 用 hub 放在 c136-data/src/tools/ 的纯 JS 重放脚本 resim.mjs（带组队配色 / 分队移植的那一版）
# 把我复盘过的局各重放一遍，记下它和日志快照（traj.csv）的核对结果。回答的问题：纯 JS 模拟器能不能逐拍复现线上。
# 用法：bash scripts/hub_resim_check.sh <局号> [--until T]      （一次一局，过 run-heavy.sh；结果追加到 out/hub-resim-check.txt）
#   resim.mjs 原样拷到 tmp/hubsim/tools/（不改一个字），它的输出 JSON 落在 tmp/hubsim/out/cache/，不进仓库。
cd "$(dirname "$0")/.." || exit 1
m="$1"; shift
mkdir -p tmp/hubsim/tools
cmp -s /agent/repos/c136-data/src/tools/resim.mjs tmp/hubsim/tools/resim.mjs || cp /agent/repos/c136-data/src/tools/resim.mjs tmp/hubsim/tools/resim.mjs
out=$(HEAVY_QUEUE=100 HEAVY_TIMEOUT=110 timeout 118 bash ../../tools/run-heavy.sh node tmp/hubsim/tools/resim.mjs "$m" --quiet "$@" 2>&1)
rc=$?
{
  echo "# $m $* （退出码 $rc）"
  echo "$out" | grep -E "^$m:|traj 核对|offset scan" | cut -c1-400
} | tee -a out/hub-resim-check.txt
