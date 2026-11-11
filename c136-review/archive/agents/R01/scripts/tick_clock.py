#!/usr/bin/env python3
"""tick_clock.py — 全量机械计数：RESULT 行的墙上时间（seconds，开局算起）和局内拍（tick）对不对得上。
只读每个对局包的 results.csv。
做法：
  1. 用所有 event != left 的 RESULT 行（阵亡、获胜）拟合 seconds = a + b×tick（最小二乘），b 就是每拍多少秒，a 是开局前的等待。
     这些行是客户端跟着服务器走到那一拍时写的，所以给出的是“正常的钟”。
  2. 对每条 event=left 的行算 残差 = seconds − (a + b×tick)：客户端停在 tick 这一拍之后，又过了多少秒才写下 RESULT。
     残差大 = 客户端的局内拍停住了、墙上时间还在走（看门狗超时或断线后才收场）。
用法: python3 tick_clock.py [matchId ...] [--min-resid 5] [--per-match]
  给了 matchId 就只列这些局的 left 行（拟合仍用全量）；--per-match 每局另用本局的非 left 行算一次残差中位（校验 a 是否逐局不同）。
输出：拟合的 a、b、非 left 行残差的分位数；left 行逐条（局、号、tick、seconds、残差）；末尾按残差分档计数。
"""
import csv, os, sys, statistics

DATA = '/agent/repos/c136-data/bundles'


def load_rows():
    rows = []
    for mid in sorted(os.listdir(DATA)):
        rp = os.path.join(DATA, mid, 'results.csv')
        if not os.path.exists(rp):
            continue
        for r in csv.DictReader(open(rp)):
            try:
                t = float(r['tick']); s = float(r['seconds'])
            except (ValueError, KeyError):
                continue
            rows.append((mid, r['bot'], r['event'], t, s))
    return rows


def fit(rows=None):
    """返回 (a, b, 非 left 行的残差列表, 非 left 行)。seconds = a + b×tick。"""
    rows = rows if rows is not None else load_rows()
    norm = [x for x in rows if x[2] != 'left' and x[3] > 0]
    n = len(norm)
    mx = sum(x[3] for x in norm) / n; my = sum(x[4] for x in norm) / n
    sxx = sum((x[3] - mx) ** 2 for x in norm); sxy = sum((x[3] - mx) * (x[4] - my) for x in norm)
    b = sxy / sxx; a = my - b * mx
    res = sorted(x[4] - (a + b * x[3]) for x in norm)
    return a, b, res, norm


def main():
    argv = sys.argv[1:]
    min_resid = float(argv[argv.index('--min-resid') + 1]) if '--min-resid' in argv else 5.0
    per_match = '--per-match' in argv
    skip = set()
    if '--min-resid' in argv:
        skip.add(argv.index('--min-resid')); skip.add(argv.index('--min-resid') + 1)
    want = [a for i, a in enumerate(argv) if i not in skip and not a.startswith('--')]
    rows = load_rows()
    a, b, res, norm = fit(rows)
    q = lambda p: res[min(len(res) - 1, int(p * len(res)))]
    print(f"# 非 left 行 {len(norm)} 条：seconds = {a:.1f} + {b * 1000:.2f} 毫秒 × tick；残差 p5/p50/p95/最大 = {q(0.05):.1f}/{q(0.5):.1f}/{q(0.95):.1f}/{res[-1]:.1f} 秒")
    off = {}
    if per_match:
        by = {}
        for x in norm:
            by.setdefault(x[0], []).append(x[4] - b * x[3])
        off = {m: statistics.median(v) for m, v in by.items()}
        vals = sorted(off.values())
        print(f"# 逐局的 a（本局非 left 行 seconds − b×tick 的中位）：{len(vals)} 局，最小/中位/最大 = {vals[0]:.1f}/{statistics.median(vals):.1f}/{vals[-1]:.1f} 秒")
    left = [x for x in rows if x[2] == 'left']
    bins = {'<5': 0, '5-15': 0, '15-30': 0, '30-60': 0, '>=60': 0}
    print('matchId bot tick seconds resid(s)' + (' residLocal(s)' if per_match else ''))
    for mid, bot, ev, t, s in left:
        r = s - (a + b * t)
        k = '<5' if r < 5 else '5-15' if r < 15 else '15-30' if r < 30 else '30-60' if r < 60 else '>=60'
        bins[k] += 1
        if (want and mid not in want) or (not want and r < min_resid):
            continue
        extra = ''
        if per_match:
            extra = f" {s - (off[mid] + b * t):.1f}" if mid in off else ' -'
        print(mid, bot, int(t), int(s), f"{r:.1f}" + extra)
    print(f"# left 行 {len(left)} 条，残差分档：" + ' '.join(f"{k}:{v}" for k, v in bins.items()))


if __name__ == '__main__':
    main()
