#!/usr/bin/env python3
# 出生阵型一览：每局我方号出生点的间距、与人均地盘半径 rCell 的比例，以及后果指标。
# 用法：python3 scripts/spawn_geometry.py [局号…]（不给局号 = tmp/truth 下全部）
# 口径：出生点 = 真引擎重放 meta.json 里每个玩家最终出生方块的中心；rCell = sqrt(陆地像素 /(π×真人数))；
#   最近队友 = 同队任何真人（含非我方号）；后果指标取 state.tsv 的拍 630 / 1530 快照（没出生的号不计）。
import sys, os, json, math, statistics
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match

OURS_B034 = [38, 27, 26, 22, 30, 48, 45, 31, 41]


def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'truth')
    ms = sys.argv[1:] or sorted(os.listdir(base))
    print('局 | 我方号数/真人数 | rCell | 到最近队友的距离：最小/中位/最大（÷rCell 中位） | 间距<0.6×rCell 的号 | 60像素内有≥2个队友的号 | 到最近敌方真人：中位 | 拍630 我方领土中位÷别人中位 | 拍1530 同上 | 拍1530 我方密度中位÷别人')
    for m in ms:
        if not os.path.exists(os.path.join(base, m, 'meta.json')):
            continue
        M = Match(m, OURS_B034 if m == 'B034' else None)
        meta = json.load(open(os.path.join(base, m, 'meta.json')))
        info = meta['info']
        hum = info['ku']
        rc = math.sqrt(info['ke'] / (math.pi * hum))
        pl = {x['p']: x for x in meta['players'] if x['p'] < hum}
        ok = lambda p: p in pl and pl[p]['box'][0] <= pl[p]['box'][2]
        ours = [p for p in M.our_ids if ok(p)]
        if not ours:
            continue
        team = pl[ours[0]]['team']
        d_ally, d_en, n60 = [], [], 0
        for p in ours:
            x, y = pl[p]['spawn']
            da = [math.hypot(x - pl[q]['spawn'][0], y - pl[q]['spawn'][1]) for q in pl if q != p and ok(q) and pl[q]['team'] == team]
            de = [math.hypot(x - pl[q]['spawn'][0], y - pl[q]['spawn'][1]) for q in pl if ok(q) and pl[q]['team'] != team]
            if da:
                d_ally.append(min(da))
                n60 += 1 if sum(1 for v in da if v <= 60) >= 2 else 0
            if de:
                d_en.append(min(de))

        def ratio(t, f):
            S = M.state[M.at(t)]
            a = [f(S[p]) for p in ours if p in S and S[p][0] > 0]
            b = [f(S[p]) for p in S if p < hum and p not in M.our_ids and S[p][0] > 0]
            if not a or not b:
                return float('nan')
            return statistics.median(a) / max(1e-9, statistics.median(b))
        med = statistics.median(d_ally) if d_ally else float('nan')
        print('%s | %d/%d | %.1f | %s | %d | %d | %.0f | %.2f | %.2f | %.2f' % (
            m, len(ours), hum, rc,
            ('%.0f/%.0f/%.0f（%.2f）' % (min(d_ally), med, max(d_ally), med / rc)) if d_ally else '没有队友',
            sum(1 for v in d_ally if v < 0.6 * rc), n60,
            statistics.median(d_en) if d_en else float('nan'),
            ratio(630, lambda s: s[0]), ratio(1530, lambda s: s[0]), ratio(1530, lambda s: s[1] / max(1, s[0]))))


if __name__ == '__main__':
    main()
