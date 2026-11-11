# A095_facts.py — A095 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / boat_fate.mjs / cap_clip.mjs /
# shadow.mjs / shadow_spawn.mjs / whatif_*.mjs / donprobe_*.py）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A095.json 机械算出（match_truth.mjs 的逐拍重放产物）；出生指令读 replay_cmds.mjs 导出的 TSV。
# 用法：python3 scripts/review_build/A095_facts.py   （TSV 不在时先跑 node scripts/replay_cmds.mjs A095 --out /tmp/c136-r05/work/A095-cmds.tsv）
import json, bisect, statistics, os
from collections import defaultdict, Counter

M = 'A095'
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
HS = J['HS']
CATS = J['cats']
OUR = J['ourTeam']
LAND = J['map']['land']
W = J['map'].get('W', 1756)


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return '中立' if p == 512 else ('机器人' if p == 600 else f'机器人#{p}')


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


def alive_at(p, t):
    return not (P[p]['deathT'] >= 0 and P[p]['deathT'] <= t)


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def taken(taker_set, victim_set, w0, w1):
    """pairAll 里 w600 ∈ [w0, w1) 的窗口内，taker_set 从 victim_set 手里拿走的像素。"""
    n = 0
    for w, a, v, tiles in J['pairAll']:
        if w0 <= w < w1 and a in taker_set and v in victim_set:
            n += tiles
    return n


humans = [p for p in P if p < J.get('H', 68) or True]
enemy_h = [p for p in P if p not in sq and P[p]['team'] != OUR]

print('== §1 出生：最后一条出生指令的拍、最终阵形、阵边上的别家号 ==')
cx = sum(P[p]['spawn'][0] for p in sq) / 10
cy = sum(P[p]['spawn'][1] for p in sq) / 10
rmax = max(dist(P[p]['spawn'], (cx, cy)) for p in sq)
nn = sorted(min(dist(P[p]['spawn'], P[q]['spawn']) for q in sq if q != p) for p in sq)
print(f'  编队质心 ({cx:.0f},{cy:.0f})，最远号半径 {rmax:.0f} 像素；最近队友距离 最小 {nn[0]:.0f} 中位 {statistics.median(nn):.0f} 最大 {nn[-1]:.0f}')
tsv = f'/tmp/c136-r05/work/{M}-cmds.tsv'
last_spawn = {}
spawn_hist = defaultdict(list)
if os.path.exists(tsv):
    for line in open(tsv, encoding='utf-8'):
        f = line.rstrip('\n').split('\t')
        if len(f) < 6 or f[2] != 'spawn' and f[1] != '0':
            continue
        try:
            t, cid, pl, a = int(f[0]), int(f[1]), int(f[3]), int(f[5])
        except ValueError:
            continue
        if cid != 0:
            continue
        spawn_hist[pl].append((t, a % W, a // W))
        last_spawn[pl] = t
    ours_last = sorted(last_spawn[p] for p in sq if p in last_spawn)
    print(f'  我方号最后一条出生指令的拍：{Counter(ours_last).most_common()}（选点期 −51…−1）')
    cnt_tr = []
    for t in (-48, -40, -30, -19, -14, -7, -6, -5, -1):
        pts = []
        for p in sq:
            h = [x for x in spawn_hist[p] if x[0] <= t]
            if h:
                pts.append(h[-1][1:])
        if pts:
            cnt_tr.append(f'{t}:({sum(x for x, _ in pts)/len(pts):.0f},{sum(y for _, y in pts)/len(pts):.0f})×{len(pts)}')
    print('  编队质心随选点拍：' + ' '.join(cnt_tr))
    placed = lambda t: sum(1 for p in spawn_hist if p not in sq and spawn_hist[p][0][0] <= t)
    print('  已落点的其他真人数：' + ' '.join(f'{t}:{placed(t)}' for t in (-30, -19, -14, -9, -8, -7, -6, -5, -1)) + '（协调器 rCell = round(sqrt(陆地/(π×(我方 10 + 已落点其他真人)))) ，L838）')
rows = []
for q in P:
    if q in sq or P[q]['spawn'] is None:
        continue
    d0 = dist(P[q]['spawn'], (cx, cy))
    dn = min((dist(P[q]['spawn'], P[p]['spawn']), sq[p]) for p in sq)
    if dn[0] <= 100:
        rows.append((dn[0], q, d0, dn[1]))
for dn, q, d0, b in sorted(rows):
    h = spawn_hist.get(q, [])
    hist = ' → '.join(f'{t}:({x},{y})' for t, x, y in h[-3:])
    inside = '阵内' if d0 <= rmax else ''
    print(f"  {nm(q)} 出生 {tuple(P[q]['spawn'])} 离最近我方号 {b} {dn:.0f} 像素，离质心 {d0:.0f} {inside}｜出生指令 {hist}｜峰值地 {P[q]['peakTerr']}@{P[q]['peakT']} 离场 {P[q]['leftT']} 阵亡 {P[q]['deathT']}")
before = [(q, last_spawn.get(q)) for dn, q, d0, b in rows if d0 <= rmax and last_spawn.get(q) is not None and last_spawn[q] < max(ours_last)] if os.path.exists(tsv) else []
print(f"  SP-ENEMY-INSIDE 口径（阵内、且最后一条出生指令早于我方最后一条）：{[(nm(q), t) for q, t in before]}")

print('== §2 抢地进度：编队各号 vs 其余在场真人（HS 每 300 拍）==')
for t in (300, 600, 900, 1200, 1500, 1800, 2400, 3000):
    terr, bal = hsrow(t)
    ours = sorted(terr[p] for p in sq if terr[p] > 0)
    oth = sorted(terr[p] for p in P if p not in sq and terr[p] > 0 and (P[p]['leftT'] < 0 or P[p]['leftT'] > t))
    q3 = oth[int(len(oth) * 0.75)] if oth else 0
    ob = [bal[p] / max(1, terr[p]) for p in sq if terr[p] > 0]
    hb = [bal[p] / max(1, terr[p]) for p in P if p not in sq and terr[p] > 0 and (P[p]['leftT'] < 0 or P[p]['leftT'] > t)]
    print(f'  t={t} 编队 {len(ours)} 号 地中位 {statistics.median(ours):.0f} 最小 {ours[0]} 最大 {ours[-1]} 合计 {sum(ours)}（{100*sum(ours)/LAND:.1f}%）密度中位 {statistics.median(ob):.1f}｜其余在场真人 {len(oth)} 人 地中位 {statistics.median(oth):.0f} 上四分位 {q3} 密度中位 {statistics.median(hb):.1f}')
S = set(sq)
others = {p for p in P if p not in sq}
for w0, w1, lab in ((0, 1, '0–599'), (1, 2, '600–1199'), (2, 3, '1200–1799')):
    bot_all = taken(S | others, {600}, w0, w1)
    neu_all = taken(S | others, {512}, w0, w1)
    sb, sn = taken(S, {600}, w0, w1), taken(S, {512}, w0, w1)
    sh = taken(S, others, w0, w1)
    per = sorted(taken({p}, {600}, w0, w1) for p in sq)
    oper = sorted(taken({p}, {600}, w0, w1) for p in others if hsrow(w0 * 600 + 300)[0][p] > 0)
    print(f'  {lab}: 机器人丢的地 {bot_all}，编队拿到 {sb}（{100*sb/max(1, bot_all):.1f}%；编队占在场真人 {10}/{10+len(oper)} = {1000/(10+len(oper)):.1f}%）；中立 {neu_all} 里编队 {sn}（{100*sn/max(1, neu_all):.1f}%）；编队从真人手里 {sh}｜每号从机器人拿到：编队中位 {statistics.median(per):.0f}，其余真人中位 {statistics.median(oper):.0f} 上四分位 {oper[int(len(oper)*0.75)]}')
print('  600–1199 每号从机器人拿到的地：' + ' '.join(f'{sq[p]}:{taken({p}, {600}, 1, 2)}' for p in sorted(sq, key=lambda p: -taken({p}, {600}, 1, 2))))
nbrs = sorted(((taken({q}, {600}, 1, 2), q) for q in others), reverse=True)[:8]
print('  同期拿得最多的 8 个别家号：' + ' '.join(f'{nm(q)}:{v}' for v, q in nbrs))

print('== §3 围死与存兵：各拍「对敌接触为 0」的在场我方号 ==')
for t in (810, 1200, 1290, 1500, 1600, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500):
    en, op = [], []
    for p in sq:
        if not alive_at(p, t):
            continue
        c = contact(p, t)
        (en if c['eh'] + c['el'] + c['bot'] + c['neut'] == 0 else op).append(sq[p])
    eb = sum(at(pid[b], t)[1] for b in en)
    tb = sum(at(p, t)[1] for p in sq if alive_at(p, t))
    print(f'  t={t} 围死 {len(en)}/{len(en)+len(op)} 个（{" ".join(en)}）：存兵 {k(eb)}＝编队 {k(tb)} 的 {100*eb/max(1, tb):.0f}%｜有接触的：' + (' '.join(f"{b}({contact(pid[b], t)['eh']}敌/{contact(pid[b], t)['bot']}机)" for b in op) or '无'))
for t in (1500, 1600, 1800, 2100):
    row = sorted(((at(p, t)[1] / max(1, at(p, t)[0])), sq[p], at(p, t)) for p in sq if alive_at(p, t))
    print(f'  t={t} 各号 密度(地/兵)：' + ' '.join(f'{b}:{d:.0f}({L}/{k(B)})' for d, b, (L, B) in row))
print('  超软上限少拿的利息（F30.capLoss）：' + ' '.join(f'{sq[p]}:{k(caploss(p, 0, 99999))}' for p in sorted(sq, key=lambda p: -caploss(p, 0, 99999)) if caploss(p, 0, 99999) > 5000) + f"｜合计 {k(sum(caploss(p, 0, 99999) for p in sq))}")
L = pid['leo_tx']
s = J['S10'][str(L)]
t_same0 = next(t for t, x in zip(s['t'], s['terr']) if x == 2768)
t_same1 = next(t for t, x in zip(s['t'], s['terr']) if t > t_same0 and x != 2768)
mx = max((b, t) for t, b in zip(s['t'], s['bal']) if t_same0 <= t < t_same1)
print(f"  leo_tx 地停在 2768 格：t={t_same0}–{t_same1 - 10}（{t_same1 - 10 - t_same0} 拍）；期间存兵最高 {k(mx[0])}@{mx[1]}（密度 {mx[0]/2768:.0f}）；期间落地指令 {sum(1 for e in ev if e['p'] == L and t_same0 <= e['t'] < t_same1 and e['type'] in ('attack', 'boat', 'donate') and e.get('ok'))} 条，被拒的捐兵 {sum(1 for e in ev if e['p'] == L and t_same0 <= e['t'] < t_same1 and e['type'] == 'donate' and not e.get('ok'))} 条")

print('== §4 1500 拍的两批：kaito9 1533/1540，zexos1 1554 ==')
for b, ticks in (('kaito9', (1533, 1540)), ('zexos1', (1554,))):
    g = [e for e in ev if e['p'] == pid[b] and e['type'] == 'attack' and e['t'] in ticks and e['ok']]
    B0 = g[0]['B0']
    out = sum(e['troops'] + e['fee'] for e in g)
    by = defaultdict(lambda: [0, 0])
    for e in g:
        by[e['q']][0] += 1
        by[e['q']][1] += e['troops']
    first = g[0]['troops'] + g[0]['fee']
    print(f"  {b} t={ticks}: {len(g)} 条，批前 {at(pid[b], ticks[0]-3)[0]} 格/{k(B0)}（密度 {B0/max(1, g[0]['L0']):.0f}），连手续费打出 {k(out)}（{100*out/B0:.0f}%）；首条 {k(first)}（{100*first/B0:.0f}%）；pct={sorted({e['pct'] for e in g})}；目标 " + '；'.join(f"{nm(q)} {v[0]} 条 {k(v[1])}" for q, v in by.items()))
    print('     逐条出兵：' + ' '.join(f"{e['t']}:{e['troops']}" for e in g) + f"｜目标当时 {'；'.join(sorted({nm(e['q']) + ' ' + str(e['tL']) + '格/' + k(e['tB']) for e in g}))}")
    tr = ' '.join(f'{t}:{at(pid[b], t)[0]}/{k(at(pid[b], t)[1])}' for t in (1500, 1560, 1600, 1700, 1800, 1890, 2000, 2100, 2170, 2430) if alive_at(pid[b], t))
    print(f'     其后 地/兵：{tr}｜阵亡 {P[pid[b]]["deathT"]}')
    hit = defaultdict(lambda: [0, 0])
    for e in ev:
        if e['type'] in ('attack', 'boat') and e.get('q') == pid[b] and e.get('ok') and 1555 <= e['t'] <= 2430:
            hit[e['p']][0] += 1
            hit[e['p']][1] += e['troops']
    print('     1555–2430 谁打它：' + '；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])}' for q, v in sorted(hit.items(), key=lambda kv: -kv[1][1])[:5]))
    took = {nm(a): tiles for w, a, v, tiles in J['pairAll'] if v == pid[b] and 2 <= w < 5 for _ in [0]}
    lost = defaultdict(int)
    for w, a, v, tiles in J['pairAll']:
        if v == pid[b] and 2 <= w <= 4:
            lost[a] += tiles
    gain = defaultdict(int)
    for w, a, v, tiles in J['pairAll']:
        if a == pid[b] and 2 <= w <= 4:
            gain[v] += tiles
    print('     1200–2999 它拿到的地：' + '；'.join(f'{nm(q)} {n}' for q, n in sorted(gain.items(), key=lambda kv: -kv[1])[:4]) + '｜它丢的地：' + '；'.join(f'{nm(q)} {n}' for q, n in sorted(lost.items(), key=lambda kv: -kv[1])[:4]))

print('== §5 调度日志 vs 配额（J.dispatch）==')
dd = J['dispatch']
for t0, t1 in ((1500, 2142), (2142, 3213), (3213, 4284), (4284, 99999)):
    d = [x for x in dd if t0 <= x['t'] < t1]
    ex = [x for x in d if x['exec']]
    rej = [x for x in d if not x['exec'] and all(s_['reason'] == 'quota' for s_ in x['sim'])]
    kinds = Counter(x['kind'] for x in d)
    print(f"  {t0}–{t1}: 日志 {len(d)} 条（{dict(kinds)}），落地 {len(ex)}（到账 {k(sum(x['exec']['got'] for x in ex))} 税 {k(sum(x['exec']['fee'] for x in ex))}），四个试算拍全被配额拒 {len(rej)}")
ratios = []
unused = 0
for x in dd:
    if x['exec']:
        continue
    e0 = x['sim'][2].get('extra') or x['sim'][0].get('extra') or {}
    if e0.get('cost') and e0.get('cap'):
        ratios.append(e0['cost'] / e0['cap'])
        if e0.get('used', 1) == 0:
            unused += 1
if ratios:
    print(f"  没落地的 {len(ratios)} 条里：本笔所需配额点 ÷ 受赠方配额上限 中位 {statistics.median(ratios):.2f}，>1（单笔就超过整个上限）的 {sum(1 for r in ratios if r > 1)} 条；试算时受赠方已用配额为 0 的 {unused} 条")
z = [x for x in dd if x['q'] == pid['zexos1']]
print(f"  发给 zexos1 的日志 {len(z)} 条（{min(x['t'] for x in z)}–{max(x['t'] for x in z)}），落地 {sum(1 for x in z if x['exec'])} 条；按捐出方 " + ' '.join(f"{b}:{n}" for b, n in Counter(x['bot'] for x in z).most_common()))
wz = [(x['t'], x['bot'], (x['sim'][2].get('extra') or {})) for x in z if not x['exec']]
print('     想捐/所需点/上限：' + ' '.join(f"{t}:{b} {k(e.get('want', 0))}/{e.get('cost')}/{e.get('cap')}" for t, b, e in wz[:16]))
don = [e for e in ev if e['type'] == 'donate' and e['p'] in sq]
ok = [e for e in don if e['ok']]
print(f"  录像里我方号的捐兵指令 {len(don)} 条，成 {len(ok)}，被拒 {len(don) - len(ok)}；最后一笔成的 t={max(e['t'] for e in ok)}；t≥4284 的捐兵指令 {sum(1 for e in don if e['t'] >= 4284)} 条")
clamp = sum(1 for e in ok if e['got'] < 2 * e['fee'])
pp = 0
for e in ok:
    for f in ok:
        if f['p'] == e['q'] and f['q'] == e['p'] and 0 < f['t'] - e['t'] <= 300:
            pp += 1
want_sum = sum((e['B0'] * e['pct']) // 1024 for e in ok)
print(f"  已落地 18 笔：到账 < 2×税 的 {clamp} 笔；300 拍内反向再捐的 {pp} 对；按比例想捐合计 {k(want_sum)}，到账 {k(sum(e['got'] for e in ok))}，税 {k(sum(e['fee'] for e in ok))}")

print('== §6 打真人：谁打、花多少、换回多少地（全程）==')
tot = defaultdict(lambda: [0, 0])
for e in ev:
    if e['type'] == 'attack' and e['p'] in sq and e.get('ok') and e.get('q') in P and e['q'] not in sq:
        tot[sq[e['p']]][0] += 1
        tot[sq[e['p']]][1] += e['troops'] + e['fee']
gain_h = {sq[p]: sum(tiles for w, a, v, tiles in J['pairAll'] if a == p and v in P and v not in sq) for p in sq}
lost_h = {sq[p]: sum(tiles for w, a, v, tiles in J['pairAll'] if v == p and a in P and a not in sq) for p in sq}
for b in sorted(tot, key=lambda b: -tot[b][1]):
    print(f"  {b}: 打真人 {tot[b][0]} 条 {k(tot[b][1])}，从真人手里拿地 {gain_h[b]}（每格 {tot[b][1]/max(1, gain_h[b]):.0f} 兵），被真人拿走 {lost_h[b]}｜峰值地 {P[pid[b]]['peakTerr']}@{P[pid[b]]['peakT']}，阵亡 {P[pid[b]]['deathT']}")
print(f"  合计 打真人 {sum(v[0] for v in tot.values())} 条 {k(sum(v[1] for v in tot.values()))}，拿地 {sum(gain_h.values())}，被拿走 {sum(lost_h.values())}")
over = [e for e in ev if e['type'] == 'attack' and e['p'] in sq and e.get('ok') and e.get('q') in P and e['q'] not in sq and e['B0'] > 100 * max(1, e['L0'])]
print(f"  存兵 >100×地 时发出的打真人指令 {len(over)} 条 {k(sum(e['troops'] + e['fee'] for e in over))}：" + ' '.join(f"{b}:{n}" for b, n in Counter(sq[e['p']] for e in over).most_common()))
for lo, hi in ((0, 1500), (1500, 3000), (3000, 4284), (4284, 4890), (4890, 99999)):
    g = [e for e in ev if e['type'] == 'attack' and e['p'] in sq and e.get('ok') and e.get('q') in P and e['q'] not in sq and lo <= e['t'] < hi]
    w0, w1 = lo // 600, min(14, -(-min(hi, 8400) // 600))
    print(f"  {lo}–{hi}: 打真人 {len(g)} 条 {k(sum(e['troops'] + e['fee'] for e in g))}；按目标 " + ' '.join(f'{nm(q)}:{k(v)}' for q, v in Counter({q: sum(e['troops'] for e in g if e['q'] == q) for q in {e['q'] for e in g}}).most_common(5)))

print('== §7 各号阵亡前：谁打的、打了多少、当时队里别人手里的兵 ==')
for p in sorted(sq, key=lambda p: P[p]['deathT']):
    dt = P[p]['deathT']
    if dt < 0:
        continue
    hit = defaultdict(lambda: [0, 0])
    for e in ev:
        if e['type'] in ('attack', 'boat') and e.get('q') == p and e.get('ok') and dt - 300 <= e['t'] <= dt:
            hit[e['p']][0] += 1
            hit[e['p']][1] += e['troops']
    L0, B0 = at(p, dt - 300)
    L1, B1 = at(p, dt - 30)
    got = sum(e['got'] for e in ev if e['type'] == 'donate' and e['q'] == p and e['ok'] and dt - 600 <= e['t'] <= dt)
    idle = [(sq[q], at(q, dt - 30)) for q in sq if q != p and alive_at(q, dt - 30)]
    idle_sum = sum(B for _, (L_, B) in idle)
    enc = [b for b, _ in idle if sum(contact(pid[b], dt - 30)[x] for x in ('eh', 'el', 'bot', 'neut')) == 0]
    s_ = J['S10'][str(p)]
    pk = P[p]['peakTerr']
    print(f"  {sq[p]} 阵亡 {dt}（峰值 {pk}@{P[p]['peakT']}，除名线约 {pk//4}）：死前 300 拍 {L0}格/{k(B0)} → 死前 30 拍 {L1}格/{k(B1)}；最后 300 拍被打 {k(sum(v[1] for v in hit.values()))}：" + '；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])}' for q, v in sorted(hit.items(), key=lambda kv: -kv[1][1])[:4]) + f"｜最后 600 拍收到捐兵 {k(got)}｜死前 30 拍其余在场我方号共 {k(idle_sum)}（其中对敌接触为 0 的 {' '.join(enc) or '无'}）")

print('== §8 队伍与对手：各队地/兵，编队兵 ÷ 最大敌队兵 ==')
for t in (600, 900, 1200, 1500, 1800, 2400, 3000, 3600, 4200, 4500, 4800, 6000, 7500):
    terr, bal = hsrow(t)
    tm = defaultdict(lambda: [0, 0])
    for p in P:
        tm[P[p]['team']][0] += terr[p]
        tm[P[p]['team']][1] += bal[p]
    sL = sum(terr[p] for p in sq)
    sB = sum(bal[p] for p in sq)
    big = max(v[1] for t_, v in tm.items() if t_ != OUR and t_ > 0)
    print(f'  t={t} ' + ' '.join(f'T{t_}:{100*v[0]/LAND:.1f}%/{k(v[1])}' for t_, v in sorted(tm.items()) if t_ > 0) + f'｜编队 {100*sL/LAND:.1f}%/{k(sB)}（占本队兵 {100*sB/max(1, tm[OUR][1]):.0f}%）｜编队兵÷最大敌队兵 {sB/max(1, big):.2f}')
mates = sorted((p for p in P if P[p]['team'] == OUR and p not in sq), key=lambda p: -P[p]['peakTerr'])
print('  本队路人：' + '；'.join(f"{nm(p)} 出生 {tuple(P[p]['spawn']) if P[p]['spawn'] else '-'} 峰值 {P[p]['peakTerr']}@{P[p]['peakT']} 阵亡 {P[p]['deathT']} 离场 {P[p]['leftT']}" for p in mates))
print('  我方号峰值地：' + ' '.join(f"{sq[p]}:{P[p]['peakTerr']}@{P[p]['peakT']}" for p in sorted(sq, key=lambda p: -P[p]['peakTerr'])))
for p in mates[:2]:
    g = defaultdict(int)
    for w, a, v, tiles in J['pairAll']:
        if a == p:
            g[v] += tiles
    print(f"  {nm(p)} 的地从谁手里来：" + '；'.join(f'{nm(q)} {n}' for q, n in sorted(g.items(), key=lambda kv: -kv[1])[:6]) + f"｜每 600 拍 地/兵：" + ' '.join(f'{t}:{hsrow(t)[0][p]}/{k(hsrow(t)[1][p])}' for t in (600, 1200, 1800, 2400, 3000, 3600, 4200, 4800)))

print('== §9 sora_w 独活（4890–8294）==')
sw = pid['sora_w']
g = [e for e in ev if e['p'] == sw and e['t'] >= 4890 and e['type'] in ('attack', 'boat') and e.get('ok')]
gh = [e for e in g if e.get('q') in P]
poke = [e for e in gh if e['t'] >= 6000 and e['tB'] >= 2 * e['B0'] and (e['troops'] + e['fee']) <= 0.15 * e['B0']]
print(f"  4890 以后落地指令 {len(g)} 条，其中打真人 {len(gh)} 条 {k(sum(e['troops'] + e['fee'] for e in gh))}；EG-GIANT-POKE 口径（t≥6000、对方兵 ≥2×自己、单条 ≤15% 存兵）{len(poke)} 条 {k(sum(e['troops'] for e in poke))}")
print('  每 600 拍 地/兵：' + ' '.join(f'{t}:{at(sw, t)[0]}/{k(at(sw, t)[1])}' for t in range(4800, 8400, 600)) + f"｜峰值 {P[sw]['peakTerr']}@{P[sw]['peakT']}")
hit = defaultdict(lambda: [0, 0])
for e in ev:
    if e['type'] in ('attack', 'boat') and e.get('q') == sw and e.get('ok') and e['t'] >= 8000:
        hit[e['p']][0] += 1
        hit[e['p']][1] += e['troops']
print('  8000 以后谁打它：' + '；'.join(f'{nm(q)} {v[0]} 条 {k(v[1])}' for q, v in sorted(hit.items(), key=lambda kv: -kv[1][1])[:4]))
by = Counter()
for e in gh:
    by[nm(e['q'])] += e['troops']
print('  它打谁：' + '；'.join(f'{q} {k(v)}' for q, v in by.most_common(5)))

print('== §10 时间线取点（HS）==')
for t in (180, 300, 600, 900, 1200, 1500, 1800, 2400, 3000, 3600, 4200, 4500, 4800, 5400, 6000, 7200, 8100):
    if t not in HS['t']:
        continue
    terr, bal = hsrow(t)
    al = [p for p in sq if terr[p] > 0]
    print(f'  t={t} 在场我方号 {len(al)}：地 {sum(terr[p] for p in sq)}（{100*sum(terr[p] for p in sq)/LAND:.1f}%）兵 {k(sum(bal[p] for p in sq))}')

print('== §11 真人之间易手的地（pairAll，每 600 拍）：编队 ↔ 各队；交换比 ==')
team_of = lambda p: ('SQ' if p in sq else f"T{P[p]['team']}") if p in P else ('中立' if p == 512 else '机')
for w in range(1, 9):
    gain = defaultdict(int)
    lost = defaultdict(int)
    for w_, a, v, tiles in J['pairAll']:
        if w_ != w:
            continue
        if a in sq and v not in sq:
            gain[team_of(v)] += tiles
        if v in sq and a not in sq:
            lost[team_of(a)] += tiles
    print(f"  {w*600}–{w*600+599}: 编队拿到 " + ' '.join(f'{t_}:{n}' for t_, n in sorted(gain.items())) + f"（合计 {sum(gain.values())}）｜编队丢给 " + ' '.join(f'{t_}:{n}' for t_, n in sorted(lost.items())) + f"（合计 {sum(lost.values())}）")
sent_by_enemy = sum(e['troops'] + e.get('fee', 0) for e in ev if e['type'] in ('attack', 'boat') and e.get('ok') and e.get('q') in sq and e['p'] in P and e['p'] not in sq)
tiles_lost = sum(tiles for w_, a, v, tiles in J['pairAll'] if v in sq and a in P and a not in sq)
sent_by_sq = sum(e['troops'] + e.get('fee', 0) for e in ev if e['type'] in ('attack', 'boat') and e.get('ok') and e['p'] in sq and e.get('q') in P and e['q'] not in sq)
tiles_gain = sum(tiles for w_, a, v, tiles in J['pairAll'] if a in sq and v in P and v not in sq)
print(f"  全程：编队对真人出兵（陆攻+登陆，含手续费）{k(sent_by_sq)} 拿 {tiles_gain} 格（每格 {sent_by_sq/max(1, tiles_gain):.0f} 兵）；真人对编队出兵 {k(sent_by_enemy)} 拿 {tiles_lost} 格（每格 {sent_by_enemy/max(1, tiles_lost):.0f} 兵）")
t4 = {p for p in P if P[p]['team'] == 4}
for w0, w1, lab in ((5, 7, '3000–4199'),):
    g = defaultdict(int)
    for w_, a, v, tiles in J['pairAll']:
        if w0 <= w_ < w1 and v in t4 and a in P:
            g[team_of(a) if a not in sq else 'SQ'] += tiles
    mate = sum(tiles for w_, a, v, tiles in J['pairAll'] if w0 <= w_ < w1 and v in t4 and a in P and a not in sq and P[a]['team'] == OUR)
    print(f"  {lab} T4 丢的地归谁：" + ' '.join(f'{t_}:{n}' for t_, n in sorted(g.items(), key=lambda kv: -kv[1])) + f"（其中 T1 路人 {mate}）")

print('== §12 最后一条落地指令到阵亡的间隔；各号阵亡时的地与引擎除名线 ==')
gaps = []
for p in sorted(sq, key=lambda p: P[p]['deathT']):
    dt = P[p]['deathT']
    last = max((e['t'] for e in ev if e['p'] == p and e['type'] in ('attack', 'boat', 'donate') and e.get('ok') and e['t'] <= dt), default=None)
    L1, B1 = at(p, dt - 10)
    gaps.append(dt - last)
    print(f"  {sq[p]}: 最后一条落地指令 t={last}，阵亡 {dt}（间隔 {dt - last} 拍）；阵亡前 10 拍 {L1} 格/{k(B1)}（峰值 {P[p]['peakTerr']} 的 {100*L1/max(1, P[p]['peakTerr']):.0f}%）")
print(f"  间隔中位 {statistics.median(gaps):.0f} 拍")

print('== §13 0–1500 打真人的小仗 ==')
for b in sq.values():
    g = [e for e in ev if e['p'] == pid[b] and e['type'] == 'attack' and e.get('ok') and e.get('q') in P and e['q'] not in sq and e['t'] < 1500]
    if not g:
        continue
    by = defaultdict(lambda: [0, 0, 0])
    for e in g:
        by[e['q']][0] += 1
        by[e['q']][1] += e['troops'] + e['fee']
    for q in by:
        by[q][2] = sum(tiles for w_, a, v, tiles in J['pairAll'] if a == pid[b] and v == q and w_ < 3)
    print(f"  {b}: " + '；'.join(f"{nm(q)} {v[0]} 条 {k(v[1])} 拿 {v[2]} 格（t={min(e['t'] for e in g if e['q']==q)}–{max(e['t'] for e in g if e['q']==q)}）" for q, v in by.items()))
g = [e for e in ev if e['p'] == pid['sora_w'] and e['type'] == 'attack' and e['t'] == 1176]
if g:
    print(f"  sora_w t=1176: {len(g)} 条，批前 {k(g[0]['B0'])}，打出 {k(sum(e['troops'] + e['fee'] for e in g))}（{100*sum(e['troops'] + e['fee'] for e in g)/g[0]['B0']:.0f}%），目标 {nm(g[0]['q'])} {g[0]['tL']} 格/{k(g[0]['tB'])}")

print('== §14 ryan_m 吃 Player 67（2142–2310）与其后 ==')
r = pid['ryan_m']
g = [e for e in ev if e['p'] == r and e['type'] == 'attack' and e.get('ok') and e.get('q') == 7]
print('  ryan_m→Player 67 逐条：' + ' '.join(f"{e['t']}:{k(e['troops'])}(pct{e['pct']},对方{e['tL']}格/{k(e['tB'])})" for e in g))
print('  ryan_m 地/兵：' + ' '.join(f'{t}:{at(r, t)[0]}/{k(at(r, t)[1])}' for t in (2100, 2140, 2200, 2250, 2310, 2400, 2500, 2700, 3000, 3200, 3370)))
din = [e for e in ev if e['type'] == 'donate' and e['q'] == r and e['ok']]
print('  收到捐兵：' + ' '.join(f"{e['t']}:{sq[e['p']]} {k(e['got'])}" for e in din))
hit = [e for e in ev if e['type'] in ('attack', 'boat') and e.get('q') == r and e.get('ok') and e['t'] >= 2300 and e['troops'] > 3000]
print('  2300 以后谁打它：' + ' '.join(f"{e['t']}:{nm(e['p'])} {k(e['troops'])}" for e in hit))

print('== §15 选点期最后 12 拍别家号的落子（首次/改点）与离编队旧质心 (1308,166) 的距离 ==')
import csv
tsv = f'/tmp/c136-r05/work/{M}-cmds.tsv'
if os.path.exists(tsv):
    rows = list(csv.reader(open(tsv, encoding='utf-8'), delimiter='\t'))
    hdr = rows[0]
    first = {}
    placed = set()
    cnt_by_t = {}
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        if d['kind'] != 'spawn':
            continue
        t = int(d['tick'])
        p = int(d['player'])
        new = p not in first
        if new:
            first[p] = t
        if p not in sq and p in P:
            placed.add(p)
            cnt_by_t[t] = len(placed)
            if -12 <= t <= -5:
                a = int(d['a'])
                x, y = a % W, a // W
                dist = ((x - 1308) ** 2 + (y - 166) ** 2) ** 0.5
                print(f"  t={t} {nm(p)} ({x},{y}) {'首次落子' if new else '改点'}｜离旧质心 {dist:.0f} 格｜此刻已落点的其他真人 {len(placed)}（+10 = {len(placed)+10} → rCell {round((max(10000, LAND) / (3.141592653589793 * (len(placed) + 10))) ** 0.5)}）")

print('== §16 已落地的 18 笔捐兵：受赠方其后 300 拍打真人花了多少、地怎么变 ==')
for e in ev:
    if e['type'] != 'donate' or not e.get('ok') or e['p'] not in sq:
        continue
    q = e['q']
    t = e['t']
    spent = sum(x['troops'] + x.get('fee', 0) for x in ev if x['p'] == q and x['type'] in ('attack', 'boat') and x.get('ok') and x.get('q') in P and x['q'] not in sq and t <= x['t'] <= t + 300)
    hit = sum(x['troops'] for x in ev if x.get('q') == q and x['type'] in ('attack', 'boat') and x.get('ok') and x['p'] in P and x['p'] not in sq and t - 100 <= x['t'] <= t + 300)
    L0, B0 = at(q, t - 1)
    L1, B1 = at(q, min(t + 300, P[q]['deathT'] - 1 if P[q]['deathT'] and P[q]['deathT'] > 0 else t + 300))
    dead = P[q]['deathT']
    print(f"  t={t} {sq[e['p']]}→{sq[q]} 到账 {k(e['got'])}（税 {k(e.get('tax', e.get('fee', 0)))}）｜受赠方 {L0} 格/{k(B0)} → +300 拍 {L1} 格/{k(B1)}｜其后 300 拍它打真人 {k(spent)}，前 100–后 300 拍被真人打 {k(hit)}｜阵亡 {dead}")

print('== §17 过软上限那一拍放出的进攻轮（首条指令 B0 > 100×L0；同号同目标间隔 ≤21 拍归一轮）与对方其后 100 拍的回击 ==')
atk = [e for e in ev if e['p'] in sq and e['type'] == 'attack' and e.get('ok') and e.get('q') in P and e['q'] not in sq]
atk.sort(key=lambda e: (e['p'], e['q'], e['t']))
vol = []
for e in atk:
    if vol and vol[-1][-1]['p'] == e['p'] and vol[-1][-1]['q'] == e['q'] and e['t'] - vol[-1][-1]['t'] <= 21:
        vol[-1].append(e)
    else:
        vol.append([e])
tot_n = tot_cmd = tot_sent = 0
tot_back = 0
big_n = big_sent = big_back = big_hit = 0
for v in sorted(vol, key=lambda v: v[0]['t']):
    f = v[0]
    if f['B0'] <= 100 * f['L0']:
        continue
    sent = sum(x['troops'] + x['fee'] for x in v)
    t1 = v[-1]['t']
    back = [x for x in ev if x['p'] == f['q'] and x['type'] in ('attack', 'boat') and x.get('ok') and x.get('q') in sq and t1 < x['t'] <= t1 + 100]
    backsum = sum(x['troops'] for x in back)
    ratio = (f.get('tB') or 0) / max(1, f['B0'])
    tot_n += 1
    tot_cmd += len(v)
    tot_sent += sent
    tot_back += backsum
    if ratio >= 2 and f['t'] < 4890:
        big_n += 1
        big_sent += sent
        big_back += backsum
        big_hit += 1 if back else 0
    print(f"  t={f['t']}–{t1} {sq[f['p']]} → {nm(f['q'])}：{len(v)} 条 {k(sent)}（首条时 {f['L0']} 格/{k(f['B0'])}，密度 {f['B0']/max(1,f['L0']):.0f}；末条时密度 {v[-1]['B0']/max(1,v[-1]['L0']):.0f}）｜对方 {f.get('tL')} 格/{k(f.get('tB') or 0)}＝{ratio:.1f}×我｜其后 100 拍对方打我方号：" + ('；'.join(f"{x['t']}→{sq[x['q']]} {k(x['troops'])}" for x in back) or '无'))
print(f"  合计 {tot_n} 轮 {tot_cmd} 条 {k(tot_sent)}，其后 100 拍对方回击 {k(tot_back)}｜其中 t<4890、对方存兵 ≥2×自己的 {big_n} 轮 {k(big_sent)}，{big_hit} 轮在 100 拍内挨了回击，共 {k(big_back)}")

print('== §18 buyLand 分支命中汇总（读 mids_tally.py 的输出 /tmp/c136-r05/work/A095-mids-buy.txt）==')
import re
mb = f'/tmp/c136-r05/work/{M}-mids-buy.txt'
if os.path.exists(mb):
    calls = sends = 0
    cont = Counter()
    per = defaultdict(lambda: [0, 0])
    for line in open(mb, encoding='utf-8'):
        mm = re.match(r'\[分支命中 buyLand\] (\S+) t=(\d+)–(\d+) 调用 (\d+) 次｜出口行 (.*?)｜途中 continue 行（按拍去重）(.*)', line)
        if not mm:
            continue
        b = mm.group(1)
        n = int(mm.group(4))
        calls += n
        per[b][0] += n
        for ln, c in re.findall(r'(\d+)×(\d+)', mm.group(5)):
            if ln != '5618':
                sends += int(c)
                per[b][1] += int(c)
        for ln, c in re.findall(r'(\d+)×(\d+)', mm.group(6)):
            cont[ln] += int(c)
    print(f"  调用 {calls} 次，有出兵的出口 {sends} 次（{100*sends/max(1,calls):.1f}%）；途中跳过行命中（按拍去重）：" + ' '.join(f'L{ln}×{c}' for ln, c in cont.most_common(8)))
    print('  各号 调用/出兵：' + ' '.join(f'{b}:{v[0]}/{v[1]}' for b, v in per.items()))

print('== §19 调度日志按受赠方逐条：日志拍:捐出方 想捐/所需点/已用/上限 → 落地或被拒；按捐出方的日志拍范围；boxedIn ==')
rname = {v: kname for kname, v in pid.items()}
for qn in ('zexos1', 'talon5', 'ryan_m', 'kaito9', 'riku_x', 'zero_7', 'noah88', 'leo_tx', 'alex_k', 'sora_w'):
    z = [x for x in dd if x['q'] == pid[qn]]
    parts = []
    for x in z:
        e0 = x['sim'][2].get('extra') or x['sim'][0].get('extra') or {}
        if x['exec']:
            parts.append(f"{x['t']}:{x['bot']} ✓{x['exec']['t']} 到账 {k(x['exec']['got'])}")
        else:
            parts.append(f"{x['t']}:{x['bot']} ✗ {k(e0.get('want', 0))}/{e0.get('cost')}/{e0.get('used')}/{e0.get('cap')}")
    print(f"  → {qn}（{len(z)} 条，落地 {sum(1 for x in z if x['exec'])}）：" + ' '.join(parts))
for b in ('leo_tx', 'sora_w', 'zero_7', 'alex_k', 'noah88'):
    z = [x for x in dd if x['bot'] == b]
    if z:
        print(f"  捐出方 {b}: 日志 {len(z)} 条 t={min(x['t'] for x in z)}–{max(x['t'] for x in z)}；落地 {sum(1 for x in z if x['exec'])}；1500–2142 拍 {sum(1 for x in z if x['t'] < 2142)} 条")
bx = Counter(bool(x.get('boxedIn')) for x in dd)
print(f"  84 条日志的捐出方 boxedIn：{dict(bx)}" + ('' if any('boxedIn' in x for x in dd) else '（J.dispatch 没有 boxedIn 字段，见 match_extra.py --sec disp）'))

print('== §20 零散核对 ==')
# (a) sora_w 1148–1176 打曾子大帝国：其后的地、兵与回流
sw = pid['sora_w']
print('  sora_w 地/兵：' + ' '.join(f"{t}:{at(sw, t)[0]}/{k(at(sw, t)[1])}" for t in (1140, 1170, 1180, 1200, 1260, 1320, 1500)))
fl = flows(sw, 1140, 1320)
print('  sora_w 1140–1320 收支：' + ' '.join(f"{c}:{k(v)}" for c, v in fl.items() if abs(v) >= 500))
zz = [p for p in P if P[p]['name'].startswith('曾子')][0]
print('  曾子大帝国 地/兵（HS）：' + ' '.join(f"{t}:{hsrow(t)[0][zz]}/{k(hsrow(t)[1][zz])}" for t in (900, 1200, 1500, 1800, 2400)))
print('  sora_w 从曾子大帝国手里拿到的地（每 600 拍窗）：' + ' '.join(f"{w*600}:{tiles}" for w, a, v, tiles in J['pairAll'] if a == sw and v == zz))
# (b) leo_tx 2185–2215 落地的指令
lt = pid['leo_tx']
print('  leo_tx 2185–2215 落地指令：' + ' '.join(f"{e['t']}:{e['type']}→{nm(e['q']) if e.get('q') is not None else '-'} {k(e.get('troops', 0))}(pct{e.get('pct')})" for e in ev if e['p'] == lt and 2185 <= e['t'] <= 2215 and e.get('ok')))
print('  leo_tx 地/兵：' + ' '.join(f"{t}:{at(lt, t)[0]}/{k(at(lt, t)[1])}" for t in (2190, 2210, 2220, 2300, 2400)))
# (c) Nice Guy 对我方号的全部出兵
ng = [p for p in P if 'Nice Guy' in P[p]['name']][0]
hits = [e for e in ev if e['p'] == ng and e['type'] in ('attack', 'boat') and e.get('ok') and e.get('q') in sq]
print(f"  Nice Guy 对我方号出兵 {len(hits)} 条 {k(sum(e['troops'] for e in hits))}：" + ' '.join(f"{e['t']}→{sq[e['q']]} {k(e['troops'])}" for e in hits))
# (d) Player 456：收到的捐兵、地从谁手里来
p456 = [p for p in P if P[p]['name'] == 'Player 456'][0]
dn = [e for e in ev if e['type'] == 'donate' and e.get('q') == p456 and e.get('ok')]
print(f"  Player 456 收到捐兵 {len(dn)} 笔 {k(sum(e.get('got', 0) for e in dn))}")
src = Counter()
for w, a, v, tiles in J['pairAll']:
    if a == p456:
        src[nm(v)] += tiles
print('  Player 456 的地从谁手里来（全程）：' + '；'.join(f"{n} {v}（{100*v/LAND:.1f}%）" for n, v in src.most_common(7)))
# (f) kaito9 3000–3700 打真人
k9 = pid['kaito9']
a9 = [e for e in ev if e['p'] == k9 and e['type'] == 'attack' and e.get('ok') and e.get('q') in P and e['q'] not in sq and 2430 <= e['t'] <= 4606]
print(f"  kaito9 2430 以后打真人 {len(a9)} 条 {k(sum(e['troops'] + e['fee'] for e in a9))}：" + ' '.join(f"{e['t']}→{nm(e['q'])} {k(e['troops'])}" for e in a9))
# (i) 编队存兵 ÷（88×编队地）：safeAt 封顶线下面压着多少兵
for t in (1500, 1800, 2400, 3000, 3600, 3900, 4200, 4500):
    if t not in HS['t']:
        continue
    terr, bal = hsrow(t)
    alive = [p for p in sq if terr[p] > 0]
    L_ = sum(terr[p] for p in alive)
    B_ = sum(bal[p] for p in alive)
    over = [sq[p] for p in alive if bal[p] > 100 * terr[p]]
    above88 = sum(max(0, bal[p] - 88 * terr[p]) for p in alive)
    print(f"  t={t} 编队 {len(alive)} 号 地 {L_} 兵 {k(B_)}＝{B_/max(1,L_):.0f}/格；88×地 = {k(88*L_)}；各号高出 88×地 的部分合计 {k(above88)}（{100*above88/max(1,B_):.1f}% 存兵）；存兵 >100×地 的号 {over or '无'}")

print('== §21 邻居的地归谁（pairAll 全程）、若干号的逐拍地/兵、机器人与 T4 占图 ==')
def named(s):
    return [p for p in P if P[p]['name'].startswith(s)][0]
for vn in ('Player 494', 'Player 67', 'Hi', 'Revolution', 'Player 539', 'JJS'):
    v_ = named(vn)
    c = Counter()
    for w, a, v, tiles in J['pairAll']:
        if v == v_:
            c[nm(a)] += tiles
    print(f"  {vn} 丢的地归谁：" + '；'.join(f"{n} {x}" for n, x in c.most_common(7)))
for b, vn in (('riku_x', 'Palestine'), ('riku_x', 'player 938')):
    v_ = named(vn)
    print(f"  {vn} 从 {b} 手里拿走 {sum(tiles for w, a, v, tiles in J['pairAll'] if a == v_ and v == pid[b])} 格；{b} 从它手里拿到 {sum(tiles for w, a, v, tiles in J['pairAll'] if v == v_ and a == pid[b])} 格")
hi = named('Hi')
print('  我方号从 Hi 手里拿到：' + ' '.join(f"{sq[a]}:{sum(t_ for w, a_, v, t_ in J['pairAll'] if a_ == a and v == hi)}" for a in sq) + f"｜合计 {sum(t_ for w, a_, v, t_ in J['pairAll'] if a_ in sq and v == hi)}")
print('  leo_tx 从 Hi 手里拿到（每 600 拍窗）：' + ' '.join(f"{w*600}:{tiles}" for w, a, v, tiles in J['pairAll'] if a == pid['leo_tx'] and v == hi))
p67 = named('Player 67')
print('  ryan_m 从 Player 67 手里拿到（每 600 拍窗）：' + ' '.join(f"{w*600}:{tiles}" for w, a, v, tiles in J['pairAll'] if a == pid['ryan_m'] and v == p67))
rev = named('Revolution')
print('  riku_x 从 Revolution 手里拿到（每 600 拍窗）：' + ' '.join(f"{w*600}:{tiles}" for w, a, v, tiles in J['pairAll'] if a == pid['riku_x'] and v == rev))
print('  zero_7 地/兵：' + ' '.join(f"{t}:{at(pid['zero_7'], t)[0]}/{k(at(pid['zero_7'], t)[1])}" for t in (1500, 1600, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 4200, 4300, 4400)))
print('  noah88 地/兵：' + ' '.join(f"{t}:{at(pid['noah88'], t)[0]}/{k(at(pid['noah88'], t)[1])}" for t in (2100, 2400, 2490, 2520, 3000, 3900, 4200, 4300, 4350, 4390, 4500, 4800)))
print('  riku_x 地/兵：' + ' '.join(f"{t}:{at(pid['riku_x'], t)[0]}/{k(at(pid['riku_x'], t)[1])}" for t in (1830, 1900, 2650, 2660, 2700, 3350, 3400, 3500, 3990, 4020, 4100, 4300, 4330)))
for t in (600, 900, 1200, 1500, 2700):
    if t in HS['t']:
        terr, bal = hsrow(t)
        hum = sum(terr[p] for p in P)
        t4 = sum(terr[p] for p in P if P[p]['team'] == 4)
        print(f"  t={t} 真人合计占图 {100*hum/LAND:.1f}%，T4 {100*t4/LAND:.1f}%")
print('  骨架时间线里的机器人/中立占图：' + ' '.join(f"{r['t']}:" + '/'.join(f"{kk}={r[kk]}" for kk in r if 'bot' in kk.lower() or 'neut' in kk.lower()) for r in json.load(open(f'/tmp/c136-r05/skel/{M}.json'))['timeline'] if r['t'] in (600, 900, 1200, 1500)))
p494 = named('Player 494')
for t in (1500, 1800, 2100, 2400, 2700):
    terr, bal = hsrow(t)
    print(f"  Player 494 t={t}: {terr[p494]} 格/{k(bal[p494])}；Player 67: {terr[p67]} 格/{k(bal[p67])}；Hi: {terr[hi]}/{k(bal[hi])}")
