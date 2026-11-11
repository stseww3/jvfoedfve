#!/usr/bin/env python3
# 逐笔列出我方号落地的捐款：捐前/捐后密度、到账、税、收款人当时的地与密度、调度种类。
# 用法：python3 scripts/donation_list.py <局号> [t0 t1] [--ours id,id,…] [--quiet]
#   调度种类（defense / yield_opt / offense）与 boxedIn 标记来自影子策略日志 tmp/shadow/<局号>/logs.txt
#   （先跑 scripts/shadow_all.sh <局号>）；没有这份日志时只列真引擎的数。
import sys, re, os, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    nums = [int(x) for x in a[1:] if x.lstrip('-').isdigit()]
    t0, t1 = (nums + [0, 10 ** 9])[:2] if len(nums) >= 2 else (0, 10 ** 9)
    quiet = '--quiet' in a
    M = Match(mid, ours)
    kinds = {}
    lp = os.path.join(HERE, '..', 'tmp', 'shadow', mid, 'logs.txt')
    if os.path.exists(lp):
        for l in open(lp, encoding='utf8', errors='replace'):
            m = re.search(r'\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(\w+) myBal=(\d+) dMe=(\d+) dAlly=(\d+)', l)
            if m:
                kinds.setdefault(int(m.group(4)), []).append((int(m.group(1)), int(m.group(7)), m.group(2), m.group(6)))
    n = 0; thin = 0; cred_tot = 0; tax_tot = 0
    under_n = 0; under_tax = 0; under_cred = 0      # 到账 < 税 的捐款
    pair = collections.defaultdict(lambda: [0, 0, 0])  # (捐款人, 收款人) -> [笔数, 到账, 税]
    seq = []                                        # (拍, 捐款人, 收款人, 到账)，用来数来回倒
    want_tot = 0; cut_n = 0; cut_want = 0; cut_cred = 0   # 想送 = 比例×捐款人余额；被收款方上限截掉的
    relay_in = collections.Counter()                # 每个号收到的
    relay_out = collections.Counter()               # 每个号又捐出去的（到账）
    relay_tax = collections.Counter()
    by_rcpt = collections.Counter(); by_kind = collections.Counter(); boxed_n = 0
    kind_cred = collections.Counter(); kind_tax = collections.Counter(); kind_thin = collections.Counter()
    over_n = over_cred = over128_n = over128_cred = 0  # 到账后收款人余额 > 100×领土（利息开始被折扣）/ > 128×领土
    for c in M.cmd:
        if c['id'] != 2 or c['p'] not in M.ours or not (t0 <= c['t'] <= t1) or 'q' not in c:
            continue
        cred = c['balQ1'] - c['balQ0']
        if cred <= 0:
            continue
        tax = c['bal0'] - c['bal1'] - cred
        k = None
        for (t, b, kind, boxed) in kinds.get(c['q'], []):
            if 0 <= c['t'] - t <= 40 and abs(b - c['bal0']) <= 0.2 * c['bal0'] + 1:
                k = (kind, boxed)
        d0 = c['bal0'] / max(1, c['terr0']); d1 = c['bal1'] / max(1, c['terr0'])
        n += 1; cred_tot += cred; tax_tot += tax
        if d1 <= 32:
            thin += 1
        by_rcpt[M.nm(c['q'])] += cred
        dq1 = c['balQ1'] / max(1, c['terrQ'])
        if dq1 > 100:
            over_n += 1; over_cred += cred
        if dq1 > 128:
            over128_n += 1; over128_cred += cred
        if cred < tax:
            under_n += 1; under_tax += tax; under_cred += cred
        pr = pair[(M.nm(c['p']), M.nm(c['q']))]
        pr[0] += 1; pr[1] += cred; pr[2] += tax
        seq.append((c['t'], c['p'], c['q'], cred))
        want = (c['a'] + 1) * c['bal0'] // 1024
        want_tot += want
        if cred < 0.98 * want:
            cut_n += 1; cut_want += want; cut_cred += cred
        relay_in[M.nm(c['q'])] += cred; relay_out[M.nm(c['p'])] += cred; relay_tax[M.nm(c['p'])] += tax
        if k:
            by_kind[k[0]] += 1
            kind_cred[k[0]] += cred; kind_tax[k[0]] += tax
            if d1 <= 45:
                kind_thin[k[0]] += 1
            if k[1] == 'true':
                boxed_n += 1
        if not quiet:
            print(' %d %s→%s 比例 %d/1024 到账 %s 税 %s | 捐款人 余额 %s 密度 %.0f→%.0f | 收款人 地 %d 密度 %.0f | %s' % (
                c['t'], M.nm(c['p']), M.nm(c['q']), c['a'], fmt(cred), fmt(tax), fmt(c['bal0']), d0, d1,
                c['terrQ'], c['balQ0'] / max(1, c['terrQ']), ('%s%s' % (k[0], '（封死号）' if k[1] == 'true' else '')) if k else '?'))
    print('[%d,%d] 落地 %d 笔，到账 %s，税 %s；捐后密度 ≤32 的 %d 笔；封死号发出的 %d 笔；按种类 %s' % (
        t0, min(t1, M.last), n, fmt(cred_tot), fmt(tax_tot), thin, boxed_n, dict(by_kind)))
    if by_kind:
        print('按调度种类（笔数 / 到账 / 税 / 捐后密度 ≤45 的笔数）：' + '；'.join('%s %d 笔 / %s / %s / %d' % (k, v, fmt(kind_cred[k]), fmt(kind_tax[k]), kind_thin[k]) for k, v in by_kind.most_common())
              + '；对不上影子日志的 %d 笔' % (n - sum(by_kind.values())))
    print('收款人到账：', {k: fmt(v) for k, v in by_rcpt.most_common()})
    print('到账 < 税 的捐款：%d 笔，到账合计 %s，税合计 %s' % (under_n, fmt(under_cred), fmt(under_tax)))
    print('到账后收款人余额 > 100×领土（软上限，利息开始打折）的捐款：%d 笔 %s；其中 > 128×领土 的 %d 笔 %s' % (over_n, fmt(over_cred), over128_n, fmt(over128_cred)))
    # 来回倒：A→B 之后 100 拍内出现 B→A
    pp = 0; pp_pairs = collections.Counter()
    for i, (t, p, q, _c) in enumerate(seq):
        for (t2, p2, q2, _c2) in seq[i + 1:]:
            if t2 - t > 100:
                break
            if p2 == q and q2 == p:
                pp += 1; pp_pairs[tuple(sorted((M.nm(p), M.nm(q))))] += 1
                break
    print('100 拍内来回倒（A→B 后 B→A）：%d 次 %s' % (pp, dict(pp_pairs)))
    # 300 拍内来回倒手：A→B 这一笔的前后 300 拍内有过 B→A
    back = 0
    for (t, p, q, cr) in seq:
        if any(abs(t2 - t) <= 300 and p2 == q and q2 == p for (t2, p2, q2, _x) in seq):
            back += cr
    print('300 拍内来回倒手的到账：%s，占到账合计的 %.0f%%' % (fmt(back), 100.0 * back / max(1, cred_tot)))
    print('想送（比例×捐款人余额）合计 %s，实际到账 %s；被收款方 150×领土 上限截短的 %d 笔：想送 %s 只到账 %s（截掉 %.0f%%），税照 6.25%%×余额 全交' % (
        fmt(want_tot), fmt(cred_tot), cut_n, fmt(cut_want), fmt(cut_cred), 100.0 * (cut_want - cut_cred) / max(1, cut_want)))
    relay = [(k, relay_in[k], relay_out[k], relay_tax[k]) for k in relay_in if relay_out[k] >= 0.3 * relay_in[k] and relay_in[k] >= 500000]
    for (k, i_, o_, tx) in sorted(relay, key=lambda r: -r[1]):
        print('二传手 %s：收到 %s，又捐出去 %s（到账），为此再交税 %s' % (k, fmt(i_), fmt(o_), fmt(tx)))
    top = sorted(pair.items(), key=lambda kv: -kv[1][1])[:6]
    print('到账最多的几条线：' + '；'.join('%s→%s %d 笔 %s（税 %s）' % (k[0], k[1], v[0], fmt(v[1]), fmt(v[2])) for k, v in top))


if __name__ == '__main__':
    main()
