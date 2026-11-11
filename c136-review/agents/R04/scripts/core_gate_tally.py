#!/usr/bin/env python3
# 核心期（t ≥ coreFrom）每个行动拍：没有陆攻意图的那一拍，Policy.buyLand 在第一条真人报价上是被哪道门拦下的。
# 用法：python3 scripts/core_gate_tally.py <局号> [t0 t1] [--bots a,b] [--by-target]
# 数据：tmp/shadow/<局号>/rows.tsv 的 gate 列（shadow.mjs --rows 产出；判定在 shadow_diag.coreGate 里照抄 buyLand 的条件）。
# 标签（行号以 v27-team-c116-vb.js 为准）：
#   出手     这一拍有陆攻意图
#   donate   这一拍发了调度（tryDonateToTeammate 先返回，buyLand 没走到）
#   boat     这一拍发了船
#   nobuy    buyLand 没被调用（非决策拍以外的提前返回：救急、清场等）
#   nooffer  报价单为空（没有可打的非队友陆上邻居）
#   price    L5359  单价 c ≥ 每像素值 worth、不便宜、余额没过 100×地 → 整张报价单到此为止
#   sole     L5361~5365 唯一的真人邻居（健康、没在打我、打穿会露出新真人）：余额 < 1.28×100×地 之前不打
#   crowded  L5371~5374 「拥挤硬目标」：余额 < 1.26×100×地 之前不打
#   floor    L5446~5447 余额 − 手续费 − 要留的兵 ≤ 0
#   inflight L5575/L5589/L5596 已有在途的兵
#   small    L5583/L5591/L5605 这一发 < max(最小指令, 4% 余额)
#   chunk    L5612  不走脉冲、兵不够一次打穿且 < 20% 余额
#   send     这些门都过了但这一拍没有意图（多半是 Policy.send L3844 的 isNoFullSend 守卫拦掉，见 check.json 的 blocked）
#   tiny / absorb / doorSea / siege 见 shadow_diag.coreGate 的注释
import sys, os, csv, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    mid = a[0]
    nums = [int(x) for x in a[1:] if x.lstrip('-').isdigit()]
    t0, t1 = (nums + [1500, 10 ** 9])[:2] if len(nums) >= 2 else (1500, 10 ** 9)
    bots = a[a.index('--bots') + 1].split(',') if '--bots' in a else None
    by_target = '--by-target' in a
    path = os.path.join(HERE, '..', 'tmp', 'shadow', mid, 'rows.tsv')
    rows = list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))
    if not rows or 'gate' not in rows[0]:
        print('rows.tsv 没有 gate 列：先重跑 bash scripts/shadow_all.sh ' + mid)
        return
    tot = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    tgt = collections.defaultdict(collections.Counter)
    n = 0
    for r in rows:
        t = int(r['t'])
        if t < t0 or t >= t1 or t < 1500:
            continue
        if bots and r['bot'] not in bots:
            continue
        gate = r['gate']
        if int(r['intents']) > 0 and gate == '':
            lab, q = '出手', ''
        elif ':' in gate:
            lab, q = gate.split(':')
        else:
            lab, q = gate or '其他', ''
        n += 1
        tot[lab] += 1
        per[r['bot']][lab] += 1
        if q:
            tgt[r['bot']][lab + '→' + q] += 1
    hi = max(int(r['t']) for r in rows)
    print(f'# {mid} 核心期行动拍的去向 [{t0},{min(t1, hi + 5)})：共 {n} 个号·行动拍')
    order = [k for k, _ in tot.most_common()]
    print('合计：' + '，'.join(f'{k} {tot[k]}（{100 * tot[k] / max(1, n):.0f}%）' for k in order))
    for b in sorted(per, key=lambda x: -sum(per[x].values())):
        c = per[b]
        s = sum(c.values())
        line = f'  {b:7s} {s:5d} 拍：' + '，'.join(f'{k} {c[k]}（{100 * c[k] / s:.0f}%）' for k in order if c[k])
        print(line)
        if by_target and tgt[b]:
            print('          按目标：' + '，'.join(f'{k} {v}' for k, v in tgt[b].most_common(8)))


main()
