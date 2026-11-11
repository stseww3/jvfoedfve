#!/usr/bin/env python3
# match_facts.py — 复盘里要引用、而 truth_digest.py 不直接给的逐号/逐窗数字（全部从 match_truth.mjs 的真值 JSON 机械算出）。
# 用法：python3 scripts/match_facts.py <matchId> [--sec a,b,c] [--at t1,t2,…] [--win 600] [--bots x,y]
#   各节（--sec 选，默认全部）：
#     bots     每个我方号在 --at 各拍的 地/兵/密度
#     line     编队最大号的地与 22% 线（--at 各拍），线下的号
#     hits     谁打我方号（真人；陆攻 + 登陆）：条数、合计、首末拍；--list 逐条
#     batch    我方号同拍 ≥3 条陆攻/出船的批，按 --bwin 分窗
#     don      捐兵：按 --win 分窗的笔数/到账/税；捐出方→受赠方矩阵；到账被截断的；两号来回倒手；转手
#     cap      超软上限少拿的利息，按 --phases 分段
#     ledger   编队收支（全程 + 按 --phases 分段）与各号收支
#     top      全场峰值地最大的 8 个玩家每 600 拍的 地/兵
#     cmds     我方号各段落地的指令数（打真人 / 打机器人 / 打中立 / 出船 / 捐兵）
#     enc      各号：峰值地@拍、几个时点的地、第一条打真人的指令、打真人条数
#     deaths   每个阵亡号：死前的 地/兵、死前 --dwin（默认 300）拍 谁打它、它自己做了什么、收到/捐出多少
import json, sys, bisect, statistics as st
from collections import defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
H = J['humans']
END = J['endTick']
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
ev = J['events']
ad = J['allDon']
CATS = J['cats']
LAND = None
SEC = set(val('--sec', 'bots,line,hits,batch,don,cap,ledger,top,cmds,enc,deaths').split(','))
WIN = int(val('--win', 600))
AT = [int(x) for x in val('--at', ','.join(str(t) for t in range(600, END + 1, 600))).split(',')]
PH = [int(x) for x in val('--phases', '0,1500,3000,4284,5400,99999').split(',')]
BW = [int(x) for x in val('--bwin', '0,600,900,1500,2100,3000,4500,6000,99999').split(',')]
only = set(val('--bots', '').split(',')) - {''}


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:18]
    return '中立' if p == 512 else f'机器人#{p}'


def at(p, t):
    s = J['S10'].get(str(p))
    if s is None:
        return (0, 0)
    if 0 <= P[p]['deathT'] <= t:
        return (0, 0)
    i = bisect.bisect_right(s['t'], t) - 1
    return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'


bots = [b for b in sq.values() if not only or b in only]

if 'bots' in SEC:
    print('== bots 各号 地/兵/密度 ==')
    for b in bots:
        out = []
        for t in AT:
            L, B = at(pid[b], t)
            out.append(f'{t}: {L}/{k(B)}/{(B/L if L else 0):.0f}')
        print(' ', b, ' | '.join(out))

if 'line' in SEC:
    print('== line 编队最大号的地 与 22% 线 ==')
    for t in AT:
        m = max(at(p, t)[0] for p in sq)
        if m:
            print(f'  t={t} 最大 {m} → 22% = {0.22*m:.0f}｜线下：', ', '.join(f'{b}({at(p,t)[0]})' for p, b in sq.items() if 0 < at(p, t)[0] < 0.22 * m) or '无')

if 'hits' in SEC:
    print('== hits 谁打我方号（真人：陆攻 + 登陆；合计 ≥ --hmin）==')
    hmin = float(val('--hmin', 200e3))
    for b in bots:
        rows = defaultdict(list)
        for e in ev:
            if e['type'] in ('attack', 'boat-land') and e.get('q') == pid[b] and 0 <= e['p'] < H and e['p'] not in sq and e.get('ok', True):
                rows[e['p']].append((e['t'], e['type'], e.get('troops', 0), e.get('pct')))
        for q, r in sorted(rows.items(), key=lambda x: -sum(y[2] for y in x[1])):
            tot = sum(y[2] for y in r)
            if tot < hmin:
                continue
            land = [y for y in r if y[1] == 'attack']
            boat = [y for y in r if y[1] == 'boat-land']
            print(f'  {nm(q)}(#{q},T{P[q]["team"]}) → {b}: 陆攻 {len(land)} 条 {k(sum(y[2] for y in land))}（pct {sorted(set(y[3] for y in land))[:6]}）登陆 {len(boat)} 次 {k(sum(y[2] for y in boat))}｜首 {r[0][0]} 末 {r[-1][0]}')
            if '--list' in a:
                print('     ', ' '.join(f"{y[0]}{'船' if y[1]=='boat-land' else ''}:{k(y[2])}" for y in r[:40]))

bt = defaultdict(list)
for e in ev:
    if e['type'] in ('attack', 'boat') and e['p'] in sq:
        bt[(e['p'], e['t'])].append(e)
if 'batch' in SEC:
    print('== batch 我方号的同拍批（≥3 条陆攻/出船）==')
    for lo, hi in zip(BW, BW[1:]):
        bs = [(p, t, v) for (p, t), v in bt.items() if lo <= t < hi and len(v) >= 3]
        n9 = sorted([x for x in bs if len(x[2]) >= 8], key=lambda x: x[1])
        allc = sum(len(v) for (p, t), v in bt.items() if lo <= t < hi)
        if not allc:
            continue
        print(f'  {lo}–{min(hi, END)}: 落地 {allc} 条；批 {len(bs)} 个（{sum(len(x[2]) for x in bs)} 条），≥8 条的 {len(n9)} 个：', ' '.join(f'{sq[p]}@{t}×{len(v)}' for p, t, v in n9[:30]))
    print('  ≥5 条的批（批前存兵 → 连手续费打出、占比、目标）：')
    for (p, t), v in sorted(bt.items(), key=lambda x: x[0][1]):
        if len(v) >= 5 and (not only or sq[p] in only):
            B0 = max(e.get('B0', 0) for e in v)
            tot = sum(e.get('troops', 0) + e.get('fee', 0) for e in v if e.get('ok', True))
            tg = defaultdict(int)
            for e in v:
                tg[nm(e['q']) if e.get('q') is not None else '船'] += 1
            if B0 >= float(val('--bmin', 100e3)):
                print(f'    {sq[p]} t={t} ×{len(v)} 批前 {k(B0)} 打出 {k(tot)}（{100*tot/B0 if B0 else 0:.0f}%）目标 {dict(tg)} pct {sorted(set(e.get("pct") for e in v))[:5]}')

if 'don' in SEC:
    print('== don 捐兵 ==')
    mine = [x for x in ad if x[1] in sq]
    print(f'  全程：{len(mine)} 笔 到账 {sum(x[3] for x in mine)} 税 {sum(x[4] for x in mine)}（税/到账 {100*sum(x[4] for x in mine)/max(1,sum(x[3] for x in mine)):.1f}%）')
    for lo, hi in [(0, 4284), (4284, 99999)]:
        r = [x for x in mine if lo <= x[0] < hi]
        print(f'  t∈[{lo},{hi}): {len(r)} 笔 到账 {sum(x[3] for x in r)} 税 {sum(x[4] for x in r)}')
    print('  按窗：' + '；'.join(f'{w}: {len(r)} 笔 {k(sum(x[3] for x in r))}/税 {k(sum(x[4] for x in r))}' for w in range(0, END + 1, WIN) for r in [[x for x in mine if w <= x[0] < w + WIN]] if r))
    mat = defaultdict(lambda: [0, 0, 0])
    for t, p, q, g, f in mine:
        m = mat[(nm(p), nm(q))]; m[0] += 1; m[1] += g; m[2] += f
    print('  捐出方→受赠方（到账 ≥ 500k 的）：' + '；'.join(f'{a_}→{b_} {n} 笔 {k(g)}/税 {k(f)}' for (a_, b_), (n, g, f) in sorted(mat.items(), key=lambda x: -x[1][1]) if g >= 500e3))
    out_by = defaultdict(lambda: [0, 0, 0]); in_by = defaultdict(lambda: [0, 0])
    for t, p, q, g, f in mine:
        o = out_by[nm(p)]; o[0] += 1; o[1] += g; o[2] += f
        i = in_by[nm(q)]; i[0] += 1; i[1] += g
    print('  各号 捐出(笔/到账/税)｜收到(笔/到账)：' + '；'.join(f'{b} {out_by[b][0]}/{k(out_by[b][1])}/{k(out_by[b][2])}｜{in_by[b][0]}/{k(in_by[b][1])}' for b in sq.values()))
    cl = [x for x in mine if x[3] < 2 * x[4]]
    cl1 = [x for x in mine if x[3] < x[4]]
    print(f'  到账 < 2×税 的 {len(cl)} 笔（到账 {k(sum(x[3] for x in cl))}，税 {k(sum(x[4] for x in cl))}）；其中到账 < 税 的 {len(cl1)} 笔（到账 {k(sum(x[3] for x in cl1))}，税 {k(sum(x[4] for x in cl1))}）')
    # 想捐多少（按捐兵事件的 pct×捐出方存兵）对 到账：被受赠方硬上限截掉的部分
    dv = [e for e in ev if e['type'] == 'donate' and e['p'] in sq and e.get('ok', True)]
    wantOf = lambda e: min(e['B0'] * (e['pct'] + 1) // 1024, e['B0'] - e['fee'])
    want = sum(wantOf(e) for e in dv if e.get('B0'))
    got = sum(e.get('got') or 0 for e in dv if e.get('B0'))
    if want:
        print(f'  想捐（pct×捐出方存兵）合计 {k(want)}，到账 {k(got)} → 被受赠方上限截掉 {k(want-got)}（{100*(want-got)/want:.1f}%）')
        for lo, hi in [(0, 4284), (4284, 99999)]:
            w_ = sum(wantOf(e) for e in dv if e.get('B0') and lo <= e['t'] < hi)
            g_ = sum(e.get('got') or 0 for e in dv if e.get('B0') and lo <= e['t'] < hi)
            if w_:
                print(f'     t∈[{lo},{hi}): 想捐 {k(w_)} 到账 {k(g_)} 截掉 {k(w_-g_)}（{100*(w_-g_)/w_:.1f}%）')
    # 来回倒手：A→B 之后 300 拍内 B→A
    GAP = int(val('--ppgap', 300))
    pp = defaultdict(lambda: [0, 0, 0])
    ppset = set()
    ms = sorted(mine)
    for i, (t, p, q, g, f) in enumerate(ms):
        for j in range(i + 1, len(ms)):
            t2, p2, q2, g2, f2 = ms[j]
            if t2 - t > GAP:
                break
            if p2 == q and q2 == p:
                ppset.add(i); ppset.add(j)
                break
    for i in ppset:
        t, p, q, g, f = ms[i]
        key = tuple(sorted((nm(p), nm(q))))
        m = pp[key]; m[0] += 1; m[1] += g; m[2] += f
    tot_pp = [sum(v[i] for v in pp.values()) for i in range(3)]
    print(f'  两号之间 {GAP} 拍内来回倒手：{tot_pp[0]} 笔 到账 {k(tot_pp[1])} 税 {k(tot_pp[2])}（占全部到账 {100*tot_pp[1]/max(1,sum(x[3] for x in mine)):.1f}%、全部税 {100*tot_pp[2]/max(1,sum(x[4] for x in mine)):.1f}%）：' + '；'.join(f'{a_}↔{b_} {n} 笔 {k(g)}/税 {k(f)}' for (a_, b_), (n, g, f) in sorted(pp.items(), key=lambda x: -x[1][1])))
    if ppset:
        ts = sorted(ms[i][0] for i in ppset)
        print(f'     时间范围 {ts[0]}–{ts[-1]}；t<4284 的 {sum(1 for x in ts if x < 4284)} 笔')
    # 转手：某号在 600 拍窗内收到 ≥1M 且同窗再捐出 ≥ 收到额的 50%
    for b in sq.values():
        p = pid[b]
        for w in range(0, END + 1, 600):
            gi = sum(x[3] for x in mine if x[2] == p and w <= x[0] < w + 600)
            go = sum(x[3] for x in mine if x[1] == p and w <= x[0] < w + 600)
            fo = sum(x[4] for x in mine if x[1] == p and w <= x[0] < w + 600)
            if gi >= 1e6 and go >= 0.5 * gi:
                print(f'  转手 {b} t={w}–{w+599}: 收到 {k(gi)}，同窗再捐出 {k(go)}（税 {k(fo)}）')

F = J['F30']
if 'cap' in SEC:
    print('== cap 超软上限少拿的利息（累计差分）==')
    tot_all = 0
    for lo, hi in zip(PH, PH[1:]):
        out = []
        for p, b in sq.items():
            f = F[str(p)]
            cum = lambda t: max([c for tt, c in zip(f['t'], f['capLoss']) if tt <= t] or [0])
            v = cum(hi) - cum(lo)
            if v > 20e3:
                out.append((v, b))
        s_ = sum(v for v, b in out); tot_all += s_
        print(f'  {lo}–{min(hi, END)}: 合计 {k(s_)}｜' + ' '.join(f'{b} {k(v)}' for v, b in sorted(out, reverse=True)))
    print(f'  全程合计（>20k 的项）{k(tot_all)}')

if 'ledger' in SEC:
    print('== ledger 编队收支 ==')

    def flows(p, lo, hi):
        f = F[str(p)]

        def cum(t):
            i = bisect.bisect_right(f['t'], t) - 1
            return f['flows'][i] if i >= 0 else [0] * len(CATS)
        a_, b_ = cum(lo), cum(hi)
        return [y - x for x, y in zip(a_, b_)]
    for lo, hi in [(0, 99999)] + list(zip(PH, PH[1:])):
        lo, hi = lo - lo % 30, min(hi, END) - min(hi, END) % 30   # 收支累计每 30 拍采样一次：窗口对齐到 30 拍栅格 (lo, hi]
        acc = [0] * len(CATS)
        for p in sq:
            for i, v in enumerate(flows(p, lo, hi)):
                acc[i] += v
        tax = sum(x[4] for x in ad if x[1] in sq and lo < x[0] <= hi)
        b0 = sum(at(p, lo)[1] for p in sq) if lo else 0
        b1 = sum(at(p, min(hi, END))[1] for p in sq)
        cl = 0
        for p in sq:
            f = F[str(p)]
            cum = lambda t: max([c for tt, c in zip(f['t'], f['capLoss']) if tt <= t] or [0])
            cl += cum(hi) - cum(lo)
        print(f'  ({lo}, {hi}]: 兵 {k(b0)}→{k(b1)}｜罚息 {k(cl)}｜' + ' '.join(f'{c} {k(v)}' for c, v in zip(CATS, acc) if abs(v) >= 1000) + f'｜donOut+donIn = {k(acc[5]+acc[6])}，其中捐兵税 {k(tax)}（占 eco {100*tax/max(1,acc[0]):.1f}%）')
    for p, b in sq.items():
        acc = flows(p, 0, 99999)
        print(f'    {b}: ' + ' '.join(f'{c} {k(v)}' for c, v in zip(CATS, acc) if abs(v) >= 50e3))

if 'top' in SEC:
    print('== top 峰值地最大的 8 个玩家（每 600 拍 地/兵）==')
    hs = J['HS']
    tops = sorted(J['players'], key=lambda p: -p['peakTerr'])[:8]
    for p in tops:
        q = p['id']
        print(f"  {nm(q)}(#{q},T{p['team']}{'，我方号' if q in sq else ''}) 峰值 {p['peakTerr']}@{p['peakT']} 离场 {p['leftT']} 阵亡 {p['deathT']}：" + ' | '.join(f"{t}: {hs['terr'][i][q]}/{k(hs['bal'][i][q])}" for i, t in enumerate(hs['t']) if t % 600 == 0 and t > 0))

if 'cmds' in SEC:
    print('== cmds 我方号各段落地的指令 ==')
    for lo, hi in zip(PH, PH[1:]):
        c = defaultdict(lambda: defaultdict(int))
        for e in ev:
            if e['p'] in sq and e['type'] in ('attack', 'boat', 'donate') and lo <= e['t'] < hi:
                q = e.get('q')
                tgt = '捐' if e['type'] == 'donate' else '船' if e['type'] == 'boat' else ('真人' if q is not None and 0 <= q < H else '中立' if q == 512 else '机器人')
                c[sq[e['p']]][tgt] += 1
        tot = defaultdict(int)
        for b, v in c.items():
            for kk, n in v.items():
                tot[kk] += n
        print(f'  {lo}–{min(hi, END)}: 合计 {dict(tot)}｜' + '；'.join(f'{b} {dict(v)}' for b, v in c.items()))

if 'enc' in SEC:
    print('== enc 各号：峰值地@拍｜t=900/1500/3000/4200 的地｜第一条打真人的指令｜打真人条数 ==')
    for p, b in sq.items():
        hum = [e for e in ev if e['p'] == p and e['type'] == 'attack' and e.get('q') is not None and 0 <= e['q'] < H and e.get('ok', True)]
        print(f"  {b}: 峰值 {P[p]['peakTerr']}@{P[p]['peakT']}｜" + '/'.join(str(at(p, t)[0]) for t in (900, 1500, 3000, 4200)) + f"｜首次打真人 t={hum[0]['t'] if hum else '-'}（{nm(hum[0]['q']) if hum else '-'}）｜打真人 {len(hum)} 条 {k(sum(e.get('troops', 0) for e in hum))}｜阵亡 {P[p]['deathT']}")

if 'deaths' in SEC:
    print('== deaths 每个阵亡号：死前 600/300/120/30 拍的 地/兵｜死前 300 拍 谁打它、它自己做了什么、收到/捐出多少 ==')
    W_ = int(val('--dwin', 300))
    for p, b in sorted(sq.items(), key=lambda x: (P[x[0]]['deathT'] if P[x[0]]['deathT'] >= 0 else 1e9)):
        dt = P[p]['deathT']
        if dt < 0:
            # 没被判阵亡：看地是否归零
            s = J['S10'][str(p)]
            z = next((t for t, L in zip(s['t'], s['terr']) if t > 600 and L == 0), None)
            print(f'  {b}: 未判阵亡；地归零拍 {z}；峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}')
            if z is None:
                continue
            dt = z
        snap = ' | '.join(f'-{d}: {at(p, dt-d)[0]}/{k(at(p, dt-d)[1])}' for d in (600, 300, 120, 60, 30))
        hit = defaultdict(lambda: [0, 0, 0, 0])
        for e in ev:
            if dt - W_ <= e['t'] <= dt and e['type'] in ('attack', 'boat-land') and e.get('q') == p and e['p'] != p and e.get('ok', True):
                h = hit[e['p']]; h[0] += 1; h[1] += e.get('troops', 0); h[2] = h[2] or e['t']; h[3] = e['t']
        mine_ = [e for e in ev if dt - W_ <= e['t'] <= dt and e['p'] == p and e['type'] in ('attack', 'boat', 'donate')]
        ah = [e for e in mine_ if e['type'] == 'attack' and e.get('q') is not None and 0 <= e['q'] < H]
        dn = [e for e in mine_ if e['type'] == 'donate' and e.get('ok', True)]
        din = [x for x in ad if x[2] == p and dt - W_ <= x[0] <= dt]
        print(f'  {b}: 阵亡 {dt}（峰值 {P[p]["peakTerr"]}@{P[p]["peakT"]}，四分之一线 {P[p]["peakTerr"]//4}）｜{snap}')
        print(f'      死前 {W_} 拍被打：' + ('；'.join(f'{nm(q)}(T{P[q]["team"] if q in P else "-"}) {n} 条 {k(tr)}（{t0}–{t1}）' for q, (n, tr, t0, t1) in sorted(hit.items(), key=lambda x: -x[1][1])) or '无'))
        print(f'      自己：打真人 {len(ah)} 条 {k(sum(e.get("troops", 0) for e in ah))}（' + ','.join(sorted(set(nm(e['q']) for e in ah))) + f'）；捐出 {len(dn)} 笔 {k(sum(e.get("got", 0) for e in dn))}（税 {k(sum(e.get("fee", 0) for e in dn))}）；收到 {len(din)} 笔 {k(sum(x[3] for x in din))}')
