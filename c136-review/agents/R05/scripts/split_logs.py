#!/usr/bin/env python3
# split_logs.py — 拆盘局里「不在录像那一盘」的我方号，只有日志可用时的事实账（全部从 in_game.log + results.csv 机械算出）。
#   这些号的拍号是另一盘自己的拍号，和录像那一盘不是同一条时间轴。
# 用法：python3 scripts/split_logs.py <matchId> [--sec tl,sum,res,disp,box,cmds,lag] [--bots a,b] [--at 90,180,…] [--all]（--all：连录像盘里的号也算）
#   tl    每号在 --at 各拍（取 ≤ 该拍的最近一条 [HL-TICK]）的 地/兵/密度/敌邻数 nb/中立邻 neut
#   sum   这些号合计：地、占全图、兵、有日志的号数（每 300 拍）
#   res   results.csv：每号阵亡拍、峰值、当时各队总地（teamTotals）→ 各队份额
#   disp  调度日志：按 捐出方→受赠方、类别、boxedIn 计数；用捐出方「下一条日志里的存兵」判断这一条有没有真的捐出去
#         （引擎 transfer：捐出 (pct+1)/1024×存兵 外加 64/1024×存兵 手续费 → 捐成的话存兵至少掉 pct/1024+6.25%；
#           下一条调度/快照里存兵没掉到这个数的一半 = 没捐成；门槛可用 --done-frac 改）
#   quota 每条调度日志按引擎 donationCost 公式要多少配额点 vs 当拍 donCap（受赠方已用配额只有下界）；要和 disp 一起跑
#   box   每号：nb=0 且 neut=0 的快照数（被围）、密度 >100 / >130 的快照数、最高密度、90 拍内存兵掉 ≥30% 的次数
#   cmds  每号每 600 拍下发的指令数（[HL-TICK] cmds 字段的增量）
#   lag   两盘开局的日志行号差：各号第一条 [HL-OPENING] 的行号与拍号
import csv, json, re, sys
from collections import defaultdict, Counter

a = sys.argv[1:]
MID = a[0]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
SEC = val('--sec', 'tl,sum,res,disp,quota,box,cmds,lag').split(',')
DONE_FRAC = float(val('--done-frac', 0.5))
DATA = '/agent/repos/c136-data/bundles/' + MID
card = json.load(open(DATA + '/card.json'))
LAND = card['mapLand']
ticks = defaultdict(list)   # bot -> [(t, terr, bal, dens, nb, neut, cmds, boats, line)]
disp = []                   # {line, bot, t, cat, pct, ally, allyName, boxed, myBal, dMe, dAlly}
me = {}
opening = defaultdict(list)
re_tick = re.compile(r'^(\d+)\s+\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)')
re_disp = re.compile(r'^(\d+)\s+\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(\w+) myBal=(\d+) dMe=(\d+) dAlly=(\d+)')
re_init = re.compile(r'^(\d+)\s+\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)')
re_open = re.compile(r'^(\d+)\s+\[([^\]]+)\] \[HL-OPENING\] t=(\d+)')
for ln in open(DATA + '/in_game.log', encoding='utf8', errors='replace'):
    m = re_tick.match(ln)
    if m:
        ticks[m.group(2)].append((int(m.group(3)), int(m.group(4)), int(m.group(5)), float(m.group(6)), int(m.group(7)), int(m.group(8)), int(m.group(9)), int(m.group(10)), int(m.group(1))))
        continue
    m = re_disp.match(ln)
    if m:
        disp.append(dict(line=int(m.group(1)), bot=m.group(2), t=int(m.group(3)), cat=m.group(4), pct=int(m.group(5)), ally=int(m.group(6)),
                         allyName=re.sub(r'\[[^\]]*\]\s*', '', m.group(7)).strip(), boxed=m.group(8) == 'true', myBal=int(m.group(9)), dMe=int(m.group(10)), dAlly=int(m.group(11))))
        continue
    m = re_init.match(ln)
    if m:
        me[m.group(2)] = int(m.group(3))
        continue
    m = re_open.match(ln)
    if m:
        opening[m.group(2)].append((int(m.group(1)), int(m.group(3))))

# 录像盘里的号：truth JSON 的 squad
inrep = set()
try:
    J = json.load(open(f'/tmp/c136-r05/truth/{MID}.json'))
    inrep = {s['bot'] for s in J['squad']}
except Exception:
    pass
bots_all = sorted(me, key=lambda b: me[b])
BOTS = [b for b in bots_all if ('--all' in a or b not in inrep)]
if '--bots' in a:
    BOTS = val('--bots', '').split(',')
AT = [int(x) for x in val('--at', '90,180,270,360,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600,3900,4200,4500').split(',')]
k = lambda v: f'{v / 1e6:.2f}M' if v >= 1e6 else (f'{v / 1e3:.0f}k' if v >= 1e4 else str(v))


def at(bot, t):
    r = None
    for row in ticks[bot]:
        if row[0] <= t:
            r = row
        else:
            break
    return r


print(f'# {MID} 只在日志里的我方号 {len(BOTS)} 个：{" ".join(f"{b}(me={me[b]})" for b in BOTS)}｜录像盘里的号：{" ".join(sorted(inrep)) or "无"}｜全图陆地 {LAND}')
res = {}
try:
    for r in csv.DictReader(open(DATA + '/results.csv', encoding='utf8')):
        res[r['bot']] = r
except Exception:
    pass

if 'tl' in SEC:
    print('== tl 每号 地/兵/密度/nb/neut（取 ≤ 该拍最近一条快照；最后一条快照之后留空）==')
    for b in BOTS:
        last = ticks[b][-1][0] if ticks[b] else -1
        parts = []
        for t in AT:
            if t > last + 89:
                break
            r = at(b, t)
            if r:
                parts.append(f'{t}: {r[1]}/{k(r[2])}/{r[3]:.0f}/nb{r[4]}/n{r[5]}')
        d = res.get(b)
        print(f'  {b}（最后快照 t={last}；{"阵亡 " + d["tick"] + " 峰值 " + d["peak"] if d else "无结果行"}）：' + ' | '.join(parts))

if 'sum' in SEC:
    print('== sum 这些号合计（每 300 拍；只算当时还有快照的号）==')
    for t in range(300, 99999, 300):
        rows = [(b, at(b, t)) for b in BOTS if ticks[b] and ticks[b][-1][0] >= t - 89]
        rows = [(b, r) for b, r in rows if r]
        if not rows:
            break
        terr = sum(r[1] for _, r in rows); bal = sum(r[2] for _, r in rows)
        big = max(rows, key=lambda x: x[1][1])
        bx = [r for _, r in rows if r[4] == 0 and r[5] == 0]
        print(f'  t={t}: {len(rows)} 号 地 {terr}（{100 * terr / LAND:.1f}%）兵 {k(bal)} 平均密度 {bal / max(1, terr):.0f}｜最大号 {big[0]} {big[1][1]}（{100 * big[1][1] / LAND:.1f}%）｜nb=0 且 neut=0 的号 {len(bx)}：地 {sum(r[1] for r in bx)} 兵 {k(sum(r[2] for r in bx))}（占这些号兵的 {100 * sum(r[2] for r in bx) / max(1, bal):.0f}%）')

if 'res' in SEC and res:
    print('== res results.csv（各号阵亡时各队总地；队 0 = 机器人）==')
    for b, r in sorted(res.items(), key=lambda x: int(x[1]['tick'])):
        tt = json.loads(r['teamTotals']) if r['teamTotals'] else {}
        tot = sum(tt.values()) or 1
        sh = ' '.join(f'T{kk}={v}({100 * v / LAND:.1f}%)' for kk, v in sorted(tt.items()))
        print(f'  {b}（me={r["meId"]}，队 {r["teamMine"]}）{r["event"]} t={r["tick"]} 名次 {r["place"]}/{int(r["alivePlayers"]) + 1} 峰值地 {r["peak"]} 末地 {r["lastTerritory"]} 存兵 {r["balance"]} 指令 发{r["sent"]}/成{r["accepted"]}｜{sh}｜{"录像盘" if b in inrep else "另一盘"}')

if 'disp' in SEC:
    print('== disp 调度日志（捐成与否：看捐出方下一条日志里的存兵）==')
    D = [d for d in disp if d['bot'] in BOTS]
    by = defaultdict(list)
    for d in D:
        by[d['bot']].append(d)
    tot = Counter(); amt = Counter()
    rows = []
    for b, L in by.items():
        L.sort(key=lambda d: d['line'])
        for i, d in enumerate(L):
            need = (d['pct'] + 1) / 1024 + 64 / 1024
            nxt = None
            if i + 1 < len(L) and L[i + 1]['t'] - d['t'] <= 120:
                nxt = (L[i + 1]['t'], L[i + 1]['myBal'], '调度')
            else:
                s = [r for r in ticks[b] if r[0] > d['t']]
                if s:
                    nxt = (s[0][0], s[0][2], '快照')
            if nxt is None:
                d['done'] = None
            else:
                drop = 1 - nxt[1] / max(1, d['myBal'])
                # 捐成：存兵掉了至少 need 的一半（期间还有利息进账；两类分得很开：没捐成的是 +0…+17%，捐成的是 −21…−42%）
                d['done'] = drop >= DONE_FRAC * need
                d['drop'] = drop; d['need'] = need; d['nxt'] = nxt
            key = '捐成' if d['done'] else ('没捐成' if d['done'] is False else '无后续')
            tot[key] += 1
            if d['done']:
                amt[(b, d['allyName'])] += int((d['pct'] + 1) / 1024 * d['myBal'])
            rows.append(d)
    print(f'  日志 {len(D)} 条：{dict(tot)}')
    c1 = Counter((d['bot'], d['allyName']) for d in D)
    done1 = Counter((d['bot'], d['allyName']) for d in D if d['done'])
    for (b, al), n in sorted(c1.items(), key=lambda x: -x[1]):
        L = [d for d in D if d['bot'] == b and d['allyName'] == al]
        print(f'  {b}→{al}: 日志 {n} 条（拍 {min(d["t"] for d in L)}–{max(d["t"] for d in L)}）捐成 {done1[(b, al)]} 条（按日志 pct×存兵估 {k(amt[(b, al)])}）｜类别 {dict(Counter(d["cat"] for d in L))}｜boxedIn {dict(Counter(d["boxed"] for d in L))}｜dMe {min(d["dMe"] for d in L)}–{max(d["dMe"] for d in L)} dAlly {min(d["dAlly"] for d in L)}–{max(d["dAlly"] for d in L)}｜pct {min(d["pct"] for d in L)}–{max(d["pct"] for d in L)}')
    for lo, hi in ((0, 2142), (2142, 3213), (3213, 4284), (4284, 99999)):
        L = [d for d in D if lo <= d['t'] < hi]
        if L:
            print(f'  拍 [{lo},{hi})：日志 {len(L)} 捐成 {sum(1 for d in L if d["done"])} 没捐成 {sum(1 for d in L if d["done"] is False)}｜类别 {dict(Counter(d["cat"] for d in L))}｜boxedIn {dict(Counter(d["boxed"] for d in L))}')
    if '--list' in a:
        for d in sorted(rows, key=lambda d: d['line']):
            nx = d.get('nxt')
            print(f'    t={d["t"]} {d["bot"]}→{d["allyName"]} {d["cat"]} pct={d["pct"]} boxed={d["boxed"]} myBal={k(d["myBal"])} dMe={d["dMe"]} dAlly={d["dAlly"]}｜下一条({nx[2]} t={nx[0]}) 存兵 {k(nx[1])} 变化 {-100 * d["drop"]:+.1f}%（捐成需 ≤ -{100 * DONE_FRAC * d["need"]:.0f}%）→ {"捐成" if d["done"] else "没捐成"}' if nx else f'    t={d["t"]} {d["bot"]}→{d["allyName"]} 无后续')

if 'quota' in SEC:
    # 引擎（sim/game.js）：donCap 开局 15，每逢 t%100==99 加 4（t<1071）/6（<2142）/8（<3213）/10；
    #   donationCost(q,v)：t<357 2+100v/uw；<714 /(4uw)；<1071 /(10uw)；<2142 /(30uw)；<3213 /(100uw)，uw=1+全图陆地//300；
    #   t≥3213：4+100v/(100×受赠方的地)；t≥4284 不限。受赠方已用配额 donQuota[q] 只增不减，放行条件 已用+本笔 ≤ donCap。
    #   这里受赠方已用配额只能给下界（= 本队我方号此前「捐成」的那些笔的点数之和；另一盘里的随机队友也可能捐过，看不到）。
    print('== quota 每条调度日志按引擎公式要多少配额点 vs 当拍配额上限（受赠方的地取 ≤ 该拍最近一条快照）==')
    UW = 1 + LAND // 300

    def cap_at(t):
        c = 15
        for tt in range(99, t, 100):   # 第 tt 拍末加，t 拍下单时已生效的是 tt < t 的那些
            c += 4 if tt < 1071 else 6 if tt < 2142 else 8 if tt < 3213 else 10
        return c

    def cost_of(t, v, qterr):
        if t >= 3213:
            return 4 + (100 * v) // max(100 * qterr, 1)
        div = UW if t < 357 else 4 * UW if t < 714 else 10 * UW if t < 1071 else 30 * UW if t < 2142 else 100 * UW
        return 2 + (100 * v) // div

    D = sorted([d for d in disp if d['bot'] in BOTS], key=lambda d: d['line'])
    if 'done' not in (D[0] if D else {}):
        print('  （需要同时带 disp 段：--sec disp,quota）')
    else:
        used = Counter()
        cls = Counter(); rows = []
        for d in D:
            B = d['myBal']; fee = (64 * B) // 1024
            v = min((B * (d['pct'] + 1)) // 1024, B - fee)
            q = at(d['allyName'], d['t']) if d['allyName'] in ticks else None
            room = (q[1] * 150 - q[2]) if q else None
            if room is not None:
                v = max(0, min(v, room))
            free = d['t'] >= 4284
            cost = 0 if free else cost_of(d['t'], v, q[1] if q else 1)
            cap = cap_at(d['t'])
            if free:
                c = '不限配额(t≥4284)'
            elif cost > cap:
                c = '单笔就超上限'
            elif used[d['allyName']] + cost > cap:
                c = '加上已用下界超上限'
            else:
                c = '按下界放得进'
            d['qcost'] = cost; d['qcap'] = cap; d['qused'] = used[d['allyName']]; d['qcls'] = c; d['v'] = v
            cls[(c, '捐成' if d['done'] else '没捐成' if d['done'] is False else '无后续')] += 1
            if d['done'] and not free:
                used[d['allyName']] += cost
            rows.append(d)
        print(f'  uw={UW}（t∈[1071,2142) 每点 {30 * UW / 100:.0f} 兵；[2142,3213) 每点 {UW} 兵；≥3213 每点 = 受赠方的地）；上限：t=2040 {cap_at(2040)}、2142 {cap_at(2142)}、3190 {cap_at(3190)}、3215 {cap_at(3215)}、4240 {cap_at(4240)}')
        for (c, dn), n in sorted(cls.items()):
            print(f'  {c} × {dn}: {n} 条')
        for lo, hi in ((0, 2142), (2142, 3213), (3213, 4284)):
            L = [d for d in rows if lo <= d['t'] < hi]
            if L:
                over = [d for d in L if d['qcls'] == '单笔就超上限']
                ratio = sorted(d['qcost'] / max(1, d['qcap']) for d in L)
                print(f'  拍 [{lo},{hi})：日志 {len(L)}｜单笔就超上限 {len(over)}（其中捐成 {sum(1 for d in over if d["done"])}）｜要的点数÷上限 中位 {ratio[len(ratio) // 2]:.2f} 最小 {ratio[0]:.2f} 最大 {ratio[-1]:.2f}｜捐成 {sum(1 for d in L if d["done"])}')
        for b in sorted({d['bot'] for d in rows}):
            L = [d for d in rows if d['bot'] == b]
            print(f'  {b}: 日志 {len(L)}｜单笔就超上限 {sum(1 for d in L if d["qcls"] == "单笔就超上限")}｜加上已用下界超 {sum(1 for d in L if d["qcls"] == "加上已用下界超上限")}｜放得进 {sum(1 for d in L if d["qcls"] == "按下界放得进")}（其中捐成 {sum(1 for d in L if d["qcls"] == "按下界放得进" and d["done"])}）｜不限 {sum(1 for d in L if d["qcls"].startswith("不限"))}')
        if '--list' in a:
            for d in rows:
                print(f'    t={d["t"]} {d["bot"]}→{d["allyName"]} pct={d["pct"]} 想捐 {k(d["v"])} → 要 {d["qcost"]} 点｜上限 {d["qcap"]}｜已用下界 {d["qused"]}｜{d["qcls"]}｜{"捐成" if d["done"] else "没捐成" if d["done"] is False else "无后续"}')

if 'box' in SEC:
    print('== box 每号：被围快照（nb=0 且 neut=0）、超密度、存兵骤降 ==')
    for b in BOTS:
        T = ticks[b]
        if not T:
            continue
        boxed = [r for r in T if r[4] == 0 and r[5] == 0]
        o100 = [r for r in T if r[3] > 100]; o130 = [r for r in T if r[3] > 130]
        mx = max(T, key=lambda r: r[3])
        drops = [(T[i][0], T[i - 1][2], T[i][2]) for i in range(1, len(T)) if T[i - 1][2] > 2000 and T[i][2] < 0.7 * T[i - 1][2]]
        runs = []
        for r in boxed:
            if runs and r[0] - runs[-1][1] <= 90:
                runs[-1][1] = r[0]
            else:
                runs.append([r[0], r[0]])
        print(f'  {b}: 快照 {len(T)}｜被围 {len(boxed)} 条（{", ".join(f"{x}–{y}" for x, y in runs) or "无"}）｜密度>100 {len(o100)} 条 >130 {len(o130)} 条｜最高密度 {mx[3]:.0f}@{mx[0]}（地 {mx[1]} 兵 {k(mx[2])}）｜存兵 90 拍掉 ≥30% {len(drops)} 次：{" ".join(f"{t}:{k(x)}→{k(y)}" for t, x, y in drops[:12])}')

if 'cmds' in SEC:
    print('== cmds 每号每 600 拍下发的指令数（cmds 字段增量）==')
    for b in BOTS:
        T = ticks[b]
        parts = []
        for lo in range(0, 99999, 600):
            A = [r for r in T if lo <= r[0] < lo + 600]
            if not A:
                if T and lo > T[-1][0]:
                    break
                continue
            prev = [r for r in T if r[0] < lo]
            base = prev[-1][6] if prev else 0
            parts.append(f'{lo}:{A[-1][6] - base}')
        print(f'  {b}: ' + ' '.join(parts) + f'｜合计 {T[-1][6] if T else 0}')

if 'lag' in SEC:
    print('== lag 各号第一条 [HL-OPENING]（行号｜拍）与第一条 [HL-TICK] ==')
    for b in bots_all:
        o = opening[b][0] if opening[b] else None
        t0 = ticks[b][0] if ticks[b] else None
        print(f'  {b}（{"录像盘" if b in inrep else "另一盘"}）: OPENING 行 {o[0] if o else "-"} t={o[1] if o else "-"}｜首条 TICK 行 {t0[8] if t0 else "-"} t={t0[0] if t0 else "-"}')
