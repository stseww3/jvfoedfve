#!/usr/bin/env python3
# quota_guard.py — 「No-Full-Send 配额闸」在一局里拦了多少次出手（读 shadow.mjs --json 的 nfsAt / sendExits / tc 字段）。
#   背景（策略源码，Policy.send / updateShadowQuota）：每次线上出手后记下 pendingQuotaCheck，其后 1–7 拍里只要存兵比出手前少了
#   （扣掉手续费），就拿「少掉的兵」和「这次想发的兵」比；想发的 ≥ 少掉的 1.12 倍 → isNoFullSend 置位、影子配额清零。
#   isNoFullSend 置位以后没有任何地方把它复位；配额不够时 Policy.send 对机器人目标直接 return false（不发），对真人目标改发 1 兵或不发。
#   线上指令要十几拍以后才落地，这 1–7 拍里存兵变少只可能是更早的指令落地或被人打——都不是「这一条被引擎限额」。
#   输出：每个号 isNoFullSend 第一次置位的拍；每 300 拍 Policy.send 被调用多少次、其中没走到最后一句（return ok）的多少次（= 配额闸拒发），
#         按出口行列出；--tc 窗口里「选了目标但没发出去」的决策拍数。
#   「走到最后一句」按本局出现过的最大出口行认（c110 = 3934，Vb = 3924）。
#   先跑：bash ../../tools/run-heavy.sh node scripts/shadow.mjs <局> --quiet --tc 600:1500 --json /tmp/c136-r05/work/<局>-shadow.json
# 用法：python3 scripts/quota_guard.py <局…> [--json FILE] [--by-bot]
import json, sys, collections
a = sys.argv[1:]
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--json')]
OUT = {}
for mid in ids:
    S = json.load(open(f'/tmp/c136-r05/work/{mid}-shadow.json'))
    if 'sendExits' not in S:
        print(f'== {mid}: 影子 JSON 里没有 sendExits（要用新版 shadow.mjs 重跑）'); continue
    X = S['sendExits']; nfs = S.get('nfsAt') or {}
    ok_line = max((x['exit'] for x in X if isinstance(x['exit'], int)), default=None)
    tot = sum(x['n'] for x in X); ref = sum(x['n'] for x in X if x['exit'] != ok_line)
    print(f'== {mid}（{S.get("ver")}）：Policy.send 被调用 {tot} 次，没走到 return ok（L{ok_line}）的 {ref} 次（{100 * ref / max(1, tot):.1f}%）==')
    set_ = {b: t for b, t in nfs.items() if t is not None}
    print(f'   isNoFullSend 置位：{len(set_)}/{len(nfs)} 个号；置位拍 ' + '、'.join(f'{b} {t}' for b, t in sorted(set_.items(), key=lambda kv: kv[1])) + ('｜没置位：' + '、'.join(b for b, t in nfs.items() if t is None) if len(set_) < len(nfs) else ''))
    byw = collections.defaultdict(lambda: collections.Counter())
    for x in X:
        byw[x['w']]['calls'] += x['n']
        if x['exit'] != ok_line: byw[x['w']]['refused'] += x['n']; byw[x['w']][f"L{x['exit']}"] += x['n']
        if x['nfs']: byw[x['w']]['nfs1'] += x['n']
    print('   每 300 拍（调用 / 拒发 / 其中各出口行 / 调用时 isNoFullSend=1）：')
    for w in sorted(byw):
        c = byw[w]
        if c['refused'] or c['calls'] >= 20:
            print(f"      {w}: {c['calls']} / {c['refused']}（{100 * c['refused'] / max(1, c['calls']):.0f}%）/ " + ' '.join(f'{k}×{v}' for k, v in sorted(c.items()) if k.startswith('L')) + f" / {c['nfs1']}")
    per = collections.defaultdict(lambda: collections.Counter())
    for x in X:
        per[x['bot']]['calls'] += x['n']
        if x['exit'] != ok_line: per[x['bot']]['refused'] += x['n']
    if '--by-bot' in a:
        print('   逐号（调用 / 拒发）：' + '；'.join(f"{b} {c['calls']}/{c['refused']}" for b, c in sorted(per.items(), key=lambda kv: -kv[1]['refused'])))
    PER = [(0, 600, '0–600'), (600, 1500, '600–1500'), (1500, 3000, '1500–3000'), (3000, 10 ** 9, '3000+')]
    pp = []
    for lo, hi, lab in PER:
        cc = sum(x['n'] for x in X if lo <= x['w'] < hi); rr = sum(x['n'] for x in X if lo <= x['w'] < hi and x['exit'] != ok_line)
        pp.append({'period': lab, 'calls': cc, 'refused': rr})
    print('   分时段（调用 / 拒发）：' + '；'.join(f"{p['period']} {p['calls']}/{p['refused']}（{100 * p['refused'] / max(1, p['calls']):.0f}%）" for p in pp))
    tc = S.get('tc') or []
    if tc and any('ps' in r for r in tc):
        n = len(tc); nocmd = [r for r in tc if not [c for c in r['cmds'] if c[0] in ('attack', 'boat', 'boatTo')]]
        refd = [r for r in nocmd if r.get('ps') and any(e != ok_line for e in r['ps'])]
        print(f"   --tc 窗口 {S.get('tcWin')}：决策拍 {n}，没发指令的 {len(nocmd)}，其中当拍选了目标但被 Policy.send 拒发的 {len(refd)}（占全部决策拍 {100 * len(refd) / max(1, n):.1f}%）")
    OUT[mid] = {'ver': S.get('ver'), 'okLine': ok_line, 'calls': tot, 'refused': ref, 'nfsAt': nfs, 'byPeriod': pp,
                'by300': [{'w': w, **dict(byw[w])} for w in sorted(byw)], 'byBot': {b: dict(c) for b, c in per.items()}}
if '--json' in a:
    json.dump(OUT if len(ids) > 1 else OUT.get(ids[0], {}), open(a[a.index('--json') + 1], 'w'), ensure_ascii=False)
