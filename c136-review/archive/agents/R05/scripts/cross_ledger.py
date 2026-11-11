#!/usr/bin/env python3
"""cross_ledger.py — 13 局统一口径的「兵与地」跨局账（全部从 match_truth.mjs 的真值 JSON 机械算出，不读日志、不读复盘 JSON）。

输入：/tmp/c136-r05/truth/<局>.json（没有就先跑：bash ../../tools/run-heavy.sh node scripts/match_truth.mjs <局>）
      /agent/repos/c136-data/bundles/<局>/card.json（只取 winnerTeam / ourPrimaryTeam）
输出：--out 写 Markdown（默认 reports/CROSS-LEDGER.md），--json 写同一批数字。

口径（每张表的表头下面还会再写一遍）：
  编队 = 录像这一盘里的我方号（truth.squad）；其余真人 = 同一盘里不是我方号的真人席位（含路人队友、含后来离场的）。
  分段：0–600 / 600–1500 / 1500–3000 / 3000–4284 / 4284–终局；收支累计每 30 拍采样一次，窗口对齐到 30 拍栅格。
  收支科目（truth.cats）：eco 利息+地租；atkNeutral/atkBot/atkHuman 打中立/机器人/真人时从存兵里扣走的兵（含手续费）；boat 出船（含船费）；
      donOut 捐出（含 6.25% 税）；donIn 收到；ret 进攻兵退回；dmg 被打掉的存兵；boatLand 船靠岸回到存兵；capLoss 超过 100×地 后少拿的利息（不是支出，单列）。
  「机器人」按引擎口径：内置 AI + 已离场的真人（game.js isBot）。
  打真人指令 = truth.events 里 type=attack、目标席位 < 真人数、ok 的；B0/L0 = 执行前一刻我方号的存兵/地，tB/tL = 目标的存兵/地。
      放行（over）= B0 > 100×L0（buyLand L5352–5359：此时跳过价格门）；一轮 = 同一个号对同一个目标、相邻两条间隔 ≤ 21 拍。
  捐兵 = truth.allDon（已执行）里捐出方是我方号的；来回 = 同一对号 300 拍内反方向也有一笔；
      受赠方之后 300 拍的地：取 S10（每 10 拍）在 [t, t+300] 的最小值/最大值 ÷ 到账那一拍的地。

用法：python3 scripts/cross_ledger.py [局…] [--out reports/CROSS-LEDGER.md] [--json out/cross-ledger.json]
"""
import bisect
import json
import os
import statistics as st
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
ALL = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']
a = sys.argv[1:]
val = lambda k, d: (a[a.index(k) + 1] if k in a else d)
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--out', '--json'))] or ALL
OUT = val('--out', os.path.join(HERE, '..', 'reports', 'CROSS-LEDGER.md'))
JOUT = val('--json', os.path.join(HERE, '..', 'out', 'cross-ledger.json'))
PH = [(0, 600), (600, 1500), (1500, 3000), (3000, 4284), (4284, 10 ** 6)]
PHN = ['0–600', '600–1500', '1500–3000', '3000–4284', '4284–终局']
VER = lambda m: 'c110' if m[0] == 'B' else ('Va' if int(m[1:]) <= 17 else 'Vb')


def k(x):
    if x is None:
        return '–'
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else (f'{x/1000:.0f}k' if abs(x) >= 1000 else f'{x:.0f}')


def pc(x, y, d=0):
    return '–' if not y else f'{100*x/y:.{d}f}%'


def load(mid):
    J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
    card = json.load(open(f'{SRC}/bundles/{mid}/card.json'))
    return J, card


def one(mid):
    J, card = load(mid)
    H, END = J['humans'], J['endTick']
    P = {p['id']: p for p in J['players']}
    sq = {s['p']: s['bot'] for s in J['squad']}
    CATS = J['cats']
    C = {c: i for i, c in enumerate(CATS)}
    F, S = J['F30'], J['S10']
    ad, ev = J['allDon'], J['events']
    R = {'mid': mid, 'ver': VER(mid), 'humans': H, 'squadN': len(sq), 'endTick': END, 'result': card['outcome']['resultLabel']}

    def cumflow(p, t):
        f = F[str(p)]
        i = bisect.bisect_right(f['t'], t) - 1
        return (f['flows'][i], f['capLoss'][i]) if i >= 0 else ([0] * len(CATS), 0)

    def s10(p, t):
        s = S.get(str(p))
        if s is None:
            return (0, 0)
        if 0 <= P[p]['deathT'] <= t:
            return (0, 0)
        i = bisect.bisect_right(s['t'], t) - 1
        return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)

    # ---- A. 分段收支 ----
    ph = []
    for (lo, hi), name in zip(PH, PHN):
        hi2 = min(hi, END)
        if hi2 <= lo:
            ph.append(None)
            continue
        lo_, hi_ = lo - lo % 30, hi2 - hi2 % 30
        acc = [0] * len(CATS)
        cl = 0
        for p in sq:
            (f0, c0), (f1, c1) = cumflow(p, lo_), cumflow(p, hi_)
            for i in range(len(CATS)):
                acc[i] += f1[i] - f0[i]
            cl += c1 - c0
        tax = sum(x[4] for x in ad if x[1] in sq and lo_ < x[0] <= hi_)
        don_sq = sum(x[3] for x in ad if x[1] in sq and x[2] in sq and lo_ < x[0] <= hi_)
        don_out_other = sum(x[3] for x in ad if x[1] in sq and x[2] not in sq and lo_ < x[0] <= hi_)
        don_in_other = sum(x[3] for x in ad if x[1] not in sq and x[2] in sq and lo_ < x[0] <= hi_)
        b0 = sum(s10(p, lo_)[1] for p in sq) if lo_ else 0
        b1 = sum(s10(p, hi_)[1] for p in sq)
        l0 = sum(s10(p, lo_)[0] for p in sq) if lo_ else 0
        l1 = sum(s10(p, hi_)[0] for p in sq)
        ph.append({'name': name, 'lo': lo_, 'hi': hi_, 'eco': acc[C['eco']], 'atkNeutral': -acc[C['atkNeutral']], 'atkBot': -acc[C['atkBot']],
                   'atkHuman': -acc[C['atkHuman']], 'boat': -acc[C['boat']], 'boatLand': acc[C['boatLand']], 'ret': acc[C['ret']], 'dmg': -acc[C['dmg']],
                   'tax': tax, 'donWithinSquad': don_sq, 'donToOthers': don_out_other, 'donFromOthers': don_in_other, 'capLoss': cl,
                   'bal0': b0, 'bal1': b1, 'land0': l0, 'land1': l1})
    R['phases'] = ph

    # ---- B. 打真人：放行口、目标强弱、连发 ----
    atk = [e for e in ev if e['type'] == 'attack' and e['p'] in sq and e.get('q') is not None and 0 <= e['q'] < H and e.get('ok', True)]
    sp = lambda e: e.get('troops', 0) + e.get('fee', 0)

    def hum(lo, hi):
        es = [e for e in atk if lo <= e['t'] < hi]
        tot = sum(sp(e) for e in es)
        ov = [e for e in es if e['B0'] > 100 * e['L0']]
        ge1 = [e for e in es if e.get('tB', 0) >= e['B0']]
        ge2 = [e for e in es if e.get('tB', 0) >= 2 * e['B0']]
        left = [e for e in es if P[e['q']]['leftT'] >= 0 and P[e['q']]['leftT'] <= e['t']]
        # 连发：按 (号, 目标) 归轮
        seq = defaultdict(list)
        for e in es:
            seq[(e['p'], e['q'])].append(e)
        vol = []
        for es2 in seq.values():
            es2.sort(key=lambda e: e['t'])
            cur = [es2[0]]
            for e in es2[1:]:
                if e['t'] - cur[-1]['t'] <= 21:
                    cur.append(e)
                else:
                    vol.append(cur)
                    cur = [e]
            vol.append(cur)
        v3 = [v for v in vol if len(v) >= 3]
        first = sum(sp(v[0]) for v in vol)
        frac = [sum(sp(e) for e in v) / v[0]['B0'] for v in vol if v[0]['B0'] > 0]
        frac1 = [sp(v[0]) / v[0]['B0'] for v in vol if v[0]['B0'] > 0]
        ovv = [v for v in vol if v[0]['B0'] > 100 * v[0]['L0']]
        return {'n': len(es), 'sent': tot, 'overN': len(ov), 'overSent': sum(sp(e) for e in ov), 'tgtGE1N': len(ge1), 'tgtGE1Sent': sum(sp(e) for e in ge1),
                'overVolleys': len(ovv), 'overVolleySent': sum(sp(e) for v in ovv for e in v),
                'volleyLenMedian': st.median([len(v) for v in vol]) if vol else None,
                'tgtGE2N': len(ge2), 'tgtGE2Sent': sum(sp(e) for e in ge2), 'leftTargetN': len(left), 'leftTargetSent': sum(sp(e) for e in left),
                'volleys': len(vol), 'volleysGE3': len(v3), 'volleysGE3Sent': sum(sp(e) for v in v3 for e in v), 'firstSent': first,
                'volleyFracMedian': round(st.median(frac), 3) if frac else None, 'firstFracMedian': round(st.median(frac1), 3) if frac1 else None}
    R['humanAtk'] = {'all': hum(0, 10 ** 6), '1500-4284': hum(1500, 4284), '4284+': hum(4284, 10 ** 6)}

    # ---- C. 地的来源、打人的价：编队 vs 其余真人 ----
    def grp(ps):
        n = len(ps)
        r = {'n': n}
        for key in ('tilesN', 'tilesB', 'tilesH', 'tilesLost', 'sentN', 'sentB', 'sentH'):
            r[key] = sum(p[key] for p in ps)
        fl = [sum(p['flows'][i] for p in ps) for i in range(len(CATS))]
        r['flows'] = dict(zip(CATS, fl))
        r['peakMedian'] = st.median([p['peakTerr'] for p in ps]) if ps else 0
        return r
    sqp = [P[p] for p in sq]
    oth = [p for p in J['players'] if p['id'] not in sq]
    wt = card['outcome'].get('winnerTeam')
    same_num = card.get('ourPrimaryTeam') == J.get('ourTeam')
    win = [p for p in oth if same_num and wt and p['team'] == wt]
    R['groups'] = {'squad': grp(sqp), 'others': grp(oth), 'winnerTeamOthers': grp(win) if win else None, 'teamNumberingAgrees': same_num, 'winnerTeam': wt, 'ourTeam': J.get('ourTeam')}

    # ---- D. 捐兵 ----
    mine = [x for x in ad if x[1] in sq]
    dv = {(e['t'], e['p'], e['q']): e for e in ev if e['type'] == 'donate' and e['p'] in sq and e.get('ok', True)}
    by_pair = defaultdict(list)
    for x in ad:
        by_pair[(x[1], x[2])].append(x[0])
    wins = []
    # 我方队占到全图陆地 90% 的第一拍（T30）：之后的捐兵是没有对手时的倒手，单列
    T = J['T30']
    t90 = next((t for t, l in zip(T['t'], T['land']) if J.get('ourTeam') and l[J['ourTeam']] >= 0.9 * J['map']['land']), None)
    R['t90'] = t90
    spans = [(0, 3213), (3213, 4284), (4284, t90 or 10 ** 6)] + ([(t90, 10 ** 6)] if t90 else [])
    names = ['<3213', '3213–4284', '≥4284' + ('（到我方队占 90% 之前）' if t90 else '')] + ([f'{t90} 拍起（我方队已占 90%）'] if t90 else [])
    for (lo, hi), name in zip(spans, names):
        r = [x for x in mine if lo <= x[0] < hi]
        got = sum(x[3] for x in r)
        pp = [x for x in r if any(abs(t2 - x[0]) <= 300 for t2 in by_pair.get((x[2], x[1]), []))]
        sink = grow = known = 0
        dens_b, dens_a, rdens_b, rdens_a = [], [], [], []
        for t, p, q, g, f in r:
            e = dv.get((t, p, q))
            if e and e.get('L0'):
                dens_b.append(e['B0'] / e['L0'])
                dens_a.append((e['B0'] - g - f) / e['L0'])
                if e.get('qL0'):
                    rdens_b.append(e['qB0'] / e['qL0'])
                    rdens_a.append((e['qB0'] + g) / e['qL0'])
            s = S.get(str(q))
            if s is None:
                continue
            i0 = bisect.bisect_right(s['t'], t) - 1
            i1 = bisect.bisect_right(s['t'], t + 300) - 1
            if i0 < 0 or s['terr'][i0] <= 0:
                continue
            known += g
            seg = s['terr'][i0:i1 + 1]
            dt = P[q]['deathT']
            mn = 0 if (0 <= dt <= t + 300) else min(seg)
            if mn <= 0.8 * s['terr'][i0]:
                sink += g
            elif max(seg) >= 1.2 * s['terr'][i0]:
                grow += g
        wins.append({'name': name, 'n': len(r), 'arrived': got, 'tax': sum(x[4] for x in r), 'pingpongN': len(pp), 'pingpongArrived': sum(x[3] for x in pp),
                     'toSquad': sum(x[3] for x in r if x[2] in sq), 'toOthers': sum(x[3] for x in r if x[2] not in sq),
                     'recipKnownArrived': known, 'recipLost20': sink, 'recipGrew20': grow,
                     'donorDensBefore': round(st.median(dens_b), 1) if dens_b else None, 'donorDensAfter': round(st.median(dens_a), 1) if dens_a else None,
                     'recipDensBefore': round(st.median(rdens_b), 1) if rdens_b else None, 'recipDensAfter': round(st.median(rdens_a), 1) if rdens_a else None})
    R['donations'] = wins

    # ---- F. 人均地：编队 对 其余真人（HS 每 300 拍、全部真人席位；已阵亡/离场的按当时的地算，阵亡 = 0）----
    hs = J['HS']
    pcap = {}
    for i, t in enumerate(hs['t']):
        if t not in (300, 600, 900, 1200, 1500, 2100, 3000, 4200):
            continue
        terr, bal = hs['terr'][i], hs['bal'][i]
        s_l = [terr[p] for p in sq]
        o_l = [terr[p['id']] for p in J['players'] if p['id'] not in sq]
        s_b = [bal[p] for p in sq]
        o_b = [bal[p['id']] for p in J['players'] if p['id'] not in sq]
        if not o_l or not sum(o_l):
            continue
        pcap[t] = {'squadMean': sum(s_l) / len(s_l), 'othersMean': sum(o_l) / len(o_l), 'ratio': (sum(s_l) / len(s_l)) / (sum(o_l) / len(o_l)),
                   'squadShareOfHumanLand': sum(s_l) / (sum(s_l) + sum(o_l)), 'headShare': len(s_l) / (len(s_l) + len(o_l)),
                   'balRatio': ((sum(s_b) / len(s_b)) / (sum(o_b) / len(o_b))) if sum(o_b) else None,
                   'humanLandOfMap': (sum(s_l) + sum(o_l)) / J['map']['land']}
    R['perCapita'] = pcap

    # ---- E. 阵亡 / 离场 ----
    dth = []
    for p, b in sq.items():
        d, l = P[p]['deathT'], P[p]['leftT']
        dth.append({'bot': b, 'deathT': d, 'leftT': l, 'peakTerr': P[p]['peakTerr'], 'peakT': P[p]['peakT']})
    R['fates'] = dth
    return R


def render(RS):
    L = []
    w = L.append
    w('# CROSS-LEDGER — 13 局统一口径的「兵与地」跨局账（R05 / M7，`cross_ledger.py` 机械生成）')
    w('')
    w('所有数字来自逐拍重演的真值（`match_truth.mjs` → `/tmp/c136-r05/truth/<局>.json`；重演已与日志 `[HL-TICK]` 逐条全等校验），不读日志估算、不读复盘 JSON。')
    w('编队 = 录像这一盘里的我方号；其余真人 = 同一盘里不是我方号的真人席位。拆盘局（A017、A043）只有录像这一盘的 1 / 2 个号。')
    w('复算：`python3 scripts/cross_ledger.py --out reports/CROSS-LEDGER.md --json out/cross-ledger.json`。')
    w('')
    # ---- 1 ----
    w('## 1. 编队各段的兵花在哪（占该段利息+地租的百分比）')
    w('')
    w('每格 = 该段从存兵里扣走的兵 ÷ 该段的利息+地租。打中立/机器人/真人含手续费；船含船费；被打掉 = 别人打我方号时扣掉的存兵；')
    w('罚息 = 存兵超过 100×地 后少拿的利息（不是支出，是没拿到的收入，单列）。「兵 起→止」是编队合计存兵。段内没有活号的记「–」。')
    for i, name in enumerate(PHN):
        if i == 0:
            continue
        w('')
        w(f'### {name} 拍')
        w('')
        w('| 局 | 版本 | 结果 | 利息+地租 | 打中立 | 打机器人 | 打真人 | 出船 | 捐兵税 | 被打掉 | 退回 | 罚息 | 兵 起→止 | 地 起→止 |')
        w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
        tot = defaultdict(float)
        for R in RS:
            p = R['phases'][i]
            if not p or p['eco'] <= 0:
                w(f"| {R['mid']} | {R['ver']} | {R['result']} | – | – | – | – | – | – | – | – | – | – | – |")
                continue
            e = p['eco']
            for key in ('eco', 'atkNeutral', 'atkBot', 'atkHuman', 'boat', 'tax', 'dmg', 'ret', 'capLoss'):
                tot[key] += p[key]
            w(f"| {R['mid']} | {R['ver']} | {R['result']} | {k(e)} | {pc(p['atkNeutral'], e)} | {pc(p['atkBot'], e)} | {pc(p['atkHuman'], e)} | {pc(p['boat'], e)} | {pc(p['tax'], e)} | {pc(p['dmg'], e)} | {pc(p['ret'], e)} | {pc(p['capLoss'], e)} | {k(p['bal0'])}→{k(p['bal1'])} | {k(p['land0'])}→{k(p['land1'])} |")
        e = tot['eco']
        w(f"| 合计 | | | {k(e)} | {pc(tot['atkNeutral'], e)} | {pc(tot['atkBot'], e)} | {pc(tot['atkHuman'], e)} | {pc(tot['boat'], e)} | {pc(tot['tax'], e)} | {pc(tot['dmg'], e)} | {pc(tot['ret'], e)} | {pc(tot['capLoss'], e)} | | |")
    # ---- 2 ----
    w('')
    w('## 2. 全程收支结构：编队 对 同一盘的其余真人 对 赢家队的真人')
    w('')
    w('每格 = 全程该科目 ÷ 全程利息+地租（组内各号相加）。赢家队 = 对局卡 winnerTeam 那一队里不是我方号的真人；我方赢的局这一列是路人队友。')
    w('捐兵净损 = 组内各号 捐出(含税) − 收到 = 交掉的税 + 净送给组外的兵（组内互捐的本金两边抵消，只剩税）。船靠岸 = 船上的兵回到存兵（落在自己或队友的地上）。')
    w('')
    w('| 局 | 结果 | 组 | 人数 | 每人利息+地租 | 打中立 | 打机器人 | 打真人 | 出船 | 船靠岸 | 捐兵净损 | 被打掉 | 退回 | 峰值地中位 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    agg = {g: defaultdict(float) for g in ('squad', 'others', 'winnerTeamOthers')}
    for R in RS:
        for g, gname in (('squad', '编队'), ('others', '其余真人'), ('winnerTeamOthers', '赢家队')):
            G = R['groups'][g]
            if not G:
                continue
            f = G['flows']
            e = f['eco']
            for key, v in f.items():
                agg[g][key] += v
            agg[g]['n'] += G['n']
            w(f"| {R['mid']} | {R['result']} | {gname} | {G['n']} | {k(e/G['n'])} | {pc(-f['atkNeutral'], e)} | {pc(-f['atkBot'], e)} | {pc(-f['atkHuman'], e)} | {pc(-f['boat'], e)} | {pc(f['boatLand'], e)} | {pc(-f['donOut'] - f['donIn'], e)} | {pc(-f['dmg'], e)} | {pc(f['ret'], e)} | {G['peakMedian']:,.0f} |")
    for g, gname in (('squad', '编队'), ('others', '其余真人'), ('winnerTeamOthers', '赢家队')):
        f = agg[g]
        e = f['eco']
        w(f"| 13 局合计 | | {gname} | {f['n']:.0f} | {k(e/f['n'])} | {pc(-f['atkNeutral'], e)} | {pc(-f['atkBot'], e)} | {pc(-f['atkHuman'], e)} | {pc(-f['boat'], e)} | {pc(f['boatLand'], e)} | {pc(-f['donOut'] - f['donIn'], e)} | {pc(-f['dmg'], e)} | {pc(f['ret'], e)} | |")
    # ---- 3 ----
    w('')
    w('## 3. 地从哪来、打下一格花多少兵：编队 对 其余真人（每人平均）')
    w('')
    w('拿到的地按「从谁手里拿的」分：中立 / 机器人（含已离场的真人）/ 真人。兵÷格 = 打这一类目标时从存兵里扣走的兵（含手续费；目标先死而退回的兵也算在内，所以是毛数）÷ 从这一类目标手里拿到的格数。')
    w('')
    w('| 局 | 结果 | 组 | 人数 | 每人：从中立 | 从机器人 | 从真人 | 被拿走 | 打机器人 兵÷格 | 打真人 兵÷格 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    agg = {g: defaultdict(float) for g in ('squad', 'others', 'winnerTeamOthers')}
    ratio = defaultdict(list)
    for R in RS:
        for g, gname in (('squad', '编队'), ('others', '其余真人'), ('winnerTeamOthers', '赢家队')):
            G = R['groups'][g]
            if not G:
                continue
            n = G['n']
            for key in ('tilesN', 'tilesB', 'tilesH', 'tilesLost', 'sentB', 'sentH'):
                agg[g][key] += G[key]
            agg[g]['n'] += n
            w(f"| {R['mid']} | {R['result']} | {gname} | {n} | {G['tilesN']/n:,.0f} | {G['tilesB']/n:,.0f} | {G['tilesH']/n:,.0f} | {G['tilesLost']/n:,.0f} | {(G['sentB']/G['tilesB'] if G['tilesB'] else 0):.1f} | {(G['sentH']/G['tilesH'] if G['tilesH'] else 0):.1f} |")
        s, o = R['groups']['squad'], R['groups']['others']
        for key in ('tilesN', 'tilesB', 'tilesH'):
            if o[key]:
                ratio[key].append((s[key] / s['n']) / (o[key] / o['n']))
    for g, gname in (('squad', '编队'), ('others', '其余真人'), ('winnerTeamOthers', '赢家队')):
        f = agg[g]
        n = f['n']
        w(f"| 13 局合计 | | {gname} | {n:.0f} | {f['tilesN']/n:,.0f} | {f['tilesB']/n:,.0f} | {f['tilesH']/n:,.0f} | {f['tilesLost']/n:,.0f} | {f['sentB']/f['tilesB']:.1f} | {f['sentH']/f['tilesH']:.1f} |")
    w('')
    w('编队每人 ÷ 其余真人每人（逐局比值的中位数；<1 = 编队少）：' + '；'.join(f"{nm} {st.median(ratio[key]):.2f}（<1 的 {sum(1 for x in ratio[key] if x < 1)}/{len(ratio[key])} 局）" for key, nm in (('tilesN', '从中立'), ('tilesB', '从机器人'), ('tilesH', '从真人'))) + '。')
    # ---- 4 ----
    w('')
    w('## 4. 打真人：是从哪个出口放出去的、打的是谁')
    w('')
    w('放行 = 执行前一刻存兵 > 100×地（`buyLand` L5352–5359 在这种情况下跳过价格门 `c >= worth`）。目标更强 = 目标存兵 ≥ 我方号存兵（执行前一刻）。')
    w('≥3 条的轮 = 同一个号对同一个目标、相邻两条间隔 ≤ 21 拍、合计 ≥3 条。每轮花掉 = 一轮连手续费打出的兵 ÷ 第一条执行前的存兵。')
    w('放行口有两种算法：「逐条」= 这一条执行前一刻过线（同一轮里第一条扣兵之后，后面几条执行时往往已经不过线，所以是下界）；')
    w('「按轮」= 一轮的第一条执行前过线，整轮都算放行口放出来的（后面几条是第一条在途期间下的单，下单时策略看到的还是过线的存兵）。')
    w('')
    w('| 局 | 版本 | 结果 | 打真人条数 | 打出(含费) | 放行口占打出（逐条） | 放行口占打出（按轮） | 目标更强占打出 | 目标 ≥2 倍 | 目标已离场 | 轮数 | 每轮条数(中位) | ≥3 条的轮占打出 | 首条花掉(中位) | 整轮花掉(中位) |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    tot = defaultdict(float)
    for R in RS:
        h = R['humanAtk']['all']
        for key in ('n', 'sent', 'overSent', 'overVolleySent', 'tgtGE1Sent', 'tgtGE2Sent', 'leftTargetSent', 'volleys', 'volleysGE3Sent'):
            tot[key] += h[key]
        fm = '–' if h['firstFracMedian'] is None else f"{100*h['firstFracMedian']:.0f}%"
        vm = '–' if h['volleyFracMedian'] is None else f"{100*h['volleyFracMedian']:.0f}%"
        lm = '–' if h['volleyLenMedian'] is None else f"{h['volleyLenMedian']:g}"
        w(f"| {R['mid']} | {R['ver']} | {R['result']} | {h['n']} | {k(h['sent'])} | {pc(h['overSent'], h['sent'])} | {pc(h['overVolleySent'], h['sent'])} | {pc(h['tgtGE1Sent'], h['sent'])} | {pc(h['tgtGE2Sent'], h['sent'])} | {pc(h['leftTargetSent'], h['sent'])} | {h['volleys']} | {lm} | {pc(h['volleysGE3Sent'], h['sent'])} | {fm} | {vm} |")
    s = tot['sent']
    w(f"| 合计 | | | {tot['n']:.0f} | {k(s)} | {pc(tot['overSent'], s)} | {pc(tot['overVolleySent'], s)} | {pc(tot['tgtGE1Sent'], s)} | {pc(tot['tgtGE2Sent'], s)} | {pc(tot['leftTargetSent'], s)} | {tot['volleys']:.0f} | | {pc(tot['volleysGE3Sent'], s)} | | |")
    w('')

    def med_share(rs, key):
        v = [100 * R['humanAtk']['all'][key] / R['humanAtk']['all']['sent'] for R in rs if R['humanAtk']['all']['sent']]
        return f"{st.median(v):.0f}%" if v else '–'
    for nm, rs in (('输的', [R for R in RS if R['result'] != 'won']), ('赢的', [R for R in RS if R['result'] == 'won'])):
        w(f"- {nm} {len(rs)} 局各局占比的中位：放行口（按轮）{med_share(rs, 'overVolleySent')}、目标更强 {med_share(rs, 'tgtGE1Sent')}、目标 ≥2 倍 {med_share(rs, 'tgtGE2Sent')}。")
    w('')
    w('按时段（13 局合计）：')
    w('')
    w('| 时段 | 条数 | 打出 | 放行口占（逐条） | 放行口占（按轮） | 目标更强占 | 目标 ≥2 倍占 | ≥3 条的轮占 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    for key, nm in (('1500-4284', '1500–4284'), ('4284+', '4284–终局')):
        t = defaultdict(float)
        for R in RS:
            for kk, v in R['humanAtk'][key].items():
                if isinstance(v, (int, float)) and v is not None:
                    t[kk] += v
        w(f"| {nm} | {t['n']:.0f} | {k(t['sent'])} | {pc(t['overSent'], t['sent'])} | {pc(t['overVolleySent'], t['sent'])} | {pc(t['tgtGE1Sent'], t['sent'])} | {pc(t['tgtGE2Sent'], t['sent'])} | {pc(t['volleysGE3Sent'], t['sent'])} |")
    w('')
    w('逐局 × 时段（每格 = 条数 / 打出 / 放行口按轮 / 目标更强 / 目标 ≥2 倍；百分比都是占该格打出的兵）：')
    w('')
    w('| 局 | 结果 | 1500–4284 拍 | 4284 拍–终局 |')
    w('| --: | --: | --: | --: |')
    for R in RS:
        cells = []
        for key in ('1500-4284', '4284+'):
            h = R['humanAtk'][key]
            cells.append('–' if not h['n'] else f"{h['n']} 条 / {k(h['sent'])} / {pc(h['overVolleySent'], h['sent'])} / {pc(h['tgtGE1Sent'], h['sent'])} / {pc(h['tgtGE2Sent'], h['sent'])}")
        w(f"| {R['mid']} | {R['result']} | {cells[0]} | {cells[1]} |")
    # ---- 5 ----
    w('')
    w('## 5. 捐兵（录像里执行了的）：三个配额时段')
    w('')
    w('t<3213：配额按全图的地计价；3213–4284：按受赠方的地计价；≥4284：不限。来回 = 同一对号 300 拍内反方向也有一笔。')
    w('受赠方之后 300 拍：地的最小值 ≤ 到账时的 80%（含阵亡）记「丢地」，否则最大值 ≥ 120% 记「长地」；只统计受赠方是我方号的。密度 = 存兵÷地（中位数，捐前→捐后）。')
    w('')
    w('| 局 | 结果 | 时段 | 笔数 | 到账 | 税 | 来回占到账 | 给丢地的号 | 给长地的号 | 捐出方密度 前→后 | 受赠方密度 前→后 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    tot = [defaultdict(float) for _ in range(4)]
    for R in RS:
        for i, d in enumerate(R['donations']):
            if not d['n']:
                continue
            for key in ('n', 'arrived', 'tax', 'pingpongArrived', 'recipKnownArrived', 'recipLost20', 'recipGrew20'):
                tot[i][key] += d[key]
            dd = '–' if d['donorDensBefore'] is None else f"{d['donorDensBefore']:.0f}→{d['donorDensAfter']:.0f}"
            rd = '–' if d['recipDensBefore'] is None else f"{d['recipDensBefore']:.0f}→{d['recipDensAfter']:.0f}"
            w(f"| {R['mid']} | {R['result']} | {d['name']} | {d['n']} | {k(d['arrived'])} | {k(d['tax'])} | {pc(d['pingpongArrived'], d['arrived'])} | {pc(d['recipLost20'], d['recipKnownArrived'])} | {pc(d['recipGrew20'], d['recipKnownArrived'])} | {dd} | {rd} |")
    for i, nm in enumerate(['<3213', '3213–4284', '≥4284（有对手时）', '我方队已占 90% 之后']):
        t = tot[i]
        if t['n']:
            w(f"| 13 局合计 | | {nm} | {t['n']:.0f} | {k(t['arrived'])} | {k(t['tax'])} | {pc(t['pingpongArrived'], t['arrived'])} | {pc(t['recipLost20'], t['recipKnownArrived'])} | {pc(t['recipGrew20'], t['recipKnownArrived'])} | | |")
    # ---- 7（放在 6 前面）----
    w('')
    w('## 7. 人均地与人均兵：编队 对 同一盘的其余真人（按席位平均）')
    w('')
    w('每格 = 编队每个席位的平均地 ÷ 其余真人每个席位的平均地（括号里是人均存兵的比值）。分母是全部真人席位（已阵亡的按 0、已离场的按当时的地），')
    w('所以 1.00 = 编队拿到了与人数相称的那一份「真人手里的地」；与 REVIEW-ROLLUP 第 2 节（在场真人的中位数之比）口径不同、互为补充。')
    w('')
    TS = (300, 600, 900, 1200, 1500, 2100, 3000, 4200)
    w('| 局 | 结果 | ' + ' | '.join(f'{t} 拍' for t in TS) + ' | 1500 拍真人手里的地占全图 |')
    w('| --: | --: | ' + ' | '.join('--:' for _ in TS) + ' | --: |')
    cols = defaultdict(list)
    for R in RS:
        cells = []
        for t in TS:
            x = R['perCapita'].get(t)
            if not x or not x['squadMean']:
                cells.append('–')
                continue
            cols[t].append(x['ratio'])
            cells.append(f"{x['ratio']:.2f}" + (f"（{x['balRatio']:.2f}）" if x.get('balRatio') is not None else ''))
        h = R['perCapita'].get(1500)
        w(f"| {R['mid']} | {R['result']} | " + ' | '.join(cells) + f" | {pc(h['humanLandOfMap'], 1) if h else '–'} |")
    w('| 中位（<1 的局数/有数的局数） | | ' + ' | '.join((f"{st.median(cols[t]):.2f}（{sum(1 for x in cols[t] if x < 1)}/{len(cols[t])}）" if cols[t] else '–') for t in TS) + ' | |')
    balm = {t: [R['perCapita'][t]['balRatio'] for R in RS if R['perCapita'].get(t) and R['perCapita'][t]['squadMean'] and R['perCapita'][t].get('balRatio') is not None] for t in TS}
    w('| 人均存兵比值的中位（>1 的局数） | | ' + ' | '.join((f"{st.median(balm[t]):.2f}（{sum(1 for x in balm[t] if x > 1)}/{len(balm[t])}）" if balm[t] else '–') for t in TS) + ' | |')
    # 延迟波局（决策级延迟账：600–1500 拍落地指令延迟 P50 ≥ 60 拍；reviews/<局>.json 的 delayAccount）对 其余局
    lag = set()
    for R in RS:
        try:
            D = json.load(open(os.path.join(HERE, '..', 'reviews', f"{R['mid']}.json")))['delayAccount']
            bp = {r['period']: r for r in D.get('delayByPeriod') or []}
            if ((bp.get('600–1500') or {}).get('p50') or 0) >= 60:
                lag.add(R['mid'])
        except (OSError, KeyError):
            pass
    w('')
    for lab, sel in ((f'延迟波局（{len(lag)} 局：' + '、'.join(sorted(lag)) + '）', lambda R: R['mid'] in lag), ('其余局', lambda R: R['mid'] not in lag)):
        parts = []
        for t in (600, 1200, 1500, 2100):
            v = [R['perCapita'][t]['ratio'] for R in RS if sel(R) and R['perCapita'].get(t) and R['perCapita'][t]['squadMean']]
            b = [R['perCapita'][t]['balRatio'] for R in RS if sel(R) and R['perCapita'].get(t) and R['perCapita'][t]['squadMean'] and R['perCapita'][t].get('balRatio') is not None]
            if v:
                parts.append(f'{t} 拍 地 {st.median(v):.2f}（兵 {st.median(b):.2f}）')
        w(f'- {lab}人均地比值的中位：' + '；'.join(parts) + '。')
    # ---- 6 ----
    w('')
    w('## 6. 我方号的结局（录像这一盘）')
    w('')
    w('离场过 = 录像里这个号在还活着的时候有离场指令（客户端掉线，或 t>8500 策略主动离场）；离场后的号由引擎的内置 AI 接管、按机器人算。')
    w('在线时阵亡 = 阵亡时没有离场过（阵亡之后客户端退出不算离场）。三列相加 = 号数。')
    w('')
    w('| 局 | 结果 | 号数 | 离场过 | 其中 <1500 | 1500–3000 | ≥3000 | 在线时阵亡 | 其中 <1500 | 1500–3000 | 3000–4284 | ≥4284 | 活到终局（在线） | 终局拍 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    tt = defaultdict(int)
    for R in RS:
        F = R['fates']
        left = [x['leftT'] for x in F if x['leftT'] >= 0 and (x['deathT'] < 0 or x['leftT'] <= x['deathT'])]
        d = [x['deathT'] for x in F if x['deathT'] >= 0 and not (0 <= x['leftT'] <= x['deathT'])]
        alive = [x for x in F if x['deathT'] < 0 and x['leftT'] < 0]
        lb = [sum(1 for t in left if lo <= t < hi) for lo, hi in ((-10 ** 6, 1500), (1500, 3000), (3000, 10 ** 6))]
        b = [sum(1 for t in d if lo <= t < hi) for lo, hi in ((0, 1500), (1500, 3000), (3000, 4284), (4284, 10 ** 6))]
        vals = (len(F), len(left), *lb, len(d), *b, len(alive))
        for key, v in zip(('n', 'left', 'l0', 'l1', 'l2', 'd', 'b0', 'b1', 'b2', 'b3', 'alive'), vals):
            tt[key] += v
        w(f"| {R['mid']} | {R['result']} | " + ' | '.join(str(v) for v in vals) + f" | {R['endTick']} |")
    w('| 合计 | | ' + ' | '.join(str(tt[key]) for key in ('n', 'left', 'l0', 'l1', 'l2', 'd', 'b0', 'b1', 'b2', 'b3', 'alive')) + ' | |')
    w('')
    return '\n'.join(L)


RS = [one(m) for m in ids]
if JOUT:
    os.makedirs(os.path.dirname(os.path.abspath(JOUT)), exist_ok=True)
    json.dump(RS, open(JOUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
txt = render(RS)
open(OUT, 'w', encoding='utf-8').write(txt)
print(f'→ {OUT} {txt.count(chr(10))} 行；{JOUT}')
