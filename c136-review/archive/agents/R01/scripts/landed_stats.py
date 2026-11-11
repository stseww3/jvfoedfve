#!/usr/bin/env python3
"""landed_stats.py — 落地的进攻令按落地拍分窗：多少条生效、实扣多少兵、多少条落地时目标已经没了（引擎改打无主地）、
多少条一兵未扣、多少条是同拍 >=3 条的批次。读 out/<mid>/shadow_match.csv。
用法: python3 landed_stats.py <matchId> [--windows 600-900,900-1500,1500-1800,1800-99999] [--bot name]
说明：shTarget = 影子策略下令时的目标席位，target = 录像里落地时的目标（512 = 无主地）；
      两者不同且 target=512 就是“下令时的目标到落地时已死，引擎改打无主地”（game.js attack L1268）。
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def f(x):
    try:
        return float(x)
    except ValueError:
        return 0.0


def main():
    a = sys.argv[1:]
    mid = a[0]
    wins = a[a.index('--windows') + 1] if '--windows' in a else '600-900,900-1500,1500-1800,1800-99999'
    bot = a[a.index('--bot') + 1] if '--bot' in a else None
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, '..', 'out', mid, 'shadow_match.csv'))) if r['kind'] == 'attack']
    if bot:
        rows = [r for r in rows if r['bot'] == bot]
    print(f"== {mid} 落地的进攻令（按落地拍分窗{'，只看 ' + bot if bot else ''}）")
    for w in wins.split(','):
        t0, t1 = map(int, w.split('-'))
        xs = [r for r in rows if t0 <= int(r['tick']) < t1]
        app = [r for r in xs if r['applied'] == '1']
        dead = [r for r in xs if r['shTarget'] not in ('', '512') and r['target'] == '512']
        zero = [r for r in xs if f(r['spent']) == 0]
        big = [r for r in xs if int(r['n']) >= 3]
        lags = sorted(f(r['lag']) for r in xs if r['lag'] not in ('', '-1'))
        med = lags[len(lags) // 2] if lags else float('nan')
        print(f"   [{t0},{t1}) 落地 {len(xs)} 条，生效 {len(app)}，实扣合计 {sum(f(r['spent']) for r in xs):.0f}；"
              f"落地时目标已变无主地 {len(dead)} 条（其中一兵未扣 {sum(1 for r in dead if f(r['spent']) == 0)}）；一兵未扣 {len(zero)}；"
              f"同拍 >=3 条的批次里 {len(big)} 条，实扣 {sum(f(r['spent']) for r in big):.0f}；能定位决策拍的延迟中位 {med:.0f}")


if __name__ == '__main__':
    main()
