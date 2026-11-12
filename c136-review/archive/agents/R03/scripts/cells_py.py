#!/usr/bin/env python3
"""cells_py.py — 每个真人的「名下」格数，不用 node：直接读地图文件和重放缓存里的开局包围盒。

口径与 land-ledger.mjs 的 [G1]、cells.mjs 相同：每格陆地归直线距离最近的真人出生点。出生点这里取「选点期结束时那块地的
包围盒中心」（重放缓存的 startBox）；cells.mjs 取的是那块地的质心。开局那块地是对称的，两者相同；被海岸切掉一角的出生点
会差不到一格。本脚本把编队每个号算出来的格数与 land-facts.json 里的逐号格数对一遍，打印不一致的个数。

  输入：out/cache/<局>-resim.json（mapIdx、mapSeed、startBox、teams、squad）、c136-data/src/sim/maps/<图>_<种子>.bin.gz、
        out/dossier/<局>-land-facts.json（核对用）
  输出：out/council/cells-py/<局>.json（格式同 cells.mjs）、out/council/cells-py/_check.txt

用法：timeout 120 python3 scripts/cells_py.py
"""
import gzip
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "out")
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
MIDS = "A051 A087 A066 A025 A045 A067 A071 A090 A042 A046 A041".split()


def load_map(idx, seed):
    buf = gzip.open(os.path.join(DATA, "src", "sim", "maps", f"{idx}_{seed}.bin.gz")).read()
    assert buf[:4] == b"TMAP"
    w, h = struct.unpack("<HH", buf[4:8])
    typ = np.frombuffer(buf, dtype=np.uint8, count=w * h, offset=8)
    return w, h, typ == 1


def main():
    os.makedirs(os.path.join(OUT, "council", "cells-py"), exist_ok=True)
    lines = []
    tot = same = 0
    for m in MIDS:
        R = json.load(open(os.path.join(OUT, "cache", f"{m}-resim.json"), encoding="utf8"))
        w, h, land = load_map(R["mapIdx"], R["mapSeed"])
        H = R["H"]
        tg = R["nTeams"] >= 2
        sq = {s["id"]: b for b, s in R["squad"].items() if s["id"] >= 0}
        pts = []
        for p in range(H):
            sb = R["startBox"][p]
            if sb is None:
                continue
            pts.append({"id": p, "x": (sb[0] + sb[2]) / 2, "y": (sb[1] + sb[3]) / 2, "team": R["teams"][p] if tg else 0, "cells": 0, "squad": 1 if p in sq else 0})
        px = np.array([p["x"] for p in pts]); py = np.array([p["y"] for p in pts])
        idx = np.flatnonzero(land)
        xs = (idx % w).astype(np.float64); ys = (idx // w).astype(np.float64)
        counts = np.zeros(len(pts), dtype=np.int64)
        for a in range(0, len(idx), 20000):
            d = (xs[a:a + 20000, None] - px[None, :]) ** 2 + (ys[a:a + 20000, None] - py[None, :]) ** 2
            counts += np.bincount(np.argmin(d, axis=1), minlength=len(pts))
        for p, c in zip(pts, counts):
            p["cells"] = int(c)
        for p in pts:
            bd = min(math.hypot(q["x"] - p["x"], q["y"] - p["y"]) for q in pts if q["id"] != p["id"])
            p["nearest"] = round(bd)
        F = json.load(open(os.path.join(OUT, "dossier", f"{m}-land-facts.json"), encoding="utf8"))
        ok = n = 0
        worst = 0
        for p in pts:
            if not p["squad"]:
                continue
            ref = F["voronoi"]["perBot"].get(sq[p["id"]])
            if not ref:
                continue
            n += 1
            if ref["cells"] == p["cells"]:
                ok += 1
            worst = max(worst, abs(ref["cells"] - p["cells"]))
        tot += n; same += ok
        lines.append(f"{m} | 陆地 {int(land.sum()):,}（缓存 {R['land']:,}） | 开局有地真人 {len(pts)}（land-facts {F['voronoi']['humans']}） | 编队号 {n} 个，名下格数与 land-facts 相同的 {ok} 个，最大差 {worst} 格 | "
                     f"编队名下合计 {sum(p['cells'] for p in pts if p['squad']):,}（land-facts {F['voronoi']['squadCells']:,}）")
        json.dump({"matchId": m, "land": int(land.sum()), "W": w, "H": h, "humans": len(pts), "pts": pts},
                  open(os.path.join(OUT, "council", "cells-py", f"{m}.json"), "w", encoding="utf8"))
    lines.append(f"合计：编队号 {tot} 个，逐号格数与 land-facts 相同的 {same} 个")
    with open(os.path.join(OUT, "council", "cells-py", "_check.txt"), "w", encoding="utf8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
