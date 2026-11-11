#!/usr/bin/env python3
"""m6_all_lobby.py — 线上的大厅长什么样（给模拟器配大厅用），和页面决策耗时 × 通道。

读 out/_all/joined.csv（m6_all_outcomes.py 写）、out/<局>/voronoi_seats.csv（好地账的席位表：第 1 拍在场的每个真人席位的
队号、是否本队、630 / 1500 拍的状态）、bundles/<局>/traj.csv（页面每 90 拍记一次的累计平均决策耗时 avgMs）。
不是同一场对局的 15 个包不计。

  1. 大厅：真人数、有真人的队数、本队所在的队有多少真人、本队席位占所在队和占全场的比例；
  2. 其他真人到 630 / 1500 拍的去向：在场、已离场（席位成了壳）、已阵亡；
  3. 决策耗时：把累计平均还原成各时段的增量平均，按 600–1500 拍的落地率分三组；和落地率的秩相关；
  4. 给模拟器对账用的一张表：按通道分三组，线上跑的版本的批次占比、重复占比、天然份额、吃到率、人均相对值、被移出的席位；
  5. 协调器三个版本（扇形半径改过两次）的天然份额：一组现成的自然对照；它混着大厅人数和随机安放两件事，
     所以另给按大厅人数分层的表（5b）和有号被引擎随机安放的局（5c）。

用法：python3 scripts/m6_all_lobby.py
"""
import csv
import os
import statistics
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
DATA = '/agent/repos/c136-data/bundles'


def quart(v, nd=None):
    v = sorted(v)
    n = len(v)
    f = (lambda x: x) if nd is None else (lambda x: round(x, nd))
    return f"{f(v[0])} / {f(v[n // 4])} / {f(v[n // 2])} / {f(v[3 * n // 4])} / {f(v[-1])}"


def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for k in range(i, j + 1):
            r[s[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def rho(x, y):
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main():
    J = [r for r in csv.DictReader(open(os.path.join(R, 'out', '_all', 'joined.csv'), encoding='utf8')) if r['multi'] == '0']

    print('== 1. 大厅（是同一场对局、有席位表的局；席位表 = 第 1 拍在场的真人席位）')
    print('编队 | 局数 | 真人数 最少 / P25 / 中位 / P75 / 最多 | 有真人的队数（队数:局数）| 本队所在的队的真人数 | 本队席位 ÷ 所在队的真人数 | 本队席位 ÷ 全部真人')
    fate = defaultdict(lambda: {'n630': Counter(), 'n1500': Counter(), 'g630': [], 'g1500': []})
    for co in ('squad10', 'squad20'):
        hum, teams, own, frac_team, frac_all = [], Counter(), [], [], []
        n = 0
        for r in J:
            if r['cohort'] != co:
                continue
            f = os.path.join(R, 'out', r['mid'], 'voronoi_seats.csv')
            if not os.path.exists(f):
                continue
            S = list(csv.DictReader(open(f, encoding='utf8')))
            sq = [s for s in S if s['squad'] == '1']
            if not sq:
                continue
            n += 1
            tc = Counter(s['team'] for s in S)
            main_team = Counter(s['team'] for s in sq).most_common(1)[0][0]
            in_main = sum(1 for s in sq if s['team'] == main_team)
            hum.append(len(S))
            if len(tc) > 1 and r['teams'] not in ('', '0', 'None'):
                teams[len(tc)] += 1
            own.append(tc[main_team])
            frac_team.append(in_main / tc[main_team])
            frac_all.append(len(sq) / len(S))
            others = [s for s in S if s['squad'] != '1']
            for key in ('630', '1500'):
                col = 'state' + key
                if col not in S[0] or not others:
                    continue
                c = Counter('dead' if s[col] == '-1' else 'left' if s[col] == '2' else 'in' for s in others)
                fate[co]['n' + key].update(c)
                fate[co]['g' + key].append({k: c[k] / len(others) for k in ('in', 'left', 'dead')})
        print(f"{co} | {n} | {quart(hum)} | {' '.join(f'{k}:{v}' for k, v in sorted(teams.items()))} | {quart(own)} | {quart(frac_team, 2)} | {quart(frac_all, 2)}")

    print()
    print('== 2. 其他真人（不含本队席位）到 630 / 1500 拍的去向：各局比例的中位数（括号里是把所有局的席位合在一起算）')
    print('编队 | 630 拍：在场 / 已离场（席位成了壳，壳还活着）/ 已阵亡 | 1500 拍：在场 / 已离场 / 已阵亡')
    for co in ('squad10', 'squad20'):
        parts = []
        for key in ('630', '1500'):
            g = fate[co]['g' + key]
            c = fate[co]['n' + key]
            tot = sum(c.values())
            parts.append(' / '.join(f"{100 * statistics.median(x[k] for x in g):.0f}%（{100 * c[k] / tot:.0f}%）" for k in ('in', 'left', 'dead')) + f"，{len(g)} 局 {tot} 个席位")
        print(f"{co} | {parts[0]} | {parts[1]}")

    print()
    print('== 3. 页面记的决策耗时（traj.csv 的 avgMs 是累计平均；这里还原成各时段的增量平均，取各号的中位数，再取各局的中位数；毫秒/拍）')
    print('分组（squad10，按 600–1500 拍陆攻+船 落地/放行）| 局数 | 90–450 拍 | 450–600 拍 | 600–1500 拍 | 1500–3000 拍')
    G = defaultdict(list)
    X = []
    for r in J:
        if r['cohort'] != 'squad10' or r['nd600_1500'] in ('', 'None') or float(r['nd600_1500']) > 1.15:
            continue
        nd = float(r['nd600_1500'])
        seats = defaultdict(dict)
        for x in csv.DictReader(open(os.path.join(DATA, r['mid'], 'traj.csv'), encoding='utf8')):
            try:
                seats[x['bot']][int(x['t'])] = float(x['avgMs'])
            except ValueError:
                pass

        def inc(a, b):
            v = []
            for S in seats.values():
                ta = max((t for t in S if t <= a), default=None)
                tb = max((t for t in S if t <= b), default=None)
                if ta and tb and tb > ta:
                    v.append((S[tb] * tb - S[ta] * ta) / (tb - ta))
            return statistics.median(v) if v else None

        row = (inc(90, 450), inc(450, 600), inc(600, 1500), inc(1500, 3000))
        G['≥ 0.9（通道干净）' if nd >= 0.9 else '< 0.7（通道差）' if nd < 0.7 else '0.7–0.9'].append(row)
        if row[0] is not None and row[2] is not None:
            X.append((nd, row[0], row[2]))
    for key in ('≥ 0.9（通道干净）', '0.7–0.9', '< 0.7（通道差）'):
        L = G[key]
        cells = []
        for i in range(4):
            v = [x[i] for x in L if x[i] is not None]
            cells.append(f"{statistics.median(v):.2f}" if v else '-')
        print(f"{key} | {len(L)} | " + ' | '.join(cells))
    nd = [x[0] for x in X]
    print(f"# 秩相关（{len(X)} 局）：90–450 拍的决策耗时 × 600–1500 拍落地率 ρ = {rho([x[1] for x in X], nd):.2f}；600–1500 拍的决策耗时 × 同期落地率 ρ = {rho([x[2] for x in X], nd):.2f}")
    lo = [x for x in X if x[1] < 0.5]
    hi = [x for x in X if x[1] >= 0.7]
    print(f"# 90–450 拍决策耗时 < 0.5 毫秒的 {len(lo)} 局里通道差的 {sum(1 for x in lo if x[0] < 0.7)} 局；≥ 0.7 毫秒的 {len(hi)} 局里通道差的 {sum(1 for x in hi if x[0] < 0.7)} 局")

    print()
    print('== 4. 给模拟器对账用：squad10 按通道分三组，线上跑的版本的各项中位数（各局的值取中位）')
    print('分组 | 局数 | 600–1500 落地/放行 | 同拍 ≥3 条的批次占落地陆攻 | 21 拍内重复占落地陆攻 | 天然份额/人头占比 | 630 拍吃到率 | 1500 拍吃到率 | AI 地份额/人头占比 | 人均相对值 630 / 1530 / 3060 | 1500 拍前被移出的席位')
    RF = {r['mid']: r for r in csv.DictReader(open(os.path.join(R, 'out', '_all', 'replay_facts.csv'), encoding='utf8'))}
    LD = {r['mid']: r for r in csv.DictReader(open(os.path.join(R, 'out', '_all', 'land.csv'), encoding='utf8'))}

    def fl(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def m(v, nd=2):
        v = sorted(x for x in v if x is not None)
        return f"{v[len(v) // 2]:.{nd}f}" if v else '-'

    for key, cond in (('≥ 0.9（通道干净）', lambda x: 0.9 <= x <= 1.15), ('0.7–0.9', lambda x: 0.7 <= x < 0.9), ('< 0.7（通道差）', lambda x: x < 0.7)):
        S = [r for r in J if r['cohort'] == 'squad10' and fl(r['nd600_1500']) is not None and cond(fl(r['nd600_1500']))]
        rep, left, seats = [], 0, 0
        for r in S:
            x = RF.get(r['mid'])
            if x and fl(x.get('atkLanded')):
                rep.append(fl(x['repeats']) / fl(x['atkLanded']))
            if x and fl(x.get('squad')):
                left += int(fl(x.get('left1500') or 0))
                seats += int(fl(x['squad']))
        L = [LD[r['mid']] for r in S if r['mid'] in LD]
        print(f"{key} | {len(S)} | {m([fl(r['nd600_1500']) for r in S])} | {m([fl(r['batchShare']) for r in S])} | {m(rep)} | "
              f"{m([fl(x['natRatio']) for x in L])} | {m([fl(x['cap630s']) for x in L])} | {m([fl(x['cap1500s']) for x in L])} | {m([fl(x['aiShare']) for x in L])} | "
              f"{m([fl(r['rel630']) for r in S])} / {m([fl(r['rel1530']) for r in S])} / {m([fl(r['rel3060']) for r in S])} | {left}/{seats}")

    # 5. 协调器换过两次扇形半径：三个版本的天然份额。版本按包号分（src/strategy/VERSION-TIMELINE.md：
    #    A001–A017 是 Va，A018–A095 是 Vb，A097–A099 是 Vc）；扇形的两行在 spawn-coordinator-c116*.mjs 的 L1076–1077。
    print()
    print('== 5. 协调器三个版本的扇形半径和天然份额（squad10，是同一场对局的局；天然份额在出生阶段结束时就定了，和策略参数无关）')
    print('版本（包号）| 外圈半径 r2（封顶，像素）| 局数 | 天然份额 ÷ 人头占比 P25 / 中位 / P75 | ≥ 0.75 的局 | 大厅真人数中位 | 通道干净（≥ 0.9）的局：局数；天然份额、630 / 1530 拍人均相对值的中位')

    def ver(mid):
        n = int(mid[1:])
        return 'Va' if n <= 17 else ('Vb' if n <= 95 else 'Vc')

    def qq(v, p):
        v = sorted(x for x in v if x is not None)
        if not v:
            return None
        k = (len(v) - 1) * p
        lo = int(k)
        hi = min(lo + 1, len(v) - 1)
        return v[lo] + (v[hi] - v[lo]) * (k - lo)

    def ranksum(a, b):
        allv = sorted([(x, 0) for x in a] + [(x, 1) for x in b])
        rk = [0.0] * len(allv)
        i = 0
        while i < len(allv):
            j = i
            while j < len(allv) and allv[j][0] == allv[i][0]:
                j += 1
            for k in range(i, j):
                rk[k] = (i + j + 1) / 2
            i = j
        n1, n2 = len(a), len(b)
        u = sum(rk[k] for k in range(len(allv)) if allv[k][1] == 0) - n1 * (n1 + 1) / 2
        z = (u - n1 * n2 / 2) / (n1 * n2 * (n1 + n2 + 1) / 12) ** 0.5
        import math
        return z, math.erfc(abs(z) / 2 ** 0.5)

    FAN = {'Va': '2.35 × rCell（225）', 'Vb': '1.88 × rCell（182）', 'Vc': '2.28 × rCell（220），内圈至多 2 个号'}
    NAT = {}
    for v in ('Va', 'Vb', 'Vc'):
        S = [r for r in J if r['cohort'] == 'squad10' and ver(r['mid']) == v and r['mid'] in LD and fl(LD[r['mid']]['natRatio']) is not None]
        nat = [fl(LD[r['mid']]['natRatio']) for r in S]
        NAT[v] = nat
        C = [r for r in S if fl(r['nd600_1500']) is not None and 0.9 <= fl(r['nd600_1500']) <= 1.15]
        hum = sorted(fl(r['humans']) for r in S)
        if len(C) <= 3:
            clean = f"{len(C)} 局；" + '；'.join(
                f"{r['mid']} {fl(LD[r['mid']]['natRatio']):.2f}、{fl(r['rel630']):.2f} / {fl(r['rel1530']):.2f}" for r in C)
        else:
            clean = (f"{len(C)} 局；{qq([fl(LD[r['mid']]['natRatio']) for r in C], .5):.2f}、"
                     f"{qq([fl(r['rel630']) for r in C], .5):.2f} / {qq([fl(r['rel1530']) for r in C], .5):.2f}")
        print(f"{v}（{S[0]['mid']}–{S[-1]['mid']}）| {FAN[v]} | {len(S)} | {qq(nat, .25):.2f} / {qq(nat, .5):.2f} / {qq(nat, .75):.2f} | {sum(1 for x in nat if x >= 0.75)} | {hum[len(hum) // 2]:.0f} | {clean}")
    z1, p1 = ranksum(NAT['Va'], NAT['Vb'])
    z2, p2 = ranksum(NAT['Va'] + NAT['Vc'], NAT['Vb'])
    print(f"# 天然份额的秩和检验（不分层）：Va 对 Vb z = {z1:.2f}（双侧 p ≈ {p1:.3f}）；Va 和 Vc 合起来对 Vb z = {z2:.2f}（p ≈ {p2:.3f}）。这个差里混着下面两件事，不能直接算成扇形半径的效果")

    # 两个混杂：大厅人数（第 1 拍在场的真人席位数，land.csv 的 humans）；没有出生指令落地、被引擎随机安放的号（joined.csv 的 noSpawn）。
    S5 = [r for r in J if r['cohort'] == 'squad10' and r['mid'] in LD and fl(LD[r['mid']]['natRatio']) is not None]

    def nat_of(r):
        return fl(LD[r['mid']]['natRatio'])

    def hum1(r):
        return fl(LD[r['mid']]['humans'])

    def nsp(r):
        return int(fl(r.get('noSpawn')) or 0)

    BINS = ((0, 45, '< 45'), (45, 70, '45–69'), (70, 9999, '≥ 70'))

    def bin_of(r):
        return next(name for lo, hi, name in BINS if lo <= hum1(r) < hi)

    ok = [r for r in S5 if nsp(r) == 0]
    okb = [r for r in ok if ver(r['mid']) == 'Vb']
    print(f"# 混杂一，大厅人数：出生指令全落地的 {len(ok)} 局里，天然份额 ÷ 人头占比和第 1 拍在场真人数的秩相关 "
          f"{rho([nat_of(r) for r in ok], [hum1(r) for r in ok]):.2f}（只看 Vb 的 {len(okb)} 局 {rho([nat_of(r) for r in okb], [hum1(r) for r in okb]):.2f}）；"
          f"第 1 拍在场真人数的中位：" + '、'.join(f"{v} {qq([hum1(r) for r in S5 if ver(r['mid']) == v], .5):.0f}" for v in ('Va', 'Vb', 'Vc')))
    print('5b. 按大厅人数分层（只算出生指令全落地的局；不超过 3 局列出各局的值，否则给局数、中位、最小–最大）')
    print('第 1 拍在场真人数 | Va | Vb | Vc')
    for lo, hi, name in BINS:
        cells = []
        for v in ('Va', 'Vb', 'Vc'):
            xs = sorted(nat_of(r) for r in ok if ver(r['mid']) == v and lo <= hum1(r) < hi)
            if not xs:
                cells.append('—')
            elif len(xs) <= 3:
                cells.append(f"{len(xs)} 局：" + '、'.join(f"{x:.2f}" for x in xs))
            else:
                cells.append(f"{len(xs)} 局，中位 {qq(xs, .5):.2f}（{xs[0]:.2f}–{xs[-1]:.2f}）")
        print(f"{name} | " + ' | '.join(cells))
    big = [r for r in ok if hum1(r) >= 70]
    wide = [nat_of(r) for r in big if ver(r['mid']) != 'Vb']
    narrow = [nat_of(r) for r in big if ver(r['mid']) == 'Vb']
    z3, p3 = ranksum(wide, narrow)
    small = [r for r in ok if hum1(r) < 70]
    z4, p4 = ranksum([nat_of(r) for r in small if ver(r['mid']) != 'Vb'], [nat_of(r) for r in small if ver(r['mid']) == 'Vb'])
    print(f"# 分层以后：≥ 70 人这一档 Va 和 Vc 的 {len(wide)} 局对 Vb 的 {len(narrow)} 局，秩和 z = {z3:.2f}（双侧 p ≈ {p3:.3f}，样本很小）；"
          f"70 人以下 Va 和 Vc 的 {sum(1 for r in small if ver(r['mid']) != 'Vb')} 局对 Vb 的 {sum(1 for r in small if ver(r['mid']) == 'Vb')} 局 z = {z4:.2f}（p ≈ {p4:.2f}），看不出差别")
    rnd = sorted((r for r in S5 if nsp(r) > 0), key=lambda r: r['mid'])
    print(f"5c. 混杂二，随机安放：有号没有出生指令落地（被引擎随机安放）的 {len(rnd)} 局，和同版本、同一档大厅、出生指令全落地的局比")
    print('局 | 版本 | 第 1 拍在场真人数 | 随机安放的号 ÷ 本队的号 | 天然份额 ÷ 人头占比 | 同版本同档的局：局数、中位 | 高于其中几局')
    above_all = 0
    for r in rnd:
        v = ver(r['mid'])
        ref = sorted(nat_of(x) for x in ok if ver(x['mid']) == v and bin_of(x) == bin_of(r))
        above = sum(1 for x in ref if nat_of(r) > x)
        above_all += 1 if ref and nat_of(r) > qq(ref, .5) else 0
        print(f"{r['mid']} | {v} | {hum1(r):.0f} | {nsp(r)}/{int(fl(r['squadN']))} | {nat_of(r):.2f} | {len(ref)} 局，{qq(ref, .5):.2f} | {above}/{len(ref)}")
    print(f"# 这 {len(rnd)} 局里 {above_all} 局高于同版本同档的中位：号被随机撒开时，名下的地比协调器排的扇形多")

    C = [r for r in S5 if fl(r['nd600_1500']) is not None and 0.9 <= fl(r['nd600_1500']) <= 1.15 and fl(r['rel1530']) is not None]
    hi = sorted((r for r in C if nat_of(r) >= 0.75), key=lambda r: r['mid'])
    lo = [r for r in C if nat_of(r) < 0.75]
    print(f"# 通道干净的 {len(C)} 局里，天然份额 ÷ 人头占比 ≥ 0.75 的 {len(hi)} 局（{' '.join(r['mid'] for r in hi)}）1530 拍人均相对值 "
          f"{min(fl(r['rel1530']) for r in hi):.2f}–{max(fl(r['rel1530']) for r in hi):.2f}，赢 {sum(1 for r in hi if r['won'] == '1')} 局；低于 0.75 的 {len(lo)} 局 "
          f"{min(fl(r['rel1530']) for r in lo):.2f}–{max(fl(r['rel1530']) for r in lo):.2f}（中位 {qq([fl(r['rel1530']) for r in lo], .5):.2f}），赢 {sum(1 for r in lo if r['won'] == '1')} 局")
    rxy = rho([nat_of(r) for r in C], [fl(r['rel1530']) for r in C])
    rxz = rho([nat_of(r) for r in C], [hum1(r) for r in C])
    ryz = rho([fl(r['rel1530']) for r in C], [hum1(r) for r in C])
    part = (rxy - rxz * ryz) / ((1 - rxz ** 2) * (1 - ryz ** 2)) ** 0.5
    print(f"# 这 {len(C)} 局里 1530 拍人均相对值和天然份额比值的秩相关 {rxy:.2f}，和大厅人数的秩相关 {ryz:.2f}（天然份额比值和大厅人数 {rxz:.2f}）；"
          f"扣掉大厅人数以后，天然份额比值的偏秩相关 {part:.2f}")


if __name__ == '__main__':
    main()
