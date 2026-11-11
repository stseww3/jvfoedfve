# A065_facts.py — 复盘 A065 里用到、而通用工具不直接打印的数字，逐条从真值 JSON 里算出来。
# 用法：python3 scripts/review_build/A065_facts.py   （先跑 match_truth.mjs A065）
import json, bisect, statistics as st
J = json.load(open('/tmp/c136-r05/truth/A065.json'))
H = J['humans']
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
nm = lambda p: sq.get(p) or (P[p]['name'] if p in P else ('中立' if p == 512 else f'机器人#{p}'))


def at(p, t):
    s = J['S10'][str(p)]
    if 0 <= P[p]['deathT'] <= t:
        return (0, 0)
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def k(x):
    return f'{x/1000:.0f}k'


print('== 1. 各号 地/兵/密度 ==')
for b, ts in [('zero_7', [4500, 4800, 5100, 5300, 5400, 5490, 6000, 6220, 6300, 6600, 7440, 7740, 7760, 7860, 7920, 8010]),
              ('sora_w', [4200, 4800, 5800, 6600, 7260, 7320, 7400, 7530, 7800, 8100, 8280, 8330, 8340, 8400, 8550]),
              ('leo_tx', [4840, 4880, 4920, 5000, 5020, 5100, 5190, 6000, 6130]),
              ('alex_k', [4950, 5400, 5950, 6200, 6500, 6590]), ('talon5', [5100, 5400, 5700, 6000, 6300, 6450, 6660, 6740, 7300]),
              ('ryan_m', [3300, 3900, 4200, 4800, 5400, 6600, 7290, 7380, 8280, 8650]), ('zexos1', [4860, 4980, 5010, 5180]),
              ('kaito9', [4200, 4800, 5400, 5780]), ('noah88', [4200, 4800, 5400, 5580]), ('riku_x', [4200, 4800, 5190, 5260])]:
    out = []
    for t in ts:
        L, B = at(pid[b], t)
        out.append(f'{t}: {L}/{k(B)}/{(B/L if L else 0):.0f}')
    print(' ', b, ' | '.join(out))

print('== 2. 编队最大号的地 与 22% 线 ==')
for t in [4500, 4850, 5060, 5300, 5640, 5800, 6000]:
    m = max(at(p, t)[0] for p in sq)
    print(f'  t={t} 最大 {m} → 22% = {0.22*m:.0f}｜低于此线的号：', ', '.join(f'{b}({at(p,t)[0]})' for p, b in sq.items() if 0 < at(p, t)[0] < 0.22 * m))

print('== 3. 谁在什么时候打我方号（真人，陆攻 + 登陆）==')
for b in sq.values():
    rows = {}
    for e in ev:
        if e['type'] in ('attack', 'boat-land') and e.get('q') == pid[b] and 0 <= e['p'] < H and e['p'] not in sq and e.get('ok', True):
            rows.setdefault(e['p'], []).append((e['t'], e['type'], e.get('troops', 0), e.get('pct')))
    for a, r in sorted(rows.items(), key=lambda x: -sum(y[2] for y in x[1])):
        tot = sum(y[2] for y in r)
        if tot < 300e3:
            continue
        land = [y for y in r if y[1] == 'attack']
        boat = [y for y in r if y[1] == 'boat-land']
        print(f'  {nm(a)} → {b}: 陆攻 {len(land)} 条 {k(sum(y[2] for y in land))}（pct {sorted(set(y[3] for y in land))}）登陆 {len(boat)} 次 {k(sum(y[2] for y in boat))}｜首 {r[0][0]} 末 {r[-1][0]}')
        if b in ('zero_7', 'sora_w', 'ryan_m', 'talon5', 'alex_k'):
            print('     ', ' '.join(f"{y[0]}{'船' if y[1]=='boat-land' else ''}:{k(y[2])}" for y in r))

print('== 4. 我方号的同拍批（≥3 条陆攻/出船）==')
from collections import defaultdict
bt = defaultdict(list)
for e in ev:
    if e['type'] in ('attack', 'boat') and e['p'] in sq:
        bt[(e['p'], e['t'])].append(e)
for lo, hi in [(600, 900), (900, 1500), (1500, 2130), (2130, 4200), (4200, 5500), (5500, 7400), (7400, 8701)]:
    bs = [(p, t, v) for (p, t), v in bt.items() if lo <= t < hi and len(v) >= 3]
    n9 = [x for x in bs if len(x[2]) >= 8]
    print(f'  {lo}–{hi}: 批 {len(bs)} 个（共 {sum(len(x[2]) for x in bs)} 条），其中 ≥8 条的 {len(n9)} 个：', ' '.join(f'{sq[p]}@{t}×{len(v)}' for p, t, v in sorted(n9, key=lambda x: x[1])[:40]))
print('  单独列出 7400 之后的批：')
for (p, t), v in sorted(bt.items(), key=lambda x: x[0][1]):
    if t >= 7400 and len(v) >= 3:
        B0 = max(e.get('B0', 0) for e in v)
        tot = sum(e.get('troops', 0) + e.get('fee', 0) for e in v if e.get('ok', True))
        tg = defaultdict(int)
        for e in v:
            tg[nm(e['q']) if e['q'] is not None else '?'] += 1
        print(f'    {sq[p]} t={t} ×{len(v)} 批前存兵 {k(B0)} 打出 {k(tot)}（{100*tot/B0 if B0 else 0:.0f}%）目标 {dict(tg)} pct {sorted(set(e.get("pct") for e in v))}')

print('== 5. 捐兵 ==')
ad = J['allDon']
for lo, hi in [(0, 4284), (4200, 4284), (4284, 4800), (4200, 4800), (4284, 8701), (5015, 6208)]:
    r = [x for x in ad if x[1] in sq and lo <= x[0] < hi]
    print(f'  {lo}–{hi}: {len(r)} 笔 到账 {sum(x[3] for x in r)} 税 {sum(x[4] for x in r)}')
r = [x for x in ad if x[1] in sq and 5015 <= x[0] < 6208]
tg = defaultdict(lambda: [0, 0])
for x in r:
    tg[nm(x[2])][0] += 1; tg[nm(x[2])][1] += x[3]
print('  5015–6207 按受赠方：', {a: (n, k(v)) for a, (n, v) in tg.items()})
print('  非我方真人收到的捐兵（全场）：', sum(1 for x in ad if x[1] not in sq), '笔；给 Yolo(7)/Eyup(25)：', [(x[0], nm(x[1]), nm(x[2]), x[3]) for x in ad if x[2] in (7, 25)][:10])

print('== 6. 超软上限少拿的利息 ==')
for lo, hi in [(0, 3000), (3000, 4200), (4200, 5490), (5490, 6480), (6480, 7440), (7440, 8701), (0, 8701)]:
    out = []
    for p, b in sq.items():
        f = J['F30'][str(p)]   # capLoss 是累计值
        cum = lambda t: max([c for tt, c in zip(f['t'], f['capLoss']) if tt <= t] or [0])
        v = cum(hi) - cum(lo)
        if v > 20e3:
            out.append((v, b))
    print(f'  {lo}–{hi}:', ' '.join(f'{b} {k(v)}' for v, b in sorted(out, reverse=True)), '合计', k(sum(v for v, b in out)))

print('== 7. 赢家 ==')
hs = J['HS']
for q in (7, 25, 10):
    print(' ', nm(q), ' | '.join(f"{t}: {hs['terr'][i][q]}/{k(hs['bal'][i][q])}" for i, t in enumerate(hs['t']) if t in (600, 1500, 3000, 4200, 4800, 5400, 6000, 6300, 6600, 7500, 8100, 8700)))
iv = []
for a in (7, 25):
    ts = sorted(e['t'] for e in ev if e['type'] == 'attack' and e['p'] == a and e.get('q') in sq and e['t'] >= 3000)
    iv += [b - a_ for a_, b in zip(ts, ts[1:])]
    print(f'  {nm(a)} 对我方号陆攻 {len(ts)} 条')
print('  相邻两条的间隔中位', st.median(iv))

print('== 8. leo_tx 5040 之后落地的指令 ==')
print('  ', [(e['t'], e['type'], nm(e['q']) if e.get('q') is not None else None, e.get('pct')) for e in ev if e['p'] == pid['leo_tx'] and e['type'] in ('attack', 'boat', 'donate') and e['t'] > 5047])
print('== 9. sora_w 7400 之后落地的指令 ==')
r = [(e['t'], e['type'], nm(e['q']) if e.get('q') is not None else None, e.get('pct'), e.get('troops')) for e in ev if e['p'] == pid['sora_w'] and e['type'] in ('attack', 'boat', 'donate') and e['t'] >= 7250]
c = defaultdict(list)
for x in r:
    c[(x[0], x[1], x[2])].append(x[4] or 0)
print('  ', ' '.join(f'{t}:{ty}→{q}×{len(v)}({k(sum(v))})' for (t, ty, q), v in c.items()))
print('== 10. zero_7 6200–6600 / 7400–7900 落地的指令 ==')
r = [(e['t'], e['type'], nm(e['q']) if e.get('q') is not None else None, e.get('pct'), e.get('troops')) for e in ev if e['p'] == pid['zero_7'] and e['type'] in ('attack', 'boat', 'donate') and (6200 <= e['t'] < 6600 or 7300 <= e['t'] < 7900)]
c = defaultdict(list)
for x in r:
    c[(x[0], x[1], x[2])].append(x[4] or 0)
print('  ', ' '.join(f'{t}:{ty}→{q}×{len(v)}({k(sum(v))})' for (t, ty, q), v in c.items()))
print('== 11. Cwel 登陆 sora_w ==')
r = [(e['t'], e['troops']) for e in ev if e['type'] == 'boat-land' and e['p'] == 10 and e.get('q') == pid['sora_w']]
print('  ', len(r), '次 合计', k(sum(x[1] for x in r)), r)
print('== 12. 我方出船 ==')
c = defaultdict(lambda: [0, 0])
for e in ev:
    if e['type'] == 'boat' and e['p'] in sq:
        w = '0–2999' if e['t'] < 3000 else '3000–4499' if e['t'] < 4500 else '4500+'
        c[(w, sq[e['p']])][0] += 1; c[(w, sq[e['p']])][1] += e.get('troops', 0)
print('  ', {f'{w} {b}': (n, k(v)) for (w, b), (n, v) in sorted(c.items())})

print('== 13. zero_7 / sora_w 5000–6200 落地的指令 ==')
for b in ('zero_7', 'sora_w'):
    r = [(e['t'], e['type'], nm(e['q']) if e.get('q') is not None else None, e.get('troops') or 0) for e in ev if e['p'] == pid[b] and e['type'] in ('attack', 'boat', 'donate') and 5000 <= e['t'] < 6200]
    c = defaultdict(list)
    for x in r:
        c[(x[0], x[1], x[2])].append(x[3])
    print('  ', b, ' '.join(f'{t}:{ty}→{q}×{len(v)}({k(sum(v))})' for (t, ty, q), v in c.items()))
print('== 14. 0–600 的同拍批 ==')
print('  ', [(sq[p], t, len(v)) for (p, t), v in bt.items() if t < 600 and len(v) >= 3])
print('== 15. 被围的七个号合计 ==')
enc = ['zexos1', 'ryan_m', 'kaito9', 'riku_x', 'talon5', 'leo_tx', 'noah88']
for t in (3000, 3300, 4200, 4500, 4800, 5400):
    L = sum(at(pid[b], t)[0] for b in enc); B = sum(at(pid[b], t)[1] for b in enc)
    L8 = L + at(pid['alex_k'], t)[0]; B8 = B + at(pid['alex_k'], t)[1]
    print(f'  t={t} 七号 地 {L}（全图 {100*L/664497:.1f}%）兵 {k(B)} 密度 {B/L:.0f}｜加 alex_k 八号 地 {L8} 兵 {k(B8)} 密度 {B8/L8:.0f}')
print('== 16. 我方号在各段落地的指令数（陆攻+出船+捐兵）==')
for lo, hi in [(5015, 6208), (5400, 6600), (6600, 7400)]:
    c = defaultdict(lambda: defaultdict(int))
    for e in ev:
        if e['p'] in sq and e['type'] in ('attack', 'boat', 'donate') and lo <= e['t'] < hi:
            tgt = '捐兵' if e['type'] == 'donate' else ('打真人' if e['q'] is not None and 0 <= e['q'] < H else '打中立/机器人/出船')
            c[sq[e['p']]][tgt] += 1
    print(f'  {lo}–{hi}:', {b: dict(v) for b, v in c.items()})
