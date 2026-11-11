#!/usr/bin/env python3
"""afk_gap.py — 录像里每条 leave 指令之前，该席位最后一条其他指令离它多少拍；以及没有 leave 的席位里，相邻两条指令之间的最大间隔。
用来核对“离场是不是发生在长时间不下令之后”（挂机踢出/客户端卡死的线索）。只读 out/<mid>/replay_cmds.csv、resim_events.csv、resim_meta.json。
用法：python3 afk_gap.py <matchId> [--squad-only]
"""
import csv, json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
D = os.path.join(HERE, '..', 'out', mid)
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
H = meta['humans']; names = meta['names']; seat = {v: k for k, v in meta['squad'].items()}
cmds = defaultdict(list); leave = {}
for r in csv.DictReader(open(os.path.join(D, 'replay_cmds.csv'))):
    p = int(r['player']); t = int(r['tick'])
    if p >= H: continue
    if r['kind'] in ('leave', 'surrender'):
        if r['kind'] == 'leave': leave.setdefault(p, t)
    elif r['kind'] != 'spawn':
        cmds[p].append(t)
died = {}
for r in csv.DictReader(open(os.path.join(D, 'resim_events.csv'))):
    if r['ev'] == 'died': died[int(r['p'])] = int(r['t'])
last = meta['lastTick']
print(f"== {mid} 离场前的静默：leave 拍 − 该席位最后一条非出生指令的拍")
gaps = []
for p, tl in sorted(leave.items(), key=lambda kv: kv[1]):
    if tl < 0: continue
    prev = [t for t in cmds[p] if t <= tl]
    g = tl - max(prev) if prev else None
    gaps.append((g, p))
    if '--squad-only' in a and p not in seat: continue
    print(f"   t={tl:5d} {names[p][:22]:22s} {'本队' if p in seat else '    '} 最后指令 t={max(prev) if prev else '-'} 静默 {g if g is not None else '-'} 拍，全程指令 {len(prev)} 条")
gs = sorted(g for g, _ in gaps if g is not None)
if gs:
    print(f"   静默拍数分布（{len(gs)} 个离场）：最小 {gs[0]} 中位 {gs[len(gs) // 2]} 最大 {gs[-1]}；落在 450–560 拍的 {sum(1 for g in gs if 450 <= g <= 560)} 个")
print("== 没有 leave 的席位：相邻两条指令之间的最大间隔（只算在世期间；到阵亡/终局为止）")
rows = []
for p in range(H):
    if p in leave or not cmds[p]: continue
    end = died.get(p, last)
    ts = sorted(t for t in cmds[p] if t <= end) + [end]
    mg = max((b - x, x) for x, b in zip(ts, ts[1:])) if len(ts) > 1 else (0, 0)
    rows.append((mg[0], mg[1], p))
for g, t0, p in sorted(rows, reverse=True)[:12]:
    print(f"   {names[p][:22]:22s} {'本队' if p in seat else '    '} 最大间隔 {g} 拍（从 t={t0} 起）{'，以阵亡结束' if p in died else ''}")
print(f"   没有 leave 的 {len(rows)} 个席位里，最大间隔 >560 拍的 {sum(1 for g, _, _ in rows if g > 560)} 个")
