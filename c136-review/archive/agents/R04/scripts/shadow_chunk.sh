#!/usr/bin/env bash
# shadow_chunk.sh — 重计算槽位紧张时跑整局影子策略：排到槽位以后，按剩下的时间能带几个号就带几个号，
#   结果写进 tmp/shadow/<局号>.chunk-<第一个号>/；所有号都跑到以后用 shadow_merge.py 合成 tmp/shadow/<局号>/。
#   各号的影子策略互不影响（都只读真引擎状态，意图不回写），所以分几次跑和一次跑完逐行相同。
# 用法（重活，套 run-heavy；DEADLINE = 这条命令必须结束的时刻，秒）：
#   DEADLINE=$(( $(date +%s) + 116 )) HEAVY_QUEUE=70 HEAVY_TIMEOUT=110 timeout 119 bash ../../tools/run-heavy.sh bash scripts/shadow_chunk.sh <局号> [--ours id,id,…]
#   python3 scripts/shadow_merge.py <局号>
# 估时：引擎整局重放约 30 秒 / 5600 拍，每个号的策略约 9.5 秒 / 5600 拍（4 核共用、nice 19 时的实测量级）；
#   剩余时间不够带 1 个号就直接退出（退出码 75），不占槽位。
cd "$(dirname "$0")/.." || exit 2
m=$1; shift
now=$(date +%s)
left=$(( ${DEADLINE:-$((now + 100))} - now ))
bots=$(python3 - "$m" "$left" "$@" <<'PY'
import json, sys, os, glob
mid, left = sys.argv[1], int(sys.argv[2])
meta = json.load(open(f'tmp/truth/{mid}/meta.json'))
ours = meta['ours']
allb = [str(p) for p in ours] if mid[0] == 'B' else [v.replace('[APEX] ', '') for v in ours.values()]
done = set()
for d in glob.glob(f'tmp/shadow/{mid}.chunk-*'):
    try:
        done |= {b['bot'] for b in json.load(open(os.path.join(d, 'check.json')))['bots']}
    except Exception:
        pass
pend = [b for b in allb if b not in done]
scale = meta['lastTick'] / 5600.0
E, B = 30.0 * scale, 9.5 * scale
k = int((left - E - 6) // B)
k = max(0, min(k, len(pend)))
print(','.join(pend[:k]) + '|' + str(len(pend)))
PY
)
pend=${bots#*|}; bots=${bots%|*}
if [ "$pend" = 0 ]; then echo "## $m：所有号都跑完了，直接 python3 scripts/shadow_merge.py $m"; exit 0; fi
if [ -z "$bots" ]; then echo "## $m：剩 ${left} 秒，不够带 1 个号（还差 $pend 个号）"; exit 75; fi
first=${bots%%,*}
echo "## $m：剩 ${left} 秒，这一次带 $bots（还差 $pend 个号）"
t0=$(date +%s)
node --max-old-space-size=700 scripts/shadow.mjs "$m" --bots "$bots" --quiet --rows --out "tmp/shadow/$m.chunk-$first" 2>&1 | grep '^#\|不一致\|报错' | cut -c1-330
echo "## 用时 $(( $(date +%s) - t0 )) 秒"
