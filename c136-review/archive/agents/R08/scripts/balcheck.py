#!/usr/bin/env python3
"""balcheck.py — 某个 bot 在两条快照之间的收支核对：按引擎利息/地租公式（不发兵、不挨打）应有多少余额，实际多少。

    python3 balcheck.py <matchId> <me|name> <t0> <t1>

分别用 t0 与 t1 的领土各算一遍（领土在窗口内变化时给出区间）。差额 = 实际 - 公式：
负数 = 窗口内净流出（出兵/船/捐款/挨打掉血/还欠款），正数 = 净流入（撤军回款/收到捐款）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts  # noqa: E402


def main():
    mid, who, t0, t1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    F = facts.build(mid)
    for me, b in F["bots"].items():
        if str(me) != who and b["name"] != who and who not in b["labels"]:
            continue
        a = facts.snap_at(b, t0, 0)
        c = facts.snap_at(b, t1, 0)
        if not a or not c:
            print("没有对应快照")
            return
        e0 = facts.interest_gain(a["terr"], F["land"], a["bal"], t0, t1)
        e1 = facts.interest_gain(c["terr"], F["land"], a["bal"], t0, t1)
        print(f"{mid} {b['name']}({me}) t={t0}->{t1}: terr {a['terr']}->{c['terr']} bal {a['bal']}->{c['bal']} "
              f"cmds+{c['cmds'] - a['cmds']} boats+{c['boats'] - a['boats']} nb {a['nb']}->{c['nb']}")
        print(f"  公式应有（按 t0 领土）{e0}，（按 t1 领土）{e1}；实际 {c['bal']}；差额 {c['bal'] - e0:+d} ~ {c['bal'] - e1:+d}")
        dterr = c["terr"] - a["terr"]
        if dterr > 0:
            print(f"  净流出/新增领土 = {(e0 - c['bal']) / dterr:.1f} ~ {(e1 - c['bal']) / dterr:.1f} 兵/格（新增 {dterr} 格）")
        elif dterr < 0:
            print(f"  失地 {-dterr} 格；按 [X15] 每失一格余额扣 floor(B/(1+floor(10L/16)))≈1.6×密度："
                  f"以 t0 密度 {a['dens']} 估计掉血 {int(-dterr * 1.6 * a['dens'])}")


if __name__ == "__main__":
    main()
