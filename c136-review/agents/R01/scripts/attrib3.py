#!/usr/bin/env python3
"""attrib3.py — 600–1500 拍“为什么没拿到地”的三分账（总部 0007 第 3 条末尾），全部从已有的重演产物机械汇总。
  ① 出生：天然份额（voronoi_seats.csv，先跑 voronoi_share.mjs）低于其他真人中位一半的号；600–1500 里“没有可打的邻居也没有无主地”（boxed）的决策拍。
  ② 保底线锁死：600–1500 里身边有机器人地（或无主地）但 winFloor/safeFinite 保底线 >= 余额、没下令的决策拍（shadow_idle.csv 的 floor+floorN），
     以及保底线取自 safeFinite / dpKeep / 回本线 各多少拍；这些拍里身边的机器人地格数（窗口均值）。
  ③ 动了但迟到：600–1500 里落地的陆攻令中，落地时目标已不在（引擎改打无主地）/ 一兵未扣 的条数，占落地条数几成；
     这些令在决策时想出的兵合计，占同期全部落地令想出的兵的几成（shadow_match.csv）。
用法：python3 scripts/attrib3.py <局号> [--t0 600 --t1 1500] [--json]
说明：决策拍数来自影子策略（每 5 拍一个决策拍）；离场/阵亡之后的号不再有决策拍。c110 的影子是近似（页面外壳会跳拍）。
     三项不是互斥的分摊，只是三张并排的账：每项各自的分母都写在行里。
"""
import csv, json, os, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
T0, T1 = int(opt('t0', 600)), int(opt('t1', 1500))
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8'))) if os.path.exists(os.path.join(D, f)) else []
idle, match, seats = rd('shadow_idle.csv'), rd('shadow_match.csv'), rd('voronoi_seats.csv')
num = lambda x: float(x) if x not in ('', None) else 0.0
out = {'mid': mid, 't0': T0, 't1': T1}

print(f'== {mid} 三分账 [{T0},{T1})')
# ① 出生
if seats:
    sq = [r for r in seats if r['squad'] == '1']
    oth = [r for r in seats if r['squad'] != '1']
    med_o = statistics.median(int(r['nat']) for r in oth)
    low = [r for r in sq if int(r['nat']) < 0.5 * med_o]
    print(f"   ① 出生：本队 {len(sq)} 个号，天然份额中位 {statistics.median(int(r['nat']) for r in sq):.0f} 格（其他真人中位 {med_o:.0f}）；低于其他真人中位一半的 {len(low)} 个：" + '、'.join(f"{r['name']} {r['nat']}" for r in low))
    out['spawn'] = {'squad': len(sq), 'natMedSquad': statistics.median(int(r['nat']) for r in sq), 'natMedOther': med_o, 'low': len(low)}
W = [r for r in idle if T0 <= int(r['t0']) < T1]
acts = sum(int(r['acts']) for r in W)
cols = ['cmd', 'boxed', 'dp', 'floor', 'floorN', 'other', 'cap', 'bySafe', 'byKeep', 'byPx', 'oPrice', 'oGate', 'oEmpty', 'oNoCall']
tot = {c: sum(int(num(r[c])) for r in W) for c in cols}
pc = lambda x: f'{100 * x / max(1, acts):.1f}%'
print(f"      决策拍合计 {acts}：下令 {tot['cmd']}（{pc(tot['cmd'])}） boxed {tot['boxed']}（{pc(tot['boxed'])}） 开局按租期等 {tot['dp']}（{pc(tot['dp'])}） 保底线 {tot['floor'] + tot['floorN']}（{pc(tot['floor'] + tot['floorN'])}） 其余 {tot['other']}（{pc(tot['other'])}：价格线 {tot['oPrice']} / 其他闸门 {tot['oGate']} / 没目标或没空槽 {tot['oEmpty']} / 没走到 offers {tot['oNoCall']}）")
bx = defaultdict(int)
for r in W:
    bx[r['bot']] += int(r['boxed'])
print('      boxed 决策拍按号：' + ('、'.join(f'{b} {n}' for b, n in sorted(bx.items(), key=lambda kv: -kv[1]) if n) or '无'))
# ② 保底线
fl = defaultdict(lambda: [0, 0, 0, 0, 0, 0.0, 0])
for r in W:
    f = int(r['floor']) + int(r['floorN'])
    if not f:
        continue
    x = fl[r['bot']]
    x[0] += f
    x[1] += int(num(r['bySafe']))
    x[2] += int(num(r['byKeep']))
    x[3] += int(num(r['byPx']))
    x[4] += int(r['cmd'])
    x[5] += num(r['aiLand']) * f
    x[6] += f
print(f"   ② 保底线锁死：{tot['floor'] + tot['floorN']} 个决策拍（身边只剩机器人地 {tot['floor']} / 身边还有无主地 {tot['floorN']}），保底线取自 safeFinite {tot['bySafe']} / dpKeep {tot['byKeep']} / 回本线 {tot['byPx']}")
for b, x in sorted(fl.items(), key=lambda kv: -kv[1][0]):
    print(f'      {b}：{x[0]} 拍（safeFinite {x[1]} / dpKeep {x[2]} / 回本线 {x[3]}），同窗口下令 {x[4]} 次，身边机器人地均值 {x[5] / max(1, x[6]):.0f} 格')
out['floor'] = {'acts': acts, 'floor': tot['floor'], 'floorN': tot['floorN'], 'bySafe': tot['bySafe'], 'byKeep': tot['byKeep'], 'byPx': tot['byPx'], 'boxed': tot['boxed'], 'cmd': tot['cmd'], 'dp': tot['dp'], 'oPrice': tot['oPrice']}
# ③ 迟到
L = [r for r in match if r['kind'] == 'attack' and T0 <= int(r['tick']) < T1]
gone = [r for r in L if r['shTarget'] not in ('', None) and r['shTarget'] != r['target'] and r['target'] == '512']
zero = [r for r in L if num(r['spent']) <= 0]
wz = sum(num(r['troopsDecide']) for r in zero if r['uniq'] != '0')
wall = sum(num(r['troopsDecide']) for r in L if r['uniq'] != '0')
lags = sorted(int(r['lag']) for r in L if r['uniq'] != '0' and r['lag'] not in ('', None))
print(f"   ③ 动了但迟到：落地陆攻 {len(L)} 条，其中目标已不在 {len(gone)} 条（{100 * len(gone) / max(1, len(L)):.1f}%），一兵未扣 {len(zero)} 条（{100 * len(zero) / max(1, len(L)):.1f}%）；"
      f"一兵未扣的令决策时想出 {wz:.0f} 兵 = 同期全部落地令想出的 {wall:.0f} 兵的 {100 * wz / max(1, wall):.1f}%；延迟中位 {lags[len(lags) // 2] if lags else '-'} 拍")
out['late'] = {'landed': len(L), 'gone': len(gone), 'zero': len(zero), 'zeroWanted': wz, 'allWanted': wall, 'lagMed': lags[len(lags) // 2] if lags else None}
if '--json' in a:
    json.dump(out, open(os.path.join(D, 'attrib3.json'), 'w'), ensure_ascii=False)
    print(f'# 已写 out/{mid}/attrib3.json')
