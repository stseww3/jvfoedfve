#!/usr/bin/env python3
"""xteam_frontier.py — B 组（一个编队分在几个队里）的“边界上是谁”账：本队每个还在场的号，在每个采样点（resim_squad.csv，每 30 拍）
的边界接触格按对方分类：
  xsq   别队的本队号（含离场壳）——c110 的 isProtectedSquadMate（L3993–3996）在还有路人存活时把它们当兄弟保护：不算邻居、不打
  mate  同队（本队号或路人）——引擎不允许打
  foe   别队的路人真人（在场）——可以打
  fhusk 别队路人的离场壳——可以打（当机器人）
  ai    内置 AI（其中名字撞池的看不见，见 pool_ai.mjs；这里只有合计格数）
  neu   无主地
用法：python3 scripts/xteam_frontier.py <局号> [--periods 0-600,600-1500,1500-3000,3000-99999] [--bot 号名]
输出：按时段、按号：采样点数；“身边没有任何可以打的对象”（foe+fhusk+ai+neu 都是 0）的采样点数，其中边界上有别队本队号的；
      人类边界（xsq+mate+foe+fhusk）里 xsq 占几成（按格数累加）；以及那些点上自己的 领土/余额/密度 均值、贴着的别队本队号是谁。
说明：接触格 = 自己的边界格里贴着对方的格数（resim.mjs 的 enemyNb/allyNb/huskNb 的第二个字段）；AI 一栏是“AI 个数:接触格数”。
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
periods = [tuple(map(int, w.split('-'))) for w in opt('periods', '0-600,600-1500,1500-3000,3000-99999').split(',')]
only = opt('bot')
D = os.path.join(HERE, '..', 'out', mid)
rows = list(csv.DictReader(open(os.path.join(D, 'resim_squad.csv'), encoding='utf8')))
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
teams = meta['teams']
tm = lambda p: teams[str(p)] if isinstance(teams, dict) else teams[p]
sq = {int(v): k for k, v in meta['squad'].items()}


def parse(s):
    out = []
    for x in (s or '').split('|'):
        if x:
            o, c, terr, bal = x.split(':')
            out.append((int(o), int(c)))
    return out


agg = defaultdict(lambda: defaultdict(lambda: {'n': 0, 'boxed': 0, 'boxedX': 0, 'xsq': 0, 'mate': 0, 'foe': 0, 'fhusk': 0, 'ai': 0, 'neu': 0, 'terr': 0, 'bal': 0, 'who': defaultdict(int)}))
for r in rows:
    if r['alive'] != '1' or r['state'] == '2':
        continue
    b, t, p = r['bot'], int(r['t']), int(r['p'])
    if only and b != only:
        continue
    per = next((f'{t0}–{t1}' if t1 < 99999 else f'{t0}+' for t0, t1 in periods if t0 <= t < t1), None)
    if per is None:
        continue
    c = {'xsq': 0, 'mate': 0, 'foe': 0, 'fhusk': 0}
    who = []
    for o, n in parse(r['enemyNb']):
        if o in sq:
            c['xsq'] += n
            who.append(o)
        else:
            c['foe'] += n
    for o, n in parse(r['allyNb']):
        c['mate'] += n
    for o, n in parse(r['huskNb']):
        if tm(o) == tm(p):
            c['mate'] += n
        elif o in sq:
            c['xsq'] += n
            who.append(o)
        else:
            c['fhusk'] += n
    ai = int((r['aiNb'] or '0:0').split(':')[1])
    neu = int(r['neutralC'] or 0)
    x = agg[per][b]
    x['n'] += 1
    for k, v in c.items():
        x[k] += v
    x['ai'] += ai
    x['neu'] += neu
    if c['foe'] + c['fhusk'] + ai + neu == 0:
        x['boxed'] += 1
        x['terr'] += int(r['terr'])
        x['bal'] += int(r['bal'])
        if c['xsq'] > 0:
            x['boxedX'] += 1
            for o in who:
                x['who'][sq[o]] += 1

print(f'== {mid} 边界上是谁（每 30 拍一个采样点；只算还在场的号）')
for t0, t1 in periods:
    per = f'{t0}–{t1}' if t1 < 99999 else f'{t0}+'
    if per not in agg:
        continue
    A = agg[per]
    N = sum(x['n'] for x in A.values())
    BX = sum(x['boxed'] for x in A.values())
    BXX = sum(x['boxedX'] for x in A.values())
    hum = sum(x['xsq'] + x['mate'] + x['foe'] + x['fhusk'] for x in A.values())
    xs = sum(x['xsq'] for x in A.values())
    print(f'-- {per}：采样点 {N}；身边没有任何可打对象的 {BX}（{100 * BX / max(1, N):.1f}%），其中贴着别队本队号的 {BXX}；人类边界格里 别队本队号 占 {100 * xs / max(1, hum):.1f}%（{xs}/{hum}）')
    for b, x in sorted(A.items(), key=lambda kv: -kv[1]['boxedX']):
        h = x['xsq'] + x['mate'] + x['foe'] + x['fhusk']
        allc = h + x['ai'] + x['neu']
        print(f"   {b:14s} 点 {x['n']:3d} | 没有可打对象 {x['boxed']:3d}（贴着别队本队号 {x['boxedX']:3d}"
              + (f"；那些点上 领土均值 {x['terr'] // max(1, x['boxed'])} 余额均值 {x['bal'] // max(1, x['boxed'])} 密度 {x['bal'] / max(1, x['terr']):.0f}" if x['boxed'] else '')
              + f"） | 边界格占比 别队本队号 {100 * x['xsq'] / max(1, allc):.0f}% 同队 {100 * x['mate'] / max(1, allc):.0f}% 别队路人 {100 * (x['foe'] + x['fhusk']) / max(1, allc):.0f}% AI {100 * x['ai'] / max(1, allc):.0f}% 无主 {100 * x['neu'] / max(1, allc):.0f}%"
              + (f" | 贴着：{'、'.join(f'{k} {v}' for k, v in sorted(x['who'].items(), key=lambda kv: -kv[1]))}" if x['who'] else ''))
