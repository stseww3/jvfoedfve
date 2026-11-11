#!/usr/bin/env bash
# shadow_all.sh — 对若干局跑整局影子策略（全部我方号），产出 tmp/shadow/<局号>/{intents.tsv,logs.txt,check.json}，
# 并把保真度自检行打印出来（重定向到 out/shadow-check.txt 留档）。
# 用法：bash scripts/shadow_all.sh A022 A038 ...   （先要有 tmp/truth/<局号>/meta.json：bash scripts/engine_truth_all.sh <局号>）
# 一局 10~30 秒；一次命令别超过 3 局（本地命令有 120 秒上限）。
cd "$(dirname "$0")/.." || exit 2
for m in "$@"; do
  bots=$(python3 - "$m" <<'PY'
import json, sys
m = json.load(open(f'tmp/truth/{sys.argv[1]}/meta.json'))
ours = m['ours']
# A 组按名字（去掉 [APEX] 前缀），B 组名字会轮换，直接用引擎编号
if sys.argv[1][0] == 'B':
    print(','.join(str(p) for p in ours))
else:
    print(','.join(n.replace('[APEX] ', '') for n in ours.values()))
PY
)
  echo "## $m"
  node scripts/shadow.mjs "$m" --bots "$bots" --quiet --rows --out "tmp/shadow/$m" 2>&1 | grep '^#\|不一致\|报错' | cut -c1-330
done
