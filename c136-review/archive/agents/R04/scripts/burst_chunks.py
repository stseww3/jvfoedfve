#!/usr/bin/env python3
# burst_chunks.py — 成批落地的指令「前后各是什么」：一批落地的是哪一段连续决策拍，这一段后面紧跟着的意图有没有落地，
#   下一批又从哪一个决策拍接上。用来区分两种读法：
#     (甲) 客户端自己的拍数落后服务器，一次补一截：每补一截，这一截里各决策拍的指令同时发出，服务器同一拍只收前几条；
#     (乙) 客户端不落后，指令在发送路上排队。
#   (甲) 的特征是「落地的一段 + 紧跟着丢掉的一段 + 下一批从丢掉的那一段之后接着来」，而且每一批落地时，
#   这一截最后一个决策拍离落地拍还差很远（客户端补完这一截仍然没追上）。
#
# 用法：python3 scripts/burst_chunks.py <局号> [<局号> …] [--list 名字] [--min 3]
#   先要有 tmp/truth/<局号>/cmd.tsv 和 tmp/shadow/<局号>/intents.tsv。
# 口径：
#   批 = 同一个号同一拍落地 ≥min 条陆攻，且能和「一段连续的陆攻意图倒序」逐条对上（burst_runs.find_run，允许跳 1 条）。
#   尾巴 = 这一段之后、下一条落地的意图之前，同一个号连着发的陆攻意图（相邻意图间隔 ≤10 拍才算连着），它们一条都没落地。
#   这一截 = 批对上的那一段 + 尾巴。「补完还差」= 落地拍 − 7 − 这一截最后一个决策拍（7 拍是一个回合，指令最快也要这么久）。
# 输出：每个时段的批数、每批落地条数的分布、有尾巴的批占多少、尾巴条数、这一截跨多少个决策拍、补完还差多少拍；tmp/chunks/<局号>.json
import sys, os, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import burst_runs
import exec_gap

BANDS = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3000, '1500~2999'), (3000, 10 ** 9, '3000+')]


def band(t):
    for lo, hi, nm in BANDS:
        if lo <= t < hi:
            return nm


def pq(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def run(mid, mn, lst):
    names, intents, cmds = burst_runs.load(mid)
    ints_all, cmds_all, _ = exec_gap.load(mid)
    pairs, _, _ = exec_gap.match(ints_all, cmds_all)
    landed = collections.defaultdict(dict)          # p -> {intent tick: landing tick}（宽配对，只看陆攻）
    for x, c in pairs:
        if x['kind'] == 'attack':
            landed[x['p']].setdefault(x['t'], c['t'])
    rows = []
    for p in sorted(names):
        ints = intents[p]
        ticks = sorted(t for (q, t) in cmds if q == p)
        prev_end = None
        for T in ticks:
            seq = [c[0] for c in cmds[(p, T)]]
            if len(seq) < mn:
                continue
            r = burst_runs.find_run(seq, ints, T, False) or burst_runs.find_run(seq, ints, T, True)
            if r is None:
                rows.append(dict(bot=names[p], T=T, n=len(seq), matched=False))
                continue
            i0, i1, _ = r
            tail = []
            j = i1 + 1
            last = ints[i1][0]
            while j < len(ints) and ints[j][0] - last <= 10 and ints[j][0] < T:
                if ints[j][0] in landed[p] and landed[p][ints[j][0]] != T:
                    break
                if ints[j][0] in landed[p] and landed[p][ints[j][0]] == T:
                    j += 1
                    continue
                tail.append(ints[j][0])
                last = ints[j][0]
                j += 1
            end_local = tail[-1] if tail else ints[i1][0]
            rows.append(dict(bot=names[p], T=T, n=len(seq), matched=True, first=ints[i0][0], lastLanded=ints[i1][0], tail=len(tail),
                             tailTo=end_local, newestLag=T - ints[i1][0], oldestLag=T - ints[i0][0], short=T - 7 - end_local,
                             span=(end_local - ints[i0][0]) // 5 + 1,
                             contiguous=(prev_end is not None and 0 < ints[i0][0] - prev_end <= 10)))
            prev_end = end_local
    print('# %s 成批落地的指令前后（同号同拍 ≥%d 条陆攻算一批）' % (mid, mn))
    out = dict(match=mid, bands={})
    for lo, hi, nm in BANDS:
        v = [r for r in rows if lo <= r['T'] < hi]
        if not v:
            continue
        m = [r for r in v if r['matched']]
        if not m:
            print('  %-10s %d 批，都没对上连续意图' % (nm, len(v)))
            continue
        wt = [r for r in m if r['tail'] > 0]
        sizes = collections.Counter(r['n'] for r in m)
        full = [r for r in m if r['n'] >= 8]
        fullt = [r for r in full if r['tail'] > 0]
        s = '  %-10s %d 批（对上 %d 批）；每批落地条数 中位 %d（8~9 条的 %d 批）；有尾巴（紧跟着的意图一条没落地）的 %d 批（%.0f%%），其中 8~9 条的批 %d/%d；' % (
            nm, len(v), len(m), pq([r['n'] for r in m], .5), len(full), len(wt), 100.0 * len(wt) / len(m), len(fullt), len(full))
        if wt:
            s += '尾巴 中位 %d 条、最多 %d 条、合计 %d 条；' % (pq([r['tail'] for r in wt], .5), max(r['tail'] for r in wt), sum(r['tail'] for r in wt))
        s += '这一截跨的决策拍数 中位 %d、最多 %d；批里最新一条晚 中位 %d 拍；补完这一截离落地拍还差 中位 %d、P90 %d 拍；和上一截首尾相接的 %d 批' % (
            pq([r['span'] for r in m], .5), max(r['span'] for r in m), pq([r['newestLag'] for r in m], .5),
            pq([r['short'] for r in m], .5), pq([r['short'] for r in m], .9), sum(1 for r in m if r['contiguous']))
        print(s)
        out['bands'][nm] = dict(batches=len(v), matched=len(m), sizeP50=pq([r['n'] for r in m], .5), full=len(full), withTail=len(wt), fullWithTail=len(fullt),
                                tailP50=pq([r['tail'] for r in wt], .5) if wt else 0, tailMax=max([r['tail'] for r in wt], default=0),
                                tailSum=sum(r['tail'] for r in wt), spanP50=pq([r['span'] for r in m], .5), spanMax=max(r['span'] for r in m),
                                newestLagP50=pq([r['newestLag'] for r in m], .5), shortP50=pq([r['short'] for r in m], .5), shortP90=pq([r['short'] for r in m], .9),
                                contiguous=sum(1 for r in m if r['contiguous']), sizes=dict(sizes))
    m = [r for r in rows if r['matched']]
    if m:
        small = [r for r in m if r['n'] < 8]
        big = [r for r in m if r['n'] >= 8]
        print('  全局：不到 8 条的批 %d 个，有尾巴的 %d 个（%.0f%%）；8~9 条的批 %d 个，有尾巴的 %d 个（%.0f%%）——尾巴几乎只跟在装满的批后面，说明是「同一拍最多收 9 条」把后面的挤掉了' % (
            len(small), sum(1 for r in small if r['tail']), 100.0 * sum(1 for r in small if r['tail']) / max(1, len(small)),
            len(big), sum(1 for r in big if r['tail']), 100.0 * sum(1 for r in big if r['tail']) / max(1, len(big))))
        out['small'] = dict(n=len(small), withTail=sum(1 for r in small if r['tail']))
        out['big'] = dict(n=len(big), withTail=sum(1 for r in big if r['tail']))
    if lst:
        for r in rows:
            if r['bot'] != lst:
                continue
            if not r['matched']:
                print('    拍 %5d 落地 %d 条：没对上' % (r['T'], r['n']))
            else:
                print('    拍 %5d 落地 %d 条 = 决策拍 %d~%d；尾巴 %d 条（到 %d 拍）；最新一条晚 %d 拍；补完还差 %d 拍%s' % (
                    r['T'], r['n'], r['first'], r['lastLanded'], r['tail'], r['tailTo'], r['newestLag'], r['short'], '；和上一截首尾相接' if r['contiguous'] else ''))
    d = os.path.join(ROOT, 'tmp', 'chunks')
    os.makedirs(d, exist_ok=True)
    out['rows'] = rows
    json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)


def main():
    a = sys.argv[1:]
    mn = int(a[a.index('--min') + 1]) if '--min' in a else 3
    lst = a[a.index('--list') + 1] if '--list' in a else None
    skip = set()
    for k in ('--min', '--list'):
        if k in a:
            skip.add(a.index(k) + 1)
    for i, x in enumerate(a):
        if x.startswith('--') or i in skip:
            continue
        run(x, mn, lst)


if __name__ == '__main__':
    main()
