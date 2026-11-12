#!/usr/bin/env python3
"""pattern_evidence.py — 按模式键把已复盘各局 reviews/<局>.json 的 decisions[] 抽出来（给假设卡的「13 局证据」一节用）。

用法：python3 scripts/pattern_evidence.py 键 [键…] [--full] [--md]
      键可以是完整键（AT-BOTLOCK）或前缀（AT-、IO-）；--full 连 evidence[] 一起列；--md 输出 Markdown 列表。
      不带键 = 列出全部键和出现的局数。
输出：每条 = 局 · 决策号 · 拍 · 号 · 判定 · what（一句话）· codePath。数字只来自各局复盘文件，本脚本不做新的计量。
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV = os.path.abspath(os.path.join(HERE, '..', 'reviews'))
a = sys.argv[1:]
full, md = '--full' in a, '--md' in a
keys = [x for x in a if not x.startswith('--')]
J = {f[:-5]: json.load(open(os.path.join(REV, f))) for f in sorted(os.listdir(REV)) if f.endswith('.json')}

if not keys:
    cnt = collections.defaultdict(lambda: collections.Counter())
    for m, j in J.items():
        for d in j.get('decisions') or []:
            cnt[d.get('patternKey') or '?'][m] += 1
    for k, c in sorted(cnt.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"{k}\t{len(c)} 局\t{sum(c.values())} 条\t" + ' '.join(f'{m}×{n}' if n > 1 else m for m, n in sorted(c.items())))
    raise SystemExit

for key in keys:
    rows = []
    for m, j in J.items():
        for d in j.get('decisions') or []:
            pk = d.get('patternKey') or ''
            if pk == key or (key.endswith('-') and pk.startswith(key)):
                rows.append((m, d))
    vc = collections.Counter(d.get('verdict') for _, d in rows)
    print(f"===== {key}：{len({m for m, _ in rows})} 局 {len(rows)} 条｜判定 " + '、'.join(f'{k} {v}' for k, v in vc.most_common()) + ' =====')
    for m, d in rows:
        bots = d.get('bots')
        if isinstance(bots, (list, tuple)):
            bots = '、'.join(str(z) for y in bots for z in (y if isinstance(y, (list, tuple)) else [y]))
        head = f"{m} {d.get('id')} t={d.get('t')} [{bots}] {d.get('verdict')}"
        if md:
            print(f"- **{head}**：{d.get('what')}（`{d.get('codePath')}`）")
        else:
            print(f"{head}\n    做了什么：{d.get('what')}\n    为什么/后果：{d.get('why')}\n    代码：{d.get('codePath')}")
        if full:
            ev = d.get('evidence') or []
            for e in ([ev] if isinstance(ev, str) else ev):
                print(f"    · {e}")
