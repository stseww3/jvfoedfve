#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""87_trace_classify.py — R07：把 65_shadow.mjs --trace 写出的逐拍明细按「这一拍为什么没发 / 发了什么」归类计数。

用法（在 scripts/ 目录下）：
    python3 87_trace_classify.py <matchId> [号:t0:t1 ...]
    不给号就扫 out/<matchId>/ 下全部 shadow_trace_*.txt。

输入：out/<matchId>/shadow_trace_<号>_<t0>_<t1>.txt（影子运行的 buyLand 明细：每个决策拍一行表头 + 每个候选目标一行 + 一行结果）
输出：out/<matchId>/trace_classify.txt
    每个明细一段：
      · 零指令的决策拍按第一个候选目标的状态归类：价高（c >= worth → break）、可用兵 <= 0、唯一真人邻居闸、crowdedHard 闸、
        没有可打的邻居（没有候选行）、已有在途进攻、要发的兵低于最小指令、可用兵不够一条（后三类来自 65_shadow.mjs 的 sizeOf()）、其他；每类给拍数和首末拍
      · 出手的决策拍：打真人 / 内置 AI 的、只打无主地的、捐兵的；打真人里 over=1（过软上限）的拍数、
        这些拍的 c/worth 范围和「约 N 兵」合计；c >= worth 的拍数和兵
      · 发令的源码行（影子指令末尾的调用栈最后一段）计数
    口径：全部是影子按源码公式在重演局面上重算的值；「约 N 兵」是影子按发令拍余额估的，不是录像里的扣款。
"""
import glob
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = re.compile(r'^t=(\d+) (\S+) B=(-?\d+) L=(\d+) d=([\d.]+).*?worth=([\d.]+).*?over=(\d)')
OFFER = re.compile(r'^\s+→ (.+?) terr=(\d+) bal=(-?\d+) dq=([\d.]+).*?\| c=([\d.]+)')
CMD = re.compile(r'⇒ 影子指令 (\w+) pct=(\d+) → (.+?)（约 (\d+) 兵）(?: 〔(.+?)〕)?')


def fmt(x):
    return f"{int(round(x)):,}"


def classify(path):
    blocks, cur = [], None
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if ln.startswith("t="):
            cur = [ln]
            blocks.append(cur)
        elif cur is not None and ln.strip():
            cur.append(ln)
    cnt, rng = Counter(), {}
    sites = Counter()
    hum = {"n": 0, "troops": 0, "over_n": 0, "over_troops": 0, "over_ratio": [], "over_t": [], "dear_n": 0, "dear_troops": 0, "t": []}
    by_target = defaultdict(lambda: [0, 0])
    for b in blocks:
        m = HEAD.match(b[0])
        if not m:
            continue
        t, worth, over = int(m.group(1)), float(m.group(6)), m.group(7) == "1"
        offers = [l for l in b[1:] if l.lstrip().startswith("→")]
        res = [l for l in b[1:] if "⇒" in l]
        r = res[0] if res else ""
        cm = CMD.search(r)
        if cm:
            kind, pct, target, troops, stack = cm.group(1), int(cm.group(2)), cm.group(3), int(cm.group(4)), cm.group(5) or ""
            if stack:
                sites[stack.split("<")[-1]] += 1
            if kind == "donate":
                k = "捐兵"
            elif kind != "attack":
                k = f"其他指令（{kind}）"
            elif "无主地" in target:
                k = "出手：只打无主地"
            else:
                k = "出手：打真人 / 内置 AI / 离开席位"
                hum["n"] += 1
                hum["troops"] += troops
                hum["t"].append(t)
                by_target[target][0] += 1
                by_target[target][1] += troops
                c = None
                for o in offers:
                    om = OFFER.match(o)
                    if om and om.group(1) == target:
                        c = float(om.group(5))
                        break
                if c is not None and c >= worth:
                    hum["dear_n"] += 1
                    hum["dear_troops"] += troops
                if over:
                    hum["over_n"] += 1
                    hum["over_troops"] += troops
                    hum["over_t"].append(t)
                    if c is not None and worth > 0:
                        hum["over_ratio"].append(c / worth)
        else:
            if not offers:
                k = "零指令：没有可打的邻居（没有候选）"
            else:
                o = offers[0]
                if "价高" in o:
                    k = "零指令：价高（c >= worth）"
                elif "无可用" in o:
                    k = "零指令：可用兵 <= 0（留底高过余额）"
                elif "唯一真人邻居" in o:
                    k = "零指令：唯一真人邻居闸"
                elif "crowdedHard" in o and "continue" in o:
                    k = "零指令：crowdedHard 闸"
                elif "在途(" in o:
                    k = "零指令：对首选目标已有在途进攻（curAtk 过门槛）"
                elif "低于最小指令(" in o:
                    k = "零指令：要发的兵低于最小指令（x < max(minCmd, pulseMinShare×B)）"
                elif "不够一条(" in o:
                    k = "零指令：可用兵不够一条（x < chunk×B）"
                else:
                    k = "零指令：其他（有可用兵但没发）"
        cnt[k] += 1
        rng.setdefault(k, [t, t])[1] = t
    return len(blocks), cnt, rng, hum, sites, by_target


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    mid = args[0]
    out = os.path.join(HERE, "..", "out", mid)
    if len(args) > 1:
        files = []
        for spec in args[1:]:
            bot, t0, t1 = spec.split(":")[:3]
            files.append(os.path.join(out, f"shadow_trace_{bot}_{t0}_{t1}.txt"))
    else:
        files = sorted(glob.glob(os.path.join(out, "shadow_trace_*.txt")))
    L = [f"# {mid} 影子逐拍明细归类（65_shadow.mjs --trace 的输出；全部是影子值）", ""]
    for f in files:
        if not os.path.exists(f):
            L.append(f"## {os.path.basename(f)}：没有这个文件")
            continue
        n, cnt, rng, hum, sites, by_target = classify(f)
        L.append(f"## {os.path.basename(f)}：决策拍 {n}")
        for k, v in cnt.most_common():
            L.append(f"  {k}：{v} 拍（t={rng[k][0]}~{rng[k][1]}）")
        if hum["n"]:
            line = f"  打真人 / AI / 离开席位的出手 {hum['n']} 拍（t={hum['t'][0]}~{hum['t'][-1]}），约 {fmt(hum['troops'])} 兵；其中 c >= worth 的 {hum['dear_n']} 拍约 {fmt(hum['dear_troops'])} 兵"
            if hum["over_n"]:
                rr = hum["over_ratio"]
                line += (f"；over=1（过软上限）的 {hum['over_n']} 拍（t={hum['over_t'][0]}~{hum['over_t'][-1]}）约 {fmt(hum['over_troops'])} 兵"
                         + (f"，c/worth {min(rr):.2f}~{max(rr):.2f}" if rr else ""))
            else:
                line += "；over=1 的 0 拍"
            L.append(line)
            L.append("  按目标：" + "；".join(f"{k} {v[0]} 拍约 {fmt(v[1])} 兵" for k, v in sorted(by_target.items(), key=lambda kv: -kv[1][1])))
        if sites:
            L.append("  发令行：" + "，".join(f"{k} ×{v}" for k, v in sites.most_common()))
        L.append("")
    fn = os.path.join(out, "trace_classify.txt")
    with open(fn, "w", encoding="utf-8") as fo:
        fo.write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"... 写入 {fn}")


if __name__ == "__main__":
    main()
