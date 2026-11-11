#!/usr/bin/env python3
# 每一笔落地的捐款，在落地那一拍让「捐款人 + 收款人」合计的利息变了多少（按引擎利息公式，见 interest_rate.py 文件头）。
# 用法：python3 scripts/yield_check.py <局号> [t0 t1] [--list] [--ours id,id,…]
#   每 10 拍利息 = floor(实际利率 × 余额 / 10000)，实际利率 = 查表利率（看领土）再按「余额超过 100×领土 的部分」打折，
#   并且不超过 150×领土 − 余额。捐款前后领土不变，所以合计利息的变化只来自：
#     (a) 捐款人和收款人的查表利率不同（地大的号利率高）；(b) 两边离软上限的远近；(c) 税（捐款人余额的 6.25%）凭空消失。
#   「回本拍数」= 税 ÷ 每 10 拍多出来的利息 × 10；合计利息变少的笔没有回本这回事。
#   调度种类（defense / yield_opt / offense）来自影子策略日志 tmp/shadow/<局号>/logs.txt（先跑 scripts/shadow_all.sh <局号>）。
import sys, os, re, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_digest import Match, fmt
from interest_rate import eff_rate, iV


def interest(terr, bal, land, t):
    if terr <= 0 or bal <= 0:
        return 0
    x = max(iV(eff_rate(terr, bal, land, t) * bal, 10000), 1)
    return max(0, min(x, 150 * terr - bal))


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    nums = [int(x) for x in a[1:] if x.lstrip('-').isdigit()]
    t0, t1 = (nums + [0, 10 ** 9])[:2] if len(nums) >= 2 else (0, 10 ** 9)
    M = Match(mid, ours)
    meta = json.load(open(os.path.join(HERE, '..', 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    land = meta['info']['ke']
    kinds = {}
    lp = os.path.join(HERE, '..', 'tmp', 'shadow', mid, 'logs.txt')
    if os.path.exists(lp):
        for l in open(lp, encoding='utf8', errors='replace'):
            m = re.search(r'\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(\w+) myBal=(\d+)', l)
            if m:
                kinds.setdefault(int(m.group(4)), []).append((int(m.group(1)), int(m.group(7)), m.group(2)))
    agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])   # 种类 -> [笔数, 到账, 税, 合计利息变化/10拍, 变少的笔数, 变多的笔数]
    rows = []
    for c in M.cmd:
        if c['id'] != 2 or c['p'] not in M.ours or not (t0 <= c['t'] <= t1) or 'q' not in c:
            continue
        cred = c['balQ1'] - c['balQ0']
        if cred <= 0:
            continue
        tax = c['bal0'] - c['bal1'] - cred
        k = '?'
        for (t, b, kind) in kinds.get(c['q'], []):
            if 0 <= c['t'] - t <= 40 and abs(b - c['bal0']) <= 0.2 * c['bal0'] + 1:
                k = kind
        t = c['t']
        i_d0 = interest(c['terr0'], c['bal0'], land, t); i_d1 = interest(c['terr0'], c['bal1'], land, t)
        i_r0 = interest(c['terrQ'], c['balQ0'], land, t); i_r1 = interest(c['terrQ'], c['balQ1'], land, t)
        d = (i_d1 + i_r1) - (i_d0 + i_r0)
        g = agg[k]
        g[0] += 1; g[1] += cred; g[2] += tax; g[3] += d
        if d < 0:
            g[4] += 1
        elif d > 0:
            g[5] += 1
        rows.append((t, M.nm(c['p']), M.nm(c['q']), k, cred, tax, i_d0, i_d1, i_r0, i_r1, d,
                     c['bal0'] / max(1, c['terr0']), c['bal1'] / max(1, c['terr0']),
                     c['balQ0'] / max(1, c['terrQ']), c['balQ1'] / max(1, c['terrQ']), c['terr0'], c['terrQ']))
    if '--list' in a:
        for r in rows:
            pay = ('回本 %d 拍' % (10 * r[5] / r[10])) if r[10] > 0 else '不回本'
            print(' %d %s→%s %s 到账 %s 税 %s | 捐款人 地 %d 密度 %.0f→%.0f 利息 %s→%s | 收款人 地 %d 密度 %.0f→%.0f 利息 %s→%s | 合计每 10 拍 %+d，%s' % (
                r[0], r[1], r[2], r[3], fmt(r[4]), fmt(r[5]), r[15], r[11], r[12], fmt(r[6]), fmt(r[7]), r[16], r[13], r[14], fmt(r[8]), fmt(r[9]), r[10], pay))
    print('%s [%d,%d] 落地 %d 笔捐款，落地当拍「捐款人 + 收款人」每 10 拍利息的变化：' % (mid, t0, min(t1, M.last), len(rows)))
    tot = [0, 0, 0, 0, 0, 0]
    for k, g in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        for i in range(6):
            tot[i] += g[i]
        pay = ('税要 %d 拍才回本' % (10 * g[2] / g[3])) if g[3] > 0 else '合计利息变少，税不回本'
        print('  %s：%d 笔，到账 %s，税 %s；合计利息每 10 拍 %+d（变少的 %d 笔，变多的 %d 笔）；%s' % (k, g[0], fmt(g[1]), fmt(g[2]), g[3], g[4], g[5], pay))
    if rows:
        pay = ('税要 %d 拍才回本' % (10 * tot[2] / tot[3])) if tot[3] > 0 else '合计利息变少，税不回本'
        print('  全部：%d 笔，到账 %s，税 %s；合计利息每 10 拍 %+d（变少的 %d 笔，变多的 %d 笔）；%s' % (tot[0], fmt(tot[1]), fmt(tot[2]), tot[3], tot[4], tot[5], pay))


if __name__ == '__main__':
    main()
