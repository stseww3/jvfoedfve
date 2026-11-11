# A037_facts.py — A037 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / boat_fate.mjs / shadow.mjs）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A037.json 机械算出；§7 另读 replay_cmds.mjs 解出的命令流（/tmp/c136-r05/work/A037-cmds.tsv）。
# 用法：python3 scripts/review_build/A037_facts.py
import json, bisect, os
from collections import defaultdict

M = 'A037'
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
team = {p['id']: p['team'] for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
ad = J['allDon']
HS = J['HS']
F = J['F30']
CATS = J['cats']
OUR = J['ourTeam']


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
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def hs(p):
    return {t: (HS['terr'][i][p], HS['bal'][i][p]) for i, t in enumerate(HS['t'])}


print('== §1 阵内的敌人 kakoscsiga(#1,T1)：每 300 拍 地/兵；它与我方号之间的全部陆攻（t<2800）==')
h = hs(1)
print('  ' + ' '.join(f'{t}:{h[t][0]}/{k(h[t][1])}' for t in sorted(h) if t <= 3000))
n_sq = defaultdict(lambda: [0, 0])
for e in ev:
    if e['t'] < 2800 and e['type'] == 'attack' and ((e['p'] == 1 and e.get('q') in sq) or (e.get('q') == 1 and e['p'] in sq)):
        print(f"  t={e['t']} {nm(e['p'])}→{nm(e.get('q'))} pct={e.get('pct')} 出 {k(e.get('troops', 0))}｜发出方 {k(e.get('B0', 0))}/{e.get('L0')}")
        if e['p'] in sq:
            w = '1610–1645' if e['t'] < 1700 else '2422–2520' if e['t'] < 2590 else '2646–2681'
            n_sq[w][0] += 1; n_sq[w][1] += e.get('troops', 0)
print('  我方号打它：' + '；'.join(f'{w} {v[0]} 条 {k(v[1])}' for w, v in n_sq.items()))
for t in (1700, 2000, 2300, 2580):
    nb = ['alex_k', 'noah88', 'kaito9', 'leo_tx']
    print(f"  t={t} 只挨着它一个敌人的四个号存兵 " + ' '.join(f'{b}:{k(at(pid[b], t)[1])}' for b in nb) + f" 合计 {k(sum(at(pid[b], t)[1] for b in nb))}" +
          f"｜另两个接壤的号 ryan_m:{k(at(pid['ryan_m'], t)[1])} sora_w:{k(at(pid['sora_w'], t)[1])}｜六号合计 {k(sum(at(pid[b], t)[1] for b in nb + ['ryan_m', 'sora_w']))}")
for b in ('ryan_m', 'sora_w'):
    c_ = defaultdict(lambda: [0, 0])
    for e in ev:
        if e['p'] == pid[b] and e['type'] == 'attack' and 1500 <= e['t'] < 2640 and e.get('q') in P and e.get('q') not in sq:
            c_[nm(e['q'])][0] += 1; c_[nm(e['q'])][1] += e['troops']
    print(f"  {b} 1500–2640 打真人：" + '；'.join(f'{x} {v[0]} 条 {k(v[1])}' for x, v in c_.items()))
lt = [e for e in ev if e['p'] == pid['leo_tx'] and e['type'] in ('attack', 'boat', 'donate') and e.get('ok', True)]
print(f"  leo_tx 全程落地指令 {len(lt)} 条，最后一条 t={lt[-1]['t']}；1600–1630 打 kakoscsiga：" +
      ' '.join(f"{e['t']}:{k(e['troops'])}" for e in lt if 1600 <= e['t'] <= 1630) + f"（批前存兵 {k(next(e['B0'] for e in lt if e['t'] >= 1600))}）")

print('== §2 [CAT] Mr. FC(#22,T2)：每 300 拍 地/兵；3600–4150 与它有关的陆攻 ==')
h = hs(22)
print('  ' + ' '.join(f'{t}:{h[t][0]}/{k(h[t][1])}' for t in sorted(h) if 2700 <= t <= 4200))
rounds = defaultdict(lambda: [0, 0])
for e in ev:
    if 3600 <= e['t'] < 4150 and e['type'] == 'attack' and (e['p'] == 22 or e.get('q') == 22):
        print(f"  t={e['t']} {nm(e['p'])}→{nm(e.get('q'))} pct={e.get('pct')} 出 {k(e.get('troops', 0))}｜发出方 {k(e.get('B0', 0))}/{e.get('L0')}")
        if e['p'] in sq:
            w = '3703–3780' if e['t'] <= 3780 else '3899–4116'
            rounds[w][0] += 1; rounds[w][1] += e['troops']
print('  我方号打 Mr. FC：' + '；'.join(f'{w} {v[0]} 条 {k(v[1])}' for w, v in rounds.items()))
z = [e for e in ev if e['p'] == pid['zexos1'] and e['type'] == 'attack' and e.get('q') == 27 and 3213 <= e['t'] <= 3600]
print(f"  zexos1 打 plz no attack(#27) 3213–3600：{len(z)} 条 {k(sum(e['troops'] for e in z))}：" + ' '.join(f"{e['t']}:{k(e['troops'])}" for e in z))
d = [x for x in ad if x[2] == pid['zexos1'] and 3213 <= x[0] <= 3241]
print(f"  3213–3241 捐给 zexos1：{len(d)} 笔 到账 {k(sum(x[3] for x in d))} 税 {k(sum(x[4] for x in d))}：" + ' '.join(f'{x[0]}:{sq[x[1]]} {k(x[3])}' for x in d))
print(f"  zexos1 地/兵：3210 {at(pid['zexos1'], 3210)}，3245 {at(pid['zexos1'], 3245)}，3600 {at(pid['zexos1'], 3600)}，3870 {at(pid['zexos1'], 3870)}，4200 {at(pid['zexos1'], 4200)}")
z = [e for e in ev if e.get('q') == pid['zexos1'] and e['p'] not in sq and e['type'] == 'attack' and 3860 <= e['t'] <= 4210 and e['troops'] >= 400e3]
print('  3860–4210 打 zexos1 的 ≥400k 的陆攻：' + ' '.join(f"{e['t']}:{nm(e['p'])} pct={e['pct']} {k(e['troops'])}" for e in z))

print('== §3 打 talon5 的 ≥300k 的陆攻/登陆（t≥5800），以及其后 150 拍 talon5 收到的捐兵、自己打出去的兵 ==')
T5 = pid['talon5']
tot = defaultdict(lambda: [0, 0])
for e in ev:
    if e.get('q') == T5 and e['p'] not in sq and e['type'] in ('attack', 'boat-land') and e.get('troops', 0) >= 300e3 and e['t'] >= 5800:
        t = e['t']
        don = [x for x in ad if x[2] == T5 and t <= x[0] < t + 150]
        out = [x for x in ev if x['p'] == T5 and x['type'] == 'attack' and t <= x['t'] < t + 150 and x.get('ok', True)]
        print(f"  t={t} {nm(e['p'])} {'登陆' if e['type'] != 'attack' else '陆攻'} {k(e['troops'])}｜talon5 {at(T5, t)} → +150 拍 {at(T5, t + 150)}｜其间收捐 {len(don)} 笔 {k(sum(x[3] for x in don))}（税 {k(sum(x[4] for x in don))}）｜自己打出 {len(out)} 条 {k(sum(x['troops'] for x in out))}")
        key = (nm(e['p']), '登陆' if e['type'] != 'attack' else '陆攻')
        tot[key][0] += 1; tot[key][1] += e['troops']
print('  合计：' + '；'.join(f'{a} {b} {v[0]} 次 {k(v[1])}' for (a, b), v in tot.items()))
for lo, hi in ((4284, 5800), (5800, 6600), (6600, 7800), (7800, 9000)):
    dd = defaultdict(lambda: [0, 0, 0])
    for t, p, q, g, f in ad:
        if q == T5 and lo <= t < hi:
            dd[sq.get(p, str(p))][0] += 1; dd[sq.get(p, str(p))][1] += g; dd[sq.get(p, str(p))][2] += f
    n = sum(v[0] for v in dd.values()); g_ = sum(v[1] for v in dd.values()); f_ = sum(v[2] for v in dd.values())
    print(f'  talon5 收捐 {lo}–{hi}: {n} 笔 {k(g_)} 税 {k(f_)}｜' + ' '.join(f'{b}:{v[0]}/{k(v[1])}' for b, v in sorted(dd.items(), key=lambda kv: -kv[1][1])))
print('  talon5 地：' + ' '.join(f'{t}:{at(T5, t)[0]}' for t in (5800, 6000, 6270, 6480, 6630, 6750, 6900, 7140, 7360, 7560, 7740, 7900, 8050, 8300, 8700, 9000)))

print('== §4 每 600 拍真人之间易手的地：按「谁丢的」×「谁拿的」（编队 / T3 路人 / T1 / T2）==')


def cls(x):
    if x in sq:
        return 'SQ'
    if x in team:
        return 'T%d' % team[x] if team[x] != OUR else 'T3r'
    return None


tab = defaultdict(lambda: defaultdict(int))
for w, x, b, n in J['pairAll']:
    if b in team and x in team:
        tab[(w, cls(b))][cls(x)] += n
print('  窗口｜从 T2 手里：T1 / 编队 / T3 路人｜从 T1 手里：T2 / 编队 / T3 路人｜从编队手里：T1 / T2｜从 T3 路人手里：T1 / T2')
for w in range(2, 16):
    a, b, c, d_ = tab[(w, 'T2')], tab[(w, 'T1')], tab[(w, 'SQ')], tab[(w, 'T3r')]
    print(f"  {w*600}–{w*600+599}｜{a['T1']} / {a['SQ']} / {a['T3r']}｜{b['T2']} / {b['SQ']} / {b['T3r']}｜{c['T1']} / {c['T2']}｜{d_['T1']} / {d_['T2']}")
for vt in ('T2', 'T1', 'SQ', 'T3r'):
    print(f'  全程 从 {vt} 手里：' + ' '.join(f"{kk}:{sum(tab[(w, vt)][kk] for w in range(0, 17))}" for kk in ('T1', 'T2', 'SQ', 'T3r')))
for lo, hi in ((3000, 4200),):
    a = sum(tab[(w, 'T2')]['SQ'] for w in range(lo // 600, hi // 600)); b = sum(tab[(w, 'T2')]['T1'] for w in range(lo // 600, hi // 600))
    c = sum(tab[(w, 'T1')]['T2'] for w in range(lo // 600, hi // 600))
    print(f'  {lo}–{hi}：编队从 T2 拿 {a}，T1 从 T2 拿 {b}，T2 从 T1 拿 {c}')

print('== §5 编队与敌方真人互打的交换比（pairsW，100 拍对齐）==')
for lo, hi in ((1500, 3000), (3000, 4200), (4200, 5400), (5400, 6600), (6600, 7800), (7800, 9500), (1500, 9500)):
    o = [0, 0, 0]; i_ = [0, 0, 0]
    for r in J['pairsW']:
        t = r['w'] * 100
        if not (lo <= t < hi):
            continue
        a, b = r['a'], r['b']
        if a in sq and b in team and team[b] != OUR:
            o[0] += r['sent']; o[1] += r['tiles']; o[2] += r['balDmg']
        if b in sq and a in team and team[a] != OUR:
            i_[0] += r['sent']; i_[1] += r['tiles']; i_[2] += r['balDmg']
    print(f"  {lo}–{hi}: 编队打敌方真人 投 {k(o[0])} 拿地 {o[1]} 打掉兵 {k(o[2])}（每格 {o[0]/max(1,o[1]):.0f} 兵）｜敌方真人打编队 投 {k(i_[0])} 拿地 {i_[1]} 打掉兵 {k(i_[2])}（每格 {i_[0]/max(1,i_[1]):.0f} 兵）")

print('== §6 ryan_m 4200–5900：地、密度、捐出 ==')
R = pid['ryan_m']
print('  地/密度：' + ' '.join(f"{t}:{at(R, t)[0]}/{at(R, t)[1]/max(1, at(R, t)[0]):.0f}" for t in range(4200, 6001, 200)))
d = [x for x in ad if x[1] == R and 4284 <= x[0] < 5900]
print(f"  4284–5900 捐出 {len(d)} 笔 到账 {k(sum(x[3] for x in d))} 税 {k(sum(x[4] for x in d))}（税/到账 {100*sum(x[4] for x in d)/sum(x[3] for x in d):.1f}%）：" + ' '.join(f'{x[0]}→{sq[x[2]]} {k(x[3])}/{k(x[4])}' for x in d))
a = [e for e in ev if e['p'] == R and e['type'] == 'attack' and e.get('q') in team and team[e['q']] != OUR and 4200 <= e['t'] < 6600]
print(f"  4200–6600 ryan_m 打敌方真人 {len(a)} 条 {k(sum(e['troops'] for e in a))}，第一条 t={a[0]['t'] if a else None}")
b = [e for e in ev if e.get('q') == R and e['p'] == 21 and e['type'] == 'attack' and 5900 <= e['t'] < 6600]
print(f"  5900–6600 过敏党(#21) 打 ryan_m {len(b)} 条 {k(sum(e['troops'] for e in b))}")
print('  过敏党 地/兵：' + ' '.join(f'{t}:{v[0]}/{k(v[1])}' for t, v in sorted(hs(21).items()) if 3900 <= t <= 6600))

print('== §7 选点阶段的出生指令（replay_cmds.mjs 的命令流；拍号为负 = 选点阶段）==')
tsv = f'/tmp/c136-r05/work/{M}-cmds.tsv'
if os.path.exists(tsv):
    W = int(J['map']['W']) if isinstance(J.get('map'), dict) and 'W' in J['map'] else 931
    by = defaultdict(list)
    for line in open(tsv):
        r = line.rstrip('\n').split('\t')
        if len(r) > 5 and r[1] == '0':
            by[int(r[3])].append((int(r[0]), int(r[5]) % W, int(r[5]) // W))
    for p in [1, 0] + sorted(sq):
        v = by.get(p, [])
        if v:
            print(f'  {nm(p)}: {len(v)} 条，首条 t={v[0][0]} ({v[0][1]},{v[0][2]})，末条 t={v[-1][0]} ({v[-1][1]},{v[-1][2]})')
    kx, ky = by[1][-1][1], by[1][-1][2]
    print('  各号最终出生点到 kakoscsiga 的距离：' + ' '.join(f"{sq[p]}:{((by[p][-1][1]-kx)**2 + (by[p][-1][2]-ky)**2) ** 0.5:.0f}" for p in sorted(sq) if by.get(p)))
else:
    print('  （先运行 node scripts/replay_cmds.mjs A037 --out /tmp/c136-r05/work/A037-cmds.tsv）')

print('== §8 编队收支（任意窗口，30 拍栅格）与船的手续费 ==')


def flows(p, lo, hi):
    f = F[str(p)]

    def cum(t):
        i = bisect.bisect_right(f['t'], t) - 1
        return f['flows'][i] if i >= 0 else [0] * len(CATS)
    return [y - x for x, y in zip(cum(lo), cum(hi))]


for lo, hi in ((1500, 3210), (3210, 4260), (4260, 5400), (5400, 9000), (4260, 9000), (9000, 9420)):
    acc = [0] * len(CATS)
    for p in sq:
        for i, v in enumerate(flows(p, lo, hi)):
            acc[i] += v
    tax = sum(x[4] for x in ad if x[1] in sq and lo < x[0] <= hi)
    eco = acc[CATS.index('eco')]
    print(f'  ({lo}, {hi}]: ' + ' '.join(f'{c} {k(v)}' for c, v in zip(CATS, acc) if abs(v) >= 1000) + f"｜捐兵税 {k(tax)}＝eco 的 {100*tax/max(1, eco):.1f}%｜打真人＝eco 的 {100*-acc[CATS.index('atkHuman')]/max(1, eco):.0f}%")
bt = [e for e in ev if e['p'] in sq and e['type'] == 'boat' and e.get('ok', True) and e.get('troops', 0) >= 10e3]
for e in bt:
    print(f"  船 t={e['t']} {sq[e['p']]} 载 {k(e['troops'])} 出发前存兵 {k(e.get('B0', 0))} 手续费（存兵的 32/1024）{k(int(e.get('B0', 0) * 32 / 1024))}")
print(f"  ≥10k 的船 {len(bt)} 条：载 {k(sum(e['troops'] for e in bt))}，手续费合计 {k(sum(int(e.get('B0', 0) * 32 / 1024) for e in bt))}")
sb = [e for e in ev if e['p'] in sq and e['type'] == 'boat' and e.get('ok', True) and e.get('troops', 0) < 10e3]
late = [e for e in sb if e['t'] >= 8900]
print(f"  <10k 的船 {len(sb)} 条：载 {k(sum(e['troops'] for e in sb))}，手续费 {k(sum(e['fee'] for e in sb))}；其中 t≥8900 的 {len(late)} 条（{late[0]['t']}–{late[-1]['t']}，pct 全为 {sorted(set(e['pct'] for e in late))}）载 {k(sum(e['troops'] for e in late))}、手续费 {k(sum(e['fee'] for e in late))}：" +
      ' '.join(f"{b}×{sum(1 for e in late if sq[e['p']] == b)}" for b in sorted(set(sq[e['p']] for e in late))))

print('== §8b 调度日志的受赠方（leo_tx 活着时 t<2697；以及 t<3213、3213–4284）==')
for lo, hi in ((0, 2697), (0, 3213), (3213, 4284)):
    c = defaultdict(lambda: [0, 0])
    for d_ in J['dispatch']:
        if lo <= d_['t'] < hi:
            b = sq.get(d_.get('q'), str(d_.get('q')))
            c[b][0] += 1; c[b][1] += 1 if d_.get('exec') else 0
    print(f'  日志拍 {lo}–{hi}: ' + ' '.join(f'{b}:{v[0]} 条/落地 {v[1]}' for b, v in sorted(c.items(), key=lambda kv: -kv[1][0])))

print('== §9 后排四号（alex_k、zero_7、noah88、kaito9）与 riku_x：密度、是否被真人打过 ==')
for b in ('alex_k', 'zero_7', 'noah88', 'kaito9', 'riku_x'):
    p = pid[b]
    hit = [e for e in ev if e.get('q') == p and e['p'] in team and team[e['p']] != OUR and e['type'] in ('attack', 'boat-land') and e['t'] >= 3000]
    print(f'  {b}: 密度 ' + ' '.join(f"{t}:{at(p, t)[1]/max(1, at(p, t)[0]):.0f}" for t in range(3000, 9001, 600)) + f"｜t≥3000 被敌方真人打 {len(hit)} 次 {k(sum(e.get('troops', 0) for e in hit))}")

print('== §10 峰值地 ≥20k 的非我方真人：全程被真人拿走的地归谁（pairAll）==')
lost = defaultdict(lambda: defaultdict(int))
for w, x, b, n in J['pairAll']:
    if b in team and x in team:
        lost[b][x] += n
for p in sorted((p for p in P if p not in sq and P[p]['peakTerr'] >= 20000), key=lambda p: -P[p]['peakTerr']):
    tot_ = sum(lost[p].values())
    if not tot_:
        continue
    s_ = sum(n for x, n in lost[p].items() if x in sq)
    r_ = sum(n for x, n in lost[p].items() if x not in sq and team[x] == OUR)
    top = sorted(lost[p].items(), key=lambda kv: -kv[1])[:4]
    print(f"  {nm(p)} 峰值 {P[p]['peakTerr']}@{P[p]['peakT']} 阵亡 {P[p]['deathT']}：被真人拿走 {tot_} 格，编队 {s_}（{100*s_/tot_:.0f}%）、T3 路人 {r_}（{100*r_/tot_:.0f}%）｜" + ' '.join(f'{nm(x)}:{n}' for x, n in top))

print('== §11 ryan_m 与 过敏党(#21) 5900–6600 的互打；ryan_m、talon5 的地 ==')
b = [e for e in ev if e.get('q') == R and e['p'] == 21 and e['type'] in ('attack', 'boat-land') and 5900 <= e['t'] < 6600]
print(f"  过敏党→ryan_m：{len(b)} 条 {k(sum(e['troops'] for e in b))}，t={b[0]['t']}–{b[-1]['t']}")
a = [e for e in ev if e['p'] == R and e['type'] == 'attack' and e.get('q') == 21 and 5900 <= e['t'] < 6600]
print(f"  ryan_m→过敏党：{len(a)} 条 {k(sum(e['troops'] for e in a))}，t={a[0]['t']}–{a[-1]['t']}")
w_ = [r for r in J['pairsW'] if 5900 <= r['w'] * 100 < 6600 and {r['a'], r['b']} == {R, 21}]
print('  pairsW 5900–6600：' + '；'.join(f"{nm(a_)}→{nm(b_)} 投 {k(sum(r['sent'] for r in w_ if r['a'] == a_))} 拿地 {sum(r['tiles'] for r in w_ if r['a'] == a_)}" for a_, b_ in ((R, 21), (21, R))))
print('  ryan_m 地/兵：' + ' '.join(f'{t}:{at(R, t)[0]}/{k(at(R, t)[1])}' for t in (5900, 6000, 6100, 6200, 6300, 6400, 6500, 6600)))
print('  talon5 地：' + ' '.join(f'{t}:{at(T5, t)[0]}' for t in (7200, 7500, 7800, 8100, 8400)))
print(f"  AngloFrenchGerman(#0) 全程被拿走的地 {P[0]['tilesLost']} 格；地 " + ' '.join(f'{t}:{v[0]}' for t, v in sorted(hs(0).items()) if 3000 <= t <= 6600))

print('== §12 机器人锁逐拍（解析 shadow.mjs --cold --floor 的逐样本输出 /tmp/c136-r05/work/A037-floor.txt）==')
fl = f'/tmp/c136-r05/work/{M}-floor.txt'
if os.path.exists(fl):
    import re
    rows = defaultdict(list)
    for ln in open(fl, encoding='utf-8'):
        m = re.match(r'\[留底\] t=(\d+) (\S+) 兵 (\d+) 地 (\d+)｜相邻机器人 (\d+) 个（共 (\d+) 格.*safeFinite=(\d+).*此刻过得了留底的机器人目标 (\d+) 个', ln)
        if m:
            t, b_, B_, L_, n_, land, sf, ok = m.groups()
            rows[int(t)].append((b_, int(n_), int(land), int(ok)))
    tw = tl = 0
    for t in sorted(rows):
        w = [x for x in rows[t] if x[1] > 0]
        lk = [x for x in w if x[3] == 0]
        tw += len(w); tl += len(lk)
        print(f'  t={t}: 有相邻机器人的号 {len(w)}，其中没有可打目标的 {len(lk)}；各号相邻机器人的地逐号相加 {sum(x[2] for x in w)}（同一个机器人挨着两个号会重复计）')
    print(f'  合计 {tl}/{tw}；605–905 四拍 {sum(1 for t in (605, 705, 805, 905) for x in rows[t] if x[1] > 0 and x[3] == 0)}/{sum(1 for t in (605, 705, 805, 905) for x in rows[t] if x[1] > 0)}')
else:
    print('  （先运行 shadow.mjs A037 --cold --quiet --t0 590 --t1 1810 --floor 605,705,…,1805 > /tmp/c136-r05/work/A037-floor.txt）')

print('== §13 引擎陆攻结算（game.js expandAttack L1007-1010、damage L1062-1074）的算术核对 ==')
print('  每推一圈 cnt 格：进攻方付 2×cnt + 2×def + 对方反击兵，def = cnt×守方存兵 ÷ (1 + 10×守方地÷16) ≈ cnt×1.6×守方密度；守方损失 def。')
print('  → 进攻方每格约付 3.2×守方密度 + 2；守方每丢 1% 的地丢 1.6% 的兵（存兵 ∝ 地^1.6）；把守方从 L0 打到 L* 约需 2×B0×(1−(L*/L0)^1.6) + 2×(L0−L*)。')


def kill_cost(B0, L0, Ls):
    return 2 * B0 * (1 - (Ls / L0) ** 1.6) + 2 * (L0 - Ls)


L5 = pid['leo_tx']
s5 = J['S10'][str(L5)]
i0 = bisect.bisect_right(s5['t'], 2590) - 1
B0, L0 = s5['bal'][i0], s5['terr'][i0]
print(f'  (a) leo_tx 2590 起挨打：起点 {L0} 格/{k(B0)}；实际 地/兵 对 公式预测的兵（不含其间利息）：' +
      ' '.join(f"{s5['t'][i]}:{s5['terr'][i]}/{k(s5['bal'][i])}→{k(B0 * (s5['terr'][i] / L0) ** 1.6)}" for i in range(i0, len(s5['t'])) if s5['t'][i] <= 2690 and (s5['t'][i] - 2590) % 20 == 0))
pk = P[L5]['peakTerr']
print(f"  (b) 把 leo_tx（{L0} 格/{k(B0)}，峰值 {pk}，四分之一线 {pk // 4}）打到除名线约需 {k(kill_cost(B0, L0, pk // 4))}；kakoscsiga 2590 出 513k。" +
      f"按公式反推：leo_tx 存兵 ≥ {k((513e3 - 2 * (L0 - pk // 4)) / (2 * (1 - (pk // 4 / L0) ** 1.6)))} 时 513k 不够（重放推演 whatif_bal.mjs 的结果是多 25k 即 269k 就活下来，其间有利息）")
h1 = hs(1)
for t in (1500, 1800, 2100, 2400):
    L_, B_ = h1[t]
    pk1 = max(v[0] for tt, v in h1.items() if tt <= t)
    print(f"  (c) t={t} kakoscsiga {L_} 格/{k(B_)}（此前峰值 {pk1}）：打到除名线约需 {k(kill_cost(B_, L_, pk1 // 4))}")
print(f"  (d) 弃子线 1.65×：进攻兵 A=1.65×B 时按公式守方还剩 {(1 - 1.65 / 2) ** (1 / 1.6) * 100:.0f}% 的地；A=1.78×B 时剩 {(1 - 1.78 / 2) ** (1 / 1.6) * 100:.0f}%（＝四分之一线，守方在峰值地时）；A=2.04×B（leo_tx）时公式给不出正数＝打穿")
print(f"  (e) 报价核对：Mr. FC t=3205 密度 41.3 → 3.2×41.3+2 = {3.2 * 41.3 + 2:.1f}（shadow.mjs --nb 的「每格价」134.1）；zexos1 3871–3885 挨 2.96M 全仓（自己 3.67M/48,073 格）：A/B={2.96 / 3.67:.2f} → 公式剩 {(1 - 2.96 / 3.67 / 2) ** (1 / 1.6) * 100:.0f}% 的地")
print('  (f) A 类评分式（Vb L4467：5000 + 被打量÷存兵×1200 + (105−对方密度)×20 + min(2200, 对方地÷18)），代入 shadow.mjs --bots zero_7 --don-probe 2595 的数：')
for who_, atk, Bp, Lp in (('leo_tx', 512609, 246367, 2951), ('riku_x', 39012, 565303, 13266)):
    sc = 5000 + atk / Bp * 1200 + (105 - Bp / Lp) * 20 + min(2200, Lp / 18)
    print(f'      {who_}: 被打 {k(atk)}＝{atk / Bp:.2f}×存兵，密度 {Bp / Lp:.1f}，地 {Lp} → {sc:,.0f} 分' + ('（实际在 L4456 被判弃子，没有进入评分）' if who_ == 'leo_tx' else '（实际入选）'))
print('  (g) 2400–2700 拍全场落地的捐兵（allDon）：' + '；'.join(f"t={x[0]} {nm(x[1])}→{nm(x[2])} 到账 {k(x[3])}" for x in J['allDon'] if 2400 <= x[0] <= 2700))
print(f"  (h) 配额：t=2595 上限 153 点（日志 dispatch[].sim.extra.cap），leo_tx 用过 0 点 → 按每点 1,821 兵最多能收 {k(153 * 1821)}；zero_7 2595 拍想捐 137,857 兵，日志试算要 77 点")
print(f"  (i) 公式：A=513k 对 B=246k+138k → A/B={513 / (246 + 138):.2f} → 剩 {(1 - 513 / (246 + 138) / 2) ** (1 / 1.6) * 100:.0f}% 的地（重放推演 whatif_bal.mjs --at 2606 --add 137857：2,706→1,558 格＝起点 2,951 的 {1558 / 2951 * 100:.0f}%）")
