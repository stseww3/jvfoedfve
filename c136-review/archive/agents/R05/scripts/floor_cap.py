#!/usr/bin/env python3
"""floor_cap.py — 机器人留底（safeFinite）是被多大的机器人定出来的。

输入：/tmp/c136-r05/work/<局>-floor.txt（`shadow.mjs --floor t1,t2,…` 不带 --quiet 的输出；每个 号×采样拍 一行 `[留底] …`）。
      影子 = 在逐拍重演的真实局面上跑真实策略代码；这些行是策略自己的 safeFinite / threatOf 在那一拍算出来的值。
      采样拍是手工指定的（600–1800 拍之间每 100 拍或每 25 拍），不是全程每拍；有文件的局才算。
口径：
  有机器人邻居 = 这个号当拍至少贴着 1 个机器人。锁死 = 有机器人邻居、但没有一个机器人目标过得了留底。
  定留底的机器人 = 行里「由 机器人#x（地 a 兵 b）决定」的那个：safeFinite 取的是它的「其它邻居里最弱的」那个玩家的存兵。
  最弱邻居的类别：我方号 / 同队的其他真人（路人队友）/ 机器人 / 敌方真人。
  机器人兵比 = 定留底的那个机器人的存兵 ÷ 这个号的存兵。留底占比 = safeFinite ÷ 这个号的存兵。
用法：python3 scripts/floor_cap.py [--out reports/BOT-FLOOR.md]
"""
import glob
import os
import re
import statistics as st
import sys
from collections import Counter

W = os.environ.get('C136_WORK', '/tmp/c136-r05/work')
a = sys.argv[1:]
out = a[a.index('--out') + 1] if '--out' in a else None
rx = re.compile(r'^\[留底\] t=(\d+) (\S+) 兵 (\d+) 地 (\d+)｜相邻机器人 (\d+) 个（共 (\d+) 格，其中几乎没兵的 (\d+) 个）｜safeFinite=(\d+)（([^）]*)）(.*?)｜此刻过得了留底的机器人目标 (\d+) 个')
rw = re.compile(r'由 机器人#(\d+)（地 (\d+) 兵 (\d+)）决定：它的其它邻居里最弱的是 (.+?) 兵 (\d+)')
med = lambda v: (st.median(v) if v else None)


def q(v, p):
    import math
    s = sorted(v)
    return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))] if s else None


def kind(name):
    if '(我方号)' in name:
        return '我方号'
    if '(路人队友)' in name or '(队友)' in name:
        return '同队的其他真人'
    if name.startswith('机器人#') or '(机器人)' in name:
        return '机器人'
    return '敌方真人'


ROWS = {}
for f in sorted(glob.glob(f'{W}/*-floor.txt')):
    m = os.path.basename(f)[:4]
    rows = []
    for line in open(f, encoding='utf-8', errors='replace'):
        x = rx.match(line.strip())
        if not x:
            continue
        t, bot, B, L, nb, cells, empty, sf, _, rest, ok = x.groups()
        w = rw.search(rest)
        rows.append(dict(t=int(t), bot=bot, B=int(B), L=int(L), nb=int(nb), cells=int(cells), sf=int(sf), ok=int(ok),
                         botBal=(int(w.group(3)) if w else None), botLand=(int(w.group(2)) if w else None),
                         who=(kind(w.group(4)) if w else None), whoBal=(int(w.group(5)) if w else None)))
    if rows:
        ROWS[m] = rows

L = []
w = L.append
pc = lambda x, y: f'{100 * x / y:.0f}%' if y else '–'
w('# BOT-FLOOR — 机器人留底（safeFinite）是被多大的机器人定出来的')
w('')
w('> 本文件由 `python3 scripts/floor_cap.py --out reports/BOT-FLOOR.md` 生成，不手改。')
w('> 输入是影子策略在指定采样拍打印的留底行（`shadow.mjs --floor`）：策略自己的 `safeFinite` / `threatOf` 当拍算出的值。采样拍在 500–1805 拍之间，手工指定，不是全程。')
w(f'> 有数据的局：{"、".join(ROWS)}（{len(ROWS)} 局）。')
w('')
w('名词：锁死 = 这个号贴着机器人，但没有一个机器人目标过得了留底。定留底的机器人 = `safeFinite` 取到最大值的那个机器人邻居；留底 = 它的其它邻居里最弱的那个玩家的存兵。')
w('')
w('## 1. 逐局')
w('')
w('| 局 | 采样（号×拍） | 贴着机器人 | 其中锁死 | 锁死里由机器人留底定的 | 定留底的机器人的存兵 ÷ 这个号的存兵：中位 | 留底 ÷ 这个号的存兵：中位 | 最弱邻居是：我方号 | 同队的其他真人 | 敌方真人 | 机器人 |')
w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
ALL = []
for m, rows in ROWS.items():
    have = [r for r in rows if r['nb'] > 0]
    lock = [r for r in have if r['ok'] == 0]
    by = [r for r in lock if r['who'] and r['sf'] > 0 and r['B'] > 0]
    ALL += [(m, r) for r in by]
    c = Counter(r['who'] for r in by)
    ratio = [r['botBal'] / r['B'] for r in by]
    share = [r['sf'] / r['B'] for r in by]
    w(f'| {m} | {len(rows)} | {len(have)} | {len(lock)}（{pc(len(lock), len(have))}） | {len(by)} | {f"{100 * med(ratio):.1f}%" if ratio else "–"} | '
      f'{f"{100 * med(share):.0f}%" if share else "–"} | {c["我方号"]} | {c["同队的其他真人"]} | {c["敌方真人"]} | {c["机器人"]} |')
by = [r for _, r in ALL]
c = Counter(r['who'] for r in by)
ratio = [r['botBal'] / r['B'] for r in by]
share = [r['sf'] / r['B'] for r in by]
tot_rows = sum(len(v) for v in ROWS.values())
tot_have = sum(1 for v in ROWS.values() for r in v if r['nb'] > 0)
tot_lock = sum(1 for v in ROWS.values() for r in v if r['nb'] > 0 and r['ok'] == 0)
w(f'| 合计 | {tot_rows} | {tot_have} | {tot_lock}（{pc(tot_lock, tot_have)}） | {len(by)} | {100 * med(ratio):.1f}% | {100 * med(share):.0f}% | '
  f'{c["我方号"]} | {c["同队的其他真人"]} | {c["敌方真人"]} | {c["机器人"]} |')
w('')
w('## 2. 锁死的样本里，定留底的那个机器人有多少兵')
w('')
w(f'锁死且由机器人留底定的样本 {len(by)} 个。')
w('')
w('| 定留底的机器人的存兵 ÷ 这个号的存兵 | 样本 | 占比 | 这些样本的留底 ÷ 存兵（中位） |')
w('| --: | --: | --: | --: |')
for lo, hi, name in [(0, 0.02, '<2%'), (0.02, 0.05, '2–5%'), (0.05, 0.10, '5–10%'), (0.10, 0.25, '10–25%'), (0.25, 0.5, '25–50%'), (0.5, 1e9, '≥50%')]:
    sub = [r for r in by if lo <= r['botBal'] / r['B'] < hi]
    w(f'| {name} | {len(sub)} | {pc(len(sub), len(by))} | {f"{100 * med([r["sf"] / r["B"] for r in sub]):.0f}%" if sub else "–"} |')
w('')
lt10 = sum(1 for x in ratio if x < 0.10)
lt25 = sum(1 for x in ratio if x < 0.25)
w(f'- 定留底的机器人的存兵不到这个号存兵 10% 的：{lt10}/{len(by)}（{pc(lt10, len(by))}）；不到 25% 的：{lt25}/{len(by)}（{pc(lt25, len(by))}）。')
w(f'- 定留底的机器人：存兵中位 {med([r["botBal"] for r in by]):,.0f}（四分位 {q([r["botBal"] for r in by], 0.25):,}–{q([r["botBal"] for r in by], 0.75):,}），'
  f'地中位 {med([r["botLand"] for r in by]):,.0f} 格；同一样本里这个号的存兵中位 {med([r["B"] for r in by]):,.0f}。')
w(f'- 留底 ≥ 这个号全部存兵的：{sum(1 for r in by if r["sf"] >= r["B"])}/{len(by)}（{pc(sum(1 for r in by if r["sf"] >= r["B"]), len(by))}）。')
dens = [r['botBal'] / r['botLand'] for r in by if r['botLand']]
w(f'- 定留底的机器人的密度（存兵 ÷ 地）：中位 {med(dens):.2f}（四分位 {q(dens, 0.25):.2f}–{q(dens, 0.75):.2f}）。')
tot = [r['cells'] / r['B'] for r in by]
w(f'- 这个号贴着的全部机器人的地（格）÷ 这个号的存兵：中位 {med(tot):.2f}（四分位 {q(tot, 0.25):.2f}–{q(tot, 0.75):.2f}）；<0.5 的 {sum(1 for x in tot if x < 0.5)}/{len(tot)}（{pc(sum(1 for x in tot if x < 0.5), len(tot))}）。'
  '机器人密度在 1 上下时，这个比值近似「贴着的机器人全部存兵 ÷ 这个号的存兵」。')
early = [r for r in by if r['t'] < 900]
late = [r for r in by if r['t'] >= 900]
for nm, sub_ in (('900 拍以前', early), ('900 拍以后', late)):
    if sub_:
        tt = [r['cells'] / r['B'] for r in sub_]
        w(f'- {nm}的 {len(sub_)} 个样本：贴着的机器人的地 ÷ 这个号的存兵 中位 {med(tt):.2f}；定留底的机器人存兵 ÷ 这个号存兵 中位 {100 * med([r["botBal"] / r["B"] for r in sub_]):.1f}%。')
w('')
w('## 3. 按最弱邻居是谁')
w('')
w('| 最弱邻居 | 锁死样本 | 占比 | 机器人存兵 ÷ 这个号存兵（中位） | 留底 ÷ 存兵（中位） | 留底 ≥ 全部存兵 |')
w('| --: | --: | --: | --: | --: | --: |')
for k in ('我方号', '同队的其他真人', '敌方真人', '机器人'):
    sub = [r for r in by if r['who'] == k]
    if not sub:
        w(f'| {k} | 0 | 0% | – | – | – |')
        continue
    w(f'| {k} | {len(sub)} | {pc(len(sub), len(by))} | {100 * med([r["botBal"] / r["B"] for r in sub]):.1f}% | {100 * med([r["sf"] / r["B"] for r in sub]):.0f}% | '
      f'{sum(1 for r in sub if r["sf"] >= r["B"])}（{pc(sum(1 for r in sub if r["sf"] >= r["B"]), len(sub))}） |')
w('')
w('读法：`threatOf` 把「机器人会打它最弱的邻居」换算成「我的存兵不能低于它别的邻居里最弱的那个」。'
  '表里量的是这条规则锁住的时候，那个机器人自己手里有多少兵——它一次最多打出自己存兵的一部分（引擎 `botAttack`：`botPct × 存兵 ÷ 1000`）。'
  '采样拍是手工指定的，局与局的采样密度不同，合计行偏向采样多的局（A030、A034）。')
w('')
text = '\n'.join(L) + '\n'
if out:
    open(out, 'w', encoding='utf-8').write(text)
    print('→', out)
else:
    sys.stdout.write(text)
