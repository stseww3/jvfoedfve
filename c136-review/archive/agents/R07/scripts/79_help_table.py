#!/usr/bin/env python3
"""79_help_table.py — R07：调度（Policy.tryDonateToTeammate）为什么没发 / 发给了谁。

输入（都由 65_shadow.mjs 产出；它把源码的判定顺序逐行复刻，并与影子实际发出的捐款逐条比对，比对结果在 tsv 第一行）：
  out/<mid>/shadow_donor_gate.tsv   每个号在自己的相位拍（t>=1500，每 25 拍一次）一行：卡在哪一步；对每个候选收方卡在哪一步
  out/<mid>/shadow_underfire.tsv    每个决策拍，我方哪些号身上有敌方真人的进攻（inHumanAtk），是否够「挨打」线、是否落进弃子判定
用法：python3 79_help_table.py <matchId> [--who 收方:t0:t1]... [--span t0:t1]...
输出：out/<mid>/help_table.txt、help_table.json
  A. 按捐方：相位拍数与各种结果的拍数
  B. 按收方：身上有真人进攻的决策拍数、够挨打线的、被判弃子的（两个分支分开）
  C. 每个 --who：这个收方在这段时间里，每个捐方的相位拍各卡在哪
  D. 每个 --span：这段时间全队的相位拍各落在哪一步；「没有合格的收方」的那些拍里，（捐方, 候选）各卡在哪里
"""
import csv, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

LABEL = {
    'D:nocall-atkH': '本拍已出手打真人（调度排在进攻后面）',
    'D:nocall-atkAI': '本拍已出手打内置 AI',
    'D:nocall-neutral': '本拍已发打无主地的指令',
    'D:nocall-boat': '本拍已发船 / 别的指令',
    'D:nocall-early': '没走到调度（act 提前返回）',
    'D:terr<1200': '捐方领土 <1200',
    'D:bal<min': '捐方余额不到下限',
    'D:cooldown': '捐方还在冷却',
    'D:meUnderFire': '捐方自己身上有真人的进攻',
    'D:meAttacking': '捐方压在真人身上的兵 >8% 余额',
    'no-cand': '没有合格的收方',
    'PCT<min': '留底以上可捐的不到下限 pct',
    'C:small': '收方领土太小',
    'C:quit': '收方已离开',
    'C:dense': '收方密度过了上限（115 / 围死捐方 142）',
    'C:rear': '收方没有敌邻、也没有进出的真人进攻',
    'C:doomedA': '收方被判弃子（挨的兵 >1.65×余额）',
    'C:doomedB': '收方被判弃子（t≥4500、领土 <22% 最大号、挨的兵 >0.45×余额）',
    'A:dMe': '协防：捐方密度不到门槛',
    'A:allyDense': '协防：收方密度过高',
    'A:floor': '协防：捐方余额不到 1.12×留底',
    'A:gap': '协防：捐方密度没比收方高出门槛',
    'B:dMe': '余粮：捐方密度不到门槛',
    'B:allyDense': '余粮：收方密度过高',
    'B:floor': '余粮：捐方余额不到 1.14×留底',
    'B:gap': '余粮：捐方密度没比收方高出门槛',
    'SENT': '捐给了它',
    'OTHER': '捐给了别的号',
    'LOST': '合格，但别的收方分更高',
    'ABSENT': '收方不在候选里（已出局）',
}


def lab(code):
    if code.startswith('SENT:'):
        return '捐出（' + {'defense_dispatch': '协防', 'offense_dispatch': '进攻余粮', 'yield_opt_dispatch': '生息余粮', 'boss': 'Boss'}.get(code[5:], code[5:]) + '）'
    return LABEL.get(code, code)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    mid = sys.argv[1]
    whos = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--who']
    spans = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--span']
    out = os.path.join(HERE, '..', 'out', mid)
    fn = os.path.join(out, 'shadow_donor_gate.tsv')
    lines = open(fn, encoding='utf-8').read().split('\n')
    head = lines[0]
    rows = list(csv.DictReader(lines[1:], delimiter='\t'))
    for r in rows:
        r['t'] = int(r['t'])
        r['c'] = dict(x.split('=', 1) for x in r['cands'].split(';') if '=' in x)
    fire = []
    for r in csv.DictReader((l for l in open(os.path.join(out, 'shadow_underfire.tsv'), encoding='utf-8') if not l.startswith('#')), delimiter='\t'):
        fire.append({k: (v if k in ('bot',) else float(v)) for k, v in r.items()})
    T = []
    P = T.append
    J = {'check': head.lstrip('# ').strip()}
    P(f'# {mid} 调度门槛表（79_help_table.py；影子运行 + 源码判定顺序复刻）')
    P(f'# {head.lstrip("# ").strip()}')
    P('')
    P('A. 按捐方：t>=1500 的相位拍（每 25 拍一次）各落在哪一步')
    by = defaultdict(Counter)
    for r in rows:
        by[r['donor']][r['reason']] += 1
    tot = Counter()
    for b in by:
        tot.update(by[b])
    n = sum(tot.values())
    P(f'   全队 {n} 个相位拍：' + '；'.join(f'{lab(k)} {v}' for k, v in tot.most_common()))
    J['A'] = {'total': dict(tot), 'byDonor': {b: dict(c) for b, c in by.items()}}
    for b in sorted(by, key=lambda x: -sum(by[x].values())):
        c = by[b]
        ts = [r['t'] for r in rows if r['donor'] == b]
        P(f'   {b}: {sum(c.values())} 拍（t={min(ts)}~{max(ts)}）：' + '；'.join(f'{lab(k)} {v}' for k, v in c.most_common()))
    # no-cand 的细分：候选里有没有正在挨打的
    nc = Counter()
    for r in rows:
        if r['reason'] != 'no-cand':
            continue
        codes = Counter(r['c'].values())
        key = '、'.join(f'{lab(k)}×{v}' for k, v in sorted(codes.items(), key=lambda kv: -kv[1])[:3])
        nc[key] += 1
    P('   「没有合格的收方」的相位拍里，各候选卡在哪（前 8 种组合）：')
    for k, v in nc.most_common(8):
        P(f'     {v} 拍：{k}')
    P('')
    P('B. 按收方：身上有敌方真人进攻的决策拍（每 5 拍一个）')
    fb = defaultdict(list)
    for r in fire:
        fb[r['bot']].append(r)
    J['B'] = {}
    for b in sorted(fb, key=lambda x: -len(fb[x])):
        L = fb[b]
        uf = [r for r in L if r['underFire'] == 1]
        dA = [r for r in L if r['doomedA'] == 1]
        dB = [r for r in L if r['doomedB'] == 1 and r['doomedA'] != 1]
        rng = lambda X: f"t={int(min(r['t'] for r in X))}~{int(max(r['t'] for r in X))}" if X else '-'
        mx = max(L, key=lambda r: r['ratio'])
        P(f"   {b}: {len(L)} 拍（{rng(L)}）；够「挨打」线 {len(uf)} 拍；弃子判定 A（挨的兵 >1.65×余额）{len(dA)} 拍（{rng(dA)}）；"
          f"弃子判定 B（t≥4500 且领土 <22% 最大号 且挨的兵 >0.45×余额）{len(dB)} 拍（{rng(dB)}）；挨的兵 / 余额 最高 {mx['ratio']:.2f}（t={int(mx['t'])}，{int(mx['inHumanAtk']):,} 兵对 {int(mx['bal']):,}）")
        J['B'][b] = {'ticks': len(L), 'underFire': len(uf), 'doomedA': len(dA), 'doomedB': len(dB), 'maxRatio': mx['ratio'], 'maxRatioT': int(mx['t'])}
    P('')
    J['C'] = {}
    for w in whos:
        who, t0, t1 = w.split(':')
        t0, t1 = int(t0), int(t1)
        P(f'C. 收方 {who}，t={t0}~{t1}：各捐方的相位拍卡在哪')
        fr = [r for r in fb.get(who, []) if t0 <= r['t'] <= t1]
        if fr:
            P(f"   这段时间 {who} 身上有真人进攻的决策拍 {len(fr)} 个（够挨打线 {sum(1 for r in fr if r['underFire'] == 1)}，弃子 A {sum(1 for r in fr if r['doomedA'] == 1)}，弃子 B {sum(1 for r in fr if r['doomedB'] == 1 and r['doomedA'] != 1)}）")
        agg = defaultdict(Counter)
        allc = Counter()
        for r in rows:
            if not (t0 <= r['t'] <= t1) or r['donor'] == who:
                continue
            if r['reason'].startswith('D:'):
                code = r['reason']
            elif r['reason'].startswith('SENT'):
                code = 'SENT' if r['target'] == who else 'OTHER→' + r['target']
            else:
                cc = r['c'].get(who)
                if cc is None:
                    code = 'ABSENT'
                elif cc.startswith('ok:'):
                    code = 'PCT<min' if r['reason'] == 'PCT<min' and r['target'] == who else 'LOST'
                else:
                    code = cc
            agg[r['donor']][code] += 1
            allc[code] += 1

        def l2(code):
            return ('捐给了 ' + code[6:]) if code.startswith('OTHER→') else lab(code)
        P(f'   合计 {sum(allc.values())} 个相位拍：' + '；'.join(f'{l2(k)} {v}' for k, v in allc.most_common()))
        for b in sorted(agg, key=lambda x: -sum(agg[x].values())):
            c = agg[b]
            dm = [float(r['dMe']) for r in rows if r['donor'] == b and t0 <= r['t'] <= t1]
            bx = [r['boxedIn'] for r in rows if r['donor'] == b and t0 <= r['t'] <= t1 and r['boxedIn'] != '']
            P(f"   {b}（{sum(c.values())} 拍，密度 {min(dm):.0f}~{max(dm):.0f}{'，其中算围死 ' + str(sum(1 for x in bx if x == '1')) + '/' + str(len(bx)) + ' 拍' if bx else ''}）：" + '；'.join(f'{l2(k)} {v}' for k, v in c.most_common()))
        J['C'][w] = {'total': dict(allc), 'byDonor': {b: dict(c) for b, c in agg.items()}}
        P('')
    J['D'] = {}
    for sp in spans:
        t0, t1 = [int(x) for x in sp.split(':')]
        R = [r for r in rows if t0 <= r['t'] <= t1]
        c = Counter(r['reason'] for r in R)
        P(f'D. t={t0}~{t1}：全队 {len(R)} 个相位拍：' + '；'.join(f'{lab(k)} {v}' for k, v in c.most_common()))
        cc = Counter()
        for r in R:
            if r['reason'] == 'no-cand':
                cc.update(r['c'].values())
        P(f"   「没有合格的收方」的 {c.get('no-cand', 0)} 拍里，（捐方, 候选）共 {sum(cc.values())} 对：" + '；'.join(f'{lab(k)} {v}' for k, v in cc.most_common()))
        byd = defaultdict(Counter)
        for r in R:
            byd[r['donor']][r['reason']] += 1
        for b in sorted(byd, key=lambda x: -sum(byd[x].values())):
            dm = [float(r['dMe']) for r in R if r['donor'] == b]
            bx = [r['boxedIn'] for r in R if r['donor'] == b and r['boxedIn'] != '']
            P(f"   {b}（{sum(byd[b].values())} 拍，密度 {min(dm):.0f}~{max(dm):.0f}{'，算围死 ' + str(sum(1 for x in bx if x == '1')) + '/' + str(len(bx)) + ' 拍' if bx else ''}）：" + '；'.join(f'{lab(k)} {v}' for k, v in byd[b].most_common()))
        J['D'][sp] = {'n': len(R), 'reasons': dict(c), 'noCandPairs': dict(cc)}
        P('')
    open(os.path.join(out, 'help_table.txt'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
    json.dump(J, open(os.path.join(out, 'help_table.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n'.join(T))


if __name__ == '__main__':
    main()
