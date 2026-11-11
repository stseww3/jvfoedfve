# A021_facts.py — A021 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / boat_fate.mjs / cap_clip.mjs / shadow.mjs）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A021.json 机械算出（match_truth.mjs 的逐拍重放产物）。
# 用法：python3 scripts/review_build/A021_facts.py
import json, bisect, statistics
from collections import defaultdict

M = 'A021'
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
ad = J['allDon']
HS = J['HS']
CATS = J['cats']
OUR = J['ourTeam']
LAND = J['map']['land']


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return '中立' if p == 512 else f'机器人#{p}'


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k' if abs(x) >= 1000 else str(int(x))


def at(p, t):
    s = J['S10'][str(p)]
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def hsrow(t):
    i = HS['t'].index(t)
    return HS['terr'][i], HS['bal'][i]


def flows(p, t0, t1):
    f = J['F30'][str(p)]
    i0 = bisect.bisect_right(f['t'], t0) - 1
    i1 = bisect.bisect_right(f['t'], t1) - 1
    a = f['flows'][i0] if i0 >= 0 else [0] * len(CATS)
    b = f['flows'][i1]
    return {c: b[j] - a[j] for j, c in enumerate(CATS)}


def caploss(p, t0, t1):
    f = J['F30'][str(p)]
    i0 = bisect.bisect_right(f['t'], t0) - 1
    i1 = bisect.bisect_right(f['t'], t1) - 1
    return f['capLoss'][i1] - (f['capLoss'][i0] if i0 >= 0 else 0)


def contact(p, t):
    c = J['C30'][str(p)]
    i = bisect.bisect_right(c['t'], t) - 1
    return {x: c[x][i] for x in ('neut', 'eh', 'el', 'bot', 'mateS', 'mateO')}


alive_at = lambda p, t: not (P[p]['deathT'] >= 0 and P[p]['deathT'] <= t)

print('== §1 叠点的两对号：出生点、各拍的地/兵；riku_x 触到硬上限（150×地）的拍 ==')
for a, b in (('zero_7', 'riku_x'), ('ryan_m', 'leo_tx')):
    sa, sb = P[pid[a]]['spawn'], P[pid[b]]['spawn']
    d = ((sa[0] - sb[0]) ** 2 + (sa[1] - sb[1]) ** 2) ** 0.5
    print(f'  {a}{tuple(sa)} 与 {b}{tuple(sb)} 相距 {d:.1f} 像素（引擎落点；出生指令是同一个像素，见 replay_cmds.mjs）')
    for t in (250, 600, 900, 1200, 1500, 2400):
        ta, tb = at(pid[a], t), at(pid[b], t)
        others = sorted(at(p, t)[0] for p in sq if sq[p] not in (a, b))
        print(f'    t={t} {a} {ta[0]}格/{k(ta[1])} {b} {tb[0]}格/{k(tb[1])} 两号合计 {ta[0]+tb[0]} 格｜其余 8 个号地中位 {statistics.median(others):.0f}')
s = J['S10'][str(pid['riku_x'])]
first_cap = next((t for t, L, B in zip(s['t'], s['terr'], s['bal']) if L > 0 and B >= 150 * L - 1), None)
stuck0 = next(t for t, L in zip(s['t'], s['terr']) if L == 360)
stuck1 = next(t for t, L in zip(s['t'], s['terr']) if t > stuck0 and L != 360)
print(f'  riku_x 地停在 360 格：t={stuck0} 到 t={stuck1 - 10}（{stuck1 - 10 - stuck0} 拍）；兵第一次顶到硬上限 150×360=54000 是 t={first_cap}')
n_cmd = [e for e in ev if e['p'] == pid['riku_x'] and e['type'] in ('attack', 'boat') and e['t'] > 0]
print(f"  riku_x 开局后落地的指令：t≤{stuck0} {sum(1 for e in n_cmd if e['t'] <= stuck0)} 条；{stuck0}<t<1500 {sum(1 for e in n_cmd if stuck0 < e['t'] < 1500)} 条；1500≤t<1800 {sum(1 for e in n_cmd if 1500 <= e['t'] < 1800)} 条（第一条 t={min((e['t'] for e in n_cmd if e['t'] >= 1500), default=None)}）")
print(f"  riku_x 超软上限少拿的利息（F30.capLoss）：0–1500 {k(caploss(pid['riku_x'], 0, 1500))}")

print('== §2 抢地进度：编队各号 vs 其余在场真人（HS 每 300 拍）==')
for t in (600, 900, 1200, 1500, 1800, 2400):
    terr, bal = hsrow(t)
    ours = sorted(terr[p] for p in sq)
    oth = sorted(terr[p] for p in P if p not in sq and terr[p] > 0)
    q3 = oth[int(len(oth) * 0.75)] if oth else 0
    allv = sorted((terr[p] for p in P if terr[p] > 0), reverse=True)
    ranks = sorted(allv.index(terr[p]) + 1 for p in sq)
    print(f'  t={t} 编队地 中位 {statistics.median(ours):.0f} 最小 {ours[0]} 最大 {ours[-1]} 合计 {sum(ours)}（{100*sum(ours)/LAND:.1f}%）｜其余在场真人 {len(oth)} 人 中位 {statistics.median(oth):.0f} 上四分位 {q3}｜编队各号在全场 {len(allv)} 人里的名次 {ranks[0]}–{ranks[-1]}')

print('== §3 阵内的敌人 Player 981(#44,T1) 与西侧的 Player 5(#18,T2) ==')
cx = sum(P[p]['spawn'][0] for p in sq) / 10
cy = sum(P[p]['spawn'][1] for p in sq) / 10
rmax = max(((P[p]['spawn'][0] - cx) ** 2 + (P[p]['spawn'][1] - cy) ** 2) ** 0.5 for p in sq)
for q in (44, 18):
    sp = P[q]['spawn']
    d0 = ((sp[0] - cx) ** 2 + (sp[1] - cy) ** 2) ** 0.5
    dn = min((((sp[0] - P[p]['spawn'][0]) ** 2 + (sp[1] - P[p]['spawn'][1]) ** 2) ** 0.5, sq[p]) for p in sq)
    h = {t: (HS['terr'][i][q], HS['bal'][i][q]) for i, t in enumerate(HS['t'])}
    print(f"  {nm(q)} 出生 {tuple(sp)} 离编队质心 {d0:.0f}（最远号半径 {rmax:.0f}）最近我方号 {dn[1]} {dn[0]:.0f} 像素｜阵亡 {P[q]['deathT']} 离场 {P[q]['leftT']} 峰值地 {P[q]['peakTerr']}@{P[q]['peakT']}")
    print('     每 300 拍 地/兵：' + ' '.join(f'{t}:{h[t][0]}/{k(h[t][1])}' for t in sorted(h) if 600 <= t <= 2400))
terr, bal = hsrow(1500)
five = ['zexos1', 'alex_k', 'talon5', 'sora_w', 'noah88']
print(f"  t=1500 与 Player 981 接壤的五个号存兵 " + ' '.join(f'{b}:{k(bal[pid[b]])}' for b in five) + f" 合计 {k(sum(bal[pid[b]] for b in five))}｜Player 981 {terr[44]}格/{k(bal[44])}")
terr, bal = hsrow(1800)
print(f"  t=1800 同上 " + ' '.join(f'{b}:{k(bal[pid[b]])}' for b in five) + f" 合计 {k(sum(bal[pid[b]] for b in five))}｜Player 981 {terr[44]}格/{k(bal[44])}")
got = defaultdict(lambda: [0, 0, 0])
for e in ev:
    if e['type'] == 'attack' and e.get('q') == 44 and e['p'] in sq and e['ok']:
        got[sq[e['p']]][0] += 1; got[sq[e['p']]][1] += e['troops']
first = min(e['t'] for e in ev if e['type'] == 'attack' and e.get('q') == 44 and e['p'] in sq)
last = max(e['t'] for e in ev if e['type'] == 'attack' and e.get('q') == 44 and e['p'] in sq)
for x in J['pairs']:
    if x['b'] == 44 and x['a'] in sq:
        got[sq[x['a']]][2] = x['tiles']
print(f"  我方号打 Player 981：t={first}–{last}；" + '；'.join(f'{b} {v[0]} 条 {k(v[1])} 拿地 {v[2]}' for b, v in got.items()) + f"｜合计 {sum(v[0] for v in got.values())} 条 {k(sum(v[1] for v in got.values()))} 拿地 {sum(v[2] for v in got.values())}（它峰值地 {P[44]['peakTerr']}）")
for e in ev:
    if e['type'] == 'attack' and e['p'] == 44 and e.get('q') in sq and e['t'] >= 1500:
        print(f"  t={e['t']} Player 981→{nm(e['q'])} pct={e['pct']} 出 {k(e['troops'])}（它当时兵 {k(e['B0'])} 地 {e['L0']}；对方 {k(e['tB'])}/{e['tL']}）")
r5 = [e for e in ev if e['type'] == 'attack' and e['p'] == pid['ryan_m'] and e.get('q') == 18 and e['ok']]
for t0 in sorted({e['t'] for e in r5}):
    g = [e for e in r5 if e['t'] == t0]
    print(f"  ryan_m→Player 5 t={t0}: {len(g)} 条，批前存兵 {k(g[0]['B0'])}，打出 {k(sum(e['troops'] + e['fee'] for e in g))}（{100*sum(e['troops'] + e['fee'] for e in g)/max(1, g[0]['B0']):.0f}%）；Player 5 当时 {k(g[0]['tB'])}/{g[0]['tL']} 格 密度 {g[0]['tB']/max(1, g[0]['tL']):.1f}")
x5 = next(x for x in J['pairs'] if x['a'] == pid['ryan_m'] and x['b'] == 18)
print(f"  ryan_m→Player 5 全程：投 {k(x5['sent'])}（{x5['n']} 条）拿地 {x5['tiles']} → 每格 {x5['sent']/max(1, x5['tiles']):.0f} 兵；ryan_m 地 t=1710 {at(pid['ryan_m'], 1710)[0]} → t=2000 {at(pid['ryan_m'], 2000)[0]}")

print('== §4 被队友围死：各拍「对敌接触为 0（没有敌方真人、机器人、中立邻格）」的在场我方号 ==')
for t in (1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400, 5700, 6000):
    en, op = [], []
    for p in sq:
        if not alive_at(p, t):
            continue
        c = contact(p, t)
        (en if c['eh'] + c['el'] + c['bot'] + c['neut'] == 0 else op).append(sq[p])
    terr, bal = hsrow(t)
    eb = sum(bal[pid[b]] for b in en)
    tb = sum(bal[p] for p in sq)
    print(f'  t={t} 围死 {len(en)}/{len(en)+len(op)} 个：存兵 {k(eb)}＝编队 {k(tb)} 的 {100*eb/max(1, tb):.0f}%｜有对敌接触的：' + (' '.join(f"{b}({contact(pid[b], t)['eh']}格)" for b in op) or '无'))

print('== §5 银行：超软上限少拿的利息（F30.capLoss）与密度 ==')
for t0, t1 in ((1500, 2400), (2400, 3213), (3213, 4284), (4284, 5400), (5400, 8940)):
    rows = sorted(((caploss(p, t0, t1), sq[p]) for p in sq), reverse=True)
    eco = sum(flows(p, t0, t1)['eco'] for p in sq)
    tot = sum(v for v, _ in rows)
    print(f'  {t0}–{t1}: 合计 {k(tot)}（同期利息地租 {k(eco)}，少拿的相当于它的 {100*tot/max(1, eco):.0f}%）｜' + ' '.join(f'{b} {k(v)}' for v, b in rows if v > 20000))
for t in (2400, 3000, 3210, 3600, 4200, 4260):
    row = [(sq[p], at(p, t)) for p in sq]
    dens = sorted(((B / max(1, L)), b) for b, (L, B) in row)
    print(f'  t={t} 各号密度：' + ' '.join(f'{b}:{d:.0f}' for d, b in dens) + f"｜编队 {sum(L for _, (L, B) in row)} 格/{k(sum(B for _, (L, B) in row))} 密度 {sum(B for _, (L, B) in row)/sum(L for _, (L, B) in row):.0f}")

print('== §6 调度日志 vs 落地（J.dispatch）==')
for t0, t1 in ((1500, 3213), (3213, 4284), (4284, 99999)):
    d = [x for x in J['dispatch'] if t0 <= x['t'] < t1]
    ex = [x for x in d if x['exec']]
    rej = [x for x in d if not x['exec'] and all(s['reason'] == 'quota' for s in x['sim'])]
    byq = defaultdict(lambda: [0, 0])
    for x in d:
        byq[sq.get(x['q'], x['qName'])][0] += 1
        byq[sq.get(x['q'], x['qName'])][1] += 1 if x['exec'] else 0
    print(f"  {t0}–{t1}: 日志 {len(d)} 条，落地 {len(ex)}（到账 {k(sum(x['exec']['got'] for x in ex))} 税 {k(sum(x['exec']['fee'] for x in ex))}），四个试算拍全被配额拒 {len(rej)}｜按受赠方 日志/落地：" + ' '.join(f'{b} {v[0]}/{v[1]}' for b, v in sorted(byq.items(), key=lambda z: -z[1][0])))
want = sum(x['sim'][0]['extra']['want'] for x in J['dispatch'] if x['t'] < 3213 and not x['exec'] and (x['sim'][0].get('extra') or {}).get('want'))
print(f"  t<3213 没落地的日志调度「想捐」合计 {k(want)}（同一意图逐拍重发，含重复）")
d0 = [x for x in J['dispatch'] if x['t'] < 3213]
days = sorted({(x['bot'], x['t'] // 300) for x in d0 if not x['exec']})
print(f"  t<3213 没落地的调度涉及 {len({b for b, _ in days})} 个捐出方、{len(days)} 个（号×300 拍窗）")
for b in ('ryan_m', 'noah88', 'zexos1', 'kaito9', 'leo_tx', 'sora_w', 'talon5', 'alex_k'):
    s = J['S10'][str(pid[b])]
    i = bisect.bisect_right(s['t'], 3210) - 1
    j = bisect.bisect_right(s['t'], 4280) - 1
    print(f"  {b} 已用配额点：t=3210 {s['quota'][i]}（地 {s['terr'][i]}），t=4280 {s['quota'][j]}")

print('== §7 3213–4284：zexos1 收到的捐兵、同拍连发、被打 ==')
z = pid['zexos1']
din = [e for e in ev if e['type'] == 'donate' and e['q'] == z and 3213 <= e['t'] < 4284]
print(f"  收到 {len(din)} 笔 到账 {k(sum(e['got'] for e in din))} 税 {k(sum(e['fee'] for e in din))}：" + ' '.join(f"{e['t']}:{sq[e['p']]} {k(e['got'])}" for e in din))
dout = [e for e in ev if e['type'] == 'donate' and e['p'] == z and 3213 <= e['t'] < 4284]
print(f"  捐出 {len(dout)} 笔：" + ' '.join(f"{e['t']}→{nm(e['q'])} {k(e['got'])}（税 {k(e['fee'])}）" for e in dout))
for t0 in (3731, 3787):
    g = [e for e in ev if e['type'] == 'attack' and e['p'] == z and e['t'] == t0]
    by = defaultdict(lambda: [0, 0, 0, 0])
    for e in g:
        by[e['q']][0] += 1; by[e['q']][1] += e['troops']; by[e['q']][2] = e['tB']; by[e['q']][3] = e['tL']
    print(f"  t={t0} 同拍 {len(g)} 条，批前存兵 {k(g[0]['B0'])}，打出 {k(sum(e['troops'] + e['fee'] for e in g))}（{100*sum(e['troops'] + e['fee'] for e in g)/g[0]['B0']:.0f}%）：" + '；'.join(f"{nm(q)} {v[0]} 条 {k(v[1])}（对方当时 兵 {v[2]} 地 {v[3]}，按每格 2 兵全吃只要 {k(2*v[3])}）" for q, v in by.items()))
f = flows(z, 3700, 3900)
print(f"  zexos1 3700–3900 收支：" + ' '.join(f'{c} {k(v)}' for c, v in f.items() if v))
for e in ev:
    if e['type'] == 'attack' and e.get('q') == z and 3700 <= e['t'] <= 3900 and e['troops'] > 1000:
        print(f"  t={e['t']} {nm(e['p'])}→zexos1 pct={e['pct']} 出 {k(e['troops'])}（它 {k(e['B0'])}/{e['L0']} 格；zexos1 {k(e['tB'])}/{e['tL']}）")
print(f"  zexos1 地 t=3300 {at(z, 3300)[0]} → t=4260 {at(z, 4260)[0]}；兵 {k(at(z, 3300)[1])} → {k(at(z, 4260)[1])}（硬上限 150×{at(z, 4260)[0]}={k(150*at(z, 4260)[0])}）")

print('== §8 4284–5400：灌给 ryan_m / noah88；ryan_m 的出兵去向；后排密度 ==')
for b in ('ryan_m', 'noah88'):
    for t0, t1 in ((4284, 5400), (5400, 6000), (6000, 8940)):
        d = [e for e in ev if e['type'] == 'donate' and e['q'] == pid[b] and t0 <= e['t'] < t1]
        if d:
            kinds = defaultdict(int)
            for e in d:
                kinds[e.get('logKind') or '?'] += 1
            print(f"  {b} {t0}–{t1} 收到 {len(d)} 笔 到账 {k(sum(e['got'] for e in d))} 税 {k(sum(e['fee'] for e in d))}（税/到账 {100*sum(e['fee'] for e in d)/sum(e['got'] for e in d):.0f}%）｜类别 {dict(kinds)}")
r = pid['ryan_m']
by = defaultdict(lambda: [0, 0])
for e in ev:
    if e['type'] == 'attack' and e['p'] == r and 4284 <= e['t'] < 5400 and e['ok']:
        by[e['q']][0] += 1; by[e['q']][1] += e['troops']
til = defaultdict(int)
for x in J['pairsW']:
    if x["a"] == r and 43 <= x["w"] <= 54:
        til[x['b']] += x['tiles']
print('  ryan_m 4284–5400 出兵（拿地按 4300–5499 的 100 拍窗）：' + '；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])} 拿地 {til.get(q, 0)}' for q, v in sorted(by.items(), key=lambda z: -z[1][1])) + f"｜合计 {sum(v[0] for v in by.values())} 条 {k(sum(v[1] for v in by.values()))}，目标 {len(by)} 个")
f = flows(r, 4284, 5400)
print('  ryan_m 4284–5400 收支：' + ' '.join(f'{c} {k(v)}' for c, v in f.items() if v) + f"｜地 {at(r, 4284)[0]} → 峰值 {P[r]['peakTerr']}@{P[r]['peakT']} → t=5400 {at(r, 5400)[0]}")
tot = {c: sum(flows(p, 4284, 5400)[c] for p in sq) for c in CATS}
tax = sum(e['fee'] for e in ev if e['type'] == 'donate' and e['p'] in sq and 4284 <= e['t'] < 5400)
print(f"  编队 4284–5400：利息地租 {k(tot['eco'])}，捐出 {k(-tot['donOut'])}（其中税 {k(tax)}＝利息的 {100*tax/tot['eco']:.0f}%），打真人 {k(-tot['atkHuman'])}，被打掉 {k(-tot['dmg'])}")
rear = ['zexos1', 'alex_k', 'talon5', 'sora_w', 'kaito9', 'leo_tx', 'zero_7', 'riku_x']
for t in (4260, 4500, 4800, 5100, 5400, 5580):
    row = [(b, at(pid[b], t)) for b in rear]
    terr, bal = (None, None)
    print(f'  t={t} 后排 8 个号密度：' + ' '.join(f'{b}:{B/max(1, L):.0f}' for b, (L, B) in row) + f"｜合计 {sum(L for _, (L, B) in row)} 格/{k(sum(B for _, (L, B) in row))} 密度 {sum(B for _, (L, B) in row)/sum(L for _, (L, B) in row):.0f}")
imp = defaultdict(list)
for x in J['dispatch']:
    if x['exec'] and 4284 <= x['t'] < 6100 and x['boxed']:
        L = x['sim'][0]['L']
        imp[x['kind']].append(x['myBal'] * (1 - x['pct'] / 1024) / max(1, L))
for kd, v in imp.items():
    v.sort()
    print(f"  已落地的调度（boxedIn=true，4284–6100）{kd} {len(v)} 笔：决策时「捐后剩兵÷地」中位 {statistics.median(v):.0f}、最小 {v[0]:.0f}、最大 {v[-1]:.0f}（未扣 6.25% 税）")
enemy = [p for p in P if p not in sq and P[p]['team'] != OUR]
for t in (4800, 5400):
    terr, bal = hsrow(t)
    ed = sorted(bal[p] / terr[p] for p in enemy if terr[p] >= 3000)
    rd = sorted(bal[pid[b]] / terr[pid[b]] for b in rear)
    print(f'  t={t} 在场敌方真人（地≥3000）{len(ed)} 人 密度中位 {statistics.median(ed):.0f}｜后排 8 号密度中位 {statistics.median(rd):.0f}｜后排合计占图 {100*sum(terr[pid[b]] for b in rear)/LAND:.1f}%')

print('== §9 5089–6011：谁打了 ryan_m；395 的登陆；三个号的阵亡 ==')
by = defaultdict(lambda: [0, 0, 9e9, 0])
for e in ev:
    if e['t'] < 5000 or e['t'] > 6011:
        continue
    if e['type'] == 'attack' and e.get('q') == r and e['ok'] and e['troops'] > 100:
        v = by[e['p']]; v[0] += 1; v[1] += e['troops']; v[2] = min(v[2], e['t']); v[3] = max(v[3], e['t'])
    if e['type'] == 'boat-land' and e.get('q') == r:
        v = by[e['p']]; v[0] += 1; v[1] += e['troops']; v[2] = min(v[2], e['t']); v[3] = max(v[3], e['t'])
print('  5000–5992 打 ryan_m：' + '；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])}（{v[2]}–{v[3]}）' for q, v in sorted(by.items(), key=lambda z: -z[1][1])) + f"｜合计 {k(sum(v[1] for v in by.values()))}")
own = [e for e in ev if e['type'] == 'attack' and e['p'] == r and e['t'] >= 5235]
print(f"  ryan_m 峰值（t=5235）之后自己的陆攻：{len(own)} 条 {k(sum(e['troops'] for e in own))}，最后一条 t={max((e['t'] for e in own), default=None)}；阵亡前 300 拍 存兵 {k(at(r, 5690)[1])}→{k(at(r, 5990)[1])}，地 {at(r, 5690)[0]}→{at(r, 5990)[0]}")
e823 = [e for e in ev if e['type'] == 'attack' and e['p'] == 31 and e.get('q') == r and e['pct'] >= 900 and e['troops'] > 10000]
for e in e823:
    print(f"  t={e['t']} Player 823→ryan_m pct={e['pct']} 出 {k(e['troops'])}（它 {k(e['B0'])}/{e['L0']} 格；ryan_m {k(e['tB'])}/{e['tL']}）")
for e in ev:
    if e['p'] == 35 and e.get('q') in sq and 5000 <= e['t'] <= 6011 and e['type'] in ('attack', 'boat-land') and e['troops'] > 1000:
        L, B = at(e['q'], e['t'] - 10)
        print(f"  t={e['t']} Player 395 {'登陆' if e['type'] == 'boat-land' else '陆攻'}→{nm(e['q'])} {k(e['troops'])}（对方此前 {L}格/{k(B)} 密度 {B/max(1, L):.0f}；{e['troops']/max(1, B):.2f}×对方存兵）")
h395 = {t: (HS['terr'][i][35], HS['bal'][i][35]) for i, t in enumerate(HS['t'])}
print('  Player 395 每 300 拍 地/兵：' + ' '.join(f'{t}:{h395[t][0]}/{k(h395[t][1])}' for t in sorted(h395) if 4800 <= t <= 8700))
from395 = defaultdict(int)
for w, a, b, tiles in J['pairAll']:
    if a == 35 and b in sq:
        from395[(w, sq[b])] += tiles
ws = sorted({w for w, _ in from395})
for w in ws:
    print(f"  Player 395 在 {w*600}–{w*600+599} 从我方号手里拿地：" + ' '.join(f'{b} {v}' for (w2, b), v in from395.items() if w2 == w) + f"｜合计 {sum(v for (w2, b), v in from395.items() if w2 == w)}")
for b, t0, t1 in (('zexos1', 5630, 5710), ('talon5', 5620, 5630)):
    d = [e for e in ev if e['type'] == 'donate' and e['p'] == pid[b] and t0 <= e['t'] <= t1]
    print(f"  {b} 在 {t0}–{t1} 捐出 {len(d)} 笔：" + ' '.join(f"{e['t']}→{nm(e['q'])} 到账 {k(e['got'])} 税 {k(e['fee'])}（捐前 {k(e['B0'])}/{e['L0']} 格）" for e in d) + f"｜合计流出 {k(sum(e['got'] + e['fee'] for e in d))}")
for t in (5400, 6000):
    terr, bal = hsrow(t)
    print(f"  t={t} 编队 {sum(terr[p] for p in sq)} 格（{100*sum(terr[p] for p in sq)/LAND:.1f}%）/{k(sum(bal[p] for p in sq))}；本队 T{OUR} {sum(terr[p] for p in P if P[p]['team'] == OUR)} 格")

print('== §10 6000–8490：noah88 ==')
n = pid['noah88']
for q, t0, t1 in ((27, 6000, 7800), (35, 7800, 8000)):
    g = [e for e in ev if e['type'] == 'attack' and e['p'] == n and e.get('q') == q and t0 <= e['t'] < t1 and e['ok']]
    til = sum(x['tiles'] for x in J['pairsW'] if x['a'] == n and x['b'] == q and t0 // 100 <= x['w'] < t1 // 100)
    print(f"  noah88→{nm(q)} {t0}–{t1}: {len(g)} 条 {k(sum(e['troops'] for e in g))} 拿地 {til}（每格 {sum(e['troops'] for e in g)/max(1, til):.0f} 兵）")
g = [e for e in ev if e['type'] == 'attack' and e['p'] == n and e['t'] == 7819]
print(f"  t=7819 同拍 {len(g)} 条，批前 {k(g[0]['B0'])}/{g[0]['L0']} 格（密度 {g[0]['B0']/g[0]['L0']:.0f}），打出 {k(sum(e['troops'] + e['fee'] for e in g))}（{100*sum(e['troops'] + e['fee'] for e in g)/g[0]['B0']:.0f}%）；Player 395 当时 {k(g[0]['tB'])}/{g[0]['tL']} 格（密度 {g[0]['tB']/g[0]['tL']:.0f}，存兵是 noah88 的 {g[0]['tB']/g[0]['B0']:.1f} 倍）")
for e in ev:
    if e['p'] == 35 and e.get('q') in sq and e['t'] > 6100 and e['type'] in ('attack', 'boat-land') and e['troops'] > 1000:
        L, B = at(e['q'], e['t'] - 10)
        print(f"  t={e['t']} Player 395 {'登陆' if e['type'] == 'boat-land' else '陆攻'}→{nm(e['q'])} {k(e['troops'])}（pct={e.get('pct')}；对方此前 {L}格/{k(B)} 密度 {B/max(1, L):.0f}；{e['troops']/max(1, B):.2f}×对方存兵）")
for b in ('alex_k',):
    a = pid[b]
    g = [e for e in ev if e['p'] == 35 and e.get('q') == a]
    c = contact(a, 7200)
    print(f"  Player 395 全程对 {b} 的陆攻/登陆：{len(g)} 条（{b} 与它的接触 t=7200 {c['eh']} 格）；{b} 对它：" + ' '.join(f"{e['t']}:{e['type']} {k(e['troops'])}" for e in ev if e['p'] == a and e.get('q') == 35 and e['type'] in ('attack', 'boat-land')))
din = [e for e in ev if e['type'] == 'donate' and e['q'] == n and 7600 <= e['t'] < 7830]
print(f"  noah88 7600–7830 收到 {len(din)} 笔 {k(sum(e['got'] for e in din))}；7740–7830 收支：" + ' '.join(f'{c} {k(v)}' for c, v in flows(n, 7740, 7830).items() if v))
print(f"  noah88 密度：" + ' '.join(f"{t}:{at(n, t)[1]/max(1, at(n, t)[0]):.0f}" for t in (7560, 7620, 7680, 7700, 7740, 7800, 7810, 7830, 7980)))

print('== §11 全程汇总 ==')
tot = {c: sum(flows(p, 0, 8940)[c] for p in sq) for c in CATS}
tax = sum(e['fee'] for e in ev if e['type'] == 'donate' and e['p'] in sq)
print('  编队全程：' + ' '.join(f'{c} {k(v)}' for c, v in tot.items() if v) + f"｜捐兵税 {k(tax)}＝利息地租的 {100*tax/tot['eco']:.1f}%；打真人 {k(-tot['atkHuman'])}＝利息地租的 {100*-tot['atkHuman']/tot['eco']:.0f}%")
for b in ('ryan_m', 'noah88'):
    p = pid[b]
    fl = dict(zip(CATS, P[p]['flows']))
    print(f"  {b}: 利息地租 {k(fl['eco'])} 收捐 {k(fl['donIn'])} 打真人 {k(-fl['atkHuman'])} 被打掉 {k(-fl['dmg'])}；打真人拿地 {P[p]['tilesH']}，被拿走 {P[p]['tilesLost']}；编队全部打真人支出里它占 {100*fl['atkHuman']/tot['atkHuman']:.0f}%")
hum = sum(P[p]['tilesH'] for p in sq)
print(f"  编队全程从真人手里拿地 {hum} 格（ryan_m+noah88 {P[pid['ryan_m']]['tilesH'] + P[pid['noah88']]['tilesH']}），被拿走 {sum(P[p]['tilesLost'] for p in sq)} 格")
T = J['T30']
i = max(range(len(T['t'])), key=lambda j: T['land'][j][OUR])
print(f"  本队 T{OUR} 峰值占图 {100*T['land'][i][OUR]/LAND:.1f}%@{T['t'][i]}（T30；land 列 = [无队, T1, T2, T3]）；编队峰值 {100*max(T['squadLand'])/LAND:.1f}%@{T['t'][max(range(len(T['t'])), key=lambda j: T['squadLand'][j])]}")
for t in (5250, 5490, 6000):
    j = T['t'].index(t)
    print(f"  t={t} T1 {100*T['land'][j][1]/LAND:.1f}% T2 {100*T['land'][j][2]/LAND:.1f}% T3 {100*T['land'][j][3]/LAND:.1f}%｜编队 {100*T['squadLand'][j]/LAND:.1f}%")
mates = [(P[p]['peakTerr'], P[p]['name'], P[p]['leftT'], P[p]['deathT']) for p in P if p not in sq and P[p]['team'] == OUR]
print('  路人队友（峰值地/离场/阵亡）：' + '；'.join(f'{n_[:14]} {a}/{b}/{c}' for a, n_, b, c in sorted(mates, reverse=True)))

print('== §12 「兵在外面时被补满」：进攻兵退回时被硬上限吃掉的两次（吃掉的数量见 cap_clip.mjs）==')
for b, t0, t1 in (('zexos1', 3731, 3822), ('ryan_m', 4361, 4401)):
    p = pid[b]
    d = [e for e in ev if e['type'] == 'donate' and e['q'] == p and t0 <= e['t'] <= t1]
    s = J['S10'][str(p)]
    rows = [(t, L, B, o) for t, L, B, o in zip(s['t'], s['terr'], s['bal'], s['out']) if t0 - 10 <= t <= t1 + 10]
    print(f"  {b} {t0}–{t1}（兵在外面的时段）收到 {len(d)} 笔 到账 {k(sum(e['got'] for e in d))} 税 {k(sum(e['fee'] for e in d))}：" + ' '.join(f"{e['t']}:{sq[e['p']]} {k(e['got'])}({(e.get('logKind') or '?')[:3]})" for e in d))
    print('     每 10 拍 地/存兵/在外的进攻兵/（存兵+在外）÷地/硬上限：' + ' '.join(f"{t}:{L}/{k(B)}/{k(o)}/{(B+o)/L:.0f}/{k(150*L)}" for t, L, B, o in rows))
for x in J['dispatch']:
    if x['q'] == pid['zexos1'] and 3730 <= x['t'] <= 3830 and x['exec']:
        print(f"     调度日志 t={x['t']} {x['bot']}→zexos1 {x['kind']} pct={x['pct']} 捐出方密度 {x['dMe']} 日志里的受赠方密度 dAlly={x['dAlly']} → 落地 t={x['exec']['t']} 到账 {k(x['exec']['got'])}")

print('== §13 存兵 >100×地（over=true）时落地的打真人指令 ==')
ov = defaultdict(lambda: [0, 0, set()])
tot_h = [0, 0]
for e in ev:
    if e['type'] == 'attack' and e['p'] in sq and e['ok'] and e.get('q') in P and e['q'] not in sq:
        tot_h[0] += 1; tot_h[1] += e['troops']
        if e['B0'] > 100 * e['L0']:
            v = ov[sq[e['p']]]; v[0] += 1; v[1] += e['troops']; v[2].add(nm(e['q']))
print(f"  全程打真人指令 {tot_h[0]} 条 {k(tot_h[1])}；其中发出当拍存兵 >100×地 的 {sum(v[0] for v in ov.values())} 条 {k(sum(v[1] for v in ov.values()))}：" + '；'.join(f"{b} {v[0]} 条 {k(v[1])} → {'、'.join(sorted(v[2]))}" for b, v in sorted(ov.items(), key=lambda z: -z[1][1])))

print('== §14 转手：noah88 收捐与捐出（4284–5400）==')
n = pid['noah88']
for e in ev:
    if e['type'] == 'donate' and (e['p'] == n or e['q'] == n) and 4284 <= e['t'] < 5400:
        print(f"  t={e['t']} {nm(e['p'])}→{nm(e['q'])} 到账 {k(e['got'])} 税 {k(e['fee'])} {e.get('logKind')}（捐出方捐前 {k(e['B0'])}/{e['L0']} 格 密度 {e['B0']/max(1, e['L0']):.0f}；受赠方 {k(e['qB0'])}/{e['qL0']} 格 密度 {e['qB0']/max(1, e['qL0']):.0f}）")
o = [e for e in ev if e['type'] == 'donate' and e['p'] == n]
i_ = [e for e in ev if e['type'] == 'donate' and e['q'] == n and 4284 <= e['t'] < 5400]
print(f"  noah88 全程捐出 {len(o)} 笔 到账 {k(sum(e['got'] for e in o))} 税 {k(sum(e['fee'] for e in o))}（全部给 {', '.join(sorted({nm(e['q']) for e in o}))}）；同期 4284–5400 它收到 {len(i_)} 笔 {k(sum(e['got'] for e in i_))}（捐出方付税 {k(sum(e['fee'] for e in i_))}）")
by = defaultdict(lambda: [0, 0])
for e in ev:
    if e['type'] == 'attack' and e['p'] == n and 4284 <= e['t'] < 5400 and e['ok']:
        by[e['q']][0] += 1; by[e['q']][1] += e['troops']
print('  noah88 4284–5400 自己出兵：' + ('；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])}' for q, v in by.items()) or '无') + f"｜地 {at(n, 4284)[0]} → {at(n, 5400)[0]}，密度 {at(n, 4284)[1]/at(n, 4284)[0]:.0f} → {at(n, 5400)[1]/at(n, 5400)[0]:.0f}")

print('== §15 5400–6000 与 7800–8700 的队伍账 ==')
T = J['T30']
def tl(t):
    j = T['t'].index(t)
    return T['land'][j][OUR], T['squadLand'][j]
for a, b in ((5400, 6000), (6000, 7800), (7800, 8700)):
    (ta, sa), (tb, sb) = tl(a), tl(b)
    print(f"  {a}→{b}: 本队 {ta}→{tb}（{tb-ta:+d}），其中编队 {sa}→{sb}（{sb-sa:+d}），路人 {ta-sa}→{tb-sb}（{(tb-sb)-(ta-sa):+d}）")
for e in ev:
    if e['type'] in ('died', 'leave') and e['p'] in P and P[e['p']]['team'] == OUR and e['p'] not in sq and e['t'] > 5000:
        print(f"  路人队友 {nm(e['p'])} {e['type']} t={e['t']}" + (f" 当时 {e.get('L0')}格/{k(e.get('B0', 0))}" if e['type'] == 'leave' else ''))
tm = defaultdict(int)
for p in P:
    if P[p]['team'] != OUR and alive_at(p, 6000) and not (0 <= P[p]['leftT'] <= 6000):
        tm[P[p]['team']] += 1
print(f"  t=6000 在场敌方真人：" + ' '.join(f'T{t_} {n_} 人' for t_, n_ in sorted(tm.items())))
