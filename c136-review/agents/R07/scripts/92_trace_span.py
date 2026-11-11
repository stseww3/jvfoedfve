#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""92_trace_span.py — 把一局里所有号的影子逐拍明细按「时间段 × 号」合起来数：出价和目标成本差多少、每道闸挡了多少拍、过软上限后发了多少兵。R07

用法（在 scripts/ 目录下）：
    python3 92_trace_span.py <matchId> --span t0:t1 [--span t0:t1 ...] [--target 名字片段:t1,t2,...]...

输入：out/<matchId>/shadow_trace_<号>_<t0>_<t1>.txt（65_shadow.mjs --trace 的输出；同一个号的多个文件按拍号合并去重）。
口径（全部是影子值：同一份策略源码在重演出的真实局面上重算的）：
  · 决策拍 = 明细里的一段（buyLand 被调用的拍）。「有真人候选」= 报价单里至少有一行带「人」。
  · 最便宜的真人候选 = 报价单里 c 最小的真人行；c 是 offers() 算出的每格成本（已乘各种系数），worth 是 buyLand 的出价（m × 参考密度）。
    c ÷ worth > 1 就是「价高」；need ÷ B 是吃光它要的兵除以自己的余额；dq ÷ d 是它的密度除以自己的密度。
  · 零指令的决策拍按报价单第一行的结论归类（与 87_trace_classify.py 同一套）。「在途」= 对这个目标已经压着的兵过了门槛（Vb L5575 / L5589 / L5596）；
    「低于最小指令」= 过了比价和留底，但算出来要发的兵 x < max(minCmd, pulseMinShare×B)（minCmd = feeK × 手续费，Vb L474-476；跳过在 L5583 / L5591 / L5605）；
    「不够一条」= 非脉冲分支 x < want 且 x < chunk×B（L5612）。这三类是 65_shadow.mjs 的 sizeOf() 按源码复刻的。
  · 「出手但跳过了更便宜的」= 这一拍发了进攻，而报价单里排在被打目标前面的某一行是「低于最小指令」。
  · 出手 = 这一拍影子发了 attack（打真人 / 内置 AI / 离开席位）；over=1 是表头里的过软上限标记；「约 N 兵」是影子按发令拍余额估的。
  · --target：在给定的决策拍，把「报价单里有这个目标」的号排在一起：各自的余额 B、领土 L、出价 worth、对它的每格成本 c、吃光它要的兵 need；
    最后一行是这些号的余额合计 ÷ need 的最大值（几个号的兵加起来够不够吃光它）。
输出：out/<matchId>/trace_span.txt
  每个时间段一张表：每号一行 + 合计一行；每个 --target 一张表；最后一张「低于最小指令」明细（号 × 目标，全部明细拍，不按时间段）。
"""
import glob
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = re.compile(r'^t=(\d+) (\S+) B=(-?\d+) L=(\d+) d=([\d.]+).*?worth=([\d.]+).*?over=(\d)')
OFFER = re.compile(r'^\s+→ (.+?) terr=(\d+) bal=(-?\d+) dq=([\d.]+).*?\| c=([\d.]+).*?need=(-?\d+) tD=[\d.]+ ([^|]*)\|(.*)$')
CMD = re.compile(r'⇒ 影子指令 (\w+) pct=(\d+) → (.+?)（约 (\d+) 兵）')


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def load(out):
    """bot -> {t: (B, L, d, worth, over, offers[(name, terr, bal, dq, c, need, tags, tail)], cmd)}"""
    data = defaultdict(dict)
    for f in sorted(glob.glob(os.path.join(out, "shadow_trace_*.txt"))):
        cur = None
        for ln in open(f, encoding="utf-8"):
            ln = ln.rstrip("\n")
            m = HEAD.match(ln)
            if m:
                t, bot = int(m.group(1)), m.group(2)
                cur = {"B": int(m.group(3)), "L": int(m.group(4)), "d": float(m.group(5)), "worth": float(m.group(6)), "over": m.group(7) == "1", "offers": [], "cmd": None}
                data[bot][t] = cur
                continue
            if cur is None:
                continue
            om = OFFER.match(ln)
            if om:
                cur["offers"].append((om.group(1), int(om.group(2)), int(om.group(3)), float(om.group(4)), float(om.group(5)), int(om.group(6)), om.group(7), om.group(8)))
                continue
            cm = CMD.search(ln)
            if cm:
                cur["cmd"] = (cm.group(1), int(cm.group(2)), cm.group(3), int(cm.group(4)))
    return data


def main():
    args = sys.argv[1:]
    if not args or ("--span" not in args and "--target" not in args):
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    spans = [tuple(int(x) for x in args[i + 1].split(":")) for i, a in enumerate(args) if a == "--span"]
    out = os.path.join(HERE, "..", "out", mid)
    data = load(out)
    L = [f"# {mid} 影子逐拍明细按时间段合计（92_trace_span.py；全部是影子值）",
         "# 列：决策拍 | 有真人候选 | 零指令·价高 | 零指令·唯一真人邻居闸 | 零指令·crowdedHard 闸 | 零指令·可用兵≤0 | 零指令·没有候选 | 零指令·在途 | 零指令·低于最小指令 | 零指令·不够一条 | 零指令·其他 | 捐兵拍 | 出手拍（约兵）| 其中 over=1（约兵）| 其中 c≥worth（约兵）| 出手但跳过了更便宜的（约兵）"
         " | 最便宜真人候选的 c÷worth 中位数（最小~最大）| need÷B 中位数 | 自己密度中位数 | 该候选密度中位数 | 候选行带 crowdedHard / sole / onMe 的拍数", ""]
    for t0, t1 in spans:
        L.append(f"## t={t0}~{t1}")
        tot = Counter()
        tot_ratio, tot_needb = [], []
        for bot in sorted(data):
            ticks = sorted(t for t in data[bot] if t0 <= t <= t1)
            if not ticks:
                continue
            c = Counter()
            ratio, needb, dme, dq = [], [], [], []
            for t in ticks:
                b = data[bot][t]
                c["n"] += 1
                hum = [o for o in b["offers"] if "人" in o[6]]
                if hum:
                    c["hum"] += 1
                    o = min(hum, key=lambda x: x[4])
                    if b["worth"] > 0:
                        ratio.append(o[4] / b["worth"])
                    if b["B"] > 0:
                        needb.append(o[5] / b["B"])
                    dme.append(b["d"])
                    dq.append(o[3])
                    if "crowdedHard" in o[6]:
                        c["tagHard"] += 1
                    if "sole" in o[7]:
                        c["tagSole"] += 1
                    if "onMe" in o[6]:
                        c["tagOnMe"] += 1
                cmd = b["cmd"]
                if cmd is None:
                    if not b["offers"]:
                        c["z_none"] += 1
                    else:
                        tail = b["offers"][0][7]
                        if "价高" in tail:
                            c["z_dear"] += 1
                        elif "无可用" in tail:
                            c["z_avail"] += 1
                        elif "唯一真人邻居" in tail:
                            c["z_sole"] += 1
                        elif "crowdedHard" in tail and "continue" in tail:
                            c["z_hard"] += 1
                        elif "在途(" in tail:
                            c["z_fly"] += 1
                        elif "低于最小指令(" in tail:
                            c["z_min"] += 1
                        elif "不够一条(" in tail:
                            c["z_short"] += 1
                        else:
                            c["z_other"] += 1
                elif cmd[0] == "donate":
                    c["don"] += 1
                elif cmd[0] == "attack" and "无主地" not in cmd[2]:
                    c["atk"] += 1
                    c["atkT"] += cmd[3]
                    cc = next((o[4] for o in b["offers"] if o[0] == cmd[2]), None)
                    if b["over"]:
                        c["ov"] += 1
                        c["ovT"] += cmd[3]
                    if cc is not None and cc >= b["worth"]:
                        c["dear"] += 1
                        c["dearT"] += cmd[3]
                    idx = next((k for k, o in enumerate(b["offers"]) if o[0] == cmd[2]), len(b["offers"]))
                    if any("低于最小指令(" in o[7] for o in b["offers"][:idx]):
                        c["skipMin"] += 1
                        c["skipMinT"] += cmd[3]
                else:
                    c["othercmd"] += 1

            def row(name, c, ratio, needb, dme=None, dq=None):
                r = (f"{med(ratio):.2f}（{min(ratio):.2f}~{max(ratio):.2f}）" if ratio else "-")
                nb = f"{med(needb):.2f}" if needb else "-"
                dm = f"{med(dme):.0f}" if dme else "-"
                dqq = f"{med(dq):.0f}" if dq else "-"
                return (f"  {name}: {c['n']} | {c['hum']} | {c['z_dear']} | {c['z_sole']} | {c['z_hard']} | {c['z_avail']} | {c['z_none']} | {c['z_fly']} | {c['z_min']} | {c['z_short']} | {c['z_other']} | {c['don']} | "
                        f"{c['atk']}（{c['atkT']:,}）| {c['ov']}（{c['ovT']:,}）| {c['dear']}（{c['dearT']:,}）| {c['skipMin']}（{c['skipMinT']:,}）| {r} | {nb} | {dm} | {dqq} | {c['tagHard']} / {c['tagSole']} / {c['tagOnMe']}")
            L.append(row(bot, c, ratio, needb, dme, dq))
            tot.update(c)
            tot_ratio += ratio
            tot_needb += needb
        L.append(row("合计", tot, tot_ratio, tot_needb))
        L.append("")
    for i, a in enumerate(args):
        if a != "--target":
            continue
        name, ts = args[i + 1].rsplit(":", 1)
        L.append(f"## 目标含「{name}」的报价（每个决策拍：号 B / L / 密度 / worth → c / need；目标当拍 领土 / 余额）")
        for t in [int(x) for x in ts.split(",")]:
            rows, tinfo = [], None
            for bot in sorted(data):
                b = data[bot].get(t)
                if not b:
                    continue
                o = next((o for o in b["offers"] if name in o[0]), None)
                if not o:
                    continue
                tinfo = (o[0], o[1], o[2])
                rows.append((bot, b["B"], b["L"], b["d"], b["worth"], o[4], o[5], o[6].strip(), o[7].strip()))
            if not rows:
                L.append(f"  t={t}: 没有号的报价单里有它")
                continue
            L.append(f"  t={t}: {tinfo[0]} {tinfo[1]:,} 格 / {tinfo[2]:,} 兵（密度 {tinfo[2] / max(1, tinfo[1]):.1f}）")
            for r in rows:
                L.append(f"    {r[0]}: B={r[1]:,} L={r[2]:,} d={r[3]:.1f} worth={r[4]:.1f} → c={r[5]:.1f}（c÷worth {r[5] / r[4] if r[4] else 0:.2f}）need={r[6]:,}（need÷B {r[6] / max(1, r[1]):.2f}）〔{r[7]}｜{r[8]}〕")
            sb = sum(r[1] for r in rows)
            mx = max(r[6] for r in rows)
            L.append(f"    这 {len(rows)} 个号余额合计 {sb:,}；need 最大 {mx:,}；合计 ÷ need = {sb / max(1, mx):.2f}")
        L.append("")
    # 「低于最小指令」明细：号 × 目标
    MIN = re.compile(r'低于最小指令\(x=(-?\d+)<(\d+)\)')
    AV = re.compile(r'avail=(-?\d+)')
    agg = defaultdict(lambda: {"zero": 0, "div": 0, "ts": [], "terr": [], "bal": [], "need": [], "x": [], "minS": [], "c": [], "worth": [], "divTo": Counter(), "divT": 0, "byNeed": [], "byAvail": []})
    for bot in sorted(data):
        for t in sorted(data[bot]):
            b = data[bot][t]
            cmd = b["cmd"]
            idx = len(b["offers"])
            if cmd and cmd[0] == "attack":
                idx = next((k for k, o in enumerate(b["offers"]) if o[0] == cmd[2]), len(b["offers"]))
            elif cmd:
                continue
            for o in b["offers"][:idx]:
                mm = MIN.search(o[7])
                if not mm:
                    continue
                a = agg[(bot, o[0])]
                a["ts"].append(t)
                a["terr"].append(o[1]); a["bal"].append(o[2]); a["need"].append(o[5]); a["c"].append(o[4]); a["worth"].append(b["worth"])
                a["x"].append(int(mm.group(1))); a["minS"].append(int(mm.group(2)))
                av = AV.search(o[7])
                (a["byNeed"] if av and int(av.group(1)) >= int(mm.group(2)) else a["byAvail"]).append(t)
                if cmd:
                    a["div"] += 1
                    a["divTo"][cmd[2]] += 1
                    a["divT"] += cmd[3]
                else:
                    a["zero"] += 1
    L.append("## 「低于最小指令」的报价：过了比价和留底，要发的兵 x 却小于最小指令 max(minCmd, pulseMinShare×B)，这一行被跳过（全部明细拍）")
    L.append("# 列：号 → 目标 | 决策拍数（其中零指令 / 其中改打了排在后面的目标：打了谁、约兵）| 拍号范围 | 目标领土 | 目标余额 | need | 要发的兵 x | 最小指令 | c | worth | 分两种：可用兵够最小指令、但吃光它用不了这么多（拍数，首末拍）/ 可用兵本身不到最小指令（拍数）")
    rg = lambda xs: f"{min(xs):,}~{max(xs):,}" if min(xs) != max(xs) else f"{xs[0]:,}"
    rgf = lambda xs: f"{min(xs):.1f}~{max(xs):.1f}"
    for (bot, tgt), a in sorted(agg.items(), key=lambda kv: -len(kv[1]["ts"])):
        div = "；".join(f"{k} {v} 拍" for k, v in a["divTo"].most_common())
        divs = f"：{div}，约 {a['divT']:,} 兵" if a["div"] else ""
        bn = f"（t={min(a['byNeed'])}~{max(a['byNeed'])}）" if a["byNeed"] else ""
        L.append(f"  {bot} → {tgt} | {len(a['ts'])}（零指令 {a['zero']} / 改打别人 {a['div']}{divs}）| t={min(a['ts'])}~{max(a['ts'])} | {rg(a['terr'])} 格 | {rg(a['bal'])} 兵 | need {rg(a['need'])} | x {rg(a['x'])} | 最小 {rg(a['minS'])} | c {rgf(a['c'])} | worth {rgf(a['worth'])} | 所需太少 {len(a['byNeed'])} 拍{bn} / 可用兵太少 {len(a['byAvail'])} 拍")
    if not agg:
        L.append("  （没有）")
    L.append("")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "trace_span.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
