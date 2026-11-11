#!/usr/bin/env python3
# safeat_tally.py — 汇总 shadow.mjs --offers 输出里的 [safeAt 拆解] 行：
#   每个（号×采样拍）：有没有真人/离场邻居的报价、存兵是否 ≤ 留底（对谁都没有可用兵）、定留底的是哪一项
#   （dpKeep＝最强真人邻居的存兵 ÷1.78；safeFinite＝相邻机器人/离场号的「最弱的其它邻居」；封顶 88×地）、
#   同拍有没有报价过了价格门（L5359）。
# 用法：python3 safeat_tally.py <offers 输出文件>... [--detail <号>]
import re, sys
from collections import defaultdict, Counter

detail = sys.argv[sys.argv.index('--detail') + 1] if '--detail' in sys.argv else None
files = [a for i, a in enumerate(sys.argv) if i >= 1 and not a.startswith('--') and sys.argv[i - 1] != '--detail']

rows = []  # dict(bot,t,L,B,blocked,term,strong,strongBal,passed,nOffers,via,owner,ownerMate)
cur = None
for fn in files:
    for line in open(fn, encoding='utf-8'):
        m = re.match(r'-- 报价 (\S+) t=(\d+) 地 (\d+) 兵 (\d+) 密度 ([\d.]+)｜.*报价 (\d+) 条', line)
        if m:
            cur = dict(bot=m.group(1), t=int(m.group(2)), L=int(m.group(3)), B=int(m.group(4)), nOffers=int(m.group(6)),
                       blocked=False, term=None, strong=None, strongBal=0, passed=0, via=None, owner=None, ownerMate=False, safe=0)
            rows.append(cur)
            continue
        if cur is None:
            continue
        if '[safeAt 拆解]' in line:
            cur['blocked'] = '对谁都没有可用兵' in line
            mm = re.search(r'定值的是 (\S+?)｜', line)
            cur['term'] = mm.group(1) if mm else None
            mm = re.search(r'safeAt\(-1\)=(\d+)', line)
            cur['safe'] = int(mm.group(1)) if mm else 0
            mm = re.search(r'最强真人邻居 (.+?) (\d+)）', line)
            if mm:
                cur['strong'], cur['strongBal'] = mm.group(1), int(mm.group(2))
            mm = re.search(r'经 (.+?)；它「最弱的其它邻居」是 (.+?)，存兵', line)
            if mm:
                cur['via'], cur['owner'] = mm.group(1), mm.group(2)
                cur['ownerMate'] = '〔我方号〕' in mm.group(2)
        elif '过价格门' in line:
            cur['passed'] += 1

by = defaultdict(list)
for r in rows:
    by[r['bot']].append(r)
print(f'[safeAt 留底汇总] 采样（号×拍）{len(rows)} 个；有报价的 {sum(1 for r in rows if r["nOffers"])} 个')
tot = Counter()
for b, rs in by.items():
    has = [r for r in rs if r['nOffers']]
    blk = [r for r in has if r['blocked']]
    terms = Counter(r['term'] for r in blk)
    blk_pass = [r for r in blk if r['passed']]
    ratio = sorted(r['strongBal'] / max(1, r['B']) for r in blk if r['strongBal'])
    mate = [r for r in has if r['ownerMate']]
    tot['has'] += len(has); tot['blk'] += len(blk); tot['blkpass'] += len(blk_pass)
    for k, v in terms.items():
        tot['term:' + str(k)] += v
    med = ratio[len(ratio) // 2] if ratio else 0
    print(f'  {b}: 有报价的采样拍 {len(has)}，存兵 ≤ 留底的 {len(blk)}（定值项 {dict(terms)}）；其中同拍有报价过了价格门的 {len(blk_pass)}'
          f'｜被挡时最强真人邻居的存兵÷自己 中位 {med:.1f}｜safeFinite 取到队友存兵的采样拍 {len(mate)}'
          + (f'（t={",".join(str(r["t"]) for r in mate)}）' if mate else ''))
print(f'  合计：有报价 {tot["has"]}，存兵 ≤ 留底 {tot["blk"]}（dpKeep {tot["term:dpKeep"]}、safeFinite {tot["term:safeFinite"]}、封顶 {tot["term:封顶"]}）；其中同拍有报价过了价格门 {tot["blkpass"]}')
if detail:
    for r in by.get(detail, []):
        print(f"    {detail} t={r['t']} 地 {r['L']} 兵 {r['B']}｜safeAt {r['safe']}（{r['term']}）｜最强真人邻居 {r['strong']} {r['strongBal']}"
              f"（{r['strongBal'] / max(1, r['B']):.2f}×自己）｜{'被挡' if r['blocked'] else '有可用兵'}｜过价格门的报价 {r['passed']} 条"
              + (f"｜safeFinite 经 {r['via']} → {r['owner']}" if r['via'] else ''))
