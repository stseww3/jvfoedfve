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
# --ai：只看贴着内置 AI 的行动拍（nAI>0），按 gateAI 列（第一条内置 AI 报价的去向）计数：
#   send     这条 AI 报价过了所有门（这一拍对它有出兵意图，或被 isNoFullSend 守卫拦掉）
#   price    L5359 这条 AI 报价的单价 ≥ worth → 报价单到此为止
#   behind   报价单在排在它前面的报价上就结束了（前面的报价 price 或已经出手）
#   floor/keep       价格预算要留的兵（L5420~5427）把可用兵压到 0
#   floor/sf/<谁>    safeAt → safeFinite 顶住（botSkip=0：不排除要买的这个 AI，也不排除队友）；<谁> = squad 编队号 / ally 同队真人 / enemy 敌方真人 / ai
#   floor/dp         safeAt 里的 killW×dpKeep 顶住；前缀 cap+ = 被 oppFloorCap×地 截住之后仍然不够
#   chunk    L5449~5454 兵不够一次吃掉且 < 20% 余额
#   covered  在途的兵已经够吃掉它（offers L5096 rawNeed ≤ 0），所以不在报价单里
#   slots    目标数已满 / 没有空槽（offers L5089）
#   nobuy    这一拍 buyLand 没走到报价单（调度、救急、清场等先返回）
import sys, os, csv, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    a_all = a
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
    if '--ai' in a_all:
        ai_mode(mid, rows, t0, t1, bots)
        return
    tot = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    tgt = collections.defaultdict(collections.Counter)
    n = 0
    fdet = collections.Counter()
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
            parts = gate.split(':')
            lab, q = parts[0], parts[1]
            if lab == 'floor' and len(parts) > 2:
                det = ':'.join(parts[2:])
                kind = det.split('/')[0]
                fdet[kind + ('/' + det.split('/')[1].split(':')[0] if '/' in det else '')] += 1
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
    if fdet:
        print('floor 是哪一项顶住的（keep = 价格预算要留的兵 L5420~5427；dp = safeAt 里的 killW×dpKeep，即最强的非队友真人邻居的全部余额打不垮我要留的兵；sf = safeFinite；cap+ = 被 oppFloorCap×地 截住后仍不够；empty = 余额已经是 0）：'
              + '，'.join(f'{k} {v}' for k, v in fdet.most_common()))
    for b in sorted(per, key=lambda x: -sum(per[x].values())):
        c = per[b]
        s = sum(c.values())
        line = f'  {b:7s} {s:5d} 拍：' + '，'.join(f'{k} {c[k]}（{100 * c[k] / s:.0f}%）' for k in order if c[k])
        print(line)
        if by_target and tgt[b]:
            print('          按目标：' + '，'.join(f'{k} {v}' for k, v in tgt[b].most_common(8)))


def ai_mode(mid, rows, t0, t1, bots):
    if 'gateAI' not in rows[0]:
        print('rows.tsv 没有 gateAI 列：先重跑 bash scripts/shadow_all.sh ' + mid)
        return
    n = nw = 0
    tot = collections.Counter()
    totw = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    refs = collections.Counter()
    span = {}
    for r in rows:
        t = int(r['t'])
        if t < max(t0, 1500) or t >= t1 or int(r['nAI']) <= 0:
            continue
        if bots and r['bot'] not in bots:
            continue
        ga = r['gateAI']
        parts = ga.split(':') if ga else ['空']
        lab = parts[0]
        if lab == 'floor':
            det = ':'.join(parts[2:]) if len(parts) > 2 else '?'
            kind = det.split('/')[0]
            if 'sf' in kind:
                who = det.split('/')[1].split(':')[0] if '/' in det else '-'
                lab = 'floor/' + kind + '/' + who
                refs[det.split('/')[1] if '/' in det else '-'] += 1
            else:
                lab = 'floor/' + kind
        n += 1
        tot[lab] += 1
        per[r['bot']][lab] += 1
        weak = int(r['nAIweak']) > 0
        if weak:
            nw += 1
            totw[lab] += 1
        lo, hi = span.get(r['bot'], (t, t))
        span[r['bot']] = (min(lo, t), max(hi, t))
    hi = max(int(r['t']) for r in rows)
    print(f'# {mid} 核心期贴着内置 AI 的行动拍 [{max(t0, 1500)},{min(t1, hi + 5)})：共 {n} 个号·行动拍，其中贴着弱 AI（兵 < 地）的 {nw} 个')
    if not n:
        return
    order = [k for k, _ in tot.most_common()]
    print('第一条 AI 报价的去向：' + '，'.join(f'{k} {tot[k]}（{100 * tot[k] / n:.0f}%）' for k in order))
    if nw:
        print('其中贴着弱 AI 的：' + '，'.join(f'{k} {totw[k]}（{100 * totw[k] / nw:.0f}%）' for k in order if totw[k]))
    if refs:
        print('safeFinite 顶住时参照的是谁（类别:引擎编号 次数）：' + '，'.join(f'{k} {v}' for k, v in refs.most_common(10)))
    for b in sorted(per, key=lambda x: -sum(per[x].values())):
        c = per[b]
        s = sum(c.values())
        print(f'  {b:7s} {s:5d} 拍（{span[b][0]}~{span[b][1]}）：' + '，'.join(f'{k} {c[k]}' for k in order if c[k]))


main()
