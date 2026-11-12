#!/usr/bin/env bash
# fid_batch.sh — 整局重演的几本账，逐批补齐（放后台跑）。一次只起一个 node 进程，每个进程都套 run-heavy.sh
# （110 秒上限，排队等空槽）；每拿到一个槽就在时间预算内尽量多跑几局，已有输出的跳过，没跑完的下一批接着跑。
#
#   bash c136-review/agents/R08/scripts/fid_batch.sh namepool     # squad20 的局：namepool.mjs（顺手写 deathbank）
#   bash c136-review/agents/R08/scripts/fid_batch.sh deathbank    # 其余的局：deathbank.mjs（隔两局取一局，分三轮）
#   bash c136-review/agents/R08/scripts/fid_batch.sh nocache      # engdiff.mjs --fid nocache（只跑触发过猎杀 / 终局提速的局）
#   bash c136-review/agents/R08/scripts/fid_batch.sh noteamend    # engdiff.mjs --fid noteamend（同上）
#
# 局单：out/_run/fidabl_list.json（fidlist.py 从 xtruth.json 生成）。跑完打印 FID-BATCH-DONE。
# namepool / deathbank 两本账另外认 roompairs.py 的结果：out/_run/room_pairs.json 里的局改用同房另一份包更长的录像
# （已有输出用的不是那一份就重跑）；out/_run/fid_extra.json 里的局（自己的录像只有出生期）也跑。
set -u
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
KIND=${1:?用法：fid_batch.sh <namepool|deathbank|nocache|noteamend>}
[ -s "$A/out/_run/fidabl_list.json" ] || PYTHONDONTWRITEBYTECODE=1 python3 "$A/scripts/fidlist.py" >/dev/null
[ -s "$A/out/_run/room_pairs.json" ] || PYTHONDONTWRITEBYTECODE=1 timeout 120 python3 "$A/scripts/roompairs.py" --quiet

remaining() {
  KIND="$KIND" PYTHONDONTWRITEBYTECODE=1 python3 - <<'EOF'
import json, os
A = 'c136-review/agents/R08/out/_run'
kind = os.environ['KIND']
out = []
base = [tuple(r) for r in json.load(open(f'{A}/fidabl_list.json', encoding='utf-8'))]
pairs, extra = {}, []
if kind in ('namepool', 'deathbank'):
    try:
        pairs = json.load(open(f'{A}/room_pairs.json', encoding='utf-8'))
        extra = [tuple(r[:3]) for r in json.load(open(f'{A}/fid_extra.json', encoding='utf-8'))]
    except Exception:
        pass


def fresh(fp, mid, need=None):
    if not os.path.exists(fp):
        return False
    R = json.load(open(fp, encoding='utf-8'))
    return (need is None or need in R) and (R.get('replayFrom') or None) == pairs.get(mid)


for mid, H, cohort in base + extra:
    if kind == 'namepool':
        if cohort != 'squad20':
            continue
        if fresh(f'{A}/namepool/{mid}.json', mid, 'deaths'):
            continue
    elif kind == 'deathbank':
        if fresh(f'{A}/deathbank/{mid}.json', mid):
            continue
    else:
        late = f'{A}/fidabl/{mid}.late.json'
        if not os.path.exists(late):
            continue
        full = json.load(open(late, encoding='utf-8'))['arms'].get('full') or {}
        if full.get('firstHunt') is None and full.get('firstFast') is None:
            continue
        if os.path.exists(f'{A}/engdiff/{mid}.{kind}.json'):
            continue
    out.append(mid)
if kind == 'deathbank':
    # 局单按真人数排过序；隔两局取一局先跑，三轮跑完——中途停下来时已有的局在房间大小上是均匀的
    lst = [m for m, _, c in json.load(open(f'{A}/fidabl_list.json', encoding='utf-8')) if c != 'squad20']
    rank = {m: (i % 3, i) for i, m in enumerate(lst)}
    out.sort(key=lambda m: rank.get(m, (9, 0)))
print(' '.join(out))
EOF
}

stuck=0
last=-1
while :; do
  LIST=$(remaining)
  [ -z "$LIST" ] && break
  n=$(echo "$LIST" | wc -w)
  if [ "$n" -eq "$last" ]; then stuck=$((stuck + 1)); else stuck=0; fi
  [ "$stuck" -ge 3 ] && { echo "【fid_batch】连续 3 批没有进展，停在 $n 局：$LIST"; break; }
  last=$n
  case "$KIND" in
    namepool)  bash c136-review/tools/run-heavy.sh node "$A/scripts/namepool.mjs" --budget 70 $LIST ;;
    deathbank) bash c136-review/tools/run-heavy.sh node "$A/scripts/deathbank.mjs" --budget 70 $LIST ;;
    *)         bash c136-review/tools/run-heavy.sh node "$A/scripts/engdiff.mjs" --fid "$KIND" --budget 55 $LIST ;;
  esac
  [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
done
echo "FID-BATCH-DONE $KIND 剩 $(remaining | wc -w) 局"
