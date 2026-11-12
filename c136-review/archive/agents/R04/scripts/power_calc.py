#!/usr/bin/env python3
# power_calc.py — 用胜率当门禁指标时，每一组要跑多少局才分得出差别（两比例 z 检验，双侧 α=0.05，把握度 80%）。
# 用法：python3 scripts/power_calc.py > out/m7/power.txt
#   基线胜率取全量对局包里的实际值（out/bundle_patterns.txt：122 局里 15 局赢）；
#   对比几个假想的改进后胜率。只是量级参考：不配对、不分层，实际门禁应当用配对设计（同图同种子同对手）把局数压下来。
import math, os, re, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZA, ZB = 1.959964, 0.841621


def n_per_arm(p1, p2):
    pb = (p1 + p2) / 2.0
    a = ZA * math.sqrt(2 * pb * (1 - pb)) + ZB * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return int(math.ceil(a * a / ((p1 - p2) ** 2)))


def wilson(k, n, z=ZA):
    p = k / float(n)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / d
    return c - h, c + h


def main():
    txt = open(os.path.join(ROOT, 'out', 'bundle_patterns.txt'), encoding='utf8').read()
    m = re.search(r'全部 ：(\d+) 局，主队赢 (\d+) 局', txt)
    if not m:
        raise SystemExit('bundle_patterns.txt 里找不到「全部 ：N 局，主队赢 K 局」')
    n, k = int(m.group(1)), int(m.group(2))
    lo, hi = wilson(k, n)
    print('基线：全量对局包 %d 局里主队赢 %d 局（%.1f%%；Wilson 95%% 区间 %.1f%%~%.1f%%）' % (n, k, 100.0 * k / n, 100 * lo, 100 * hi))
    p1 = k / float(n)
    for p2 in (0.20, 0.25, 0.34, 0.50):
        print('  胜率 %.1f%% → %.0f%%：每组要 %d 局' % (100 * p1, 100 * p2, n_per_arm(p1, p2)))
    print('说明：两比例 z 检验，双侧 α=0.05、把握度 80%，两组独立、不配对；配对设计（同图、同种子、同对手、同通道种子）需要的局数更少，少多少取决于两组结果的相关程度，要在模拟器上实测。')
    for nn in (50, 100, 200, 400):
        lo, hi = wilson(round(p1 * nn), nn)
        print('  跑 %d 局、胜率和基线一样时，Wilson 95%% 区间的宽度：%.1f%%~%.1f%%' % (nn, 100 * lo, 100 * hi))


if __name__ == '__main__':
    main()
