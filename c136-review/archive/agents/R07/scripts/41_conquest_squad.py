#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""41_conquest_squad.py — R07：把 conquest.txt A 段里「从 我方号」那一列按时间段加起来（94_conquest.mjs 只印了每个吃地方的格子，没有印列合计）。

用法（在 scripts/ 目录下）：
    python3 41_conquest_squad.py <matchId> [--merge t0:t1]...
        --merge：把 conquest.txt 里相邻的几个时间段并成一段再列一行（t0、t1 必须是 conquest.txt 的切点），写在 C 段；
                 同一行另给「其他真人队吃进合计」（conquest.txt A 段里「T? 真人」各行的吃进合计相加，我方号所在队的别的真人如果单列也算在内）。

输入：out/<matchId>/conquest.txt（94_conquest.mjs 的逐格过户账）
输出：out/<matchId>/conquest_squad.txt
    每个时间段一行：我方吃进合计 | 我方被直接打掉（进攻目标就是我方号）| 我方清场后被别人捡走（a + b 里的 b）| 两项合计（= 各吃地方「从 我方号」之和）|
    我方清场放掉（变成无主地的格数；其中被捡走的就是前一列，其余到段末还是无主地或被我方自己捡回）| 各吃地方明细
    最后一行：全程合计。
    B 段：conquest.txt C 段里每个指定玩家，全程「它的地被谁拿走」按拿的一方合计（直接 + 清场后被捡走），带 * 的是我方号；
          再给一行「我方合计 / 别人合计 / 清场放掉合计」和它全程从我方号手里拿走的格数。
    口径：和 conquest.txt 相同（每格「崩盘后捡走」只算第一次）；「我方号」含已离开的我方席位。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def num(s):
    return int(s.replace(",", ""))


SQUAD_RE = re.compile(r"^\*(sora_w|ryan_m|noah88|zexos1|talon5|alex_k|leo_tx|zero_7|kaito9|riku_x)#\d+\[T\d+\]$")


def is_squad(name):
    """conquest.txt 里我方号写成「*alex_k#11[T2]」。只看开头的 * 不够：A070 对面有个真人的名字本身以 * 开头（*Cr-nA* …）。"""
    return bool(SQUAD_RE.match(name.strip()))


def split_items(body):
    """把「甲 1,234 + 56、乙 78」拆成 [(甲, 1234, 56), (乙, 78, 0)]；名字里可能带空格和 #。"""
    items = []
    for part in body.split("、"):
        m = re.match(r"^(.*?) ([\d,]+)(?: \+ ([\d,]+))?$", part.strip())
        if m:
            items.append((m.group(1), num(m.group(2)), num(m.group(3)) if m.group(3) else 0))
    return items


def focus_totals(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("C. ")), None)
    res = []
    if start is None:
        return res
    cur, taken, got, cleared = None, {}, {}, 0

    def flush():
        if cur is None:
            return
        ours = sum(a + b for k, (a, b) in taken.items() if is_squad(k))
        others = sum(a + b for k, (a, b) in taken.items() if not is_squad(k))
        from_ours = sum(a + b for k, (a, b) in got.items() if is_squad(k))
        order = sorted(taken.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
        txt = "、".join(f"{k} {a:,}" + (f" + {b:,}" if b else "") for k, (a, b) in order) or "-"
        res.append(f"  {cur}\t{txt}\t我方 {ours:,}\t别人 {others:,}\t清场放掉 {cleared:,}\t从我方号拿走 {from_ours:,}")

    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            flush()
            cur, taken, got, cleared = ln[3:], {}, {}, 0
            continue
        if cur is None or "|" not in ln:
            continue
        seg = ln.split("|")
        m = re.search(r"吃进 [\d,]+（(.*)）", seg[0])
        if m and m.group(1) != "-":
            for k, a, b in split_items(m.group(1)):
                x = got.setdefault(k, [0, 0])
                x[0] += a
                x[1] += b
        m = re.search(r"被拿走 [\d,]+（(.*)）", seg[1])
        if m and m.group(1) != "-":
            for k, a, b in split_items(m.group(1)):
                x = taken.setdefault(k, [0, 0])
                x[0] += a
                x[1] += b
        m = re.search(r"清场放掉 ([\d,]+)", seg[2]) if len(seg) > 2 else None
        if m:
            cleared += num(m.group(1))
    flush()
    return res


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mid = sys.argv[1]
    outdir = os.path.join(HERE, "..", "out", mid)
    rows, cur, hdr = [], None, None
    for ln in open(os.path.join(outdir, "conquest.txt"), encoding="utf-8"):
        ln = ln.rstrip("\n")
        if ln.startswith("B."):
            break
        if ln.startswith("## t="):
            cur = {"span": ln[3:], "intake": 0, "direct": 0, "picked": 0, "cleared": 0, "by": []}
            rows.append(cur)
            hdr = None
            continue
        if cur is None:
            continue
        if ln.startswith("吃地的一方"):
            hdr = ln.split("\t")
            continue
        if ln.startswith("清场放掉"):
            m = re.search(r"我方号 ([\d,]+)", ln)
            cur["cleared"] = num(m.group(1)) if m else 0
            continue
        if hdr and "\t" in ln:
            cells = ln.split("\t")
            row = dict(zip(hdr, cells))
            if cells[0] == "我方号":
                cur["intake"] = num(row.get("吃进合计", "0"))
                continue
            if re.match(r"^T\d+ 真人$", cells[0]):
                cur["humans"] = cur.get("humans", 0) + num(row.get("吃进合计", "0"))
            v = row.get("从 我方号")
            if v and v != "0":
                parts = [num(x) for x in v.split(" + ")]
                cur["direct"] += parts[0]
                if len(parts) > 1:
                    cur["picked"] += parts[1]
                cur["by"].append(f"{cells[0]} {v}")
    out = [f"# {mid} 我方号的地：各时间段吃进 / 被直接打掉 / 清场后被捡走 / 清场放掉（41_conquest_squad.py；conquest.txt A 段「从 我方号」一列的合计）",
           "时间段\t吃进合计\t被直接打掉\t清场后被捡走\t被拿走合计\t清场放掉\t谁拿的（直接 + 清场后捡）"]
    tot = [0, 0, 0, 0, 0]
    for r in rows:
        vals = [r["intake"], r["direct"], r["picked"], r["direct"] + r["picked"], r["cleared"]]
        tot = [a + b for a, b in zip(tot, vals)]
        out.append(f"{r['span']}\t" + "\t".join(f"{v:,}" for v in vals) + "\t" + "；".join(r["by"]))
    out.append("全程\t" + "\t".join(f"{v:,}" for v in tot) + "\t")
    out.append("")
    out.append("B. 指定玩家全程：它的地被谁拿走（直接 + 清场后被捡走，按拿的一方合计）| 我方合计 | 别人合计 | 清场放掉合计 | 它从我方号手里拿走")
    out.extend(focus_totals(os.path.join(outdir, "conquest.txt")))
    merges = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--merge" and i + 1 < len(sys.argv)]
    if merges:
        out.append("")
        out.append("C. 合并时间段（--merge）：吃进合计 | 被直接打掉 | 清场后被捡走 | 被拿走合计 | 清场放掉 | 其他真人队吃进合计 | 并了哪几段")
        spans = []
        for r in rows:
            m = re.match(r"t=(-?\d+)~(\d+)", r["span"])
            spans.append((int(m.group(1)), int(m.group(2))) if m else None)
        for mg in merges:
            a, b = (int(x) for x in mg.split(":"))
            sel = [r for r, sp in zip(rows, spans) if sp and sp[0] >= a and sp[1] <= b]
            ok = bool(sel) and any(sp and sp[0] == a for sp in spans) and any(sp and sp[1] == b for sp in spans)
            if not ok:
                out.append(f"  t={a}~{b}\t（不是 conquest.txt 的切点，没法合并）")
                continue
            vals = [sum(r["intake"] for r in sel), sum(r["direct"] for r in sel), sum(r["picked"] for r in sel),
                    sum(r["direct"] + r["picked"] for r in sel), sum(r["cleared"] for r in sel), sum(r.get("humans", 0) for r in sel)]
            out.append(f"  t={a}~{b}\t" + "\t".join(f"{v:,}" for v in vals) + "\t" + " + ".join(r["span"] for r in sel))
    path = os.path.join(outdir, "conquest_squad.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"-> {os.path.relpath(path, os.path.join(HERE, '..', '..', '..', '..'))}")


if __name__ == "__main__":
    main()
