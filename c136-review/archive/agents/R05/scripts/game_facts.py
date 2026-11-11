#!/usr/bin/env python3
# game_facts.py — 逐局复盘里通用脚本（truth_digest.py / match_facts.py / match_extra.py）不直接给、而每局都要引用的一组数字。
# 是 review_build/A034_facts.py 的通用版（节号沿用），全部从 /tmp/c136-r05/truth/<局>.json（match_truth.mjs 的逐拍重放产物）机械算出；
# §18、§19、§23 另读 /tmp/c136-r05/work/<局>-shadow.json、<局>-match.txt、<局>-cmds.tsv（shadow.mjs --json / --match、replay_cmds.mjs --out）。
#
# 用法：python3 scripts/game_facts.py <局> [--sec 1,2,…] [--ids 35,25] [--tl 3380:4300] [--wins 3200:3600,3600:4350]
#                                        [--from 1500] [--segs 0,900,1500,2100,3600] [--min 60000]
#   --ids   关心的非我方玩家编号（§3 地/兵轨迹、§13 它的地归谁、§26 某拍的存兵）
#   --tl    §17 逐条时间线的拍段；--min 该时间线里陆攻的最小兵数
#   --wins  §26 合计窗口
#   --from  §16、§19 的起始拍
#   --segs  §11 分段收支的分界拍
# 各节：
#   1 各队地/兵/密度与编队对敌队的兵力比   2 接敌面与不接敌的号握兵   3 路人队友与指定玩家的轨迹   4 已执行捐兵
#   5 打真人的同拍批   6 阵亡号   7 机器人让出的地   8 地的名次   11 分段收支   12 交换比   13 谁拿了谁的地
#   14 捐兵之后 300 拍   15 多号打同一人   16 各号每 300 拍   17 时间线与谁先动手   18 影子决策构成   19 影子里打真人的出手段
#   23 指令对账   25 除名时的存兵   26 窗口合计   28 放行轮与捐兵去向
#   29 被围：每 300 拍各号边界构成、被围的号握兵占比   30 本队路人队友 对 编队 对 敌队   31 路人队友逐个的下场
import os
import json, bisect, statistics, sys, math, csv
from collections import defaultdict, Counter

a = sys.argv[1:]
M = a[0]
val = lambda k_, d: (a[a.index(k_) + 1] if k_ in a else d)
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
END = J['endTick']
SEC = set(val('--sec', '').split(',')) - {''} or None
on = lambda n: SEC is None or str(n) in SEC
IDS = [int(x) for x in val('--ids', '').split(',') if x]
TL = tuple(int(x) for x in val('--tl', '0:0').split(':'))
WINS = [tuple(int(x) for x in w.split(':')) for w in val('--wins', '').split(',') if w]
FROM = int(val('--from', 1500))
SEGS = [int(x) for x in val('--segs', '0,900,1500,2100,3000,3600,4200,4800').split(',')]
MIN = int(val('--min', 60000))


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


def dead_t(p):
    d = P[p]['deathT']
    return d if d is not None and d >= 0 else None


def alive_at(p, t):
    d = dead_t(p)
    return not (d is not None and d <= t)


def left_at(p, t):
    lt = P[p].get('leftT', -1)
    return lt is not None and 0 <= lt <= t


def t30(t):
    return bisect.bisect_right(T30['t'], t) - 1


def hs(p, t):
    i = HS['t'].index(t)
    return HS['terr'][i][p], HS['bal'][i][p]


ORDER = [s['bot'] for s in J['squad']]
S10, C30, F30 = J['S10'], J['C30'], J['F30']
NT = len(T30['land'][0]) - 1
OUR = J['ourTeam']
ENEMY = [j for j in range(1, NT + 1) if j != OUR]
TICKS300 = [t for t in range(600, END + 1, 300)]

if on(1):
    print('§1 各队 地/兵/密度，编队对各队的兵力比（T30；下标 0=机器人与无队）')
    for t in [600, 900] + [t for t in TICKS300 if t >= 1200]:
        i = t30(t)
        land, bal = T30['land'][i], T30['bal'][i]
        sl, sb = T30['squadLand'][i], T30['squadBal'][i]
        row = '｜'.join(f'T{j} {100*land[j]/LAND:.1f}%/{k(bal[j])}/密{bal[j]/max(1,land[j]):.0f}' for j in range(1, NT + 1))
        print(f'   t={T30["t"][i]}: {row}｜机 {100*land[0]/LAND:.1f}%｜编队 {100*sl/LAND:.1f}%（{sl} 格）/{k(sb)}/密{sb/max(1,sl):.0f}｜'
              + '、'.join(f'编队兵÷T{j} 兵 {sb/max(1,bal[j]):.2f}' for j in ENEMY) + f'｜编队占本队 地 {100*sl/max(1,land[OUR]):.0f}% 兵 {100*sb/max(1,bal[OUR]):.0f}%')

if on(2):
    print('§2 接敌面：每 300 拍哪些号边界上有在线敌方真人的格子（C30 的 eh>0）；没有接敌面的号握着编队多少兵；贴着机器人的号')
    for t in range(900, END + 1, 300):
        fr, nofr, tb, nb, bots = [], [], 0, 0, []
        for b in ORDER:
            p = pid[b]
            if not alive_at(p, t) or left_at(p, t):
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
        if tb == 0:
            continue
        print(f'   t={t}: 接敌 {len(fr)} 个 {" ".join(fr) or "-"}｜不接敌 {len(nofr)} 个 {" ".join(nofr) or "-"}，握兵 {k(nb)}（编队 {k(tb)} 的 {100*nb/max(1,tb):.0f}%）｜贴着机器人 {" ".join(bots) or "-"}')

if on(3):
    print('§3 我方队的路人队友，以及 --ids 指定的玩家：地/兵（HS，每 300 拍一个点）')
    mates = [p['id'] for p in J['players'] if p['team'] == OUR and p['id'] not in sq]
    for q in mates + IDS:
        pts = '；'.join(f'{t}: {hs(q, t)[0]}/{k(hs(q, t)[1])}' for t in (600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4800, 5400) if t in HS['t'])
        print(f'   {nm(q)} 出生 {P[q]["spawn"]} 峰值 {P[q]["peakTerr"]}@{P[q]["peakT"]} 阵亡 {P[q]["deathT"]} 离场 {P[q]["leftT"]}：{pts}')
    don_sq_to_r = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] in sq and e['q'] not in sq]
    don_r_to_sq = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] not in sq and e['q'] in sq]
    print(f'   我方号 → 路人队友的捐兵 {len(don_sq_to_r)} 笔；路人队友 → 我方号 {len(don_r_to_sq)} 笔（到账 {k(sum(e["got"] for e in don_r_to_sq))}）')

if on(4):
    print('§4 已执行的捐兵（我方号之间）：按类别、按受赠方、税率；捐出方当拍的地/兵/密度')
    D = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] in sq and e['q'] in sq]
    got, fee = sum(e['got'] for e in D), sum(e['fee'] for e in D)
    if D:
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
    kinds_x = Counter(d['kind'].replace('_dispatch', '') for d in J['dispatch'] if d['exec'])
    print('   日志类别：' + '、'.join(f'{x} {n}（落地 {kinds_x[x]}）' for x, n in kinds.most_common()) + f'｜日志 {len(J["dispatch"])} 条，落地 {sum(1 for d in J["dispatch"] if d["exec"])} 条')
    for e in D:
        inc = S10[str(e['q'])]
        i = bisect.bisect_right(inc['t'], e['t']) - 1
        print(f'     t={e["t"]} {sq[e["p"]]}（{e["L0"]} 格/{k(e["B0"])}/密 {e["B0"]/max(1,e["L0"]):.0f}）→ {sq[e["q"]]}（{e["qL0"]} 格/{k(e["qB0"])}/密 {e["qB0"]/max(1,e["qL0"]):.0f}，正被真人打 {k(inc["inH"][i])}）到账 {k(e["got"])} 税 {k(e["fee"])} [{e.get("logKind")}] 配额 {e.get("quotaAfter")}/{e.get("cap")}')

if on(5):
    print('§5 打真人的同拍批（同号同拍 ≥3 条、目标是真人）：批前存兵、这一批合计打出（含手续费）、占比、目标当时的地/兵，批后 60/150 拍自己的地/兵')
    per = defaultdict(list)
    for e in ev:
        if e['type'] == 'attack' and e['p'] in sq and e['q'] < H and e['q'] not in sq:
            per[(e['p'], e['t'])].append(e)
    for (p, t), es in sorted(per.items(), key=lambda z: z[0][1]):
        if len(es) < 3:
            continue
        B0 = es[0]['B0']
        out = sum(x.get('troops', 0) + x.get('fee', 0) for x in es if x['ok'])
        tg = Counter(nm(x['q']) for x in es)
        L60, B60 = at(p, t + 60)
        L150, B150 = at(p, t + 150)
        print(f'   t={t} {sq[p]} ×{len(es)}（pct {min(x["pct"] for x in es)}–{max(x["pct"] for x in es)}；落空 {sum(1 for x in es if not x["ok"])}）批前 {es[0]["L0"]} 格/{k(B0)} 打出 {k(out)}（{100*out/max(1,B0):.0f}%；逐条 ' + '/'.join(k(x.get('troops', 0)) for x in es) + '）→ ' + '、'.join(f'{a_}×{n}' for a_, n in tg.items())
              + f'（目标 {es[0]["tL"]} 格/{k(es[0]["tB"])}）｜+60 拍 {L60} 格/{k(B60)}，+150 拍 {L150} 格/{k(B150)}')

if on(6):
    print('§6 阵亡号：死前 600/300/150/60 拍的 地/兵/密度，≥100k 的来袭指令，死前 600 拍收到的捐兵')
    for b in ORDER:
        p = pid[b]
        dt = dead_t(p) or END
        pts = '；'.join(f't={t} {at(p, t)[0]} 格/{k(at(p, t)[1])}/密 {at(p, t)[1]/max(1, at(p, t)[0]):.0f}' for t in (dt - 600, dt - 300, dt - 150, dt - 60))
        hits = [e for e in ev if e['type'] == 'attack' and e['ok'] and e['q'] == p and e['p'] < H and e['p'] not in sq and e['t'] >= dt - 700 and e['troops'] >= 100000]
        don = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['q'] == p and e['t'] >= dt - 600]
        dout = [e for e in ev if e['type'] == 'donate' and e['ok'] and e['p'] == p and e['t'] >= dt - 600]
        own = [e for e in ev if e['type'] in ('attack', 'boat') and e['ok'] and e['p'] == p and e['t'] >= dt - 600 and e['q'] < H]
        print(f'   {b}（阵亡 {P[p]["deathT"]}，离场 {P[p]["leftT"]}，峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}）：{pts}')
        print(f'      来袭 ≥100k：' + ('；'.join(f't={e["t"]} {nm(e["p"])} {k(e["troops"])}（当时它 {e["tL"]} 格/{k(e["tB"])}；对方 {e["L0"]} 格/{k(e["B0"])}）' for e in hits[:12]) or '无')
              + f'｜死前 600 拍收到捐兵 {len(don)} 笔 {k(sum(e["got"] for e in don))}，捐出 {len(dout)} 笔 {k(sum(e["got"] for e in dout))}（税 {k(sum(e["fee"] for e in dout))}），自己打真人 {len(own)} 条 {k(sum(e["troops"] for e in own))}')

if on(7):
    print('§7 机器人让出的地里编队拿到多少（pairAll，600 拍一窗；600=机器人合计）')
    for w in (0, 1, 2, 3):
        tot = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x < H)
        ours = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x in sq)
        mates_ = sum(n for ww, x, v, n in J['pairAll'] if ww == w and v == 600 and x < H and x not in sq and P[x]['team'] == OUR)
        per = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if ww == w and v == 600 and x < H:
                per[x] += n
        alive = [p['id'] for p in J['players'] if p['id'] < H and p['spawn'] and p['spawn'][0] >= 0 and alive_at(p['id'], 600 * w)]
        o = sorted(per.get(x, 0) for x in alive if x not in sq)
        s = sorted(per.get(x, 0) for x in alive if x in sq)
        if not s or not o:
            continue
        print(f'   {600*w}–{600*w+599}: 真人从机器人手里拿走 {tot} 格，编队 {ours}（{100*ours/max(1,tot):.1f}%；人数占 {100*len(s)/max(1,len(s)+len(o)):.0f}%），本队路人 {mates_}（{100*mates_/max(1,tot):.1f}%）｜每人中位：编队 {s[len(s)//2]}、其他在场真人 {o[len(o)//2]}（{len(o)} 人）')
    for t0, t1 in ((600, 900), (900, 1200), (1200, 1500), (900, 1500), (1500, 1800), (1800, 2100)):
        i0, i1 = t30(t0), t30(t1)
        db = T30['land'][i0][0] - T30['land'][i1][0]
        ds = T30['squadLand'][i1] - T30['squadLand'][i0]
        print(f'   {t0}→{t1}: 机器人与无队的地 少了 {db} 格（{100*db/LAND:.1f}%），编队多了 {ds} 格（{100*ds/LAND:.1f}%）｜' + '、'.join(f'T{j} {100*(T30["land"][i1][j]-T30["land"][i0][j])/LAND:+.1f}%' for j in range(1, NT + 1))
              + f'｜编队兵 {k(T30["squadBal"][i0])}→{k(T30["squadBal"][i1])}；' + '、'.join(f'T{j} 兵 {k(T30["bal"][i0][j])}→{k(T30["bal"][i1][j])}' for j in range(1, NT + 1)))

if on(8):
    print('§8 在场真人的地分布与我方号的名次（HS）')
    for t in (600, 900, 1200, 1500, 2100, 3000):
        if t not in HS['t']:
            continue
        i = HS['t'].index(t)
        al = [p['id'] for p in J['players'] if p['id'] < H and HS['terr'][i][p['id']] > 0]
        v = sorted((HS['terr'][i][x] for x in al), reverse=True)
        o = sorted((HS['terr'][i][x] for x in al if x not in sq), reverse=True)
        s = sorted((HS['terr'][i][pid[b]] for b in ORDER if HS['terr'][i][pid[b]] > 0), reverse=True)
        mt = sorted((HS['terr'][i][x] for x in al if x not in sq and P[x]['team'] == OUR), reverse=True)
        en = sorted((HS['terr'][i][x] for x in al if P[x]['team'] != OUR), reverse=True)
        ranks = ' '.join(f'{b} {1 + sum(1 for x in v if x > HS["terr"][i][pid[b]])}' for b in ORDER if HS['terr'][i][pid[b]] > 0)
        if not s or not o:
            print(f'   t={t} 在场 {len(al)} 人：其他真人中位 {o[len(o)//2] if o else "-"}｜我方号已全部不在场')
            continue
        print(f'   t={t} 在场 {len(al)} 人：其他真人中位 {o[len(o)//2]}（上四分位 {o[len(o)//4]}、下四分位 {o[3*len(o)//4]}）｜我方号中位 {s[len(s)//2]}（{s[-1]}–{s[0]}）｜本队路人中位 {mt[len(mt)//2] if mt else "-"}（{len(mt)} 人）｜敌方真人中位 {en[len(en)//2] if en else "-"}（{len(en)} 人）｜名次：{ranks}')

if on(11):
    print('§11 编队分段兵力收支（F30 合计）')
    segs = tuple((SEGS[i], SEGS[i + 1]) for i in range(len(SEGS) - 1)) + ((SEGS[-1], END),)
    for t0, t1 in segs + ((0, END),):
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
        f'{600*w}: +{sum(n for ww, x, v, n in J["pairAll"] if ww == w and x in sq and v < H and v not in sq)} / −{sum(n for ww, x, v, n in J["pairAll"] if ww == w and v in sq and x < H and x not in sq)}' for w in range(1, END // 600 + 1)))

if on(13):
    print('§13 --ids 指定的玩家和我方号：它的地归了谁（pairAll 全程合计，前 6；变成中立后被谁拿走不在此列）')
    for q in tuple(IDS) + tuple(pid[b] for b in ORDER):
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
    print(f'   {len(rows)} 笔（到账 {k(sum(r[3] for r in rows))}，税 {k(sum(r[8] for r in rows))}）：其后 300 拍受赠方的地 变多 {len(grew)} 笔（到账 {k(sum(r[3] for r in grew))}）、变少 {len(shrank)} 笔（到账 {k(sum(r[3] for r in shrank))}）、不变 {len(rows)-len(grew)-len(shrank)} 笔；受赠方 300 拍内清零 {sum(1 for r in rows if r[6] == 0)} 笔')
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
    print(f'§16 {FROM} 拍以后各号每 300 拍：地/兵/密度·敌邻格（C30 eh）｜窗口内 利息地租 / 打真人 / 出船 / 捐出 / 收到 / 被打掉')
    for b in ORDER:
        p = pid[b]
        print(f'   {b}:')
        for t in range(FROM, END + 1, 300):
            if not alive_at(p, t):
                break
            L, B = at(p, t)
            f = flows(p, t, t + 300)
            c = contact(p, t)
            print(f'      t={t}: {L}/{k(B)}/密 {B/max(1,L):.0f}·敌邻 {c["eh"]}·离场敌邻 {c["el"]}·机器人 {c["bot"]}·中立 {c["neut"]}·队友邻 {c["mateS"]}+{c["mateO"]}｜利息地租 {k(f["eco"])} 打真人 {k(-f["atkHuman"])} 出船 {k(-f["boat"])} 捐出 {k(-f["donOut"])} 收到 {k(f["donIn"])} 被打掉 {k(-f["dmg"])}')

k2 = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'


def load_shadow():
    return json.load(open(f'/tmp/c136-r05/work/{M}-shadow.json'))


if on(17) and TL[1] > 0:
    print(f'§17 {TL[0]}–{TL[1]} 拍的逐条时间线：≥{MIN//1000}k 的 我方打真人（OUT）/ 真人打我方（IN）、已落地的捐兵（DON）、阵亡')
    rows = []
    for e in ev:
        if not (TL[0] <= e['t'] <= TL[1]):
            continue
        if e['type'] in ('attack', 'boat') and e.get('ok') and e.get('troops', 0) >= MIN:
            if e['q'] in sq and e['p'] < H and e['p'] not in sq:
                rows.append((e['t'], f'IN  {nm(e["p"])} → {nm(e["q"])} {k2(e["troops"])}（对方 {e["L0"]} 格/{k2(e["B0"])}；我 {e.get("tL")} 格/{k2(e.get("tB", 0))}）'))
            if e['p'] in sq and e['q'] < H and e['q'] not in sq:
                rows.append((e['t'], f'OUT {nm(e["p"])} → {nm(e["q"])} {k2(e["troops"])}（我 {e["L0"]} 格/{k2(e["B0"])}；对方 {e.get("tL")} 格/{k2(e.get("tB", 0))}）'))
        if e['type'] == 'donate' and e.get('ok') and e['p'] in sq:
            rows.append((e['t'], f'DON {nm(e["p"])} → {nm(e["q"])} 到账 {k2(e["got"])} 税 {k2(e["fee"])}'))
        if e['type'] == 'died' and e['p'] in sq:
            rows.append((e['t'], f'*** {nm(e["p"])} 阵亡'))
    for t, s in sorted(rows):
        print(f'   {t} {s}')
if on(17):
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
    for lo in range(300, 2400, 300):
        rows = [(r, c) for r in S_['ticks'] if lo <= r['t'] < lo + 300 for c in r['cmds'] if c['k'] == 'attack']
        by = Counter(cls(c['q']) for _, c in rows)
        pb = [c['pct'] for _, c in rows if cls(c['q']) == 'B']
        tb = [c.get('troops', 0) for _, c in rows if cls(c['q']) == 'B']
        pn = [c['pct'] for _, c in rows if cls(c['q']) == 'N']
        paths = Counter(' > '.join(r['sig'].split(' > ')[-5:-3]) for r, c in rows if cls(c['q']) == 'B')
        print(f'   {lo}–{lo+299}: 陆攻决策 {len(rows)}（中立 {by["N"]}、机器人 {by["B"]}、真人 {by["H"]}）｜打机器人 pct 中位 {statistics.median(pb) if pb else "-"}，pct≤48 的 {sum(1 for p in pb if p <= 48)}（{100*sum(1 for p in pb if p <= 48)/max(1,len(pb)):.0f}%），每条兵数中位 {statistics.median(tb) if tb else 0:.0f}'
              f'｜打中立 {len(pn)} 条（pct≤48 的 {sum(1 for p in pn if p <= 48)}）｜路径 ' + '；'.join(f'{p}×{n}' for p, n in paths.most_common(2)))

if on(19):
    print(f'§19 {FROM} 拍以后影子里每个号对真人的出手：每一段（相邻决策间隔 ≤15 拍归一段）的起止拍、条数、当时密度、pct、出口行；以及捐兵决策')
    S_ = load_shadow()
    for b in ORDER:
        segs = []
        dons = []
        for r in S_['ticks']:
            if r['bot'] != b or r['t'] < FROM:
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
        print(f'   {b}: 打真人 {len(segs)} 段，其中开打时密度 ≥100 的 {over} 段｜' + '；'.join(f'{s["t0"]}–{s["t1"]} ×{s["n"]} → {nm(s["q"])}（密 {s["d"]:.0f}，pct {min(s["pcts"])}–{max(s["pcts"])}，{s["line"]}）' for s in segs[:20]))
        if dons:
            print(f'      捐兵决策 {len(dons)} 条：' + '；'.join(dons[:8]) + (' …' if len(dons) > 8 else ''))

if on(23):
    print('§23 指令对账（逐号）：影子想发 / 同拍第 2 条起被「每拍 1 条」挤掉 / 客户端自报 sent−accepted（results.csv）/ 过了本地闸的局内指令 / 录像里实际出现的局内指令（replay_cmds.mjs → <局>-cmds.tsv）/ 差额')
    S_ = load_shadow()
    want = Counter(); squeezed = Counter(); want_don = Counter()
    for r in S_['ticks']:
        want[r['bot']] += len(r['cmds'])          # 影子输出的是过了「每拍 1 条」闸之后的指令
        want_don[r['bot']] += sum(1 for c in r['cmds'] if c['k'] == 'donate')
    try:                                           # 被挤掉的条数取自 shadow.mjs --match 的汇总行「按号：」
        for ln in open(f'/tmp/c136-r05/work/{M}-match.txt', encoding='utf-8'):
            if ln.strip().startswith('按号：'):
                f = ln.strip()[3:].split()
                for i in range(0, len(f) - 1, 2):
                    squeezed[f[i]] = int(f[i + 1])
    except FileNotFoundError:
        print(f'   （缺 {M}-match.txt：先跑 shadow.mjs {M} --quiet --match）')
    res = {r['bot']: r for r in csv.DictReader(open(os.environ.get('C136_DATA', '/agent/repos/c136-data') + f'/bundles/{M}/results.csv'))}
    inrep = Counter(); spawn_rep = Counter(); inrep_don = Counter()
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
                inrep_don[b[0]] += f[2] == 'donate'
    except FileNotFoundError:
        print(f'   （缺 {M}-cmds.tsv：先跑 replay_cmds.mjs {M} --out /tmp/c136-r05/work/{M}-cmds.tsv）')
    tw = ts = td = ta = ti = tm = tdw = tdi = 0
    for b in ORDER:
        if b not in res:
            continue
        d = int(res[b]['sent']) - int(res[b]['accepted'])
        passed = want[b]
        miss = passed - inrep[b]
        tw += want[b]; ts += squeezed[b]; td += d; ta += passed; ti += inrep[b]; tm += miss; tdw += want_don[b]; tdi += inrep_don[b]
        print(f'   {b}: 策略想发 {want[b] + squeezed[b]}｜同拍被挤 {squeezed[b]}｜自报 sent {res[b]["sent"]} − accepted {res[b]["accepted"]} = {d}｜过闸 {passed}（其中捐兵 {want_don[b]}）｜录像里 {inrep[b]}（其中捐兵 {inrep_don[b]}；选点期另有 {spawn_rep[b]} 条）｜没出现在录像里 {miss}（{100*miss/max(1,passed):.0f}%；其中捐兵 {want_don[b] - inrep_don[b]}）')
    print(f'   合计：策略想发 {tw + ts}｜同拍被挤 {ts}｜自报 sent−accepted {td}｜过闸 {ta}（捐兵 {tdw}）｜录像里 {ti}（捐兵 {tdi}）｜没出现在录像里 {tm}（{100*tm/max(1,ta):.0f}%；捐兵 {tdw - tdi}，陆攻/出船 {tm - (tdw - tdi)}）')
    print('   按 300 拍：过闸的局内指令（影子；陆攻+出船 | 捐兵）/ 录像里执行拍落在该窗口的指令（陆攻+出船 | 捐兵）')
    pa = Counter(); pd = Counter(); ra = Counter(); rd = Counter()
    for r in S_['ticks']:
        for c in r['cmds']:
            (pd if c['k'] == 'donate' else pa)[r['t'] // 300 * 300] += 1
    for e in ev:
        if e.get('p') in sq and e['type'] in ('attack', 'boat'):
            ra[e['t'] // 300 * 300] += 1
        if e.get('p') in sq and e['type'] == 'donate':
            rd[e['t'] // 300 * 300] += 1
    print('   ' + '；'.join(f'{w}: {pa[w]}|{pd[w]} / {ra[w]}|{rd[w]}' for w in sorted(set(pa) | set(ra) | set(pd) | set(rd))))

if on(25):
    print('§25 除名时手里还有多少兵：阵亡拍之前最后一个 S10 采样点（≤10 拍前）的 地/兵，与历史峰值地的比；除名规则 game.js aliveTick L1298-1312（地 ≤ 峰值的 1/4，峰值随时间回落）')
    tot = 0
    for b in ORDER:
        p = pid[b]
        d = dead_t(p)
        s = S10[str(p)]
        if d is None:
            zi = next((i for i in range(len(s['t'])) if s['t'][i] > 600 and s['terr'][i] == 0), None)
            if zi is None:
                print(f'   {b}: 未阵亡（终局 {s["terr"][-1]} 格/{k(s["bal"][-1])}）')
                continue
            i = zi - 1
            print(f'   {b}: 未判阵亡；t={s["t"][i]} {s["terr"][i]} 格/{k(s["bal"][i])} → t={s["t"][zi]} 0 格/0 兵｜峰值 {P[p]["peakTerr"]}（地÷峰值 {s["terr"][i]/P[p]["peakTerr"]:.2f}）')
            tot += s['bal'][i]
            continue
        i = max(j for j in range(len(s['t'])) if s['t'][j] < d)
        tot += s['bal'][i]
        print(f'   {b}: 阵亡 {d}；t={s["t"][i]} {s["terr"][i]} 格/{k(s["bal"][i])}（密 {s["bal"][i]/max(1,s["terr"][i]):.0f}）｜峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}（地÷峰值 {s["terr"][i]/P[p]["peakTerr"]:.2f}）')
    print(f'   除名前最后一个采样点的存兵合计 {k(tot)}')

if on(26) and WINS:
    print('§26 窗口合计：已执行陆攻（不含手续费）按窗口、按对手；捐兵；--ids 玩家在窗口起点的地/兵')
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
    dn = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] in sq]
    for t0, t1 in WINS:
        o = win(t0, t1, True)
        print(f'   {t0}–{t1} 我方打真人：{sum(v[0] for v in o.values())} 条 {k2(sum(v[1] for v in o.values()))}｜' + '；'.join(f'{a_}→{b} {n} 条 {k2(x)}' for (a_, b), (n, x) in sorted(o.items(), key=lambda z: -z[1][1])[:12]))
        i = win(t0, t1, False)
        print(f'   {t0}–{t1} 真人打我方：{sum(v[0] for v in i.values())} 条 {k2(sum(v[1] for v in i.values()))}｜' + '；'.join(f'{a_}→{b} {n} 条 {k2(x)}' for (a_, b), (n, x) in sorted(i.items(), key=lambda z: -z[1][1])[:12]))
        d = [e for e in dn if t0 <= e['t'] <= t1]
        print(f'   {t0}–{t1} 捐兵 {len(d)} 笔 到账 {k2(sum(e["got"] for e in d))} 税 {k2(sum(e["fee"] for e in d))}')
        th = max(t for t in HS['t'] if t <= max(t0, HS['t'][0]))
        if IDS:
            print(f'   t={th} --ids 玩家（HS）：' + '；'.join(f'{nm(q)} {hs(q, th)[0]} 格/{k2(hs(q, th)[1])}' for q in IDS) + f'｜合计 {k2(sum(hs(q, th)[1] for q in IDS))}')
        print(f'   t={t0} 我方号（S10）：' + '；'.join(f'{b} {at(pid[b], t0)[0]} 格/{k2(at(pid[b], t0)[1])}' for b in ORDER if alive_at(pid[b], t0)))

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
    allsent = sum(v['sent'] for v in vol)
    print(f'   打真人 {len(vol)} 轮 {k2(allsent)}，其中放行的 {len(over)} 轮（出兵 {k2(sum(v["sent"] for v in over))}＝{100*sum(v["sent"] for v in over)/max(1,allsent):.0f}%，不含手续费）；目标存兵 ≥ 自己的 {len(eq)} 轮（{k2(sum(v["sent"] for v in eq))}），≥ 2×自己的 {len(big)} 轮（{k2(sum(v["sent"] for v in big))}）')
    for v in sorted(vol, key=lambda v: v['t0']):
        back = [e for e in ev if e['type'] == 'attack' and e.get('ok') and e['p'] == v['q'] and e['q'] in sq and v['t0'] < e['t'] <= v['t0'] + 300]
        me_back = [e for e in back if e['q'] == v['p']]
        flag = '放行' if v['B0'] > 100 * v['L0'] else '    '
        print(f'      {flag} {v["t0"]}–{v["t1"]} {sq[v["p"]]} → {nm(v["q"])} {v["n"]} 条 {k2(v["sent"])}｜我 {v["L0"]} 格/{k2(v["B0"])}（密 {v["B0"]/max(1,v["L0"]):.0f}）对方 {v["tL"]} 格/{k2(v["tB"])}（密 {v["tB"]/max(1,v["tL"]):.0f}；存兵是我的 {v["tB"]/max(1,v["B0"]):.2f} 倍）'
              f'｜其后 300 拍它打我方号 {len(back)} 条 {k2(sum(e["troops"] for e in back))}（其中打这个号 {len(me_back)} 条 {k2(sum(e["troops"] for e in me_back))}）')
    byq = defaultdict(lambda: [0, 0, set()])
    for v in over:
        byq[v['q']][0] += 1; byq[v['q']][1] += v['sent']; byq[v['q']][2].add(sq[v['p']])
    print('   放行按目标：' + '；'.join(f'{nm(q)} {n} 轮 {k2(x)}（{"、".join(sorted(b))}）' for q, (n, x, b) in sorted(byq.items(), key=lambda z: -z[1][1])))
    dn = [e for e in ev if e['type'] == 'donate' and e.get('ok') and e['p'] in sq and e['q'] in sq]
    sink = []
    for e in dn:
        la = at(e['q'], e['t'])[0]; lb = at(e['q'], e['t'] + 300)[0]
        if lb <= 0.8 * la:
            sink.append(e)
    print(f'   捐兵 {len(dn)} 笔里，受赠方其后 300 拍的地少了 ≥20% 的 {len(sink)} 笔：到账 {k2(sum(e["got"] for e in sink))}、税 {k2(sum(e["fee"] for e in sink))}；其余 {len(dn) - len(sink)} 笔到账 {k2(sum(e["got"] for e in dn if e not in sink))}')

if on(29):
    print('§29 被围（C30：敌方真人 eh=0、离场敌人 el=0、机器人=0、中立=0 → 边界上只有队友和水）：每 300 拍被围的号、它们握着编队多少兵、密度；罚息')
    for t in range(900, END + 1, 300):
        boxed, tb, bb = [], 0, 0
        for b in ORDER:
            p = pid[b]
            if not alive_at(p, t) or left_at(p, t):
                continue
            L, B = at(p, t)
            c = contact(p, t)
            tb += B
            if c['eh'] == 0 and c['el'] == 0 and c['bot'] == 0 and c['neut'] == 0:
                boxed.append(f'{b}({L}/{k(B)}/密{B/max(1,L):.0f}；我方号邻 {c["mateS"]} 路人邻 {c["mateO"]})'); bb += B
        if tb:
            print(f'   t={t}: 被围 {len(boxed)} 个，握兵 {k(bb)}（编队 {k(tb)} 的 {100*bb/max(1,tb):.0f}%）：' + ' '.join(boxed))
    print('   各号被围的拍段（C30 每 30 拍一个点；连续被围 ≥90 拍才列）：')
    for b in ORDER:
        p = pid[b]
        c = C30[str(p)]
        runs = []; start = None; prev = None
        for i, t in enumerate(c['t']):
            if not alive_at(p, t) or left_at(p, t):
                break
            bx = c['eh'][i] == 0 and c['el'][i] == 0 and c['bot'][i] == 0 and c['neut'][i] == 0 and t >= 300
            if bx and start is None:
                start = t
            if not bx and start is not None:
                runs.append((start, prev)); start = None
            prev = t
        if start is not None:
            runs.append((start, prev))
        runs = [r for r in runs if r[1] - r[0] >= 90]
        tot = sum(r[1] - r[0] for r in runs)
        print(f'      {b}: ' + ('；'.join(f'{r[0]}–{r[1]}' for r in runs) or '无') + f'｜合计 {tot} 拍')

if on(30):
    print('§30 本队：编队 对 路人队友 对 敌队——地占全图、兵、在场人数（T30；路人 = 本队 − 编队）')
    for t in [600, 900] + [t for t in TICKS300 if t >= 1200]:
        i = t30(t)
        land, bal = T30['land'][i], T30['bal'][i]
        sl, sb = T30['squadLand'][i], T30['squadBal'][i]
        ml, mb = land[OUR] - sl, bal[OUR] - sb
        act = T30['active'][i]; sact = T30['squadActive'][i]
        print(f'   t={T30["t"][i]}: 编队 {100*sl/LAND:.1f}%/{k(sb)}（在场 {sact}）｜路人队友 {100*ml/LAND:.1f}%/{k(mb)}（在场 {act[OUR]-sact}）｜' + '｜'.join(f'T{j} {100*land[j]/LAND:.1f}%/{k(bal[j])}（在场 {act[j]}）' for j in ENEMY) + f'｜机 {100*land[0]/LAND:.1f}%')

if on(31):
    print('§31 本队路人队友逐个：出生、峰值、离场、阵亡；它丢的地归了谁（pairAll 前 4）；到我方号最近出生点的距离')
    mates = [p for p in J['players'] if p['team'] == OUR and p['id'] not in sq]
    for p in sorted(mates, key=lambda p: -(p['peakTerr'] or 0)):
        q = p['id']
        tk = defaultdict(int)
        for ww, x, v, n in J['pairAll']:
            if v == q:
                tk[x] += n
        sp = p['spawn']
        dn_ = min((math.hypot(sp[0] - P[s]['spawn'][0], sp[1] - P[s]['spawn'][1]), sq[s]) for s in sq) if sp and sp[0] >= 0 else (-1, '-')
        print(f'   {nm(q)} 出生 {sp}（离 {dn_[1]} {dn_[0]:.0f} 格）峰值 {p["peakTerr"]}@{p["peakT"]} 离场 {p["leftT"]} 阵亡 {p["deathT"]}｜陆攻 {p["nAtk"]} 船 {p["nBoat"]} 打真人 {k(p["sentH"])}｜被拿走 {sum(tk.values())} 格：' + '、'.join(f'{nm(x)} {n}' for x, n in sorted(tk.items(), key=lambda z: -z[1])[:4]))
