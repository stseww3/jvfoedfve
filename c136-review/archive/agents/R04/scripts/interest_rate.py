#!/usr/bin/env python3
# 利息率与「顶格少拿的利息」：按引擎公式逐个采样点算每个号的利率。
# 用法：python3 scripts/interest_rate.py <局号> [--at t1,t2,…] [--win t0,t1,…] [--ours id,id,…] [--top N]
# 公式（总部镜像 c136-data/src/sim/sim/game.js 第 40~41、739~746 行；本脚本 --verify 用真引擎余额核对）：
#   查表利率（万分之几 / 每 10 拍）= 100 + isqrt( floor(25600 × floor(511×领土/全图陆地) / 508) )
#   t < 1920 时与 floor(100×(13440−6t)/1920) 取大；离场的号为 0；
#   余额 > 100×领土（软上限）时再减 floor(2×利率×(余额−上限)/上限)，到 150×领土 减到 0。
# 输出：
#   --at：各时刻我方每个号的 占地、查表利率、软上限折扣后的实际利率；编队按余额加权的实际利率；
#         「同样的地和兵如果在一个号手里」的查表利率；地最多的 N 个其他真人的利率（默认 3 个）。
#   --win：每个窗口里编队实拿利息（按每 10 拍采样的余额估算）、因软上限折扣少拿的利息、
#         因为地分在多个号手里（相对于合成一个号的查表利率）少拿的利息。
#   --verify：挑没有任何收支的 10 拍，核对公式算出的利息与真引擎余额增量是否一致。
import sys, os, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def iV(a, b):
    return int(math.floor((a + 0.5) / b))


def table_rate(terr, land, t=10 ** 9):
    i = iV(511 * terr, land)
    n1 = 100 + math.isqrt(max(0, iV(25600 * i, 508)))
    if t < 1920:
        n1 = max(iV(100 * (13440 - 6 * t), 1920), n1)
    return n1


def eff_rate(terr, bal, land, t=10 ** 9, left=False):
    if left or terr <= 0:
        return 0
    n1 = table_rate(terr, land, t)
    cap = 100 * terr
    if bal > cap:
        n1 -= iV(2 * n1 * (bal - cap), cap)
    return min(max(n1, 0), 700)


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta = json.load(open(os.path.join(here, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    land = meta['info']['ke']
    humans = meta['info']['ku']
    top = int(a[a.index('--top') + 1]) if '--top' in a else 3
    if '--verify' in a:
        ok = bad = 0
        ts = M.samples
        for i in range(len(ts) - 1):
            t0, t1 = ts[i], ts[i + 1]
            if t1 - t0 != 10 or t0 % 100 == 90:
                continue
            for p in M.our_ids:
                s0 = M.state[t0].get(p); s1 = M.state[t1].get(p)
                if not s0 or not s1 or s0[0] != s1[0] or s0[2] or s1[2] or s0[4] or s1[4] or s0[6] != s1[6]:
                    continue
                if any(c['p'] == p and t0 <= c['t'] <= t1 for c in M.cmd_by_p.get(p, [])) if hasattr(M, 'cmd_by_p') else False:
                    continue
                want = max(iV(eff_rate(s0[0], s0[1], land, t0 + 9, s0[8] == 2) * s0[1], 10000), 1)
                want = min(want, max(0, 150 * s0[0] - s0[1]))
                got = s1[1] - s0[1]
                if got == want:
                    ok += 1
                elif 0 < got < 3 * want + 5:
                    bad += 1
        print('核对：没有领土变化、没有进出攻击的 10 拍区间里，公式利息与真引擎余额增量完全相等 %d 次，不等 %d 次（不等的多是这 10 拍里有捐款/指令落地）' % (ok, bad))
        return
    if '--at' in a:
        for t in [int(x) for x in a[a.index('--at') + 1].split(',')]:
            tt = M.at(t)
            S = M.state[tt]
            print('== 拍 %d' % tt)
            sb = st = wr = 0
            for p in M.our_ids:
                s = S.get(p)
                if not s or s[0] <= 0:
                    continue
                tr = table_rate(s[0], land, tt); er = eff_rate(s[0], s[1], land, tt, s[8] == 2)
                sb += s[1]; st += s[0]; wr += er * s[1]
                print('  %-7s 地 %6d（%.2f%%） 兵 %8s 密度 %5.1f 查表利率 %.2f%% 实际 %.2f%%%s' % (
                    M.nm(p), s[0], 100.0 * s[0] / land, fmt(s[1]), s[1] / max(1, s[0]), tr / 100.0, er / 100.0,
                    '（离场）' if s[8] == 2 else ''))
            if sb:
                one = table_rate(st, land, tt)
                print('  编队：地 %d（%.2f%%） 兵 %s；按余额加权的实际利率 %.2f%%/10 拍（每 10 拍进账约 %s）；同样的地在一个号手里查表利率 %.2f%%' % (
                    st, 100.0 * st / land, fmt(sb), wr / sb / 100.0, fmt(wr / 10000.0), one / 100.0))
            others = sorted(((s[0], p) for p, s in S.items() if p < humans and p not in M.ours and s[0] > 0), reverse=True)[:top]
            for terr, p in others:
                s = S[p]
                tr = table_rate(s[0], land, tt); er = eff_rate(s[0], s[1], land, tt, s[8] == 2)
                print('  对照 %s：地 %d（%.2f%%） 兵 %s 密度 %.1f 查表利率 %.2f%% 实际 %.2f%%（每 10 拍进账约 %s）%s' % (
                    M.nm(p), s[0], 100.0 * s[0] / land, fmt(s[1]), s[1] / max(1, s[0]), tr / 100.0, er / 100.0, fmt(er * s[1] / 10000.0),
                    '（离场）' if s[8] == 2 else ''))
    if '--win' in a:
        edges = [int(x) for x in a[a.index('--win') + 1].split(',')]
        for i in range(len(edges) - 1):
            t0, t1 = edges[i], edges[i + 1]
            got = cap_loss = split_loss = 0
            per = {}
            for t in M.samples:
                if not (t0 <= t < t1) or t % 10:
                    continue
                S = M.state[t]
                st = sum(S[p][0] for p in M.our_ids if p in S and S[p][8] != 2)
                one = table_rate(st, land, t + 9) if st else 0
                for p in M.our_ids:
                    s = S.get(p)
                    if not s or s[0] <= 0 or s[8] == 2:
                        continue
                    tr = table_rate(s[0], land, t + 9); er = eff_rate(s[0], s[1], land, t + 9)
                    g = er * s[1] / 10000.0
                    g = min(g, max(0, 150 * s[0] - s[1]))
                    got += g
                    cl = (tr - er) * s[1] / 10000.0
                    cap_loss += cl
                    split_loss += max(0, one - tr) * s[1] / 10000.0
                    per[p] = per.get(p, 0) + cl
            worst = sorted(per.items(), key=lambda kv: -kv[1])[:4]
            print('(%d,%d] 编队实拿利息约 %s；因余额超过 100×领土 被折扣少拿 %s（%s）；因为地分在多个号手里、相对合成一个号少拿 %s' % (
                t0, t1, fmt(got), fmt(cap_loss), '，'.join('%s %s' % (M.nm(p), fmt(v)) for p, v in worst if v > 0) or '无', fmt(split_loss)))


if __name__ == '__main__':
    main()
