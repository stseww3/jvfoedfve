#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""49b_audit_report.py — R07：跨局报告 / 假设卡 / 议题建议成稿前自查「没有脚本的数字不收」。

把一份 .md 里的数字拿出来，看它是否在脚本输出里出现过：
  - ≥3 位的整数（带逗号或不带逗号）
  - 小数（如 0.67、39.5）
  - 百分数（如 37%、18.6%）
对照的文件（默认）：out/_cross/ 下的 .txt / .tsv / .json，reviews/*.json，reviews/*.md。
可以用 --src 追加别的文件或通配（可多次）。
找不到的逐个列出来（数值 + 行号 + 那一行的开头）。剩下的应该只有三类：
  (a) 正文里写明了算式的加减（「a + b」）；(b) 源码行号（紧跟在 L 后面的不列）；
  (c) 口径里的阈值（如「≥180 拍」）——这些要逐个看一眼确认。
1~2 位的整数不查（哪里都有），要靠人对表。

用法：python3 49b_audit_report.py [报告路径 ...] [--src 通配 ...] [--all]
  不给路径时查 reports/*.md 和 cards/*.md。--all：连找到的也列出来（数值 → 第一个出现的文件）。
输出：只打印到终端（不写文件）。
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, '..'))
INT = re.compile(r'(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d{3,})(?![\d,]|\.\d)')
DEC = re.compile(r'(?<![\d,.])(\d+\.\d+)(?![\d%])')
PCT = re.compile(r'(?<![\d,.])(\d+(?:\.\d+)?)%')


def tokens(text):
    out = {}
    for ln, line in enumerate(text.split('\n'), 1):
        s = line.strip()
        if s.startswith(('python3 ', 'bash ', 'cd ', '#!')) or 'run-heavy.sh' in line:
            continue
        for m in INT.finditer(line):
            pre = line[max(0, m.start() - 1):m.start()]
            if pre == 'L' or re.search(r'L\d+-$', line[max(0, m.start() - 8):m.start()]):
                continue
            # 局号（A070、B029、G01）和脚本编号不算
            if re.search(r'[A-Za-z_]$', line[max(0, m.start() - 1):m.start()]):
                continue
            out.setdefault(('int', int(m.group(1).replace(',', ''))), []).append((ln, line))
        for m in DEC.finditer(line):
            out.setdefault(('dec', m.group(1)), []).append((ln, line))
        for m in PCT.finditer(line):
            out.setdefault(('pct', m.group(1)), []).append((ln, line))
    return out


def main():
    a = sys.argv[1:]
    srcs = []
    paths = []
    show_all = False
    i = 0
    while i < len(a):
        if a[i] == '--src':
            srcs.append(a[i + 1])
            i += 2
        elif a[i] == '--all':
            show_all = True
            i += 1
        else:
            paths.append(a[i])
            i += 1
    if not paths:
        paths = sorted(glob.glob(os.path.join(BASE, 'reports', '*.md'))) + sorted(glob.glob(os.path.join(BASE, 'cards', '*.md')))
    pats = [os.path.join(BASE, 'out', '_cross', '*.txt'), os.path.join(BASE, 'out', '_cross', '*.tsv'),
            os.path.join(BASE, 'out', '_cross', '*.json'), os.path.join(BASE, 'reviews', '*.json'),
            os.path.join(BASE, 'reviews', '*.md')] + srcs
    files = []
    for p in pats:
        files += sorted(glob.glob(p))
    ints, decs, pcts = {}, {}, {}
    for f in files:
        try:
            txt = open(f, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        name = os.path.relpath(f, BASE)
        for x in re.findall(r'(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d+)(?![\d,])', txt):
            ints.setdefault(int(x.replace(',', '')), name)
        for x in re.findall(r'(?<![\d,])(\d+\.\d+)', txt):
            decs.setdefault(x, name)
            # 0.50 和 0.5、39.50 和 39.5 算同一个数
            decs.setdefault(x.rstrip('0').rstrip('.'), name)
        for x in re.findall(r'(\d+(?:\.\d+)?)%', txt):
            pcts.setdefault(x, name)
    for path in paths:
        text = open(path, encoding='utf-8').read()
        toks = tokens(text)
        miss = []
        hit = []
        for (kind, v), where in toks.items():
            if kind == 'int':
                ok = ints.get(v)
            elif kind == 'dec':
                ok = decs.get(v) or decs.get(v.rstrip('0').rstrip('.'))
            else:
                ok = pcts.get(v)
            (hit if ok else miss).append((kind, v, where, ok))
        print(f'{os.path.relpath(path, BASE)}：{len(toks)} 个不同的数（≥3 位整数 / 小数 / 百分数）；对照 {len(files)} 个文件；{len(miss)} 个找不到：')
        for kind, v, where, _ in sorted(miss, key=lambda r: r[2][0][0]):
            lns = ','.join(str(x[0]) for x in where[:6])
            shown = f'{v:,}' if kind == 'int' else (v + '%' if kind == 'pct' else v)
            print(f'  {shown}\t行 {lns}\t{where[0][1].strip()[:70]}')
        if show_all:
            print('  —— 找到的：')
            for kind, v, where, ok in sorted(hit, key=lambda r: r[2][0][0]):
                shown = f'{v:,}' if kind == 'int' else (v + '%' if kind == 'pct' else v)
                print(f'  {shown}\t行 {where[0][0]}\t← {ok}')


if __name__ == '__main__':
    main()
