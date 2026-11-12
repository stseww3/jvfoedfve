#!/usr/bin/env python3
"""fidlist.py — 保真度系列脚本（fidabl / engdiff / namepool / deathbank）共用的局单。

从 out/_cross/xtruth.json 里取「重演和日志逐行对得上、且有对局段」的局，按开局真人数从小到大排，
写到 out/_run/fidabl_list.json：[[局, 真人数, 编队档], …]。

    python3 fidlist.py            # 写文件并打印局数
    python3 fidlist.py squad20    # 另外把某一档的局号打印成一行（给批处理脚本用）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def build():
    X = json.load(open(os.path.join(OUT, "_cross", "xtruth.json"), encoding="utf-8"))
    lst = [[m["matchId"], m["H"], m["cohort"]] for m in X["matches"] if m.get("valid") and not m.get("spawnOnly")]
    lst.sort(key=lambda r: (r[1], r[0]))
    return lst


def main():
    lst = build()
    os.makedirs(os.path.join(OUT, "_run"), exist_ok=True)
    json.dump(lst, open(os.path.join(OUT, "_run", "fidabl_list.json"), "w", encoding="utf-8"))
    if len(sys.argv) > 1:
        print(" ".join(m for m, _, c in lst if c == sys.argv[1]))
    else:
        print(f"{len(lst)} 局：" + "；".join(f"{c} {sum(1 for r in lst if r[2] == c)}" for c in sorted({r[2] for r in lst})))


if __name__ == "__main__":
    main()
