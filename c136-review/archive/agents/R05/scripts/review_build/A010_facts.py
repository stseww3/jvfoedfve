#!/usr/bin/env python3
# A010_facts.py — A010 专用事实表（全部机械计数；只读 /tmp/c136-r05/truth/A010.json、work/A010-cmds.tsv、
#   bundles/A010 与 bundles/B009 的 in_game.log / results.csv / card.json）。
#   先跑：bash scripts/accounts_batch.sh A010（产出 truth 和 cmds.tsv）。
#   A 段：同拍批（同一个玩家同一拍落地 ≥3 条陆攻/出船）——20 名真人逐个数；我方 10 个号、同机房的 c110 号 Mali（B009 的 me=0）、其余 9 名真人分开列。
#   B 段：出生点——20 人的最终出生点与最后一条出生指令的拍；我方号到最近我方号 / 最近敌方真人的距离；阵心、阵半径、阵内的敌方真人；
#         人均地与「人均间距」（2×sqrt(人均地/π)）。
#   C 段：协调器 30 轮求解——每轮的 minSep、点集与指派；点集相同只是换人（置换）的轮数；逐号指派次数与来回跳的次数。
#   D 段：20 名真人逐个的地账与兵账（地从中立/机器人/真人各拿多少、各投多少兵、每格机器人地花的兵、利息地租合计、捐出/收到）。
#   E 段：全场捐兵（allDon）按队、按 捐出方→受赠方 汇总；每 600 拍的笔数与到账。
#   F 段：钟面时间——results.csv 的 (拍, 秒) 线性拟合；延迟波起止拍对应的 UTC；B009 里 Mali 的结果行；B009 其余 9 个结果行的 meId/事件/队数（它们在另一间房）。
#   G 段：1500 拍以后影子对真人的出手（work/A010-delay.json 的 decisions[]）：逐号 决策条数 / 落地条数 / 名义兵 / 实际打出。
#   H 段：阵内的敌人；I 段：前排号对相邻真人的报价。
#   J 段：逐号受击账（谁打它、几条、多少兵、首末拍、拿走几格；≥100k 的来袭条数），以及两次出手之后对面的回击。
#   K 段：调度与配额（dispatch[]：逐捐出方 日志/落地/到账/税；没落地的按「所需点数 > 总上限」「已用 + 所需 > 上限」分开数；逐受赠方列出每条日志的 已用/所需/上限）。
#   L 段：正文引用的零散数字（各号在指定拍的地/兵、被围期间的密度范围、600 拍全场地最大的人、出船条数、出生点之间的距离、最后一轮改派挪了多远）。
# 用法：python3 scripts/review_build/A010_facts.py [--sec A,B,C,D,E,F,G,H,I,J,K,L]
import csv, json, math, os, re, sys, collections, statistics as st
M = 'A010'
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
W = os.environ.get('C136_WORK', '/tmp/c136-r05/work')
T = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
sec = set((sys.argv[sys.argv.index('--sec') + 1] if '--sec' in sys.argv else 'A,B,C,D,E,F,G,H,I,J,K,L').split(','))
H = T['humans']
P = {p['id']: p for p in T['players']}
SQ = {s['p']: s['bot'] for s in T['squad']}
card = json.load(open(f'{DATA}/bundles/{M}/card.json'))
MW = int(re.search(r'\((\d+)x(\d+)\)', f"({T['map']['w']}x{T['map']['h']})" if isinstance(T.get('map'), dict) and 'w' in T['map'] else '(956x873)').group(1))
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
nm = lambda p: (SQ[p] if p in SQ else P[p]['name'])
dist = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
cmds = list(csv.DictReader(open(f'{W}/{M}-cmds.tsv', encoding='utf-8'), delimiter='\t'))

if 'A' in sec:
    print('== A 同拍批（同一玩家同一拍落地 ≥3 条陆攻/出船；录像命令流）==')
    per = collections.defaultdict(collections.Counter)
    for r in cmds:
        if r['kind'] in ('attack', 'boat'): per[int(r['player'])][int(r['tick'])] += 1
    grp = collections.defaultdict(list)
    for p in range(H):
        c = per[p]; n = sum(c.values()); b = {t: v for t, v in c.items() if v >= 3}
        kind = '我方号' if p in SQ else ('同机房 c110 号' if P[p]['name'] == 'Mali' else '其余真人')
        grp[kind].append((p, n, len(b), sum(b.values()), max(c.values()) if c else 0, b))
    for kind in ('我方号', '同机房 c110 号', '其余真人'):
        rows = grp[kind]
        print(f'   {kind}（{len(rows)} 人）：陆攻/出船 {sum(r[1] for r in rows)} 条，同拍批 {sum(r[2] for r in rows)} 个共 {sum(r[3] for r in rows)} 条；有批的 {sum(1 for r in rows if r[2])} 人；单拍最多 {max(r[4] for r in rows)} 条')
        for p, n, nb, nc, mx, b in rows:
            bins = collections.Counter((t // 600) * 600 for t in b)
            print(f'      {nm(p)}#{p}: {n} 条｜批 {nb} 个 {nc} 条（单拍最多 {mx}）' + (f"｜批所在拍 {' '.join(f'{t}×{v}' for t, v in sorted(b.items()))}｜按 600 拍 {dict(sorted(bins.items()))}" if b else ''))
    sqb = [t for r in grp['我方号'] for t in r[5]]
    print(f'   我方号的批：最早 {min(sqb)} 拍、最晚 {max(sqb)} 拍；Mali 的批：最早 {min(grp["同机房 c110 号"][0][5])} 拍、最晚 {max(grp["同机房 c110 号"][0][5])} 拍')

if 'B' in sec:
    print('== B 出生点 ==')
    last = {}
    for r in cmds:
        if r['kind'] == 'spawn': last[int(r['player'])] = int(r['tick'])
    nsp = collections.Counter(int(r['player']) for r in cmds if r['kind'] == 'spawn')
    land = card['mapLand']; per_head = land / H; rc = math.sqrt(per_head / math.pi)
    print(f'   陆地 {land} 格、真人 {H} 人：人均 {per_head:.0f} 格；rCell = sqrt(人均/π) = {rc:.1f}；人均间距 2×rCell = {2 * rc:.0f} 格')
    sp = {p: tuple(P[p]['spawn']) for p in range(H)}
    for p in range(H):
        o = sorted((dist(sp[p], sp[q]), q) for q in range(H) if q != p)
        mate = next(((d, q) for d, q in o if P[q]['team'] == P[p]['team']), None)
        foe = next(((d, q) for d, q in o if P[q]['team'] != P[p]['team']), None)
        print(f"   {nm(p)}#{p}（T{P[p]['team']}）出生 {sp[p]}，最后一条出生指令在 {last.get(p)} 拍（共 {nsp[p]} 条）｜最近同队 {nm(mate[1])} {mate[0]:.0f} 格｜最近敌方 {nm(foe[1])} {foe[0]:.0f} 格")
    sq = [sp[p] for p in SQ]
    cx = sum(x for x, _ in sq) / len(sq); cy = sum(y for _, y in sq) / len(sq)
    rad = max(dist((cx, cy), s) for s in sq)
    nn = [min(dist(sp[p], sp[q]) for q in SQ if q != p) for p in SQ]
    print(f'   我方阵心 ({cx:.0f},{cy:.0f})，最远的号离阵心 {rad:.0f} 格；我方号到最近我方号：中位 {st.median(nn):.0f}、最小 {min(nn):.0f}、最大 {max(nn):.0f} 格 = 人均间距的 {st.median(nn) / (2 * rc):.2f}')
    inside = sorted((dist((cx, cy), sp[p]), p) for p in range(H) if p not in SQ and dist((cx, cy), sp[p]) <= rad)
    print('   阵半径内的敌方真人：' + ('；'.join(f'{nm(p)}#{p} 离阵心 {d:.0f} 格（最后一条出生指令 {last.get(p)} 拍）' for d, p in inside) or '无'))
    foe_nn = [min(dist(sp[p], sp[q]) for q in range(H) if q not in SQ and q != p) for p in range(H) if p not in SQ]
    print(f'   敌方真人到最近敌方真人：中位 {st.median(foe_nn):.0f}、最小 {min(foe_nn):.0f}、最大 {max(foe_nn):.0f} 格')
    late = sorted((last[p], p) for p in range(H) if p not in SQ and last.get(p, -99) >= -5)
    print('   选点期最后 5 拍才定点的敌方真人：' + '；'.join(f'{nm(p)}#{p} {t} 拍 {sp[p]}' for t, p in late))
    print(f'   我方号最后一条出生指令的拍：' + '、'.join(f'{nm(p)} {last[p]}' for p in sorted(SQ, key=lambda p: last[p])))

if 'C' in sec:
    print('== C 协调器求解轮次（[BACKEND-SPAWN-COORD]）==')
    rounds = []
    for ln in open(f'{DATA}/bundles/{M}/in_game.log', encoding='utf-8', errors='replace'):
        if '[BACKEND-SPAWN-COORD]' not in ln: continue
        ms = int(re.search(r'minSep=(\d+)px', ln).group(1))
        el = float(re.search(r'in ([\d.]+)ms', ln).group(1))
        a = {b: (int(x), int(y)) for b, x, y in re.findall(r'\[APEX\] (\w+)\([A-Z_]+\)->\((\d+),(\d+)\)', ln)}
        rounds.append((ms, el, a))
    asg = [tuple(sorted(a.items())) for _, _, a in rounds]
    pts = [tuple(sorted(a.values())) for _, _, a in rounds]
    perm = sum(1 for i in range(1, len(rounds)) if pts[i] == pts[i - 1] and asg[i] != asg[i - 1])
    same = sum(1 for i in range(1, len(rounds)) if asg[i] == asg[i - 1])
    print(f'   求解 {len(rounds)} 轮：不同的指派 {len(set(asg))} 个、不同的点集 {len(set(pts))} 个；与上一轮点集相同只是换了人的 {perm} 轮；与上一轮完全相同的 {same} 轮；每轮耗时 中位 {st.median(r[1] for r in rounds):.0f} 毫秒、最大 {max(r[1] for r in rounds):.0f} 毫秒')
    print('   minSep 逐轮：' + ' '.join(str(r[0]) for r in rounds))
    for b in sorted(rounds[0][2]):
        seq = [a[b] for _, _, a in rounds]
        chg = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
        back = sum(1 for i in range(2, len(seq)) if seq[i] == seq[i - 2] and seq[i] != seq[i - 1])
        p = next(p for p, n in SQ.items() if n == b)
        print(f'      {b}: 不同的点 {len(set(seq))} 个，换点 {chg} 次，其中跳回上上轮那个点的 {back} 次；最后一轮 {seq[-1]}，实际出生 {tuple(P[p]["spawn"])}（差 {dist(seq[-1], P[p]["spawn"]):.0f} 格）；最后 6 轮 {seq[-6:]}')

if 'D' in sec:
    print('== D 20 名真人的地账与兵账（truth.players；flows 按 cats 顺序）==')
    cats = T['cats']; tot = {}
    for p in range(H):
        q = P[p]; f = dict(zip(cats, q['flows']))
        g = '编队' if p in SQ else 'T1'
        t = tot.setdefault(g, collections.Counter()); t['n'] += 1
        for kk in ('tilesN', 'tilesB', 'tilesH', 'sentN', 'sentB', 'sentH', 'tilesLost'): t[kk] += q[kk]
        for kk in ('eco', 'ret', 'dmg', 'donOut', 'donIn'): t[kk] += f[kk]
        print(f"   {nm(p)}#{p}（{g}）峰值 {q['peakTerr']}@{q['peakT']}｜拿地 中立 {q['tilesN']} / 机器人 {q['tilesB']} / 真人 {q['tilesH']}，被拿走 {q['tilesLost']}｜投兵 中立 {k(q['sentN'])} / 机器人 {k(q['sentB'])} / 真人 {k(q['sentH'])}｜每格机器人地 {q['sentB'] / max(1, q['tilesB']):.1f} 兵｜利息地租 {k(f['eco'])}，退回 {k(f['ret'])}，被打掉 {k(-f['dmg'])}，捐出 {k(-f['donOut'])}，收到 {k(f['donIn'])}")
    for g, t in tot.items():
        print(f"   {g} 合计（{t['n']} 人）：拿地 中立 {t['tilesN']} / 机器人 {t['tilesB']} / 真人 {t['tilesH']}｜投兵 中立 {k(t['sentN'])} / 机器人 {k(t['sentB'])} / 真人 {k(t['sentH'])}｜每格 中立 {t['sentN'] / t['tilesN']:.1f} / 机器人 {t['sentB'] / t['tilesB']:.1f} / 真人 {t['sentH'] / max(1, t['tilesH']):.1f} 兵｜利息地租 {k(t['eco'])}｜捐出 {k(-t['donOut'])} 收到 {k(t['donIn'])}")
    a, b = tot['编队'], tot['T1']
    print(f"   编队 ÷ T1：利息地租 {a['eco'] / b['eco']:.2f}；机器人地 {a['tilesB'] / b['tilesB']:.2f}；中立地 {a['tilesN'] / b['tilesN']:.2f}；从真人手里拿的地 {a['tilesH'] / b['tilesH']:.2f}；投向真人的兵 {a['sentH'] / b['sentH']:.2f}")

if 'E' in sec:
    print('== E 全场捐兵（allDon：[拍, 捐出方, 受赠方, 到账, 税]）==')
    by = collections.defaultdict(lambda: [0, 0, 0, 10 ** 9, -1])
    team = collections.defaultdict(lambda: [0, 0, 0]); win = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for t, a, b, v, fee in T['allDon']:
        r = by[(a, b)]; r[0] += 1; r[1] += v; r[2] += fee; r[3] = min(r[3], t); r[4] = max(r[4], t)
        g = '编队' if a in SQ else 'T1'
        team[g][0] += 1; team[g][1] += v; team[g][2] += fee
        w = win[g][(t // 600) * 600]; w[0] += 1; w[1] += v
    for g, (n, v, fee) in team.items():
        print(f'   {g}：{n} 笔，到账 {k(v)}，税 {k(fee)}（税÷到账 {100 * fee / v:.1f}%）｜按 600 拍 ' + '；'.join(f'{t}: {x[0]} 笔 {k(x[1])}' for t, x in sorted(win[g].items())))
    for (a, b), (n, v, fee, t0, t1) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f'      {nm(a)}#{a} → {nm(b)}#{b}: {n} 笔 到账 {k(v)} 税 {k(fee)}（{t0}–{t1} 拍）')
    t1 = team['T1']; sqd = team['编队']
    print(f'   T1 到账 ÷ 编队到账 = {t1[1] / sqd[1]:.1f}')
    don = collections.defaultdict(lambda: [0, 0, 0])
    for t, a, b, v, fee in T['allDon']:
        don[a][0] += 1; don[a][1] += v; don[a][2] += fee
    print('   按捐出方：' + '；'.join(f'{nm(a)}#{a} {n} 笔 到账 {k(v)} 税 {k(fee)}' for a, (n, v, fee) in sorted(don.items(), key=lambda x: -x[1][1])))
    END = card['outcome']['endTick']
    pre = [d for d in T['allDon'] if d[1] not in SQ and d[0] <= END]
    print(f'   T1 在编队最后一个号阵亡（{END} 拍）之前：{len(pre)} 笔，到账 {k(sum(d[3] for d in pre))}，税 {k(sum(d[4] for d in pre))}；其中 Player 600 捐出 {sum(1 for d in pre if d[1] == 3)} 笔 到账 {k(sum(d[3] for d in pre if d[1] == 3))}')
    ml = [d for d in T['allDon'] if d[1] == 0]
    print('   Mali（同机房的 c110 号，在 T1）的捐兵：' + '；'.join(f'{d[0]} 拍 → {nm(d[2])} 到账 {k(d[3])} 税 {k(d[4])}' for d in ml) + f'｜{END} 拍之前 {sum(1 for d in ml if d[0] <= END)} 笔 到账 {k(sum(d[3] for d in ml if d[0] <= END))}')
    re_hits = [e for e in T['events'] if e['type'] == 'attack' and e['p'] == 12 and e.get('q') in SQ and e.get('ok')]
    by_t = collections.Counter()
    for e in re_hits: by_t[SQ[e['q']]] += e['troops']
    print(f"   受赠方 Russian Empire 全程打我方号 {len(re_hits)} 条 {k(sum(e['troops'] for e in re_hits))}：" + '、'.join(f'{b} {k(v)}' for b, v in by_t.most_common()) + f"；其中 3332 拍（Mali 第一笔）以后 {k(sum(e['troops'] for e in re_hits if e['t'] >= 3332))}")

if 'F' in sec:
    print('== F 钟面时间（results.csv 的 拍/秒 线性拟合）==')
    import datetime as dt
    def fit(path, events):
        pts = [(int(r['tick']), float(r['seconds'])) for r in csv.DictReader(open(path, encoding='utf-8')) if r['event'] in events]
        n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
        b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
        return my - b * mx, b, n
    a0, b0, n = fit(f'{DATA}/bundles/{M}/results.csv', ('died', 'end'))
    t0 = dt.datetime.fromisoformat(card['timeUtc'].replace('Z', '+00:00'))
    print(f'   A010 开始 {card["timeUtc"]}；{n} 个阵亡行拟合：秒 = {a0:.1f} + {b0 * 1000:.1f} 毫秒 × 拍')
    for tk in (600, 900, 1500, 2100, 4036):
        print(f'      {tk} 拍 ≈ 开始后 {a0 + b0 * tk:.0f} 秒 = {(t0 + dt.timedelta(seconds=a0 + b0 * tk)).strftime("%H:%M:%S")} UTC')
    cb = json.load(open(f'{DATA}/bundles/B009/card.json'))
    print(f"   B009（{cb['cohort']}）开始 {cb['timeUtc']}，同图同种子：mapId {cb['mapId']} / mapSeed {cb['mapSeed']} / mapLand {cb['mapLand']} / mode {cb['mode']} / 真人 {cb['seededPlayers']}；A010：mapId {card['mapId']} / mapSeed {card['mapSeed']} / mapLand {card['mapLand']} / mode {card['mode']} / 真人 {card['seededPlayers']}")
    for r in csv.DictReader(open(f'{DATA}/bundles/B009/results.csv', encoding='utf-8')):
        if r['meId'] == '0':
            print(f"   B009 结果行 meId=0：{r['bot']} event={r['event']} result={r['result']} tick={r['tick']} 地 {r['territory']} 兵 {r['balance']} teamTotals={r['teamTotals']}（at {r['at'][11:23]}）")
    for ln in open(f'{DATA}/bundles/B009/in_game.log', encoding='utf-8', errors='replace'):
        if 'HL-GAME-INIT' in ln and 'me=0' in ln: print('   B009 日志：' + ln.split('\t', 1)[-1].strip())
    m0 = P[0]
    print(f"   A010 录像里的 #0：{m0['name']}（T{m0['team']}）出生 {tuple(m0['spawn'])}，终局 {m0['endTerr']} 格 / {m0['endBal']} 兵；捐出 {m0['donOutN']} 笔 到账 {m0['donOutV']} 税 {m0['donOutFee']}")
    # B009 其余号在不在这间房：它们的 meId 在 A010 录像里是谁、结果行的 teamTotals 有几个队
    rest = [r for r in csv.DictReader(open(f'{DATA}/bundles/B009/results.csv', encoding='utf-8')) if r['meId'] != '0']
    ev = collections.Counter(f"{r['event']}/{r['result']}" for r in rest)
    nteam = sorted({len([k_ for k_ in json.loads(r['teamTotals']) if k_ != '0']) for r in rest if r['teamTotals']})
    print(f"   B009 其余 {len(rest)} 个结果行：meId {sorted(int(r['meId']) for r in rest)}；事件 {dict(ev)}；拍 {min(int(r['tick']) for r in rest)}–{max(int(r['tick']) for r in rest)}；teamTotals 里的队数 {nteam}；left 行的记录时刻 {min(r['at'][11:23] for r in rest if r['event'] == 'left')}–{max(r['at'][11:23] for r in rest if r['event'] == 'left')}")
    print('   这些 meId 在 A010 录像里是：' + '、'.join(f"#{int(r['meId'])} {P[int(r['meId'])]['name']}" for r in sorted(rest, key=lambda r: int(r['meId']))) + '（A010 录像 4601 拍结束、只有 2 个队）→ B009 其余号在另一间房')

if 'G' in sec:
    print('== G 1500 拍以后影子对真人的出手 对 录像里落地的（work/A010-delay.json）==')
    # decisions[] 每条 = [号, 决策拍, 类型, 目标类别(N/B/H/S/D), 状态(hit/dead/void/lost), 落地拍, 延迟, 决策拍名义兵, 实际打出, 退回]
    D = json.load(open(f'{W}/{M}-delay.json'))
    rows = [d for d in D['decisions'] if d[2] == 'attack' and d[3] == 'H']
    for lo, hi in ((1500, 2100), (2100, 10 ** 9)):
        print(f'   -- 决策拍 {lo}–{hi if hi < 10 ** 9 else "终局"} --')
        tot = collections.Counter()
        for b in SQ.values():
            r = [d for d in rows if d[0] == b and lo <= d[1] < hi]
            if not r: continue
            ld = [d for d in r if d[4] != 'lost']
            tot['n'] += len(r); tot['ld'] += len(ld); tot['nom'] += sum(d[7] for d in r); tot['out'] += sum(d[8] for d in ld)
            first = min(d[1] for d in r); fl = min((d[5] for d in ld), default=None)
            print(f"      {b}: 想打真人 {len(r)} 条（名义 {k(sum(d[7] for d in r))}），落地 {len(ld)} 条（实际打出 {k(sum(d[8] for d in ld))}）｜第一条决策 {first} 拍，第一条落地 " + (f'{fl} 拍（晚 {fl - first} 拍）' if fl is not None else '无') + (f"｜落地的延迟 中位 {st.median(d[6] for d in ld):.0f}、最大 {max(d[6] for d in ld)}" if ld else ''))
        if tot['n']: print(f"      合计：想打真人 {tot['n']} 条（名义 {k(tot['nom'])}），落地 {tot['ld']} 条（{100 * tot['ld'] / tot['n']:.0f}%；实际打出 {k(tot['out'])}）")

if 'H' in sec:
    print('== H 阵内的敌人 [OG]😎#16：600–1500 拍它的地/兵，与围着它的四个我方号（work/A010-nb.txt = shadow.mjs --nb 605,905,1205,1405）==')
    cur = None; hdr = {}; og = collections.defaultdict(dict)
    for ln in open(f'{W}/{M}-nb.txt', encoding='utf-8', errors='replace'):
        m = re.match(r'-- 邻居报价 (\w+) t=(\d+) 地 (\d+) 兵 (\d+)', ln)
        if m: cur = (m.group(1), int(m.group(2))); hdr[cur] = (int(m.group(3)), int(m.group(4))); continue
        m = re.match(r'\s+\[OG\]😎#16 地 (\d+) 兵 (\d+) 密度 ([\d.]+) 接触 (\d+)｜每格价 ([\d.]+).*?吃掉需 (-?\d+)｜留底 (\d+)（winFloor (\d+)）→ (.*)', ln)
        if m and cur: og[cur[1]][cur[0]] = dict(terr=int(m.group(1)), bal=int(m.group(2)), touch=int(m.group(4)), need=int(m.group(6)), floor=int(m.group(7)), why=m.group(9).strip())
    for t in sorted(og):
        any_ = next(iter(og[t].values()))
        bots = sorted(og[t])
        sm = sum(hdr[(b, t)][1] for b in bots)
        print(f"   t={t}: [OG]😎 {any_['terr']} 格 / {any_['bal']} 兵；吃掉需 {any_['need']}｜贴着它的我方号 {len(bots)} 个：" + '、'.join(f"{b} {hdr[(b, t)][1]} 兵（接触 {og[t][b]['touch']} 格，留底 {og[t][b]['floor']}）" for b in bots) + f"｜这几个号的兵合计 {sm} = 吃掉所需的 {sm / any_['need']:.2f} 倍、它存兵的 {sm / any_['bal']:.1f} 倍")
    HS = T['HS']
    print('   [OG]😎 每 300 拍 地/兵（HS）：' + '；'.join(f"{t}: {HS['terr'][i][16]}/{k(HS['bal'][i][16])}" for i, t in enumerate(HS['t']) if t <= 2400))
    ev = [e for e in T['events'] if e['type'] == 'attack' and e.get('q') == 16 and e['p'] in SQ and e.get('ok')]
    print(f"   我方号第一次打它：{min(e['t'] for e in ev)} 拍；全程 {len(ev)} 条 {k(sum(e['troops'] for e in ev))}")
    lost = collections.Counter()
    for w, to, frm, n in T['pairAll']:
        if to == 16 and frm in SQ: lost[SQ[frm]] += n
    print('   它从我方号手里拿走的地（pairAll 全程）：' + '、'.join(f'{b} {n}' for b, n in lost.most_common()) + f'；合计 {sum(lost.values())}')

if 'I' in sec:
    print('== I 1535/1700/1900 拍前排号对相邻真人的报价（work/A010-offers.txt = shadow.mjs --cold --offers 1535,1700,1900）==')
    cur = None
    for ln in open(f'{W}/{M}-offers.txt', encoding='utf-8', errors='replace'):
        m = re.match(r'-- 报价 (\w+) t=(\d+) 地 (\d+) 兵 (\d+) 密度 ([\d.]+)', ln)
        if m: cur = m.groups(); continue
        m = re.match(r'\s+(.+?)#(\d+) 地 (\d+) 兵 (\d+) 密度 ([\d.]+) 接触 (\d+)｜每格价 c=([\d.]+).*?吃掉需 (\d+)（([\d.]+)×存兵）.*?｜真人', ln)
        if m and cur:
            av = re.search(r'可用 (-?\d+)', ln)
            print(f"   t={cur[1]} {cur[0]}（{cur[2]} 格/{k(int(cur[3]))}，密度 {cur[4]}）→ {m.group(1)}#{m.group(2)}（{m.group(3)} 格/{k(int(m.group(4)))}，密度 {m.group(5)}，接触 {m.group(6)} 格）：每格价 {m.group(7)}，吃掉需 {k(int(m.group(8)))} = 自己存兵的 {m.group(9)} 倍" + (f"，可用 {k(int(av.group(1)))}（存兵的 {100 * int(av.group(1)) / int(cur[3]):.0f}%）" if av else '，价格门收口'))

EV = T['events']
BOT = {n: p for p, n in SQ.items()}

if 'J' in sec:
    print('== J 逐号受击账（录像里已执行的陆攻；拿走的格数取 pairs）==')
    tiles = {(r['a'], r['b']): r['tiles'] for r in T['pairs']}
    order = sorted(SQ, key=lambda p: P[p]['deathT'])
    for b in order:
        hits = collections.defaultdict(list)
        for e in EV:
            if e['type'] == 'attack' and e.get('q') == b and e.get('ok') and e['p'] < H and e['p'] not in SQ: hits[e['p']].append(e)
        parts = []
        for a, es in sorted(hits.items(), key=lambda x: -sum(e['troops'] for e in x[1])):
            big = [e for e in es if e['troops'] >= 100e3]
            parts.append(f"{nm(a)}#{a} {len(es)} 条 {k(sum(e['troops'] for e in es))}（{es[0]['t']}–{es[-1]['t']} 拍；≥100k 的 {len(big)} 条" + (f"，{k(min(e['troops'] for e in big))}–{k(max(e['troops'] for e in big))}" if big else '') + f"；拿走 {tiles.get((a, b), 0)} 格）")
        bl = [e for e in EV if e['type'] == 'boat-land' and e.get('q') == b and e['p'] < H and e['p'] not in SQ]
        if bl: parts.append('船登陆：' + '、'.join(f"{e['t']} 拍 {nm(e['p'])} {k(e['troops'])}" for e in bl))
        print(f"   {nm(b)}（阵亡 {P[b]['deathT']}）：" + '；'.join(parts))
    three = [BOT[x] for x in ('leo_tx', 'zero_7', 'ryan_m')]
    es = [e for e in EV if e['type'] == 'attack' and e['p'] == 13 and e.get('q') in three and e.get('ok')]
    print(f"   Pizza Calzone 打 leo_tx、zero_7、ryan_m（三个清仓后的号）：{len(es)} 条 {k(sum(e['troops'] for e in es))}，拿走 {sum(tiles.get((13, b), 0) for b in three)} 格（每格 {sum(e['troops'] for e in es) / max(1, sum(tiles.get((13, b), 0) for b in three)):.0f} 兵）")
    def after(att, t0, t1):
        es = [e for e in EV if e['type'] == 'attack' and e['p'] == att and e.get('q') in SQ and e.get('ok') and t0 < e['t'] <= t1]
        c = collections.Counter(); n = collections.Counter()
        for e in es: c[SQ[e['q']]] += e['troops']; n[SQ[e['q']]] += 1
        return f"{len(es)} 条 {k(sum(e['troops'] for e in es))}（" + '、'.join(f'{x} {n[x]} 条 {k(v)}' for x, v in c.most_common()) + '）'
    print(f"   zexos1 1939 拍那一批之后 300 拍，[OG]😎 对我方号的陆攻：{after(16, 1939, 2239)}")
    print(f"   leo_tx 2079 拍那一批之后 300 拍，Pizza Calzone 对我方号的陆攻：{after(13, 2079, 2379)}")
    print(f"   kaito9 3507–3514 拍出手之后 300 拍，Player 642 对我方号的陆攻：{after(18, 3514, 3814)}")
    for b, q, t0, t1 in (('kaito9', 18, 3507, 3514), ('riku_x', 18, 3528, 3591), ('zero_7', 19, 1757, 1827), ('sora_w', 14, 2422, 3318)):
        es = [e for e in EV if e['type'] == 'attack' and e['p'] == BOT[b] and e.get('q') == q and e.get('ok') and t0 <= e['t'] <= t1]
        rounds = []
        for e in es:
            if rounds and e['t'] - rounds[-1][-1] <= 21: rounds[-1].append(e['t'])
            else: rounds.append([e['t']])
        print(f"   {b} → {nm(q)} {t0}–{t1} 拍 {len(es)} 条 {k(sum(e['troops'] for e in es))}：目标在第一条时 {es[0]['tL']} 格/{k(es[0]['tB'])}、最后一条时 {es[-1]['tL']} 格/{k(es[-1]['tB'])}；单条占当时存兵 {100 * min(e['troops'] / e['B0'] for e in es):.0f}%–{100 * max(e['troops'] / e['B0'] for e in es):.0f}%；按间隔 ≤21 拍归成 {len(rounds)} 轮，每轮条数 {[len(r) for r in rounds]}")

if 'K' in sec:
    print('== K 调度与配额（truth.dispatch：[HL-DISPATCH] 日志 + 按日志拍 +0/7/14/21 的试算）==')
    D = T['dispatch']
    for donor in sorted({d['bot'] for d in D}):
        ds = [d for d in D if d['bot'] == donor]; ex = [d for d in ds if d.get('exec')]
        no = [d for d in ds if not d.get('exec')]
        over = [d for d in no if d['sim'][0].get('extra') and d['sim'][0]['extra']['cost'] > d['sim'][0]['extra']['cap']]
        allq = [d for d in no if all(s['reason'] == 'quota' for s in d['sim'])]
        print(f"   {donor}: 日志 {len(ds)} 条，落地 {len(ex)} 条（到账 {k(sum(d['exec']['got'] for d in ex))}，税 {k(sum(d['exec']['fee'] for d in ex))}）；没落地 {len(no)} 条，其中四个试算拍都被配额拒的 {len(allq)} 条、所需点数 > 受赠方总上限的 {len(over)} 条")
    no = [d for d in D if not d.get('exec')]
    print(f"   合计：日志 {len(D)} 条，落地 {sum(1 for d in D if d.get('exec'))} 条；没落地 {len(no)} 条里所需点数 > 受赠方总上限的 {sum(1 for d in no if d['sim'][0].get('extra') and d['sim'][0]['extra']['cost'] > d['sim'][0]['extra']['cap'])} 条")
    byq = collections.defaultdict(list)
    for d in D: byq[d['qName'].replace('[APEX] ', '')].append(d)
    for q, ds in byq.items():
        row = []
        for d in ds:
            x = d['sim'][0].get('extra')
            row.append(f"{d['t']}{'✓' if d.get('exec') else '✗'}" + (f"(已用{x['used']}+需{x['cost']}>上限{x['cap']})" if x else '') + (f"[到账{k(d['exec']['got'])}]" if d.get('exec') else ''))
        print(f"   → {q}（{len(ds)} 条，落地 {sum(1 for d in ds if d.get('exec'))}）：" + ' '.join(row))
    for e in EV:
        if e['type'] == 'donate': print(f"   落地 t={e['t']} {nm(e['p'])}→{nm(e['q'])} 到账 {k(e['got'])} 税 {k(e['fee'])}｜受赠方配额 用后 {e['quotaAfter']} / 上限 {e['cap']}｜受赠方当时 {e['qL0']} 格/{k(e['qB0'])}（密度 {e['qB0'] / max(1, e['qL0']):.0f}）｜捐出方 {e['L0']} 格/{k(e['B0'])}（密度 {e['B0'] / max(1, e['L0']):.0f}）")

if 'L' in sec:
    print('== L 正文引用的零散数字 ==')
    def s10(b, t):
        s = T['S10'][str(BOT[b])]; i = min(range(len(s['t'])), key=lambda i: abs(s['t'][i] - t))
        return s['t'][i], s['terr'][i], s['bal'][i]
    for b, ts in (('ryan_m', (900, 1200, 1500, 1900, 2040)), ('leo_tx', (900, 1200, 1500, 1800, 2070)), ('zero_7', (1200, 1500, 1750, 1820, 1960)), ('zexos1', (900, 1200, 1500, 1930)),
                  ('riku_x', (900, 1200, 1500, 1800, 2400, 3000)), ('sora_w', (900, 1200, 1500, 2400, 3000)), ('noah88', (1500, 1930, 2400, 2500, 3000)), ('talon5', (1500, 2400, 2660)), ('alex_k', (1200, 1500, 2600)), ('kaito9', (1500, 1800, 1890))):
        print(f"   {b}: " + '；'.join('t={} {} 格/{}（密度 {:.0f}）'.format(tt, L, k(B), B / max(1, L)) for tt, L, B in (s10(b, t) for t in ts)))
    for b, t0, t1 in (('kaito9', 1890, 3360), ('riku_x', 2280, 3480)):
        s = T['S10'][str(BOT[b])]; idx = [i for i, t in enumerate(s['t']) if t0 <= t <= t1]
        dens = [s['bal'][i] / max(1, s['terr'][i]) for i in idx]; im = max(idx, key=lambda i: s['bal'][i])
        print(f"   {b} {t0}–{t1} 拍：地 {min(s['terr'][i] for i in idx)}–{max(s['terr'][i] for i in idx)} 格，存兵 {k(min(s['bal'][i] for i in idx))}–{k(max(s['bal'][i] for i in idx))}（最高在 {s['t'][im]} 拍），密度 {min(dens):.0f}–{max(dens):.0f}")
    for b, wins in (('kaito9', ((1890, 3360),)), ('riku_x', ((2280, 2850), (3030, 3480)))):
        c = T['C30'][str(BOT[b])]
        for t0, t1 in wins:
            idx = [i for i, t in enumerate(c['t']) if t0 <= t <= t1]
            other = max(c['eh'][i] + c['el'][i] + c['bot'][i] + c['neut'][i] + c['mateO'][i] for i in idx)
            print(f"   {b} {t0}–{t1} 拍（{len(idx)} 个采样点）：边界上我方号 {min(c['mateS'][i] for i in idx)}–{max(c['mateS'][i] for i in idx)} 格，敌方真人/机器人/中立/路人合计最多 {other} 格，敌邻个数最多 {max(c['nEnemy'][i] for i in idx)}")
    hs = T['HS']
    for t in (600, 900, 1500):
        i = hs['t'].index(t); terr = hs['terr'][i]
        rk = sorted(range(H), key=lambda p: -terr[p])
        print(f"   t={t} 地最大的 4 人：" + '、'.join(f'{nm(p)} {terr[p]}' for p in rk[:4]) + '｜我方号名次：' + ' '.join(f'{nm(p)} {rk.index(p) + 1}' for p in sorted(SQ, key=lambda p: rk.index(p))))
    boats = [e for e in EV if e['type'] == 'boat' and e['p'] in SQ]
    print(f"   我方出船 {len(boats)} 条：" + '；'.join(f"{e['t']} 拍 {nm(e['p'])} {k(e['troops'])}（手续费 {k(e['fee'])}）" for e in boats) + f"｜全场出船指令 {T['stats']['boatOk']} 条")
    sp = {p: tuple(P[p]['spawn']) for p in range(H)}
    for a in (13, 16, 15, 19, 14, 12, 18):
        o = sorted((dist(sp[a], sp[q]), q) for q in SQ)
        print(f"   {nm(a)}#{a} 出生 {sp[a]}：最近的我方号 " + '、'.join(f'{nm(q)} {d:.0f} 格' for d, q in o[:3]))
    rounds = []
    for ln in open(f'{DATA}/bundles/{M}/in_game.log', encoding='utf-8', errors='replace'):
        if '[BACKEND-SPAWN-COORD]' not in ln: continue
        rounds.append({b: (int(x), int(y)) for b, x, y in re.findall(r'\[APEX\] (\w+)\([A-Z_]+\)->\((\d+),(\d+)\)', ln)})
    mv = sorted(((dist(rounds[-2][b], rounds[-1][b]), b) for b in rounds[-1]), reverse=True)
    print('   最后一轮相对上一轮各号挪了多远：' + '、'.join(f'{b} {d:.0f} 格' for d, b in mv))
    c0 = [sum(v[i] for v in rounds[-2].values()) / len(rounds[-2]) for i in (0, 1)]; c1 = [sum(v[i] for v in rounds[-1].values()) / len(rounds[-1]) for i in (0, 1)]
    print(f'   阵心：倒数第二轮 ({c0[0]:.0f},{c0[1]:.0f}) → 最后一轮 ({c1[0]:.0f},{c1[1]:.0f})，挪了 {dist(c0, c1):.0f} 格；到 [OG]😎 出生点的距离 {dist(c0, sp[16]):.0f} → {dist(c1, sp[16]):.0f} 格')
    nsq = sum(1 for r in cmds if r['kind'] == 'spawn' and int(r['player']) in SQ); nall = sum(1 for r in cmds if r['kind'] == 'spawn')
    print(f'   出生指令：我方 10 个号 {nsq} 条，其余 {H - len(SQ)} 名真人 {nall - nsq} 条')
    f = f'{W}/{M}-shadowspawn.txt'
    if os.path.exists(f):
        seen = set(); row = []
        for ln in open(f, encoding='utf-8'):
            m = re.match(r't=(-?\d+) 已落点的其他真人 (\d+).*?"rCell":(\d+).*?质心 \((\d+),(\d+)\).*?角尖 \((\d+),(\d+)\)', ln)
            if not m: continue
            t, n, rc, cx, cy, ax, ay = map(int, m.groups())
            if (cx, cy, ax, ay) in seen: continue
            seen.add((cx, cy, ax, ay))
            row.append(f't={t}（已落子的其他真人 {n}，rCell {rc}）角尖 ({ax},{ay}) 阵心 ({cx},{cy})，阵心相对角尖 ({cx - ax:+d},{cy - ay:+d})，阵心到 [OG]😎 {dist((cx, cy), sp[16]):.0f} 格')
        print('   协调器重放（shadow_spawn.mjs）里阵的朝向：' + '；'.join(row))
