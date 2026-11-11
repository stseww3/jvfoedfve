#!/usr/bin/env python3
"""strike_reply.py — 本队每一轮打真人的进攻之后，多久有人类席位对这个号下进攻令、是谁。
“一轮” = 同一个号对同一个人类目标落地的进攻令，相邻两条落地拍相差 <= --gap（默认 30）拍算同一轮。
每轮列出：
  号、目标（队）、落地拍区间、条数、整轮实扣（shadow_match.csv 的 spent 之和）占第一条执行前余额的比例、
  第一条决策时想出的兵占当时余额的比例（意图；只有一条能配上决策拍时才有）、
  打之前 / 打完后本号的密度（resim_squad.csv 上一个 / 下一个 30 拍采样点）、
  这一轮最后一条落地之后，第一条人类席位对本号的进攻令：落地拍、相隔拍数、谁（队；是否和目标同队）、它在上一采样点的密度、按 pct 估的出兵量；
  --win（默认 200）拍内对本号下进攻令的人类席位数 / 条数 / 估算出兵合计；本号阵亡拍。
末尾给一个基线：1500 拍起每个号每个 30 拍采样点（存活时）往后 --win 拍内有没有人类进攻令，有的比例是多少（和“打完一轮之后”的比例对照）。
依赖 out/<matchId>/ 下的 shadow_match.csv、replay_cmds.csv、resim_squad.csv、resim_players.csv、resim_meta.json、resim_events.csv。
用法：python3 strike_reply.py <matchId> [--gap 30] [--win 200] [--min-share 0.05]
  --min-share：只列整轮实扣占执行前余额不低于这个比例的轮（默认 5%，过滤掉扫残部的小单）。
"""
import csv, json, os, statistics, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
GAP, WIN, MINSH = int(opt('gap', 30)), int(opt('win', 200)), float(opt('min-share', 0.05))
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8')))
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
names, teams, H = meta['names'], meta['teams'], meta['humans']
squad = meta['squad']; seat2bot = {int(v): k for k, v in squad.items()}
tm = lambda p: teams[str(p)] if isinstance(teams, dict) else teams[p]
nm = lambda p: seat2bot.get(p) or (f'{names[p]}/T{tm(p)}' if p < H else f'AI#{p}')
pl = {(int(r['p']), int(r['t'])): (int(r['terr']), int(r['bal'])) for r in rd('resim_players.csv')}
at = lambda p, t: pl.get((p, (t // 90) * 90))
sq = defaultdict(dict)
for r in rd('resim_squad.csv'): sq[r['bot']][int(r['t'])] = r
died = {}
for e in rd('resim_events.csv'):
    if e['ev'] in ('died', 'left') and int(e['p']) in seat2bot: died.setdefault(seat2bot[int(e['p'])], int(e['t']))
# 人类对本队号的进攻令
foe = defaultdict(list)
for r in rd('replay_cmds.csv'):
    if r['kind'] != 'attack': continue
    try: q = int(r['dZ'])
    except ValueError: continue
    p = int(r['player'])
    if q in seat2bot and p < H and p not in seat2bot: foe[seat2bot[q]].append((int(r['tick']), p, int(r['dX'])))
# 本队打真人的落地令，按号、目标分轮
mine = defaultdict(list)
for r in rd('shadow_match.csv'):
    if r['kind'] != 'attack' or r['applied'] != '1': continue
    try: q = int(r['target'])
    except ValueError: continue
    if q >= H or q in seat2bot: continue
    mine[(r['bot'], q)].append(r)
rounds = []
for (bot, q), lst in mine.items():
    lst.sort(key=lambda r: int(r['tick']))
    cur = [lst[0]]
    for r in lst[1:]:
        if int(r['tick']) - int(cur[-1]['tick']) <= GAP: cur.append(r)
        else: rounds.append((bot, q, cur)); cur = [r]
    rounds.append((bot, q, cur))
rounds.sort(key=lambda x: int(x[2][0]['tick']))
def dens_at(bot, t, after):
    ts = sorted(sq[bot])
    c = [x for x in ts if (x >= t if after else x <= t)]
    if not c: return None
    r = sq[bot][c[0] if after else c[-1]]
    return r if r['alive'] == '1' and int(r['terr']) > 0 else None
print(f'== {mid} 本队打真人的每一轮进攻，和之后第一条打回来的人类进攻令（整轮实扣占执行前余额 >= {MINSH:.0%} 的轮）')
print('   号 | 目标 | 落地拍 | 条数 | 实扣/执行前余额（意图）| 密度 打前→打后 | 之后第一条人类进攻令：相隔拍数 谁 密度 估算出兵 | 之后 %d 拍内：席位数/条数/估算出兵合计 | 阵亡拍' % WIN)
gaps = []; n_same = 0; n = 0
for bot, q, lst in rounds:
    t0, t1 = int(lst[0]['tick']), int(lst[-1]['tick'])
    spent = sum(int(float(r['spent'] or 0)) for r in lst)
    bal0 = max(int(float(r['balExec'] or 0)) for r in lst)   # 同拍多条时，最先执行的那条余额最大
    if bal0 <= 0 or spent / bal0 < MINSH: continue
    first = min(lst, key=lambda r: int(r['tDecide']) if r['tDecide'] else 10**9)
    intent = (float(first['troopsDecide']) / float(first['balDecide'])) if first['tDecide'] and float(first['balDecide'] or 0) > 0 else None
    b0, b1 = dens_at(bot, t0 - 1, False), dens_at(bot, t1 + 30, True)
    d0 = f"{float(b0['dens']):.0f}" if b0 else '-'; d1 = f"{float(b1['dens']):.0f}" if b1 else '-'
    nxt = [x for x in foe[bot] if x[0] > t1]
    within = [x for x in nxt if x[0] <= t1 + WIN]
    est = lambda x: int((at(x[1], x[0]) or (0, 0))[1] * (x[2] + 1) / 1024)
    if nxt:
        ft, fp, fpct = nxt[0]; s = at(fp, ft) or (1, 0)
        same = tm(fp) == tm(q)
        rep = f'{ft - t1:4d} 拍 {nm(fp)}{"（目标同队）" if same and fp != q else "（就是目标）" if fp == q else ""} 密度 {s[1] / max(1, s[0]):.0f} 约 {est(nxt[0])} 兵'
        if ft - t1 <= WIN: gaps.append(ft - t1); n_same += 1 if same else 0
    else: rep = '无'
    n += 1
    print(f'   {bot:7s} | {nm(q)[:22]:22s} | {t0}–{t1} | {len(lst)} | {spent / bal0:5.1%}（{"%.1f%%" % (intent * 100) if intent else "-"}）| {d0}→{d1} | {rep} | '
          f'{len({x[1] for x in within})}/{len(within)}/{sum(est(x) for x in within)} | {died.get(bot, "-")}')
if gaps:
    print(f'   合计 {n} 轮；其中 {len(gaps)} 轮在 {WIN} 拍内有人类席位对这个号下进攻令：相隔拍数 最小/中位/最大 = {min(gaps)}/{statistics.median(gaps):g}/{max(gaps)}；第一条来自目标本人或其同队的 {n_same} 轮')
# 基线：不管有没有出手，任取一个采样点，往后 WIN 拍内有人类进攻令的比例
tot = hit = 0
for bot, d in sq.items():
    ticks = [x[0] for x in foe[bot]]
    for t, r in d.items():
        if t < 1500 or r['alive'] != '1' or int(r['terr']) == 0: continue
        if died.get(bot, 10**9) < t + WIN: continue          # 窗口没走完就阵亡的点不算
        tot += 1; hit += 1 if any(t < x <= t + WIN for x in ticks) else 0
if tot: print(f'   基线：1500 拍起各号的 30 拍采样点（往后 {WIN} 拍内仍存活）{tot} 个，其中往后 {WIN} 拍内有人类进攻令的 {hit} 个（{hit / tot:.1%}）；打完一轮之后是 {len(gaps)}/{n}（{len(gaps) / max(1, n):.1%}）')
