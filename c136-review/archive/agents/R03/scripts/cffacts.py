#!/usr/bin/env python3
"""cffacts.py — 把开环消融试跑（cfopen.mjs）的输出汇成表：安慰剂逐条、噪声底 ε(h)、机制臂与 ε 的对比、配对臂。

    timeout 120 python3 scripts/cffacts.py          # 读 out/council/cf/*.txt，写 out/council/CF-facts.txt

只做文本解析和取最大值/中位数，不跑重放。口径：
  · 断面 = 臂名 @ 后面的拍（drop1@630:k 的断面是 630；dead@600-1500 的断面取窗口起点 600）。
  · h = 读数拍 − 这一臂的起点（安慰剂 = 被拿掉的那条指令的拍；机制臂 = 窗口起点）。cfopen 默认在 h=90/300/600/900/1500/2400 和跑到的最后一拍各读一次。
  · 偏离 = (反事实 − 真值) ÷ 真值，量是编队合计地；真值为 0 的读数不算偏离，单列。
  · ε(h) = 同一局、同一断面的各条安慰剂在同一个 h 上 |偏离| 的最大值。机制臂找「同一局、断面拍相差不超过 100」的安慰剂组来比。
  · 配对臂（写法 臂+drop1@T:k）：同一条安慰剂扰动下「有机制臂 − 没有机制臂」，读数拍用 --at 给的绝对拍。
"""
import glob
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF = os.path.join(ROOT, "out", "council", "cf")
OUT = os.path.join(ROOT, "out", "council", "CF-facts.txt")
HS = [90, 300, 600, 900, 1500, 2400]
ORDER = ["A051", "A087", "A066", "A025", "A045", "A067", "A071", "A090", "A042", "A046", "A041"]

num = lambda s: int(s.replace(",", ""))


def parse(path):
    """→ (head, arms)；arms: dict(spec → {...})，按文件里的顺序。"""
    head, arms, cur = None, [], None
    for ln in open(path, encoding="utf-8").read().split("\n"):
        m = re.match(r"^\[CF-O\] (\w+) \| 跑到 (\S+) \| 真值臂：traj (\d+)/(\d+) 行一致，结束拍 (\d+)(?:，胜队 (\d+))? \| 编队 (\d+) 号", ln)
        if m:
            head = dict(mid=m.group(1), until=m.group(2), ok=int(m.group(3)), rows=int(m.group(4)), end=int(m.group(5)), win=m.group(6), nsq=int(m.group(7)))
            continue
        c = ln.split(" | ")
        if len(c) < 3 or not head or c[0] != head["mid"]:
            continue
        spec = c[1]
        if c[2].startswith("拿掉"):
            m1 = re.match(r"丢 (\d+) 条", c[3])
            m1b = re.search(r"最早 (\d+) 拍", c[3])
            m2 = re.match(r"traj (\d+)/(\d+) 行仍与日志一致，首个不一致拍 (\S+)", c[4])
            m3 = re.match(r"结束拍 (\d+)(?:，胜队 (\d+))?（真值 (\d+)）", c[5])
            cur = dict(mid=head["mid"], spec=spec, label=c[2], dropped=int(m1.group(1)), ok=int(m2.group(1)), rows=int(m2.group(2)),
                       first=m2.group(3), end=int(m3.group(1)), win=m3.group(2), tend=int(m3.group(3)), reads=[], flips=None,
                       file=os.path.basename(path), until=head["until"], firstdrop=int(m1b.group(1)) if m1b else None)
            arms.append(cur)
        elif c[2].startswith("受理结果变了") and cur and cur["spec"] == spec:
            m = re.match(r"受理结果变了的录像指令：其他真人 (\d+)/(\d+) 条(?:（最早 (\d+) 拍）)?，编队其余指令 (\d+)/(\d+) 条(?:（最早 (\d+) 拍）)?", c[2])
            cur["flips"] = dict(ot=int(m.group(1)), otN=int(m.group(2)), otT=m.group(3), sq=int(m.group(4)), sqN=int(m.group(5)), sqT=m.group(6))
        elif c[2].startswith("t=") and cur and cur["spec"] == spec:
            r = dict(t=int(c[2][2:]))
            for cell in c[3:]:
                m = re.match(r"(\S+?) ?([\d,]+) → ([\d,]+)", cell)
                if m:
                    r[m.group(1)] = (num(m.group(2)), num(m.group(3)))
            cur["reads"].append(r)
    return head, arms


def base_of(a):
    """这一臂的起点拍。"""
    name = a["spec"].split("+")[0]
    if name.startswith("drop1@"):
        return int(re.match(r"拿掉 (\d+) 拍", a["label"]).group(1))
    return int(re.match(r"\w+@(\d+)", name).group(1))


def cut_of(spec):
    return int(re.match(r"\w+@(\d+)", spec).group(1))


def dev(pair):
    a, b = pair
    return None if a == 0 else 100.0 * (b - a) / a


def pc(x, plus=True):
    if x is None:
        return "—"
    return f"{x:+.2f}%" if plus else f"{x:.2f}%"


def flip_txt(f):
    if not f:
        return "—", "—"
    a = f"{f['ot']}/{f['otN']}" + (f"（最早 {f['otT']}）" if f["otT"] else "")
    b = f"{f['sq']}/{f['sqN']}" + (f"（最早 {f['sqT']}）" if f["sqT"] else "")
    return a, b


def last_txt(a):
    r = a["reads"][-1]
    sl, sn = r["编队地"], r["有地号数"]
    return f"t={r['t']}：{sl[0]:,} → {sl[1]:,}（{sn[0]} → {sn[1]} 号）"


def by_h(a):
    """h → 偏离（编队地）；只收标准 h。"""
    b = base_of(a)
    out = {}
    for r in a["reads"]:
        h = r["t"] - b
        if h in HS:
            out[h] = dev(r["编队地"])
    return out


def by_h_enemy(a):
    b = base_of(a)
    out = {}
    for r in a["reads"]:
        h = r["t"] - b
        if h in HS and "敌方真人地" in r:
            out[h] = dev(r["敌方真人地"])
    return out


def main():
    files = sorted(glob.glob(os.path.join(CF, "*.txt")))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    heads, arms = [], []
    for f in files:
        h, a = parse(f)
        if not h:
            continue
        h["file"] = os.path.basename(f)
        h["n"] = len(a)
        heads.append(h)
        arms += a
    key = lambda mid: ORDER.index(mid) if mid in ORDER else 99
    L = []
    P = L.append
    P("# CF-facts.txt — 开环消融试跑（scripts/cfopen.mjs）的汇总；出处 out/council/cf/*.txt；脚本 scripts/cffacts.py")
    P("# 偏离 = (反事实 − 真值) ÷ 真值，量是编队合计地。h = 读数拍 − 这一臂的起点。ε(h) = 同局同断面各条安慰剂 |偏离| 的最大值。")
    P("")

    pf0 = {a["file"] for a in arms if "+" in a["spec"]}
    P("[CF-0] 试跑清单")
    P("局 | 文件 | 类型 | 跑到 | 真值臂 traj 一致行 | 真值结束拍 | 臂数")
    for h in sorted(heads, key=lambda h: (h["file"] in pf0, key(h["mid"]), h["file"])):
        P(f"{h['mid']} | {h['file']} | {'配对' if h['file'] in pf0 else '单臂'} | {h['until']} | {h['ok']}/{h['rows']} | {h['end']} | {h['n']}")
    for kind, hs in (("单臂", [h for h in heads if h["file"] not in pf0]), ("配对", [h for h in heads if h["file"] in pf0])):
        if hs:
            P(f"{kind}合计：{len(hs)} 次试跑、{sum(h['n'] for h in hs)} 个臂；不删任何指令的真值臂 traj {sum(h['ok'] for h in hs)}/{sum(h['rows'] for h in hs)} 行一致")
    P(f"全部合计：{len(heads)} 次试跑、{sum(h['n'] for h in heads)} 个臂；真值臂 traj {sum(h['ok'] for h in heads)}/{sum(h['rows'] for h in heads)} 行一致；涉及 {len({h['mid'] for h in heads})} 局")
    P("")

    # 带配对臂的文件用的是 --at 给的绝对读数拍，不进 CF-1~CF-3（那三张表按 h 对齐），单独进 CF-4
    pfiles = {a["file"] for a in arms if "+" in a["spec"]}
    single = [a for a in arms if "+" not in a["spec"] and a["file"] not in pfiles]
    plac = [a for a in single if a["spec"].startswith("drop1@")]
    mech = [a for a in single if not a["spec"].startswith("drop1@")]
    pairs = [a for a in arms if "+" in a["spec"]]

    # ---- CF-1 安慰剂逐条
    P("[CF-1] 安慰剂逐条：只拿掉编队一条成交指令，其余全场指令照录像")
    P("局 | 断面 | 拿掉的指令 | traj 仍一致行 | 首个不一致拍 | 受理变了：其他真人 | 受理变了：编队其余 | " + " | ".join(f"h={h}" for h in HS) + " | 跑到的最后一拍：编队地 真值 → 安慰剂")
    groups = {}
    for a in sorted(plac, key=lambda a: (key(a["mid"]), cut_of(a["spec"]), base_of(a))):
        g = groups.setdefault((a["mid"], cut_of(a["spec"])), [])
        g.append(a)
        d = by_h(a)
        fo, fs = flip_txt(a["flips"])
        lab = re.sub(r"^拿掉 ", "", a["label"])
        P(f"{a['mid']} | {cut_of(a['spec'])} | {lab} | {a['ok']}/{a['rows']} | {a['first']} | {fo} | {fs} | " + " | ".join(pc(d.get(h)) if h in d else "" for h in HS) + f" | {last_txt(a)}")
    n0 = sum(1 for a in plac if a["flips"] and a["flips"]["ot"] == 0 and a["flips"]["sq"] == 0)
    P(f"合计：安慰剂 {len(plac)} 条；到跑完为止别人和编队其余指令的受理结果一条都没变的 {n0} 条，有变的 {len(plac) - n0} 条")
    P("")

    # ---- CF-2 噪声底
    P("[CF-2] 噪声底 ε(h)：同局同断面各条安慰剂在 h 上 |编队地偏离| 的最大值（括号里：中位数；有读数的条数）")
    P("局 | 断面 | 安慰剂条数 | " + " | ".join(f"h={h}" for h in HS))
    EPS = {}
    for (mid, cut), g in sorted(groups.items(), key=lambda kv: (key(kv[0][0]), kv[0][1])):
        cells = []
        for h in HS:
            v = [abs(x) for x in (by_h(a).get(h) for a in g) if x is not None]
            if not v:
                cells.append("")
                continue
            EPS[(mid, cut, h)] = max(v)
            cells.append(f"{max(v):.2f}%（{statistics.median(v):.2f}%；{len(v)}）")
        P(f"{mid} | {cut} | {len(g)} | " + " | ".join(cells))
    P("")
    P("[CF-2b] 同一批安慰剂在 h 上 |敌方真人地偏离| 的最大值（括号里：中位数；有读数的条数）")
    P("局 | 断面 | 安慰剂条数 | " + " | ".join(f"h={h}" for h in HS))
    for (mid, cut), g in sorted(groups.items(), key=lambda kv: (key(kv[0][0]), kv[0][1])):
        cells = []
        for h in HS:
            v = [abs(x) for x in (by_h_enemy(a).get(h) for a in g) if x is not None]
            cells.append(f"{max(v):.2f}%（{statistics.median(v):.2f}%；{len(v)}）" if v else "")
        P(f"{mid} | {cut} | {len(g)} | " + " | ".join(cells))
    P("")

    # ---- CF-2d 各组安慰剂并排（单臂试跑的一组、配对试跑的一组），按绝对拍分窗
    P("[CF-2d] 各组安慰剂并排：断面后三个时间窗里 |编队地偏离| 的最大值（按读数的绝对拍分窗；跑到的最后一拍不算）")
    P("局 | 断面 | 哪一次试跑 | 安慰剂条数 | 被拿掉指令的拍 | 断面后 600 拍之内 | 600~1500 拍 | 1500 拍之后")
    sets = {}
    for a in arms:
        if "+" in a["spec"] or not a["spec"].startswith("drop1@"):
            continue
        sets.setdefault((a["mid"], cut_of(a["spec"]), a["file"]), []).append(a)
    for (mid, cut, fname), g in sorted(sets.items(), key=lambda kv: (key(kv[0][0]), kv[0][1], kv[0][2] in pfiles, kv[0][2])):
        win = {0: [], 1: [], 2: []}
        for a in g:
            b0 = base_of(a)
            for r in a["reads"]:
                if fname in pfiles:
                    if r["t"] == a["end"]:
                        continue
                elif (r["t"] - b0) not in HS:
                    continue
                d = dev(r["编队地"])
                if d is None:
                    continue
                dt = r["t"] - cut
                win[0 if dt <= 600 else 1 if dt <= 1500 else 2].append(abs(d))
        ticks = sorted(base_of(a) for a in g)
        cell = lambda v: f"{max(v):.2f}%（{len(v)} 个读数）" if v else ""
        P(f"{mid} | {cut} | {'配对' if fname in pfiles else '单臂'}（{fname}） | {len(g)} | {ticks[0]}~{ticks[-1]} | {cell(win[0])} | {cell(win[1])} | {cell(win[2])}")
    P("")

    # ---- CF-2c 末拍翻转
    P("[CF-2c] 跑到的最后一拍，编队有地号数与真值不同的臂（安慰剂和机制臂都算）")
    P("局 | 臂 | 拿掉了什么 | 最后一拍 | 编队有地号数 真值 → 反事实 | 编队地 真值 → 反事实 | 敌方真人地偏离")
    nflip = nflip_p = 0
    for a in sorted(single, key=lambda a: (key(a["mid"]), a["file"], base_of(a))):
        r = a["reads"][-1]
        sn, sl = r["有地号数"], r["编队地"]
        if sn[0] == sn[1]:
            continue
        nflip += 1
        nflip_p += a["spec"].startswith("drop1@")
        lab = re.sub(r"（真值里.*$", "", re.sub(r"^拿掉 ", "", a["label"]))
        P(f"{a['mid']} | {a['spec']} | {lab} | {r['t']} | {sn[0]} → {sn[1]} | {sl[0]:,} → {sl[1]:,} | {pc(dev(r['敌方真人地']))}")
    P(f"合计：{len(single)} 个单臂里 {nflip} 个在最后一拍的编队有地号数与真值不同，其中安慰剂 {nflip_p} 个")
    chg = [a for a in single if a["flips"] and a["flips"]["ot"] > 0]
    same = [a for a in single if a["flips"] and a["flips"]["ot"] == 0]
    d1 = sum(1 for a in chg if a["reads"][-1]["有地号数"][0] != a["reads"][-1]["有地号数"][1])
    d0 = sum(1 for a in same if a["reads"][-1]["有地号数"][0] != a["reads"][-1]["有地号数"][1])
    P(f"其他真人指令的受理结果有变的 {len(chg)} 个臂里，最后一拍号数与真值不同的 {d1} 个；一条都没变的 {len(same)} 个臂里 {d0} 个")
    P("")

    # ---- CF-2e 同一件事，配对试跑里不带「+」的臂（安慰剂和机制臂单跑的那一条）
    P("[CF-2e] 配对试跑里单跑的臂（安慰剂、机制臂各自单跑的那一条）在跑到的最后一拍，编队有地号数与真值不同的")
    P("局 | 文件 | 臂 | 拿掉了什么 | 最后一拍 | 编队有地号数 真值 → 反事实 | 编队地 真值 → 反事实")
    pe = [a for a in arms if a["file"] in pfiles and "+" not in a["spec"] and a["reads"] and a["reads"][-1]["t"] == a["end"]]
    ne = ne_p = 0
    for a in sorted(pe, key=lambda a: (key(a["mid"]), a["file"], not a["spec"].startswith("drop1@"), base_of(a))):
        r = a["reads"][-1]
        sn, sl = r["有地号数"], r["编队地"]
        if sn[0] == sn[1]:
            continue
        ne += 1
        ne_p += a["spec"].startswith("drop1@")
        lab = re.sub(r"（真值里.*$", "", re.sub(r"^拿掉 ", "", a["label"]))
        P(f"{a['mid']} | {a['file']} | {a['spec']} | {lab} | {r['t']} | {sn[0]} → {sn[1]} | {sl[0]:,} → {sl[1]:,}")
    npl = sum(1 for a in pe if a["spec"].startswith("drop1@"))
    P(f"合计：这样的臂 {len(pe)} 个（安慰剂 {npl} 个、机制臂 {len(pe) - npl} 个），{ne} 个在最后一拍的编队有地号数与真值不同，其中安慰剂 {ne_p} 个")
    chg2 = [a for a in pe if a["flips"] and a["flips"]["ot"] > 0]
    same2 = [a for a in pe if a["flips"] and a["flips"]["ot"] == 0]
    e1 = sum(1 for a in chg2 if a["reads"][-1]["有地号数"][0] != a["reads"][-1]["有地号数"][1])
    e0 = sum(1 for a in same2 if a["reads"][-1]["有地号数"][0] != a["reads"][-1]["有地号数"][1])
    P(f"其他真人指令的受理结果有变的 {len(chg2)} 个臂里，最后一拍号数与真值不同的 {e1} 个；一条都没变的 {len(same2)} 个臂里 {e0} 个")
    P("")

    # ---- CF-3 机制臂
    P("[CF-3] 机制臂：每格是「编队地偏离 / 同局同断面安慰剂的 ε(h)」；没有同断面安慰剂的写「无 ε」")
    P("局 | 臂 | 拿掉了什么 | 实际丢掉 | 受理变了：其他真人 | 受理变了：编队其余 | " + " | ".join(f"h={h}" for h in HS) + " | 超过 ε 的 h | 跑到的最后一拍：编队地 真值 → 反事实")
    cuts_by_mid = {}
    for (mid, cut) in groups:
        cuts_by_mid.setdefault(mid, []).append(cut)
    for a in sorted(mech, key=lambda a: (key(a["mid"]), base_of(a), a["spec"])):
        b = base_of(a)
        near = [c for c in cuts_by_mid.get(a["mid"], []) if abs(c - b) <= 100]
        cut = min(near, key=lambda c: abs(c - b)) if near else None
        d = by_h(a)
        cells, over = [], []
        noeps = cut is None
        for h in HS:
            if h not in d:
                cells.append("")
                continue
            e = EPS.get((a["mid"], cut, h)) if cut is not None else None
            if d[h] is None:
                cells.append("真值为 0")
            elif e is None:
                cells.append(f"{pc(d[h])} / 无 ε")
            else:
                cells.append(f"{pc(d[h])} / {e:.2f}%")
                if abs(d[h]) > e:
                    over.append(str(h))
        fo, fs = flip_txt(a["flips"])
        lab = re.sub(r"^拿掉 ", "", a["label"])
        P(f"{a['mid']} | {a['spec']} | {lab} | {a['dropped']} 条 | {fo} | {fs} | " + " | ".join(cells) + f" | {'无 ε' if noeps else ('、'.join(over) if over else '没有')} | {last_txt(a)}")
    P("")

    # ---- CF-3b 配对试跑里单跑的那一条机制臂删掉了什么
    P("[CF-3b] 配对试跑里的机制臂（不加安慰剂、单跑的那一条）：拿掉了什么")
    P("局 | 臂 | 拿掉了什么 | 实际丢掉 | 最早丢在哪一拍 | 受理变了：其他真人 | 受理变了：编队其余")
    pm = [a for a in arms if a["file"] in pfiles and "+" not in a["spec"] and not a["spec"].startswith("drop1@")]
    for a in sorted(pm, key=lambda a: (key(a["mid"]), base_of(a), a["spec"])):
        fo, fs = flip_txt(a["flips"])
        lab = re.sub(r"^拿掉 ", "", a["label"])
        P(f"{a['mid']} | {a['spec']} | {lab} | {a['dropped']} 条 | {a.get('firstdrop') or '—'} | {fo} | {fs}")
    P("")

    # ---- CF-5 机制臂逐读数拍的绝对数
    P("[CF-5] 机制臂逐读数拍：编队地与有地号数的绝对数（单臂）；「有效」= 读数拍早于其他真人第一条受理结果改变的拍")
    P("局 | 臂 | 读数拍 | 编队地 真值 | 编队地 反事实 | 偏离 | 有地号数 真值 → 反事实 | 有效")
    for a in sorted(mech, key=lambda a: (key(a["mid"]), base_of(a), a["spec"])):
        ft = int(a["flips"]["otT"]) if a["flips"] and a["flips"]["otT"] else None
        for r in a["reads"]:
            sl, sn = r["编队地"], r["有地号数"]
            ok = "是" if ft is None or r["t"] < ft else "否"
            P(f"{a['mid']} | {a['spec']} | {r['t']} | {sl[0]:,} | {sl[1]:,} | {pc(dev(sl))} | {sn[0]} → {sn[1]} | {ok}")
    P("")

    # ---- CF-4 配对臂
    if pairs:
        P("[CF-4] 配对臂：同一条安慰剂扰动下「加上机制臂 − 不加」的编队地差 ÷ 真值编队地；读数拍是绝对拍")
        P("局 | 机制臂 | 读数拍 | 配对数 | 配对差：中位 | 最小 | 最大 | 同号的对数 | 单跑一次的偏离 | 同拍安慰剂 |偏离| 最大 | 其他真人受理结果最早改变的拍：机制臂单跑 | 同上：各配对臂里最早的")
        idx = {(a["mid"], a["file"], a["spec"]): a for a in arms}
        table, table2, firstflip, files_of = {}, {}, {}, {}
        for a in pairs:
            m_spec, p_spec = a["spec"].split("+", 1)
            p = idx.get((a["mid"], a["file"], p_spec))
            if not p:
                continue
            k = (a["mid"], a["file"], m_spec)
            if a["flips"] and a["flips"]["otT"]:
                firstflip[k] = min(firstflip.get(k, 10 ** 9), int(a["flips"]["otT"]))
            pr = {r["t"]: r for r in p["reads"]}
            for r in a["reads"]:
                if r["t"] not in pr or r["t"] == a["reads"][-1]["t"] and r["t"] == a["end"]:
                    continue
                truth = r["编队地"][0]
                if truth == 0:
                    continue
                d = 100.0 * (r["编队地"][1] - pr[r["t"]]["编队地"][1]) / truth
                table.setdefault(k, {}).setdefault(r["t"], []).append(d)
                if "本队地" in r and "本队地" in pr[r["t"]] and r["本队地"][0] > 0:
                    d2 = 100.0 * (r["本队地"][1] - pr[r["t"]]["本队地"][1]) / r["本队地"][0]
                    table2.setdefault(k, {}).setdefault(r["t"], []).append(d2)
        allsame = {}
        for k, tt in sorted(table.items(), key=lambda kv: (key(kv[0][0]), kv[0][1], kv[0][2])):
            mid, fname, m_spec = k
            s_arm = idx.get((mid, fname, m_spec))
            sd = {r["t"]: dev(r["编队地"]) for r in s_arm["reads"]} if s_arm else {}
            pl = [a for a in arms if a["mid"] == mid and a["file"] == fname and a["spec"].startswith("drop1@")]
            for t in sorted(tt):
                v = tt[t]
                med = statistics.median(v)
                pos, neg = sum(1 for x in v if x > 0), sum(1 for x in v if x < 0)
                same = "都是 0" if pos == 0 and neg == 0 else f"{max(pos, neg)}/{len(v)}（{'正' if pos >= neg else '负'}）"
                pv = [abs(dev(r["编队地"])) for a in pl for r in a["reads"] if r["t"] == t and dev(r["编队地"]) is not None]
                eps = f"{max(pv):.2f}%" if pv else ""
                ff = firstflip.get(k)
                f1 = s_arm["flips"]["otT"] if s_arm and s_arm["flips"] else None
                P(f"{mid} | {m_spec} | {t} | {len(v)} | {pc(med)} | {pc(min(v))} | {pc(max(v))} | {same} | {pc(sd.get(t)) if t in sd else ''} | {eps} | {f1 if f1 else '没有变'} | {ff if ff else '没有变'}")
                if max(pos, neg) == len(v) and len(v) >= 6:
                    allsame.setdefault((mid, m_spec), []).append((t, med, '正' if pos else '负'))
        P("")
        # ---- CF-4c 配对差并上真值编队地、折成格数、对着同一时段真值编队地自高点掉了多少
        P("[CF-4c] 配对臂逐读数拍：配对差、折成格数、对着真值编队地自高点掉了多少（高点 = 本次试跑各读数拍里到这一拍为止真值编队地的最大值；掉了不到高点 1% 的不算比例；「有效」= 读数拍早于机制臂单跑时其他真人第一条受理结果改变的拍）")
        P("局 | 机制臂 | 读数拍 | 真值编队地 | 配对差中位 | 配对差范围 | 同号的对数 | 配对差中位（格） | 真值自高点掉了（格） | 配对差 ÷ 掉的格数 | 有效")
        recs = []
        for k, tt in sorted(table.items(), key=lambda kv: (key(kv[0][0]), kv[0][1], kv[0][2])):
            mid, fname, m_spec = k
            s_arm = idx.get((mid, fname, m_spec))
            if not s_arm:
                continue
            truth = {r["t"]: r["编队地"][0] for r in s_arm["reads"]}
            f1 = int(s_arm["flips"]["otT"]) if s_arm["flips"] and s_arm["flips"]["otT"] else None
            peak = 0
            for t in sorted(tt):
                v = tt[t]
                med = statistics.median(v)
                pos, neg = sum(1 for x in v if x > 0), sum(1 for x in v if x < 0)
                same = "都是 0" if pos == 0 and neg == 0 else f"{max(pos, neg)}/{len(v)}（{'正' if pos >= neg else '负'}）"
                peak = max(peak, truth[t])
                drop = peak - truth[t]
                cells = med * truth[t] / 100.0
                big = drop > 0 and drop >= 0.01 * peak
                share = f"{100.0 * cells / drop:+.1f}%" if big else ("没掉" if drop == 0 else "掉了不到 1%")
                valid = f1 is None or t < f1
                P(f"{mid} | {m_spec} | {t} | {truth[t]:,} | {pc(med)} | {pc(min(v))}~{pc(max(v))} | {same} | {cells:+,.0f} | {drop:,} | {share} | {'是' if valid else '否'}")
                recs.append(dict(mid=mid, spec=m_spec, t=t, med=med, nz=pos + neg > 0, allsame=max(pos, neg) == len(v), valid=valid,
                                 share=100.0 * cells / drop if big else None))
        P("")
        P("[CF-4d] 按机制臂小结：只算有效期内的读数拍；范围只取 6 对同号的拍")
        P("机制臂 | 局 | 有效期内配对差不全为 0 的读数拍 | 其中全部配对同号的 | 同号拍的配对差中位范围 | 同号拍的「配对差 ÷ 掉的格数」范围（只算真值编队地自高点掉了 1% 以上的拍）")
        def summarize(rs):
            seen_specs = []
            for r in rs:
                if r["spec"] not in seen_specs:
                    seen_specs.append(r["spec"])
            for sp in seen_specs:
                rr = [r for r in rs if r["spec"] == sp and r["valid"] and r["nz"]]
                mids = sorted({r["mid"] for r in rs if r["spec"] == sp}, key=key)
                ss = [r for r in rr if r["allsame"]]
                if not ss:
                    P(f"{sp} | {'、'.join(mids)} | {len(rr)} 个 | 0 个 | — | —")
                    continue
                meds = [r["med"] for r in ss]
                sh = [r["share"] for r in ss if r["share"] is not None]
                rng = pc(meds[0]) if len(meds) == 1 else f"{pc(min(meds))}~{pc(max(meds))}"
                shr = "—" if not sh else (f"{sh[0]:+.1f}%（1 个拍）" if len(sh) == 1 else f"{min(sh):+.1f}%~{max(sh):+.1f}%（{len(sh)} 个拍）")
                P(f"{sp} | {'、'.join(mids)} | {len(rr)} 个 | {len(ss)} 个 | {rng} | {shr}")
        summarize(recs)
        P("")
        # ---- CF-4e 同样的配对，量换成编队所在队的合计地
        P("[CF-4e] 配对臂逐读数拍，量换成「本队地」（编队所在那一队的合计地，含同队路人；没有队伍的局就是编队自己。配对差 = 两臂本队地之差 ÷ 真值本队地；高点、比例、有效的算法同 [CF-4c]）")
        P("局 | 机制臂 | 读数拍 | 真值本队地 | 真值编队地 | 配对差中位（本队地） | 配对差范围 | 同号的对数 | 配对差中位（格） | 真值本队地自高点掉了（格） | 配对差 ÷ 掉的格数 | 有效")
        recs2 = []
        for k, tt in sorted(table2.items(), key=lambda kv: (key(kv[0][0]), kv[0][1], kv[0][2])):
            mid, fname, m_spec = k
            s_arm = idx.get((mid, fname, m_spec))
            if not s_arm:
                continue
            tl = {r["t"]: r["本队地"][0] for r in s_arm["reads"] if "本队地" in r}
            sl = {r["t"]: r["编队地"][0] for r in s_arm["reads"]}
            f1 = int(s_arm["flips"]["otT"]) if s_arm["flips"] and s_arm["flips"]["otT"] else None
            peak = 0
            for t in sorted(tt):
                v = tt[t]
                med = statistics.median(v)
                pos, neg = sum(1 for x in v if x > 0), sum(1 for x in v if x < 0)
                same = "都是 0" if pos == 0 and neg == 0 else f"{max(pos, neg)}/{len(v)}（{'正' if pos >= neg else '负'}）"
                peak = max(peak, tl.get(t, 0))
                drop = peak - tl.get(t, 0)
                cells = med * tl.get(t, 0) / 100.0
                big = drop > 0 and drop >= 0.01 * peak
                share = f"{100.0 * cells / drop:+.1f}%" if big else ("没掉" if drop == 0 else "掉了不到 1%")
                valid = f1 is None or t < f1
                P(f"{mid} | {m_spec} | {t} | {tl.get(t, 0):,} | {sl.get(t, 0):,} | {pc(med)} | {pc(min(v))}~{pc(max(v))} | {same} | {cells:+,.0f} | {drop:,} | {share} | {'是' if valid else '否'}")
                recs2.append(dict(mid=mid, spec=m_spec, t=t, med=med, nz=pos + neg > 0, allsame=max(pos, neg) == len(v), valid=valid,
                                  share=100.0 * cells / drop if big else None))
        P("")
        P("[CF-4f] 按机制臂小结，量是「本队地」：只算有效期内的读数拍；范围只取 6 对同号的拍")
        P("机制臂 | 局 | 有效期内配对差不全为 0 的读数拍 | 其中全部配对同号的 | 同号拍的配对差中位范围 | 同号拍的「配对差 ÷ 掉的格数」范围（只算真值本队地自高点掉了 1% 以上的拍）")
        summarize(recs2)
        P("")
        P("[CF-4b] 配对臂小结：哪些读数拍上全部配对同号（不少于 6 对）")
        P("局 | 机制臂 | 全部同号的读数拍（配对差中位） | 方向 | 机制臂删掉的第一条指令在哪一拍 | 机制臂单跑时其他真人受理结果最早改变的拍 | 同上：编队其余指令")
        seen = set()
        for k in sorted(table, key=lambda k: (key(k[0]), k[1], k[2])):
            mid, fname, m_spec = k
            if (mid, m_spec) in seen:
                continue
            seen.add((mid, m_spec))
            lst = allsame.get((mid, m_spec), [])
            s_arm = idx.get((mid, fname, m_spec))
            fd = s_arm["firstdrop"] if s_arm and s_arm.get("firstdrop") else "—"
            f1 = (s_arm["flips"]["otT"] or "没有变") if s_arm and s_arm["flips"] else "—"
            f2 = (s_arm["flips"]["sqT"] or "没有变") if s_arm and s_arm["flips"] else "—"
            if lst:
                dirs = {x[2] for x in lst}
                P(f"{mid} | {m_spec} | " + "、".join(f"{t}（{pc(m)}）" for t, m, _ in lst) + f" | {'、'.join(sorted(dirs))} | {fd} | {f1} | {f2}")
            else:
                P(f"{mid} | {m_spec} | 没有 | — | {fd} | {f1} | {f2}")
        P("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"写 {os.path.relpath(OUT, ROOT)}（{len(L)} 行；{len(heads)} 次试跑，安慰剂 {len(plac)} 条，机制臂 {len(mech)} 个，配对臂 {len(pairs)} 个）")


if __name__ == "__main__":
    sys.exit(main())
