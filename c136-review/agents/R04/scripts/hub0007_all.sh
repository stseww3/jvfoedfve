#!/usr/bin/env bash
# hub0007_all.sh — 一局的「延迟账 + 好地账 + 三层归因」一次跑完，结果写进 out/<局号>/{good_land,latency_ledger,capture_attrib,slow_ticks,delay_vs_rate}.txt。
# 用法（重活，套 run-heavy）：HEAVY_QUEUE=100 HEAVY_TIMEOUT=110 timeout 118 bash ../../tools/run-heavy.sh bash scripts/hub0007_all.sh <局号> [--ours id,id,…]
#   先要有 tmp/truth/<局号>/（engine_truth_all.sh）和 tmp/shadow/<局号>/（shadow_all.sh，rows.tsv 要带 bind / gateAI 列）。
cd "$(dirname "$0")/.." || exit 2
m=$1; shift
mkdir -p "out/$m"
node --max-old-space-size=700 scripts/good_land.mjs "$m" --at 630,1080,1500,1800,2250,3000 "$@" > "out/$m/good_land.txt" || { echo "good_land 失败"; exit 1; }
python3 scripts/latency_ledger.py "$m" "$@" > "out/$m/latency_ledger.txt" || { echo "latency_ledger 失败"; exit 1; }
python3 scripts/capture_attrib.py "$m" > "out/$m/capture_attrib.txt" || { echo "capture_attrib 失败"; exit 1; }
python3 scripts/slow_ticks.py "$m" > "out/$m/slow_ticks.txt" || { echo "slow_ticks 失败"; exit 1; }
python3 scripts/delay_vs_rate.py "$m" --fine > "out/$m/delay_vs_rate.txt" || { echo "delay_vs_rate 失败"; exit 1; }
echo "## $m"; head -4 "out/$m/good_land.txt" | cut -c1-300; cat "out/$m/capture_attrib.txt" | cut -c1-700
