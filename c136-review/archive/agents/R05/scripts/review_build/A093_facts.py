# A093_facts.py — A093 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / quota_room.py / shadow_gap.py /
# floor_tally.py / bot_fate.mjs / spawn_voronoi.mjs / shadow.mjs …）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A093.json 机械算出（match_truth.mjs 的逐拍重放产物）。
# 用法：python3 scripts/review_build/A093_facts.py [--sec 1,2,…]
import json, bisect, statistics, sys
from collections import defaultdict, Counter

M = 'A093'
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
HS = J['HS']
T30 = J['T30']
CATS = J['cats']
LAND = J['map']['land']
H = J['humans']
a = sys.argv[1:]
SEC = set(a[a.index('--sec') + 1].split(',')) if '--sec' in a else None
on = lambda n: SEC is None or str(n) in SEC


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


def flows(p, t0, t1):
    f = J['F30'][str(p)]
    i0 = bisect.bisect_right(f['t'], t0) - 1
    i1 = bisect.bisect_right(f['t'], t1) - 1
    x = f['flows'][i0] if i0 >= 0 else [0] * len(CATS)
    y = f['flows'][i1]
    return {c: y[j] - x[j] for j, c in enumerate(CATS)}


def contact(p, t):
    c = J['C30'][str(p)]
    i = bisect.bisect_right(c['t'], t) - 1
    return {x: c[x][i] for x in ('neut', 'eh', 'el', 'bot', 'mateS', 'mateO')}


def alive_at(p, t):
    return not (P[p]['deathT'] >= 0 and P[p]['deathT'] <= t)


def t30(t):
    return bisect.bisect_right(T30['t'], t) - 1


def hs(p, t):
    i = HS['t'].index(t)
    return HS['terr'][i][p], HS['bal'][i][p]


ORDER = ['zero_7', 'sora_w', 'ryan_m', 'zexos1', 'alex_k', 'kaito9', 'noah88', 'riku_x', 'leo_tx']

if on(1):
    print('§1 各队 地/兵/密度，编队对各队的兵力比（T30；下标 0=机器人与无队，1..3=队）')
    for t in (900, 1200, 1500, 2100, 2400, 3000, 3210, 3600, 4200, 4260, 4800, 5400, 6000):
        i = t30(t)
        land, bal = T30['land'][i], T30['bal'][i]
        sl, sb = T30['squadLand'][i], T30['squadBal'][i]
        row = '｜'.join(f'T{j} {100*land[j]/LAND:.1f}%/{k(bal[j])}/密{bal[j]/max(1,land[j]):.0f}' for j in (1, 2, 3))
        print(f'   t={T30["t"][i]}: {row}｜机 {100*land[0]/LAND:.1f}%｜编队 {100*sl/LAND:.1f}%（{sl} 格）/{k(sb)}/密{sb/max(1,sl):.0f}'
              f'｜编队兵÷T2 兵 {sb/max(1,bal[2]):.2f}、÷T3 兵 {sb/max(1,bal[3]):.2f}｜编队占 T1 地 {100*sl/max(1,land[1]):.0f}%、兵 {100*sb/max(1,bal[1]):.0f}%')

if on(2):
    print('§2 接敌面：每 300 拍哪些号边界上有在线敌方真人的格子（C30 的 eh>0），没有接敌面的号握着编队多少兵')
    for t in range(900, 6001, 300):
        fr, nofr, tb, nb = [], [], 0, 0
        for b in ORDER:
            p = pid[b]
            if not alive_at(p, t):
                continue
            L, B = at(p, t)
            c = contact(p, t)
            tb += B
            if c['eh'] > 0:
                fr.append(f'{b}({c["eh"]})')
            else:
                nofr.append(b); nb += B
        print(f'   t={t}: 接敌 {len(fr)} 个 {" ".join(fr) or "-"}｜不接敌 {len(nofr)} 个，握兵 {k(nb)}（编队 {k(tb)} 的 {100*nb/max(1,tb):.0f}%）')
    print('   各号「边界上没有在线敌方真人」的连续区间（按 30 拍采样，≥300 拍才列）：')
    for b in ORDER:
        p = pid[b]
        c = J['C30'][str(p)]
        segs, cur = [], None
        for i, t in enumerate(c['t']):
            if t < 600 or not alive_at(p, t):
                continue
            if c['eh'][i] == 0:
                cur = [t, t] if cur is None else [cur[0], t]
            else:
                if cur and cur[1] - cur[0] >= 300:
                    segs.append(cur)
                cur = None
        if cur and cur[1] - cur[0] >= 300:
            segs.append(cur)
        print(f'      {b}: ' + ('、'.join(f'{x}–{y}' for x, y in segs) or '无'))

if on(3):
    print('§3 贴着编队的路人队友（72 Hours a Dang Day#13、Enjoy#14）和其他 T1 路人：地/兵（HS，每 300 拍一个点）')
    for q in (13, 14, 9, 39, 17):
        print(f'   {nm(q)} 出生 {P[q]["spawn"]} 阵亡 {P[q]["deathT"]} 离场 {P[q]["leftT"]}：' + '；'.join(f'{t}: {hs(q, t)[0]}/{k(hs(q, t)[1])}' for t in (1500, 2100, 2400, 3000, 3600, 4200, 4800, 5400)))
    don_sq_to_r = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] in sq and e['q'] not in sq]
    don_r_to_sq = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] not in sq and e['q'] in sq]
    print(f'   我方号 → 路人队友的捐兵 {len(don_sq_to_r)} 笔；路人队友 → 我方号 {len(don_r_to_sq)} 笔 到账 {k(sum(e["got"] for e in don_r_to_sq))}：'
          + '；'.join(f't={e["t"]} {nm(e["p"])}→{nm(e["q"])} {k(e["got"])}' for e in don_r_to_sq[:14]))

if on(4):
    print('§4 调度日志的受赠方分布（J.dispatch），按配额分段；括号里是落地条数')
    for lo, hi in ((0, 2142), (2142, 3213), (3213, 4284), (4284, 99999)):
        D = [d for d in J['dispatch'] if lo <= d['t'] < hi]
        c = Counter(d['qName'].replace('[APEX] ', '') for d in D)
        e = Counter(d['qName'].replace('[APEX] ', '') for d in D if d['exec'])
        kinds = Counter(d['kind'].replace('_dispatch', '') for d in D)
        print(f'   [{lo},{hi})：{len(D)} 条（落地 {sum(e.values())}）｜受赠方 ' + '、'.join(f'{q} {n}（{e.get(q, 0)}）' for q, n in c.most_common())
              + '｜类别 ' + '、'.join(f'{x} {n}' for x, n in kinds.most_common()))
    print('   2142–3213 拍各受赠方当拍的状态（发给它的日志条数；其中它当拍有在线敌邻的条数；它的地中位）：')
    for b in ORDER:
        D = [d for d in J['dispatch'] if 2142 <= d['t'] < 3213 and d['q'] == pid[b]]
        if not D:
            continue
        fr = sum(1 for d in D if contact(pid[b], d['t'])['eh'] > 0)
        print(f'      {b}: {len(D)} 条，当拍有敌邻 {fr} 条，地中位 {int(statistics.median(at(pid[b], d["t"])[0] for d in D))}')

if on(5):
    print('§5 1806/1841 拍的同拍连发批前后：存兵与密度（S10）')
    for b in ('zero_7', 'riku_x', 'alex_k'):
        p = pid[b]
        print(f'   {b}: ' + '；'.join(f't={t} 地 {at(p, t)[0]} 兵 {k(at(p, t)[1])} 密 {at(p, t)[1]/max(1, at(p, t)[0]):.1f}' for t in (1500, 1800, 1840, 1850, 1900, 1980, 2040, 2100, 2400)))
    for q in (49, 23):
        i = HS['t'].index(1500)
        print(f'   {nm(q)}: t=1500 地 {HS["terr"][i][q]} 兵 {k(HS["bal"][i][q])}；t=1800 地 {hs(q, 1800)[0]} 兵 {k(hs(q, 1800)[1])}；阵亡 {P[q]["deathT"]}')

if on(6):
    print('§6 后排捐出方在 T2 打过来之前的厚度，以及打死它们的那几条指令')
    for b in ('riku_x', 'leo_tx', 'zexos1', 'kaito9', 'sora_w', 'zero_7'):
        p = pid[b]
        don = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] == p and 4284 <= e['t'] < 5600]
        hits = [e for e in ev if e['type'] == 'attack' and e['ok'] and e['q'] == p and e['p'] < H and e['p'] not in sq and e['t'] >= 4800 and e['troops'] >= 150000]
        print(f'   {b}: ' + '；'.join(f't={t} 地 {at(p, t)[0]} 兵 {k(at(p, t)[1])} 密 {at(p, t)[1]/max(1, at(p, t)[0]):.0f}' for t in (3300, 4284, 4800, 5090))
              + f'｜4284–5600 拍捐出 {len(don)} 笔 到账 {k(sum(e["got"] for e in don))} 税 {k(sum(e["fee"] for e in don))}'
              + f'｜阵亡 {P[p]["deathT"]}｜≥150k 的来袭：' + '；'.join(f't={e["t"]} {nm(e["p"])} {k(e["troops"])}（当时它 {k(e["tB"])}/{e["tL"]} 格）' for e in hits[:6]))

if on(7):
    print('§7 机器人让出的地里编队拿到多少（pairAll，600 拍一窗；600=机器人合计）')
    for w in (1, 2):
        tot = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x < H)
        ours = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x in sq)
        per = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if ww == w and v == 600 and x < H:
                per[x] += n
        alive = [p['id'] for p in J['players'] if p['id'] < H and p['spawn'] and p['spawn'][0] >= 0 and alive_at(p['id'], 600 * w)]
        o = sorted(per.get(x, 0) for x in alive if x not in sq)
        s = sorted(per.get(x, 0) for x in alive if x in sq)
        print(f'   {600*w}–{600*w+599}: 真人从机器人手里拿走 {tot} 格，编队 {ours}（{100*ours/max(1,tot):.1f}%）｜每人中位：编队 {s[len(s)//2]}、其他在场真人 {o[len(o)//2]}（{len(o)} 人）')
    for t0, t1 in ((900, 1500), (1200, 1500)):
        i0, i1 = t30(t0), t30(t1)
        db = T30['land'][i0][0] - T30['land'][i1][0]
        ds = T30['squadLand'][i1] - T30['squadLand'][i0]
        print(f'   {t0}→{t1}: 机器人与无队的地 少了 {db} 格（{100*db/LAND:.1f}%），编队多了 {ds} 格（{100*ds/LAND:.1f}%）＝ {100*ds/max(1,db):.1f}%'
              + '｜' + '、'.join(f'T{j} +{100*(T30["land"][i1][j]-T30["land"][i0][j])/LAND:.1f}%' for j in (1, 2, 3)))

if on(8):
    print('§8 t=1500 在场真人的地分布与我方号的名次（HS）')
    i = HS['t'].index(1500)
    al = [p['id'] for p in J['players'] if p['id'] < H and HS['terr'][i][p['id']] > 0]
    v = sorted((HS['terr'][i][x] for x in al), reverse=True)
    print(f'   在场 {len(al)} 人：中位 {v[len(v)//2]}、上四分位 {v[len(v)//4]}、下四分位 {v[3*len(v)//4]}、最大 {v[0]}')
    for b in ORDER:
        L = HS['terr'][i][pid[b]]
        print(f'      {b}: {L} 格，第 {1 + sum(1 for x in v if x > L)}/{len(v)} 名')
    below = sum(1 for x in al if x not in sq and HS['terr'][i][x] < statistics.median(HS['terr'][i][pid[b]] for b in ORDER))
    print(f'   地比我方号中位（{int(statistics.median(HS["terr"][i][pid[b]] for b in ORDER))}）还小的其他真人：{below} 个')

if on(9):
    print('§9 zero_7（协调器给的角色 CORNER_APEX_BANK）每 300 拍：地/兵/密度/敌邻格/窗口内 打真人、捐出、收到')
    p = pid['zero_7']
    for t in range(1500, 5401, 300):
        L, B = at(p, t)
        f = flows(p, t, t + 300)
        print(f'   t={t}: 地 {L} 兵 {k(B)} 密 {B/max(1,L):.0f} 敌邻 {contact(p, t)["eh"]}｜后 300 拍 打真人 {k(-f["atkHuman"])} 捐出 {k(-f["donOut"])} 收到 {k(f["donIn"])} 被打掉 {k(-f["dmg"])}')

if on(10):
    print('§10 alex_k 3300–4800 拍：存兵对硬上限（150×地）、窗口内收到的捐兵与打出的兵')
    p = pid['alex_k']
    for t in range(3000, 4801, 150):
        L, B = at(p, t)
        f = flows(p, t, t + 150)
        print(f'   t={t}: 地 {L} 兵 {k(B)} 密 {B/max(1,L):.0f}（硬上限的 {100*B/max(1,150*L):.0f}%）敌邻 {contact(p, t)["eh"]}｜后 150 拍 收到 {k(f["donIn"])} 打真人 {k(-f["atkHuman"])} 出船 {k(-f["boat"])} 被打掉 {k(-f["dmg"])} 利息 {k(f["eco"])}')

if on(11):
    print('§11 编队分段兵力收支（F30 合计）')
    for t0, t1 in ((0, 1500), (1500, 2100), (2100, 3210), (3210, 4260), (4260, 5400), (5400, 6810)):
        tot = defaultdict(int)
        for b in ORDER:
            for c, v in flows(pid[b], t0, t1).items():
                tot[c] += v
        b0 = sum(at(pid[b], t0)[1] for b in ORDER if alive_at(pid[b], t0))
        b1 = sum(at(pid[b], t1)[1] for b in ORDER if alive_at(pid[b], t1))
        print(f'   ({t0},{t1}]: 存兵 {k(b0)}→{k(b1)}｜' + ' '.join(f'{c} {k(tot[c])}' for c in CATS if tot[c]))

if on(12):
    print('§12 交换比（J.pairs：a 打 b 的全程合计；sent=投入的兵，tiles=拿走的格，balDmg=打掉对方的存兵，ret=退回）')
    out = [x for x in J['pairs'] if x['a'] in sq and x['b'] < H and x['b'] not in sq]
    inc = [x for x in J['pairs'] if x['b'] in sq and x['a'] < H and x['a'] not in sq]
    for lab, R in (('编队 → 真人', out), ('真人 → 编队', inc)):
        s, tl, dm, rt = (sum(x[c] for x in R) for c in ('sent', 'tiles', 'balDmg', 'ret'))
        print(f'   {lab}: 投兵 {k(s)}（{sum(x["n"] for x in R)} 条）拿地 {tl} 格 打掉存兵 {k(dm)} 退回 {k(rt)}｜每格 {s/max(1,tl):.0f} 兵（扣退兵 {(s-rt)/max(1,tl):.0f}）')
    by = defaultdict(lambda: [0, 0, 0])
    for x in out:
        by[sq[x['a']]][0] += x['sent']; by[sq[x['a']]][1] += x['tiles']; by[sq[x['a']]][2] += x['ret']
    print('   各号打真人：' + '；'.join(f'{b} {k(v[0])}/{v[1]} 格（每格 {v[0]/max(1,v[1]):.0f}，扣退兵 {(v[0]-v[2])/max(1,v[1]):.0f}）' for b, v in sorted(by.items(), key=lambda z: -z[1][0])))
    byq = defaultdict(lambda: [0, 0])
    for x in inc:
        byq[x['a']][0] += x['sent']; byq[x['a']][1] += x['tiles']
    print('   打编队最多的真人：' + '；'.join(f'{nm(q)} {k(v[0])}/{v[1]} 格' for q, v in sorted(byq.items(), key=lambda z: -z[1][0])[:8]))
    print('   每 600 拍 编队从真人手里拿到 / 被真人拿走的格（pairAll）：' + '；'.join(
        f'{600*w}: +{sum(n for ww, x, v, n in J["pairAll"] if ww == w and x in sq and v < H and v not in sq)} / −{sum(n for ww, x, v, n in J["pairAll"] if ww == w and v in sq and x < H and x not in sq)}' for w in range(1, 12)))

if on(13):
    print('§13 被吃掉的邻居：它的地归了谁（pairAll 全程合计，前 5）')
    for q in (49, 23, 6, 53, 47, 10, 14, 13):
        tk = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if v == q:
                tk[x] += n
        tot = sum(tk.values())
        print(f'   {nm(q)} 峰值 {P[q]["peakTerr"]}@{P[q]["peakT"]} 离场 {P[q]["leftT"]} 阵亡 {P[q]["deathT"]}：被拿走 {tot} 格：' + '、'.join(f'{nm(x)} {n}' for x, n in sorted(tk.items(), key=lambda z: -z[1])[:5]))

S10, C30, F30, cats = J['S10'], J['C30'], J['F30'], CATS

if on(14):
    print('§14 捐兵之后（已落地且到账 ≥100k 的每一笔）：受赠方其后 300 拍对真人的出兵（陆攻+出船，含手续费）与地的变化')
    ev = J['events']
    def terr_at(p, t):
        s = S10[str(p)]
        i = min(range(len(s['t'])), key=lambda j: abs(s['t'][j] - t))
        return s['terr'][i]
    rows = []
    for e in ev:
        if e['type'] != 'donate' or not e.get('ok') or e['p'] not in sq or e['q'] not in sq or e.get('got', 0) < 100000:
            continue
        t, q = e['t'], e['q']
        spent = sum(x.get('troops', 0) + x.get('fee', 0) for x in ev if x['type'] in ('attack', 'boat') and x.get('ok') and x['p'] == q and t < x['t'] <= t + 300 and x['q'] < H and x['q'] not in sq)
        l0, l1 = terr_at(q, t), terr_at(q, t + 300)
        rows.append((t, sq[e['p']], sq[q], e['got'], spent, l0, l1, e.get('logKind')))
    good = [r for r in rows if r[4] >= 0.8 * r[3] and r[6] >= 1.3 * r[5]]
    spent80 = [r for r in rows if r[4] >= 0.8 * r[3]]
    grew = [r for r in rows if r[6] > r[5]]
    shrank = [r for r in rows if r[6] < r[5]]
    print(f'   ≥100k 的 {len(rows)} 笔（到账 {k(sum(r[3] for r in rows))}）：其后 300 拍打真人 ≥ 到账 80% 的 {len(spent80)} 笔；地变多的 {len(grew)} 笔、变少的 {len(shrank)} 笔；两条都满足（出兵 ≥80% 且地 +30%）的 {len(good)} 笔')
    for lo, hi in ((0, 3213), (3213, 4284), (4284, 99999)):
        R = [r for r in rows if lo <= r[0] < hi]
        if R:
            print(f'   t∈[{lo},{hi}): {len(R)} 笔 到账 {k(sum(r[3] for r in R))}｜其后 300 拍受赠方打真人合计 {k(sum(r[4] for r in R))}（同一受赠方的窗口有重叠，会重复计）｜地 变多 {sum(1 for r in R if r[6] > r[5])} 变少 {sum(1 for r in R if r[6] < r[5])} 不变 {sum(1 for r in R if r[6] == r[5])}')
    for r in rows:
        if r[3] >= 400000 or r in good:
            print(f'     t={r[0]} {r[1]}→{r[2]} {k(r[3])}（{r[7]}）｜其后 300 拍打真人 {k(r[4])}｜地 {r[5]}→{r[6]}')

if on(15):
    print('§15 多个号打同一个真人：我方号对 Player 67(#49)、Player 807(#23)、Kazakhstan(#53)、Player 278(#47)、Player 132(#6) 的已执行陆攻（每号 首–末拍、条数、出兵）')
    for q in (49, 23, 53, 47, 6):
        by = defaultdict(list)
        for e in J['events']:
            if e['type'] == 'attack' and e.get('ok') and e['p'] in sq and e['q'] == q:
                by[sq[e['p']]].append(e)
        print(f'   {nm(q)}（阵亡 {P[q]["deathT"]}）：' + '；'.join(f'{b} {min(x["t"] for x in v)}–{max(x["t"] for x in v)} {len(v)} 条 {k(sum(x["troops"] for x in v))}' for b, v in by.items()))

if on(16):
    print('§16 四个从没打过真人的号（sora_w、zexos1、kaito9、leo_tx）：每 600 拍 地/兵/密度、敌邻格数（C30 eh）、累计 利息地租/捐出/被打掉（F30）')
    for p, b in sq.items():
        if b not in ('sora_w', 'zexos1', 'kaito9', 'leo_tx'):
            continue
        s, c, f = S10[str(p)], C30[str(p)], F30[str(p)]
        def near(arr_t, arr, t):
            i = min(range(len(arr_t)), key=lambda j: abs(arr_t[j] - t))
            return arr[i]
        parts = []
        for t in (1200, 1800, 2400, 3000, 3210, 3600, 4200, 4800, 5400):
            parts.append(f'{t}: {near(s["t"], s["terr"], t)}/{k(near(s["t"], s["bal"], t))}/{near(s["t"], s["bal"], t)/max(1, near(s["t"], s["terr"], t)):.0f}·敌邻{near(c["t"], c["eh"], t)}')
        tot = flows(p, -1, 10 ** 9)   # F30 是累计值：取末行
        print(f'   {b}: ' + ' | '.join(parts))
        print(f'      全程 利息地租 {k(tot["eco"])} 捐出(含税) {k(-tot["donOut"])} 出船 {k(-tot["boat"])} 打机器人/中立 {k(-tot["atkBot"] - tot["atkNeutral"])} 打真人 {k(-tot["atkHuman"])} 被打掉 {k(-tot["dmg"])}｜软上限 = 100×地 = {k(100*near(s["t"], s["terr"], 3000))}，硬上限 150×地 = {k(150*near(s["t"], s["terr"], 3000))}')
