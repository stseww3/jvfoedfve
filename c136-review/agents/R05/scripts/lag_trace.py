#!/usr/bin/env python3
"""lag_trace.py — 延迟波的形状：给模拟器的「指令通道」定参数用。

输入：/tmp/c136-r05/work/<局>-delay.json（delay_account.py 的决策级延迟账；decisions[] 每条 = [号, 决策拍, 类型, 目标类别, 状态, 落地拍, 延迟, …]）。
      决策拍 = 客户端本地拍（锁步：客户端本地第 t 拍看到的就是录像第 t 拍的局面）；落地拍 = 录像里执行的拍；延迟 = 落地拍 − 决策拍。
只看陆攻和出船（捐兵没落地多半是配额挡的，不是通道丢的）。13 局已复盘的对局；延迟波局 = 600–1500 拍落地指令延迟中位 ≥60 拍的 8 局。

出四张表：
  1) 每 300 拍（按落地拍分箱）的延迟中位，和由相邻两箱推出来的「客户端速度」：
         速度 = 1 − (后一箱延迟中位 − 前一箱延迟中位) ÷ 300        （客户端每过 1 个服务器拍，本地走了几拍；<1 = 越落越远，>1 = 在追）
  2) 同一局同一箱里各号的延迟中位：延迟是一局所有号一起慢，还是个别号慢。
         只算箱内 ≥3 条落地的号；「延迟箱」= 全队延迟中位 ≥35 拍的箱。
  3) 一个回合里落地的一批指令在本地跨了多少拍、延迟多少（批 = 同号同拍落地 ≥3 条）。
  4) 丢弃规则的旁证：满 9 条的批，前后两侧各有多少条没落地的决策。
         前 = 这一批第一条决策 之前、上一条落地决策之后 的没落地决策数；后 = 这一批最后一条决策 之后、下一条落地决策之前 的。
         稳态下「前」就是上一批的「后」，分不开；只有「孤立批」分得开：上一条落地决策延迟 <35 拍（波还没起）或下一条落地决策延迟 <35 拍（波已退）。
         「先到先收、多的丢掉」预言：波头的孤立批 前 = 0；波尾的孤立批 后 > 0。「只留最新的」预言反过来。
         注意：批是按「连续 9 条决策的 (类型, pct) 序列」配出来的，同样的序列在决策流里出现多处时取最晚的一处（延迟取下界），
         所以这张表偏向「前」多「后」少；只能当旁证。
用法：python3 scripts/lag_trace.py [--out reports/LAG-TRACE.md] [--json out/lag-trace.json]
"""
import glob
import json
import os
import statistics as st
import sys
from collections import defaultdict

W = os.environ.get('C136_WORK', '/tmp/c136-r05/work')
MATCHES = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']
a = sys.argv[1:]
val = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
out, jout = val('--out'), val('--json')
med = lambda v: (st.median(v) if v else None)
f0 = lambda v: '–' if v is None else f'{v:.0f}'
f2 = lambda v: '–' if v is None else f'{v:.2f}'


def q(v, p):
    if not v:
        return None
    s = sorted(v)
    import math
    return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))]


DATA = {}
for m in MATCHES:
    p = f'{W}/{m}-delay.json'
    if os.path.exists(p):
        DATA[m] = json.load(open(p))
WAVE = []
for m, D in DATA.items():
    r = [x for x in D['delayByPeriod'] if x['period'].startswith('600')]
    if r and r[0].get('p50') is not None and r[0]['p50'] >= 60:
        WAVE.append(m)

L = []
w = L.append
J = {'wave': WAVE}
w('# LAG-TRACE — 延迟波的形状（给模拟器的指令通道定参数用）')
w('')
w('> 本文件由 `python3 scripts/lag_trace.py --out reports/LAG-TRACE.md --json out/lag-trace.json` 生成，不手改。')
w('> 输入是 13 局的决策级延迟账（`delay_account.py`）。决策拍 = 客户端本地拍，落地拍 = 录像里执行的拍，延迟 = 落地拍 − 决策拍。只看陆攻和出船。')
w(f'> 延迟波局（600–1500 拍落地指令延迟中位 ≥60 拍）：{"、".join(WAVE)}（{len(WAVE)} 局）；其余 {len(DATA) - len(WAVE)} 局。')
w('')

# ---------- 1) 每 300 拍延迟中位 + 客户端速度 ----------
BINS = list(range(0, 4200, 300))
w('## 1. 每 300 拍的延迟中位，和推出来的客户端速度')
w('')
w('按落地拍分箱；每格 = 延迟中位（拍）/ 落地条数。箱内不到 5 条的记「–」。')
w('')
w('| 局 | ' + ' | '.join(str(b) for b in BINS) + ' |')
w('| --: | ' + ' | '.join('--:' for _ in BINS) + ' |')
P50 = {}
for m in MATCHES:
    if m not in DATA:
        continue
    by = defaultdict(list)
    for r in DATA[m]['decisions']:
        if r[2] in ('attack', 'boat') and r[5] is not None:
            by[(r[5] // 300) * 300].append(r[6])
    P50[m] = {b: (med(by[b]) if len(by[b]) >= 5 else None) for b in BINS}
    w(f'| {m}{"＊" if m in WAVE else ""} | ' + ' | '.join((f'{f0(P50[m][b])} / {len(by[b])}' if P50[m][b] is not None else '–') for b in BINS) + ' |')
w('')
w('＊ = 延迟波局。')
w('')
w('客户端速度 = 1 −（后一箱延迟中位 − 前一箱延迟中位）÷ 300；相邻两箱都有数才算。<1 = 客户端越落越远，>1 = 在追。')
w('')
w('| 局 | ' + ' | '.join(f'{b}→{b + 300}' for b in BINS[:-1]) + ' |')
w('| --: | ' + ' | '.join('--:' for _ in BINS[:-1]) + ' |')
speeds = defaultdict(list)
allsp = []
peak = {}
for m in WAVE:
    row = []
    for b in BINS[:-1]:
        x, y = P50[m][b], P50[m][b + 300]
        if x is None or y is None:
            row.append('–')
            continue
        s = 1 - (y - x) / 300
        row.append(f2(s))
        speeds[b].append(s)
        allsp.append((m, b, s, x, y))
    vals = [(v, b) for b, v in P50[m].items() if v is not None]
    peak[m] = max(vals) if vals else (None, None)
    w(f'| {m} | ' + ' | '.join(row) + ' |')
w('')
slow = [s for _, _, s, x, y in allsp if y - x >= 30]
fast = [s for _, _, s, x, y in allsp if x - y >= 30]
flat = [s for _, _, s, x, y in allsp if abs(y - x) < 30]
w(f'- 8 个延迟波局合计 {len(allsp)} 个相邻箱对：延迟在涨（后箱比前箱多 ≥30 拍）的 {len(slow)} 对，客户端速度中位 {f2(med(slow))}（最慢 {f2(min(slow) if slow else None)}）；'
  f'延迟在退（少 ≥30 拍）的 {len(fast)} 对，速度中位 {f2(med(fast))}（最快 {f2(max(fast) if fast else None)}）；变化不到 30 拍的 {len(flat)} 对。')
w('- 各局延迟中位最高的一箱：' + '；'.join(f'{m} {f0(peak[m][0])} 拍（{peak[m][1]} 箱）' for m in WAVE) + '。')
on, off = [], []
for m in WAVE:
    bs = [b for b in BINS if P50[m][b] is not None and P50[m][b] >= 35]
    if bs:
        on.append((m, bs[0]))
        later = [b for b in BINS if b > bs[-1] and P50[m][b] is not None]
        off.append((m, later[0] if later else None))
w('- 延迟中位第一次 ≥35 拍的箱：' + '；'.join(f'{m} {b}' for m, b in on) + '。')
w('- 之后第一个延迟中位回到 <35 拍的箱：' + '；'.join(f'{m} {b if b is not None else "到录像结束都没回来（或之后没有落地指令）"}' for m, b in off) + '。')
w('')
J['p50by300'] = {m: {str(b): v for b, v in P50[m].items()} for m in P50}

# ---------- 2) 各号同步不同步 ----------
w('## 2. 延迟是全队一起慢，还是个别号慢')
w('')
w('按（局 × 300 拍箱）看各号自己的延迟中位（箱内 ≥3 条落地的号才算；≥2 个号有数的箱才算）。延迟箱 = 这些号的延迟中位的中位 ≥35 拍。')
w('')
w('| 局 | 可判的箱 | 延迟箱 | 延迟箱里：各号延迟中位 ≥35 拍的号占比（中位） | 全部号都 ≥35 拍的箱 | 延迟箱里：最慢号 ÷ 最快号（中位） | 最慢号 − 最快号（拍，中位） |')
w('| --: | --: | --: | --: | --: | --: | --: |')
tot = [0, 0, 0]
allshare, allratio, alldiff = [], [], []
for m in MATCHES:
    if m not in DATA:
        continue
    cell = defaultdict(lambda: defaultdict(list))
    for r in DATA[m]['decisions']:
        if r[2] in ('attack', 'boat') and r[5] is not None:
            cell[(r[5] // 300) * 300][r[0]].append(r[6])
    n = lagn = full = 0
    share, ratio, diff = [], [], []
    for b, bots in cell.items():
        ps = [med(v) for v in bots.values() if len(v) >= 3]
        if len(ps) < 2:
            continue
        n += 1
        if med(ps) < 35:
            continue
        lagn += 1
        sh = sum(1 for x in ps if x >= 35) / len(ps)
        share.append(sh)
        full += sh == 1
        ratio.append(max(ps) / max(1, min(ps)))
        diff.append(max(ps) - min(ps))
    tot[0] += n
    tot[1] += lagn
    tot[2] += full
    allshare += share
    allratio += ratio
    alldiff += diff
    w(f'| {m}{"＊" if m in WAVE else ""} | {n} | {lagn} | {f"{100 * med(share):.0f}%" if share else "–"} | {full if lagn else "–"} | {f2(med(ratio))} | {f0(med(diff))} |')
w(f'| 合计 | {tot[0]} | {tot[1]} | {f"{100 * med(allshare):.0f}%" if allshare else "–"} | {tot[2]} | {f2(med(allratio))} | {f0(med(alldiff))} |')
w('')
J['sync'] = {'cells': tot[0], 'lagCells': tot[1], 'allBotsLag': tot[2]}

# ---------- 3) 批的形状 ----------
w('## 3. 一个回合里落地的一批指令')
w('')
w('批 = 同一个号同一拍落地 ≥3 条陆攻/出船。本地跨度 = 批内最晚决策拍 − 最早决策拍；延迟 = 落地拍 − 批内最晚决策拍（批里最新的那条等了多久）。')
w('')
w('| 局 | 批数 | 其中满 9 条 | 本地跨度：中位 / P90（拍） | 最新一条的延迟：中位 / P90（拍） | 最老一条的延迟：中位（拍） |')
w('| --: | --: | --: | --: | --: | --: |')
GROUPS = {}
for m in MATCHES:
    if m not in DATA:
        continue
    by = defaultdict(list)
    for r in DATA[m]['decisions']:
        if r[2] in ('attack', 'boat'):
            by[r[0]].append(r)
    G = []
    for bot, rs in by.items():
        rs.sort(key=lambda r: r[1])
        land = defaultdict(list)
        for i, r in enumerate(rs):
            if r[5] is not None:
                land[r[5]].append(i)
        for T, idx in land.items():
            G.append((bot, T, idx, rs))
    GROUPS[m] = G
    bs = [g for g in G if len(g[2]) >= 3]
    if not bs:
        w(f'| {m}{"＊" if m in WAVE else ""} | 0 | 0 | – | – | – |')
        continue
    span = [g[3][max(g[2])][1] - g[3][min(g[2])][1] for g in bs]
    newest = [g[1] - max(g[3][i][1] for i in g[2]) for g in bs]
    oldest = [g[1] - min(g[3][i][1] for i in g[2]) for g in bs]
    w(f'| {m}{"＊" if m in WAVE else ""} | {len(bs)} | {sum(1 for g in bs if len(g[2]) >= 9)} | {f0(med(span))} / {f0(q(span, 0.9))} | {f0(med(newest))} / {f0(q(newest, 0.9))} | {f0(med(oldest))} |')
w('')

# ---------- 4) 丢弃规则 ----------
w('## 4. 满 9 条的批，前后各有多少条没落地的决策')
w('')
w('前 = 这一批第一条决策之前、上一条落地决策之后的没落地决策数；后 = 这一批最后一条决策之后、下一条落地决策之前的。')
w('波头的孤立批 = 上一条落地决策的延迟 <35 拍；波尾的孤立批 = 下一条落地决策的延迟 <35 拍。')
w('')
rows = {'all': [], 'head': [], 'tail': []}
for m, G in GROUPS.items():
    for bot, T, idx, rs in G:
        if len(idx) < 9:
            continue
        i0, i1 = min(idx), max(idx)
        if i1 - i0 + 1 != len(idx):
            inter = sum(1 for i in range(i0, i1 + 1) if rs[i][5] is None)
        else:
            inter = 0
        pb = i0 - 1
        before = 0
        while pb >= 0 and rs[pb][5] is None:
            before += 1
            pb -= 1
        na = i1 + 1
        after = 0
        while na < len(rs) and rs[na][5] is None:
            after += 1
            na += 1
        prevd = rs[pb][6] if pb >= 0 else None
        nextd = rs[na][6] if na < len(rs) else None
        rec = (m, bot, T, before, after, inter, prevd, nextd)
        rows['all'].append(rec)
        if prevd is not None and prevd < 35:
            rows['head'].append(rec)
        if nextd is not None and nextd < 35:
            rows['tail'].append(rec)
w('| 哪些批 | 批数 | 前 = 0 的批 | 前：合计 / 中位 | 后 = 0 的批 | 后：合计 / 中位 |')
w('| --: | --: | --: | --: | --: | --: |')
for key, name in (('all', '全部满 9 条的批'), ('head', '波头的孤立批（上一条落地决策延迟 <35 拍）'), ('tail', '波尾的孤立批（下一条落地决策延迟 <35 拍）')):
    R = rows[key]
    if not R:
        w(f'| {name} | 0 | – | – | – | – |')
        continue
    bf = [r[3] for r in R]
    af = [r[4] for r in R]
    w(f'| {name} | {len(R)} | {sum(1 for x in bf if x == 0)} | {sum(bf)} / {f0(med(bf))} | {sum(1 for x in af if x == 0)} | {sum(af)} / {f0(med(af))} |')
w('')
both = [r for r in rows['head'] if r in rows['tail']]
if both:
    w(f'- 两侧都是低延迟落地决策的满批（波头也是波尾）：{len(both)} 个；前 = 0 的 {sum(1 for r in both if r[3] == 0)} 个、后 = 0 的 {sum(1 for r in both if r[4] == 0)} 个；'
      f'前合计 {sum(r[3] for r in both)} 条、后合计 {sum(r[4] for r in both)} 条。')
w('')
w('读法：两种简单规则都对不上——波头的孤立批前面多数有没落地的决策，波尾的孤立批后面多数也有。'
  '配对在序列重复时取最晚一处，会把「后」算少、「前」算多；录像本身分不出是哪一种。模拟器里这条规则要做成开关，两种都跑。')
w('')
J['dropRule'] = {k: [list(r) for r in v] for k, v in rows.items()}

text = '\n'.join(L) + '\n'
if out:
    open(out, 'w', encoding='utf-8').write(text)
    print('→', out)
else:
    sys.stdout.write(text)
if jout:
    json.dump(J, open(jout, 'w', encoding='utf-8'), ensure_ascii=False)
    print('→', jout)
