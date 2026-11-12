#!/usr/bin/env python3
"""m6_all_land.py — 全量好地账：把每个对局包的 out/<局>/voronoi_summary.json（voronoi_share.mjs 写）并起来，和 out/_all/joined.csv 对上。

先跑：bash scripts/batch_loop.sh scripts/steps/m6-voronoi-all.txt /tmp/r01_m6d.log（其余有录像的包，一局 1–2 秒）；
      python3 scripts/m6_all_pages.py --csv; python3 scripts/m6_all_replay.py --csv; python3 scripts/m6_all_traj.py --csv; python3 scripts/m6_all_outcomes.py --csv
每局一行：
  natRatio   本队名下的天然陆地占全图几成 ÷ 本队人头占比（1.0 = 落点摊开得和别人一样；0.5 = 十个号挤在一半的地上）
  natMed     每号天然地盘的中位：本队 ÷ 其他真人
  cap630     630 拍吃到自己天然地盘的几成：本队中位 / 其他真人中位
  cap1500    1500 拍：本队中位 / 其他真人中位
  self1500   1500 拍本队各号的天然多边形里，归自己或本队别的号的占比；enemy1500 归敌方真人的占比；husk1500 归离场壳的占比
  aiShare    600 拍的 AI 地到 1800 拍被本队拿到的占比 ÷ 本队人头占比（1.0 = 按人头拿到了该拿的 AI 地）
用法：python3 scripts/m6_all_land.py [--csv] [--list]     --list 逐局列出；末尾按编队汇总，并按“指令通道干净不干净”分开看。
说明：泰森多边形是“谁离得近”的几何切法，不考虑山、水和先手；它回答的是“落点本身给了多少地”，不是“应该拿到多少”。
     录像不到 1510 拍的局没有 1500 拍的列；不是同一场对局的包（平行两场、先后两场，见 m6_match_split.py）不算。
"""
import csv, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
DATA = '/agent/repos/c136-data/bundles'


def main():
    argv = sys.argv[1:]
    jp = os.path.join(R, 'out', '_all', 'joined.csv')
    joined = {r['mid']: r for r in csv.DictReader(open(jp))} if os.path.exists(jp) else {}
    rows = []
    for mid in sorted(os.listdir(DATA)):
        p = os.path.join(R, 'out', mid, 'voronoi_summary.json')
        if not os.path.exists(p):
            continue
        v = json.load(open(p))
        j = joined.get(mid, {})
        if j.get('multi') == '1':     # 不是同一场对局的包（m6_match_split.py）：席位表对不上日志里的号
            continue
        card = json.load(open(os.path.join(DATA, mid, 'card.json')))
        r = {'mid': mid, 'cohort': card['cohort'], 'won': int(bool(card['outcome']['primaryTeamWon'])), 'teams': joined.get(mid, {}).get('teams') or card.get('nominalTeams'),
             'humans': v['humans'], 'squadN': v['squadN'], 'headPct': round(v['headPct'], 2), 'natPct': round(v['squadNatPct'], 2),
             'natRatio': round(v['squadNatPct'] / v['headPct'], 3) if v['headPct'] else None,
             'natMed': round(v['natMedSquad'] / v['natMedOther'], 3) if v.get('natMedOther') else None}
        t6, t15 = v['ticks'].get('630'), v['ticks'].get('1500')
        r['cap630s'] = round(t6['ratioMedSquad'], 3) if t6 else None
        r['cap630o'] = round(t6['ratioMedOther'], 3) if t6 else None
        r['cap1500s'] = round(t15['ratioMedSquad'], 3) if t15 else None
        r['cap1500o'] = round(t15['ratioMedOther'], 3) if t15 else None
        if t15 and t15.get('regionCells'):
            g, n = t15['region'], t15['regionCells']
            r['self1500'] = round((g.get('self', 0) + g.get('squadSameTeam', 0) + g.get('squadOtherTeam', 0)) / n, 3)
            r['enemy1500'] = round(g.get('enemy', 0) / n, 3)
            r['husk1500'] = round(g.get('husk', 0) / n, 3)
        else:
            r['self1500'] = r['enemy1500'] = r['husk1500'] = None
        a = v.get('ai')
        if a and a.get('cellsAll') and a.get('to') == 1800 and v['headPct']:
            sq = sum(c for k, c in a['all'].items() if k.startswith('squad/'))
            r['aiShare'] = round(100 * sq / a['cellsAll'] / v['headPct'], 3)
        else:
            r['aiShare'] = None
        nd = j.get('nd600_1500')
        r['nd600_1500'] = float(nd) if nd not in (None, '') else None
        r['rel1530'] = float(j['rel1530']) if j.get('rel1530') not in (None, '') else None
        rows.append(r)
    f = lambda x: '-' if x is None else (f'{x:.2f}' if isinstance(x, float) else str(x))
    if '--list' in argv:
        print('局 | 编队 赢 | 真人·本队号 | 天然份额/人头占比 | 每号天然地盘 本队/其他 | 630 拍拿到率 本队/其他 | 1500 拍 本队/其他 | 1500 拍自家多边形 归本队/敌方/壳 | AI 地份额/人头占比 | 600–1500 落地/放行')
        for r in rows:
            print(f"{r['mid']} | {r['cohort']} {r['won']} | {r['humans']}·{r['squadN']} | {f(r['natRatio'])} | {f(r['natMed'])} | {f(r['cap630s'])}/{f(r['cap630o'])} | {f(r['cap1500s'])}/{f(r['cap1500o'])} | "
                  f"{f(r['self1500'])}/{f(r['enemy1500'])}/{f(r['husk1500'])} | {f(r['aiShare'])} | {f(r['nd600_1500'])}")
    if '--csv' in argv:
        od = os.path.join(R, 'out', '_all')
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'land.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/land.csv（{len(rows)} 局）')
    # 两种人数口径：card.seededPlayers（录像头的真人数，人均相对值用）对 第 1 拍在场的真人数（好地账用）
    dh = [abs(int(float(joined[r['mid']]['humans'])) - r['humans']) for r in rows if joined.get(r['mid'], {}).get('humans') not in (None, '')]
    nz = [x for x in dh if x >= 1]
    if dh and '--md' not in argv:
        print(f"# 人数口径：{len(dh)} 局里 card.seededPlayers 和第 1 拍在场的真人数相差 ≥ 1 的 {len(nz)} 局（差的中位 {statistics.median(nz) if nz else 0:.0f}，最多 {max(dh)}）")

    def med(L, k):
        v = [r[k] for r in L if r[k] is not None]
        return f'{statistics.median(v):.2f}' if v else '-'

    def line(name, L):
        if not L:
            return
        lo = sum(1 for r in L if r['natRatio'] is not None and r['natRatio'] < 0.75)
        b6 = [r for r in L if r['cap630s'] is not None and r['cap630o'] is not None]
        b15 = [r for r in L if r['cap1500s'] is not None and r['cap1500o'] is not None]
        ai = [r for r in L if r['aiShare'] is not None]
        print(f"   {name:<30s} {len(L):3d} 局（赢 {sum(r['won'] for r in L)}）| 天然份额/人头 中位 {med(L, 'natRatio')}（< 0.75 的 {lo} 局）· 每号天然地盘 本队/其他 {med(L, 'natMed')} | "
              f"630 拍拿到率 本队 {med(L, 'cap630s')} / 其他 {med(L, 'cap630o')}（本队 ≥ 其他的 {sum(1 for r in b6 if r['cap630s'] >= r['cap630o'])}/{len(b6)} 局）| "
              f"1500 拍 本队 {med(L, 'cap1500s')} / 其他 {med(L, 'cap1500o')}（本队 ≥ 其他的 {sum(1 for r in b15 if r['cap1500s'] >= r['cap1500o'])}/{len(b15)} 局）| "
              f"自家多边形 1500 拍归本队 {med(L, 'self1500')}、敌方 {med(L, 'enemy1500')}、壳 {med(L, 'husk1500')} | AI 地份额/人头 {med(L, 'aiShare')}（≥ 1 的 {sum(1 for r in ai if r['aiShare'] >= 1)}/{len(ai)} 局）| 1530 拍人均相对值 {med(L, 'rel1530')}")

    if '--md' in sys.argv:
        print('| 组 | 局数（主队赢） | 天然份额 ÷ 人头占比 | 每号天然地盘：本队 ÷ 其他真人 | 630 拍吃到率：本队 / 其他真人 | 1500 拍吃到率：本队 / 其他真人（本队不低于其他的局数） | 1500 拍本队多边形里归本队的 | 本队拿到的 AI 地份额 ÷ 人头占比 | 1530 拍人均相对值 |')
        print('|---|---|---|---|---|---|---|---|---|')
        for co in ('squad10', 'squad20'):
            L = [r for r in rows if r['cohort'] == co]
            for name, G in ((f'{co} 全部', L),
                            ('　通道干净（600–1500 落地/放行 ≥ 0.9）', [r for r in L if r['nd600_1500'] is not None and r['nd600_1500'] >= 0.9]),
                            ('　中间（0.7–0.9）', [r for r in L if r['nd600_1500'] is not None and 0.7 <= r['nd600_1500'] < 0.9]),
                            ('　通道差（< 0.7）', [r for r in L if r['nd600_1500'] is not None and r['nd600_1500'] < 0.7]),
                            ('　主队赢', [r for r in L if r['won']]),
                            ('　主队没赢', [r for r in L if not r['won']])):
                if not G:
                    continue
                b15 = [r for r in G if r['cap1500s'] is not None and r['cap1500o'] is not None]
                print(f"| {name} | {len(G)}（{sum(r['won'] for r in G)}） | {med(G, 'natRatio')} | {med(G, 'natMed')} | {med(G, 'cap630s')} / {med(G, 'cap630o')} | "
                      f"{med(G, 'cap1500s')} / {med(G, 'cap1500o')}（{sum(1 for r in b15 if r['cap1500s'] >= r['cap1500o'])}/{len(b15)}） | {med(G, 'self1500')} | {med(G, 'aiShare')} | {med(G, 'rel1530')} |")
        return

    for co in ('squad10', 'squad20'):
        L = [r for r in rows if r['cohort'] == co]
        print(f'#### {co}：{len(L)} 局有好地账')
        line('全部', L)
        line('通道干净（600–1500 ≥ 0.9）', [r for r in L if r['nd600_1500'] is not None and r['nd600_1500'] >= 0.9])
        line('中间（0.7–0.9）', [r for r in L if r['nd600_1500'] is not None and 0.7 <= r['nd600_1500'] < 0.9])
        line('通道差（< 0.7）', [r for r in L if r['nd600_1500'] is not None and r['nd600_1500'] < 0.7])
        line('天然份额/人头 < 0.6', [r for r in L if r['natRatio'] is not None and r['natRatio'] < 0.6])
        line('0.6–0.9', [r for r in L if r['natRatio'] is not None and 0.6 <= r['natRatio'] < 0.9])
        line('≥ 0.9', [r for r in L if r['natRatio'] is not None and r['natRatio'] >= 0.9])
        line('主队赢', [r for r in L if r['won']])
        line('主队没赢', [r for r in L if not r['won']])
        # 通道干净的局里，落点挤不挤和 1530 拍人均相对值
        C = [r for r in L if r['nd600_1500'] is not None and r['nd600_1500'] >= 0.9 and r['natRatio'] is not None and r['rel1530'] is not None]
        if len(C) >= 6:
            C.sort(key=lambda r: r['natRatio'])
            h = len(C) // 2
            print(f"   通道干净的 {len(C)} 局按天然份额/人头排：低的一半 中位 {statistics.median(r['natRatio'] for r in C[:h]):.2f} → 1530 拍人均相对值中位 {statistics.median(r['rel1530'] for r in C[:h]):.2f}；"
                  f"高的一半 {statistics.median(r['natRatio'] for r in C[h:]):.2f} → {statistics.median(r['rel1530'] for r in C[h:]):.2f}")

        def spearman(P):
            def rank(v):
                order = sorted(range(len(v)), key=lambda i: v[i])
                out = [0.0] * len(v)
                i = 0
                while i < len(order):
                    j = i
                    while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                        j += 1
                    for k in range(i, j + 1):
                        out[order[k]] = (i + j) / 2
                    i = j + 1
                return out
            if len(P) < 6:
                return None
            rx, ry = rank([p[0] for p in P]), rank([p[1] for p in P])
            mx, my = statistics.mean(rx), statistics.mean(ry)
            den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
            return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / den if den else None

        def corr(name, L2, kx, ky):
            P = [(r[kx], r[ky]) for r in L2 if r[kx] is not None and r[ky] is not None]
            s = spearman(P)
            if s is not None:
                print(f'   秩相关 {name}：{len(P)} 局，ρ = {s:.2f}')

        corr('通道干净的局里 天然份额/人头 × 1530 拍人均相对值', C, 'natRatio', 'rel1530')
        corr('全部局 600–1500 落地/放行 × 1530 拍人均相对值', L, 'nd600_1500', 'rel1530')
        corr('全部局 600–1500 落地/放行 × 1500 拍本队拿到率', L, 'nd600_1500', 'cap1500s')
        corr('全部局 600–1500 落地/放行 × AI 地份额/人头', L, 'nd600_1500', 'aiShare')
        corr('全部局 天然份额/人头 × 1530 拍人均相对值', L, 'natRatio', 'rel1530')


if __name__ == '__main__':
    main()
