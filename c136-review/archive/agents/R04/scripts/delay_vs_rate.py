#!/usr/bin/env python3
# delay_vs_rate.py — 指令延迟和「下单密度」的关系：一个号连续每个决策拍都下单时，延迟是不是跟着涨。
# 用法：python3 scripts/delay_vs_rate.py <局号> [<局号> …] [--win 50] [--fine]      --fine：编队密度再按 3 条一档细分
#   对每条能配上的落地指令（exec_gap 的宽配对）：
#     自己的密度 = 这个号在决策拍之前 win 拍内（含本拍）的意图条数；
#     编队的密度 = 录像里全部我方号在同一窗口内的意图条数。
#   按密度分档给延迟（执行拍 − 决策拍）的条数 / P50 / P90 和落地率；
#   另给吞吐（每 105 拍一格：编队想发几条 → 录像里落地几条）和成批落地的节拍（同一个号相邻两批相隔多少拍）。
# 输出另写 tmp/rate/<局号>.json。
import sys, os, json, collections, bisect
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import exec_gap  # noqa: E402

OWN = [(1, 1, '1 条'), (2, 3, '2~3 条'), (4, 6, '4~6 条'), (7, 99, '≥7 条')]
SQ = [(1, 5, '1~5 条'), (6, 15, '6~15 条'), (16, 30, '16~30 条'), (31, 999, '≥31 条')]


def pq(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else None


def one(mid, win):
    intents, cmds, check = exec_gap.load(mid)
    ours = {b['p']: b['bot'] for b in check['bots']}
    pairs, rest, lone = exec_gap.match(intents, [c for c in cmds if c['p'] in ours])
    byp = collections.defaultdict(list)
    for x in intents:
        byp[x['p']].append(x['t'])
    for v in byp.values():
        v.sort()
    allt = sorted(x['t'] for x in intents)

    def dens(ts, t):
        return bisect.bisect_right(ts, t) - bisect.bisect_right(ts, t - win)

    landed = {id(x): c['t'] - x['t'] for x, c in pairs}
    rows = [(dens(byp[x['p']], x['t']), dens(allt, x['t']), landed.get(id(x)), x['t']) for x in intents if x['kind'] in ('attack', 'donate', 'boat')]
    print('# %s 指令延迟对下单密度（窗口 %d 拍；意图 %d 条，其中落地 %d 条）' % (mid, win, len(rows), sum(1 for r in rows if r[2] is not None)))
    out = dict(match=mid, win=win, own={}, squad={}, squadFine={})
    fine = [(1, 3, '1~3'), (4, 6, '4~6'), (7, 9, '7~9'), (10, 12, '10~12'), (13, 15, '13~15'), (16, 20, '16~20'), (21, 30, '21~30'), (31, 999, '≥31')]
    for lab, idx, bins, key in (('自己的密度', 0, OWN, 'own'), ('编队的密度', 1, SQ, 'squad')) + ((('编队的密度（细档）', 1, fine, 'squadFine'),) if FINE else ()):
        cells = []
        for lo, hi, name in bins:
            sel = [r for r in rows if lo <= r[idx] <= hi]
            lag = [r[2] for r in sel if r[2] is not None]
            if not sel:
                continue
            cells.append('%s：意图 %d 条、落地 %d 条（%.0f%%），延迟 P50/P90 %s/%s' % (name, len(sel), len(lag), 100.0 * len(lag) / len(sel), pq(lag, .5), pq(lag, .9)))
            out[key][name] = dict(n=len(sel), landed=len(lag), p50=pq(lag, .5), p90=pq(lag, .9))
        print('  %s —— ' % lab + '；'.join(cells))
    # 两维交叉：自己稀（≤1 条）而编队密，自己密而编队稀
    for lab, f in (('自己 1 条、编队 ≥16 条', lambda r: r[0] <= 1 and r[1] >= 16), ('自己 1 条、编队 ≤5 条', lambda r: r[0] <= 1 and r[1] <= 5),
                   ('自己 ≥4 条、编队 ≤15 条', lambda r: r[0] >= 4 and r[1] <= 15), ('自己 ≥4 条、编队 ≥16 条', lambda r: r[0] >= 4 and r[1] >= 16)):
        sel = [r for r in rows if f(r)]
        lag = [r[2] for r in sel if r[2] is not None]
        if sel:
            print('  交叉 %s：意图 %d 条、落地 %d 条（%.0f%%），延迟 P50/P90 %s/%s' % (lab, len(sel), len(lag), 100.0 * len(lag) / len(sel), pq(lag, .5), pq(lag, .9)))
            out.setdefault('cross', {})[lab] = dict(n=len(sel), landed=len(lag), p50=pq(lag, .5), p90=pq(lag, .9))
    # 吞吐：把全局切成 105 拍（15 个回合）一格，数这一格里编队想发几条、录像里落地几条
    last = max(allt) if allt else 0
    wins = []
    ourc = [c for c in cmds if c['p'] in ours and c['id'] in (1, 2, 3, 4, 5)]
    lt = sorted(c['t'] for c in ourc)
    for lo in range(0, last + 1, 105):
        w = bisect.bisect_left(allt, lo + 105) - bisect.bisect_left(allt, lo)
        l = bisect.bisect_left(lt, lo + 105) - bisect.bisect_left(lt, lo)
        wins.append((lo, w, l))
    cells = []
    for lo, hi, name in ((0, 14, '想发 <15 条'), (15, 39, '15~39 条'), (40, 79, '40~79 条'), (80, 9999, '≥80 条')):
        sel = [x for x in wins if lo <= x[1] <= hi]
        if not sel:
            continue
        ls = [x[2] for x in sel]
        cells.append('%s 的 %d 格：落地 中位 %s、最多 %s 条' % (name, len(sel), pq(ls, .5), max(ls)))
        out.setdefault('throughput', {})[name] = dict(windows=len(sel), landedP50=pq(ls, .5), landedMax=max(ls))
    print('  吞吐（每 105 拍 = 15 个回合一格，全部我方号合计）—— ' + '；'.join(cells) + '；全局单格落地最多 %d 条（= 每回合 %.1f 条）' % (
        max(x[2] for x in wins), max(x[2] for x in wins) / 15.0))
    out['throughputMax'] = max(x[2] for x in wins)
    # 成批落地的节拍：同一个号相邻两批（同拍 ≥3 条陆攻）相隔多少拍
    bt = collections.defaultdict(list)
    cnt = collections.Counter((c['p'], c['t']) for c in ourc if c['id'] == 1)
    for (p, t), n in sorted(cnt.items()):
        if n >= 3:
            bt[p].append(t)
    gaps = collections.defaultdict(list)
    for p, ts in bt.items():
        for i in range(1, len(ts)):
            if ts[i] - ts[i - 1] <= 450:
                gaps['<1500' if ts[i] < 1500 else '1500~2999' if ts[i] < 3000 else '3000+'].append(ts[i] - ts[i - 1])
    if gaps:
        print('  成批落地的节拍（同一个号相邻两批相隔的拍数，只算 ≤450 拍的）—— ' + '；'.join(
            '%s：%d 对，中位 %s、最小 %s、最大 %s' % (k, len(v), pq(v, .5), min(v), max(v)) for k, v in gaps.items()))
        out['batchGap'] = {k: dict(n=len(v), p50=pq(v, .5), min=min(v), max=max(v)) for k, v in gaps.items()}
    d = os.path.join(ROOT, 'tmp', 'rate')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False)


FINE = False


def main():
    global FINE
    a = sys.argv[1:]
    FINE = '--fine' in a
    win = int(a[a.index('--win') + 1]) if '--win' in a else 50
    for mid in [x for x in a if not x.startswith('--') and not x.isdigit()]:
        one(mid, win)


if __name__ == '__main__':
    main()
