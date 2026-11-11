#!/usr/bin/env python3
"""anchors.py — 给 MECHANICS-B.md 里引用到的每个引擎函数生成“出处表”。

输入：scripts/mech-b-anchors.list（每行一个 `构造函数.成员` 或 `构造函数`，# 开头是注释/分节）
      tmp/pretty/index.json（prep.sh 生成）与 /agent/repos/c136-data/src/engine/live_game_js.js
输出：标准输出（重定向到 out/mech-b-anchors.txt）。每行：
      名称 <TAB> @起始下标+长度 <TAB> 函数文本 sha256 前 10 位 <TAB> 全局访问路径 <TAB> 开头 70 个字符
用法：cd c136-review/agents/R04 && timeout 120 python3 scripts/anchors.py > out/mech-b-anchors.txt
下标是 JS 字符串下标（与 engine-evidence.txt 的 @offset 同一口径）。
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.environ.get('R04_LIVE', '/agent/repos/c136-data/src/engine/live_game_js.js')
INDEX = os.path.join(HERE, '..', 'tmp', 'pretty', 'index.json')
LIST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'mech-b-anchors.list')

src = open(LIVE, encoding='utf8').read()
# acorn 给的是 JS 字符串下标（UTF-16 码元）；文件里有 BMP 之外的字符，所以按 UTF-16 切片才对得上。
U16 = src.encode('utf-16-le')
NCHARS = len(U16) // 2


def cut(start, end):
    return U16[2 * start:2 * end].decode('utf-16-le')

ix = json.load(open(INDEX))
ctors, globs = ix['ctors'], ix['globals']


def paths_of(ctor):
    out, queue, seen = [], [], set()
    for g, c in globs.items():
        for cc in c.split('|'):
            queue.append((g, cc))
    while queue:
        path, c = queue.pop(0)
        if (path, c) in seen:
            continue
        seen.add((path, c))
        if c == ctor:
            out.append(path)
        if path.count('.') >= 2 or c not in ctors:
            continue
        for prop, cc in ctors[c]['news'].items():
            queue.append((path + '.' + prop, cc))
    return out


print(f'# mech-b-anchors  live sha256={hashlib.sha256(src.encode("utf8")).hexdigest()} chars={NCHARS}')
print('# 名称\t@下标+长度\t文本sha256前10位\t全局路径\t开头')
missing = 0
for line in open(LIST, encoding='utf8'):
    line = line.rstrip('\n')
    if not line.strip():
        continue
    if line.startswith('#'):
        print(line)
        continue
    name = line.split()[0]
    parts = name.split('.')
    ent = None
    if len(parts) == 1 and parts[0] in ctors:
        ent = ctors[parts[0]]
        ctor = parts[0]
    elif len(parts) == 2 and parts[0] in ctors and parts[1] in ctors[parts[0]]['members']:
        ent = ctors[parts[0]]['members'][parts[1]]
        ctor = parts[0]
    if ent is None:
        print(f'{name}\tNOT-FOUND')
        missing += 1
        continue
    text = cut(ent['start'], ent['end'])
    h = hashlib.sha256(text.encode('utf8')).hexdigest()[:10]
    head = text[:70].replace('\n', ' ')
    print(f'{name}\t@{ent["start"]}+{ent["end"] - ent["start"]}\t{h}\t{",".join(paths_of(ctor)) or "-"}\t{head}')
print(f'# 共 {missing} 个未找到')
