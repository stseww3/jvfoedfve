#!/usr/bin/env python3
# slow_ticks.py — 我方日志里的「慢拍」：[HL-SLOW-TICK] t=… took …ms（一次决策算了 ≥25 毫秒才记一行，约 20~25 拍最多记一行）。
# 一拍约 56 毫秒、5 拍决策一次；一次决策 50~140 毫秒就是把实时预算的两到五成花在策略自己身上，客户端会落后于服务器，指令跟着迟到。
# 用法：python3 scripts/slow_ticks.py <局号> [<局号> …] [--list 号名]
# 输出：每个号各时段的慢拍行数 / 耗时中位 / 最大，第一条慢拍在哪一拍；有 tmp/shadow 和 tmp/truth 时，
#       另给「慢拍密集段（相邻慢拍相隔 ≤60 拍连成一段）」里这个号的指令延迟（执行拍 − 决策拍，exec_gap 的宽配对）对「同一个号不在慢拍段里」的延迟。
import sys, os, re, json, collections, statistics
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
BANDS = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3000, '1500~2999'), (3000, 10 ** 9, '3000+')]
RX = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-SLOW-TICK\] t=(\d+) took ([\d.]+)ms')


def load(mid):
    by = collections.defaultdict(list)
    p = os.path.join(DATA, 'bundles', mid, 'in_game.log')
    if not os.path.exists(p):
        return by
    with open(p, encoding='utf8', errors='replace') as f:
        for line in f:
            m = RX.match(line)
            if m:
                by[m.group(2)].append((int(m.group(3)), float(m.group(4))))
    return by


def segments(v, gap=60):
    segs = []
    for t, ms in sorted(v):
        if segs and t - segs[-1][1] <= gap:
            segs[-1][1] = t
            segs[-1][2].append(ms)
        else:
            segs.append([t, t, [ms]])
    return segs


def pq(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else None


def one(mid, lst=None):
    by = load(mid)
    n = sum(len(v) for v in by.values())
    print('# %s 慢拍（[HL-SLOW-TICK]，一次决策 ≥25 毫秒）：%d 个号共 %d 行' % (mid, len(by), n))
    out = dict(match=mid, lines=n, bots={})
    if not n:
        return out
    print('  号        ' + '  '.join('%-18s' % lab for _, _, lab in BANDS) + ' 第一条慢拍   慢拍密集段（起~止 拍：行数，耗时中位/最大 毫秒）')
    lag_in, lag_out = [], []
    by_band = collections.defaultdict(lambda: ([], []))
    pairs = None
    try:
        import exec_gap
        intents, cmds, check = exec_gap.load(mid)
        ours = {b['p']: b['bot'] for b in check['bots']}
        pr, _, _ = exec_gap.match(intents, [c for c in cmds if c['p'] in ours])
        pairs = collections.defaultdict(list)
        for x, c in pr:
            pairs[x['bot']].append((x['t'], c['t'] - x['t']))
    except Exception:
        pairs = None
    for b, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        cells = []
        for lo, hi, lab in BANDS:
            x = [ms for t, ms in v if lo <= t < hi]
            cells.append('%-18s' % (('%d 行 %.0f/%.0f' % (len(x), statistics.median(x), max(x))) if x else '—'))
        segs = [s for s in segments(v) if len(s[2]) >= 3]
        print('  %-8s  %s %5d        %s' % (b, '  '.join(cells), min(t for t, _ in v),
                                         '；'.join('%d~%d：%d 行 %.0f/%.0f' % (s[0], s[1], len(s[2]), statistics.median(s[2]), max(s[2])) for s in segs[:6]) or '没有连成段的'))
        out['bots'][b] = dict(n=len(v), first=min(t for t, _ in v), med=statistics.median([ms for _, ms in v]), max=max(ms for _, ms in v),
                              segments=[[s[0], s[1], len(s[2])] for s in segs])
        if pairs is not None and b in pairs:
            for t, lag in pairs[b]:
                inside = any(s[0] <= t <= s[1] for s in segs)
                (lag_in if inside else lag_out).append(lag)
                band = next(lab for lo, hi, lab in BANDS if lo <= t < hi)
                by_band[band][0 if inside else 1].append(lag)
        if lst == b:
            for t, ms in v:
                print('      t=%d %.1f 毫秒' % (t, ms))
    if pairs is not None and (lag_in or lag_out):
        print('  指令延迟（执行拍 − 决策拍，宽配对；只算有慢拍的号）：决策拍落在慢拍密集段里的 %d 条 P50/P90/Max %s/%s/%s；不在段里的 %d 条 %s/%s/%s' % (
            len(lag_in), pq(lag_in, .5), pq(lag_in, .9), max(lag_in) if lag_in else None, len(lag_out), pq(lag_out, .5), pq(lag_out, .9), max(lag_out) if lag_out else None))
        out['lagIn'] = dict(n=len(lag_in), p50=pq(lag_in, .5), p90=pq(lag_in, .9))
        out['lagOut'] = dict(n=len(lag_out), p50=pq(lag_out, .5), p90=pq(lag_out, .9))
        print('    按时段（段里 条数 P50/P90 对 段外 条数 P50/P90）：' + '；'.join(
            '%s 段里 %d 条 %s/%s 对 段外 %d 条 %s/%s' % (lab, len(by_band[lab][0]), pq(by_band[lab][0], .5), pq(by_band[lab][0], .9),
                                                 len(by_band[lab][1]), pq(by_band[lab][1], .5), pq(by_band[lab][1], .9)) for _, _, lab in BANDS if by_band[lab][0] or by_band[lab][1]))
        out['byBand'] = {lab: dict(inN=len(v[0]), inP50=pq(v[0], .5), outN=len(v[1]), outP50=pq(v[1], .5)) for lab, v in by_band.items()}
    return out


def main():
    a = sys.argv[1:]
    lst = a[a.index('--list') + 1] if '--list' in a else None
    mids = [x for x in a if not x.startswith('--') and x != lst]
    for mid in mids:
        out = one(mid, lst)
        d = os.path.join(ROOT, 'tmp', 'slow')
        os.makedirs(d, exist_ok=True)
        json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
