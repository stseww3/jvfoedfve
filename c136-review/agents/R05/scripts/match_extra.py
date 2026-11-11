# match_extra.py — 逐局复盘里通用脚本（truth_digest.py / match_facts.py）不直接给、但每局都要用的几组数。
# 全部从 /tmp/c136-r05/truth/<局>.json（match_truth.mjs 的产物）机械算出。
#
# 用法：python3 scripts/match_extra.py <局> [--sec disp,team,mates,grab,active,rate,form,quota] [--ticks 1500,3000,...]
#   disp   调度日志按时段：日志条数 / 录像里对上执行 / 类别
#   team   各队 地/兵，编队占本队兵和地的比例
#   mates  我方队的路人队友：峰值、离场、阵亡；存活/在线人数
#   grab   每 600 拍从 中立/机器人/真人 手里拿到的地：编队 对 路人队友 对 其余在场真人
#   active 各队在场真人数与最大的三个号
#   rate   利率表：各号的表利率、编队若是一个号的表利率、按存兵加权的实际表利率
#   form   选点阵形半径（按该局所用版本的算式）与编队出生点间距
#   quota  没落地的调度按四个试算拍的结果分类
#   qeff   配额效率：已执行捐兵按引擎公式复算花掉的配额点数，3213 前后每点换来多少兵
import json, sys, math, statistics as st
from collections import Counter, defaultdict

a = sys.argv[1:]
M = a[0]


def opt(name, dflt):
    return a[a.index(name) + 1] if name in a else dflt


SEC = opt('--sec', 'disp,team,mates,grab,active,rate,form,quota,qeff').split(',')
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
H = J['humans']
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
D = J['dispatch']
HS = J['HS']
OUR = J['ourTeam']
END = J['endTick']
TEAMS = sorted({P[p]['team'] for p in range(H) if p in P and P[p]['team'] > 0})
TICKS = [int(x) for x in opt('--ticks', '').split(',') if x] or [t for t in (1500, 3000, 4200, 4800, 5400, 6000, 6600, 7200, 7800, 8400, 9000) if t <= END]
TICKS = [t for t in TICKS if t in HS['t']]


def land_of_map():
    import re
    try:
        txt = open(f'/tmp/c136-r05/work/{M}-digest.txt').read()
        m = re.search(r'陆地 (\d+)', txt)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    sk = json.load(open(f'/tmp/c136-r05/skel/{M}.json'))
    return sk['context'].get('mapLand') or sk['context'].get('land')


LANDT = land_of_map()


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return '中立' if p == 512 else f'机器人#{p}'


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'


def hs(t):
    i = HS['t'].index(t)
    return HS['terr'][i], HS['bal'][i]


def active(p, t):
    return p in P and (P[p]['deathT'] < 0 or P[p]['deathT'] > t) and (P[p]['leftT'] < 0 or P[p]['leftT'] > t)


def ver():
    v = opt('--ver', '')
    if v:
        return v
    if M[0] != 'A':
        return 'c110'
    n = int(M[1:])
    return 'va' if n <= 17 else 'vb' if n <= 95 else 'vc'


if 'disp' in SEC:
    print('== disp 调度日志按时段（日志条数 / 录像里对上执行 / 类别）==')
    cuts = [0, 1500, 3000, 3213, 4284, 5400, 6600, 7800, 99999]
    for lo, hi in list(zip(cuts, cuts[1:])) + [(0, 4284), (4284, 99999)]:
        r = [d for d in D if lo <= d['t'] < hi]
        if not r:
            continue
        ex = [d for d in r if d.get('exec')]
        print(f'  {lo}–{hi}: 日志 {len(r)} 执行 {len(ex)}（到账 {k(sum(d["exec"]["got"] for d in ex))} 税 {k(sum(d["exec"]["fee"] for d in ex))}）｜日志类别 {dict(Counter(d["kind"] for d in r))}｜执行类别 {dict(Counter(d["kind"] for d in ex))}｜boxedIn {dict(Counter(d["boxed"] for d in r))}')
    for lab, key in (('受赠方', lambda d: d['qName'].replace('[APEX] ', '')), ('捐出方', lambda d: d['bot'])):
        for lo, hi in ((0, 4284), (4284, 99999)):
            c = defaultdict(lambda: [0, 0, 0])
            for d in D:
                if lo <= d['t'] < hi:
                    x = c[key(d)]; x[0] += 1
                    if d.get('exec'):
                        x[1] += 1; x[2] += d['exec']['got']
            print(f'  {lo}–{hi} 按{lab} 日志/执行/到账：' + '；'.join(f'{b} {v[0]}/{v[1]}/{k(v[2])}' for b, v in sorted(c.items(), key=lambda x: -x[1][0])))
    ex = [d for d in D if d.get('exec')]
    print('  已执行的：决策时 捐出方密度 dMe / 受赠方密度 dAlly 的中位，按类别：' + '；'.join(f'{kd} {len(r)} 笔 dMe {st.median(d["dMe"] for d in r):.0f} dAlly {st.median(d["dAlly"] for d in r):.0f}（dAlly ≥ dMe 的 {sum(1 for d in r if d["dAlly"] >= d["dMe"])} 笔）' for kd in sorted({d['kind'] for d in ex}) for r in [[d for d in ex if d['kind'] == kd]]))

if 'team' in SEC:
    print('== team 各队 地/兵 与编队占本队的比例（HS 每 300 拍一采）==')
    for t in TICKS:
        terr, bal = hs(t)
        tb = defaultdict(int); tl = defaultdict(int)
        for p in range(H):
            if p in P:
                tb[P[p]['team']] += bal[p]; tl[P[p]['team']] += terr[p]
        sb = sum(bal[p] for p in sq); sl = sum(terr[p] for p in sq)
        print(f'  t={t}: ' + ' '.join(f'T{x}{"*" if x == OUR else ""} {tl[x]}格({100*tl[x]/LANDT:.1f}%)/{k(tb[x])}' for x in TEAMS) + f'｜编队 {sl}格/{k(sb)} = 本队兵的 {100*sb/max(1,tb[OUR]):.0f}%、本队地的 {100*sl/max(1,tl[OUR]):.0f}%｜编队兵 ÷ 敌方最大一队的兵 {sb/max(1, max(tb[x] for x in TEAMS if x != OUR)):.2f}')

if 'mates' in SEC:
    print(f'== mates 我方队（T{OUR}）路人队友：按峰值地排序 ==')
    mates = sorted([p for p in J['players'] if p['team'] == OUR and not p['squad'] and p['id'] < H], key=lambda p: -p['peakTerr'])
    for p in mates[:8]:
        print(f"  {nm(p['id'])} 峰值 {p['peakTerr']}({100*p['peakTerr']/LANDT:.1f}%)@{p['peakT']} 离场 {p['leftT']} 阵亡 {p['deathT']}")
    alive = lambda t: sum(1 for p in mates if p['deathT'] < 0 or p['deathT'] > t)
    online = lambda t: sum(1 for p in mates if active(p['id'], t))
    print(f'  路人队友共 {len(mates)} 人；存活/在线：' + ' '.join(f'{t}:{alive(t)}/{online(t)}' for t in TICKS))

if 'grab' in SEC:
    print('== grab 每 600 拍从 中立/机器人/真人 手里拿到的地（pairAll：512=中立，600=机器人）==')
    wmax = max(x[0] for x in J['pairAll']) if J['pairAll'] else 0
    for w in range(0, wmax + 1):
        frm = defaultdict(lambda: defaultdict(int))
        for ww, x, b, n in J['pairAll']:
            if ww != w or x >= H:
                continue
            frm['机器人' if b == 600 else '中立' if b == 512 else '真人'][x] += n
        hi = w * 600 + 599
        mates = [p for p in range(H) if p in P and P[p]['team'] == OUR and p not in sq]
        foes = [p for p in range(H) if p in P and P[p]['team'] != OUR]
        act_all = [p for p in range(H) if p not in sq and active(p, hi)]
        row = []
        for cls in ('中立', '机器人', '真人'):
            d = frm[cls]
            tot = sum(d.values())
            if tot < 0.002 * LANDT:
                continue
            s = [d.get(p, 0) for p in sq]
            o = [d.get(p, 0) for p in act_all]
            row.append(f'从{cls} 全场 {tot}（{100*tot/LANDT:.1f}%）：编队 {sum(s)}＝{100*sum(s)/max(1,tot):.1f}%（每号中位 {st.median(s):.0f}）｜路人队友 {sum(d.get(p, 0) for p in mates)}｜敌方真人 {sum(d.get(p, 0) for p in foes)}｜其余在场真人每人中位 {st.median(o) if o else 0:.0f}、上四分位 {sorted(o)[3*len(o)//4] if o else 0}')
        n_act = len(act_all) + sum(1 for p in sq if active(p, hi))
        n_sq = sum(1 for p in sq if active(p, hi))
        print(f'  {w*600}–{hi}（窗末在场真人 {n_act}，其中编队 {n_sq}＝{100*n_sq/max(1,n_act):.1f}%）')
        for r in row:
            print('     ' + r)
        if w <= 2 or 'grab-bots' in a:
            for cls in ('中立', '机器人', '真人'):
                d = frm[cls]
                if sum(d.get(p, 0) for p in sq):
                    print(f'       各号从{cls}：' + ' '.join(f'{b}:{d.get(p, 0)}' for p, b in sq.items()))

if 'active' in SEC:
    print('== active 各队在场真人数（未阵亡且未离场）与各队最大的三个号 ==')
    for t in TICKS:
        terr, bal = hs(t)
        row = []
        for tm in TEAMS:
            act = [p for p in range(H) if p in P and P[p]['team'] == tm and active(p, t)]
            top = sorted(act, key=lambda p: -terr[p])[:3]
            row.append(f'T{tm}{"*" if tm == OUR else ""} 在场 {len(act)}（' + '；'.join(f'{nm(p)} {terr[p]}格/{k(bal[p])}' for p in top) + '）')
        print(f'  t={t}: ' + ' ｜ '.join(row))

if 'rate' in SEC:
    print('== rate 利率表（game.js L40-41、L739-746）：每 10 拍利率（万分之）= 100 + isqrt(25600*i/508)，i = 511×地/全图陆地 ==')
    iV = lambda x, y: int((x + 0.5) // y)

    def isq(h):
        if h < 1:
            return 0
        x = iV(h + 1, 2)
        for _ in range(9):
            x = iV(x + iV(h, x), 2)
        return x
    rate = lambda terr: 100 + isq(iV(25600 * iV(511 * terr, LANDT), 508))
    for t in TICKS:
        terr, bal = hs(t)
        tops = sorted([p for p in range(H) if p in P and p not in sq and active(p, t)], key=lambda p: -terr[p])[:3]
        tot = sum(terr[p] for p in sq); tb = sum(bal[p] for p in sq)
        print(f'  t={t}: ' + ' '.join(f'{b}:{terr[p]}格→{rate(terr[p])}' for p, b in sq.items() if terr[p] > 0) + '｜' + '；'.join(f'{nm(p)} {terr[p]}格→{rate(terr[p])}' for p in tops))
        print(f'     编队 {tot} 格如果是一个号 → {rate(tot)}；按各号存兵加权的实际表利率 {sum(rate(terr[p]) * bal[p] for p in sq) / max(1, tb):.0f}')

if 'form' in SEC:
    V = ver()
    print(f'== form 选点阵形半径（版本 {V}；算式照抄 spawn-coordinator L838、L1074-1077）与编队出生点 ==')
    clamp = lambda v, lo, hi: max(lo, min(hi, v))
    K = {'va': (1.38, 78, 132, 2.35, 142, 225), 'vb': (1.12, 66, 108, 1.88, 122, 182), 'vc': (1.32, 76, 126, 2.28, 145, 220)}.get(V)
    rCell = math.sqrt(max(10000, LANDT) / (math.pi * H))
    print(f'  rCell = sqrt(陆地 {LANDT} / (π × 真人 {H})) = {rCell:.1f} 格（人均 {LANDT/H:.0f} 格地；相邻两人平均间距约 {2*rCell:.0f} 格）')
    if K:
        minReqSep = clamp(round(0.95 * rCell), 42, 68)
        r0 = clamp(round(0.48 * rCell), 28, 46)
        lo1 = max(K[1], r0 + minReqSep); r1 = clamp(round(K[0] * rCell), lo1, K[2])
        lo2 = max(K[4], r1 + minReqSep); r2 = clamp(round(K[3] * rCell), lo2, K[5])
        print(f'  minReqSep={minReqSep} r0={r0} r1={r1}（系数给 {round(K[0]*rCell)}，下限 {lo1}）r2={r2}（系数给 {round(K[3]*rCell)}，下限 {lo2}）；allyMinSep = clamp(round(1.48×rCell),72,118) = {clamp(round(1.48*rCell), 72, 118)}')
    sp = {p: P[p]['spawn'] for p in sq if P[p].get('spawn')}
    if len(sp) >= 2:
        nn = []
        for p, (x, y) in sp.items():
            nn.append(min(math.hypot(x - x2, y - y2) for q, (x2, y2) in sp.items() if q != p))
        cx = sum(v[0] for v in sp.values()) / len(sp); cy = sum(v[1] for v in sp.values()) / len(sp)
        far = max(math.hypot(x - cx, y - cy) for x, y in sp.values())
        others = {p: P[p]['spawn'] for p in range(H) if p in P and p not in sq and P[p].get('spawn')}
        inside = [p for p, (x, y) in others.items() if math.hypot(x - cx, y - cy) <= far]
        print(f'  编队 {len(sp)} 个出生点：最近队友距离 最小 {min(nn):.0f} 中位 {st.median(nn):.0f} 最大 {max(nn):.0f}；质心 ({cx:.0f},{cy:.0f})，最远号离质心 {far:.0f}；质心这个半径内的其他真人 {len(inside)} 人：' + '，'.join(f'{nm(p)} 离质心 {math.hypot(others[p][0]-cx, others[p][1]-cy):.0f}' for p in inside[:8]))
        allsp = {**sp, **others}
        nn_all = []
        for p, (x, y) in others.items():
            nn_all.append(min(math.hypot(x - x2, y - y2) for q, (x2, y2) in allsp.items() if q != p))
        if nn_all:
            print(f'  对照：其他真人 {len(nn_all)} 人的最近邻距离 中位 {st.median(nn_all):.0f}、下四分位 {sorted(nn_all)[len(nn_all)//4]:.0f}')

if 'quota' in SEC:
    print('== quota 没落地的调度：按日志拍 +0/7/14/21 四个试算拍的结果分类（quota = 受赠方配额不够）==')
    for lo, hi in [(0, 3213), (3213, 4284), (4284, 99999)]:
        r = [d for d in D if lo <= d['t'] < hi and not d.get('exec')]
        n = sum(1 for d in D if lo <= d['t'] < hi)
        c = Counter()
        for d in r:
            rs = [x.get('reason') for x in d['sim']]
            c['四拍全被配额拒' if all(x == 'quota' for x in rs) else '四拍全通过' if all(x == 'ok' for x in rs) else '有过有拒/其它'] += 1
        print(f'  日志拍 {lo}–{hi}: 日志 {n} 条，没落地 {len(r)} 条：{dict(c)}')
    ex = [d for d in D if d['t'] < 4284 and not d.get('exec') and d['sim'] and d['sim'][0].get('reason') == 'quota' and d['sim'][0].get('extra')]
    if ex:
        over = [d for d in ex if d['sim'][0]['extra']['cost'] > d['sim'][0]['extra']['cap']]
        print(f'  t<4284 被配额拒的 {len(ex)} 条里，单笔所需配额 > 受赠方配额总上限的 {len(over)} 条；所需/上限 中位 {sorted(d["sim"][0]["extra"]["cost"] / max(1, d["sim"][0]["extra"]["cap"]) for d in ex)[len(ex)//2]:.2f}')
        print('  例：' + '；'.join(f"t={d['t']} {d['bot']}→{d['qName'].replace('[APEX] ', '')} 想捐 {k(d['sim'][0]['extra']['want'])}：需 {d['sim'][0]['extra']['cost']} 点，对方已用 {d['sim'][0]['extra']['used']}/上限 {d['sim'][0]['extra']['cap']}" for d in (ex[0], ex[len(ex)//2], ex[-1])))

if 'qeff' in SEC:
    # 配额效率：引擎 donationCost（game.js L348-357）与 donationCapTick（L379-383）照抄。
    # t<3213：每点配额换 uw = 1 + 全图陆地/300 个兵（2142 拍起；更早更贵），另每笔固定 2 点；
    # t≥3213：每点换 受赠方的地（softCap/100）个兵，另每笔固定 4 点；t≥4284 不限。
    print('== qeff 配额效率（已执行的捐兵按引擎公式复算花掉的配额点数；受赠方 = 我方号）==')
    import bisect
    uw = 1 + int((LANDT + 0.5) // 300)

    def cost(t, v, terr_q):
        iV = lambda x, y: int((x + 0.5) // y)
        if t >= 3213:
            return 4 + iV(100 * v, max(100 * terr_q, 1))
        if t < 357:
            return 2 + iV(100 * v, uw)
        if t < 714:
            return 2 + iV(100 * v, 4 * uw)
        if t < 1071:
            return 2 + iV(100 * v, 10 * uw)
        if t < 2142:
            return 2 + iV(100 * v, 30 * uw)
        return 2 + iV(100 * v, 100 * uw)

    def cap(t):
        c = 15
        for tt in range(99, t + 1, 100):
            c += 4 if tt < 1071 else 6 if tt < 2142 else 8 if tt < 3213 else 10
        return c

    def terr_at(p, t):
        s = J['S10'].get(str(p))
        if s:
            i = bisect.bisect_right(s['t'], t) - 1
            return s['terr'][max(i, 0)]
        i = bisect.bisect_right(HS['t'], t) - 1
        return HS['terr'][max(i, 0)][p]

    print(f'  全图陆地 {LANDT} → uw = {uw}：2142–3212 拍每点配额换 {uw} 兵（1071–2141 拍 {uw*30//100} 兵）；3213 拍起每点换「受赠方的地」个兵；配额上限 cap：t=2142 {cap(2141)}、t=3213 {cap(3212)}、t=4284 {cap(4283)}（每 100 拍 +4/+6/+8/+10）')
    used = defaultdict(lambda: [0, 0, 0, 0, 0, 0])   # 受赠方：3213 前 点数/兵/笔，3213–4284 点数/兵/笔
    for t, p, q, got, fee in J['allDon']:
        if q not in sq or t >= 4284:
            continue
        c = cost(t, got, terr_at(q, t))
        u = used[q]
        if t < 3213:
            u[0] += c; u[1] += got; u[2] += 1
        else:
            u[3] += c; u[4] += got; u[5] += 1
    tot = [sum(u[i] for u in used.values()) for i in range(6)]
    for q, u in sorted(used.items(), key=lambda x: -(x[1][1] + x[1][4])):
        L1, L2 = terr_at(q, 3213), terr_at(q, 4283)
        print(f'  {sq[q]}: 3213 前 {u[2]} 笔 到账 {k(u[1])} 花 {u[0]} 点（{u[1]//max(1,u[0])} 兵/点）→ t=3213 剩 {cap(3212)-u[0]} 点（按当时 {L1} 格地，可再收约 {k((cap(3212)-u[0])*L1)}）｜3213–4284 {u[5]} 笔 到账 {k(u[4])} 花 {u[3]} 点（{u[4]//max(1,u[3])} 兵/点）→ t=4284 剩 {cap(4283)-u[0]-u[3]} 点')
    print(f'  合计：3213 前 {tot[2]} 笔 到账 {k(tot[1])} 花 {tot[0]} 点（{tot[1]//max(1,tot[0])} 兵/点）；3213–4284 {tot[5]} 笔 到账 {k(tot[4])} 花 {tot[3]} 点（{tot[4]//max(1,tot[3])} 兵/点）')
    # 没落地的调度想要的点数
    rej = [d for d in D if d['t'] < 4284 and not d.get('exec') and d['sim'] and d['sim'][0].get('extra')]
    if rej:
        pre = [d for d in rej if d['t'] < 3213]; post = [d for d in rej if d['t'] >= 3213]
        for lab, r in (('3213 前', pre), ('3213–4284', post)):
            if r:
                print(f'  {lab} 被拒的 {len(r)} 条：想捐量中位 {k(st.median(d["sim"][0]["extra"]["want"] for d in r))}、所需点数中位 {st.median(d["sim"][0]["extra"]["cost"] for d in r):.0f}、对方当时剩余点数中位 {st.median(d["sim"][0]["extra"]["cap"] - d["sim"][0]["extra"]["used"] for d in r):.0f}')
