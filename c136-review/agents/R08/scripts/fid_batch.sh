#!/usr/bin/env bash
# fid_batch.sh — 整局重演的几本账，逐批补齐（放后台跑）。一次只起一个 node 进程，每个进程都套 run-heavy.sh
# （110 秒上限，排队等空槽）；每拿到一个槽就在时间预算内尽量多跑几局，已有输出的跳过，没跑完的下一批接着跑。
#
#   bash c136-review/agents/R08/scripts/fid_batch.sh namepool     # squad20 的局：namepool.mjs（顺手写 deathbank）
#   bash c136-review/agents/R08/scripts/fid_batch.sh deathbank    # 其余的局：deathbank.mjs（隔两局取一局，分三轮）
#   bash c136-review/agents/R08/scripts/fid_batch.sh nocache      # engdiff.mjs --fid nocache（只跑触发过猎杀 / 终局提速的局）
#   bash c136-review/agents/R08/scripts/fid_batch.sh noteamend    # engdiff.mjs --fid noteamend（同上）
#   bash c136-review/agents/R08/scripts/fid_batch.sh cloneprobe   # cloneprobe.mjs：断面克隆续跑（先跑触发过猎杀 / 终局提速的局，按第一次事件的拍排；
#                                                                 #   CLONE_EVENTS_ONLY=1 时这一轮只跑有事件的局）
#   bash c136-review/agents/R08/scripts/fid_batch.sh hidstate     # hidstate.mjs：线上引擎 对 模拟器，整局逐拍比看不见的状态（固定的 8 局样本，见下面 HID_SAMPLE）
#
# 注意：这个脚本在跑的时候不要改它（bash 是边读边执行的，改了会从错位的地方接着读）。要改先停批处理。
#
# 局单：out/_run/fidabl_list.json（fidlist.py 从 xtruth.json 生成）。跑完打印 FID-BATCH-DONE。
# namepool / deathbank 两本账另外认 roompairs.py 的结果：out/_run/room_pairs.json 里的局改用同房另一份包更长的录像
# （已有输出用的不是那一份就重跑）；out/_run/fid_extra.json 里的局（自己的录像只有出生期）也跑。
set -u
# 统筹 0006 号广播：重计算最多 2 个槽。显式写死，不跟 tools/run-heavy.sh 里的缺省值走。
export HEAVY_SLOTS=2
ROOT=/agent/repos/c136-r08
A=c136-review/agents/R08
cd "$ROOT" || exit 2
KIND=${1:?用法：fid_batch.sh <namepool|deathbank|nocache|noteamend|cloneprobe|hidstate>}
# hidstate 的样本（一局要线上引擎和模拟器各重放一遍，全量跑不起）：两处已知走偏各带一局做对照（B010：船退回的兵抵了欠账；
# A001：扫描表），其余按编队档、真人数、队数、模式摊开——squad10 的 20 / 69 / 74 人组队局，squad20 的 20 人 5 队两局和 72 人自由混战一局。
export HID_SAMPLE="B010 A001 A027 B042 A051 B027 A098 B011"
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


if kind == 'hidstate':
    for mid in os.environ['HID_SAMPLE'].split():
        if os.path.exists(f'{A}/hidstate/{mid}.json') or os.path.exists(f'{A}/hidstate/{mid}.started'):
            continue
        out.append(mid)
    base, extra = [], []
if kind == 'cloneprobe':
    # 先跑触发过猎杀 / 终局提速的局（按第一次事件的拍从早到晚），再跑其余的（按录像长短从短到长）；
    # 已有输出的跳过；上一轮跑到一半被杀的（留着 .started 记号）也跳过
    rows = []
    for mid, H, cohort in base:
        late = f'{A}/fidabl/{mid}.late.json'
        if not os.path.exists(late):
            continue
        full = json.load(open(late, encoding='utf-8'))['arms'].get('full') or {}
        ev = [x for x in (full.get('firstHunt'), full.get('firstFast')) if x is not None]
        rows.append(((0, min(ev)) if ev else (1, full.get('endTick') or 0), mid))
    for key, mid in sorted(rows):
        if os.path.exists(f'{A}/cloneprobe/{mid}.json') or os.path.exists(f'{A}/cloneprobe/{mid}.started'):
            continue
        if key[0] == 1 and os.environ.get('CLONE_EVENTS_ONLY'):
            continue    # CLONE_EVENTS_ONLY=1：这一轮只跑有事件的局
        out.append(mid)
    base, extra = [], []
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
    hidstate)  HEAVY_TIMEOUT=600 bash c136-review/tools/run-heavy.sh node "$A/scripts/hidstate.mjs" --budget 20 $LIST ;;
    # 一局 40~160 秒，机器挤的时候（4 核、负载 15）超过 240 秒：一个槽只跑一局；上限放宽到 600 秒，免得跑到一半被杀白跑
    cloneprobe) HEAVY_TIMEOUT=600 bash c136-review/tools/run-heavy.sh node "$A/scripts/cloneprobe.mjs" --budget 20 $LIST ;;
    # 一局约 50 秒：超过 35 秒就不再开第二局，免得跑到一半被 110 秒上限杀掉
    *)         bash c136-review/tools/run-heavy.sh node "$A/scripts/engdiff.mjs" --fid "$KIND" --budget 35 $LIST ;;
  esac
  [ $? -eq 75 ] && last=-1     # 排队没等到空槽：不算「没有进展」，接着排
done
echo "FID-BATCH-DONE $KIND 剩 $(remaining | wc -w) 局"
