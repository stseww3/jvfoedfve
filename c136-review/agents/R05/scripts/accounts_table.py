#!/usr/bin/env python3
"""accounts_table.py — 把已复盘各局的三本账（广播 0007：延迟硬账 / 好地账 / 600–1500 拍三层归因）和配额闸账并成跨局表（Markdown）。

数据来源：reviews/<局>.json 的 delayAccount / landAccount / tickAttribution / quotaGuard 四个字段
          （由 delay_account.py、land_account.mjs、tick_attrib.py、quota_guard.py 的输出原样裁剪进去，见 review_build/common.py 的 accounts()）；
          out/unlock-diff.json（unlock_diff.py --json 的产物，有就并进配额闸表）；out/rules-header.json（rules_header.mjs 的产物，有就并进去）。
本脚本不做任何新的计量，只排表、求中位。

口径（与各脚本头注一致）：
  延迟 = 指令在录像里的执行拍 − 影子策略做出同一条决策的拍（同样的指令重复发时取最晚的那条决策，所以是下界）；基线 = 0–600 拍的中位。
  「延迟波局」= 600–1500 拍落地指令的延迟中位 ≥ 60 拍。
  漏斗按决策拍分段：想发（影子，过闸后）→ 落地（录像里执行了）→ 按原意（落地时目标还活着、接壤）。
  名下份额 = 每格陆地归离它最近的真人出生点；实际地 ÷ 名下份额 = 该拍实际占地 ÷ 名下格数。
  三层归因：600–1500 拍每个（号 × 决策拍）归一类；① 结构 = 只贴敌方真人 + 被围；② 留底 = 留底锁（有/无在途）；③ 发了没用 = 目标已死 + 不接壤 + 没落地。

用法：python3 scripts/accounts_table.py [局…] [--out reports/DELAY-AND-LAND-ACCOUNT.md]
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
a = sys.argv[1:]
outp = a[a.index('--out') + 1] if '--out' in a else None
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--out')]
if not ids:
    ids = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'reviews')) if f.endswith('.json'))
J = {m: json.load(open(os.path.join(ROOT, 'reviews', f'{m}.json'))) for m in ids}


def opt_json(name):
    p = os.path.join(ROOT, 'out', name)
    return json.load(open(p)) if os.path.exists(p) else {}


UNL, RULES = opt_json('unlock-diff.json'), opt_json('rules-header.json')
num = lambda v: '–' if v is None else (f'{v:g}' if isinstance(v, float) and v != int(v) else f'{int(v):,}')
pct = lambda x, y, d=0: f'{100 * x / y:.{d}f}%' if y else '–'
med = lambda v: statistics.median(v) if v else None
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v / 1e3:.1f}k' if abs(v) >= 1e3 else f'{v:.0f}')
PER = ['0–600', '600–1500', '1500–3000', '3000+']
out = []
P = out.append


def by_period(rows):
    return {r['period']: r for r in rows or []}


def D(m):
    return J[m].get('delayAccount') or {}


def is_lag(m):
    r = by_period(D(m).get('delayByPeriod')).get('600–1500') or {}
    return (r.get('p50') or 0) >= 60


def outcome(m):
    r = J[m].get('result') or J[m].get('outcome') or {}
    if isinstance(r, dict):
        return r.get('label') or r.get('resultLabel') or ('赢' if r.get('won') else '输')
    return str(r)


def table(head, rows, align=None):
    P('| ' + ' | '.join(head) + ' |')
    P('|' + '|'.join((' :-- ' if (align and align[i] == 'l') else ' --: ') for i in range(len(head))) + '|')
    for r in rows:
        P('| ' + ' | '.join(str(x) for x in r) + ' |')
    P('')


LAG = [m for m in ids if is_lag(m)]
OK = [m for m in ids if not is_lag(m)]
P('# 13 局三本账跨局表（延迟硬账 / 好地账 / 600–1500 拍三层归因 / 配额闸）')
P('')
P('> 本文件由 `python3 scripts/accounts_table.py --out reports/DELAY-AND-LAND-ACCOUNT.md` 生成，不手改。数字全部来自各局 `reviews/<局>.json` 里的账本字段，')
P('> 账本字段由 `delay_account.py`、`land_account.mjs`、`tick_attrib.py`、`quota_guard.py` 的输出原样裁剪而来（重跑方法见各局复盘第 7 节末尾）。')
P('> 「延迟波局」= 600–1500 拍落地指令的延迟中位 ≥ 60 拍：' + '、'.join(LAG) + f'（{len(LAG)} 局）；其余 {len(OK)} 局：' + '、'.join(OK) + '。')
P('> A017、A043 是拆盘局，账本只覆盖有录像那一盘的 1 个、2 个号。B010 是 squad20（c110）。')
P('')

# ---------- 表 1 出生执行 ----------
P('## 1. 出生执行：协调器给的最终坐标有没有变成出生点')
P('')
rows = []
for m in ids:
    sp = D(m).get('spawnExecution') or {}
    v = sp.get('verdicts') or {}
    bots = sp.get('bots') or []
    dist = sorted(b['distActualToFinal'] for b in bots if b.get('verdict') == '停在旧坐标' and b.get('distActualToFinal') is not None)
    rnd = sum(c for kk, c in v.items() if kk.startswith('0 条落地'))
    off = sum(c for kk, c in v.items() if kk.startswith('日志外'))
    V = (J[m].get('landAccount') or {}).get('voronoi') or {}
    rows.append([m, len(bots), num(sp.get('solveRounds')), num(sp.get('distinctSolutions')), v.get('最终坐标落地', 0), v.get('停在旧坐标', 0),
                 (num(round(med(dist))) if dist else '–'), rnd, off, sp.get('stackPairs', 0), num(round(sp.get('nearestAllyMedian') or 0)) if len(bots) > 1 else '–',
                 f"{V.get('ratio', 0):.2f}" if V else '–'])
table(['局', '录像里的号', '求解轮数', '不同的解', '最终坐标落地', '停在旧坐标', '旧坐标离最终坐标（中位，格）', '0 条落地（引擎随机落子）', '日志外坐标', '同像素堆叠（对）', '到最近我方号（中位，格）', '名下份额÷人数份额'], rows)
tot = [sum(r[i] for r in rows) for i in (1, 4, 5, 7, 8)]
P(f'合计 {tot[0]} 个号：最终坐标落地 {tot[1]} 个（{pct(tot[1], tot[0])}）、停在旧坐标 {tot[2]} 个（{pct(tot[2], tot[0])}）、0 条落地 {tot[3]} 个、日志外坐标 {tot[4]} 个。')
P('')

# ---------- 表 2 指令延迟 ----------
P('## 2. 指令延迟（执行拍 − 影子决策拍；每格 = 落地条数 P50/P90/最大）')
P('')
rows = []
for m in ids:
    bp = by_period(D(m).get('delayByPeriod'))
    r = [m + ('＊' if m in LAG else ''), num(D(m).get('baselineTicks'))]
    for p in PER:
        x = bp.get(p)
        r.append(f"{x['landed']} 条 {num(x['p50'])}/{num(x['p90'])}/{num(x['max'])}" if x and x.get('matched') else ('–' if not x or not x['landed'] else f"{x['landed']} 条（无配对）"))
    x = bp.get('600–1500') or {}
    r.append(pct(x.get('ge90', 0), x.get('matched', 0)))
    x = bp.get('1500–3000') or {}
    r.append(pct(x.get('ge90', 0), x.get('matched', 0)))
    rows.append(r)
table(['局（＊延迟波局）', '基线（拍）'] + [p + ' 拍' for p in PER] + ['600–1500 拍 ≥90 拍的占比', '1500–3000 拍 ≥90 拍的占比'], rows)
for name, G in (('延迟波局', LAG), ('其余局', OK)):
    for p in ('600–1500', '1500–3000'):
        xs = [by_period(D(m).get('delayByPeriod')).get(p) for m in G]
        xs = [x for x in xs if x and x.get('matched')]
        if xs:
            P(f"- {name} {p} 拍：P50 的中位 {num(med([x['p50'] for x in xs]))} 拍（{num(min(x['p50'] for x in xs))}–{num(max(x['p50'] for x in xs))}），P90 的中位 {num(med([x['p90'] for x in xs]))} 拍，最大 {num(max(x['max'] for x in xs))} 拍。")
P('')

# ---------- 表 3 漏斗 ----------
P('## 3. 漏斗：影子想发 → 录像里落地 → 按原意落地（按决策拍分段）')
P('')
rows = []
for m in ids:
    F = by_period(D(m).get('funnel'))
    r = [m + ('＊' if m in LAG else '')]
    for p in ('600–1500', '1500–3000'):
        x = F.get(p)
        if not x or not x['intended']:
            r += ['–', '–', '–', '–']
            continue
        r += [f"{x['intended']:,} → {x['landed']:,} → {x['asIntended']:,}", pct(x['asIntended'], x['intended']),
              f"{x['deadToNeutral'] + x['deadVoid']}（改打中立 {x['deadToNeutral']}、作废 {x['deadVoid']}）＋不接壤 {x['void']}", f"{x['neverLanded']:,}（{pct(x['neverLanded'], x['intended'])}）"]
    ft = D(m).get('funnelTotals') or {}
    r += [f"{ft['intended']:,} / {ft['executed']:,}" if ft else '–', f"{ft['neverLandedByCount']:,}（{pct(ft['neverLandedByCount'], ft['intended'])}）" if ft else '–']
    rows.append(r)
table(['局', '600–1500 拍：想发 → 落地 → 按原意', '按原意占想发', '到达时目标已死＋不接壤', '没落地', '1500–3000 拍：想发 → 落地 → 按原意', '按原意占想发', '到达时目标已死＋不接壤', '没落地',
       '全程陆攻/出船：想发 / 录像执行', '全程没落地（按条数差）'], rows)
for name, G in (('延迟波局', LAG), ('其余局', OK)):
    xs = [by_period(D(m).get('funnel')).get('600–1500') for m in G]
    xs = [x for x in xs if x and x['intended']]
    if xs:
        P(f"- {name} 600–1500 拍合计：想发 {sum(x['intended'] for x in xs):,} 条 → 落地 {sum(x['landed'] for x in xs):,}（{pct(sum(x['landed'] for x in xs), sum(x['intended'] for x in xs))}）→ 按原意 "
          f"{sum(x['asIntended'] for x in xs):,}（{pct(sum(x['asIntended'] for x in xs), sum(x['intended'] for x in xs))}）；没落地 {sum(x['neverLanded'] for x in xs):,}（{pct(sum(x['neverLanded'] for x in xs), sum(x['intended'] for x in xs))}）。"
          f"各局「按原意占想发」的中位 {num(round(med([100 * x['asIntended'] / x['intended'] for x in xs])))}%。")
P('')

# ---------- 表 4 直接损失 ----------
P('## 4. 两类直接损失（600–1500 拍）')
P('')
P('(a) 迟到作废：打机器人的指令到达时目标已经死了（引擎把目标改成中立，或不接壤作废）。(b) 在途重复：决策下在上一条同目标指令的在途期间；同拍批：一个号一拍落地 ≥3 条。')
P('')
rows = []
for m in ids:
    LV = by_period(D(m).get('lateVoid')).get('600–1500') or {}
    B = LV.get('B') or {}
    IR = by_period(D(m).get('inflightRepeats')).get('600–1500') or {}
    BT = by_period(D(m).get('batches'))
    b1, b2 = BT.get('600–1500') or {}, BT.get('1500–3000') or {}
    dead = B.get('rewrittenOk', 0) + B.get('rewrittenVoid', 0)
    rows.append([m + ('＊' if m in LAG else ''), B.get('landed', 0), f"{dead}（{pct(dead, B.get('landed', 0))}）", num(B.get('staleRewrittenP50')), B.get('rewrittenVoid', 0),
                 f"{B.get('rewrittenOk', 0)} 条 {k(B.get('rewrittenOut', 0))}＋费 {k(B.get('rewrittenFee', 0))}", f"{k(B.get('hitOut', 0))} → {num(B.get('hitTiles', 0))} 格",
                 f"{IR.get('repeatDecisions', 0)}/{IR.get('attackDecisions', 0)}（{pct(IR.get('repeatDecisions', 0), IR.get('attackDecisions', 0))}）",
                 f"{k(IR.get('repeatOut', 0))}（{pct(IR.get('repeatOut', 0), IR.get('allOut', 0))}）",
                 f"{b1.get('batches', 0)} 批 {b1.get('cmds', 0)} 条（{pct(b1.get('cmds', 0), b1.get('landedAll', 0))}）", b1.get('allVoidBatches', 0), b1.get('drain50', 0),
                 f"{b2.get('batches', 0)} 批 {b2.get('cmds', 0)} 条（{pct(b2.get('cmds', 0), b2.get('landedAll', 0))}）"])
table(['局', '落地的打机器人指令', '到达时目标已死', '这些指令的延迟中位（拍）', '其中作废', '其中改打中立（打出兵＋手续费）', '命中的：打出兵 → 拿地', '陆攻决策里的在途重复', '落地的重复打出的兵（占打出兵数）',
       '同拍批（占落地指令）', '整批作废（批）', '一拍打掉一半以上存兵（批）', '1500–3000 拍同拍批'], rows)
for name, G in (('延迟波局', LAG), ('其余局', OK)):
    Bs = [(by_period(D(m).get('lateVoid')).get('600–1500') or {}).get('B') or {} for m in G]
    ld, dd = sum(b.get('landed', 0) for b in Bs), sum(b.get('rewrittenOk', 0) + b.get('rewrittenVoid', 0) for b in Bs)
    bt = [by_period(D(m).get('batches')).get('600–1500') or {} for m in G]
    P(f"- {name}合计：落地的打机器人指令 {ld:,} 条里到达时目标已死 {dd:,} 条（{pct(dd, ld)}）；同拍批 {sum(b.get('batches', 0) for b in bt)} 批 {sum(b.get('cmds', 0) for b in bt):,} 条，"
      f"占这些局 600–1500 拍落地指令的 {pct(sum(b.get('cmds', 0) for b in bt), sum(b.get('landedAll', 0) for b in bt))}；整批作废 {sum(b.get('allVoidBatches', 0) for b in bt)} 批。")
P('')

# ---------- 表 5 好地账 ----------
P('## 5. 好地账：名下份额、实际拿到多少、机器人地归了谁')
P('')
rows = []
for m in ids:
    L = J[m].get('landAccount') or {}
    V = L.get('voronoi') or {}
    cap = {c['t']: c for c in L.get('capture') or []}
    r = [m + ('＊' if m in LAG else ''), f"{100 * V.get('landShare', 0):.1f}%", f"{100 * V.get('headShare', 0):.1f}%", f"{V.get('ratio', 0):.2f}"]
    for t in (630, 1500):
        c = cap.get(t) or {}
        g = (c.get('groups') or {}).get('我方号') or {}
        r += [f"{g.get('ratio', 0):.2f}", f"{c.get('othersMedianRatio', 0):.2f}"]
    bl = L.get('botLand') or {}
    fate = bl.get('fate') or {}
    for key in ('A', 'B'):
        rr = (fate.get(key) or [None])[-1]
        tot = (bl.get(key) or {}).get('tiles')
        if rr and tot:
            mine = rr.get('我方号', 0)
            enemy = rr.get('敌方真人', 0)
            still = rr.get('机器人', 0) + rr.get('同队机器人', 0)
            r += [f"{tot:,}", pct(mine, tot), pct(enemy, tot), pct(still, tot)]
        else:
            r += ['–', '–', '–', '–']
    rr = (fate.get('C') or [None])[-1]
    tot = (bl.get('C') or {}).get('tiles')
    r.append(pct(rr.get('我方号', 0), tot, 1) if rr and tot else '–')
    rows.append(r)
table(['局', '名下份额（全图）', '人数占比', '名下÷人数', '630 拍 实际÷名下：编队', '其余真人中位', '1500 拍 实际÷名下：编队', '其余真人中位',
       '名下的机器人地（格）', '到 1800 拍我方拿到', '敌方真人拿到', '仍是机器人', '贴着我方、可打的机器人地（格）', '我方拿到', '敌方真人拿到', '仍是机器人', '全图机器人地我方拿到'], rows)
for name, G in (('延迟波局', LAG), ('其余局', OK)):
    r630, r1500, o1500 = [], [], []
    for m in G:
        cap = {c['t']: c for c in (J[m].get('landAccount') or {}).get('capture') or []}
        if 630 in cap and 1500 in cap:
            r630.append(cap[630]['groups']['我方号']['ratio'])
            r1500.append(cap[1500]['groups']['我方号']['ratio'])
            o1500.append(cap[1500].get('othersMedianRatio', 0))
    if r630:
        P(f"- {name}：编队 实际÷名下 630 拍中位 {med(r630):.2f} → 1500 拍中位 {med(r1500):.2f}；同局其余真人 1500 拍中位的中位 {med(o1500):.2f}；1500 拍编队低于其余真人中位的局 {sum(1 for x, y in zip(r1500, o1500) if x < y)}/{len(r1500)}。")
bs = []
for m in ids:
    L = J[m].get('landAccount') or {}
    bl = L.get('botLand') or {}
    rr = ((bl.get('fate') or {}).get('C') or [None])[-1]
    tot = (bl.get('C') or {}).get('tiles')
    hs = (L.get('voronoi') or {}).get('headShare')
    if rr and tot and hs:
        bs.append((m, rr.get('我方号', 0) / tot / hs))
if bs:
    P(f"- 全图机器人地（600 拍时机器人占着的地，到 1800 拍的去向）我方拿到的份额 ÷ 人数占比：中位 {med([x for _, x in bs]):.2f}（{min(x for _, x in bs):.2f}–{max(x for _, x in bs):.2f}），<1 的 {sum(1 for _, x in bs if x < 1)}/{len(bs)} 局；"
      + '、'.join(f'{m} {x:.2f}' for m, x in bs) + '。')
P('')
P('把 1500 拍的落后拆成两个因子：**出生份额** = 名下÷人数（出生点分到的陆地是不是与人数相称）；**相对拿地** = 编队的 实际÷名下 ÷ 同局其余真人的中位（分到的地拿到手的程度，与别人比）。两者的乘积近似等于编队人均地 ÷ 其余真人人均地（`cross_ledger.py` 第 7 节按席位平均的实测值列在最后一列对照）。')
P('')
rows = []
fac = {'延迟波局': [], '其余局': []}
try:
    CL = {r['mid']: r for r in json.load(open(os.path.join(HERE, '..', 'out', 'cross-ledger.json'), encoding='utf-8'))}
except OSError:
    CL = {}
for m in ids:
    L = J[m].get('landAccount') or {}
    V = L.get('voronoi') or {}
    cap = {c['t']: c for c in L.get('capture') or []}
    c = cap.get(1500) or {}
    g = (c.get('groups') or {}).get('我方号') or {}
    if not V.get('ratio') or not g.get('ratio') or not c.get('othersMedianRatio'):
        continue
    rel = g['ratio'] / c['othersMedianRatio']
    pcap = ((CL.get(m) or {}).get('perCapita') or {}).get('1500') or {}
    fac['延迟波局' if m in LAG else '其余局'].append((V['ratio'], rel))
    rows.append([m + ('＊' if m in LAG else ''), f"{V['ratio']:.2f}", f"{rel:.2f}", f"{V['ratio'] * rel:.2f}", f"{pcap['ratio']:.2f}" if pcap.get('ratio') else '–'])
table(['局', '出生份额（名下÷人数）', '相对拿地（1500 拍）', '乘积', '实测：编队人均地÷其余真人人均地（1500 拍）'], rows)
for name in ('延迟波局', '其余局'):
    v = fac[name]
    if v:
        P(f"- {name}（{len(v)} 局）：出生份额中位 {med([x for x, _ in v]):.2f}（<1 的 {sum(1 for x, _ in v if x < 1)}/{len(v)}）；相对拿地中位 {med([y for _, y in v]):.2f}（<1 的 {sum(1 for _, y in v if y < 1)}/{len(v)}）。")
allv = fac['延迟波局'] + fac['其余局']
if allv:
    P(f"- 13 局合并：出生份额中位 {med([x for x, _ in allv]):.2f}（{min(x for x, _ in allv):.2f}–{max(x for x, _ in allv):.2f}，<1 的 {sum(1 for x, _ in allv if x < 1)}/{len(allv)}）。")
P('')

# ---------- 表 6 三层归因 ----------
P('## 6. 600–1500 拍决策拍的三层归因（每个 号×决策拍 归一类，百分比 = 占全部决策拍）')
P('')
rows = []
LY = {}
for m in ids:
    A = J[m].get('tickAttribution') or {}
    R = A.get('rows') or 0
    if not R:
        continue
    c, ly = A.get('cats') or {}, A.get('layers') or {}
    ns = (A.get('notSentSplit') or {}).get('split') or {}
    LY[m] = {kk: 100 * v / R for kk, v in ly.items()}
    rows.append([m + ('＊' if m in LAG else ''), f'{R:,}', pct(ly.get('①结构', 0), R, 1), pct(c.get('只贴敌方真人', 0), R, 1), pct(c.get('围在里面', 0), R, 1),
                 pct(ly.get('②留底', 0), R, 1), pct(c.get('留底锁·无在途', 0), R, 1), pct(c.get('留底·有在途', 0), R, 1),
                 pct(ly.get('③执行', 0), R, 1), pct(c.get('迟到·目标已死', 0), R, 1), pct(c.get('迟到·不接壤', 0), R, 1), pct(c.get('没落地', 0), R, 1),
                 pct(ly.get('有效', 0), R, 1), pct(ly.get('其余', 0), R, 1),
                 '、'.join(f"{kk} {pct(ns[kk], R, 1)}" for kk in ('冷却空过', '在途已够', '配额闸拒发') if ns.get(kk)) or '–', pct(c.get('只剩中立边', 0), R, 1)])
table(['局', '决策拍', '① 结构', '只贴敌方真人', '被围住', '② 留底', '纯锁（无在途）', '上一条还在路上', '③ 发了没用', '目标已死', '不接壤', '没落地', '有效', '其余', '其余里：有目标没发的拆分', '其余里：只剩中立边'], rows)
for name, G in (('延迟波局', LAG), ('其余局', OK)):
    G = [m for m in G if m in LY]
    if G:
        P(f"- {name}（{len(G)} 局）各层占比的中位：① 结构 {med([LY[m].get('①结构', 0) for m in G]):.1f}%、② 留底 {med([LY[m].get('②留底', 0) for m in G]):.1f}%、"
          f"③ 发了没用 {med([LY[m].get('③执行', 0) for m in G]):.1f}%、有效 {med([LY[m].get('有效', 0) for m in G]):.1f}%。")
P('')

# ---------- 表 7 配额闸 ----------
P('## 7. 配额闸与 isNoFullSend 置位（影子策略复算）')
P('')
P('isNoFullSend 在 `Policy.updateShadowQuota`（Va/Vb L3800–3836，c110 L3810–3846）里由「发令后 1–7 拍内余额掉得比预期少」推断，置位后不复位；')
P('置位后 `Policy.send` 的配额闸（Va/Vb L3844，c110 L3854）才会拒发。引擎真实规则见「引擎禁全兵」列（`rules_header.mjs`：录像头 battleRoyaleMode → game.js L58）。')
P('')
rows = []
for m in ids:
    Q = J[m].get('quotaGuard') or {}
    if not Q:
        rows.append([m, '–'] + ['–'] * 9)
        continue
    nf = Q.get('nfsAt') or {}
    flagged = sorted(t for t in nf.values() if t is not None and t >= 0)
    bp = by_period(Q.get('byPeriod'))
    u = UNL.get(m) or {}
    late = next((r for r in u.get('byPeriod', []) if r['period'] == '5000+'), None)
    rh = RULES.get(m) or {}
    rows.append([m + ('＊' if m in LAG else ''), Q.get('ver', '–'), ('是' if rh.get('engineNoFullSend') else '否') if rh else '–', f"{len(flagged)}/{len(nf)}",
                 (f"{flagged[0]}–{flagged[-1]}" if flagged else '–'), f"{Q.get('calls', 0):,}", f"{Q.get('refused', 0)}（{pct(Q.get('refused', 0), Q.get('calls', 0), 1)}）",
                 '；'.join(f"{p} {bp[p].get('refused', 0)}/{bp[p].get('calls', 0)}" for p in PER if p in bp and bp[p].get('calls')),
                 (f"{u['asPlayed']:,} / {u['unlocked']:,}" if u else '–'), (f"{100 * u['changedShare']:.1f}%" if u else '–'),
                 (f"锁着才发 {late['onlyLocked']}、锁挡掉 {late['onlyUnlocked']}（原样 {late['asPlayed']}）" if late and (late['asPlayed'] or late['unlocked']) else '–')])
table(['局', '版本', '引擎禁全兵', '被置位的号', '置位拍', 'Policy.send 调用', '配额闸拒发', '各时段 拒发/调用', '影子指令数：原样 / 不锁', '两边有差别的指令占比', '5000 拍后的差别'], rows)

txt = '\n'.join(out) + '\n'
if outp:
    open(os.path.join(ROOT, outp) if not os.path.isabs(outp) else outp, 'w', encoding='utf-8').write(txt)
    print('→', outp, txt.count('\n'), '行')
else:
    sys.stdout.write(txt)
