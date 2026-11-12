#!/usr/bin/env python3
"""build_report.py — 把汇总表嵌进报告正文。

正文写在 reports/ckpt-data/REPORT.tmpl.md；里面的占位符

    {{ckpt:表 H:1}}                 ckpt_tables.md 里「### 表 H」这一节的第 1 张表（整张）
    {{ckpt:表 C2:1:rows=^\\| 全部}}   只留表头和匹配正则的行
    {{ckpt:表 R:note}}              这一节里表后面的那段说明文字（不以 | 开头的非空行，按出现次序拼起来）
    {{ckpt:表 G:note:2}}            第 2 段说明文字
    {{fid:①:1}}                     fid_tables.md 里「## ①」这一节的第 1 张表

换成对应的内容，写到 reports/OFFLINE-CHECKPOINT-ATTRIBUTION.md。表没生成（那一批还没跑出来）时占位符换成一行「（这一组还没跑完）」。
正文里手写的数字不归它管——改完数据要自己对一遍（脚本会把正文里出现的「待补」标记数出来提醒）。

用法（在 agents/R01 下）：python3 scripts/ckpt/build_report.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(R01, 'reports', 'ckpt-data')
TMPL = os.path.join(DATA, 'REPORT.tmpl.md')
OUT = os.path.join(R01, 'reports', 'OFFLINE-CHECKPOINT-ATTRIBUTION.md')
SRC = {'ckpt': ('ckpt_tables.md', '### '), 'fid': ('fid_tables.md', '## ')}


def sections(name):
    fn, mark = SRC[name]
    out, cur = {}, None
    for line in open(os.path.join(DATA, fn), encoding='utf8').read().split('\n'):
        if line.startswith(mark):
            title = line[len(mark):].strip()
            key = re.split(r'[\s　]', title, maxsplit=1)[0] if name == 'fid' else '表 ' + re.split(r'[\s　]', title[2:].strip(), maxsplit=1)[0] if title.startswith('表') else title
            cur = out.setdefault(key, [])
            continue
        if cur is not None:
            cur.append(line)
    return out


def tables(lines):
    """→ [表（连续的 | 行）…]"""
    out, cur = [], []
    for line in lines:
        if line.startswith('|'):
            cur.append(line)
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def notes(lines):
    """→ [说明段落…]（不以 | 开头的非空行；相邻的并成一段）"""
    out, cur = [], []
    for line in lines:
        if line.strip() and not line.startswith('|'):
            cur.append(line)
        elif cur:
            out.append('\n'.join(cur)); cur = []
    if cur:
        out.append('\n'.join(cur))
    return out


def main():
    sec = {k: sections(k) for k in SRC}
    text = open(TMPL, encoding='utf8').read()
    missing = []

    def sub(m):
        src, key, rest = m.group(1), m.group(2).strip(), (m.group(3) or '').strip(':')
        parts = rest.split(':') if rest else []
        s = sec[src].get(key)
        if s is None:
            missing.append(m.group(0))
            return '（这一组还没跑完）'
        if parts and parts[0] == 'note':
            ns = notes(s)
            i = int(parts[1]) - 1 if len(parts) > 1 else 0
            if i >= len(ns):
                missing.append(m.group(0))
                return '（这一组还没跑完）'
            return ns[i]
        i = int(parts[0]) - 1 if parts and parts[0].isdigit() else 0
        ts = tables(s)
        if i >= len(ts):
            missing.append(m.group(0))
            return '（这一组还没跑完）'
        t = ts[i]
        flt = next((p[5:] for p in parts if p.startswith('rows=')), None)
        if flt:
            rx = re.compile(flt)
            t = t[:2] + [r for r in t[2:] if rx.search(r)]
        cols = next((p[5:] for p in parts if p.startswith('cols=')), None)
        if cols:
            keep = [int(c) for c in cols.split(',')]
            def cut(r):
                cells = r.strip().strip('|').split('|')
                return '| ' + ' | '.join(cells[c - 1].strip() for c in keep if c - 1 < len(cells)) + ' |'
            t = [cut(r) for r in t]
        return '\n'.join(t)

    text = re.sub(r'\{\{(ckpt|fid):([^:}]+)((?::[^:}]+)*)\}\}', sub, text)
    open(OUT, 'w', encoding='utf8').write(text)
    todo = len(re.findall(r'待补', text))
    print(f'写出 {os.path.relpath(OUT, R01)}：{len(text.splitlines())} 行；没填上的占位符 {len(missing)} 个；正文里「待补」{todo} 处')
    for x in missing:
        print('  没填上：', x)


if __name__ == '__main__':
    sys.exit(main())
