#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""49c_audit_by_game.py — R07：比 49b 再严一层的自查，看「数字是不是挂在对的那一局上」。

49b 只看一个数在脚本输出里出现过没有。这里把 .md 按句子切开（。；），每一句里提到哪几局
（A0xx / G0x / g09…），就只到那几局自己的文件里找这句话里的数：
    reviews/<局>.json、reviews/<局>.md、out/<局>/*.txt|tsv|json
一句话里没提局号的，沿用同一行里前一句的局号；整行都没提局号的不查（那是跨局的数，归 49b 管）。
只查 ≥4 位的整数（带不带逗号都行）和带小数点的数；3 位以下的整数哪里都有，不查。
在本局文件里找不到、但在跨局输出（out/_cross/）里那一局的行里也找不到的，逐个列出来人工看。

用法：python3 49c_audit_by_game.py [报告路径 ...]
  不给路径时查 reports/COUNCIL-PROPOSAL.md。
输出：只打印到终端（不写文件）。
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, '..'))
GAME = re.compile(r'(?<![A-Za-z0-9_])([AG]\d{2,3}|g\d{2})(?![A-Za-z0-9_])')
INT = re.compile(r'(?<![\d,.A-Za-z_])(\d{1,3}(?:,\d{3})+|\d{4,})(?![\d,]|\.\d)')
DEC = re.compile(r'(?<![\d,.A-Za-z_])(\d+\.\d+)(?![\d])')
SPLIT = re.compile(r'[。；]')


def norm(tok):
    return tok.replace(',', '')


def load_game(gid):
    texts = []
    pats = [
        os.path.join(BASE, 'reviews', gid + '.json'),
        os.path.join(BASE, 'reviews', gid + '.md'),
        os.path.join(BASE, 'out', gid, '*.txt'),
        os.path.join(BASE, 'out', gid, '*.tsv'),
        os.path.join(BASE, 'out', gid, '*.json'),
    ]
    for pat in pats:
        for f in glob.glob(pat):
            try:
                texts.append(open(f, encoding='utf-8', errors='replace').read())
            except OSError:
                pass
    big = '\n'.join(texts)
    nums = set()
    for m in re.finditer(r'\d{1,3}(?:,\d{3})+|\d+\.\d+|\d+', big):
        nums.add(norm(m.group(0)))
    return nums


def load_cross():
    """跨局输出里，按行收集：这一行提到的局号 -> 这一行里的数。"""
    by_game = {}
    for f in glob.glob(os.path.join(BASE, 'out', '_cross', '*')):
        if not f.endswith(('.txt', '.tsv', '.json')):
            continue
        try:
            text = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for line in text.split('\n'):
            gids = set(GAME.findall(line))
            if not gids:
                continue
            ns = {norm(m.group(0)) for m in re.finditer(r'\d{1,3}(?:,\d{3})+|\d+\.\d+|\d+', line)}
            for g in gids:
                by_game.setdefault(g, set()).update(ns)
    return by_game


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not paths:
        paths = [os.path.join(BASE, 'reports', 'COUNCIL-PROPOSAL.md')]
    cache = {}
    cross = load_cross()
    for p in paths:
        text = open(p, encoding='utf-8').read()
        checked = 0
        misses = []
        in_code = False
        for ln, line in enumerate(text.split('\n'), 1):
            if line.startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            ctx = []
            for seg in SPLIT.split(line):
                gids = GAME.findall(seg)
                if gids:
                    ctx = sorted(set(gids))
                if not ctx:
                    continue
                toks = [m.group(1) for m in INT.finditer(seg)]
                toks += [m.group(1) for m in DEC.finditer(seg)]
                for tok in toks:
                    at = seg.find(tok)
                    if seg[max(0, at - 1):at] == 'L' or re.search(r'L\d+-$', seg[max(0, at - 8):at]):
                        continue
                    n = norm(tok)
                    checked += 1
                    ok = False
                    for g in ctx:
                        if g not in cache:
                            cache[g] = load_game(g)
                        if n in cache[g] or n in cross.get(g, ()):
                            ok = True
                            break
                    if not ok:
                        misses.append((ln, tok, ','.join(ctx), seg.strip()[:70]))
        print('%s：查了 %d 个挂着局号的数；%d 个在那一局自己的文件里找不到：' % (
            os.path.relpath(p, BASE), checked, len(misses)))
        for ln, tok, g, seg in misses:
            print('  行 %d\t%s\t[%s]\t%s' % (ln, tok, g, seg))


if __name__ == '__main__':
    main()
