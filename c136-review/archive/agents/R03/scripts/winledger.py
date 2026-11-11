#!/usr/bin/env python3
"""winledger.py — 同一个时间窗里，编队和其它各组真人「收入多少、花到哪里去了」的对照账。

数据：out/cache/<mid>-resim.json（重放精确值），算法直接用 dossier.py 的 Dossier.ledger(pl, a, b)，和卷宗 [E] 同一套口径：
  利息 = snapInc 的差；出/费 = cmdLog 里这一段落地的陆攻指令（按目标当时是 中立/AI/真人 分）；烧、得地 = pairLog（30 拍一桶，桶末拍落在 (a, b] 的行）；
  挨打掉兵/失地 = pairLog 里别人打它的行；捐出到账/税、收捐 = cmdLog 的成交捐款；船 = cmdLog 的发船（上船的兵、船费）；退兵 = snapRet 的差。
分组：编队（本房间的编队号）；各队里不是编队号的真人（按队）。离线后由内置 AI 托管的空壳也算在所在的队里（它的指令不在 cmdLog 里）。
每组一行：窗口两端 有地的人数、地、兵；窗口里 利息；对真人 出/费/烧/得地；对 AI+中立 烧/得地；挨打 掉兵/失地；捐出到账/税（组内互捐也算）；船 上船兵/船费；
          三项费（陆攻手续费 + 捐款税 + 船费）与它占利息的百分比。

用法：python3 scripts/winledger.py <mid> <t0> <t1> [<t0> <t1> …]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dossier import Dossier, k  # noqa: E402


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    ts = [int(x) for x in sys.argv[2:]]
    D = Dossier(mid)
    R = D.R
    H, teams = D.H, R["teams"]
    sqids = set(D.sqids)
    groups = [("编队", sorted(sqids))]
    for T in sorted(set(teams[:H])):
        if T <= 0 and D.team_game:
            continue
        ids = [p for p in range(H) if teams[p] == T and p not in sqids]
        if ids:
            groups.append((f"队{T}" + ("路人" if T == D.my_team else ""), ids))
    print(f"# {mid} 时间窗对照账（winledger.py；口径同卷宗[E]；组内互捐算在捐出里）")
    for i in range(0, len(ts) - 1, 2):
        a, b = ts[i], ts[i + 1]
        ia, ib = D.ix(a), D.ix(b)
        print(f"  == {a}~{b} 拍 ==")
        for name, ids in groups:
            n0 = sum(1 for p in ids if R["snapTerr"][ia][p] > 0)
            n1 = sum(1 for p in ids if R["snapTerr"][ib][p] > 0)
            L0 = sum(R["snapTerr"][ia][p] for p in ids)
            L1 = sum(R["snapTerr"][ib][p] for p in ids)
            B0 = sum(R["snapBal"][ia][p] for p in ids)
            B1 = sum(R["snapBal"][ib][p] for p in ids)
            inc = ret = 0
            sentH = [0, 0, 0]
            feeAll = 0
            burnH = tilesH = burnO = tilesO = 0
            defBal = defTiles = 0
            don = [0, 0, 0]
            donIn = 0
            boat = [0, 0, 0]
            for p in ids:
                d = D.ledger(p, a, b)
                inc += d["inc"]
                ret += d["ret"]
                for cl, s in d["sent"].items():
                    feeAll += s[1]
                    if cl == "H":
                        sentH[0] += s[0]; sentH[1] += s[1]; sentH[2] += s[2]
                for cl, g in d["gain"].items():
                    if cl == "H":
                        tilesH += g[0]; burnH += g[1]
                    else:
                        tilesO += g[0]; burnO += g[1]
                for x in d["lost"].values():
                    defTiles += x[0]; defBal += x[1]
                don[0] += d["don_out"][0]; don[1] += d["don_out"][1]; don[2] += d["don_out"][2]
                donIn += d["don_in"]
                boat[0] += d["boat"][0]; boat[1] += d["boat"][1]; boat[2] += d["boat"][2]
            fees = feeAll + don[1] + boat[1]
            pct = f"{100.0 * fees / inc:.1f}%" if inc > 0 else "—"
            print(f"  {name}：有地 {n0}→{n1} 人，地 {L0}→{L1}，兵 {k(B0)}→{k(B1)} | 利息 {k(inc)} | "
                  f"对真人 {sentH[2]} 条 出 {k(sentH[0])} 费 {k(sentH[1])} 烧 {k(burnH)} 得地 {tilesH} | 对 AI/中立 烧 {k(burnO)} 得地 {tilesO} | "
                  f"挨打 掉兵 {k(defBal)} 失地 {defTiles} | 捐出 {don[2]} 笔 到账 {k(don[0])} 税 {k(don[1])}（收捐 {k(donIn)}） | "
                  f"船 {boat[2]} 条 {k(boat[0])} 费 {k(boat[1])} | 退兵 {k(ret)} | 三项费 {k(fees)} = 利息的 {pct}")


if __name__ == "__main__":
    main()
