#!/usr/bin/env python3
"""belowworth.py — 数一个时间窗里每个号的决策拍：有真人报价、报价已经低于 worth、却整拍没发令的有多少。

只读影子缓存 out/cache/<mid>-shadow.json 的 bots[号].acts（每个决策拍一行，格式见 scripts/acts.py 文件头），不重跑重放。
分类（每个决策拍只进一类，按下面的顺序判）：
  发令      本拍发了令（陆攻、船、调度/捐款都算；被围的后排的「发令」基本是调度）
  没报价    offers 里一条都没有（没有陆上邻居，或邻居都进不了报价表）
  过软上限  没发令，over=1（余额 > 100×地）
  低于worth 没发令，排第一的报价是真人、c < worth
  高于worth 没发令，排第一的报价是真人、c ≥ worth
  其它      没发令，排第一的报价不是真人
「低于worth」里再数一项「不给脉冲档」：排第一的报价 pulseMode=0 且 nearCollapse=0——这种报价在 buyLand 里只剩整吃档可走
（Vb L5611-5616：预算不够吃掉整个号、又不到余额的 chunk 就整拍不发）。只是按标记数，不重算预算。
用法：python3 scripts/belowworth.py <mid> <t0> <t1> [号 ...] [--brief]      区间按决策拍 [t0, t1]；--brief 只打合计行
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLS = ("发令", "没报价", "过软上限", "低于worth", "高于worth", "其它")


def classify(row):
    """返回 (类别, 是否不给脉冲档)。row 的格式见 acts.py 文件头。"""
    sent = row[10] if len(row) > 10 else 0
    worth, over = (row[11], row[12]) if len(row) > 13 else (-1, 0)
    offs = row[9] or []
    if sent:
        return "发令", False
    if not offs:
        return "没报价", False
    if over:
        return "过软上限", False
    o = offs[0]
    if not o[3]:
        return "其它", False
    if o[1] < worth:
        nopulse = len(o) > 7 and not o[7] and not o[4]
        return "低于worth", nopulse
    return "高于worth", False


def count(mid, t0, t1, want=()):
    """返回 (每个号的计数 dict, 合计 dict, 决策拍数, 每个号的明细)。"""
    sh = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-shadow.json"), encoding="utf-8"))
    per, det = {}, {}
    tot = dict.fromkeys(CLS + ("不给脉冲档",), 0)
    ticks = 0
    for bot, b in sh["bots"].items():
        if want and bot not in want:
            continue
        cnt = dict.fromkeys(CLS + ("不给脉冲档",), 0)
        lo, hi = [], []
        n = 0
        for row in b["acts"]:
            t = row[0]
            if t < t0 or t > t1:
                continue
            n += 1
            c, npulse = classify(row)
            cnt[c] += 1
            if npulse:
                cnt["不给脉冲档"] += 1
            if c in ("低于worth", "高于worth"):
                o = row[9][0]
                (lo if c == "低于worth" else hi).append((t, o[1], row[11], o[0], o[2], row[1]))
        if not n:
            continue
        cnt["决策拍"] = n
        per[bot] = cnt
        det[bot] = (lo, hi)
        ticks += n
        for c in tot:
            tot[c] += cnt[c]
    return per, tot, ticks, det


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    mid, t0, t1 = args[0], int(args[1]), int(args[2])
    brief = "--brief" in sys.argv
    per, tot, ticks, det = count(mid, t0, t1, set(args[3:]))
    rs = json.load(open(os.path.join(ROOT, "out", "cache", f"{mid}-resim.json"), encoding="utf-8"))
    names = rs["names"]

    def nm(q):
        if q is None or q < 0:
            return "-"
        if q < len(names):
            return "%s#%d" % (names[q].replace("[APEX] ", "")[:10], q)
        return "中立" if q == 512 else "AI%d" % q

    print(f"# {mid} 决策拍 {t0}~{t1}：报价低于 worth 却没出手的拍数（belowworth.py；读影子缓存的 acts）")
    if not brief:
        for bot, cnt in per.items():
            lo, hi = det[bot]
            line = f"  {bot:7s} 决策拍 {cnt['决策拍']}：" + "，".join(f"{c} {cnt[c]}" for c in CLS)
            if cnt["低于worth"]:
                line += f"（其中不给脉冲档 {cnt['不给脉冲档']}）"
            for tag, rows in (("低于worth", lo), ("高于worth", hi)):
                if rows:
                    a, z = rows[0], rows[-1]
                    tg = sorted({nm(r[3]) for r in rows})
                    line += (f" | {tag} {a[0]}~{z[0]} 拍：c {a[1]}→{z[1]} 对 worth {a[2]}→{z[2]}，need {int(a[4])}→{int(z[4])}，"
                             f"余额 {int(a[5])}→{int(z[5])}，目标 {'、'.join(tg)}")
            print(line)
    print(f"  合计 决策拍 {ticks}：" + "，".join(f"{c} {tot[c]}" for c in CLS) + f"（低于worth 里不给脉冲档 {tot['不给脉冲档']}）")


if __name__ == "__main__":
    main()
