#!/usr/bin/env python3
"""build_report.py — 把报告源文件里的表格占位符换成 out/cross/ 里脚本表的原文，报告里的表与脚本输出逐字一致（不手抄数字）。

    python3 scripts/build_report.py scripts/report_src/CROSS-MATCH-SUMMARY.src.md reports/CROSS-MATCH-SUMMARY.md

占位符各占一行：
  {{TAB X2-land.txt [X2a] cols=0,1,3,4,5 where=1:编队|敌方真人 head=局|在场|…}}
        取该文件 [X2a] 段的表头行与数据行（段 = 标记行之后第一行含「 | 」且不以 # 开头的行起，到空行或下一个 [ 标记止）；
        没有段标记的文件写 - ，取文件里第一张表；cols 按列号挑列（从 0 起，省略 = 全部）；where=列号:值|值 只留该列等于这些值的行；
        head= 用「|」分开的新表头（列数要和挑出来的列一样多；省略 = 用原表头）；rows=A051|A041 只留这些局（第 0 列）；
        nohead=1 该段没有表头行（要配 head=）；join=K 把第 K 列起的各列并成一列；top=N 只留前 N 行；nofoot=1 不带表尾的单列说明行。
  {{SER A1,A2,B6 head=局|人均地比 630|…}}
        从 X12-summary.txt 里取编号开头是 A1、A2、B6 的几行，转成「每局一行」的表（各局取值按 X12 文件头写的顺序）。
  {{LINE X12-summary.txt 计数 | A1 }}
        原样取该文件里第一条以给定文字开头（去掉行首空格后）的行，前面加「> 」。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROSS = os.path.join(ROOT, "out", "cross")


def read(name):
    return open(os.path.join(CROSS, name), encoding="utf-8").read().split("\n")


def section(lines, mark):
    i = 0
    if mark != "-":
        i = next((k for k, x in enumerate(lines) if x.startswith(mark)), None)
        if i is None:
            raise SystemExit(f"找不到段 {mark}")
        i += 1
    while i < len(lines) and (lines[i].startswith("#") or " | " not in lines[i]):
        i += 1
    out = []
    while i < len(lines) and lines[i].strip() and not lines[i].startswith("["):
        if not lines[i].startswith("#") and not lines[i].lstrip().startswith("!!"):
            out.append([c.strip() for c in lines[i].split(" | ")])
        i += 1
    return out


def opts(text):
    o = {}
    for m in re.finditer(r"(\w+)=((?:[^\s]|\s(?!\w+=))+)", text):
        o[m.group(1)] = m.group(2).strip()
    return o


def md(rows):
    n = len(rows[0])
    out = ["| " + " | ".join(rows[0]) + " |", "|" + " :-- |" * n]
    for r in rows[1:]:
        r = (r + [""] * n)[:n]
        out.append("| " + " | ".join(r) + " |")
    return out


def tab(arg):
    parts = arg.split(None, 2)
    fname, mark = parts[0], parts[1]
    o = opts(parts[2] if len(parts) > 2 else "")
    rows = section(read(fname), mark)
    head, body = rows[0], rows[1:]
    if "nohead" in o:
        width = max(len(r) for r in rows)
        head, body = [""] * width, rows
    if "join" in o:
        k = int(o["join"])
        body = [r[:k] + [" ｜ ".join(r[k:])] for r in body]
        head = head[:k + 1]
    if "top" in o:
        body = body[:int(o["top"])]
    if "where" in o:
        ci, vals = o["where"].split(":", 1)
        vals = set(vals.split("|"))
        body = [r for r in body if len(r) > int(ci) and r[int(ci)] in vals]
    if "rows" in o:
        keep = set(o["rows"].split("|"))
        body = [r for r in body if r[0] in keep]
    foot = [r for r in body if len(r) == 1]
    body = [r for r in body if len(r) > 1]
    if "cols" in o:
        idx = [int(x) for x in o["cols"].split(",")]
        head = [head[k] if k < len(head) else "" for k in idx]
        body = [[r[k] if k < len(r) else "" for k in idx] for r in body]
    if "head" in o:
        nh = [x.strip() for x in o["head"].split("|")]
        if len(nh) != len(head):
            raise SystemExit(f"{fname} {mark}: head 给了 {len(nh)} 列，挑出来的是 {len(head)} 列")
        head = nh
    out = md([head] + body)
    if foot and "nofoot" not in o:
        out.append("")
        out += ["> " + r[0] for r in foot]
    return out


def ser(arg):
    parts = arg.split(None, 1)
    ids = parts[0].split(",")
    o = opts(parts[1] if len(parts) > 1 else "")
    lines = read("X12-summary.txt")
    order = next(x for x in lines if x.startswith("# 各局取值的顺序：")).split("：", 1)[1].split("；")[0].split()
    cols, names = [], []
    for i in ids:
        line = next((x for x in lines if x.startswith(i + " ")), None)
        if line is None:
            raise SystemExit(f"X12 里找不到 {i}")
        cells = line.split(" | ")
        names.append(cells[0].split("（")[0])
        cols.append(cells[1].split())
    head = ["局"] + names
    if "head" in o:
        nh = [x.strip() for x in o["head"].split("|")]
        if len(nh) != len(head):
            raise SystemExit(f"SER {parts[0]}: head 给了 {len(nh)} 列，应为 {len(head)} 列")
        head = nh
    rows = [head]
    for k, m in enumerate(order):
        rows.append([m] + [c[k] for c in cols])
    return md(rows)


def line(arg):
    fname, key = arg.split(None, 1)
    key = key.strip()
    for x in read(fname):
        if x.strip().startswith(key):
            return ["> " + x.strip()]
    raise SystemExit(f"{fname} 里找不到以「{key}」开头的行")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    src = src if os.path.isabs(src) else os.path.join(ROOT, src)
    dst = dst if os.path.isabs(dst) else os.path.join(ROOT, dst)
    out = []
    n = 0
    for raw in open(src, encoding="utf-8").read().split("\n"):
        m = re.match(r"^\{\{(TAB|SER|LINE)\s+(.*)\}\}\s*$", raw)
        if not m:
            out.append(raw)
            continue
        n += 1
        out += {"TAB": tab, "SER": ser, "LINE": line}[m.group(1)](m.group(2))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"写 {os.path.relpath(dst, ROOT)}（{len(out)} 行，替换了 {n} 处占位符）")


if __name__ == "__main__":
    main()
