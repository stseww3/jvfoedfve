#!/usr/bin/env python3
# thin_after_spend.py — NEW-DF-THIN 的机械口径：自己花兵把密度压到 20 以下，随后 300 拍内被敌方真人拿走 ≥25% 的地或出局。
# 用法：python3 scripts/thin_after_spend.py <局号> [--ours id,id,…] [--dens 20] [--pre 90] [--post 300] [--from 630] [--all]
#   --from：只看这一拍之后的变薄点（开局头几百拍人人密度都低，不算）。
# 数据：tmp/truth/<局号>/（真引擎重放的 our.tsv / cmd.tsv / flow.tsv / ev.tsv）。
# 口径：
#   变薄点 = 某号的采样拍 t（每 10 拍一个），余额 < dens×领土，而 t−pre 拍时余额 ≥ dens×领土（从线上掉到线下）；
#   自己花的 = (t−pre, t] 该号的陆攻 / 捐款 / 发船指令让余额少掉的量（含手续费和税）；≥ 这段时间余额跌幅的一半才算「自己花薄的」；
#   后果 = (t, t+post] 内出局，或被敌方真人净拿走的地 ≥ 变薄点领土的 25%（flow.tsv，只算非队友真人）。
#   同一个号一次变薄只记一次（余额回到线上之后才重新计）。
# 输出：每个变薄点一行（默认只列有后果的；--all 全列），最后一行合计。
import sys, collections, bisect
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    ours = [int(x) for x in opt('--ours', '').split(',')] if '--ours' in a else None
    dens = float(opt('--dens', 20)); pre = int(opt('--pre', 90)); post = int(opt('--post', 300))
    t_from = int(opt('--from', 630))
    show_all = '--all' in a
    M = Match(mid, ours)
    spend = collections.defaultdict(list)  # p -> [(t, drop, id)]
    for c in M.cmd:
        if c['p'] in M.ours and c['id'] in (1, 2, 3):
            spend[c['p']].append((c['t'], c['bal0'] - c['bal1'], c['id']))
    flows = collections.defaultdict(list)  # p -> [(t, to, px)] / 负数 = 拿回来
    for (t, x, y, px) in M.flow:
        if x in M.ours and y < M.ku and M.team[y] != M.team[x]:
            flows[x].append((t, y, px))
        if y in M.ours and x < M.ku and M.team[x] != M.team[y]:
            flows[y].append((t, x, -px))
    print(f'# {mid} 自己花兵后变薄（密度 < {dens:g}）的时刻与随后 {post} 拍的后果')
    n_all = n_bad = 0
    for p in M.our_ids:
        ser = M.our[p]
        ts = sorted(ser)
        armed = True
        for t in ts:
            terr, bal = ser[t][0], ser[t][1]
            if terr <= 0 and t > t_from:
                break
            if t < t_from or bal >= dens * terr:
                armed = True
                continue
            if not armed:
                continue
            k = bisect.bisect_right(ts, t - pre) - 1
            if k < 0:
                continue
            t0 = ts[k]
            terr0, bal0 = ser[t0][0], ser[t0][1]
            if bal0 < dens * terr0:
                continue
            armed = False
            own = sum(d for (tc, d, i) in spend[p] if t0 < tc <= t)
            kinds = collections.Counter(i for (tc, d, i) in spend[p] if t0 < tc <= t)
            if bal >= bal0 or own <= 0 or own < 0.5 * (bal0 - bal):
                continue
            n_all += 1
            dead = M.dead.get(p)
            died = dead is not None and t < dead[0] <= t + post
            lost = collections.Counter()
            for (tf, q, px) in flows[p]:
                if t < tf <= t + post:
                    lost[q] += px
            net = sum(v for v in lost.values())
            bad = died or net >= 0.25 * terr
            if bad:
                n_bad += 1
            if not (bad or show_all):
                continue
            who = '，'.join(f'{M.nm(q)} {v}' for q, v in lost.most_common(3) if v > 0)
            km = {1: '陆攻', 2: '捐款', 3: '发船'}
            ks = '、'.join(f'{km[i]} {n} 条' for i, n in sorted(kinds.items()))
            tail = (f'{dead[0]} 拍出局' if died else '没有出局') + f'；被敌方真人净拿走 {net} 格（{100 * net / max(1, terr):.0f}%' + (f'：{who}' if who else '') + '）'
            print(f'  {M.ours[p]:7s} 拍 {t}：余额 {fmt(bal0)}→{fmt(bal)}（{t0} 拍密度 {bal0 / max(1, terr0):.0f} → {bal / max(1, terr):.1f}，领土 {terr}）；这 {pre} 拍自己花掉 {fmt(own)}（{ks}）；随后 {post} 拍：{tail}' + ('' if bad else ' [无后果]'))
    print(f'合计：自己花薄的 {n_all} 次，其中随后 {post} 拍内出局或丢地 ≥25% 的 {n_bad} 次')


if __name__ == '__main__':
    main()
