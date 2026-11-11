#!/usr/bin/env python3
"""retq.py — 对真人的陆攻：送出去的兵里烧掉多少、原路退回多少、手续费多少（按时段、按号）。

用法：python3 scripts/retq.py <mid> [切点,切点,…]      默认切点 0,1500,3000,4284,<结束>
数据：out/cache/<mid>-resim.json（和卷宗[E] 同一套区间账：dossier.Dossier.ledger）。
  出   = 这一段落地的、目标是在线真人的陆攻指令实际送出的兵（cmdLog 第 7 列）
  费   = 这些指令的手续费（每条 = 发令时余额的 12/1024，与送多少无关）
  烧   = pairLog 里这一段对真人消耗掉的兵（不含在槽里和对方进攻兵 1:1 对消的那部分）
  对消 = 这一段在槽里和对方进攻兵 1:1 抵掉的兵
  退   = 引擎把进攻槽里剩下的兵退回余额的量（snapRet 的差；含对中立/AI 的退兵，单列一栏对照）
注意：出/烧/退 不是同一批兵的严格分解（跨段在途、槽内对消都不在里面），只用来看量级。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(os.path.dirname(HERE))

from dossier import Dossier, k  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    D = Dossier(mid)
    end = D.R["endTick"]
    cuts = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 1500, 3000, 4284]
    cuts = sorted({c for c in cuts if c < end}) + [end]
    print(f"# {mid} 对真人陆攻的 出/费/烧/退（retq.py；区间 [a,b) 按落地拍；数取自重放）")
    tot = {}
    for b, pl in sorted(D.sq.items(), key=lambda x: x[1]):
        stop = min(D.alive_until(pl), end)
        segs = []
        for a, bnd in zip(cuts, cuts[1:]):
            if a >= stop:
                continue
            bnd = min(bnd, ((stop // 10) + 1) * 10)
            d = D.ledger(pl, a, bnd)
            s = d["sent"].get("H") or [0, 0, 0]
            g = [0, 0, 0]  # 得地, 烧（不含对消）, 对消
            ta, tb = D.T[D.ix(a)], D.T[D.ix(bnd)]
            for t, att, de, tiles, burnt, dB, dS, n in D.pair_att.get(pl, ()):
                if t <= ta or t > tb or D.cls(de, t) != "H":
                    continue
                g[0] += tiles; g[1] += burnt - dS; g[2] += dS
            sn = d["sent"].get("N") or [0, 0, 0]
            sa = d["sent"].get("AI") or [0, 0, 0]
            fee_all = s[1] + sn[1] + sa[1]
            segs.append(f"{a}~{bnd}: 真人 {s[2]} 条 出 {k(s[0])} 费 {k(s[1])} 烧 {k(g[1])} 对消 {k(g[2])} 得地 {g[0]} | 全部陆攻费 {k(fee_all)} | 退 {k(d['ret'])}")
            t = tot.setdefault((a, cuts[cuts.index(a) + 1] if a in cuts else bnd), [0, 0, 0, 0, 0, 0, 0, 0])
            t[0] += s[2]; t[1] += s[0]; t[2] += s[1]; t[3] += g[1]; t[4] += g[0]; t[5] += fee_all; t[6] += d["ret"]; t[7] += g[2]
        print(f"  {b:<7} " + " ‖ ".join(segs))
    print("  合计：")
    for (a, bnd), t in sorted(tot.items()):
        pct = f"（退÷出 {100 * t[6] / t[1]:.0f}%，费÷烧 {100 * t[2] / t[3]:.0f}%）" if t[1] and t[3] else ""
        print(f"    {a}~{bnd}: 真人 {t[0]} 条 出 {k(t[1])} 费 {k(t[2])} 烧 {k(t[3])} 对消 {k(t[7])} 得地 {t[4]} | 全部陆攻费 {k(t[5])} | 退 {k(t[6])} {pct}")


if __name__ == "__main__":
    main()
