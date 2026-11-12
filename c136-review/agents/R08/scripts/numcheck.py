#!/usr/bin/env python3
"""numcheck.py — 文稿里的数字对不对得上脚本输出（「没有脚本的数字不收」的自查工具）。

    python3 numcheck.py cards/H15-post-1500-gates.md reports/CROSS-MATCH-SUMMARY.md [--all] [--show N]

做法：把文稿里的数字记号逐个拿出来，到「数字来源」里找一模一样的记号；找不到的列出来（带行号和上下文），人工逐条看：
要么是抄错了，要么是手算的派生数（改成脚本里算、或者改写法），要么是结构性的数（拍号窗口、代码行号、参数取值——这些有白名单）。

数字来源：
  out/_cross/*.txt（跨局脚本的输出）、out/_cross/params.txt、out/_cross/codemap.txt、
  reviews/*.md 和 reviews/*.json（16 份复盘稿，已过 checker）、out/<局>/*.txt（各局事实表的文字输出）、
  src/engine/live-donation-check.txt（hub 的数据文件，H12 引过）。
不查的记号：
  代码行号（L 开头的，或 `…js` / `…mjs` / `…py` 后面跟的行号范围）、卡号 / 模式号 / 局号里的数字、反引号里的代码片段、
  白名单里的结构性数字（拍号窗口、分位点名、参数取值等，见 STRUCT）。
只读 c136-review/agents/R08/ 和 /agent/repos/c136-data/src/engine/live-donation-check.txt。
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")

# 结构性数字：拍号、窗口、分位点、参数取值（params.txt 里有的也会自动进来源，这里只放文稿里常当「名字」用的）
STRUCT = set("""0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 24 25 30 35 40 45 50 60 64 75 80 85 88 90 95 99 100 107 110 116 120 123 136 141 150 180 200 250 256 300 357 400 450 500 512
600 630 714 800 900 1000 1023 1024 1071 1100 1200 1260 1500 1530 1800 2000 2142 2400 2500 3000 3060 3213 4000 4284 4500 4800 5000 6000 6030 8500 10000 20000
0.05 0.1 0.2 0.25 0.3 0.35 0.5 0.7 0.75 0.9 1.0 1.25 1.5 1.6 1.78 2.0 3.2""".split())

NUM = re.compile(r"(?<![A-Za-z_\d.])[-+−]?\d[\d,]*(?:\.\d+)?%?(?![\d])")


def norm(tok):
    t = tok.replace(",", "").replace("−", "-").lstrip("+")
    if t.endswith("%"):
        t = t[:-1]
    if "." in t:
        t = t.rstrip("0").rstrip(".") if not t.endswith(".0") else t[:-2]
    if t.startswith("-"):
        t = t[1:]
    return t


def tokens(text):
    for m in NUM.finditer(text):
        yield m.start(), m.group(0)


def strip_code(line):
    """去掉反引号片段、代码行号、编号里的数字。"""
    line = re.sub(r"`[^`]*`", " ", line)
    line = re.sub(r"\bL\d+(?:\s*[-–~]\s*L?\d+)?", " ", line)
    line = re.sub(r"\b(?:NEW-)?[A-Z]{1,3}-?[A-Z]?\d+[A-Za-z]?\b", " ", line)          # H01、NEW-EC-07、B029、A051、E2、G02、XT-C
    line = re.sub(r"\[(?:X[A-Z]|XM|XP|XS|XT|XD|XG|XO|XB|PA|CM)-[A-Z]\d*\]", " ", line)
    line = re.sub(r"https?://\S+", " ", line)
    return line


def load_sources():
    src = set()
    pats = [os.path.join(ROOT, "out", "_cross", "*.txt"), os.path.join(ROOT, "reviews", "*.md"), os.path.join(ROOT, "reviews", "*.json"),
            os.path.join(ROOT, "out", "*", "*.txt"), os.path.join(DATA, "src", "engine", "live-donation-check.txt")]
    n = 0
    for pat in pats:
        for p in glob.glob(pat):
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            n += 1
            for _pos, tok in tokens(text):
                src.add(norm(tok))
    return src, n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show = 400
    if "--show" in sys.argv:
        show = int(sys.argv[sys.argv.index("--show") + 1])
        args = [a for a in args if a != str(show)]
    if not args:
        args = sorted(glob.glob(os.path.join(ROOT, "cards", "*.md"))) + sorted(glob.glob(os.path.join(ROOT, "reports", "*.md")))
    src, nfiles = load_sources()
    print(f"数字来源：{nfiles} 个文件，{len(src)} 个不同的数字记号")
    total = miss = 0
    for path in args:
        p = path if os.path.isabs(path) else os.path.join(ROOT, path) if not os.path.exists(path) else path
        with open(p, encoding="utf-8") as f:
            lines = f.read().split("\n")
        bad = []
        in_code = False
        cnt = 0
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            clean = strip_code(line)
            for pos, tok in tokens(clean):
                t = norm(tok)
                if not t or t in STRUCT:
                    continue
                cnt += 1
                if t in src:
                    continue
                # 「12.3 万」这类万位写法：×10000 之后前三位对得上就算找到
                bad.append((i, tok, clean[max(0, pos - 24):pos + len(tok) + 24].strip()))
        total += cnt
        miss += len(bad)
        print(f"\n{os.path.relpath(p, ROOT)}：数字记号 {cnt} 个，来源里找不到的 {len(bad)} 个")
        for i, tok, ctx in bad[:show]:
            print(f"  行 {i}: {tok}    …{ctx}…")
    print(f"\n合计：数字记号 {total} 个，来源里找不到的 {miss} 个")


if __name__ == "__main__":
    main()
