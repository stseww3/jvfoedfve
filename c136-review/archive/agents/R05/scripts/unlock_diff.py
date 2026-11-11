#!/usr/bin/env python3
"""unlock_diff.py — isNoFullSend 误锁改变了多少决策：原样影子 对 「每拍把 isNoFullSend 清回 false」的对照影子，逐拍逐号比较。

输入：/tmp/c136-r05/work/<局>-shadow.json（shadow.mjs <局> --quiet --tc 600:1500 --json）
      /tmp/c136-r05/work/<局>-shadow-unlock.json（shadow.mjs <局> --quiet --unlock --json；批量 shadow_unlock.sh）
      /tmp/c136-r05/truth/<局>.json（取真人数，分目标类别）
口径：
  一条决策 = (号, 拍, 类型, 目标, pct)。两边都有 → 相同；只在原样影子里 → 「锁着才发的」（锁把某道门关掉后多发的）；
  只在对照影子里 → 「锁挡掉的」（配额闸拒发，或锁改变内部状态后没再发的）。
  两个影子跑在同一份录像局面上，决策都不落地，所以差异只来自策略内部状态（isNoFullSend、shadowQuota 以及它们带出的记忆）。
  这是一阶量：某条决策不同以后，真实对局会走向别处，这里看不到。
  时段按决策拍：0–600 / 600–1500 / 1500–3000 / 3000–5000 / 5000+（Vb、c110 的 leaderHardFrom = 5000）。
  目标类别：N 中立、B 机器人、H 真人、S 船、D 捐兵。兵数 = 影子记录的该条指令名义兵数。

用法：python3 scripts/unlock_diff.py <局…> [--json FILE] [--list N]
"""
import json, sys, collections

a = sys.argv[1:]
jo = a[a.index('--json') + 1] if '--json' in a else None
nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--json', '--list'))]
W = '/tmp/c136-r05/work'
PER = [(0, 600), (600, 1500), (1500, 3000), (3000, 5000), (5000, 10 ** 9)]
PN = ['0–600', '600–1500', '1500–3000', '3000–5000', '5000+']
per = lambda t: next(i for i, (lo, hi) in enumerate(PER) if lo <= max(0, t) < hi)
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
OUT = {}


def load(p, H):
    S = json.load(open(p))
    d = {}
    for r in S['ticks']:
        for i, c in enumerate(r['cmds']):
            kk = {'attack': 'attack', 'boat': 'boat', 'boatTo': 'boat', 'donate': 'donate'}.get(c['k'])
            if not kk:
                continue
            q = c.get('q', -1)
            cl = 'D' if kk == 'donate' else 'S' if kk == 'boat' else ('N' if q >= 512 else 'H' if q < H else 'B')
            key = (r['bot'], r['t'], kk, q, c['pct'])
            d[key] = (cl, c.get('troops', 0), r.get('bal', 0))
    return S, d


for mid in ids:
    try:
        J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
        S0, A = load(f'{W}/{mid}-shadow.json', J['humans'])
        S1, U = load(f'{W}/{mid}-shadow-unlock.json', J['humans'])
    except OSError as e:
        print(f'{mid}: 缺输入 {e}')
        continue
    rows = []
    for i, pn in enumerate(PN):
        ka = {x for x in A if per(x[1]) == i}
        ku = {x for x in U if per(x[1]) == i}
        only_a, only_u = ka - ku, ku - ka
        ca, cu = collections.Counter(A[x][0] for x in only_a), collections.Counter(U[x][0] for x in only_u)
        ta, tu = collections.Counter(), collections.Counter()
        for x in only_a:
            ta[A[x][0]] += A[x][1]
        for x in only_u:
            tu[U[x][0]] += U[x][1]
        rows.append({'period': pn, 'asPlayed': len(ka), 'unlocked': len(ku), 'same': len(ka & ku), 'onlyLocked': len(only_a), 'onlyUnlocked': len(only_u),
                     'onlyLockedByClass': dict(ca), 'onlyUnlockedByClass': dict(cu), 'onlyLockedTroops': dict(ta), 'onlyUnlockedTroops': dict(tu)})
    nfs = S0.get('nfsAt') or {}
    tot_a, tot_u = len(A), len(U)
    same = len(set(A) & set(U))
    OUT[mid] = {'ver': S0.get('ver'), 'asPlayed': tot_a, 'unlocked': tot_u, 'same': same, 'changedShare': (tot_a - same + tot_u - same) / max(1, tot_a + tot_u - same),
                'nfsAt': nfs, 'byPeriod': rows}
    print(f"===== {mid}（{S0.get('ver')}）原样影子 {tot_a} 条｜对照影子（不锁）{tot_u} 条｜两边相同 {same} 条｜有差别的 {tot_a - same + tot_u - same} 条（占并集 {100 * OUT[mid]['changedShare']:.1f}%）=====")
    if nfs:
        flagged = sorted((t, b) for b, t in nfs.items() if t is not None and t >= 0)
        print(f"   isNoFullSend 置位：{len(flagged)}/{len(nfs)} 个号" + ('，置位拍 ' + '、'.join(f'{b} {t}' for t, b in flagged) if flagged else ''))
    for r in rows:
        if not (r['asPlayed'] or r['unlocked']):
            continue
        fa = '、'.join(f"{c}×{n}（{k(r['onlyLockedTroops'].get(c, 0))}）" for c, n in sorted(r['onlyLockedByClass'].items())) or '–'
        fu = '、'.join(f"{c}×{n}（{k(r['onlyUnlockedTroops'].get(c, 0))}）" for c, n in sorted(r['onlyUnlockedByClass'].items())) or '–'
        print(f"   {r['period']:>9}: 原样 {r['asPlayed']:>4}｜不锁 {r['unlocked']:>4}｜相同 {r['same']:>4}｜锁着才发的 {r['onlyLocked']:>3}：{fa}｜锁挡掉的 {r['onlyUnlocked']:>3}：{fu}")
    if nlist:
        xs = sorted(set(A) ^ set(U), key=lambda x: (x[1], x[0]))
        for x in xs[:nlist]:
            src = '锁着才发' if x in A else '锁挡掉'
            cl, tr, bal = (A.get(x) or U.get(x))
            print(f"      {x[1]:>5} {x[0]:<12} {src} {x[2]} → {x[3]} pct={x[4]} 类 {cl} 兵 {tr:,}（存兵 {bal:,}）")
if jo:
    json.dump(OUT, open(jo, 'w'), ensure_ascii=False)
    print('→', jo)
