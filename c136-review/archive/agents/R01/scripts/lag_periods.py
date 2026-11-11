#!/usr/bin/env python3
"""lag_periods.py — 一局的“延迟硬账”（总部 0007 第 2 条），按时段 0–600 / 600–1500 / 1500–3000 / 3000+ 出四张表。
只读 out/<局号>/ 下的重演产物：shadow_cmds.csv（影子策略每个决策拍想发的令；ok=1 是页面闸门放行的）、
shadow_match.csv（录像里本队每条落地指令，能对上影子决策的带决策拍和延迟）、shadow_check.csv（日志 HL-TICK 里页面自己数的 cmds/boats）。
用法：python3 scripts/lag_periods.py <局号> [--periods 0-600,600-1500,1500-3000,3000-99999] [--confirm 21] [--tag land] [--json]
  表 1 指令延迟（按决策拍分段）：影子放行的陆攻+捐兵 → 在录像里定位到的落地 → 落地率；延迟 = 落地拍 − 决策拍 的 P50/P90/最大。
  表 2 漏斗（按拍分段）：影子想发（含闸门拦下的）/ 影子放行 / 页面日志 cmds 增量（本地拍）/ 录像落地（陆攻+捐兵+船）。
  表 3 迟到扑空（按落地拍分段，只算陆攻）：落地条数、生效条数、落地时目标已不在（引擎改打无主地）的条数、一兵未扣的条数；
        生效的指令里“决策时想出的兵”对“落地时实扣的兵”。
  表 4 重复下令与补帧批次（按落地拍分段）：同一个号对同一目标在上一条落地后 --confirm 拍内又落地一条（看不到上一条的结果就又下令）的条数和这些条实扣的兵；
        同一个服务器拍里同一个号落地 >=3 条陆攻的批次数、条数、实扣的兵、批次里单拍花掉余额的最大比例。
说明：c110（B 组）的页面外壳会跳过一部分决策拍，影子是“每个决策拍都跑”的近似，表 1/2 的“影子”列偏多，以录像落地和日志为准。
      延迟只对能在影子里找到同号同类同目标同 pct 的落地指令有定义（uniq != 0）。
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
periods = [tuple(map(int, w.split('-'))) for w in opt('periods', '0-600,600-1500,1500-3000,3000-99999').split(',')]
confirm = int(opt('confirm', '21'))
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8'))) if os.path.exists(os.path.join(D, f)) else []
tag = opt('tag', '')  # --tag land：读 shadow_*_land.csv（A031 的默认输出是旧核对口径，land 口径才和日志逐点全同）
sfx = '_' + tag if tag else ''
cmds, match, check = rd(f'shadow_cmds{sfx}.csv'), rd(f'shadow_match{sfx}.csv'), rd(f'shadow_check{sfx}.csv')
fnum = lambda x: float(x) if x not in ('', None) else 0.0


def q(v, p):
    if not v:
        return '-'
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


def pname(t0, t1):
    return f'{t0}+' if t1 >= 99999 else f'{t0}–{t1}'


out = {'mid': mid, 'tag': tag, 'periods': {}}
print(f'== {mid} 表 1 指令延迟（按决策拍分段；影子放行的陆攻+捐兵）：放行 / 定位到落地 / 落地率；延迟 P50 / P90 / 最大（拍）')
for t0, t1 in periods:
    acc = [r for r in cmds if r['ok'] == '1' and r['kind'] in ('attack', 'donate') and t0 <= int(r['t']) < t1]
    lags = [int(r['landedAt']) - int(r['t']) for r in acc if r['landedAt']]
    print(f'   {pname(t0, t1):>10s} 放行 {len(acc):5d} 落地 {len(lags):5d} ({100 * len(lags) / max(1, len(acc)):5.1f}%)  延迟 {q(lags, .5)} / {q(lags, .9)} / {max(lags) if lags else "-"}')
    out['periods'][pname(t0, t1)] = {'accepted': len(acc), 'landed': len(lags), 'p50': q(lags, .5), 'p90': q(lags, .9), 'max': max(lags) if lags else None}
    # 分开陆攻和捐兵：捐兵不落地多半是引擎的捐款额度拒收（不进录像），和迟到是两回事
    for kind, key in (('attack', 'a'), ('donate', 'd')):
        ak = [r for r in acc if r['kind'] == kind]
        lk = [int(r['landedAt']) - int(r['t']) for r in ak if r['landedAt']]
        out['periods'][pname(t0, t1)].update({key + 'Acc': len(ak), key + 'Land': len(lk), key + 'P50': q(lk, .5), key + 'P90': q(lk, .9), key + 'Max': max(lk) if lk else None})
    o = out['periods'][pname(t0, t1)]
    print(f'   {"":>10s}   其中陆攻 {o["aAcc"]:5d}→{o["aLand"]:5d} ({100 * o["aLand"] / max(1, o["aAcc"]):5.1f}%) 延迟 {o["aP50"]} / {o["aP90"]}；捐兵 {o["dAcc"]:5d}→{o["dLand"]:5d} ({100 * o["dLand"] / max(1, o["dAcc"]):5.1f}%)')

print(f'== {mid} 表 1b 指令延迟（按落地拍分段；录像里本队落地的陆攻+捐兵）：落地 / 能对上决策拍 / 延迟 P50 / P90 / 最大（拍）')
for t0, t1 in periods:
    L = [r for r in match if r['kind'] in ('attack', 'donate') and t0 <= int(r['tick']) < t1]
    lags = [int(r['lag']) for r in L if r['uniq'] != '0' and r['lag'] not in ('', None)]
    print(f'   {pname(t0, t1):>10s} 落地 {len(L):5d} 对上 {len(lags):5d}  延迟 {q(lags, .5)} / {q(lags, .9)} / {max(lags) if lags else "-"}')
    out['periods'][pname(t0, t1)].update({'landedAll': len(L), 'located': len(lags), 'lp50': q(lags, .5), 'lp90': q(lags, .9), 'lmax': max(lags) if lags else None})

# 页面日志 cmds：每个号在每个时段末最后一个采样点的累计值
log_at = defaultdict(dict)
for r in check:
    log_at[r['bot']][int(r['t'])] = int(r['logCmds'] or 0)


def log_cum(t):
    s = 0
    for b, d in log_at.items():
        ks = [k for k in d if k < t]
        if ks:
            s += d[max(ks)]
    return s


print(f'== {mid} 表 2 漏斗：影子想发（含闸门拦下）/ 影子放行 / 页面日志 cmds 增量（按本地拍，取时段末最后一个 HL-TICK 采样点）/ 录像落地（陆攻+捐兵+船，按落地拍）')
tot = [0, 0, 0, 0]
for t0, t1 in periods:
    want = [r for r in cmds if t0 <= int(r['t']) < t1]
    acc = [r for r in want if r['ok'] == '1']
    land = [r for r in match if t0 <= int(r['tick']) < t1]
    lg = log_cum(t1) - log_cum(t0)
    for i, v in enumerate((len(want), len(acc), lg, len(land))):
        tot[i] += v
    print(f'   {pname(t0, t1):>10s} 想发 {len(want):5d} 放行 {len(acc):5d} 日志 {lg:5d} 落地 {len(land):5d}')
    out['periods'][pname(t0, t1)].update({'want': len(want), 'ok': len(acc), 'logCmds': lg, 'replayLanded': len(land)})
print(f'   {"合计":>10s} 想发 {tot[0]:5d} 放行 {tot[1]:5d} 日志 {tot[2]:5d} 落地 {tot[3]:5d}  （落地/日志 = {100 * tot[3] / max(1, tot[2]):.1f}%）')
out['total'] = {'want': tot[0], 'ok': tot[1], 'logCmds': tot[2], 'replayLanded': tot[3]}

print(f'== {mid} 表 3 迟到扑空（按落地拍分段，陆攻）：落地 / 生效 / 目标已不在（改打无主地）/ 一兵未扣；生效指令 想出的兵 → 实扣的兵')
for t0, t1 in periods:
    L = [r for r in match if r['kind'] == 'attack' and t0 <= int(r['tick']) < t1]
    eff = [r for r in L if fnum(r['spent']) > 0]
    gone = [r for r in L if r['shTarget'] not in ('', None) and r['shTarget'] != r['target'] and r['target'] == '512']
    zero = [r for r in L if fnum(r['spent']) <= 0]
    want = sum(fnum(r['troopsDecide']) for r in eff if r['uniq'] != '0')
    got = sum(fnum(r['spent']) for r in eff if r['uniq'] != '0')
    allgot = sum(fnum(r['spent']) for r in eff)
    wz = sum(fnum(r['troopsDecide']) for r in zero if r['uniq'] != '0')
    print(f'   {pname(t0, t1):>10s} 落地 {len(L):4d} 生效 {len(eff):4d} 目标已不在 {len(gone):4d}（其中一兵未扣 {sum(1 for r in gone if fnum(r["spent"]) <= 0)}） 一兵未扣 {len(zero):4d}（决策时想出的兵合计 {wz:.0f}）| 生效且对上决策的：想出 {want:.0f} → 实扣 {got:.0f}（{got / want:.2f} 倍）；全部生效实扣 {allgot:.0f}' if want else
          f'   {pname(t0, t1):>10s} 落地 {len(L):4d} 生效 {len(eff):4d} 目标已不在 {len(gone):4d} 一兵未扣 {len(zero):4d} | 全部生效实扣 {allgot:.0f}')
    out['periods'][pname(t0, t1)].update({'atkLanded': len(L), 'atkEff': len(eff), 'targetGone': len(gone), 'zero': len(zero), 'zeroWanted': wz, 'wantTroops': want, 'gotTroops': got, 'allSpent': allgot})

print(f'== {mid} 表 4 重复下令与补帧批次（按落地拍分段，陆攻）：上一条落地后 {confirm} 拍内对同一目标又落地的条数 / 这些条实扣的兵；同拍 >=3 条的批次 数 / 条数 / 实扣 / 单拍花掉余额的最大比例')
by = defaultdict(list)
for r in match:
    if r['kind'] == 'attack':
        by[r['bot']].append(r)
for t0, t1 in periods:
    rep = repT = 0
    nb = nrows = 0
    bsp = 0.0
    worst = 0.0
    worst_at = ''
    for b, rs in by.items():
        rs = sorted(rs, key=lambda r: int(r['tick']))
        last = {}
        ticks = defaultdict(list)
        for r in rs:
            t = int(r['tick'])
            if t0 <= t < t1:
                ticks[t].append(r)
                k = r['target']
                if k in last and 0 < t - last[k] <= confirm:
                    rep += 1
                    repT += fnum(r['spent'])
            last[r['target']] = t
        for t, L in ticks.items():
            if len(L) >= 3:
                nb += 1
                nrows += len(L)
                sp = sum(fnum(r['spent']) for r in L)
                bsp += sp
                b0 = max(fnum(r['balExec']) for r in L)
                if b0 > 0 and sp / b0 > worst:
                    worst = sp / b0
                    worst_at = f'{b}@{t} {len(L)} 条'
    print(f'   {pname(t0, t1):>10s} 重复 {rep:4d} 条 实扣 {repT:.0f} | 批次 {nb:3d} 个 {nrows:4d} 条 实扣 {bsp:.0f} 单拍最多花掉余额 {100 * worst:.1f}%（{worst_at}）')
    out['periods'][pname(t0, t1)].update({'repeat': rep, 'repeatTroops': repT, 'batches': nb, 'batchRows': nrows, 'batchTroops': bsp, 'batchWorst': worst})
if '--json' in a:
    json.dump(out, open(os.path.join(D, 'lag_periods.json'), 'w'), ensure_ascii=False)
    print(f'# 已写 out/{mid}/lag_periods.json')
