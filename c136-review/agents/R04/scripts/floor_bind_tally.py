#!/usr/bin/env python3
# floor_bind_tally.py — 核心期之前，我方号「贴着内置 AI 却没出手」的决策拍里，出兵底线是被哪一项顶住的。
# 用法：python3 scripts/floor_bind_tally.py <局号> [t0 t1]        默认 630 1500
#   先要有 tmp/shadow/<局号>/rows.tsv，且带 bind / sbRef 两列（bash scripts/shadow_all.sh <局号>，shadow.mjs --rows）。
# 口径（每个决策拍 = 每 5 拍一次；只数「有内置 AI 邻居、这一拍影子策略没有给出任何指令」的决策拍）：
#   对底线最低的那个 AI 邻居，底线 = max(winFloor, peopleFloor)（V13.floorFor0 L2233~2241）；winFloor = max(项1, 项2, 项3)（Policy.winFloor L4562~4570）：
#     t1  项1 = mult × AI 单价 × 自己的领土 /(winR × t)        —— 地越多、拍数越早，要留的兵越多
#     dp  项2 = dpKeep                                          —— 开局扩张要留的兵
#     sb  项3 = safeFinite（V13.safeFinite L2500~2510）          —— 每个 AI 邻居的「最弱的别的邻居」的余额 + 它正在打这个 AI 的兵，取最大
#     pf  peopleFloor                                           —— 真人邻居一侧要留的兵
#     ok  底线没有卡住（可用兵 > minShare × 余额 且 ≥ 最小指令），没出手是别的原因（目标数已满、单价、在途兵已够等）
#   sb 的参照对象分四类：squad = 我方编队的号，ally = 同队的其他真人，enemy = 外队真人，ai = 另一个内置 AI。
# 输出：按号、按项的决策拍数；sb 按参照对象分类；被卡住时贴着的弱 AI（兵比地少）的地（平均）。
import sys, os, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    a = sys.argv[1:]
    mid = a[0]
    t0 = int(a[1]) if len(a) > 1 else 630
    t1 = int(a[2]) if len(a) > 2 else 1500
    rp = os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv')
    by = collections.defaultdict(collections.Counter)
    refs = collections.Counter()
    refwho = collections.Counter()
    weak = collections.defaultdict(list)
    n_dec = collections.Counter()
    with open(rp, encoding='utf8') as f:
        rd = csv.DictReader(f, delimiter='\t')
        if 'bind' not in rd.fieldnames:
            raise SystemExit('rows.tsv 没有 bind 列：请重跑 bash scripts/shadow_all.sh ' + mid)
        for r in rd:
            t = int(r['t'])
            if not (t0 <= t < t1):
                continue
            b = r['bot']
            n_dec[b] += 1
            if int(r['intents']) > 0:
                by[b]['出手'] += 1
                continue
            if int(float(r['nAI'])) <= 0:
                by[b]['没有AI邻居'] += 1
                continue
            k = r['bind'] or '?'
            by[b][k] += 1
            if k == 'sb':
                kind = (r['sbRef'] or '?:').split(':')[0]
                refs[kind] += 1
                by[b]['sb:' + kind] += 1
                refwho[r['sbRef']] += 1
            if k != 'ok':
                weak[b].append(int(float(r['weakLand'])))
    cols = ['出手', '没有AI邻居', 't1', 'dp', 'sb', 'pf', 'ok', '?']
    print(f'# {mid} 拍段 [{t0},{t1}) 贴着内置 AI 没出手的决策拍：底线被哪一项顶住')
    print('号       决策拍 | 出手 | 没有AI邻居 | 项1(t1) | 项2(dp) | 项3(sb) [编队号/同队真人/外队真人/另一个AI] | peopleFloor | 底线没卡住 | 被卡住时贴着的弱AI地（平均）')
    tot = collections.Counter()
    for b in sorted(n_dec):
        c = by[b]
        for k, v in c.items():
            tot[k] += v
        tot['n'] += n_dec[b]
        w = weak[b]
        print(f'{b:8s} {n_dec[b]:5d} | {c["出手"]:4d} | {c["没有AI邻居"]:4d} | {c["t1"]:4d} | {c["dp"]:4d} | {c["sb"]:4d} [{c["sb:squad"]}/{c["sb:ally"]}/{c["sb:enemy"]}/{c["sb:ai"]}] | {c["pf"]:4d} | {c["ok"]:4d} | {round(sum(w) / len(w)) if w else 0}')
    n = max(1, tot['n'])
    stuck = tot['t1'] + tot['dp'] + tot['sb'] + tot['pf']
    print(f'合计     {tot["n"]:5d} | {tot["出手"]}（{100 * tot["出手"] / n:.0f}%） | {tot["没有AI邻居"]}（{100 * tot["没有AI邻居"] / n:.0f}%） | {tot["t1"]}（{100 * tot["t1"] / n:.0f}%） | {tot["dp"]}（{100 * tot["dp"] / n:.0f}%） | '
          f'{tot["sb"]}（{100 * tot["sb"] / n:.0f}%）[{tot["sb:squad"]}/{tot["sb:ally"]}/{tot["sb:enemy"]}/{tot["sb:ai"]}] | {tot["pf"]}（{100 * tot["pf"] / n:.0f}%） | {tot["ok"]}（{100 * tot["ok"] / n:.0f}%）')
    print(f'贴着内置 AI、没出手、底线卡住的决策拍合计 {stuck}（占全部决策拍的 {100 * stuck / n:.0f}%）；其中项3 的参照对象：'
          + '、'.join(f'{k} {v}' for k, v in refs.most_common()))
    print('项3 参照对象出现最多的几个（类别:引擎编号 决策拍数）：' + '、'.join(f'{k} {v}' for k, v in refwho.most_common(8)))


if __name__ == '__main__':
    main()
