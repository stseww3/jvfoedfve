# A034_facts.py — A034 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / quota_room.py / shadow_gap.py /
# floor_tally.py / bot_fate.mjs / spawn_voronoi.mjs / shadow.mjs …）不直接给的数字。
# 全部从 /tmp/c136-r05/truth/A034.json 机械算出（match_truth.mjs 的逐拍重放产物）。
# 用法：python3 scripts/review_build/A034_facts.py [--sec 1,2,…]
import json, bisect, statistics, sys, math
from collections import defaultdict, Counter

M = 'A034'
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


ORDER = ['ryan_m', 'zero_7', 'talon5', 'kaito9', 'sora_w', 'noah88', 'alex_k', 'leo_tx', 'riku_x']
S10, C30, F30, cats = J['S10'], J['C30'], J['F30'], CATS
NT = len(T30['land'][0]) - 1   # 真人队数
OUR = J['ourTeam']
ENEMY = [j for j in range(1, NT + 1) if j != OUR]

if on(1):
    print('§1 各队 地/兵/密度，编队对各队的兵力比（T30；下标 0=机器人与无队）')
    for t in (600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800):
        i = t30(t)
        land, bal = T30['land'][i], T30['bal'][i]
        sl, sb = T30['squadLand'][i], T30['squadBal'][i]
        row = '｜'.join(f'T{j} {100*land[j]/LAND:.1f}%/{k(bal[j])}/密{bal[j]/max(1,land[j]):.0f}' for j in range(1, NT + 1))
        print(f'   t={T30["t"][i]}: {row}｜机 {100*land[0]/LAND:.1f}%｜编队 {100*sl/LAND:.1f}%（{sl} 格）/{k(sb)}/密{sb/max(1,sl):.0f}｜'
              + '、'.join(f'编队兵÷T{j} 兵 {sb/max(1,bal[j]):.2f}' for j in ENEMY))

if on(2):
    print('§2 接敌面：每 300 拍哪些号边界上有在线敌方真人的格子（C30 的 eh>0）；没有接敌面的号握着编队多少兵；贴着机器人的号')
    for t in range(900, 5101, 300):
        fr, nofr, tb, nb, bots = [], [], 0, 0, []
        for b in ORDER:
            p = pid[b]
            if not alive_at(p, t):
                continue
            L, B = at(p, t)
            c = contact(p, t)
            tb += B
            if c['bot'] > 0:
                bots.append(f'{b}({c["bot"]})')
            if c['eh'] > 0:
                fr.append(f'{b}({c["eh"]})')
            else:
                nofr.append(b); nb += B
        print(f'   t={t}: 接敌 {len(fr)} 个 {" ".join(fr) or "-"}｜不接敌 {len(nofr)} 个 {" ".join(nofr) or "-"}，握兵 {k(nb)}（编队 {k(tb)} 的 {100*nb/max(1,tb):.0f}%）｜贴着机器人 {" ".join(bots) or "-"}')

if on(3):
    print('§3 我方队的路人队友，以及贴着编队的几个敌人：地/兵（HS，每 300 拍一个点）')
    mates = [p['id'] for p in J['players'] if p['team'] == OUR and p['id'] not in sq]
    for q in mates + [10, 11, 12, 20, 2, 9, 1, 7, 13]:
        pts = '；'.join(f'{t}: {hs(q, t)[0]}/{k(hs(q, t)[1])}' for t in (900, 1200, 1500, 1800, 2100, 2400, 3000, 3600, 4200, 4800) if t in HS['t'])
        print(f'   {nm(q)} 出生 {P[q]["spawn"]} 峰值 {P[q]["peakTerr"]}@{P[q]["peakT"]} 阵亡 {P[q]["deathT"]} 离场 {P[q]["leftT"]}：{pts}')
    don_sq_to_r = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] in sq and e['q'] not in sq]
    don_r_to_sq = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] not in sq and e['q'] in sq]
    print(f'   我方号 → 路人队友的捐兵 {len(don_sq_to_r)} 笔；路人队友 → 我方号 {len(don_r_to_sq)} 笔')

if on(4):
    print('§4 已执行的捐兵（我方号之间）：按类别、按受赠方、税率；捐出方当拍的地/兵/密度')
    D = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] in sq and e['q'] in sq]
    got, fee = sum(e['got'] for e in D), sum(e['fee'] for e in D)
    print(f'   {len(D)} 笔 到账 {k(got)} 税 {k(fee)}（税÷到账 {100*fee/max(1,got):.1f}%；每笔 pct 中位 {int(statistics.median(e["pct"] for e in D))}＝存兵的 {100*statistics.median(e["pct"] for e in D)/1024:.0f}%）')
    byq = defaultdict(lambda: [0, 0, 0])
    for e in D:
        byq[sq[e['q']]][0] += 1; byq[sq[e['q']]][1] += e['got']; byq[sq[e['q']]][2] += e['fee']
    print('   按受赠方：' + '；'.join(f'{b} {v[0]} 笔 {k(v[1])}（税 {k(v[2])}）' for b, v in sorted(byq.items(), key=lambda z: -z[1][1])))
    byp = defaultdict(lambda: [0, 0, 0])
    for e in D:
        byp[sq[e['p']]][0] += 1; byp[sq[e['p']]][1] += e['got']; byp[sq[e['p']]][2] += e['fee']
    print('   按捐出方：' + '；'.join(f'{b} {v[0]} 笔 {k(v[1])}（税 {k(v[2])}，税÷到账 {100*v[2]/max(1,v[1]):.0f}%）' for b, v in sorted(byp.items(), key=lambda z: -z[1][1])))
    kinds = Counter(d['kind'].replace('_dispatch', '') for d in J['dispatch'])
    print('   日志类别：' + '、'.join(f'{x} {n}' for x, n in kinds.most_common()) + f'｜日志 {len(J["dispatch"])} 条，落地 {sum(1 for d in J["dispatch"] if d["exec"])} 条')
    for e in D:
        qL, qB = at(e['q'], e['t'])
        c = contact(e['q'], e['t'])
        inc = S10[str(e['q'])]
        i = bisect.bisect_right(inc['t'], e['t']) - 1
        print(f'     t={e["t"]} {sq[e["p"]]}（{e["L0"]} 格/{k(e["B0"])}/密 {e["B0"]/max(1,e["L0"]):.0f}）→ {sq[e["q"]]}（{e["qL0"]} 格/{k(e["qB0"])}/密 {e["qB0"]/max(1,e["qL0"]):.0f}，正被真人打 {k(inc["inH"][i])}）到账 {k(e["got"])} 税 {k(e["fee"])}')

if on(5):
    print('§5 打真人的同拍批（同号同拍 ≥5 条、目标是真人）：批前存兵、这一批合计打出（含手续费）、占比、目标当时的地/兵，批后 60/150 拍自己的地/兵')
    per = defaultdict(list)
    for e in ev:
        if e['type'] == 'attack' and e['p'] in sq and e['q'] < H and e['q'] not in sq:
            per[(e['p'], e['t'])].append(e)
    for (p, t), es in sorted(per.items(), key=lambda z: z[0][1]):
        if len(es) < 5:
            continue
        B0 = es[0]['B0']
        out = sum(x.get('troops', 0) + x.get('fee', 0) for x in es if x['ok'])
        tg = Counter(nm(x['q']) for x in es)
        L60, B60 = at(p, t + 60)
        L150, B150 = at(p, t + 150)
        print(f'   t={t} {sq[p]} ×{len(es)}（pct {min(x["pct"] for x in es)}–{max(x["pct"] for x in es)}）批前 {es[0]["L0"]} 格/{k(B0)} 打出 {k(out)}（{100*out/max(1,B0):.0f}%；第一条 {k(es[0].get("troops",0))}）→ ' + '、'.join(f'{a_}×{n}' for a_, n in tg.items())
              + f'（目标 {es[0]["tL"]} 格/{k(es[0]["tB"])}）｜+60 拍 {L60} 格/{k(B60)}，+150 拍 {L150} 格/{k(B150)}')

if on(6):
    print('§6 阵亡号：死前 600/300/60 拍的 地/兵/密度，≥150k 的来袭指令，死前 600 拍收到的捐兵')
    for b in ORDER:
        p = pid[b]
        dt = P[p]['deathT']
        if dt < 0:
            dt = J['endTick']
        pts = '；'.join(f't={t} {at(p, t)[0]} 格/{k(at(p, t)[1])}/密 {at(p, t)[1]/max(1, at(p, t)[0]):.0f}' for t in (dt - 600, dt - 300, dt - 150, dt - 60))
        hits = [e for e in ev if e['type'] == 'attack' and e['ok'] and e['q'] == p and e['p'] < H and e['p'] not in sq and e['t'] >= dt - 700 and e['troops'] >= 150000]
        don = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['q'] == p and e['t'] >= dt - 600]
        own = [e for e in ev if e['type'] in ('attack', 'boat') and e['ok'] and e['p'] == p and e['t'] >= dt - 600 and e['q'] < H]
        print(f'   {b}（阵亡 {P[p]["deathT"]}，峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}）：{pts}')
        print(f'      来袭 ≥150k：' + ('；'.join(f't={e["t"]} {nm(e["p"])} {k(e["troops"])}（当时它 {e["tL"]} 格/{k(e["tB"])}）' for e in hits[:9]) or '无')
              + f'｜死前 600 拍收到捐兵 {len(don)} 笔 {k(sum(e["got"] for e in don))}，自己打真人 {len(own)} 条 {k(sum(e["troops"] for e in own))}')

if on(7):
    print('§7 机器人让出的地里编队拿到多少（pairAll，600 拍一窗；600=机器人合计）')
    for w in (0, 1, 2, 3):
        tot = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x < H)
        ours = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x in sq)
        per = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if ww == w and v == 600 and x < H:
                per[x] += n
        alive = [p['id'] for p in J['players'] if p['id'] < H and p['spawn'] and p['spawn'][0] >= 0 and alive_at(p['id'], 600 * w)]
        o = sorted(per.get(x, 0) for x in alive if x not in sq)
        s = sorted(per.get(x, 0) for x in alive if x in sq)
        print(f'   {600*w}–{600*w+599}: 真人从机器人手里拿走 {tot} 格，编队 {ours}（{100*ours/max(1,tot):.1f}%；人数占 {100*len(s)/max(1,len(s)+len(o)):.0f}%）｜每人中位：编队 {s[len(s)//2]}、其他在场真人 {o[len(o)//2]}（{len(o)} 人）')
    for t0, t1 in ((600, 900), (900, 1200), (1200, 1500), (900, 1500), (1500, 1800), (1800, 2100)):
        i0, i1 = t30(t0), t30(t1)
        db = T30['land'][i0][0] - T30['land'][i1][0]
        ds = T30['squadLand'][i1] - T30['squadLand'][i0]
        print(f'   {t0}→{t1}: 机器人与无队的地 少了 {db} 格（{100*db/LAND:.1f}%），编队多了 {ds} 格（{100*ds/LAND:.1f}%）｜' + '、'.join(f'T{j} {100*(T30["land"][i1][j]-T30["land"][i0][j])/LAND:+.1f}%' for j in range(1, NT + 1))
              + f'｜编队兵 {k(T30["squadBal"][i0])}→{k(T30["squadBal"][i1])}；' + '、'.join(f'T{j} 兵 {k(T30["bal"][i0][j])}→{k(T30["bal"][i1][j])}' for j in ENEMY))

if on(8):
    print('§8 在场真人的地分布与我方号的名次（HS）')
    for t in (600, 900, 1200, 1500, 2100, 3000):
        i = HS['t'].index(t)
        al = [p['id'] for p in J['players'] if p['id'] < H and HS['terr'][i][p['id']] > 0]
        v = sorted((HS['terr'][i][x] for x in al), reverse=True)
        o = sorted((HS['terr'][i][x] for x in al if x not in sq), reverse=True)
        s = sorted((HS['terr'][i][pid[b]] for b in ORDER if HS['terr'][i][pid[b]] > 0), reverse=True)
        ranks = ' '.join(f'{b} {1 + sum(1 for x in v if x > HS["terr"][i][pid[b]])}' for b in ORDER if HS['terr'][i][pid[b]] > 0)
        print(f'   t={t} 在场 {len(al)} 人：其他真人中位 {o[len(o)//2]}（上四分位 {o[len(o)//4]}、下四分位 {o[3*len(o)//4]}）｜我方号中位 {s[len(s)//2]}（{s[-1]}–{s[0]}）｜名次：{ranks}')

if on(11):
    print('§11 编队分段兵力收支（F30 合计）')
    segs = ((0, 900), (900, 1500), (1500, 2100), (2100, 3600), (3600, 4200), (4200, 4800), (4800, J['endTick']))
    for t0, t1 in segs + ((0, J['endTick']),):
        tot = defaultdict(int)
        for b in ORDER:
            for c, v in flows(pid[b], t0, t1).items():
                tot[c] += v
        b0 = sum(at(pid[b], t0)[1] for b in ORDER if alive_at(pid[b], t0))
        b1 = sum(at(pid[b], t1)[1] for b in ORDER if alive_at(pid[b], t1))
        l0 = sum(at(pid[b], t0)[0] for b in ORDER if alive_at(pid[b], t0))
        l1 = sum(at(pid[b], t1)[0] for b in ORDER if alive_at(pid[b], t1))
        print(f'   ({t0},{t1}]: 地 {l0}→{l1} 存兵 {k(b0)}→{k(b1)}｜' + ' '.join(f'{c} {k(tot[c])}' for c in CATS if tot[c]))
    print('   各号全程：')
    for b in ORDER:
        tot = flows(pid[b], -1, 10 ** 9)
        print(f'      {b}: ' + ' '.join(f'{c} {k(tot[c])}' for c in CATS if tot[c]))

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
    byt = defaultdict(lambda: [0, 0, 0, 0])
    for x in out:
        byt[x['b']][0] += x['sent']; byt[x['b']][1] += x['tiles']; byt[x['b']][2] += x['ret']; byt[x['b']][3] += x['n']
    print('   编队打得最多的真人：' + '；'.join(f'{nm(q)} {k(v[0])}（{v[3]} 条，退 {k(v[2])}）/{v[1]} 格' for q, v in sorted(byt.items(), key=lambda z: -z[1][0])[:10]))
    byq = defaultdict(lambda: [0, 0, 0])
    for x in inc:
        byq[x['a']][0] += x['sent']; byq[x['a']][1] += x['tiles']; byq[x['a']][2] += x['n']
    print('   打编队最多的真人：' + '；'.join(f'{nm(q)} {k(v[0])}（{v[2]} 条）/{v[1]} 格' for q, v in sorted(byq.items(), key=lambda z: -z[1][0])[:10]))
    print('   每 600 拍 编队从真人手里拿到 / 被真人拿走的格（pairAll）：' + '；'.join(
        f'{600*w}: +{sum(n for ww, x, v, n in J["pairAll"] if ww == w and x in sq and v < H and v not in sq)} / −{sum(n for ww, x, v, n in J["pairAll"] if ww == w and v in sq and x < H and x not in sq)}' for w in range(1, 10)))

if on(13):
    print('§13 被吃掉的邻居和我方号：它的地归了谁（pairAll 全程合计，前 6；512=变成中立后被谁拿走不在此列）')
    for q in (10, 11, 4, 2, 1, 20, 12) + tuple(pid[b] for b in ORDER):
        tk = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if v == q:
                tk[x] += n
        tot = sum(tk.values())
        print(f'   {nm(q)} 峰值 {P[q]["peakTerr"]}@{P[q]["peakT"]} 离场 {P[q]["leftT"]} 阵亡 {P[q]["deathT"]}：被拿走 {tot} 格：' + '、'.join(f'{nm(x)} {n}' for x, n in sorted(tk.items(), key=lambda z: -z[1])[:6]))

if on(14):
    print('§14 捐兵之后（每一笔已落地的）：受赠方其后 300 拍对真人的出兵（陆攻，含手续费）、被打掉的兵、地的变化')
    def terr_at(p, t):
        s = S10[str(p)]
        i = min(range(len(s['t'])), key=lambda j: abs(s['t'][j] - t))
        return s['terr'][i]
    rows = []
    for e in ev:
        if e['type'] != 'donate' or not e.get('ok') or e['p'] not in sq or e['q'] not in sq:
            continue
        t, q = e['t'], e['q']
        spent = sum(x.get('troops', 0) + x.get('fee', 0) for x in ev if x['type'] in ('attack', 'boat') and x.get('ok') and x['p'] == q and t < x['t'] <= t + 300 and x['q'] < H and x['q'] not in sq)
        f = flows(q, t, t + 300)
        l0, l1 = terr_at(q, t), terr_at(q, t + 300)
        rows.append((t, sq[e['p']], sq[q], e['got'], spent, l0, l1, -f['dmg'], e['fee']))
    grew = [r for r in rows if r[6] > r[5]]
    shrank = [r for r in rows if r[6] < r[5]]
    print(f'   {len(rows)} 笔（到账 {k(sum(r[3] for r in rows))}，税 {k(sum(r[8] for r in rows))}）：其后 300 拍受赠方的地 变多 {len(grew)} 笔、变少 {len(shrank)} 笔、不变 {len(rows)-len(grew)-len(shrank)} 笔；受赠方 300 拍内阵亡 {sum(1 for r in rows if r[6] == 0)} 笔')
    for r in rows:
        print(f'     t={r[0]} {r[1]}→{r[2]} 到账 {k(r[3])} 税 {k(r[8])}｜其后 300 拍：打真人 {k(r[4])}，被打掉 {k(r[7])}，地 {r[5]}→{r[6]}')

if on(15):
    print('§15 多个号打同一个真人：我方号对各真人的已执行陆攻（每号 首–末拍、条数、出兵）')
    tg = Counter(e['q'] for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] in sq and e['q'] < H and e['q'] not in sq)
    for q, _ in tg.most_common(12):
        by = defaultdict(list)
        for e in ev:
            if e['type'] == 'attack' and e.get('ok') and e['p'] in sq and e['q'] == q:
                by[sq[e['p']]].append(e)
        print(f'   {nm(q)}（阵亡 {P[q]["deathT"]} 离场 {P[q]["leftT"]}）：' + '；'.join(f'{b} {min(x["t"] for x in v)}–{max(x["t"] for x in v)} {len(v)} 条 {k(sum(x["troops"] for x in v))}' for b, v in by.items()))

if on(16):
    print('§16 2100 拍以后各号每 300 拍：地/兵/密度·敌邻格（C30 eh）｜窗口内 利息地租 / 打真人 / 捐出 / 收到 / 被打掉')
    for b in ORDER:
        p = pid[b]
        print(f'   {b}:')
        for t in range(2100, 5101, 300):
            if not alive_at(p, t):
                break
            L, B = at(p, t)
            f = flows(p, t, t + 300)
            c = contact(p, t)
            print(f'      t={t}: {L}/{k(B)}/密 {B/max(1,L):.0f}·敌邻 {c["eh"]}·队友邻 {c["mateS"]+c["mateO"]}｜利息地租 {k(f["eco"])} 打真人 {k(-f["atkHuman"])} 捐出 {k(-f["donOut"])} 收到 {k(f["donIn"])} 被打掉 {k(-f["dmg"])}')

k2 = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'


def load_shadow():
    return json.load(open(f'/tmp/c136-r05/work/{M}-shadow.json'))


if on(17):
    print('§17 3380–4300 拍的逐条时间线：≥60k 的 我方打真人（OUT）/ 真人打我方（IN）、已落地的捐兵（DON）、阵亡')
    rows = []
    for e in ev:
        if not (3380 <= e['t'] <= 4300):
            continue
        if e['type'] in ('attack', 'boat') and e.get('ok') and e.get('troops', 0) >= 60000:
            if e['q'] in sq and e['p'] < H and e['p'] not in sq:
                rows.append((e['t'], f'IN  {nm(e["p"])} → {nm(e["q"])} {k2(e["troops"])}（对方 {e["L0"]} 格/{k2(e["B0"])}；我 {e["tL"]} 格/{k2(e["tB"])}）'))
            if e['p'] in sq and e['q'] < H and e['q'] not in sq:
                rows.append((e['t'], f'OUT {nm(e["p"])} → {nm(e["q"])} {k2(e["troops"])}（我 {e["L0"]} 格/{k2(e["B0"])}；对方 {e["tL"]} 格/{k2(e["tB"])}）'))
        if e['type'] == 'donate' and e.get('ok') and e['p'] in sq:
            rows.append((e['t'], f'DON {nm(e["p"])} → {nm(e["q"])} 到账 {k2(e["got"])} 税 {k2(e["fee"])}'))
        if e['type'] == 'died' and e['p'] in sq:
            rows.append((e['t'], f'*** {nm(e["p"])} 阵亡'))
    for t, s in sorted(rows):
        print(f'   {t} {s}')
    print('   每一对「我方号×敌方真人」谁先动手（全程第一条 ≥30k 的已执行陆攻）：')
    first = {}
    for e in ev:
        if e['type'] == 'attack' and e.get('ok') and e.get('troops', 0) >= 30000:
            if e['p'] in sq and e['q'] < H and e['q'] not in sq:
                first.setdefault((e['p'], e['q']), [None, None])
                if first[(e['p'], e['q'])][0] is None:
                    first[(e['p'], e['q'])][0] = e['t']
            if e['q'] in sq and e['p'] < H and e['p'] not in sq:
                first.setdefault((e['q'], e['p']), [None, None])
                if first[(e['q'], e['p'])][1] is None:
                    first[(e['q'], e['p'])][1] = e['t']
    ours = theirs = 0
    for (b, q), (t_out, t_in) in sorted(first.items(), key=lambda z: min(x for x in z[1] if x is not None)):
        who = '我方先' if t_in is None or (t_out is not None and t_out < t_in) else '对方先'
        ours += who == '我方先'
        theirs += who == '对方先'
        print(f'      {nm(b)} × {nm(q)}: 我方第一条 {t_out}，对方第一条 {t_in} → {who}')
    print(f'   合计 {len(first)} 对：我方先动手 {ours} 对，对方先动手 {theirs} 对')

if on(18):
    print('§18 影子决策的构成（按 300 拍）：陆攻决策数（目标 中立/机器人/真人）、打机器人的 pct 中位、pct ≤48（最小额 = 存兵的 4.7%）的占比、调用路径')
    S_ = load_shadow()
    cls = lambda q: 'N' if q == 512 else ('H' if q < H else 'B')
    for lo in range(600, 2400, 300):
        rows = [(r, c) for r in S_['ticks'] if lo <= r['t'] < lo + 300 for c in r['cmds'] if c['k'] == 'attack']
        by = Counter(cls(c['q']) for _, c in rows)
        pb = [c['pct'] for _, c in rows if cls(c['q']) == 'B']
        tb = [c.get('troops', 0) for _, c in rows if cls(c['q']) == 'B']
        pn = [c['pct'] for _, c in rows if cls(c['q']) == 'N']
        paths = Counter(' > '.join(r['sig'].split(' > ')[-5:-3]) for r, c in rows if cls(c['q']) == 'B')
        print(f'   {lo}–{lo+299}: 陆攻决策 {len(rows)}（中立 {by["N"]}、机器人 {by["B"]}、真人 {by["H"]}）｜打机器人 pct 中位 {statistics.median(pb) if pb else "-"}，pct≤48 的 {sum(1 for p in pb if p <= 48)}（{100*sum(1 for p in pb if p <= 48)/max(1,len(pb)):.0f}%），每条兵数中位 {statistics.median(tb) if tb else 0:.0f}'
              f'｜打中立 {len(pn)} 条（pct≤48 的 {sum(1 for p in pn if p <= 48)}）｜路径 ' + '；'.join(f'{p}×{n}' for p, n in paths.most_common(2)))

if on(19):
    print('§19 2100 拍以后影子里每个号对真人的出手：每一段（相邻决策间隔 ≤15 拍归一段）的起止拍、条数、当时密度、pct、出口行；以及捐兵决策')
    S_ = load_shadow()
    for b in ORDER:
        segs = []
        dons = []
        for r in S_['ticks']:
            if r['bot'] != b or r['t'] < 2100:
                continue
            for c in r['cmds']:
                d = r['bal'] / max(1, r['terr'])
                line = [x for x in r['sig'].split(' > ') if x.startswith('buyLand:')]
                if c['k'] == 'attack' and c['q'] < H:
                    if segs and r['t'] - segs[-1]['t1'] <= 15 and segs[-1]['q'] == c['q']:
                        segs[-1]['t1'] = r['t']; segs[-1]['n'] += 1; segs[-1]['pcts'].append(c['pct'])
                    else:
                        segs.append({'t0': r['t'], 't1': r['t'], 'n': 1, 'q': c['q'], 'd': d, 'pcts': [c['pct']], 'line': line[-1] if line else '?', 'bal': r['bal']})
                if c['k'] == 'donate':
                    dons.append(f'{r["t"]}→{nm(c["q"])}（密 {d:.0f}，pct {c["pct"]}）')
        over = sum(1 for s in segs if s['d'] >= 100)
        print(f'   {b}: 打真人 {len(segs)} 段，其中开打时密度 ≥100 的 {over} 段｜' + '；'.join(f'{s["t0"]}–{s["t1"]} ×{s["n"]} → {nm(s["q"])}（密 {s["d"]:.0f}，pct {min(s["pcts"])}–{max(s["pcts"])}，{s["line"]}）' for s in segs[:16]))
        if dons:
            print(f'      捐兵决策 {len(dons)} 条：' + '；'.join(dons[:10]))

if on(20):
    print('§20 ProfChaos(#11) 被分掉的过程：它和 [SPARTUS] 300(#12)、kaito9、noah88 每 300 拍的 地/兵（HS、S10）')
    for t in (1800, 2100, 2400, 2700, 3000, 3300):
        print(f'   t={t}: ProfChaos {hs(11, t)[0]} 格/{k(hs(11, t)[1])}｜[SPARTUS] 300 {hs(12, t)[0]} 格/{k(hs(12, t)[1])}（密 {hs(12, t)[1]/max(1,hs(12, t)[0]):.0f}）｜kaito9 {at(pid["kaito9"], t)[0]}/{k(at(pid["kaito9"], t)[1])}｜noah88 {at(pid["noah88"], t)[0]}/{k(at(pid["noah88"], t)[1])}｜ryan_m {at(pid["ryan_m"], t)[0]}/{k(at(pid["ryan_m"], t)[1])}')
    for w in (3, 4, 5):
        tk = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if ww == w and v == 11:
                tk[x] += n
        print(f'   {600*w}–{600*w+599}: ProfChaos 被拿走 ' + '、'.join(f'{nm(x)} {n}' for x, n in sorted(tk.items(), key=lambda z: -z[1])))
    out = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] in sq and e['q'] == 11 and e['t'] >= 2100]
    print('   2100 拍以后我方号打 ProfChaos：' + '；'.join(f't={e["t"]} {nm(e["p"])} {k(e["troops"])}（它 {e["tL"]} 格/{k(e["tB"])}）' for e in out))
    inc = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] == 11 and e['q'] in sq and e['t'] >= 2000]
    print('   ProfChaos 打我方号：' + '；'.join(f't={e["t"]} → {nm(e["q"])} {k(e["troops"])}' for e in inc))

if on(21):
    print('§21 leo_tx 4380–4530 拍：每 10 拍 地/兵（S10）与它的船')
    p = pid['leo_tx']
    s = S10[str(p)]
    print('   ' + '；'.join(f'{s["t"][i]}: {s["terr"][i]}/{k(s["bal"][i])}' for i in range(len(s['t'])) if 4420 <= s['t'][i] <= 4520))
    for e in ev:
        if e.get('p') == p and e['type'] in ('boat', 'boat-land'):
            print(f'   {e["type"]} t={e["t"]} 兵 {e.get("troops")} 手续费 {e.get("fee")} pct {e.get("pct")} 航程 {e.get("routeLen")} 目标 {nm(e["q"]) if e["q"] != 512 else "中立"}（当时 {e.get("L0")} 格/{e.get("B0")}）')
    print(f'   终局（S10 最后一点）：{s["terr"][-1]} 格/{s["bal"][-1]} 兵｜峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}｜阵亡拍 {P[p]["deathT"]}')

if on(22):
    print('§22 9 条同拍批落地前后的存兵（S10，批前一个采样点 → 批后 30 拍）：打真人的批')
    for b, T in (('riku_x', 1799), ('riku_x', 1911), ('kaito9', 1932), ('zero_7', 1946), ('alex_k', 1988), ('sora_w', 2002), ('zero_7', 2023)):
        p = pid[b]
        es = [e for e in ev if e['type'] == 'attack' and e['p'] == p and e['t'] == T]
        print(f'   {b} t={T}: {len(es)} 条 → {nm(es[0]["q"])}，逐条兵数 ' + '/'.join(k(e.get('troops', 0)) for e in es) + f'｜批前 {es[0]["L0"]} 格/{k(es[0]["B0"])} → +30 拍 {at(p, T + 30)[0]} 格/{at(p, T + 30)[1]} 兵｜目标当时 {es[0]["tL"]} 格/{k(es[0]["tB"])}')
    p = pid['zero_7']
    hits = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['q'] == p and e['p'] < H]
    print('   zero_7 被打：' + '；'.join(f't={e["t"]} {nm(e["p"])} {k(e["troops"])}（pct {e["pct"]}；它当时 {e["tL"]} 格/{e["tB"]} 兵）' for e in hits))
    print('   zero_7 每 30 拍 地/兵：' + '；'.join(f'{t}: {at(p, t)[0]}/{at(p, t)[1]}' for t in range(2040, 2400, 30)))

if on(23):
    print('§23 指令对账（逐号）：影子想发 / 同拍第 2 条起被「每拍 1 条」挤掉 / 客户端自报 sent−accepted（results.csv）/ 过了本地闸的局内指令 / 录像里实际出现的局内指令（replay_cmds.mjs → A034-cmds.tsv）/ 差额')
    import csv as _csv
    S_ = load_shadow()
    want = Counter(); squeezed = Counter()
    for r in S_['ticks']:
        want[r['bot']] += len(r['cmds'])          # 影子输出的是过了「每拍 1 条」闸之后的指令
    try:                                           # 被挤掉的条数取自 shadow.mjs --match 的汇总行「按号：」
        for ln in open(f'/tmp/c136-r05/work/{M}-match.txt', encoding='utf-8'):
            if ln.strip().startswith('按号：'):
                f = ln.strip()[3:].split()
                for i in range(0, len(f) - 1, 2):
                    squeezed[f[i]] = int(f[i + 1])
    except FileNotFoundError:
        print('   （缺 A034-match.txt：先跑 shadow.mjs A034 --quiet --match）')
    res = {r['bot']: r for r in _csv.DictReader(open(f'/agent/repos/c136-data/bundles/{M}/results.csv'))}
    inrep = Counter(); spawn_rep = Counter()
    try:
        for ln in open(f'/tmp/c136-r05/work/{M}-cmds.tsv'):
            f = ln.rstrip('\n').split('\t')
            if f[0] == 'tick':
                continue
            b = [x for x in ORDER if x in f[4]]
            if not b:
                continue
            if int(f[0]) < 0:
                spawn_rep[b[0]] += 1
            elif f[2] in ('attack', 'donate', 'boat'):
                inrep[b[0]] += 1
    except FileNotFoundError:
        print('   （缺 A034-cmds.tsv：先跑 replay_cmds.mjs A034 --out /tmp/c136-r05/work/A034-cmds.tsv）')
    tw = ts = td = ta = ti = tm = 0
    for b in ORDER:
        d = int(res[b]['sent']) - int(res[b]['accepted'])
        passed = want[b]
        miss = passed - inrep[b]
        tw += want[b]; ts += squeezed[b]; td += d; ta += passed; ti += inrep[b]; tm += miss
        print(f'   {b}: 策略想发 {want[b] + squeezed[b]}｜同拍被挤 {squeezed[b]}｜自报 sent {res[b]["sent"]} − accepted {res[b]["accepted"]} = {d}｜过闸 {passed}｜录像里 {inrep[b]}（选点期另有 {spawn_rep[b]} 条）｜没出现在录像里 {miss}（{100*miss/max(1,passed):.0f}%）')
    print(f'   合计：策略想发 {tw + ts}｜同拍被挤 {ts}｜自报 sent−accepted {td}｜过闸 {ta}｜录像里 {ti}｜没出现在录像里 {tm}（{100*tm/max(1,ta):.0f}%）')
    print('   按 300 拍：过闸的局内指令（影子，每拍只算第 1 条）/ 录像里执行拍落在该窗口的指令')
    passed_w = Counter(); rep_w = Counter()
    for r in S_['ticks']:
        if r['cmds']:
            passed_w[r['t'] // 300 * 300] += 1
    for e in ev:
        if e['type'] in ('attack', 'boat', 'donate') and e.get('p') in sq:
            rep_w[e['t'] // 300 * 300] += 1
    print('   ' + '；'.join(f'{w}: {passed_w[w]}/{rep_w[w]}' for w in sorted(set(passed_w) | set(rep_w))))

if on(24):
    print('§24 选点期：协调器锚点 (766,180) 周围的其他真人——第一条/最后一条出生指令的拍号与位置、到锚点的距离、到最近我方号的距离（A034-cmds.tsv）；r2+45 = 217 以内的算「角里的敌人」（SPAWN L1258-1261）')
    AX, AY, W_ = 766, 180, 931
    sp = defaultdict(list)
    for ln in open(f'/tmp/c136-r05/work/{M}-cmds.tsv'):
        f = ln.rstrip('\n').split('\t')
        if f[0] == 'tick' or f[2] != 'spawn':
            continue
        sp[int(f[3])].append((int(f[0]), int(f[5]) % W_, int(f[5]) // W_))
    ours = {p: sp[p][-1][1:] for p in sq if sp.get(p)}
    first_ours = min(sp[p][0][0] for p in sq if sp.get(p))
    print(f'   我方号第一条出生指令在 t={first_ours}；最后一条在 t={max(sp[p][-1][0] for p in sq if sp.get(p))}')
    rows = []
    for p, lst in sp.items():
        if p in sq:
            continue
        t0, x0, y0 = lst[0]
        t1, x1, y1 = lst[-1]
        dA = math.hypot(x1 - AX, y1 - AY)
        dN, who = min((math.hypot(x1 - ox, y1 - oy), sq[p2]) for p2, (ox, oy) in ours.items())
        rows.append((dA, p, t0, (x0, y0), t1, (x1, y1), dN, who))
    inside = [r for r in rows if r[0] <= 217]
    for dA, p, t0, a, t1, b, dN, who in sorted(rows)[:9]:
        print(f'   {nm(p)}: 第一条 t={t0} {a}，最后一条 t={t1} {b}｜到锚点 {dA:.0f}｜到最近我方号 {dN:.0f}（{who}）' + ('｜在我方第一条出生指令之前已落点' if t0 < first_ours else ''))
    print(f'   锚点 217 以内的其他真人 {len(inside)} 个，其中敌方 {sum(1 for r in inside if P[r[1]]["team"] != J["ourTeam"])} 个；在我方第一条出生指令之前就已经落点的 {sum(1 for r in inside if r[2] < first_ours)} 个')

if on(25):
    print('§25 除名时手里还有多少兵：阵亡拍之前最后一个 S10 采样点（≤10 拍前）的 地/兵，与历史峰值地的比；除名规则 game.js aliveTick L1298-1312（地 ≤ 峰值的 1/4，峰值随时间回落）')
    tot = 0
    for b in ORDER:
        p = pid[b]
        d = P[p]['deathT']
        s = S10[str(p)]
        if d is None or d < 0:
            zi = next((i for i in range(len(s['t'])) if s['t'][i] > 600 and s['terr'][i] == 0), None)
            if zi is None:
                print(f'   {b}: 未阵亡')
                continue
            i = zi - 1
            print(f'   {b}: 未判阵亡（海上有船，collapse L1314-1330）；t={s["t"][i]} {s["terr"][i]} 格/{k(s["bal"][i])} → t={s["t"][zi]} 0 格/0 兵｜峰值 {P[p]["peakTerr"]}（地÷峰值 {s["terr"][i]/P[p]["peakTerr"]:.2f}）')
            tot += s['bal'][i]
            continue
        i = max(j for j in range(len(s['t'])) if s['t'][j] < d)
        tot += s['bal'][i]
        print(f'   {b}: 阵亡 {d}；t={s["t"][i]} {s["terr"][i]} 格/{k(s["bal"][i])}（密 {s["bal"][i]/max(1,s["terr"][i]):.0f}）｜峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}（地÷峰值 {s["terr"][i]/P[p]["peakTerr"]:.2f}）')
    print(f'   九个号除名前最后一个采样点的存兵合计 {k(tot)}')

if on(26):
    print('§26 崩盘段的合计：已执行陆攻（不含手续费）按窗口、按对手')
    def win(t0, t1, out):
        by = defaultdict(lambda: [0, 0])
        for e in ev:
            if e['type'] != 'attack' or not e.get('ok') or not (t0 <= e['t'] <= t1):
                continue
            if out and e['p'] in sq and e['q'] < H and e['q'] not in sq:
                by[(sq[e['p']], nm(e['q']))][0] += 1; by[(sq[e['p']], nm(e['q']))][1] += e['troops']
            if not out and e['q'] in sq and e['p'] < H and e['p'] not in sq:
                by[(nm(e['p']), sq[e['q']])][0] += 1; by[(nm(e['p']), sq[e['q']])][1] += e['troops']
        return by
    for t0, t1 in ((3514, 3619), (3620, 4217)):
        o = win(t0, t1, True)
        print(f'   {t0}–{t1} 我方打真人：{sum(v[0] for v in o.values())} 条 {k2(sum(v[1] for v in o.values()))}｜' + '；'.join(f'{a}→{b} {n} 条 {k2(x)}' for (a, b), (n, x) in sorted(o.items(), key=lambda z: -z[1][1])))
        i = win(t0, t1, False)
        print(f'   {t0}–{t1} 真人打我方：{sum(v[0] for v in i.values())} 条 {k2(sum(v[1] for v in i.values()))}｜' + '；'.join(f'{a}→{b} {n} 条 {k2(x)}' for (a, b), (n, x) in sorted(i.items(), key=lambda z: -z[1][1])))
    dn = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] in sq]
    for t0, t1 in ((3381, 3600), (3601, 3900), (3901, 4217), (4218, 4500), (4501, 5200)):
        d = [e for e in dn if t0 <= e['t'] <= t1]
        print(f'   {t0}–{t1} 捐兵 {len(d)} 笔 到账 {k2(sum(e["got"] for e in d))} 税 {k2(sum(e["fee"] for e in d))}')
    print('   3600 拍各敌邻的存兵（HS）：' + '；'.join(f'{nm(q)} {hs(q, 3600)[0]} 格/{k2(hs(q, 3600)[1])}' for q in (7, 1, 12, 13, 9, 2, 20)) + f'｜合计 {k2(sum(hs(q, 3600)[1] for q in (7, 1, 12, 13, 9, 2, 20)))}')
    print('   3600 拍我方号的存兵（S10）：' + '；'.join(f'{b} {at(pid[b], 3600)[0]} 格/{k2(at(pid[b], 3600)[1])}' for b in ORDER if not (0 <= (P[pid[b]]['deathT'] if P[pid[b]]['deathT'] is not None else -1) <= 3600)))

if on(27):
    print('§27 做对的几手：对密度不到自己一半的真人邻居出兵（已执行陆攻；每格净花费 =（出兵 − 退回）÷ 拿到的格；地的变化取 S10）')
    PAIRS = {(x['a'], x['b']): x for x in J['pairs']}
    S_ = load_shadow()
    for b, q, t0, t1 in (('talon5', 1, 2040, 2100), ('noah88', 11, 1850, 1930), ('riku_x', 10, 1790, 1810), ('zero_7', 2, 1940, 1950)):
        p = pid[b]
        es = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] == p and e['q'] == q and t0 <= e['t'] <= t1]
        if not es:
            continue
        e0 = es[0]
        sent = sum(e['troops'] for e in es)
        dme = e0['B0'] / max(1, e0['L0']); dq = e0['tB'] / max(1, e0['tL'])
        pr = PAIRS.get((p, q), {})
        tiles_w = sum(n for w, x, v, n in J['pairAll'] if x == p and v == q and t0 // 600 <= w <= (t1 + 300) // 600)
        la = at(p, e0['t'] - 10)[0]; lb = at(p, e0['t'] + 300)[0]
        decs = [(r['t'], c['pct'], [x for x in r['sig'].split(' > ') if x.startswith('buyLand:')][-1:]) for r in S_['ticks'] if r['bot'] == b and t0 - 320 <= r['t'] <= t1 for c in r['cmds'] if c['k'] == 'attack' and c['q'] == q]
        print(f'   {b} → {nm(q)} {es[0]["t"]}–{es[-1]["t"]}：{len(es)} 条 {k2(sent)}（pct {min(e["pct"] for e in es)}–{max(e["pct"] for e in es)}）｜开打时 我 {e0["L0"]} 格/{k2(e0["B0"])}（密 {dme:.1f}）对方 {e0["tL"]} 格/{k2(e0["tB"])}（密 {dq:.1f}，是我的 {dq/dme:.2f}）'
              f'｜全程对它 {pr.get("n")} 条 {k2(pr.get("sent", 0))} 退回 {k2(pr.get("ret", 0))} 拿 {pr.get("tiles")} 格 → 每格净 {(pr.get("sent", 0) - pr.get("ret", 0)) / max(1, pr.get("tiles", 1)):.1f} 兵'
              f'｜我的地 {la}（开打前 10 拍）→ {lb}（+300 拍，{(lb - la) / max(1, la) * 100:+.0f}%）'
              f'｜对方对我的第一条 ≥30k 陆攻：{next((e["t"] for e in ev if e["type"] == "attack" and e.get("ok") and e["p"] == q and e["q"] == p and e.get("troops", 0) >= 30000 and e["t"] >= e0["t"]), "无")}')
        if decs:
            print(f'      影子里对它的决策 {len(decs)} 条：首条 t={decs[0][0]}（pct {decs[0][1]}，{decs[0][2]}），末条 t={decs[-1][0]}（pct {decs[-1][1]}，{decs[-1][2]}）')

if on(28):
    print('§28 放行（批前存兵 > 100×地）的轮：目标存兵÷自己存兵、对方其后 300 拍对我方号的陆攻；以及每笔捐兵之后 300 拍受赠方的地')
    atk = sorted([e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] in sq and e['q'] < H and e['q'] not in sq], key=lambda e: (e['p'], e['q'], e['t']))
    vol = []
    for e in atk:
        if vol and vol[-1]['p'] == e['p'] and vol[-1]['q'] == e['q'] and e['t'] - vol[-1]['t1'] <= 21:
            vol[-1]['t1'] = e['t']; vol[-1]['n'] += 1; vol[-1]['sent'] += e['troops']
        else:
            vol.append({'p': e['p'], 'q': e['q'], 't0': e['t'], 't1': e['t'], 'n': 1, 'sent': e['troops'], 'B0': e['B0'], 'L0': e['L0'], 'tB': e['tB'], 'tL': e['tL']})
    over = [v for v in vol if v['B0'] > 100 * v['L0']]
    big = [v for v in over if v['tB'] >= 2 * v['B0']]
    eq = [v for v in over if v['tB'] >= v['B0']]
    print(f'   打真人 {len(vol)} 轮，其中放行的 {len(over)} 轮（出兵 {k2(sum(v["sent"] for v in over))}，不含手续费）；目标存兵 ≥ 自己的 {len(eq)} 轮（{k2(sum(v["sent"] for v in eq))}），≥ 2×自己的 {len(big)} 轮（{k2(sum(v["sent"] for v in big))}）')
    for v in sorted(over, key=lambda v: v['t0']):
        back = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] == v['q'] and e['q'] in sq and v['t0'] < e['t'] <= v['t0'] + 300]
        me_back = [e for e in back if e['q'] == v['p']]
        print(f'      {v["t0"]}–{v["t1"]} {sq[v["p"]]} → {nm(v["q"])} {v["n"]} 条 {k2(v["sent"])}｜我 {v["L0"]} 格/{k2(v["B0"])}（密 {v["B0"]/max(1,v["L0"]):.0f}）对方 {v["tL"]} 格/{k2(v["tB"])}（密 {v["tB"]/max(1,v["tL"]):.0f}；存兵是我的 {v["tB"]/max(1,v["B0"]):.2f} 倍）'
              f'｜其后 300 拍它打我方号 {len(back)} 条 {k2(sum(e["troops"] for e in back))}（其中打这个号 {len(me_back)} 条 {k2(sum(e["troops"] for e in me_back))}）')
    # 每个目标：放行轮数、合计
    byq = defaultdict(lambda: [0, 0, set()])
    for v in over:
        byq[v['q']][0] += 1; byq[v['q']][1] += v['sent']; byq[v['q']][2].add(sq[v['p']])
    print('   按目标：' + '；'.join(f'{nm(q)} {n} 轮 {k2(x)}（{"、".join(sorted(b))}）' for q, (n, x, b) in sorted(byq.items(), key=lambda z: -z[1][1])))
    dn = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] in sq and e['q'] in sq]
    sink = []
    for e in dn:
        la = at(e['q'], e['t'])[0]; lb = at(e['q'], e['t'] + 300)[0]
        if lb <= 0.8 * la:
            sink.append(e)
    print(f'   捐兵 {len(dn)} 笔里，受赠方其后 300 拍的地少了 ≥20% 的 {len(sink)} 笔：到账 {k2(sum(e["got"] for e in sink))}、税 {k2(sum(e["fee"] for e in sink))}；其余 {len(dn) - len(sink)} 笔到账 {k2(sum(e["got"] for e in dn if e not in sink))}')
