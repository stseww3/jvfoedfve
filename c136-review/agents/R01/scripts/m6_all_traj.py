#!/usr/bin/env python3
"""m6_all_traj.py — 全量机械计数（123 个对局包，只读 traj.csv / events.csv / results.csv / card.json）：
页面自己每 90 拍写的快照（HL-TICK：terr、bal、dens、nb、neut、cmds）里，各号有多少时间是“有地可打却一条令不发”“没有任何可打对象”“满仓”。

字段含义（策略源码 HL-TICK 行）：nb = 可陆攻的邻居个数（同队和受保护的席位不算），neut = 接壤的无主地格数，cmds = 页面累计放行的指令数（陆攻+捐兵+船）。
捐兵行（events.csv 的 DISPATCH/DONATE）从 cmds 增量里扣掉，剩下的是“陆攻+船”的放行数。

每局按三个时段（本地拍 600–1500 / 1500–3000 / 3000+）数“快照对”（同一个号相邻两个快照 t → t+90，起点落在时段内）：
  pairs      快照对总数
  boxed      起点 nb=0 且 neut=0（陆上没有任何可打对象）                               → SP01 / EC01 / EC03
  idleTgt    起点 nb>0 或 neut>0，而这 90 拍里放行的陆攻+船 = 0（有对象、18 个决策拍一条不发）  → OP02 / OP05 / AT05 / DF03 的上限
  idleNeut   其中起点 neut>0（身边还有无主地）
  full       起点 dens ≥ 100（过了 100 倍领土，利息开始打折）
  boxedFull  起点 nb=0、neut=0 且 dens ≥ 95（anomalies.json 的 boxedHighDens 口径，只在 1500 拍后有意义）  → EC01
  cmdRate    每个快照对平均放行的陆攻+船条数
另外：
  drop30     card 的 drop30Count（90 拍内余额掉 ≥30% 的次数）
  don / rej  events.csv 的捐兵行数、其中 likelyRejected 的行数；3213 拍前、3213–4284、4284 拍后三段  → DN05
  doomed     捐兵对象在这笔之后 400 拍内写了 died 的 RESULT 行的笔数（两边都是本地拍）               → DN04
  smallPct   pct < 150 的捐兵行数（手续费按捐出方全部余额的 64/1024 收，捐得越少税率越高：pct 150 ≈ 30%）
  d1/d2/d3_* 相邻两个快照（90 拍）余额掉 ≥30%（起点余额 ≥1000）的次数，按起点拍分 1500 前 / 1500–3000 / 3000 后，再按同一区间里发生了什么分四类（依次判）：
             lost = 领土同时掉 ≥3%（在挨打）；don = 没丢地、区间里有没被标 likelyRejected 的捐兵行；cmd = 没丢地、只放行了陆攻/船（cmdGain = 其中领土涨 ≥3%）；
             none = 这 90 拍页面一条指令也没放行（余额是被更早放行、现在才落地的令划走的，或被别人的船/陆攻换掉而领土没掉到 3%）   → IO02 / DN / AT08 的全量上限
用法：python3 scripts/m6_all_traj.py [局号 ...] [--csv]      不给局号 = 全部；--csv 写 out/_all/traj.csv。末尾按编队 × 输赢汇总。
说明：这是只靠日志的上限估计——“有对象不发令”不区分保底线、价格线还是在等 DP 租期；逐拍的原因要用影子策略（attrib3.py、shadow_report --section idle）。
"""
import csv, json, os, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/agent/repos/c136-data/bundles'
PHASES = (('p1', 600, 1500), ('p2', 1500, 3000), ('p3', 3000, 10 ** 9))


def one(mid):
    card = json.load(open(os.path.join(DATA, mid, 'card.json')))
    tp = os.path.join(DATA, mid, 'traj.csv')
    if not os.path.exists(tp):
        return None
    snaps = defaultdict(list)
    for x in csv.DictReader(open(tp)):
        try:
            snaps[x['bot']].append((int(x['t']), int(x['cmds']), int(x['nb']), int(x['neut']), float(x['dens']), int(x['terr']), int(x['bal'])))
        except ValueError:
            continue
    don = defaultdict(list)
    don_ok = defaultdict(list)
    ev = []
    ep = os.path.join(DATA, mid, 'events.csv')
    if os.path.exists(ep):
        for e in csv.DictReader(open(ep)):
            if e['type'] in ('DISPATCH', 'DONATE'):
                try:
                    t = int(e['t'])
                except ValueError:
                    continue
                don[e['bot']].append(t)
                if e['likelyRejected'] != 'True':
                    don_ok[e['bot']].append(t)
                try:
                    pc = int(e['pct'])
                except (ValueError, KeyError):
                    pc = None
                ev.append((t, e['bot'], e['targetName'], e['likelyRejected'] == 'True', pc))
    died = {}
    rp = os.path.join(DATA, mid, 'results.csv')
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp)):
            if r['event'] == 'died':
                try:
                    died[r['bot']] = float(r['tick'])
                except ValueError:
                    pass
    out = {'mid': mid, 'cohort': card['cohort'], 'result': card['outcome']['resultLabel'], 'won': int(bool(card['outcome']['primaryTeamWon'])),
           'teams': card.get('actualTeams'), 'drop30': card['anomaliesSummary'].get('drop30Count')}
    acc = {k: defaultdict(float) for k, _, _ in PHASES}
    d30 = {k: defaultdict(int) for k in ('d1', 'd2', 'd3')}
    for bot, L in snaps.items():
        for i in range(1, len(L)):
            t0, c0, nb, neut, dens, terr0, bal0 = L[i - 1]
            t1, c1, terr1, bal1 = L[i][0], L[i][1], L[i][5], L[i][6]
            if t1 - t0 != 90:      # 快照缺口、或一个包里的第二场
                continue
            dn = sum(1 for t in don.get(bot, []) if t0 < t <= t1)
            nd = max(0, (c1 - c0) - dn)
            if bal0 >= 1000 and bal1 <= 0.7 * bal0:
                D = d30['d1' if t0 < 1500 else ('d2' if t0 < 3000 else 'd3')]
                D['n'] += 1
                if terr1 < 0.97 * terr0:
                    D['lost'] += 1
                elif any(t0 < t <= t1 for t in don_ok.get(bot, [])):
                    D['don'] += 1
                elif nd > 0:
                    D['cmd'] += 1
                    if terr1 > 1.03 * terr0:
                        D['cmdGain'] += 1
                else:
                    D['none'] += 1
            for k, a, b in PHASES:
                if a <= t0 < b:
                    A = acc[k]
                    A['pairs'] += 1
                    A['cmd'] += nd
                    if nb == 0 and neut == 0:
                        A['boxed'] += 1
                        if dens >= 95:
                            A['boxedFull'] += 1
                    elif nd == 0:
                        A['idleTgt'] += 1
                        if neut > 0:
                            A['idleNeut'] += 1
                    if dens >= 100:
                        A['full'] += 1
    for k, _, _ in PHASES:
        A = acc[k]
        n = A['pairs']
        out[f'{k}_pairs'] = int(n)
        for key in ('boxed', 'idleTgt', 'idleNeut', 'full', 'boxedFull'):
            out[f'{k}_{key}'] = round(A[key] / n, 3) if n else None
        out[f'{k}_cmdRate'] = round(A['cmd'] / n, 2) if n else None
    for k in ('d1', 'd2', 'd3'):
        for key in ('n', 'lost', 'don', 'cmd', 'cmdGain', 'none'):
            out[f'{k}_{key}'] = d30[k][key]
    for name, a, b in (('q1', 0, 3213), ('q2', 3213, 4284), ('q3', 4284, 10 ** 9)):
        L = [e for e in ev if a <= e[0] < b]
        out[f'{name}_don'] = len(L)
        out[f'{name}_rej'] = sum(1 for e in L if e[3])
    out['doomed'] = sum(1 for t, b, tgt, rj, pc in ev if tgt in died and 0 <= died[tgt] - t <= 400)
    out['don'] = len(ev)
    # 小额捐兵：pct < 150（捐不到余额的 15%，手续费按全部余额的 64/1024 收 → 税率 ≥ 30%）
    out['smallPct'] = sum(1 for e in ev if e[4] is not None and e[4] < 150)
    return out


def main():
    argv = sys.argv[1:]
    mids = [x for x in argv if not x.startswith('--')] or sorted(os.listdir(DATA))
    rows = [r for r in (one(m) for m in mids) if r]
    f = lambda x: '-' if x is None else (f'{100 * x:.0f}%' if isinstance(x, float) else str(x))
    print('局 | 编队 结果 | 600–1500：对数 / 没对象 / 有对象不发令（其中身边有无主地）/ 每对放行 | 1500–3000：对数 / 没对象 / 有对象不发令 / 满仓 / 没对象且满仓 | 3000+：同前 | 捐兵行（疑似被拒）<3213 / 3213–4284 / ≥4284 | 给 400 拍内阵亡的号')
    for r in rows:
        print(f"{r['mid']} | {r['cohort']} {r['result']} | {r['p1_pairs']} / {f(r['p1_boxed'])} / {f(r['p1_idleTgt'])}（{f(r['p1_idleNeut'])}）/ {r['p1_cmdRate']} | "
              f"{r['p2_pairs']} / {f(r['p2_boxed'])} / {f(r['p2_idleTgt'])} / {f(r['p2_full'])} / {f(r['p2_boxedFull'])} | "
              f"{r['p3_pairs']} / {f(r['p3_boxed'])} / {f(r['p3_idleTgt'])} / {f(r['p3_full'])} / {f(r['p3_boxedFull'])} | "
              f"{r['q1_don']}（{r['q1_rej']}）/ {r['q2_don']}（{r['q2_rej']}）/ {r['q3_don']}（{r['q3_rej']}）| {r['doomed']}")
    if '--csv' in argv:
        od = os.path.join(HERE, '..', 'out', '_all')
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'traj.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/traj.csv（{len(rows)} 局）')
    print('# 汇总（各局比例的中位数；括号里是把所有局的快照对合在一起算的比例）')
    for co in sorted({r['cohort'] for r in rows}):
        for won in (1, 0):
            L = [r for r in rows if r['cohort'] == co and r['won'] == won]
            if not L:
                continue

            def med(k):
                v = [r[k] for r in L if r[k] is not None]
                return f'{100 * statistics.median(v):.0f}%' if v else '-'

            def pooled(k, ph):
                n = sum(r[f'{ph}_pairs'] for r in L)
                return f"{100 * sum((r[f'{ph}_{k}'] or 0) * r[f'{ph}_pairs'] for r in L) / n:.0f}%" if n else '-'
            print(f"#   {co} {'主队赢' if won else '主队没赢'} {len(L)} 局：600–1500 没对象 {med('p1_boxed')}（{pooled('boxed', 'p1')}），有对象不发令 {med('p1_idleTgt')}（{pooled('idleTgt', 'p1')}）；"
                  f"1500–3000 没对象 {med('p2_boxed')}（{pooled('boxed', 'p2')}），有对象不发令 {med('p2_idleTgt')}（{pooled('idleTgt', 'p2')}），满仓 {med('p2_full')}（{pooled('full', 'p2')}），没对象且满仓 {med('p2_boxedFull')}（{pooled('boxedFull', 'p2')}）；"
                  f"3000+ 有对象不发令 {med('p3_idleTgt')}（{pooled('idleTgt', 'p3')}），满仓 {med('p3_full')}（{pooled('full', 'p3')}）")
        L = [r for r in rows if r['cohort'] == co]
        d1, j1 = sum(r['q1_don'] for r in L), sum(r['q1_rej'] for r in L)
        d2, j2 = sum(r['q2_don'] for r in L), sum(r['q2_rej'] for r in L)
        d3, j3 = sum(r['q3_don'] for r in L), sum(r['q3_rej'] for r in L)
        pc = lambda a, b: f'{100 * a / b:.0f}%' if b else '-'
        print(f"#   {co} 捐兵行：3213 拍前 {d1} 行（疑似被拒 {j1} = {pc(j1, d1)}），3213–4284 拍 {d2} 行（{j2} = {pc(j2, d2)}），4284 拍后 {d3} 行（{j3} = {pc(j3, d3)}）；"
              f"对象 400 拍内阵亡的 {sum(r['doomed'] for r in L)} 行（{pc(sum(r['doomed'] for r in L), sum(r['don'] for r in L))}）；"
              f"pct < 150 的 {sum(r['smallPct'] for r in L)} 行（{pc(sum(r['smallPct'] for r in L), sum(r['don'] for r in L))}）")
        for k, nm in (('d1', '1500 拍前'), ('d2', '1500–3000'), ('d3', '3000 拍后')):
            n = sum(r[f'{k}_n'] for r in L)
            g = lambda key: sum(r[f'{k}_{key}'] for r in L)
            print(f"#   {co} 90 拍内余额掉 ≥30%（{nm}）：{n} 次 = 同时丢地 ≥3% 的 {g('lost')}（{pc(g('lost'), n)}）+ 没丢地、有没被拒的捐兵行 {g('don')}（{pc(g('don'), n)}）"
                  f" + 没丢地、只放行了陆攻/船 {g('cmd')}（{pc(g('cmd'), n)}；其中领土涨 ≥3% 的 {g('cmdGain')}）+ 这 90 拍一条没放行 {g('none')}（{pc(g('none'), n)}）")


if __name__ == '__main__':
    main()
