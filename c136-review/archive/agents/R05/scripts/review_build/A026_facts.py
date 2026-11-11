#!/usr/bin/env python3
"""A026_facts.py — A026 复盘里通用脚本没有直接给出的几组数字（只读对局包、真值 JSON、delay_account.py 的 JSON）。

  §A 出生：每个号在日志里的出生坐标序列（L = 策略自己兜底算的点 [HL-SPAWN]，B = 协调器给的点 [HL-SPAWN-BACKEND]；
     每变一次记一行）对 录像里它的出生指令；实际出生点、离指派点多远、最近的敌方真人/我方号出生点。
  §B 落地批（≥3 条同拍）逐批：批内决策拍范围、延迟、目标、名义兵数（决策拍按当时存兵算）对实际兵数、批前存兵、打出比例、拿到的格数。
  §C 我方每个号被敌方真人拿走的地：对方投入的兵 ÷ 拿到的格（守方密度越高越贵）。
  §D 两个离场的号：最后一条日志的本地拍 对 录像里的离场拍。
  §E 每 300 拍：影子想发 / 落地 / 按原意落地，延迟中位；我方号地中位 对 其余真人地中位。

用法：python3 scripts/review_build/A026_facts.py [--sec A,B,C,D,E] [--from 2300]
需要：/tmp/c136-r05/truth/A026.json、/tmp/c136-r05/work/A026-delay.json、/tmp/c136-r05/work/A026-cmds.tsv、/tmp/c136-r05/skel/A026.json
"""
import csv
import json
import math
import re
import statistics
import sys
from collections import defaultdict

M = 'A026'
a = sys.argv[1:]
secs = set((a[a.index('--sec') + 1] if '--sec' in a else 'A,B,C,D,E').split(','))
T0 = int(a[a.index('--from') + 1]) if '--from' in a else 0
B = f'/agent/repos/c136-data/bundles/{M}'
T = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
D = json.load(open(f'/tmp/c136-r05/work/{M}-delay.json'))
W = T['map']['W']
P = {p['id']: p for p in T['players']}
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip()
SQ = [p for p in T['players'] if p['squad']]
k = lambda v: f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}'

if 'A' in secs:
    print('§A 出生：日志里的坐标序列 对 录像里的出生指令')
    seq = defaultdict(list)
    solves = []
    n = 0
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        n += 1
        m = re.search(r'\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms .*?\): (.*)', ln)
        if m:
            solves.append((n, float(m.group(2)), m.group(3).strip()))
        m = re.search(r'\[(\w+)\] \[(HL-SPAWN(?:-BACKEND)?)\].*?-> \((\d+),(\d+)\)', ln)
        if m:
            seq[m.group(1)].append((n, 'L' if m.group(2) == 'HL-SPAWN' else 'B', int(m.group(3)), int(m.group(4))))
    sp = defaultdict(list)
    for r in csv.DictReader(open(f'/tmp/c136-r05/work/{M}-cmds.tsv', encoding='utf-8'), delimiter='\t'):
        if r['kind'] == 'spawn':
            sp[int(r['player'])].append((int(r['tick']), int(r['a']) % W, int(r['a']) // W))
    print(f'   求解日志 {len(solves)} 行（日志行号 {solves[0][0]}–{solves[-1][0]}），去掉耗时后不同的解 {len(set(s[2] for s in solves))} 个；耗时中位 {statistics.median(s[1] for s in solves):.0f} 毫秒')
    print(f'   录像里选点期的出生指令：我方号 {sum(len(sp[p["id"]]) for p in SQ)} 条，其余真人 {sum(len(v) for q, v in sp.items() if not P[q]["squad"])} 条（{sum(1 for q in sp if not P[q]["squad"])} 人）；选点期第一拍 {min(t for v in sp.values() for t, _, _ in v)}')
    lens = [math.hypot(x - 940, y - 425) for v in seq.values() for _, kd, x, y in v if kd == 'L']
    print(f'   兜底点（L）{len(lens)} 个，其中离 (940,425) ≤20 格的 {sum(1 for d in lens if d <= 20)} 个')
    for p in SQ:
        b = bare(p['name'])
        s = seq.get(b, [])
        ax, ay = p['spawn']
        fin = next(((x, y) for _, kd, x, y in reversed(s) if kd == 'B'), None)
        eh = min(((math.hypot(ax - q['spawn'][0], ay - q['spawn'][1]), bare(q['name'])) for q in T['players'] if q['team'] != p['team'] and q['spawn'][0] >= 0), default=(0, '-'))
        al = min(((math.hypot(ax - q['spawn'][0], ay - q['spawn'][1]), bare(q['name'])) for q in SQ if q['id'] != p['id']), default=(0, '-'))
        print(f'   {b}#{p["id"]}: 日志 ' + ' '.join(f'{kd}#{ln}({x},{y})' for ln, kd, x, y in s)
              + f'｜录像 {" ".join(f"拍{t}:({x},{y})" for t, x, y in sp.get(p["id"], [])) or "0 条"}'
              + f'｜实际出生 ({ax},{ay})' + (f'，离最后一次指派 {math.hypot(ax - fin[0], ay - fin[1]):.0f} 格' if fin else '')
              + f'｜最近敌方真人 {eh[1]} {eh[0]:.0f} 格｜最近我方号 {al[1]} {al[0]:.0f} 格')
    en = [(q['id'], bare(q['name']), q['spawn']) for q in T['players'] if not q['squad'] and q['team'] != SQ[0]['team']]
    slots = {bare(p['name']): next(((x, y) for _, kd, x, y in reversed(seq.get(bare(p['name']), [])) if kd == 'B'), None) for p in SQ}
    for qid, qn, (qx, qy) in en:
        near = sorted((math.hypot(qx - s[0], qy - s[1]), b) for b, s in slots.items() if s)
        if near and near[0][0] <= 60:
            print(f'   敌方 {qn}#{qid} 出生 ({qx},{qy})（录像出生指令 {" ".join(f"拍{t}" for t, _, _ in sp.get(qid, []))}）：离指派给 {near[0][1]} 的点 {near[0][0]:.0f} 格' + (f'、{near[1][1]} {near[1][0]:.0f} 格' if len(near) > 1 and near[1][0] <= 90 else ''))

if 'B' in secs:
    print(f'§B 落地批（同拍 ≥3 条；落地拍 ≥{T0}）：号 落地拍×条数｜批内决策拍｜延迟｜目标类（N 中立 B 机器人 H 真人 S 船）｜结果（h 命中 d 目标已死 v 不接壤作废）｜名义兵→实际兵｜批前存兵、打出比例、退回、格数')
    BL = {(b['bot'], b['T']): b for b in D['batchList']}
    g = defaultdict(list)
    for bot, t, kind, cls, st, TT, delay, nom, act, ret in D['decisions']:
        if TT is not None and st != 'lost':
            g[(bot, TT)].append((t, delay, cls, st, nom or 0, act or 0))
    for (bot, TT), L in sorted(g.items(), key=lambda x: (x[0][0], x[0][1])):
        if len(L) < 3 or TT < T0:
            continue
        b = BL.get((bot, TT), {})
        ts = [x[0] for x in L]
        ds = [x[1] for x in L]
        print(f'   {bot} {TT}×{len(L)}｜决策 {min(ts)}–{max(ts)}｜延迟 {min(ds)}–{max(ds)}｜{"".join(sorted(set(x[2] for x in L)))}｜{"".join(sorted(set(x[3][0] for x in L)))}'
              f'｜名义 {k(sum(x[4] for x in L))} → 实际 {k(sum(x[5] for x in L))}'
              + (f'｜批前存兵 {k(b["B0"])}，打出 {b["drain"] * 100:.0f}%，手续费 {k(b["fee"])}，退回 {k(b["ret"])}，拿地 {b["tiles"]:.0f} 格' if b else ''))

if 'C' in secs:
    print('§C 敌方真人从我方每个号手里拿地：投入的兵 ÷ 格数（events：对方打这个号的已执行陆攻兵数；pairAll：拿走的格数）')
    sent = defaultdict(float)
    for e in T['events']:
        if e['type'] == 'attack' and e.get('ok') and e['q'] in P and P[e['q']]['squad'] and e['p'] in P and not P[e['p']]['squad']:
            sent[(e['p'], e['q'])] += e.get('troops', 0)
    tiles = defaultdict(float)
    for w, aa, bb, n in T['pairAll']:   # [600 拍窗号, 拿地的人, 被拿的人（512 中立、600 机器人）, 格数]
        if bb in P and P[bb]['squad'] and aa in P and not P[aa]['squad'] and P[aa]['team'] != P[bb]['team']:
            tiles[(aa, bb)] += n
    for p in SQ:
        tot_s = sum(v for (aa, bb), v in sent.items() if bb == p['id'])
        tot_t = sum(v for (aa, bb), v in tiles.items() if bb == p['id'])
        if tot_t:
            who = sorted(((v, bare(P[aa]['name'])) for (aa, bb), v in tiles.items() if bb == p['id']), reverse=True)[:3]
            print(f'   {bare(p["name"])}: 敌方真人投入 {k(tot_s)}，拿走 {tot_t:.0f} 格 → {tot_s / tot_t:.0f} 兵/格（峰值地 {p["peakTerr"]}）｜' + '、'.join(f'{n} {v:.0f} 格' for v, n in who))

if 'D' in secs:
    print('§D 离场的号：最后一条 [HL-TICK] 的本地拍 对 录像里的离场拍')
    last = defaultdict(int)
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        last[r['bot']] = max(last[r['bot']], int(r['t']))
    res = {r['bot'] for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8'))}
    for p in SQ:
        b = bare(p['name'])
        if p['leftT'] >= 0:
            print(f'   {b}: 最后一条日志 t={last[b]}（下一条该在 t={last[b] + 90}）｜录像离场拍 {p["leftT"]} → 离场时本地拍 < {last[b] + 90}，至少落后 {p["leftT"] - last[b] - 90} 拍｜结果行 {"有" if b in res else "无"}｜阵亡拍 {p["deathT"]}')

if 'E' in secs:
    print('§E 每 300 拍：影子想发（按决策拍）/ 其中落地 / 按原意落地；落地指令的延迟中位（按落地拍）；我方号地中位 对 其余真人地中位（骨架 cmp）')
    S = json.load(open(f'/tmp/c136-r05/skel/{M}.json'))
    cmp_ = {r['t']: r for r in S['cmp']}
    iss, land, hit = defaultdict(int), defaultdict(int), defaultdict(int)
    dl = defaultdict(list)
    for bot, t, kind, cls, st, TT, delay, nom, act, ret in D['decisions']:
        w = t // 300 * 300
        iss[w] += 1
        if st != 'lost':
            land[w] += 1
            if st == 'hit':
                hit[w] += 1
            dl[TT // 300 * 300].append(delay)
    for w in sorted(iss):
        c = cmp_.get(w + 300) or {}
        print(f'   {w}–{w + 299}: 想发 {iss[w]}｜落地 {land[w]}（{land[w] * 100 // max(1, iss[w])}%）｜按原意 {hit[w]}（{hit[w] * 100 // max(1, iss[w])}%）｜这一窗落地的指令延迟中位 {statistics.median(dl[w]) if dl[w] else "-"}'
              + (f'｜t={w + 300} 我方号地中位 {c.get("squadTerrMedianAllAlive")} 对 其余真人 {c.get("realTerrMedian")}' if c else ''))
