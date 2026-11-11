#!/usr/bin/env python3
"""death_ledger.py — 每个阵亡（或离场）的本队号在死前的兵力账：
  · “最后一段围攻”的起点 = 阵亡前最后一次“连续 >=3 个采样点没有来兵”之后第一个有来兵的采样点；
  · 起点前 900 拍内：捐出（付出额/到账额/笔数）、收到的捐款、出海装兵+手续费、对外进攻实扣；
  · 起点时的余额、密度、150 倍上限；起点到阵亡之间：收到的捐款、自己发出的进攻令条数与实扣、被拒的协防调度条数；
  · 夺走它领土最多的 3 个对手。
用法：python3 death_ledger.py <matchId> [--window 900]
依赖 out/<matchId>/ 下的 resim_squad.csv、resim_transfers.csv、resim_events.csv、resim_meta.json、shadow_match.csv、boat_trace.csv、dispatch_audit.csv。
"""
import csv, json, os, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
WIN = int(opt('window', 900))
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8'))) if os.path.exists(os.path.join(D, f)) else []
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
names, teams, H = meta['names'], meta['teams'], meta['humans']
squad = meta['squad']; seat = {v: k for k, v in squad.items()}
nm = lambda p: (seat.get(int(p)) or (f"{names[int(p)]}/T{teams[str(int(p))]}" if int(p) < H else f"AI#{p}"))
sq = defaultdict(list)
for r in rd('resim_squad.csv'): sq[r['bot']].append(r)
tr = [r for r in rd('resim_transfers.csv') if r['ok'] == '1']
ev = [r for r in rd('resim_events.csv') if int(r['p']) in seat and r['ev'] in ('died', 'left')]
mt = rd('shadow_match.csv'); boats = rd('boat_trace.csv'); da = rd('dispatch_audit.csv')
def atk_in(r):
    s = 0
    for part in (r['atkIn'] or '').split('|'):
        if ':' in part:
            try: s += int(part.rsplit(':', 1)[1])
            except ValueError: pass
    return s
for e in sorted(ev, key=lambda r: int(r['t'])):
    bot = seat[int(e['p'])]; T = int(e['t'])
    rows = [r for r in sq[bot] if int(r['t']) <= T and r['alive'] == '1']
    # 最后一段围攻的起点
    start = None; quiet = 0
    for r in rows:
        if atk_in(r) > 0:
            if start is None or quiet >= 3: start = r
            quiet = 0
        else: quiet += 1
    if start is None: start = rows[-1]
    t0 = int(start['t'])
    def pick(t):
        c = [r for r in rows if int(r['t']) <= t]
        return c[-1] if c else rows[0]
    p = int(e['p'])
    out_pre = [r for r in tr if int(r['from']) == p and r['kind'] == 'cmd' and t0 - WIN <= int(r['t']) < t0]
    in_pre = [r for r in tr if int(r['to']) == p and t0 - WIN <= int(r['t']) < t0]
    in_siege = [r for r in tr if int(r['to']) == p and t0 <= int(r['t']) <= T]
    out_siege = [r for r in tr if int(r['from']) == p and r['kind'] == 'cmd' and t0 <= int(r['t']) <= T]
    b_pre = [b for b in boats if b['bot'] == bot and t0 - WIN <= int(b['launch']) < t0]
    atk_pre = [x for x in mt if x['bot'] == bot and x['kind'] == 'attack' and t0 - WIN <= int(x['tick']) < t0]
    atk_siege = [x for x in mt if x['bot'] == bot and x['kind'] == 'attack' and t0 <= int(x['tick']) <= T]
    rej = [r for r in da if r['toName'].replace('[APEX] ', '') == bot and r['executed'] != '1' and t0 <= int(r['t']) <= T]
    spent = lambda xs: sum(int(float(x['spent'] or 0)) for x in xs)
    took = ''
    for k in e['detail'].split(';'):
        if k.startswith('tookLife='):
            took = '，'.join(f"{nm(x.split(':')[0])} {x.split(':')[1]}" for x in k[9:].split('|')[:3] if ':' in x)
    r900 = pick(t0 - WIN); r0 = start
    print(f"== {bot} {e['ev']}@{T}（剩 {e['terr']} 格、{e['bal']} 兵）；最后一段围攻从 {t0} 拍起（当拍来兵 {atk_in(r0)}）")
    print(f"   {t0 - WIN} 拍：领土 {r900['terr']} 余额 {r900['bal']} 密度 {r900['dens']} | {t0} 拍：领土 {r0['terr']} 余额 {r0['bal']} 密度 {r0['dens']}（150 倍上限 {150 * int(r0['terr'])}）")
    print(f"   起点前 {WIN} 拍：捐出 {len(out_pre)} 笔 付出 {sum(int(r['paid']) for r in out_pre)}（到账 {sum(int(r['received']) for r in out_pre)}）；收到 {len(in_pre)} 笔 {sum(int(r['received']) for r in in_pre)}；"
          f"出海 {len(b_pre)} 条 装兵 {sum(int(b['troops0']) for b in b_pre)} 手续费 {sum(int(b['fee']) for b in b_pre)}；进攻落地 {len(atk_pre)} 条 实扣 {spent(atk_pre)}")
    print(f"   围攻期间（{t0}–{T}）：收到捐款 {len(in_siege)} 笔 {sum(int(r['received']) for r in in_siege)}；自己又捐出 {len(out_siege)} 笔 付出 {sum(int(r['paid']) for r in out_siege)}；进攻落地 {len(atk_siege)} 条 实扣 {spent(atk_siege)}；发给它但没落地的调度 {len(rej)} 条")
    print(f"   夺地：{took}")
