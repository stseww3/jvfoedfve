#!/usr/bin/env python3
# postkill_exposure.py — 「把快垮的邻居打死之后，站在它身后的大号成了新邻居」的账。
# 用来机械地数 NEW-DF-NEXTNB：策略的出兵底线只看当前的陆上真人邻居（V13.dpKeep L2459~2464，postKill=0 时
# V13.safeAt L2728~2738 不把目标的其他邻居算进来），唯一的邻居濒崩时底线跟着掉下去，兵倒进去；它一出局，
# 原先隔着它的敌方真人就贴上来。
#
# 用法：python3 scripts/postkill_exposure.py <局号> [--ours id,id,…] [--pre 300] [--post 400]
# 口径（全部来自真引擎重放 tmp/truth/<局号>/）：
#   X        = 出局的敌方真人，出局拍 tX；
#   出手     = 我方号 b 在 (tX−pre, tX] 对 X 落地的陆攻兵合计（不含手续费），只列 ≥ b 在 tX−pre 时余额 10% 的；
#   密度     = b 在 tX−pre 与 tX 两拍的 余额/领土；
#   新来的   = 在 (tX−150, tX+post] 对 b 出过手（陆攻或船登陆）、而在 (tX−900, tX−150] 没对 b 出过手的敌方真人，
#              列它们在 tX 时的领土与余额、对 b 的出兵合计；
#   后果     = b 在 (tX, tX+post] 被这些新来的拿走的地、b 是否在这段出局；
#   算一例   = tX 时密度 ≤ 45 且 ≤ tX−pre 时的 60%，新来的出兵合计 ≥ b 在 tX 的余额，
#              且 b 在 tX+post 之前出局或被新来的拿走 ≥ 25% 的地。
import sys, os, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    pre = int(a[a.index('--pre') + 1]) if '--pre' in a else 300
    post = int(a[a.index('--post') + 1]) if '--post' in a else 400
    M = Match(mid, ours)

    def troops(c):
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')

    out_hits = collections.defaultdict(list)   # (b, X) -> [(t, 兵)]
    in_hits = collections.defaultdict(list)    # b -> [(t, 出手方, 兵)]
    for c in M.cmd:
        if c['id'] != 1:
            continue
        s = troops(c)
        if s <= 0:
            continue
        if c['p'] in M.ours and c['b'] < M.ku and M.team.get(c['b']) != M.our_team:
            out_hits[(c['p'], c['b'])].append((c['t'], s))
        if c['b'] in M.ours and c['p'] < M.ku and M.team.get(c['p']) != M.our_team:
            in_hits[c['b']].append((c['t'], c['p'], s))
    for (t, kind, p, x, y, det) in M.ev:
        if kind != 'land' or '|' not in det:
            continue
        for part in det.split('|', 1)[1].split(';'):
            f = part.split(':')
            if f[0] == 'atk' and len(f) >= 3 and int(f[2]) > 0:
                tgt, s = int(f[1]), int(f[2])
                if p in M.ours and tgt < M.ku and M.team.get(tgt) != M.our_team:
                    out_hits[(p, tgt)].append((t, s))
                if tgt in M.ours and p < M.ku and M.team.get(p) != M.our_team:
                    in_hits[tgt].append((t, p, s))

    def our_at(b, t):
        d = M.our.get(b, {})
        while t >= 0 and t not in d:
            t -= 1
        return d.get(t)

    def st_at(p, t):
        return M.state[M.at(t)].get(p)

    print(f'# {mid} 打死濒崩邻居之后（出局前 {pre} 拍的出手；出局后 {post} 拍的后果）')
    n_case, rows = 0, 0
    for X, (tX, _, _, _) in sorted(M.dead.items(), key=lambda kv: kv[1][0]):
        if X >= M.ku or M.team.get(X) == M.our_team or X in M.ours:
            continue
        for b in M.our_ids:
            hs = [(t, s) for (t, s) in out_hits.get((b, X), []) if tX - pre < t <= tX]
            if not hs:
                continue
            s0 = our_at(b, tX - pre)
            s1 = our_at(b, tX)
            if not s0 or not s1 or s1[0] <= 0:
                continue
            spent = sum(s for (_, s) in hs)
            if spent < 0.10 * s0[1]:
                continue
            rows += 1
            d0, d1 = s0[1] / max(1, s0[0]), s1[1] / max(1, s1[0])
            old = {p for (t, p, s) in in_hits.get(b, []) if tX - 900 < t <= tX - 150}
            new = collections.defaultdict(lambda: [0, 0])
            for (t, p, s) in in_hits.get(b, []):
                if tX - 150 < t <= tX + post and p not in old and p != X:
                    new[p][0] += 1
                    new[p][1] += s
            fl = M.flows(tX, tX + post)
            lost_new = sum(px for (fr, to), px in fl.items() if fr == b and to in new)
            dead_b = M.dead.get(b)
            died = bool(dead_b and tX < dead_b[0] <= tX + post)
            new_sum = sum(v[1] for v in new.values())
            case = d1 <= 45 and d1 <= 0.6 * d0 and new_sum >= s1[1] and (died or lost_new >= 0.25 * s1[0])
            n_case += case
            desc = []
            for p, (n, s) in sorted(new.items(), key=lambda kv: -kv[1][1]):
                sp = st_at(p, tX)
                desc.append(f'{M.nm(p)} {n} 发 {fmt(s)} 兵（它在拍 {tX} 地 {sp[0] if sp else "?"} 兵 {fmt(sp[1]) if sp else "?"}）')
            print(f'  {M.nm(X)} 拍 {tX} 出局 ← {M.nm(b)} 此前 {pre} 拍对它出手 {len(hs)} 发 {fmt(spent)} 兵；'
                  f'{M.nm(b)} 密度 {d0:.0f}→{d1:.0f}（地 {s0[0]}→{s1[0]}，兵 {fmt(s0[1])}→{fmt(s1[1])}）；'
                  f'新来的：{"；".join(desc) if desc else "无"}；之后 {post} 拍被新来的拿走 {lost_new} 格'
                  f'{"，拍 " + str(dead_b[0]) + " 出局" if died else ""}{" ⇒ 算一例" if case else ""}')
    print(f'合计：列出 {rows} 组（我方号 × 出局的敌方真人），按 NEW-DF-NEXTNB 的口径算 {n_case} 例')


main()
