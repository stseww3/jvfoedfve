#!/usr/bin/env python3
"""review_rollup.py — 把已复盘各局的 reviews/<局>.json 机械汇总成跨局表（Markdown）：概况、编队对真人、阵亡、转折点时段、捐兵、模式矩阵、判定计数。

只读 reviews/*.json，不做新的计量；每个数字都能在对应的 <局>.json 里找到原值。
用法：python3 scripts/review_rollup.py [局…] [--out reports/REVIEW-ROLLUP.md] [--min 3]      --min：模式矩阵只列出现在 ≥ N 局的模式键（默认 3）
"""
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
a = sys.argv[1:]
outp = a[a.index('--out') + 1] if '--out' in a else None
minn = int(a[a.index('--min') + 1]) if '--min' in a else 3
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--out', '--min'))]
if not ids:
    ids = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'reviews')) if f.endswith('.json'))
J = {m: json.load(open(os.path.join(ROOT, 'reviews', f'{m}.json'))) for m in ids}
out = []
P = out.append
med = lambda v: statistics.median(v) if v else None
num = lambda v: '–' if v is None else (f'{v:g}' if isinstance(v, float) and v != int(v) else f'{int(v):,}')
k = lambda v: '–' if v is None else (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:,.0f}')
pct = lambda x, y, d=0: f'{100 * x / y:.{d}f}%' if y else '–'


def table(head, rows):
    P('| ' + ' | '.join(head) + ' |')
    P('|' + '|'.join(' --: ' for _ in head) + '|')
    for r in rows:
        P('| ' + ' | '.join(str(x) for x in r) + ' |')
    P('')


P(f'# {len(ids)} 局复盘 JSON 的机械汇总')
P('')
P('> 本文件由 `python3 scripts/review_rollup.py --out reports/REVIEW-ROLLUP.md` 生成，不手改。只读 `reviews/<局>.json`。')
P('')

# ---- 1 概况 ----
P('## 1. 概况')
P('')
rows = []
for m in ids:
    c, o = J[m]['context'], J[m]['outcome']
    rows.append([m, c['strategyVersion'].split('(')[0], c['timeUtc'][5:16].replace('T', ' '), c['map'].split('(')[0], c['humans'], f"{c['actualTeams']}（{'/'.join(str(x) for x in c['teamSizes'])}）",
                 f"{c['baseWinExpectation']:.3f}", len(c['squadBotsInReplay']), len(c.get('squadBotsNotInReplay') or []), o['result'], f"{o['endTick']:,}",
                 f"{o['ourTeamPeakShare']}%@{o['ourTeamPeakT']}", f"{o['squadPeakShare']}%@{o['squadPeakT']}", J[m].get('lossArchetype', '–')])
table(['局', '版本', '时间（UTC）', '地图', '真人', '队数（各队人数）', '按队数的胜率期望', '录像盘里的我方号', '不在录像盘的号', '结局', '终局拍', '我方队峰值份额@拍', '编队峰值份额@拍', '复盘归类'], rows)
won = sum(1 for m in ids if J[m]['outcome']['result'] == 'won')
P(f"赢 {won} 局、输 {len(ids) - won} 局；按队数的胜率期望之和 {sum(J[m]['context']['baseWinExpectation'] for m in ids):.2f} 局。")
P('')

# ---- 2 编队对真人 ----
P('## 2. 编队的号对同局其他真人：地的中位、密度的中位')
P('')
P('每格 = 我方在线号的地中位 ÷ 其他真人的地中位（括号里是 我方密度中位 / 真人密度中位；密度 = 兵 ÷ 地）。来源：各局 JSON 的 squadVsRealHumans。')
P('')
TS = [300, 600, 900, 1200, 1500, 2100, 3000]
rows = []
ratio_at = collections.defaultdict(list)
for m in ids:
    by = {r['t']: r for r in J[m]['squadVsRealHumans']}
    r = [m]
    for t in TS:
        x = by.get(t)
        if not x or not x.get('realTerrMedian') or x.get('squadTerrMedianActive') is None:
            r.append('–')
            continue
        q = x['squadTerrMedianActive'] / x['realTerrMedian']
        ratio_at[t].append(q)
        r.append(f"{q:.2f}（{num(x.get('squadDensMedianActive'))} / {num(x.get('realDensMedian'))}）")
    rows.append(r)
table(['局'] + [f'{t} 拍' for t in TS], rows)
P('各拍的中位（跨局）：' + '；'.join(f"{t} 拍 {med(ratio_at[t]):.2f}（{len(ratio_at[t])} 局，<1 的 {sum(1 for x in ratio_at[t] if x < 1)} 局）" for t in TS if ratio_at[t]) + '。')
P('')

# ---- 3 阵亡 ----
P('## 3. 阵亡与离场')
P('')
rows = []
for m in ids:
    D = J[m].get('deaths') or []
    S = J[m].get('survivors') or []
    died = sorted(d['diedT'] for d in D if d.get('diedT') is not None)
    left = sorted(d['leftT'] for d in D if d.get('leftT') is not None)
    rows.append([m, len(D), len(S), num(died[0]) if died else '–', num(med(died)) if died else '–', num(died[-1]) if died else '–', len(left), num(left[0]) if left else '–',
                 sum(1 for d in D if d.get('diedT') is not None and d['diedT'] < 3000)])
table(['局', '阵亡条目', '活到终局的号', '最早阵亡拍', '阵亡拍中位', '最晚阵亡拍', '其中先离场（有离场拍）的', '最早离场拍', '3000 拍前阵亡'], rows)

# ---- 4 转折点 ----
P('## 4. 转折点落在哪个时段')
P('')
PERS = [(0, 600), (600, 1500), (1500, 3000), (3000, 5000), (5000, 10 ** 9)]
PN = ['0–600', '600–1500', '1500–3000', '3000–5000', '5000+']
cnt = collections.Counter()
rows = []
for m in ids:
    r = [m]
    cell = collections.defaultdict(list)
    for tp in J[m].get('turningPoints') or []:
        t0 = max(0, tp.get('t0') or 0)      # 选点期开始的转折点（负拍）并进 0–600
        i = next(i for i, (lo, hi) in enumerate(PERS) if lo <= t0 < hi)
        cnt[i] += 1
        sb, sa = tp.get('squadShareBefore'), tp.get('squadShareAfter')
        cell[i].append(f"{tp['id']} {tp.get('t0')}–{tp.get('t1')}" + (f"（编队 {sb}→{sa}%）" if sb is not None and sa is not None else ''))
    for i in range(len(PERS)):
        r.append('；'.join(cell[i]) or '–')
    rows.append(r)
table(['局'] + [p + ' 拍开始' for p in PN], rows)
P('转折点个数：' + '、'.join(f"{PN[i]} 拍 {cnt[i]} 个" for i in range(len(PERS))) + f"；{sum(1 for m in ids if any(600 <= (tp.get('t0') or 0) < 1500 for tp in J[m].get('turningPoints') or []))}/{len(ids)} 局有一个从 600–1500 拍开始的转折点。")
P('')

# ---- 5 捐兵 ----
P('## 5. 捐兵：日志里发的、录像里执行的、被配额拒掉的')
P('')
rows = []
tot = collections.Counter()
for m in ids:
    d = J[m].get('dispatchAudit') or {}
    rs = d.get('notExecutedReasons') or {}
    quota = sum(v for kk, v in rs.items() if 'quota' in kk and '全被拒' in kk)
    rows.append([m, num(d.get('logged')), num(d.get('executed')), pct(d.get('executed', 0), d.get('logged', 0)), num(quota), pct(quota, d.get('logged', 0)),
                 k(d.get('arrived')), k(d.get('tax')), num(d.get('execLagMedian')), num(d.get('execLagMax')), num(d.get('toOtherTeammates'))])
    for kk in ('logged', 'executed'):
        tot[kk] += d.get(kk) or 0
    tot['quota'] += quota
table(['局', '日志里发出', '录像里执行', '执行率', '试算全被配额拒', '占发出', '到账兵', '税', '执行延迟中位（拍）', '最大（拍）', '捐给路人队友'], rows)
P(f"合计：日志里发出 {tot['logged']:,} 条，录像里执行 {tot['executed']:,} 条（{pct(tot['executed'], tot['logged'])}），试算全被配额拒 {tot['quota']:,} 条（{pct(tot['quota'], tot['logged'])}）。")
P('')

# ---- 6 模式矩阵 ----
P(f'## 6. 模式矩阵（出现在 ≥{minn} 局的模式键）')
P('')
P('一个模式算「出现在某局」= 该局 JSON 的 decisions[].patternKey 或 newPatterns[].key 里有它。格子里是该局与它挂钩的决策条目的判定：E = error、U = unclear、G = good；· = 只登记了定义。')
P('')
pk = collections.defaultdict(lambda: collections.defaultdict(list))
names = {}
for m in ids:
    for d in J[m].get('decisions') or []:
        key = d.get('patternKey') or d.get('patternId')
        if key and key != 'NEW':
            pk[key][m].append({'error': 'E', 'unclear': 'U', 'good': 'G'}.get(d.get('verdict'), '?'))
    for p in J[m].get('newPatterns') or []:
        names.setdefault(p['key'], p['name'])
        pk[p['key']][m]
keys = sorted((kk for kk in pk if len(pk[kk]) >= minn), key=lambda kk: (-len(pk[kk]), kk))
rows = []
for kk in keys:
    vs = collections.Counter(v for L in pk[kk].values() for v in L)
    rows.append([f'`{kk}`', names.get(kk, ''), len(pk[kk]), vs.get('E', 0), vs.get('U', 0), vs.get('G', 0)] + [(''.join(pk[kk][m]) or '·') if m in pk[kk] else '' for m in ids])
table(['模式键', '名字', '局数', 'E', 'U', 'G'] + ids, rows)
rest = sorted(kk for kk in pk if len(pk[kk]) < minn)
P(f"另有 {len(rest)} 个模式键只出现在 {minn - 1} 局以内：" + '、'.join(f"`{kk}`（{'、'.join(sorted(pk[kk]))}）" for kk in rest) + '。')
P('')

# ---- 7 判定 ----
P('## 7. 决策条目的判定计数')
P('')
rows = []
tot = collections.Counter()
for m in ids:
    c = collections.Counter(d.get('verdict') for d in J[m].get('decisions') or [])
    st = collections.Counter(d.get('statementType') for d in J[m].get('decisions') or [])
    rows.append([m, sum(c.values()), c.get('error', 0), c.get('unclear', 0), c.get('good', 0), '、'.join(f'{kk} {v}' for kk, v in st.most_common())])
    tot.update(c)
table(['局', '决策条目', 'error', 'unclear', 'good', '陈述类型'], rows)
P(f"合计 {sum(tot.values())} 条：error {tot.get('error', 0)}、unclear {tot.get('unclear', 0)}、good {tot.get('good', 0)}。")

txt = '\n'.join(out) + '\n'
if outp:
    open(os.path.join(ROOT, outp) if not os.path.isabs(outp) else outp, 'w', encoding='utf-8').write(txt)
    print('→', outp, txt.count('\n'), '行')
else:
    sys.stdout.write(txt)
