#!/usr/bin/env python3
"""m6_all_lobby.py — 线上的大厅长什么样（给模拟器配大厅用），和页面决策耗时 × 通道。

读 out/_all/joined.csv（m6_all_outcomes.py 写）、out/<局>/voronoi_seats.csv（好地账的席位表：第 1 拍在场的每个真人席位的
队号、是否本队、630 / 1500 拍的状态）、bundles/<局>/traj.csv（页面每 90 拍记一次的累计平均决策耗时 avgMs）。
不是同一场对局的 15 个包不计。

  1. 大厅：真人数、有真人的队数、本队所在的队有多少真人、本队席位占所在队和占全场的比例；
  2. 其他真人到 630 / 1500 拍的去向：在场、已离场（席位成了壳）、已阵亡；
  3. 决策耗时：把累计平均还原成各时段的增量平均，按 600–1500 拍的落地率分三组；和落地率的秩相关；
  4. 给模拟器对账用的一张表：按通道分三组，线上跑的版本的批次占比、重复占比、天然份额、吃到率、人均相对值、被移出的席位。

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


if __name__ == '__main__':
    main()
