#!/usr/bin/env python3
# incoming_tally.py — 一个拍段里「谁打了我方号、我方号打了谁」的总账（陆攻指令 + 船登陆后的进攻）。
# 用法：python3 scripts/incoming_tally.py <局号> <t0> <t1> [--ours id,id,…] [--by-target]
#   口径同 enemy_ledger.py：兵 = 进攻槽登记的兵（不含手续费）；船登陆 = ev.tsv 的 land 事件里的 atk 项。
#   输出：
#     1) 敌方真人按队、按人：对我方号出了几发多少兵（其中船登陆几发多少兵）、打的是哪几个号；
#        同一拍段里我方号对这个人出了几发多少兵；这个人拍段两端的 领土 / 余额。
#     2) 我方号按号：挨了几发多少兵（几个不同的敌方真人）、自己对真人出了多少兵、收到捐款多少、拍段两端的 领土 / 余额。
#     3) 合计：敌方对我方号出兵 ÷ 我方号对敌方真人出兵；我方队在这个拍段的地块净流动（flow.tsv）。
#   --by-target 再按「出手方 → 挨打的号」逐对列出。
import sys, collections
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    pos = [x for x in a[1:] if not x.startswith('--')]
    if ours is not None:
        pos = [x for x in pos if x != a[a.index('--ours') + 1]]
    t0, t1 = int(pos[0]), int(pos[1])
    M = Match(mid, ours)

    def troops(c):
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')

    strikes = []   # (t, 出手方, 目标, 兵, 是否船登陆)
    for c in M.cmd:
        if c['id'] != 1 or not (t0 < c['t'] <= t1):
            continue
        s = troops(c)
        if s > 0 and 0 <= c['b'] < M.ku:
            strikes.append((c['t'], c['p'], c['b'], s, False))
    for (t, kind, p, x, y, det) in M.ev:
        if kind != 'land' or '|' not in det or not (t0 < t <= t1):
            continue
        for part in det.split('|', 1)[1].split(';'):
            f = part.split(':')
            if f[0] == 'atk' and len(f) >= 3 and int(f[2]) > 0 and 0 <= int(f[1]) < M.ku:
                strikes.append((t, p, int(f[1]), int(f[2]), True))
    dons = collections.Counter()
    for c in M.cmd:
        if c['id'] == 2 and t0 < c['t'] <= t1 and c.get('q') in M.ours and 'balQ1' in c:
            dons[c['q']] += max(0, c['balQ1'] - c['balQ0'])

    def st(p, t):
        s = M.state[M.at(t)].get(p)
        return (s[0], s[1]) if s else (0, 0)

    inc = collections.defaultdict(lambda: [0, 0, 0, 0, collections.Counter()])  # 敌方 p -> [发, 兵, 船发, 船兵, 目标计数]
    out = collections.defaultdict(lambda: [0, 0])                                # 敌方 p -> 我方对它 [发, 兵]
    got = collections.defaultdict(lambda: [0, 0, set()])                         # 我方号 -> [发, 兵, 出手方集合]
    sent = collections.defaultdict(lambda: [0, 0])                               # 我方号 -> 对敌方真人 [发, 兵]
    pair = collections.defaultdict(lambda: [0, 0])
    for (t, p, q, s, boat) in strikes:
        if q in M.ours and p < M.ku and M.team.get(p) != M.our_team:
            e = inc[p]; e[0] += 1; e[1] += s; e[4][q] += s
            if boat:
                e[2] += 1; e[3] += s
            g = got[q]; g[0] += 1; g[1] += s; g[2].add(p)
            pair[(p, q)][0] += 1; pair[(p, q)][1] += s
        elif p in M.ours and q < M.ku and M.team.get(q) != M.our_team:
            out[q][0] += 1; out[q][1] += s
            sent[p][0] += 1; sent[p][1] += s
    print(f'# {mid} 拍段 ({t0},{t1}] 对打总账（陆攻指令 + 船登陆后的进攻；兵不含手续费）')
    tin = sum(v[1] for v in inc.values()); tout = sum(v[1] for v in out.values())
    print(f'敌方真人对我方号：{sum(v[0] for v in inc.values())} 发 {fmt(tin)} 兵（其中船登陆 {sum(v[2] for v in inc.values())} 发 {fmt(sum(v[3] for v in inc.values()))} 兵），出手的敌方真人 {len(inc)} 个；'
          f'我方号对敌方真人：{sum(v[0] for v in out.values())} 发 {fmt(tout)} 兵；比值 {tin / max(1, tout):.2f}')
    byteam = collections.defaultdict(lambda: [0, 0])
    for p, v in inc.items():
        byteam[M.team.get(p)][0] += v[0]; byteam[M.team.get(p)][1] += v[1]
    print('按队：' + '；'.join(f'队{k} {v[0]} 发 {fmt(v[1])}' for k, v in sorted(byteam.items(), key=lambda kv: -kv[1][1])))
    outteam = collections.defaultdict(lambda: [0, 0])
    for q, v in out.items():
        outteam[M.team.get(q)][0] += v[0]; outteam[M.team.get(q)][1] += v[1]

    def tshare(team, t):
        v = M.teamts[M.at(t)].get(team, (0, 0, 0, 0))
        return v[0], v[1]

    print('我方号出手按对方所在的队（发 / 兵 / 占我方对真人出兵的比例；这个队在拍段两端的 领土·余额）：')
    for k, v in sorted(outteam.items(), key=lambda kv: -kv[1][1]):
        b0, b1 = tshare(k, t0), tshare(k, t1)
        print(f'  队{k}：{v[0]} 发 {fmt(v[1])}（{100 * v[1] / max(1, tout):.0f}%）；队{k} {b0[0]}·{fmt(b0[1])} → {b1[0]}·{fmt(b1[1])}')
    print('按出手方（发 / 兵 / 船登陆 / 打的号 / 我方对它 / 它在拍段两端的 领土·余额）：')
    for p, v in sorted(inc.items(), key=lambda kv: -kv[1][1]):
        a0, a1 = st(p, t0), st(p, t1)
        tg = '、'.join(f'{M.nm(q)} {fmt(s)}' for q, s in v[4].most_common())
        o = out.get(p, [0, 0])
        print(f'  {M.nm(p)}：{v[0]} 发 {fmt(v[1])}（船登陆 {v[2]} 发 {fmt(v[3])}）→ {tg}；我方对它 {o[0]} 发 {fmt(o[1])}；它 {a0[0]}·{fmt(a0[1])} → {a1[0]}·{fmt(a1[1])}')
    print('按我方号（挨打 发 / 兵 / 出手的敌方真人数；自己对真人 发 / 兵；收到捐款；拍段两端的 领土·余额）：')
    for q in M.our_ids:
        g = got.get(q, [0, 0, set()]); s = sent.get(q, [0, 0])
        a0, a1 = st(q, t0), st(q, t1)
        if a0[0] <= 0 and a1[0] <= 0 and g[0] == 0:
            continue
        print(f'  {M.nm(q):8s} 挨 {g[0]} 发 {fmt(g[1])}（{len(g[2])} 个人）；自己出 {s[0]} 发 {fmt(s[1])}；收到捐款 {fmt(dons.get(q, 0))}；{a0[0]}·{fmt(a0[1])} → {a1[0]}·{fmt(a1[1])}')
    fl = M.flows(t0, t1)
    tm = set(M.teammates)
    gain = sum(n for (f, t), n in fl.items() if t in tm and f not in tm)
    loss = sum(n for (f, t), n in fl.items() if f in tm and t not in tm)
    sq = set(M.our_ids)
    gain_s = sum(n for (f, t), n in fl.items() if t in sq and f not in sq)
    loss_s = sum(n for (f, t), n in fl.items() if f in sq and t not in sq)
    print(f'地块流动：我方队从外面拿到 {gain}、被拿走 {loss}（净 {gain - loss:+d}）；只算我方号：拿到 {gain_s}、被拿走 {loss_s}（净 {gain_s - loss_s:+d}，含与同队其他真人之间的流动）')
    if '--by-target' in a:
        print('逐对（出手方 → 挨打的号）：')
        for (p, q), v in sorted(pair.items(), key=lambda kv: -kv[1][1]):
            print(f'  {M.nm(p)} → {M.nm(q)}：{v[0]} 发 {fmt(v[1])}')


if __name__ == '__main__':
    main()
