#!/usr/bin/env bash
# heavy-chain.sh — 一局的重计算步骤串成一条链，逐步排队过 run-heavy.sh 的闸（同一时刻只占一个槽）。
#
#   bash scripts/heavy-chain.sh <mid> <步骤…>
#   步骤：shadow（要 MAPS 环境变量，逗号分隔的地图拍）  dossier（轻，跟在 shadow 后面，同样用 MAPS）
#         freeze  donwhy  land
#   例：MAPS=630,1530,3060 bash scripts/heavy-chain.sh A090 shadow dossier freeze donwhy land
#   SHADOW_ARGS：附加给 shadow.mjs 的参数（例：SHADOW_ARGS="--minlat 5"，A046 用）
#
# 机器忙的时候 run-heavy 的排队可能要等好几分钟。外面再套 timeout 120 的话，超时只杀掉闸本身，
# 里面的 node 变成没人管的孤儿、槽位锁也提前放掉。所以这里不套外层 timeout：单步运行时间由闸自己的
# HEAVY_TIMEOUT（110 秒）卡住，排队时间由 HEAVY_QUEUE 卡住。
# 进度写 /tmp/r03-chain-<mid>.log，最后一行 CHAIN-DONE；每步的标准输出/错误在 /tmp/r03-chain-<mid>-<步骤>.{out,err}。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
mid=${1:?用法：heavy-chain.sh <mid> <步骤…>}
shift
log=/tmp/r03-chain-$mid.log
echo "CHAIN-START $mid $* $(date +%s)" > "$log"
GATE="$HERE/../../../tools/run-heavy.sh"

heavy() { # heavy <名字> <命令…>；最多试 3 次（排队超时 75 或运行超时 124 时重来）
  local name=$1; shift
  local out=/tmp/r03-chain-$mid-$name.out err=/tmp/r03-chain-$mid-$name.err
  local attempt rc s
  for attempt in 1 2 3; do
    s=$(date +%s)
    HEAVY_QUEUE=${CHAIN_QUEUE:-900} HEAVY_TIMEOUT=${CHAIN_TIMEOUT:-110} bash "$GATE" "$@" > "$out" 2> "$err"
    rc=$?
    echo "$name attempt=$attempt rc=$rc secs=$(( $(date +%s) - s ))" >> "$log"
    [ $rc -eq 0 ] && return 0
  done
  return 1
}

for step in "$@"; do
  case $step in
    shadow)
      heavy shadow node scripts/shadow.mjs "$mid" --quiet --maps "${MAPS:?shadow 要 MAPS}" ${SHADOW_ARGS:-} || { echo "CHAIN-FAIL shadow" >> "$log"; exit 1; } ;;
    dossier)
      timeout 120 python3 scripts/dossier.py "$mid" --quiet --map "${MAPS:?dossier 要 MAPS}" > /tmp/r03-chain-$mid-dossier.out 2>&1
      echo "dossier rc=$?" >> "$log"
      timeout 120 python3 scripts/shadow-digest.py "$mid" --quiet > /tmp/r03-chain-$mid-digest.out 2>&1
      echo "digest rc=$?" >> "$log"
      timeout 120 python3 scripts/delay-ledger.py "$mid" --quiet > /tmp/r03-chain-$mid-delay.out 2>&1
      echo "delay rc=$?" >> "$log" ;;
    freeze)
      heavy freeze node scripts/freeze-scan.mjs "$mid" && cp /tmp/r03-chain-$mid-freeze.out "out/dossier/$mid-freeze.txt" ;;
    donwhy)
      heavy donwhy node scripts/donate-why.mjs "$mid" && cp /tmp/r03-chain-$mid-donwhy.out "out/dossier/$mid-donwhy.txt" ;;
    land)
      heavy land node scripts/land-ledger.mjs "$mid" --quiet ;;
    *) echo "未知步骤 $step" >> "$log" ;;
  esac
done
echo "CHAIN-DONE $(date +%s)" >> "$log"
