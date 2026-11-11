#!/usr/bin/env python3
# A017_facts.py — A017（拆盘局）里通用脚本不直接给的数字。Y 盘（9 个号，没有录像）只用 in_game.log / traj.csv / results.csv；
#   X 盘（ryan_m，有录像）另读 /tmp/c136-r05/truth/A017.json、/tmp/c136-r05/work/A017-shadow.json、A017-cmds.tsv。
# 用法：python3 scripts/review_build/A017_facts.py [--sec A,B,C,D,E,F,G,H]
#   A  阵形：日志里每个号最后一条协调器指派点 → 两两间距、质心、半径、外接框；缺的角位
#   B  Y 盘各号在几个时点的地，对 X 盘（同图同种子）在场真人的中位数
#   C  「纯收入」检验：相邻两条 [HL-TICK]（90 拍）之间，按引擎 economyTick 公式（game.js L739-746、L778-790）
#      从前一条的 地/兵 推「一个兵都不花、也没挨打」时后一条该有多少兵；实际 − 预测 = 这一窗的净支出（负数 = 花掉或被打掉）。
#      发令窗 = 这一窗里自报指令数 cmds 增加 ≥ --stream（默认 10）条。
#   D  清仓窗：90 拍内存兵掉 ≥ --dump（默认 60）% 且窗前存兵 ≥ 10 万；窗前连续多少个发令窗、窗后 180 拍的地
#   E  Y 盘 9 个号合计（每 300 拍）与 results.csv 各号阵亡时的各队总地
#   F  X 盘校准：对 ryan_m 的日志做同样的 C/D，并排列出录像里这一窗真正执行了几条指令、打出多少兵
#   G  X 盘 ryan_m：影子决策 → 录像落地的逐批对账（决策拍、落地拍、陈旧度、相邻两批间隔、两批之间没落地的决策数）
#   H  X 盘 ryan_m 对 TRABZONSPOR：几个时点双方的 地/兵/密度；ryan_m 的边界构成
#   I  客户端时钟：results.csv 每个号上报阵亡的墙上时间 at 与它上报的本地拍 tick；用 Y 盘最后三行拟合服务器时钟，
#      其余各行「按这条线当时服务器走到第几拍 − 上报的本地拍」= 这个号的客户端在上报那一刻落后多少拍
#   J  日志先后次序：in_game.log 每行带一个全局递增的行号（到达收集器的先后）。同一时刻各号写到第几拍，
#      就能比出谁的客户端走在前面、谁落在后面（粒度 90 拍）；再用 X 盘 ryan_m 的实测落后量（指令落地拍 − 决策拍）把 Y 盘的绝对落后量锚出来
import csv, json, sys, math, re, statistics
from collections import defaultdict

a = sys.argv[1:]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
SEC = set(val('--sec', 'A,B,C,D,E,F,G,H,I,J').split(','))
STREAM = int(val('--stream', 10))
DUMP = float(val('--dump', 60))
B = '/agent/repos/c136-data/bundles/A017'
LAND = json.load(open(B + '/card.json'))['mapLand']
YB = ['alex_k', 'talon5', 'zexos1', 'sora_w', 'leo_tx', 'riku_x', 'kaito9', 'noah88', 'zero_7']


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k' if abs(x) >= 1000 else str(int(x))


# ---- 引擎公式（逐字移植 game.js：iV、INTEREST_TABLE、interestRate、economyTick、addBalance 的硬上限）----
iV = lambda x, y: math.floor((x + 0.5) / y)


def mn(h, cs):
    v = iV(h + 1, 2)
    for _ in range(cs):
        v = iV(v + iV(h, v), 2)
    return v


TABLE = [100 + (0 if iV(25600 * i, 508) < 1 else mn(iV(25600 * i, 508), 9)) for i in range(512)]


def rate(terr, bal, t):
    n1 = TABLE[iV(511 * terr, LAND)]
    if t < 1920:
        n1 = max(iV(100 * (13440 - 6 * t), 1920), n1)
    cap = min(100 * terr, 1e9)
    if cap > 0 and bal > cap:
        n1 -= iV(2 * n1 * (bal - cap), cap)
    return min(max(n1, 0), 700)


def pure(terr, bal, t0, t1):
    """从 t0 那一拍结束时的 (terr, bal) 起，地不变、不花兵、不挨打，推到 t1 那一拍结束。"""
    for t in range(t0 + 1, t1 + 1):
        if t % 10 == 9:
            bal = min(bal + max(iV(rate(terr, bal, t) * bal, 1e4), 1), max(bal, 150 * terr))
            if t % 100 == 99:
                bal = min(bal + terr, max(bal, 150 * terr))
    return bal


traj = defaultdict(list)
for r in csv.DictReader(open(B + '/traj.csv')):
    traj[r['bot']].append(dict(t=int(r['t']), terr=int(r['terr']), bal=int(r['bal']), dens=float(r['dens']), nb=int(r['nb']), neut=int(r['neut']), cmds=int(r['cmds']), boats=int(r['boats'])))
for b in traj:
    traj[b].sort(key=lambda r: r['t'])
res = {r['bot']: r for r in csv.DictReader(open(B + '/results.csv'))}


def windows(bot):
    out = []
    rows = traj[bot]
    for x, y in zip(rows, rows[1:]):
        if y['t'] - x['t'] != 90:
            continue
        p0 = pure(x['terr'], x['bal'], x['t'], y['t'])
        p1 = pure(y['terr'], x['bal'], x['t'], y['t'])
        out.append(dict(t0=x['t'], t1=y['t'], terr0=x['terr'], terr1=y['terr'], bal0=x['bal'], bal1=y['bal'], dens0=x['dens'], nb0=x['nb'], neut0=x['neut'], dcmd=y['cmds'] - x['cmds'], dboat=y['boats'] - x['boats'],
                        pred=p0, pred1=p1, net=y['bal'] - p0, net1=y['bal'] - p1))
    return out


if 'A' in SEC:
    print('§A 阵形：日志里每个号最后一条 [HL-SPAWN-BACKEND] 指派点（Y 盘 9 个号 + 进了 X 盘的 ryan_m）')
    pts = {}
    roles = {}
    for ln in open(B + '/in_game.log', encoding='utf-8'):
        m = re.search(r'\[([a-z0-9_]+)\] \[HL-SPAWN-BACKEND\] me=(\d+) slot=(\d+) role=(\S+) -> \((\d+),(\d+)\).*minAllyDist=(-?\d+)', ln)
        if m:
            pts[m.group(1)] = (int(m.group(5)), int(m.group(6)))
            roles[m.group(1)] = (m.group(4), int(m.group(3)), int(m.group(7)))
    solves = sum(1 for ln in open(B + '/in_game.log', encoding='utf-8') if 'BACKEND-SPAWN-COORD' in ln and 'Solved' in ln)
    distinct = len({re.sub(r'in [\d.]+ms', '', ln.split('\t', 1)[1]) for ln in open(B + '/in_game.log', encoding='utf-8') if 'BACKEND-SPAWN-COORD' in ln and 'Solved' in ln})
    print(f'   协调器求解日志 {solves} 条，去掉耗时后不同的解 {distinct} 种；每条都是「Solved 10 bots」（十个号当一个编队）')
    for b, (x, y) in sorted(pts.items(), key=lambda kv: roles[kv[0]][1]):
        others = [math.hypot(x - q[0], y - q[1]) for c, q in pts.items() if c != b]
        oy = [math.hypot(x - q[0], y - q[1]) for c, q in pts.items() if c != b and c != 'ryan_m']
        print(f'   slot {roles[b][1]} {b:7s} {roles[b][0]:18s} ({x},{y}) 最近队友点 {min(others):.0f} 格（日志 minAllyDist={roles[b][2]}）｜不算 ryan_m 的点 {min(oy):.0f} 格' + ('  ← 这个号在 X 盘，这个点在 Y 盘没人' if b == 'ryan_m' else ''))
    for tag, names in (('十个点', list(pts)), ('Y 盘九个点', [b for b in pts if b != 'ryan_m'])):
        P = [pts[b] for b in names]
        cx, cy = sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P)
        d = sorted(math.hypot(p[0] - q[0], p[1] - q[1]) for i, p in enumerate(P) for q in P[i + 1:])
        nn = sorted(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in P if q != p) for p in P)
        print(f'   {tag}：质心 ({cx:.0f},{cy:.0f})，最远点离质心 {max(math.hypot(p[0]-cx, p[1]-cy) for p in P):.0f} 格；两两最小 {d[0]:.0f}、最大 {d[-1]:.0f}；最近邻距离中位 {statistics.median(nn):.0f}；外接框 {min(p[0] for p in P)}–{max(p[0] for p in P)} × {min(p[1] for p in P)}–{max(p[1] for p in P)}'
              f'（{(max(p[0] for p in P)-min(p[0] for p in P))}×{(max(p[1] for p in P)-min(p[1] for p in P))} 格）')
    print(f'   全图 1541×1080，陆地 {LAND} 格；20 个真人人均 {LAND//20} 格；间距 86 格的六角排布每个点 {0.866*86*86:.0f} 格（含水）')
    for ln in open(B + '/in_game.log', encoding='utf-8'):
        m = re.search(r'\[([a-z0-9_]+)\] \[HL-SPAWN\] me=(\d+) slot=(\d+) \(squad=(\d+),rankIdx=(\d+)\) -> \((\d+),(\d+)\)', ln)
        if m:
            print(f'   自主兜底 [HL-SPAWN]：{m.group(1)} 看到的我方号 squad={m.group(4)} → ({m.group(6)},{m.group(7)})')

if 'B' in SEC:
    print('§B Y 盘各号的地，对 X 盘（同图同种子）在场真人（不含 ryan_m）的地中位数；Y 盘的拍是它自己的拍')
    J = json.load(open('/tmp/c136-r05/truth/A017.json'))
    HS = J['HS']
    H = J['humans']
    for t in (630, 900, 1170, 1530, 1800, 2070, 2430):
        ys = sorted(r['terr'] for b in YB for r in traj[b] if r['t'] == t)
        xt = min(HS['t'], key=lambda q: abs(q - t))
        i = HS['t'].index(xt)
        xs = sorted(HS['terr'][i][p] for p in range(H) if p != 18 and HS['terr'][i][p] > 0)
        print(f'   t={t}: Y 盘 {len(ys)} 个号 合计 {sum(ys)}（{100*sum(ys)/LAND:.1f}%）中位 {ys[len(ys)//2]}（{ys[0]}–{ys[-1]}）｜X 盘 t={xt} 在场真人 {len(xs)} 人 中位 {xs[len(xs)//2]}（下四分位 {xs[len(xs)//4]}、上四分位 {xs[3*len(xs)//4]}）｜Y 中位÷X 中位 {ys[len(ys)//2]/xs[len(xs)//2]:.2f}')
    print('   各号 t=1530 的地（按日志指派点离九点质心的距离排）：')
    pts = {}
    for ln in open(B + '/in_game.log', encoding='utf-8'):
        m = re.search(r'\[([a-z0-9_]+)\] \[HL-SPAWN-BACKEND\] .* -> \((\d+),(\d+)\)', ln)
        if m and m.group(1) != 'ryan_m':
            pts[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    cx, cy = sum(p[0] for p in pts.values()) / 9, sum(p[1] for p in pts.values()) / 9
    for b in sorted(pts, key=lambda q: math.hypot(pts[q][0] - cx, pts[q][1] - cy)):
        g = {r['t']: r for r in traj[b]}
        print(f'      {b:7s} 离质心 {math.hypot(pts[b][0]-cx, pts[b][1]-cy):4.0f} 格｜t=900 {g[900]["terr"]:6d}｜t=1530 {g[1530]["terr"]:6d}｜t=2070 {g[2070]["terr"]:6d}｜峰值 {int(res[b]["peak"]):6d}')

if 'C' in SEC:
    print(f'§C 纯收入检验（发令窗 = 90 拍内自报指令 +≥{STREAM} 条；净 = 实际存兵 − 按「不花不挨打、地不变」推出的存兵；括号内是按窗末的地推的）')
    tot = defaultdict(float)
    for b in YB + ['ryan_m']:
        W = windows(b)
        S = [w for w in W if w['dcmd'] >= STREAM]
        if not S:
            print(f'   {b}: 没有发令窗')
            continue
        quiet = [w for w in S if abs(w['net']) <= 0.03 * w['bal0'] or abs(w['net1']) <= 0.03 * w['bal0']]
        small = [w for w in S if w['net'] >= -0.10 * w['bal0']]
        big = [w for w in S if w['net'] < -0.30 * w['bal0']]
        late = [w for w in S if w['t0'] >= 1200]
        lq = [w for w in late if w['net'] >= -0.10 * w['bal0']]
        print(f'   {b:7s} 发令窗 {len(S)} 个（{S[0]["t0"]}–{S[-1]["t1"]}），窗内自报指令 {sum(w["dcmd"] for w in S)} 条｜净支出 ≤3% 的 {len(quiet)} 个，≤10% 的 {len(small)} 个，>30% 的 {len(big)} 个'
              f'｜t≥1200 的发令窗 {len(late)} 个：自报 {sum(w["dcmd"] for w in late)} 条，净支出 ≤10% 的 {len(lq)} 个（这些窗自报 {sum(w["dcmd"] for w in lq)} 条、净合计 {k(sum(w["net"] for w in lq))}、窗前存兵合计 {k(sum(w["bal0"] for w in lq))}）')
        if b != 'ryan_m':
            tot['S'] += len(late); tot['q'] += len(lq); tot['cmd'] += sum(w['dcmd'] for w in late); tot['qcmd'] += sum(w['dcmd'] for w in lq)
            tot['net'] += sum(w['net'] for w in lq); tot['bal'] += sum(w['bal0'] for w in lq)
    print(f'   Y 盘合计（t≥1200）：发令窗 {tot["S"]:.0f} 个、自报 {tot["cmd"]:.0f} 条｜净支出 ≤10% 的 {tot["q"]:.0f} 个窗、自报 {tot["qcmd"]:.0f} 条：净合计 {k(tot["net"])}，是窗前存兵合计 {k(tot["bal"])} 的 {100*tot["net"]/tot["bal"]:.1f}%')
    if '--list' in a:
        for b in YB + ['ryan_m']:
            print(f'   -- {b}')
            for w in windows(b):
                if w['t0'] >= 1100:
                    print(f'      {w["t0"]}–{w["t1"]}: 地 {w["terr0"]}→{w["terr1"]} 兵 {k(w["bal0"])}→{k(w["bal1"])}｜推 {k(w["pred"])}（{k(w["pred1"])}）净 {k(w["net"])}（{100*w["net"]/max(1,w["bal0"]):.0f}%）｜指令 +{w["dcmd"]} 船 +{w["dboat"]}｜nb {w["nb0"]} neut {w["neut0"]}')

if 'D' in SEC:
    print(f'§D 清仓窗（90 拍内存兵掉 ≥{DUMP:.0f}%，窗前存兵 ≥10 万）')
    n = 0
    for b in YB + ['ryan_m']:
        W = windows(b)
        g = {r['t']: r for r in traj[b]}
        for i, w in enumerate(W):
            if w['bal0'] >= 100000 and w['bal1'] <= (1 - DUMP / 100) * w['bal0']:
                run = 0
                j = i - 1
                while j >= 0 and W[j]['dcmd'] >= STREAM:
                    run += 1; j -= 1
                runq = 0
                j = i - 1
                while j >= 0 and W[j]['dcmd'] >= STREAM and W[j]['net'] >= -0.10 * W[j]['bal0']:
                    runq += 1; j -= 1
                flat = 0
                j = i - 1
                while j >= 0 and abs(W[j]['terr1'] - W[j]['terr0']) <= 0.03 * W[j]['terr0']:
                    flat += 1; j -= 1
                after = '、'.join(f'+{d}: {g[w["t1"]+d]["terr"]}/{k(g[w["t1"]+d]["bal"])}' for d in (90, 180, 270) if w['t1'] + d in g)
                spent = w['pred'] - w['bal1']
                per = spent / max(1, w['terr1'] - w['terr0']) if w['terr1'] > w['terr0'] else float('nan')
                n += 1
                print(f'   {b:7s} {w["t0"]}–{w["t1"]}: 兵 {k(w["bal0"])}→{k(w["bal1"])}（−{100*(1-w["bal1"]/w["bal0"]):.0f}%；比纯收入少 {k(spent)}）地 {w["terr0"]}→{w["terr1"]}（密度 {w["dens0"]:.0f}→{w["bal1"]/max(1,w["terr1"]):.0f}）｜这一窗自报指令 +{w["dcmd"]}'
                      f'｜窗前连续发令窗 {run} 个（其中净支出 ≤10% 的 {runq} 个 = {runq*90} 拍），地连续不变（±3%）{flat} 个窗｜每多一格 {per:.0f} 兵｜其后 {after}｜阵亡 {res[b]["tick"]}')
    print(f'   合计 {n} 个清仓窗')
    print('   按 0.65^n（每条指令打出当时存兵的 35%）：n=5 剩 12%，n=7 剩 5%，n=9 剩 2%')

if 'E' in SEC:
    print('§E Y 盘 9 个号合计（只算当拍有快照的号）与 results.csv 各号阵亡时的各队总地')
    for t in range(300, 4501, 300):
        tt = t if t % 90 == 0 else (t // 90) * 90
        rows = [(b, next((r for r in traj[b] if r['t'] == tt), None)) for b in YB]
        rows = [(b, r) for b, r in rows if r]
        if not rows:
            continue
        L = sum(r['terr'] for _, r in rows); Bal = sum(r['bal'] for _, r in rows)
        mx = max(rows, key=lambda q: q[1]['terr'])
        print(f'   t={tt}: {len(rows)} 个号 地 {L}（{100*L/LAND:.1f}%）兵 {k(Bal)} 密度 {Bal/max(1,L):.0f}｜最大 {mx[0]} {mx[1]["terr"]}｜密度 ≥60 的号 {sum(1 for _, r in rows if r["dens"] >= 60)} 个握兵 {k(sum(r["bal"] for _, r in rows if r["dens"] >= 60))}')
    for b in sorted(res, key=lambda q: int(res[q]['tick'])):
        r = res[b]
        tt = json.loads(r['teamTotals'])
        s = sum(tt.values())
        print(f'   {b:7s} {r["event"]} t={r["tick"]} 峰值 {r["peak"]} 末地 {r["lastTerritory"]} 存兵 {r["balance"]} sent {r["sent"]} accepted {r["accepted"]}｜机器人 {100*tt.get("0",0)/LAND:.1f}% 队1 {100*tt.get("1",0)/LAND:.1f}% 队2 {100*tt.get("2",0)/LAND:.1f}%（合计 {100*s/LAND:.1f}%）' + ('  ← X 盘' if b == 'ryan_m' else ''))
    # 队 2 里编队以外的部分：阵亡拍前最近一条快照的编队合计 对 teamTotals 的队 2
    for b in ('leo_tx', 'alex_k', 'zexos1', 'sora_w', 'riku_x', 'kaito9', 'noah88'):
        t = int(res[b]['tick'])
        sq = 0
        for c in YB:
            if c == b:
                continue
            rr = [r for r in traj[c] if r['t'] <= t]
            if rr and int(res[c]['tick']) > t:
                sq += rr[-1]['terr']
        t2 = json.loads(res[b]['teamTotals']).get('2', 0)
        print(f'      {b} 阵亡 t={t}：队 2 总地 {t2}；其余在场我方号最近快照合计 {sq}；差 {t2 - sq}（队 2 里不是我方号的地，含快照误差）')

if 'F' in SEC or 'G' in SEC or 'H' in SEC:
    J = json.load(open('/tmp/c136-r05/truth/A017.json'))
    ev = [e for e in J['events'] if e['p'] == 18]
    SH = json.load(open('/tmp/c136-r05/work/A017-shadow.json'))
    dec = [(r['t'], c) for r in SH['ticks'] for c in r['cmds']]

if 'F' in SEC:
    print('§F X 盘校准：ryan_m 的日志窗 对 录像真值（同一窗里录像执行的陆攻/出船条数、打出的兵）')
    for w in windows('ryan_m'):
        if w['t0'] < 540:
            continue
        ex = [e for e in ev if w['t0'] < e['t'] <= w['t1'] and e['type'] in ('attack', 'boat')]
        ok = [e for e in ex if e.get('ok') and e.get('troops', 0) > 0]
        dd = [c for t, c in dec if w['t0'] < t <= w['t1']]
        print(f'   {w["t0"]}–{w["t1"]}: 地 {w["terr0"]}→{w["terr1"]} 兵 {k(w["bal0"])}→{k(w["bal1"])}｜纯收入推 {k(w["pred"])} 净 {k(w["net"])}（{100*w["net"]/max(1,w["bal0"]):.0f}%）｜自报指令 +{w["dcmd"]}（影子 {len(dd)}）｜录像执行 {len(ex)} 条（有效 {len(ok)} 条，打出 {k(sum(e.get("troops",0)+e.get("fee",0) for e in ok))}）')

if 'G' in SEC:
    print('§G X 盘 ryan_m：录像里每个落地拍的指令 对 影子决策（pct 相同、决策在落地之前、每个决策只用一次；批内倒序匹配）')
    used = set()
    byt = defaultdict(list)
    for e in ev:
        if e['type'] in ('attack', 'boat'):
            byt[e['t']].append(e)
    prev = None
    rows = []
    for t in sorted(byt):
        es = byt[t]
        st = []
        for e in es:
            kk = 'attack' if e['type'] == 'attack' else 'boatTo'
            cand = [i for i, (dt, c) in enumerate(dec) if i not in used and dt < t and c['k'] == kk and c['pct'] == e['pct']]
            if cand:
                i = cand[0] if len(es) >= 3 else cand[-1]
                used.add(i)
                st.append(t - dec[i][0])
        void = sum(1 for e in es if not e.get('ok') or e.get('troops', 0) <= 0)
        out = sum(e.get('troops', 0) + e.get('fee', 0) for e in es if e.get('ok'))
        rows.append((t, len(es), st, void, out, None if prev is None else t - prev))
        prev = t
    for t, n, st, void, out, gap in rows:
        print(f'   t={t}: 落地 {n} 条（落空 {void}）打出 {k(out)}｜对上影子决策 {len(st)} 条，陈旧度 {min(st) if st else "-"}–{max(st) if st else "-"} 拍｜距上一个落地拍 {gap if gap is not None else "-"} 拍')
    batches = [r for r in rows if r[1] >= 3]
    gaps = [b2[0] - b1[0] for b1, b2 in zip(batches, batches[1:])]
    print(f'   落地拍 {len(rows)} 个，其中 ≥3 条的批 {len(batches)} 个共 {sum(r[1] for r in batches)} 条；批与批的间隔：{gaps}（×56 毫秒 = {[round(g*0.056,1) for g in gaps]} 秒）')
    allst = [s for r in rows for s in r[2]]
    for lo, hi in ((0, 700), (700, 900), (900, 1200), (1200, 1600), (1600, 2100), (2100, 2800)):
        ss = [s for r in rows if lo <= r[0] < hi for s in r[2]]
        dn = sum(1 for t, c in dec if lo <= t < hi)
        en = sum(r[1] for r in rows if lo <= r[0] < hi)
        print(f'   {lo}–{hi}: 影子决策 {dn} 条，录像落地 {en} 条；落地指令的陈旧度中位 {statistics.median(ss) if ss else "-"}（{min(ss) if ss else "-"}–{max(ss) if ss else "-"}）')
    print(f'   全程：影子决策 {len(dec)} 条（策略自报 {traj["ryan_m"][-1]["cmds"]} 条），录像落地 {sum(r[1] for r in rows)} 条，没落地 {len(dec) - sum(r[1] for r in rows)} 条；对上的 {len(allst)} 条陈旧度中位 {statistics.median(allst)}')
    tg = defaultdict(lambda: [0, 0, 0])
    for t, c in dec:
        kind = '中立' if c['q'] == 512 else ('真人' if c['q'] < J['humans'] else '机器人')
        if c['k'] == 'boatTo':
            kind = '船'
        tg[kind][0] += 1
        tg[kind][1] += c.get('troops', 0)
    print('   影子决策按目标：' + '；'.join(f'{q} {v[0]} 条（名义 {k(v[1])}）' for q, v in tg.items()))
    hd = [(t, c) for t, c in dec if c['k'] == 'attack' and c['q'] == 8]
    print(f'   打 TRABZONSPOR 的影子决策 {len(hd)} 条：首条 t={hd[0][0]}（pct {hd[0][1]["pct"]}，{k(hd[0][1]["troops"])}），末条 t={hd[-1][0]}；录像里第一条落地 t={min(e["t"] for e in ev if e["type"]=="attack" and e.get("q")==8)}')

if 'H' in SEC:
    print('§H X 盘 ryan_m 对 TRABZONSPOR（#8，T1）')
    S = J['S10']['18']
    HS = J['HS']
    import bisect

    def me_at(t):
        i = bisect.bisect_right(S['t'], t) - 1
        return (S['terr'][i], S['bal'][i]) if i >= 0 else (0, 0)
    for t in HS['t']:
        if t > 2700:
            break
        i = HS['t'].index(t)
        m, e = me_at(t), (HS['terr'][i][8], HS['bal'][i][8])
        print(f'   t={t}: ryan_m {m[0]} 格/{k(m[1])}（密 {m[1]/max(1,m[0]):.0f}）｜TRABZONSPOR {e[0]} 格/{k(e[1])}（密 {e[1]/max(1,e[0]):.0f}）｜兵 ÷ 对方 {m[1]/max(1,e[1]):.2f}')
    print('   逐条（录像真值）：ryan_m 打 TRABZONSPOR 的陆攻当拍双方的 地/兵；TRABZONSPOR 打 ryan_m 的陆攻当拍双方的 地/兵')
    mine = [e for e in J['events'] if e['p'] == 18 and e['type'] == 'attack' and e.get('q') == 8 and e.get('ok')]
    for t in sorted({e['t'] for e in mine}):
        es = [e for e in mine if e['t'] == t]
        print(f'      t={t} ryan_m ×{len(es)}：批前 {es[0]["L0"]} 格/{k(es[0]["B0"])} 打出 {k(sum(e["troops"]+e["fee"] for e in es))}｜对方 {es[0]["tL"]} 格/{k(es[0]["tB"])}（密 {es[0]["tB"]/max(1,es[0]["tL"]):.0f}）')
    C = J['C30']['18']
    for t in (600, 900, 1200, 1500, 1800, 2010):
        i = min(range(len(C['t'])), key=lambda q: abs(C['t'][q] - t))
        print(f'   边界 t={C["t"][i]}: 中立 {C["neut"][i]} 敌方真人 {C["eh"][i]} 机器人 {C["bot"][i]} 队友 {C["mateS"][i]}+{C["mateO"][i]}')
    pr = [x for x in J['pairs'] if (x.get('a') == 8 and x.get('b') == 18) or (x.get('a') == 18 and x.get('b') == 8)] if isinstance(J['pairs'], list) and J['pairs'] and isinstance(J['pairs'][0], dict) else []
    for x in pr:
        print('   pairs', {kk: x[kk] for kk in list(x)[:10]})
    sp = {p['id']: p for p in J['players']}
    a_, b_ = sp[18]['spawn'], sp[8]['spawn']
    print(f'   出生点：ryan_m {a_}（录像里没有它的出生指令，引擎在选点期结束时随机落子）｜TRABZONSPOR {b_}｜相距 {math.hypot(a_[0]-b_[0], a_[1]-b_[1]):.0f} 格')
    near = sorted((math.hypot(a_[0] - p['spawn'][0], a_[1] - p['spawn'][1]), p['name'], p['team']) for p in J['players'] if p['id'] < J['humans'] and p['id'] != 18 and p['spawn'][0] >= 0)
    print('   离 ryan_m 出生点最近的真人：' + '；'.join(f'{n}（T{tm}）{d:.0f} 格' for d, n, tm in near[:4]))
    lg = (1198, 294)
    nr = sorted((math.hypot(lg[0] - p['spawn'][0], lg[1] - p['spawn'][1]), p['name'], p['team']) for p in J['players'] if p['id'] < J['humans'] and p['id'] != 18 and p['spawn'][0] >= 0)
    print(f'   协调器给 ryan_m 的点 {lg}：X 盘里离它最近的真人 ' + '；'.join(f'{n}（T{tm}）{d:.0f} 格' for d, n, tm in nr[:4]))

if 'I' in SEC:
    from datetime import datetime
    print('§I 客户端时钟（results.csv 的 at / tick / seconds）')
    rows = []
    for b, r in res.items():
        at = datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp()
        rows.append((b, int(r['tick']), at, int(r['seconds']), r['event']))
    rows.sort(key=lambda q: q[2])
    t00 = json.load(open(B + '/card.json'))['timestampMs'] / 1000
    yr = [q for q in rows if q[0] != 'ryan_m']
    fit = yr[-3:]
    n = len(fit)
    mx = sum(q[1] for q in fit) / n; my = sum(q[2] for q in fit) / n
    slope = sum((q[1] - mx) * (q[2] - my) for q in fit) / sum((q[1] - mx) ** 2 for q in fit)
    icpt = my - slope * mx
    print(f'   用 Y 盘最后三行（{"、".join(q[0] for q in fit)}）拟合：每拍 {1000*slope:.1f} 毫秒；第 0 拍在对局卡时间戳之后 {icpt - t00:.1f} 秒；三行残差 ' + '、'.join(f'{(q[2]-(icpt+slope*q[1]))/slope:+.1f} 拍' for q in fit))
    for b, tick, at, sec, evn in rows:
        srv = (at - icpt) / slope
        own = sec - tick * slope
        tag = '（X 盘：另一条时间轴，下面单列）' if b == 'ryan_m' else f'按线当时服务器在第 {srv:.0f} 拍 → 落后 {srv - tick:.0f} 拍（{(srv - tick) * slope:.1f} 秒）'
        print(f'   {b:7s} {evn} 本地拍 {tick}，上报时刻 +{at - t00:.1f} 秒，客户端自计 {sec} 秒｜{tag}')
    # 相邻两行：墙上时间差 对 本地拍差
    for (b1, k1, a1, _, _), (b2, k2, a2, _, _) in zip(yr, yr[1:]):
        print(f'      {b1}→{b2}: 本地拍 +{k2 - k1}，墙上 +{a2 - a1:.2f} 秒' + ('  ← 后上报的号本地拍反而靠前' if k2 < k1 else ''))
    # X 盘：OPENING-CHECK 里同一时刻 ryan_m 的拍号 − Y 盘各号的拍号
    for ln in open(B + '/in_game.log', encoding='utf-8'):
        if 'OPENING-CHECK' in ln:
            tk = {m.group(1): int(m.group(2)) for m in re.finditer(r'\[APEX\] ([a-z0-9_]+):tick=(\d+)', ln)}
            oth = sorted(v for b, v in tk.items() if b != 'ryan_m')
            off = tk['ryan_m'] - oth[len(oth) // 2]
            print(f'   [OPENING-CHECK]：同一时刻 ryan_m 在第 {tk["ryan_m"]} 拍，Y 盘九个号在第 {oth[0]}–{oth[-1]} 拍 → X 盘比 Y 盘早开 {off} 拍（{off*slope:.1f} 秒）')
            b, tick, at, sec, evn = next(q for q in rows if q[0] == 'ryan_m')
            srvx = (at - icpt) / slope + off
            print(f'   ryan_m（X 盘）：上报时 X 盘服务器约在第 {srvx:.0f} 拍，上报的本地拍 {tick} → 落后约 {srvx - tick:.0f} 拍；录像里它 2580 拍地归零、重放判定 2751 拍除名')
            break

if 'J' in SEC:
    print('§J 日志先后次序（[HL-TICK] 行的全局行号）')
    seqs = defaultdict(list)   # bot -> [(seq, t)]
    for ln in open(B + '/in_game.log', encoding='utf-8'):
        m = re.match(r'(\d+)\t\[([a-z0-9_]+)\] \[HL-TICK\] t=(\d+) ', ln)
        if m:
            seqs[m.group(2)].append((int(m.group(1)), int(m.group(3))))
    ybots = [b for b in seqs if b != 'ryan_m']
    allrows = sorted((sq, b, t) for b in ybots for sq, t in seqs[b])
    # 每个 Y 盘的号在写第 T 拍那一行时，Y 盘走得最靠前的号已经写到第几拍
    front = []; cur = 0
    for sq, b, t in allrows:
        cur = max(cur, t); front.append((sq, cur))
    def front_at(sq):
        v = 0
        for s2, f in front:
            if s2 > sq: break
            v = f
        return v
    print('   Y 盘各号相对「Y 盘走得最靠前的号」落后多少拍（写第 T 拍那一行时，最靠前的号已写到的拍 − T；粒度 90）：')
    lv = [900, 1260, 1620, 1980, 2340, 2700, 3060, 3420, 3780, 4140]
    print('     号      ' + ' '.join(f'{t:>5d}' for t in lv))
    for b in sorted(ybots):
        d = {t: sq for sq, t in seqs[b]}
        print(f'     {b:7s} ' + ' '.join(f'{(front_at(d[t]) - t):>5d}' if t in d else '    -' for t in lv))
    lead = defaultdict(int)
    for sq, b, t in allrows:
        if t >= 900 and front_at(sq) == t and not any(s2 < sq and f >= t for s2, f in front):
            lead[b] += 1
    print('   900 拍起各拍号第一个写到的号（次数）：' + '、'.join(f'{b} {n}' for b, n in sorted(lead.items(), key=lambda q: -q[1])))
    # X 盘锚：ryan_m 的实测落后量（§G 的落地批：决策拍→落地拍）
    try:
        T = json.load(open('/tmp/c136-r05/truth/A017.json'))
        SH = json.load(open('/tmp/c136-r05/work/A017-shadow.json'))
        ev = [e for e in T['events'] if e.get('p') == 18 and e['type'] in ('attack', 'boat')]
        land_ticks = sorted(set(e['t'] for e in ev))
    except Exception as ex:
        land_ticks = []
    # 手工锚点来自 batch_origin.py / cmd_staleness.py 的输出：（本地决策拍, 落后拍）
    anchor = [(700, 0), (790, 25), (850, 35), (915, 60), (970, 105), (1090, 175), (1280, 290), (1592, 414), (2020, 483)]
    def lagx(t):
        if t <= anchor[0][0]: return anchor[0][1]
        for (a0, l0), (a1, l1) in zip(anchor, anchor[1:]):
            if a0 <= t <= a1: return l0 + (l1 - l0) * (t - a0) / (a1 - a0)
        return anchor[-1][1]
    OFF = 91
    print(f'   用 X 盘锚 Y 盘：ryan_m 写第 T 拍时 X 盘服务器在 T+落后量（批落地实测），Y 盘服务器 = 再减 {OFF} 拍（X 盘早开 {OFF} 拍）；与那一刻 Y 盘最靠前的号写到的拍相减（粒度 90，真值在 −90…0 之内再小一点）')
    for sq, t in seqs['ryan_m']:
        if t in (720, 900, 1080, 1260, 1440, 1620, 1800, 1980):
            ysrv = t + lagx(t) - OFF
            f = front_at(sq)
            back = min((tt for s2, b2, tt in allrows if s2 < sq and s2 > sq - 40), default=0)
            print(f'     ryan_m 写 t={t}（实测落后 {lagx(t):.0f}）→ Y 盘服务器约第 {ysrv:.0f} 拍；此刻 Y 盘最靠前的号写到 {f} → 最靠前的号落后 {ysrv - f - 90:.0f}…{ysrv - f:.0f} 拍')
