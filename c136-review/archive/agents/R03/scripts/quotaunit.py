#!/usr/bin/env python3
"""quotaunit.py — 这张图上受捐额度「1 点」值多少兵（只做引擎公式的代入，不读对局过程）。

用法：python3 scripts/quotaunit.py <mid> [<mid> …]
引擎 src/sim/sim/game.js donationCost（L348-357）：
  t < 3213：每笔点数 = 2 + floor(100·到账 / (k·uv))，uv = 1 + floor(全图陆地/300)，k = 1/4/10/30/100（分界 357/714/1071/2142）
  t ≥ 3213：每笔点数 = 4 + floor(100·到账 / 受捐方软上限)；t ≥ 4284 不限
  上限从 15 点起，每逢 t%100==99 加 4（t<1071）/6（<2142）/8（<3213）/10（之后）
所以 t<3213 时「每点」= k·uv/100 个兵；上限每 100 拍涨的点数 × 每点的兵 = 每 100 拍多放行的兵。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BANDS = [(0, 357, 1, 4), (357, 714, 4, 4), (714, 1071, 10, 4), (1071, 2142, 30, 6), (2142, 3213, 100, 8)]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    for mid in sys.argv[1:]:
        f = json.load(open(os.path.join(ROOT, "out", "dossier", f"{mid}-facts.json")))
        land = f["land"]
        uv = 1 + land // 300
        print(f"# {mid} 图陆地 {land:,} 格 → uv = 1 + floor(陆地/300) = {uv:,}")
        for a, b, kk, grow in BANDS:
            per = kk * uv / 100
            print(f"  {a:>4}~{b - 1:<4} 拍：k={kk:<3} 每点 {per:,.1f} 兵；上限每 100 拍 +{grow} 点 = 每 100 拍多放行 {grow * per:,.0f} 兵")
        print("  3213~4283 拍：每笔 4 + floor(100·到账 / 受捐方软上限)，上限每 100 拍 +10 点；4284 拍起不限")


if __name__ == "__main__":
    main()
