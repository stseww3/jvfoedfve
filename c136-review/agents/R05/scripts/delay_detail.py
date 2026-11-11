#!/usr/bin/env python3
"""delay_detail.py — 延迟硬账的明细视图：把 delay_account.py 的逐条决策表按「号 × 300 拍窗口」摊开，
回答三个问题：慢的那几波是哪些号、在哪些拍；没落地的指令集中在哪里（是不是这个号快死了 / 已经掉线）；
迟到 ≥ N 拍的指令打的是什么目标、结果如何。

输入：/tmp/c136-r05/work/<局>-delay.json（delay_account.py <局> --json 生成）；
      /tmp/c136-r05/truth/<局>.json（match_truth.mjs；取阵亡拍、离开拍）。
口径：延迟 = 录像执行拍 − 影子决策拍；决策按「决策拍」归窗口；class：N 中立、B 机器人、H 敌方真人、S 船、D 捐兵（捐兵没落地 = 引擎没执行，多数是被配额拒）；
      status：hit 按原意、dead 目标已死（改打中立）、void 作废、lost 录像里没有这条。

用法：python3 scripts/delay_detail.py <局> [--late 90] [--win 300] [--from 0] [--to 99999]
"""
import json, sys, collections, statistics

a = sys.argv[1:]
mid = a[0]


def val(k, d):
    return a[a.index(k) + 1] if k in a else d


LATE = int(val('--late', 90)); WIN = int(val('--win', 300)); T0 = int(val('--from', 0)); T1 = int(val('--to', 10**9))
D = json.load(open(f'/tmp/c136-r05/work/{mid}-delay.json'))
T = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
died = {}
left = {}
names = {}
for s in T['squad']:
    names[s['p']] = s['bot']
for e in T['events']:
    if e['type'] == 'died' and e['p'] in names:
        died[names[e['p']]] = e['t']
    if e['type'] == 'leave' and e['p'] in names:
        left[names[e['p']]] = e['t']
rows = [r for r in D['decisions'] if T0 <= r[1] < T1]
base = D.get('baseline')
print(f"===== {mid} 延迟明细（基线 {base} 拍；决策 {len(rows)} 条；慢 = 延迟 ≥ {LATE} 拍）=====")
print('阵亡拍：' + '、'.join(f'{b} {t}' for b, t in sorted(died.items(), key=lambda kv: kv[1])) + ('｜离开拍：' + '、'.join(f'{b} {t}' for b, t in sorted(left.items(), key=lambda kv: kv[1])) if left else ''))
last = D.get('lastLocalTick') or {}
if last:
    print('客户端日志最后一拍：' + '、'.join(f'{b} {t}' for b, t in sorted(last.items(), key=lambda kv: kv[1])))

W = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    W[r[1] // WIN * WIN][r[0]].append(r)
print(f"\n-- 每 {WIN} 拍：决策数 / 落地 / 延迟中位 / 最大 / 慢的条数 / 没落地；后面是慢或丢得最多的号 --")
for w in sorted(W):
    allr = [r for rs in W[w].values() for r in rs]
    dl = [r[6] for r in allr if r[6] is not None]
    lost = [r for r in allr if r[4] == 'lost']
    late = [r for r in allr if r[6] is not None and r[6] >= LATE]
    per = []
    for b, rs in W[w].items():
        d2 = [r[6] for r in rs if r[6] is not None]
        l2 = sum(1 for r in rs if r[4] == 'lost')
        s2 = sum(1 for x in d2 if x >= LATE)
        if l2 or s2:
            per.append((s2 + l2, f"{b} 中位 {statistics.median(d2):g}/慢 {s2}/丢 {l2}" if d2 else f"{b} 丢 {l2}"))
    per.sort(reverse=True)
    print(f"   {w:>5}: {len(allr):>4} / {len(dl):>4} / {statistics.median(dl) if dl else float('nan'):>6g} / {max(dl) if dl else 0:>5g} / {len(late):>3} / {len(lost):>3}   " + '；'.join(x[1] for x in per[:6]))

print('\n-- 没落地的指令：号 × 窗口 × 目标类别（条数 / 名义兵数）；括号里是这个号的阵亡拍 --')
L = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r[4] == 'lost':
        k = (r[0], r[1] // WIN * WIN, r[3])
        L[k][0] += 1; L[k][1] += r[7] or 0
tot = collections.Counter(); totT = collections.Counter()
for (b, w, c), (n, tr) in sorted(L.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    tot[c] += n; totT[c] += tr
    near = ''
    if b in died and 0 <= died[b] - w <= 2 * WIN:
        near = '  ← 阵亡前后'
    if b in left and w + WIN >= left[b] - 600:
        near += '  ← 掉线前后'
    print(f"   {w:>5} {b:<14} {c} {n:>3} 条 {tr:>10,.0f}（阵亡 {died.get(b, '–')}）{near}")
print('   合计：' + '；'.join(f"{c} {tot[c]} 条 {totT[c]:,.0f}" for c in tot))
# 没落地的指令离这个号的阵亡 / 客户端最后一拍有多远
gap = []
for r in rows:
    if r[4] == 'lost' and r[0] in died:
        gap.append(died[r[0]] - r[1])
if gap:
    g = sorted(gap)
    print(f"   没落地且该号后来阵亡的 {len(g)} 条：决策拍离阵亡拍 中位 {statistics.median(g):g}、≤60 拍的 {sum(1 for x in g if x <= 60)}、≤300 拍的 {sum(1 for x in g if x <= 300)}")

print(f'\n-- 慢指令（延迟 ≥ {LATE}）：目标类别 × 结果（条数 / 实际打出 / 退回）；D = 捐兵 --')
S = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    if r[6] is not None and r[6] >= LATE:
        k = (r[3], r[4])
        S[k][0] += 1; S[k][1] += r[8] or 0; S[k][2] += r[9] or 0
for (c, st), (n, out, tiles) in sorted(S.items()):
    print(f"   {c} {st:<5} {n:>4} 条 打出 {out:>10,.0f} 退回 {tiles:>10,.0f}")
