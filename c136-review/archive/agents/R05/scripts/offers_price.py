#!/usr/bin/env python3
"""offers_price.py — 把 shadow.mjs --offers 的输出压成一张「价格门」表：每个（号×采样拍）一行。

列：地/兵/密度、其他真人密度中位、m（L5350）、worth（L5352）、over（L5353）、报价条数、
    最便宜一条报价的目标、每格价 c、c÷worth、吃掉需÷存兵、结局（价格门收口 / 过门后可用兵 / L5447 跳过 / 没有报价）、
    safeAt(-1) 与定值项、存兵是否 ≤ 留底。
末尾汇总：每个采样拍 有报价的号里 被 L5359 收口的个数、c÷worth 的中位；每个号在所有采样拍里被收口的次数。
--contact：对「最便宜一条被 L5359 收口、接触 <25 格、不带 将垮/正打我 标记」的行，按 Policy.offers L5177-5180 复算接触面罚价：
    steps = 0.75×目标的地÷接触格数；steps > contactStepsMax 时 c 乘以 1 + contactPenalty×min(400, steps − contactStepsMax)
    （Vb 实际参数 contactStepsMax=350、contactPenalty=0.002，见 out/params-raw-vb.json；可用 --steps-max / --penalty 改），
    打印罚价倍数、去掉罚价后的每格价与它÷worth，并统计去掉罚价后能过价格门的（号×拍）数。
用法：python3 scripts/offers_price.py <offers 输出文件>... [--bots a,b] [--brief] [--contact]
"""
import re
import sys
import statistics as st
from collections import defaultdict

a = sys.argv[1:]
bots = set(a[a.index('--bots') + 1].split(',')) if '--bots' in a else None
brief = '--brief' in a
contact = '--contact' in a
STEPS_MAX = float(a[a.index('--steps-max') + 1]) if '--steps-max' in a else 350.0
PENALTY = float(a[a.index('--penalty') + 1]) if '--penalty' in a else 0.002
files = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--bots', '--steps-max', '--penalty'))]

rows = []
cur = None
for fn in files:
    for line in open(fn, encoding='utf-8'):
        m = re.match(r'-- 报价 (\S+) t=(\d+) 地 (\d+) 兵 (\d+) 密度 ([\d.]+)｜其他真人密度中位 ([\d.]+|无|null) m=([\d.]+) refDens=([\d.]+) worth=([\d.]+) cheap=([\d.]+) over=(\w+)｜真人邻居 (\d+) 个，报价 (\d+) 条', line)
        if m:
            cur = dict(bot=m.group(1), t=int(m.group(2)), L=int(m.group(3)), B=int(m.group(4)), d=float(m.group(5)),
                       dOther=m.group(6), m=float(m.group(7)), worth=float(m.group(9)), over=m.group(11) == 'true',
                       nb=int(m.group(12)), n=int(m.group(13)), offers=[], safe=None, term=None, blocked=False)
            rows.append(cur)
            continue
        if cur is None:
            continue
        if '[safeAt 拆解]' in line:
            m2 = re.search(r'safeAt\(-1\)=(\d+)', line)
            cur['safe'] = int(m2.group(1)) if m2 else None
            m3 = re.search(r'定值的是 (\S+?)｜', line)
            cur['term'] = m3.group(1) if m3 else None
            cur['blocked'] = '≤ 留底' in line
            continue
        m = re.match(r'\s+(.+?)#(\d+) 地 (\d+) 兵 (\d+) 密度 ([\d.]+) 接触 (\d+)｜每格价 c=([\d.]+)（([\d.]+)×worth）吃掉需 (\d+)（([\d.]+)×存兵）.*?｜([^｜]*)｜(.*)$', line)
        if m:
            tail = m.group(12)
            av = re.search(r'可用 (-?\d+)', tail)
            cur['offers'].append(dict(q=m.group(1), qid=int(m.group(2)), qL=int(m.group(3)), qB=int(m.group(4)), qd=float(m.group(5)), contact=int(m.group(6)),
                                      c=float(m.group(7)), cw=float(m.group(8)), need=int(m.group(9)), needB=float(m.group(10)), tags=m.group(11),
                                      gate='L5359' in tail and '收口' in tail and '已收口' not in tail, skipped='已收口' in tail,
                                      passed='过价格门' in tail, avail=int(av.group(1)) if av else None, l5447='L5447' in tail, tail=tail.strip()))

if bots:
    rows = [r for r in rows if r['bot'] in bots]
k = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'
by_t = defaultdict(list)
by_bot = defaultdict(list)
for r in rows:
    by_t[r['t']].append(r)
    by_bot[r['bot']].append(r)
    o = r['offers'][0] if r['offers'] else None
    if o is None:
        res = '没有报价（没有可打的邻居）'
    elif o['gate']:
        res = f'L5359 收口：最便宜的 {o["q"]}#{o["qid"]}（密 {o["qd"]:.0f}，接触 {o["contact"]}）每格价 {o["c"]:.1f} = {o["cw"]:.2f}×worth，吃掉需 {o["needB"]:.2f}×存兵'
    elif o['passed']:
        res = f'过门：{o["q"]}#{o["qid"]}（密 {o["qd"]:.0f}）每格价 {o["c"]:.1f} = {o["cw"]:.2f}×worth，可用 {k(o["avail"]) if o["avail"] is not None else "?"}' + ('（L5447 跳过）' if o['l5447'] else '')
    else:
        res = f'{o["q"]}#{o["qid"]} c={o["c"]:.1f}（{o["cw"]:.2f}×worth）{o["tail"][:60]}'
    r['res'] = res
    if not brief:
        print(f't={r["t"]} {r["bot"]}: {r["L"]} 格/{k(r["B"])}/密 {r["d"]:.0f}｜他人密度中位 {r["dOther"]} m={r["m"]:.2f} worth={r["worth"]:.1f} over={"是" if r["over"] else "否"}｜报价 {r["n"]} 条｜{res}'
              f'｜safeAt(-1)={k(r["safe"]) if r["safe"] is not None else "?"}（{r["term"]}定）{"，存兵 ≤ 留底" if r["blocked"] else ""}')

print('== 每个采样拍 ==')
for t in sorted(by_t):
    R = by_t[t]
    has = [r for r in R if r['offers']]
    gate = [r for r in has if r['offers'][0]['gate']]
    passed = [r for r in has if r['offers'][0]['passed']]
    pos = [r for r in passed if (r['offers'][0]['avail'] or 0) > 0]
    cw = [r['offers'][0]['cw'] for r in has]
    over = [r['bot'] for r in R if r['over']]
    blocked = [r for r in R if r['blocked']]
    bal = sum(r['B'] for r in R)
    gbal = sum(r['B'] for r in gate)
    print(f'   t={t}: {len(R)} 个号 存兵 {k(bal)}｜有报价 {len(has)} 个；最便宜一条被 L5359 收口 {len(gate)} 个（握兵 {k(gbal)}＝{100*gbal/max(1,bal):.0f}%），过门 {len(passed)} 个（其中可用兵 >0 的 {len(pos)} 个）｜'
          f'最便宜一条的 c÷worth 中位 {st.median(cw):.2f}（{min(cw):.2f}–{max(cw):.2f}）｜m={R[0]["m"]:.2f}｜over 的号 {" ".join(over) or "无"}｜存兵 ≤ safeAt 留底 {len(blocked)} 个' if has else f'   t={t}: 无报价')
print('== 每个号（所有采样拍）==')
for b, R in by_bot.items():
    has = [r for r in R if r['offers']]
    gate = [r for r in has if r['offers'][0]['gate']]
    print(f'   {b}: 采样 {len(R)} 拍，有报价 {len(has)} 拍，被 L5359 收口 {len(gate)} 拍｜密度 {min(r["d"] for r in R):.0f}–{max(r["d"] for r in R):.0f}｜over {sum(1 for r in R if r["over"])} 拍｜存兵 ≤ 留底 {sum(1 for r in R if r["blocked"])} 拍')

if contact:
    print(f'== 接触面罚价（L5177-5180；contactStepsMax={STEPS_MAX:.0f}，contactPenalty={PENALTY}）：最便宜一条被 L5359 收口、接触 <25 格、无 将垮/正打我 标记的行 ==')
    n_gate = n_pen = n_flip = 0
    for r in rows:
        o = r['offers'][0] if r['offers'] else None
        if o is None or not o['gate']:
            continue
        n_gate += 1
        if o['contact'] >= 25 or o['contact'] <= 0 or '将垮' in o['tags'] or '正打我' in o['tags']:
            continue
        steps = 0.75 * o['qL'] / o['contact']
        if steps <= STEPS_MAX:
            continue
        fac = 1 + PENALTY * min(400, steps - STEPS_MAX)
        c0 = o['c'] / fac
        n_pen += 1
        flip = c0 < r['worth']
        n_flip += flip
        print(f'   t={r["t"]} {r["bot"]}（密 {r["d"]:.0f}，存兵 {k(r["B"])}）→ {o["q"]}#{o["qid"]}（{o["qL"]} 格/{k(o["qB"])}，接触 {o["contact"]} 格）：steps={steps:.0f}，罚价 ×{fac:.2f}；每格价 {o["c"]:.1f}（{o["cw"]:.2f}×worth）→ 不罚 {c0:.1f}（{c0/r["worth"]:.2f}×worth）' + ('｜不罚就过价格门' if flip else ''))
    print(f'   被 L5359 收口的（号×拍）{n_gate} 行，其中带接触面罚价的 {n_pen} 行，去掉罚价后能过价格门的 {n_flip} 行')

