#!/usr/bin/env python3
"""cmd_gaps.py — 本队指令通道的“断档”：录像里连续 >= N 拍没有任何一条本队号的指令落地的窗口，
对照同一窗口里影子策略受理（本地 g.attack/donate 返回 ok；不含船）的指令条数，以及断档结束后 70 拍内落地的条数。
用来区分“各号各自延迟”和“整队的指令在一段时间里一条都没到”。
用法：python3 cmd_gaps.py <matchId> [--min 60] [--t0 a --t1 b] [--bots]
  --bots：每个断档再列出窗口内各号受理的条数、断档后 70 拍内各号落地的条数和这些指令的决策拍范围（来自 shadow_match）。
依赖 out/<id>/replay_cmds.csv、shadow_cmds.csv、shadow_match.csv、resim_meta.json。
"""
import csv, json, os, sys
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
MIN = int(opt('min', 60)); T0 = int(opt('t0', 0)); T1 = int(opt('t1', 10**9))
OUT = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(OUT, 'resim_meta.json')))
squad = {int(v): k for k, v in meta['squad'].items()} if all(str(v).isdigit() for v in meta['squad'].values()) else {int(k): v for k, v in meta['squad'].items()}
allrep = [r for r in csv.DictReader(open(os.path.join(OUT, 'replay_cmds.csv'))) if r['kind'] in ('attack', 'boat', 'donate')]
rep = [r for r in allrep if int(r['player']) in squad]
others = sorted(int(r['tick']) for r in allrep if int(r['player']) not in squad)
ticks = sorted({int(r['tick']) for r in rep})
# 船指令不计：影子对 boatTo 的受理比真实客户端宽（见 shadow_report.py --section check），进攻和捐兵两类与日志计数一致
cm = [r for r in csv.DictReader(open(os.path.join(OUT, 'shadow_cmds.csv'))) if r['ok'] == '1' and r['kind'] != 'boatTo']
mt = list(csv.DictReader(open(os.path.join(OUT, 'shadow_match.csv'))))
last_alive = max(int(r['t']) for r in cm) if cm else 0
print(f'== {mid} 本队指令断档（连续 >= {MIN} 拍没有任何本队指令落地；只列窗口内影子策略受理过指令的）')
print('   断档 [上一条落地拍, 下一条落地拍] 长度 | 窗口内受理的指令 条数（发令的号数） | 断档后 70 拍内落地 条数 | 其中同拍 >=3 条的批次数 | 同一窗口里其他玩家落地的指令条数')
rows = []
for x, y in zip(ticks, ticks[1:]):
    if y - x < MIN or y < T0 or x > T1: continue
    inside = [r for r in cm if x < int(r['t']) < y]
    if not inside: continue
    after = [r for r in rep if y <= int(r['tick']) < y + 70]
    per = Counter((r['player'], r['tick']) for r in after)
    nb = sum(1 for v in per.values() if v >= 3)
    rows.append((x, y, inside, after, nb))
    no = sum(1 for t in others if x < t < y)
    print(f'   [{x:5d},{y:5d}] {y - x:4d} 拍 | 受理 {len(inside):3d} 条（{len({r["bot"] for r in inside})} 个号） | 之后 70 拍落地 {len(after):3d} 条 | 批次 {nb} | 其他玩家 {no} 条')
    if '--bots' in a:
        by = Counter(r['bot'] for r in inside)
        land = defaultdict(list)
        for r in mt:
            if y <= int(r['tick']) < y + 70 and r['tDecide'] != '':
                land[r['bot']].append(int(r['tDecide']))
        for b in sorted(set(by) | set(land)):
            d = land.get(b, [])
            print(f'        {b:8s} 窗口内受理 {by.get(b, 0):3d} 条；之后 70 拍内配上决策拍的落地 {len(d):2d} 条' + (f'，决策拍 {min(d)}–{max(d)}' if d else ''))
tot = sum(y - x for x, y, *_ in rows)
print(f'   合计 {len(rows)} 个断档、{tot} 拍；窗口内受理 {sum(len(r[2]) for r in rows)} 条')
