#!/usr/bin/env python3
"""donprobe_tally.py — 汇总 shadow.mjs --don-probe 的输出：弃子线（isDoomedPocket，Vb L4455-4456）按两个分支分别计数。

第一分支：被真人打的量 > 1.65×存兵。
第二分支：t≥4500 且 地 < 22%×编队最大号 且 被真人打的量 > 0.45×存兵。
探针行里写的是「实际让判定成立的那个分支」（第一分支成立时不再看第二分支）；本脚本另外用探针行里的
地、兵、被打量和表头里的「编队最大号」重算第二分支的条件，给出「第二分支单独也成立」的次数。

用法：
  node scripts/shadow.mjs <局> --cold --quiet --t0 1495 --t1 <末拍> --don-probe 1500,1505,... > probe.txt
  python3 scripts/donprobe_tally.py probe.txt [--match <局>]   # --match 时读 /tmp/c136-r05/truth/<局>.json 取阵亡拍
输出：（候选×拍）与（捐出方×候选×拍）两种口径的计数、每个候选的起止拍、其后 600 拍内是否阵亡。
"""
import json
import re
import sys
from collections import Counter, defaultdict

args = sys.argv[1:]
files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--match')]
mid = args[args.index('--match') + 1] if '--match' in args else None

rx_head = re.compile(r'^-- 调度候选 (\S+) t=(\d+) .*编队最大号 (\d+) 格')
rx_cand = re.compile(r'^\s+→ (?:\[[^\]]*\] )?(.+?)#(\d+) 地 (\d+) 兵 (\d+) 密度 \S+｜被真人打 (\d+)（.*?L\d+ 判为弃子（被真人打 \d+ > (1\.65×兵|0\.45×兵)')

pair = defaultdict(set)      # branch -> {(cand, t)}
trip = Counter()             # branch -> donor×cand×t
b2also = set()               # (cand, t)：第一分支成立、第二分支的条件同时也成立
per = defaultdict(list)      # cand -> [t]
ratio = defaultdict(list)    # cand -> [被打量/存兵]
donor = t = mx = None
for f in files:
    for line in open(f, encoding='utf-8', errors='replace'):
        m = rx_head.match(line)
        if m:
            donor, t, mx = m.group(1), int(m.group(2)), int(m.group(3))
            continue
        m = rx_cand.match(line)
        if not m or donor is None:
            continue
        cand, Lp, Bp, inH = m.group(1).strip(), int(m.group(3)), int(m.group(4)), int(m.group(5))
        br = 'b1' if m.group(6).startswith('1.65') else 'b2'
        key = (cand, t)
        if key not in pair[br]:
            per[cand].append(t)
            ratio[cand].append(inH / max(1, Bp))
        pair[br].add(key)
        trip[br] += 1
        if br == 'b1' and t >= 4500 and Lp < 0.22 * mx and inH > 0.45 * Bp:
            b2also.add(key)

death = {}
if mid:
    T = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
    for p in T['players']:
        if p.get('squad'):
            death[p['name']] = p.get('deathT')
    for s in T['squad']:
        for p in T['players']:
            if p['id'] == s['p']:
                death[s['bot']] = p.get('deathT')

print(f"[弃子线 两个分支] （候选×拍）第一分支 {len(pair['b1'])}、第二分支 {len(pair['b2'])}｜（捐出方×候选×拍）第一分支 {trip['b1']}、第二分支 {trip['b2']}")
print(f"  第一分支成立时第二分支的条件也成立：{len(b2also)}（候选×拍）")
for cand in sorted(per, key=lambda c: min(per[c])):
    ts = sorted(set(per[cand]))
    r = sorted(ratio[cand])
    d = None
    for k, v in death.items():
        if k and (k == cand or cand.endswith(k)):
            d = v
    tail = ''
    if mid:
        tail = f"｜阵亡拍 {d if d else '—'}" + (f"（最后一次被判弃子后 {d - ts[-1]} 拍）" if d else '')
    print(f"  {cand:10s} {len(ts):4d} 拍 {ts[0]}–{ts[-1]}｜被打量÷存兵 中位 {r[len(r) // 2]:.2f} 最大 {r[-1]:.2f}{tail}")
