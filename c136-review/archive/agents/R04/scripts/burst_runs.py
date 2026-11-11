#!/usr/bin/env python3
# burst_runs.py — 「成批落地」的形状：同一个号同一拍落地 ≥3 条陆攻时，这一批是不是「一段连着的发令意图，倒着排」。
#
# 用法：python3 scripts/burst_runs.py <局号> [--list] [--min 3]
#   先要有 tmp/truth/<局号>/cmd.tsv（engine_truth.cjs）和 tmp/shadow/<局号>/intents.tsv（shadow.mjs）。
# 做法（不靠“最近一条同参数意图”的贪心配对）：
#   1) 每个号的陆攻意图按发令拍排成一列，只留比例 pct；
#   2) 每一批（同号同拍 ≥min 条陆攻落地）取落地顺序的 pct 序列，倒过来，
#      在「发令拍 ≤ 落地拍」的意图列里找最靠后的一段连续意图，pct 逐条相同 → 算“整段倒序对上”；
#      找不到时允许中间跳过 1 条意图再找一次 → 算“跳 1 条对上”；
#   3) 对上的批：最新一条意图到落地隔几拍、最老一条隔几拍、这一段前面紧挨着没落地的意图有几条；
#   4) 汇总：批数、对上的批数、批的大小分布、相邻两批隔几拍、每批把余额花掉多少。
# 读法：如果批里的指令就是“某一段连续的决策拍各发的一条”，而且顺序是倒的，说明指令在路上被攒成一摞再一起放出来；
#       最新一条的延迟就是这一摞在路上至少待了多久。
import sys, os, csv, collections, statistics
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(mid):
    intents = collections.defaultdict(list)
    names = {}
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            names[int(r['p'])] = r['bot']
            if r['kind'] == 'attack':
                intents[int(r['p'])].append((int(r['t']), int(r['pct']), int(r['target'])))
    cmds = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'truth', mid, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['spawnStep']) >= 0 or int(r['id']) != 1:
                continue
            cmds[(int(r['p']), int(r['t']))].append((int(r['a']), int(r['b']), int(r['bal0']), int(r['bal1'])))
    return names, intents, cmds


def find_run(seq, ints, T, skip):
    """seq：落地顺序的 pct；ints：[(t,pct,target)] 按 t 升序。返回 (i0,i1,跳过的下标) 或 None。"""
    want = list(reversed(seq))
    n = len(want)
    hi = max((i for i, x in enumerate(ints) if x[0] <= T), default=-1)
    lo_t = T - 400
    for end in range(hi, n - 2, -1):
        if ints[end][0] < lo_t:
            break
        if not skip:
            start = end - n + 1
            if start >= 0 and [x[1] for x in ints[start:end + 1]] == want:
                return start, end, None
        else:
            start = end - n
            if start < 0:
                continue
            seg = [x[1] for x in ints[start:end + 1]]
            for k in range(1, n):
                if seg[:k] + seg[k + 1:] == want:
                    return start, end, start + k
    return None


def band(t):
    return '<630' if t < 630 else '630~1499' if t < 1500 else '1500~2999' if t < 3000 else '3000~4283' if t < 4284 else '≥4284'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mid = args[0]
    lst = '--list' in sys.argv
    mn = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 3
    names, intents, cmds = load(mid)
    print(f'# {mid} 成批落地的形状（同号同拍落地 ≥{mn} 条陆攻算一批）')
    tot = collections.Counter()
    all_sizes = collections.Counter()
    by_band = collections.defaultdict(lambda: collections.Counter())
    for p in sorted(names):
        ints = intents[p]
        ticks = sorted(t for (q, t) in cmds if q == p)
        all_n = sum(len(cmds[(p, t)]) for t in ticks)
        bursts = [t for t in ticks if len(cmds[(p, t)]) >= mn]
        if not bursts:
            print(f'{names[p]}: 陆攻落地 {all_n} 条，没有 ≥{mn} 条的批')
            continue
        sizes = collections.Counter(len(cmds[(p, t)]) for t in bursts)
        in_burst = sum(len(cmds[(p, t)]) for t in bursts)
        ok = okskip = 0
        d_new, d_old, drained, used = [], [], [], set()
        rows = []
        for T in bursts:
            seq = [c[0] for c in cmds[(p, T)]]
            r = find_run(seq, ints, T, False)
            how = '整段倒序对上'
            if r is None:
                r = find_run(seq, ints, T, True)
                how = '跳 1 条对上'
            bal0, bal1 = cmds[(p, T)][0][2], cmds[(p, T)][-1][3]
            frac = 1 - bal1 / bal0 if bal0 else 0
            drained.append(frac)
            all_sizes[len(seq)] += 1
            if bal1 == bal0:
                tot['没花批'] += 1
                tot['没花条'] += len(seq)
            if bal0 and bal1 < 0.4 * bal0:
                tot['抽干批'] += 1
            b = band(T)
            by_band[b]['批'] += 1
            by_band[b]['条'] += len(seq)
            if r is None:
                rows.append(f'  拍 {T:5d} {len(seq)} 条 [{",".join(map(str, seq))}] 没对上连续意图；余额 {bal0}→{bal1}（花掉 {frac:.0%}）')
                continue
            i0, i1, sk = r
            if sk is None:
                ok += 1
            else:
                okskip += 1
            by_band[b]['对上'] += 1
            for i in range(i0, i1 + 1):
                if i != sk:
                    used.add(i)
            dn, do = T - ints[i1][0], T - ints[i0][0]
            d_new.append(dn)
            d_old.append(do)
            by_band[b]['dn'] += dn
            rows.append(f'  拍 {T:5d} {len(seq)} 条 = 意图 {ints[i0][0]}~{ints[i1][0]} 倒序（{how}）；最新一条晚 {dn} 拍、最老一条晚 {do} 拍；余额 {bal0}→{bal1}（花掉 {frac:.0%}）')
        gaps = [b - a for a, b in zip(bursts, bursts[1:]) if b - a <= 300]
        print(f'{names[p]}: 陆攻落地 {all_n} 条，其中 {in_burst} 条在 {len(bursts)} 批里（批的大小 {dict(sorted(sizes.items()))}）；'
              f'整段倒序对上 {ok} 批、跳 1 条对上 {okskip} 批、没对上 {len(bursts) - ok - okskip} 批')
        if d_new:
            print(f'   对上的批：最新一条意图到落地 中位 {statistics.median(d_new):.0f} 拍（最小 {min(d_new)}、最大 {max(d_new)}）；最老一条 中位 {statistics.median(d_old):.0f} 拍')
        if gaps:
            print(f'   相邻两批相隔（≤300 拍的）中位 {statistics.median(gaps):.0f} 拍（最小 {min(gaps)}、最大 {max(gaps)}）；每批花掉余额 中位 {statistics.median(drained):.0%}、最多 {max(drained):.0%}')
        tot['批'] += len(bursts)
        tot['对上'] += ok + okskip
        if lst:
            print('\n'.join(rows))
    print('按时段：' + '；'.join(f'{b} {c["批"]} 批 {c["条"]} 条、对上 {c["对上"]} 批' + (f'（最新一条平均晚 {c["dn"] / c["对上"]:.0f} 拍）' if c['对上'] else '')
                            for b, c in sorted(by_band.items(), key=lambda kv: ['<630', '630~1499', '1500~2999', '3000~4283', '≥4284'].index(kv[0]))))
    print(f'合计 {tot["批"]} 批，对上 {tot["对上"]} 批')
    print('批的大小（条数: 批数）：' + '，'.join(f'{k}: {v}' for k, v in sorted(all_sizes.items()))
          + f'；余额一兵没动的批 {tot["没花批"]} 个共 {tot["没花条"]} 条；一批把余额抽到四成以下的 {tot["抽干批"]} 个')


if __name__ == '__main__':
    main()
