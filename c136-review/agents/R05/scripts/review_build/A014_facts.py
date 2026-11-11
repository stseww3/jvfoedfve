# A014_facts.py — A014 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / boat_fate.mjs / shadow.mjs）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A014.json 机械算出。用法：python3 scripts/review_build/A014_facts.py
import json, bisect
from collections import Counter, defaultdict

J = json.load(open('/tmp/c136-r05/truth/A014.json'))
H = J['humans']
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
ad = J['allDon']
D = J['dispatch']
T = J['T30']
HS = J['HS']


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return '中立' if p == 512 else f'机器人#{p}'


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'


def at(p, t):
    s = J['S10'][str(p)]
    if 0 <= P[p]['deathT'] <= t:
        return (0, 0)
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def hs(t):
    i = HS['t'].index(t)
    return HS['terr'][i], HS['bal'][i]


print('== 1 调度日志按时段（日志条数 / 录像里对上执行 / 类别 / boxedIn）==')
for lo, hi in [(0, 3000), (3000, 4284), (0, 4284), (4284, 5400), (5400, 9999)]:
    r = [d for d in D if lo <= d['t'] < hi]
    ex = [d for d in r if d.get('exec')]
    print(f'  {lo}–{hi}: 日志 {len(r)} 执行 {len(ex)}｜日志类别 {dict(Counter(d["kind"] for d in r))}｜boxedIn {dict(Counter(d["boxed"] for d in r))}｜执行类别 {dict(Counter(d["kind"] for d in ex))}')
c = defaultdict(lambda: [0, 0])
for d in D:
    if d['t'] < 4284:
        c[d['qName']][0] += 1
        c[d['qName']][1] += 1 if d.get('exec') else 0
print('  t<4284 按受赠方 日志/执行：', dict(c))
c = defaultdict(lambda: [0, 0])
for d in D:
    if d['t'] < 4284:
        c[d['bot']][0] += 1
        c[d['bot']][1] += 1 if d.get('exec') else 0
print('  t<4284 按捐出方 日志/执行：', dict(c))

print('== 2 yield_opt_dispatch：4284–5400 已执行的，按 捐出方→受赠方 ==')
m = defaultdict(lambda: [0, 0, 0])
for d in D:
    e = d.get('exec')
    if e and 4284 <= d['t'] < 5400 and d['kind'] == 'yield_opt_dispatch':
        x = m[(d['bot'], d['qName'].replace('[APEX] ', ''))]; x[0] += 1; x[1] += e['got']; x[2] += e['fee']
tot = [sum(v[i] for v in m.values()) for i in range(3)]
print(f'  合计 {tot[0]} 笔 到账 {k(tot[1])} 税 {k(tot[2])}')
print('  ' + '；'.join(f'{a}→{b} {n} 笔 {k(g)}/税 {k(f)}' for (a, b), (n, g, f) in sorted(m.items(), key=lambda x: -x[1][1])[:14]))
ring = {'alex_k', 'ryan_m', 'talon5'}
rr = [(d, d['exec']) for d in D if d.get('exec') and 4284 <= d['t'] < 5400 and d['bot'] in ring and d['qName'].replace('[APEX] ', '') in ring]
print(f'  其中 alex_k/ryan_m/talon5 三号之间：{len(rr)} 笔 到账 {k(sum(e["got"] for d, e in rr))} 税 {k(sum(e["fee"] for d, e in rr))}；决策时 dMe 中位 {sorted(d["dMe"] for d, e in rr)[len(rr)//2]}、dAlly 中位 {sorted(d["dAlly"] for d, e in rr)[len(rr)//2]}；dAlly ≥100 的 {sum(1 for d, e in rr if d["dAlly"] >= 100)} 笔')
print('  三号合计存兵：' + ' '.join(f'{t}:{k(sum(at(pid[b], t)[1] for b in ring))}' for t in (4200, 4284, 4500, 4800, 5100, 5400)))
print('  其余七号合计存兵：' + ' '.join(f'{t}:{k(sum(at(p, t)[1] for p, b in sq.items() if b not in ring))}' for t in (4200, 4284, 4500, 4800, 5100, 5400)))

print('== 3 各队 地%/兵（T30）与编队占本队兵的比例 ==')
LAND = None
for t in (3000, 3600, 4200, 4500, 4800, 4980, 5100, 5400, 5490, 5700, 6000):
    terr, bal = hs(t) if t in HS['t'] else (None, None)
    if terr is None:
        continue
    tb = defaultdict(int); tl = defaultdict(int)
    for p in range(H):
        if p in P:
            tb[P[p]['team']] += bal[p]; tl[P[p]['team']] += terr[p]
    sb = sum(bal[p] for p in sq); sl = sum(terr[p] for p in sq)
    print(f'  t={t}: ' + ' '.join(f'T{x} {tl[x]}格/{k(tb[x])}' for x in sorted(tb)) + f'｜编队 {sl}格/{k(sb)} = 本队兵的 {100*sb/max(1,tb[J["ourTeam"]]):.0f}%、本队地的 {100*sl/max(1,tl[J["ourTeam"]]):.0f}%')

print('== 4 我方队（T2）非编队队友：峰值地前 8 的离场/阵亡拍 ==')
mates = sorted([p for p in J['players'] if p['team'] == J['ourTeam'] and not p['squad'] and p['id'] < H], key=lambda p: -p['peakTerr'])[:8]
for p in mates:
    print(f"  {nm(p['id'])} 峰值 {p['peakTerr']}@{p['peakT']} 离场 {p['leftT']} 阵亡 {p['deathT']}")
alive = lambda t: sum(1 for p in J['players'] if p['team'] == J['ourTeam'] and not p['squad'] and p['id'] < H and (p['deathT'] < 0 or p['deathT'] > t))
online = lambda t: sum(1 for p in J['players'] if p['team'] == J['ourTeam'] and not p['squad'] and p['id'] < H and (p['deathT'] < 0 or p['deathT'] > t) and (p['leftT'] < 0 or p['leftT'] > t))
print('  非编队队友 存活/在线：' + ' '.join(f'{t}:{alive(t)}/{online(t)}' for t in (1500, 3000, 4200, 4800, 5400, 5700, 5900, 6000, 6100, 6200, 6300)))

print('== 5 [Void] 123(#19) 打我方号的每一条（拍、目标、比例、兵、对方当时的兵/地）==')
for e in ev:
    if e['p'] == 19 and e['type'] in ('attack', 'boat-land') and e.get('q') in sq and e.get('ok', True):
        L, B = at(e['q'], e['t'])
        print(f"  t={e['t']} → {sq[e['q']]} pct={e.get('pct')}（{100*(e.get('pct', 0)+1)/1024:.0f}% 存兵）出 {k(e.get('troops', 0))}；[Void] 当时 {k(e.get('B0', 0))}/{e.get('L0')} 格；{sq[e['q']]} 当时 {k(B)}/{L} 格")

print('== 6 我方号打 [Void] 123 的合计 ==')
m = defaultdict(lambda: [0, 0, 0, 0])
for e in ev:
    if e['p'] in sq and e['type'] == 'attack' and e.get('q') == 19 and e.get('ok', True):
        x = m[sq[e['p']]]; x[0] += 1; x[1] += e.get('troops', 0) + e.get('fee', 0); x[2] = x[2] or e['t']; x[3] = e['t']
print('  ' + '；'.join(f'{b} {n} 条 {k(v)}（{t0}–{t1}）' for b, (n, v, t0, t1) in m.items()) + f'｜合计 {sum(v[0] for v in m.values())} 条 {k(sum(v[1] for v in m.values()))}')

print('== 7 ryan_m 5400–6300 每 100 拍：地/兵/密度、落地的指令 ==')
for t in range(5400, 6400, 100):
    L, B = at(23, t)
    cm = Counter(('捐' if e['type'] == 'donate' else '船' if e['type'] == 'boat' else '打' + ('真人' if 0 <= e.get('q', -1) < H else '中立' if e.get('q') == 512 else '机')) for e in ev if e['p'] == 23 and t <= e['t'] < t + 100 and e['type'] in ('attack', 'boat', 'donate'))
    print(f'  {t}: {L}/{k(B)}/{B/max(1,L):.0f}｜{dict(cm)}')

print('== 8 手续费只为送很少兵的船（出船兵 < 10k）==')
sb = [e for e in ev if e['type'] == 'boat' and e['p'] in sq and e.get('troops', 0) < 10000]
print(f'  {len(sb)} 条：出船兵合计 {k(sum(e["troops"] for e in sb))}，手续费合计 {k(sum(e["fee"] for e in sb))}：' + ' '.join(f"{sq[e['p']]}@{e['t']}({e['troops']}兵/费{k(e['fee'])})" for e in sb))
ab = [e for e in ev if e['type'] == 'boat' and e['p'] in sq]
print(f'  全部出船 {len(ab)} 条：兵 {k(sum(e["troops"] for e in ab))}，手续费 {k(sum(e["fee"] for e in ab))}')

print('== 9 捐给 kaito9 的（5236–5698）==')
r = [x for x in ad if x[2] == 31]
print(f'  {len(r)} 笔 到账 {k(sum(x[3] for x in r))} 税 {k(sum(x[4] for x in r))}；到账 < 税 的 {sum(1 for x in r if x[3] < x[4])} 笔（到账 {k(sum(x[3] for x in r if x[3] < x[4]))} 税 {k(sum(x[4] for x in r if x[3] < x[4]))}）；首 {r[0][0]} 末 {r[-1][0]}')

print('== 10 600 拍窗口里从 中立/机器人/真人 手里拿到的地：编队 对 其余在场真人（pairAll：512=中立，600=机器人）==')
import statistics as st
for w in (0, 1, 2):
    frm = defaultdict(lambda: defaultdict(int))
    for ww, a, b, t in J['pairAll']:
        if ww != w or a >= H:
            continue
        frm['机器人' if b == 600 else '中立' if b == 512 else '真人'][a] += t
    hi = w * 600 + 599
    others = [p for p in range(H) if p not in sq and p in P and (P[p]['deathT'] < 0 or P[p]['deathT'] > hi) and (P[p]['leftT'] < 0 or P[p]['leftT'] > hi)]
    for cls in ('中立', '机器人', '真人'):
        d = frm[cls]
        s = [d.get(p, 0) for p in sq]
        o = [d.get(p, 0) for p in others]
        print(f'  {w*600}–{hi} 从{cls}：编队合计 {sum(s)}（每号中位 {st.median(s):.0f}；{" ".join(f"{b}:{d.get(p, 0)}" for p, b in sq.items())}）｜其余在场真人 {len(o)} 人合计 {sum(o)}（每人中位 {st.median(o):.0f}，上四分位 {sorted(o)[3*len(o)//4]}）｜编队拿到其中 {100*sum(s)/max(1, sum(s)+sum(o)):.1f}%，人数占 {100*10/(10+len(o)):.1f}%')

print('== 11 各队在场真人数（未阵亡且未离场）与各队最大的三个号 ==')
for t in (1500, 3000, 4200, 4800, 5400, 5700, 6000, 6300):
    terr, bal = hs(t)
    row = []
    for tm in (1, 2, 3):
        act = [p for p in range(H) if p in P and P[p]['team'] == tm and (P[p]['deathT'] < 0 or P[p]['deathT'] > t) and (P[p]['leftT'] < 0 or P[p]['leftT'] > t)]
        top = sorted(act, key=lambda p: -terr[p])[:3]
        row.append(f'T{tm} 在场 {len(act)}（' + '；'.join(f'{nm(p)} {terr[p]}格/{k(bal[p])}' for p in top) + '）')
    print(f'  t={t}: ' + ' ｜ '.join(row))

print('== 12 [Void] 123(#19) 打我方号的陆攻（录像事件表只收与我方号有关的指令）==')
va = [e for e in ev if e['p'] == 19 and e['type'] in ('attack', 'boat')]
print(f'  pct 分布：{sorted(Counter(e["pct"] for e in va if e["type"] == "attack" and e.get("q") in sq).items(), key=lambda x: -x[1])[:8]}')
vs = [e for e in va if e['type'] == 'attack' and e.get('q') in sq]
gaps = [b['t'] - a['t'] for a, b in zip(vs, vs[1:])]
print(f'  打我方号 {len(vs)} 条；相邻两条间隔 中位 {sorted(gaps)[len(gaps)//2]} 拍、最短 {min(gaps)} 拍；同拍 ≥2 条的次数 {sum(1 for g in gaps if g == 0)}')
print('  [Void] 地/兵/密度：' + ' '.join(f'{t}:{hs(t)[0][19]}/{k(hs(t)[1][19])}/{hs(t)[1][19]/max(1,hs(t)[0][19]):.0f}' for t in (600, 1500, 3000, 4200, 4800, 5400, 6000, 6300, 6600)))

print('== 13 利率表（game.js L40-41、L739-746）：每 10 拍利率（万分之）= 100 + isqrt(25600*i/508)，i = 511×地/全图陆地 ==')
iV = lambda x, y: int((x + 0.5) // y)
def isq(h):
    if h < 1:
        return 0
    x = iV(h + 1, 2)
    for _ in range(9):
        x = iV(x + iV(h, x), 2)
    return x
LANDT = 546152
rate = lambda terr: 100 + isq(iV(25600 * iV(511 * terr, LANDT), 508))
for t in (4200, 5400):
    terr, bal = hs(t)
    print(f'  t={t}: [Void] 123 {terr[19]} 格 → {rate(terr[19])}；Mittelfranken {terr[7]} 格 → {rate(terr[7])}；ryan_m {terr[23]} 格 → {rate(terr[23])}；alex_k {terr[30]} 格 → {rate(terr[30])}；其余八号 ' + ' '.join(f'{b}:{rate(terr[p])}' for p, b in sq.items() if b not in ('ryan_m', 'alex_k')))
    tot = sum(terr[p] for p in sq)
    print(f'     编队 {tot} 格如果是一个号 → {rate(tot)}；按各号存兵加权的实际表利率 {sum(rate(terr[p]) * bal[p] for p in sq) / max(1, sum(bal[p] for p in sq)):.0f}')

print('== 14 选点阵形半径（spawn-coordinator-c116-va.mjs L838、L1074-1077 的算式照抄）==')
import math
clamp = lambda v, lo, hi: max(lo, min(hi, v))
rCell = math.sqrt(max(10000, LANDT) / (math.pi * H))
minReqSep = clamp(round(0.95 * rCell), 42, 68)
r0 = clamp(round(0.48 * rCell), 28, 46)
r1 = clamp(round(1.38 * rCell), max(78, r0 + minReqSep), 132)
r2 = clamp(round(2.35 * rCell), max(142, r1 + minReqSep), 225)
print(f'  rCell = sqrt(陆地 {LANDT} / (π × 真人 {H})) = {rCell:.1f} 格（全图人均一个半径 {rCell:.0f} 格的圆 ≈ {LANDT/H:.0f} 格地；相邻两人平均间距约 {2*rCell:.0f} 格）')
print(f'  minReqSep={minReqSep} r0={r0} r1={r1} r2={r2}（三个半径都落在下限上）；通用规则的队友最小间距 allyMinSep = clamp(round(1.48×rCell),72,118) = {clamp(round(1.48*rCell), 72, 118)}')

print('== 15 没落地的调度：按日志拍 +0/7/14/21 四个试算拍的结果分类（quota = 受赠方配额不够）==')
for lo, hi in [(0, 4284), (4284, 99999)]:
    r = [d for d in D if lo <= d['t'] < hi and not d.get('exec')]
    c = Counter()
    for d in r:
        rs = [x.get('reason') for x in d['sim']]
        c['四拍全被配额拒' if all(x == 'quota' for x in rs) else '四拍全通过' if all(x == 'ok' for x in rs) else '有过有拒/其它'] += 1
    print(f'  日志拍 {lo}–{hi}: 没落地 {len(r)} 条：{dict(c)}')
ex = [d for d in D if d['t'] < 4284 and not d.get('exec') and d['sim'] and d['sim'][0].get('reason') == 'quota' and d['sim'][0].get('extra')]
over = [d for d in ex if d['sim'][0]['extra']['cost'] > d['sim'][0]['extra']['cap']]
print(f'  t<4284 被配额拒的 {len(ex)} 条里，单笔所需配额 > 受赠方配额总上限（即使一点没用过也过不了）的 {len(over)} 条；所需/上限 中位 {sorted(d["sim"][0]["extra"]["cost"] / max(1, d["sim"][0]["extra"]["cap"]) for d in ex)[len(ex)//2]:.2f}')
print('  例：' + '；'.join(f"t={d['t']} {d['bot']}→{d['qName'].replace('[APEX] ', '')} 想捐 {k(d['sim'][0]['extra']['want'])}：需 {d['sim'][0]['extra']['cost']} 点，对方已用 {d['sim'][0]['extra']['used']}/上限 {d['sim'][0]['extra']['cap']}" for d in (ex[0], ex[len(ex)//2], ex[-1])))
