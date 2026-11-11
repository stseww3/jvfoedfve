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
    by_rcpt = collections.Counter(); by_kind = collections.Counter(); boxed_n = 0
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
        if k:
            by_kind[k[0]] += 1
            if k[1] == 'true':
                boxed_n += 1
        if not quiet:
            print(' %d %s→%s 比例 %d/1024 到账 %s 税 %s | 捐款人 余额 %s 密度 %.0f→%.0f | 收款人 地 %d 密度 %.0f | %s' % (
                c['t'], M.nm(c['p']), M.nm(c['q']), c['a'], fmt(cred), fmt(tax), fmt(c['bal0']), d0, d1,
                c['terrQ'], c['balQ0'] / max(1, c['terrQ']), ('%s%s' % (k[0], '（封死号）' if k[1] == 'true' else '')) if k else '?'))
    print('[%d,%d] 落地 %d 笔，到账 %s，税 %s；捐后密度 ≤32 的 %d 笔；封死号发出的 %d 笔；按种类 %s' % (
        t0, min(t1, M.last), n, fmt(cred_tot), fmt(tax_tot), thin, boxed_n, dict(by_kind)))
    print('收款人到账：', {k: fmt(v) for k, v in by_rcpt.most_common()})


if __name__ == '__main__':
    main()
