#!/usr/bin/env python3
# enemy_strike_fate.py — 敌方真人打我方号的每一轮进攻最后怎么收场：打光了、目标没地了，还是「没地可打、兵退回去」。
# 起因：船登陆在我方号的小岛上时，一发几十万兵只吃掉那座小岛，剩下的兵回到出手方余额里；
#       只数「对我方号出了多少兵」会把这种退回的兵也算成压在我方号身上的兵。
# 用法：python3 scripts/enemy_strike_fate.py <局号> [t0 t1] [--ours id,id,…] [--list] [--min 50000]
# 口径（全部来自真引擎重放 tmp/truth/<局号>/）：
#   一轮进攻 = atk.tsv（每 10 拍一行的在途进攻兵）里同一对「出手方 → 我方号」连续有在途兵的一段（中间断 ≤10 拍算同一段）；
#   投入     = 这一段里出手方对这个号的陆攻指令登记的兵 + 船登陆后的进攻兵（cmd.tsv / ev.tsv，同 incoming_tally.py）；
#   收场     = 段尾那一行的在途兵 last，以及段尾之后第一行（+10 拍）的情况：
#              目标没地了   我方号在段尾 +10 拍时领土为 0（或已出局）；
#              退回         目标还有地，last ≥ max(--min, 投入的 20%)，且出手方余额在这 10 拍里涨了 ≥ 0.7×last；
#              打光         其余（在途兵被守方的兵和对冲耗完，或剩下不多）。
#   退回的兵 = 收场为「退回」的段的 last；真正压在我方号身上的兵 ≈ 投入 − 退回的兵。
#   这一段里目标丢的地 = 段首前一行到段尾后一行我方号领土的变化（同期被别人拿走的也在内）。
# 输出：按出手方合计（段数 / 投入 / 退回 / 目标没地了的段数），按我方号合计；--list 逐段列出（投入 ≥ --min 的）。
import sys, collections, bisect
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    vmin = int(a[a.index('--min') + 1]) if '--min' in a else 50000
    skip = set()
    for k in ('--ours', '--min'):
        if k in a:
            skip.add(a.index(k) + 1)
    pos = [x for i, x in enumerate(a) if i >= 1 and not x.startswith('--') and i not in skip]
    t0, t1 = (int(pos[0]), int(pos[1])) if len(pos) >= 2 else (0, 10 ** 9)
    M = Match(mid, ours)
    step = M.step

    def troops(c):
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')

    strikes = collections.defaultdict(list)   # (p,q) -> [(t, 兵, 是否船)]
    for c in M.cmd:
        if c['id'] != 1:
            continue
        s = troops(c)
        if s > 0 and c['b'] in M.ours and c['p'] < M.ku and M.team.get(c['p']) != M.our_team:
            strikes[(c['p'], c['b'])].append((c['t'], s, False))
    for (t, kind, p, x, y, det) in M.ev:
        if kind != 'land' or '|' not in det:
            continue
        for part in det.split('|', 1)[1].split(';'):
            f = part.split(':')
            if f[0] == 'atk' and len(f) >= 3 and int(f[2]) > 0 and int(f[1]) in M.ours and p < M.ku and M.team.get(p) != M.our_team:
                strikes[(p, int(f[1]))].append((t, int(f[2]), True))
    series = collections.defaultdict(list)
    for (t, p, q, s) in M.atk:
        if q in M.ours and p < M.ku and M.team.get(p) != M.our_team and s > 0:
            series[(p, q)].append((t, s))

    def st(p, t):
        s = M.state[M.at(max(0, t))].get(p)
        return (s[0], s[1]) if s else (0, 0)

    eps = []
    miss = []      # 没有落进任何一轮的出手
    allin = []
    for (p, q), sarr in strikes.items():
        arr = sorted(series.get((p, q), []))
        segs = []
        if arr:
            seg = [arr[0]]
            for x in arr[1:]:
                if x[0] - seg[-1][0] <= 2 * step:
                    seg.append(x)
                else:
                    segs.append(seg); seg = [x]
            segs.append(seg)
        own = [[] for _ in segs]
        for x in sorted(sarr):
            k = next((i for i, sg in enumerate(segs) if sg[0][0] - step <= x[0] <= sg[-1][0]), None)
            if k is None:
                k = next((i for i, sg in enumerate(segs) if sg[-1][0] < x[0] < sg[-1][0] + step), None)
            if k is None:
                if t0 <= x[0] <= t1:
                    miss.append((p, q, x)); allin.append((p, q, x))
                continue
            own[k].append(x)
        for seg, ss in zip(segs, own):
            ta, tb = seg[0][0], seg[-1][0]
            if not (t0 <= ta <= t1):
                continue
            allin.extend((p, q, x) for x in ss)
            put = sum(x[1] for x in ss)
            last = seg[-1][1]
            q_after = st(q, tb + step)
            p_b, p_a = st(p, tb), st(p, tb + step)
            q_before = st(q, ta - step)
            if tb + step > M.last:
                fate = '录像结束'
            elif q_after[0] <= 0:
                fate = '目标没地了'
            elif last >= max(vmin, 0.2 * put) and p_a[1] - p_b[1] >= 0.7 * last:
                fate = '退回'
            else:
                fate = '打光'
            eps.append(dict(p=p, q=q, ta=ta, tb=tb, put=put, n=len(ss), boats=sum(1 for x in ss if x[2]), boat_put=sum(x[1] for x in ss if x[2]),
                            last=last, fate=fate, dterr=q_after[0] - q_before[0], jump=p_a[1] - p_b[1], peak=max(x[1] for x in seg)))
    rng = f'[{t0},{t1}]' if t1 < 10 ** 9 else '全局'
    print(f'# {mid} {rng} 敌方真人对我方号的每一轮进攻怎么收场（在途兵每 10 拍一行；投入 = 指令登记的兵 + 船登陆的兵）')
    tot = collections.Counter()
    for e in eps:
        tot['put'] += e['put']; tot['n'] += 1
        if e['fate'] == '退回':
            tot['ref'] += e['last']; tot['nref'] += 1
            tot['ref_boat'] += e['last'] if e['boats'] else 0
        if e['fate'] == '目标没地了':
            tot['nkill'] += 1; tot['kill_left'] += e['last']
    print(f'合计 {tot["n"]} 轮，投入 {fmt(tot["put"])} 兵；其中「退回」{tot["nref"]} 轮、退回 {fmt(tot["ref"])} 兵（有船登陆的轮里退回 {fmt(tot["ref_boat"])}）；'
          f'「目标没地了」{tot["nkill"]} 轮，收场时还剩在途兵 {fmt(tot["kill_left"])}；真正耗在我方号身上的兵 ≈ {fmt(tot["put"] - tot["ref"] - tot["kill_left"])}')
    print(f'对账：按「一轮的起点在拍段里」算，敌方真人对我方号一共 {len(allin)} 发 {fmt(sum(z[2][1] for z in allin))} 兵；其中 {len(miss)} 发 {fmt(sum(z[2][1] for z in miss))} 兵在两行快照之间就结束了，没有落进任何一轮（不计入上面的投入）')
    byp = collections.defaultdict(collections.Counter)
    byq = collections.defaultdict(collections.Counter)
    for e in eps:
        for d, k in ((byp, e['p']), (byq, e['q'])):
            d[k]['n'] += 1; d[k]['put'] += e['put']
            if e['fate'] == '退回':
                d[k]['ref'] += e['last']; d[k]['nref'] += 1
            if e['fate'] == '目标没地了':
                d[k]['nkill'] += 1; d[k]['left'] += e['last']
            d[k]['dterr'] += e['dterr']
    print('按出手方（轮 / 投入 / 退回的轮·兵 / 目标没地了的轮·剩兵）：')
    for p, c in sorted(byp.items(), key=lambda kv: -kv[1]['put']):
        print(f'  {M.nm(p)}：{c["n"]} 轮，投入 {fmt(c["put"])}；退回 {c["nref"]} 轮 {fmt(c["ref"])}；目标没地了 {c["nkill"]} 轮（剩 {fmt(c["left"])}）')
    print('按我方号（轮 / 投入 / 其中退回 / 各轮期间领土变化合计）：')
    for q, c in sorted(byq.items(), key=lambda kv: -kv[1]['put']):
        print(f'  {M.nm(q):8s} {c["n"]} 轮，投入 {fmt(c["put"])}；退回 {c["nref"]} 轮 {fmt(c["ref"])}；领土变化合计 {c["dterr"]:+d}')
    if '--list' in a:
        print(f'逐轮（投入 ≥ {vmin}）：')
        for e in sorted(eps, key=lambda e: e['ta']):
            if e['put'] < vmin:
                continue
            print(f'  拍 {e["ta"]}~{e["tb"]} {M.nm(e["p"])} → {M.nm(e["q"])}：{e["n"]} 发 {fmt(e["put"])}（船 {e["boats"]} 发 {fmt(e["boat_put"])}），在途峰值 {fmt(e["peak"])}，段尾在途 {fmt(e["last"])}，'
                  f'{e["fate"]}（出手方余额这 10 拍 {e["jump"]:+d}）；这一轮期间目标领土 {e["dterr"]:+d}')


if __name__ == '__main__':
    main()
