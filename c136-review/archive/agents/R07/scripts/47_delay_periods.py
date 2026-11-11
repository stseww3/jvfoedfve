#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""47_delay_periods.py — R07：指令延迟与执行延迟的四时段账（统筹广播 0007-② 的口径）。

把已有的几份输出按 0~600 / 600~1500 / 1500~3000 / 3000+ 四个时段重新合计，不重演：
  shadow_cmds.tsv、shadow_log.txt   65_shadow.mjs：影子（同一份策略源码、没有延迟）每拍想发的指令、影子自己的 cmds 计数
  truth_cmd.tsv                     60_truth.cjs：录像里我方每条指令的落地拍
  humans_cmd.tsv                    60_truth.cjs：落地指令的发兵 / 手续费 / 目标类别（N 无主地、A 内置 AI、H 真人、L 已离开的席位）
  tick_net.tsv                      67_troop_flow.mjs：每 10 拍每号的利息地租 / 退回的兵 / 挨打掉
  same_tick_batches.json            81_same_tick_batches.py：同一号同一拍落地 ≥3 条的批
  side_flow_tp.json / side_flow.json 74_side_flow.mjs：各组分段流水（并成四段做对照；切点取最近的）
  shadow_early.tsv                  65_shadow.mjs：t<1500 每个决策拍的归类（出手 / 卡在哪一项留底 / 价高 / 猎杀规则）
  repeat_sends.json                 72_repeat_sends.py：同一目标连发的组（间隔 ≤12 拍）
  bundles/<id>/in_game.log          真号日志 [HL-TICK] 里的 cmds 计数（策略自己数的「被受理的指令」）

配对规则和 64_cmd_loss.py 相同：同号、同种类、同 pct、同目标；每条落地指令配「发令拍 ≤ 落地拍、还没配过的最晚一条影子指令」
（延迟的下限），另按先发先到再配一遍（上限）。目标是无主地却配不上的进攻，再按「同 pct、任意目标」配一次 = 改投无主地。
延迟按影子的发令拍归时段。影子的发令拍是「策略在没有延迟的局面上想发的那一拍」，真号当时不一定在同一拍发——所以这是
「意图 → 落地」的延迟，不是纯网络延迟；两边 pct 逐条相同的才算配上。

用法：python3 47_delay_periods.py <matchId>
输出：out/<matchId>/delay_periods.txt、delay_periods.json
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/agent/repos/c136-data'
PERIODS = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
PNAME = ['0~600', '600~1500', '1500~3000', '3000+']
FUNNEL_CUTS = [0, 630, 1530, 3060, 10 ** 9]


LATE_MIN = 60


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def per_of(t):
    for i, (a, b) in enumerate(PERIODS):
        if a <= t < b:
            return i
    return len(PERIODS) - 1


def q(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def fmt(x):
    return '-' if x is None else f'{int(round(x)):,}'


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    out = os.path.join(HERE, '..', 'out', mid)
    sh = load(os.path.join(out, 'shadow_cmds.tsv'))
    tr = load(os.path.join(out, 'truth_cmd.tsv'))
    hc = [r for r in load(os.path.join(out, 'humans_cmd.tsv')) if r.get('squad') == '1']
    if not sh or not tr:
        print('缺 shadow_cmds.tsv / truth_cmd.tsv：先跑 60_truth.cjs 和 65_shadow.mjs')
        sys.exit(1)
    bots = sorted(set(r['bot'] for r in sh) | set(r['bot'] for r in tr if r['bot']))
    end_t = max([int(r['tick']) for r in tr] + [int(r['t']) for r in sh])

    # ---- 配对（同 64_cmd_loss.py）
    want = defaultdict(list)
    for r in sh:
        if r['kind'] in ('attack', 'donate'):
            want[r['bot']].append({'t': int(r['t']), 'kind': r['kind'], 'pct': int(r['pct']), 'target': int(r['target']), 'tname': r['targetName'],
                                   'troops': int(float(r['troops'] or 0)), 'hit': None, 'fifo': None, 're': False})
    got = defaultdict(list)
    for r in tr:
        if not r['bot'] or r['bot'] not in bots:
            continue
        kind = {'attack': 'attack', 'donate': 'donate', 'don': 'donate', 'atk': 'attack'}.get(r['kind'])
        if kind is None:
            continue
        got[r['bot']].append({'T': int(r['tick']), 'kind': kind, 'pct': int(r['a']), 'target': int(r['b']), 'hit': None, 're': False,
                              'tname': r.get('target', ''), 'b0': int(float(r.get('bal_m1') or 0)), 'b1': int(float(r.get('bal_p1') or 0))})
    lags = defaultdict(lambda: [[] for _ in PERIODS])       # bot -> period -> [lag]（精确配上）
    lags_re = [[] for _ in PERIODS]                         # 改投无主地（启发式配对）的延迟
    lags_fifo = [[] for _ in PERIODS]
    n_exact = n_re = 0
    for b in bots:
        W, G = want[b], got[b]
        idx = defaultdict(list)
        for w in W:
            idx[(w['kind'], w['pct'], w['target'])].append(w)
        used = set()
        for g in G:
            for w in idx.get((g['kind'], g['pct'], g['target']), []):
                if id(w) not in used and w['t'] <= g['T']:
                    used.add(id(w))
                    lags_fifo[per_of(w['t'])].append(g['T'] - w['t'])
                    break
        for g in G:
            cands = [w for w in idx.get((g['kind'], g['pct'], g['target']), []) if w['hit'] is None and w['t'] <= g['T']]
            if cands:
                w = cands[-1]
                w['hit'] = g['T']
                g['hit'] = w['t']
                lags[b][per_of(w['t'])].append(g['T'] - w['t'])
                n_exact += 1
        for g in G:
            if g['hit'] is not None or g['kind'] != 'attack' or g['target'] != 512:
                continue
            cands = [w for w in W if w['hit'] is None and w['kind'] == 'attack' and w['pct'] == g['pct'] and w['t'] <= g['T']]
            if cands:
                w = cands[-1]
                w['hit'] = g['T']
                w['re'] = True
                g['hit'] = w['t']
                g['re'] = True
                g['intent'] = w['tname']
                lags_re[per_of(w['t'])].append(g['T'] - w['t'])
                n_re += 1

    L = []
    P = L.append
    J = {'matchId': mid, 'periods': PNAME, 'delay': {}, 'funnel': {}, 'whiff': {}, 'repeat': {}}
    P(f'# {mid} 指令延迟与执行延迟的四时段账（47_delay_periods.py；配对规则同 64_cmd_loss.py：精确配上 {n_exact} 条、改投无主地 {n_re} 条）')
    P('# 延迟 = 录像落地拍 − 影子发令拍（按影子发令拍归时段；最晚优先 = 下限，先发先到 = 上限）。影子没有延迟，真号当时不一定在同一拍发令。')
    P('')
    P('A. 全队四时段：影子想发（进攻 + 捐兵）| 录像落地（按落地拍）| 精确配上 | 延迟 P50 / P90 / 最大（下限）| P50 / P90（上限）| ≥21 拍 | ≥35 拍 | ≥90 拍 | 改投无主地（同 pct、目标不同，启发式）条 · P50 / P90 / 最大')
    for i, nm in enumerate(PNAME):
        a, b_ = PERIODS[i]
        n_want = sum(1 for b in bots for w in want[b] if a <= w['t'] < b_)
        n_got = sum(1 for b in bots for g in got[b] if a <= g['T'] < b_)
        xs = [x for b in bots for x in lags[b][i]]
        fx = lags_fifo[i]
        P(f"  {nm}\t{n_want}\t{n_got}\t{len(xs)}\t{fmt(q(xs, 0.5))} / {fmt(q(xs, 0.9))} / {fmt(max(xs) if xs else None)}\t{fmt(q(fx, 0.5))} / {fmt(q(fx, 0.9))}\t"
          f"{sum(1 for x in xs if x >= 21)}\t{sum(1 for x in xs if x >= 35)}\t{sum(1 for x in xs if x >= 90)}\t"
          f"{len(lags_re[i])} · {fmt(q(lags_re[i], 0.5))} / {fmt(q(lags_re[i], 0.9))} / {fmt(max(lags_re[i]) if lags_re[i] else None)}")
        J['delay'][nm] = {'want': n_want, 'landed': n_got, 'matched': len(xs), 'p50': q(xs, 0.5), 'p90': q(xs, 0.9), 'max': max(xs) if xs else None,
                          'p50fifo': q(fx, 0.5), 'p90fifo': q(fx, 0.9), 'ge21': sum(1 for x in xs if x >= 21), 'ge35': sum(1 for x in xs if x >= 35), 'ge90': sum(1 for x in xs if x >= 90),
                          'retargetN': len(lags_re[i]), 'retargetP50': q(lags_re[i], 0.5), 'retargetP90': q(lags_re[i], 0.9)}
    P('')
    P('B. 各号四时段延迟（只算精确配上的）：条数 · P50 / P90 / 最大（下限）；最后一列 = 全程最小延迟（这个客户端的底延迟）/ P50')
    P('号\t' + '\t'.join(PNAME) + '\t全程最小 / P50')
    J['perBot'] = {}
    for b in bots:
        cells = []
        allx = []
        for i in range(len(PERIODS)):
            xs = lags[b][i]
            allx += xs
            cells.append('.' if not xs else f"{len(xs)} · {fmt(q(xs, 0.5))} / {fmt(q(xs, 0.9))} / {fmt(max(xs))}")
        P(f"  {b}\t" + '\t'.join(cells) + f"\t{fmt(min(allx) if allx else None)} / {fmt(q(allx, 0.5))}")
        J['perBot'][b] = {'min': min(allx) if allx else None, 'p50': q(allx, 0.5), 'p90': q(allx, 0.9), 'max': max(allx) if allx else None, 'n': len(allx)}

    # ---- 漏斗：影子 cmds / 真号日志 cmds / 录像落地（全部种类），按 90 拍快照切
    rx = re.compile(r'\[([A-Za-z0-9_]+)\] \[HL-TICK\] t=(\d+) .*?cmds=(\d+)')

    def read_cmds(path):
        d = defaultdict(dict)
        if os.path.exists(path):
            for line in open(path, encoding='utf-8', errors='replace'):
                m = rx.search(line)
                if m:
                    d[m.group(1)][int(m.group(2))] = int(m.group(3))
        return d
    real = read_cmds(os.path.join(DATA, 'bundles', mid, 'in_game.log'))
    shad = read_cmds(os.path.join(out, 'shadow_log.txt'))

    def at_or_before(series, t):
        ks = [k for k in series if k <= t]
        return series[max(ks)] if ks else 0
    P('')
    P('C. 漏斗（全部种类的指令；按 90 拍快照切，所以分界是 630 / 1530 / 3060）：影子受理的 cmds | 真号日志的 cmds | 录像落地 | 真号 ÷ 影子 | 落地 ÷ 真号 | 其中捐兵：影子想发 / 录像落地（服务器按配额拒收的捐兵不进录像）| 去掉捐兵后：真号 / 落地')
    P('   影子 cmds = 没有延迟时策略会发出并被引擎接受的条数；真号 cmds = 策略自己数的被受理条数（[HL-TICK] cmds=）；只有两边都有快照的号才计入')
    all_landed = defaultdict(list)
    don_want = defaultdict(list)
    don_got = defaultdict(list)
    for r in sh:
        if r['kind'] == 'donate':
            don_want[r['bot']].append(int(r['t']))
    for r in tr:
        if r['bot'] and r['kind'] in ('donate', 'don'):
            don_got[r['bot']].append(int(r['tick']))
    for r in tr:
        if r['bot'] and r['kind'] in ('attack', 'atk', 'donate', 'don', 'boat', 'boatTo', 'chase', 'recall', 'retreat'):
            all_landed[r['bot']].append(int(r['tick']))
    for i in range(len(FUNNEL_CUTS) - 1):
        a, b_ = FUNNEL_CUTS[i], FUNNEL_CUTS[i + 1]
        s_n = r_n = l_n = dw = dg = 0
        nb = 0
        for b in bots:
            if b not in real or b not in shad:
                continue
            last_real = max(real[b])
            hi = min(b_, last_real)      # 真号最后一个快照之后没有计数
            if hi <= a:
                continue
            nb += 1
            s_n += at_or_before(shad[b], hi) - at_or_before(shad[b], a)
            r_n += at_or_before(real[b], hi) - at_or_before(real[b], a)
            l_n += sum(1 for t in all_landed[b] if a < t <= hi)
            dw += sum(1 for t in don_want[b] if a < t <= hi)
            dg += sum(1 for t in don_got[b] if a < t <= hi)
        nm = f"{a}~{b_ if b_ < 10 ** 9 else '末'}"
        P(f"  {nm}\t{s_n}\t{r_n}\t{l_n}\t{(r_n / s_n if s_n else 0):.2f}\t{(l_n / r_n if r_n else 0):.2f}\t{dw} / {dg}\t{r_n - dw} / {l_n - dg}\t（{nb} 个号）")
        J['funnel'][nm] = {'shadow': s_n, 'real': r_n, 'landed': l_n, 'bots': nb, 'donWant': dw, 'donLanded': dg}

    P('   各号（影子 / 真号 / 落地）：')
    for b in bots:
        if b not in real or b not in shad:
            continue
        cells = []
        last_real = max(real[b])
        for i in range(len(FUNNEL_CUTS) - 1):
            a, b_ = FUNNEL_CUTS[i], FUNNEL_CUTS[i + 1]
            hi = min(b_, last_real)
            if hi <= a:
                cells.append('.')
                continue
            cells.append(f"{at_or_before(shad[b], hi) - at_or_before(shad[b], a)} / {at_or_before(real[b], hi) - at_or_before(real[b], a)} / {sum(1 for t in all_landed[b] if a < t <= hi)}")
        P(f"    {b}\t" + '\t'.join(cells) + f"\t（最后一个快照 t={last_real}）")

    # ---- 迟到落空
    P('')
    P('D. 迟到落空（按落地拍归时段）：空指令 = 落地时余额没动（没有可推进的边界，不扣兵不收费）；改投无主地 = 影子想打别人、落地时记成打无主地')
    P('   时段 | 我方落地的进攻 条 / 发兵 | 其中空指令 条（占比）| 改投无主地 条 / 发兵 | 影子想打内置 AI 条 / 约兵（按发令拍）| 落在内置 AI 身上 条 / 兵 | 落在无主地 条 / 兵 | 发兵 → 退回（退回 ÷ 发兵）')
    tn = load(os.path.join(out, 'tick_net.tsv'))
    key_re = {}
    for b in bots:
        for g in got[b]:
            if g.get('re'):
                key_re[(b, g['T'], g['pct'])] = key_re.get((b, g['T'], g['pct']), 0) + 1
    for i, nm in enumerate(PNAME):
        a, b_ = PERIODS[i]
        rows = [r for r in hc if r['kind'] == 'attack' and a <= int(r['t']) < b_]
        n = len(rows)
        troops = sum(int(float(r['troops'] or 0)) for r in rows)
        noop = [r for r in rows if int(float(r['spent'] or 0)) == 0]
        re_n = re_tr = 0
        seen = defaultdict(int)
        for r in rows:
            b = r['name'].split('] ')[-1].strip()
            k = (b, int(r['t']), int(r['pct']))
            if r['tt'] == 'N' and seen[k] < key_re.get(k, 0):
                seen[k] += 1
                re_n += 1
                re_tr += int(float(r['troops'] or 0))
        w_ai = [w for b in bots for w in want[b] if a <= w['t'] < b_ and w['kind'] == 'attack' and w['tname'].startswith('AI#')]
        on_ai = [r for r in rows if r['tt'] in ('A', 'L')]
        on_n = [r for r in rows if r['tt'] == 'N']
        refund = sum(int(float(r['refund'] or 0)) for r in tn if a <= int(r['t0']) < b_)
        P(f"  {nm}\t{n} / {fmt(troops)}\t{len(noop)}（{(100 * len(noop) / n if n else 0):.0f}%）\t{re_n} / {fmt(re_tr)}\t{len(w_ai)} / {fmt(sum(w['troops'] for w in w_ai))}\t"
          f"{len(on_ai)} / {fmt(sum(int(float(r['troops'] or 0)) for r in on_ai))}\t{len(on_n)} / {fmt(sum(int(float(r['troops'] or 0)) for r in on_n))}\t"
          f"{fmt(troops)} → {fmt(refund)}（{(100 * refund / troops if troops else 0):.0f}%）")
        J['whiff'][nm] = {'atkN': n, 'troops': troops, 'noop': len(noop), 'retargetN': re_n, 'retargetTroops': re_tr, 'wantAiN': len(w_ai), 'wantAiTroops': sum(w['troops'] for w in w_ai),
                          'onAiN': len(on_ai), 'onAiTroops': sum(int(float(r['troops'] or 0)) for r in on_ai), 'onNeutralN': len(on_n), 'refund': refund}

    # ---- 重复下单与同拍批
    P('')
    P('E. 确认窗内重复下单与同拍清仓批（按落地拍归时段）')
    P('   时段 | 同一号同一拍 ≥3 条的批：个数 / 条数 / 发兵 | 其中把余额打掉 ≥50% 的批 个数 / 发兵（批前余额合计 → 批后）| 同一目标连发的组：个数 / 条数 / 第 2 条起的兵 / 第 2 条起的手续费 / 超出吃光所需')
    stb = {}
    p_stb = os.path.join(out, 'same_tick_batches.json')
    if os.path.exists(p_stb):
        stb = json.load(open(p_stb, encoding='utf-8'))
    rs = {}
    p_rs = os.path.join(out, 'repeat_sends.json')
    if os.path.exists(p_rs):
        rs = json.load(open(p_rs, encoding='utf-8'))
    for i, nm in enumerate(PNAME):
        a, b_ = PERIODS[i]
        bs = [x for x in stb.get('batches', []) if a <= x['t'] < b_]
        big = [x for x in bs if x.get('b0', 0) > 0 and (x['b0'] - x['b1']) >= 0.5 * x['b0']]
        gs = [x for x in rs.get('groups', []) if a <= x['t0'] < b_]
        P(f"  {nm}\t{len(bs)} / {sum(x['n'] for x in bs)} / {fmt(sum(x.get('troops', 0) for x in bs))}\t"
          f"{len(big)} / {fmt(sum(x.get('troops', 0) for x in big))}（{fmt(sum(x['b0'] for x in big))} → {fmt(sum(x['b1'] for x in big))}）\t"
          f"{len(gs)} / {sum(x['n'] for x in gs)} / {fmt(sum(x.get('repeatTroops', 0) for x in gs))} / {fmt(sum(x.get('repeatFee', 0) for x in gs))} / {fmt(sum(max(0, x.get('over', 0) or 0) for x in gs))}")
        J['repeat'][nm] = {'batches': len(bs), 'batchCmds': sum(x['n'] for x in bs), 'batchTroops': sum(x.get('troops', 0) for x in bs), 'bigBatches': len(big), 'bigTroops': sum(x.get('troops', 0) for x in big),
                           'groups': len(gs), 'groupCmds': sum(x['n'] for x in gs), 'repeatTroops': sum(x.get('repeatTroops', 0) for x in gs), 'repeatFee': sum(x.get('repeatFee', 0) for x in gs),
                           'over': sum(max(0, x.get('over', 0) or 0) for x in gs)}
    if stb.get('batches'):
        big_all = [x for x in stb['batches'] if x.get('b0', 0) > 0 and (x['b0'] - x['b1']) >= 0.5 * x['b0']]
        if big_all:
            P('   把余额打掉 ≥50% 的批：' + '；'.join(f"t={x['t']} {x['bot']} ×{x['n']}（{fmt(x['b0'])} → {fmt(x['b1'])}，−{100 * (x['b0'] - x['b1']) / x['b0']:.0f}%）" for x in big_all))
    # ---- 各组对照：把 74_side_flow.mjs 已有的分段表并成四段（取离 600 / 1500 / 3000 最近的切点，不重演）
    sf = None
    for nm_sf in ('side_flow_p4.json', 'side_flow_tp.json', 'side_flow.json'):
        p_sf = os.path.join(out, nm_sf)
        if os.path.exists(p_sf):
            sf = json.load(open(p_sf, encoding='utf-8'))
            sf_name = nm_sf
            break
    if sf and sf.get('phases'):
        phs = sf['phases']
        cuts = sorted(set([ph['t0'] for ph in phs] + [ph['t1'] for ph in phs]))
        bounds = [cuts[0]] + [min(cuts, key=lambda c: abs(c - x)) for x in (600, 1500, 3000)] + [cuts[-1]]
        P('')
        P(f"F. 各组对照（{sf_name} 的分段并成四段，切点取离 600 / 1500 / 3000 最近的 {bounds[1]} / {bounds[2]} / {bounds[3]}）：")
        P('   组 | 期初人数 | 进攻 条（无主地 / 内置 AI / 真人）| 发兵 | 退回（÷ 发兵）| 每人打内置 AI 的兵 | 领土 期初→期末')
        J['groups'] = {}
        for i in range(4):
            a, b_ = bounds[i], bounds[i + 1]
            sel = [ph for ph in phs if a <= ph['t0'] and ph['t1'] <= b_]
            if not sel:
                continue
            lab = f"{a}~{b_}"
            P(f"  {lab}")
            J['groups'][lab] = {}
            for gname in sel[0]['row']:
                rows = [ph['row'][gname] for ph in sel if gname in ph['row']]
                tot = {k: sum(r.get(k, 0) or 0 for r in rows) for k in ('atkN', 'atkNn', 'atkNa', 'atkNh', 'tN', 'tA', 'tH', 'refund', 'eco')}
                sent = tot['tN'] + tot['tA'] + tot['tH']
                heads = max(1, rows[0].get('n0') or 1)
                P(f"    {gname}\t{rows[0].get('n0')}\t{tot['atkN']}（{tot['atkNn']} / {tot['atkNa']} / {tot['atkNh']}）\t{fmt(sent)}\t{fmt(tot['refund'])}（{(100 * tot['refund'] / sent if sent else 0):.0f}%）\t"
                  f"{fmt(tot['tA'] / heads)}\t{fmt(rows[0]['terr0'])}→{fmt(rows[-1]['terr1'])}")
                J['groups'][lab][gname] = {'n0': rows[0].get('n0'), 'atkN': tot['atkN'], 'sent': sent, 'refund': tot['refund'], 'tA': tot['tA'], 'terr0': rows[0]['terr0'], 'terr1': rows[-1]['terr1'], 'eco': tot['eco']}
    # ---- t<1500 的决策拍归类（65_shadow.mjs 的 shadow_early.tsv），按 300~600 / 600~1500 合计
    er = load(os.path.join(out, 'shadow_early.tsv'))
    if er:
        def layer(scene, cls):
            if cls.startswith('出手') or cls == '有指令':
                return '出手'
            if cls.startswith('只打无主地'):
                return '只打无主地 / 其他指令'
            if 'safeFinite' in cls:
                return '留底：safeFinite（' + ('参照我方队友' if '我方队友' in cls else '参照敌方真人' if '敌方真人' in cls else '参照其他') + '）'
            if cls.startswith('dpKeep'):
                return '留底：dpKeep'
            if cls.startswith('价格项'):
                return '留底：价格项'
            if cls.startswith('peopleFloor'):
                return '留底：peopleFloor'
            if '留底由这一项定' in cls:
                tail = cls.split('留底由这一项定：')[-1]
                if 'defenseNeed' in tail:
                    return '留底：defenseNeed（' + ('参照我方队友' if '我方队友' in tail else '参照敌方真人' if '敌方真人' in tail else '其他') + '）'
                if 'keepCap' in tail:
                    return '留底：keepCap×100×领土 封顶'
                if '价格留底' in tail:
                    return '留底：价格留底（reserve）'
                if 'dpKeep' in tail:
                    return '留底：dpKeep'
                if 'peopleSafe' in tail:
                    return '留底：safeP×peopleSafe'
                return '留底：其他'
            if 'preyKill' in cls:
                return '猎杀规则：一次吃不光就不发（preyKill）'
            if '都不让打' in cls:
                return '不让打（单价高于出价 / 没有动机）'
            if '四周只有队友' in cls:
                return '四周只有队友'
            return '过了留底但没发（need≤0 / 不够一条 / 没有空槽）'
        P('')
        P('G. t<1500 的决策拍归类（影子；shadow_early.tsv）：场景 × 时段：决策拍 | 出手 | 各类零指令（留底 = winFloor / floorFor 的哪一项把可用兵压到发不出）')
        J['early'] = {}
        for (a, b_) in ((300, 600), (600, 1500)):
            for scene in ('AI邻居', '只剩真人'):
                rows = [r for r in er if a <= int(r['t']) < b_ and r['scene'] == scene]
                if not rows:
                    continue
                cnt = defaultdict(int)
                who = defaultdict(lambda: defaultdict(int))
                for r in rows:
                    k = layer(scene, r['cls'])
                    cnt[k] += 1
                    who[k][r['bot']] += 1
                floor_n = sum(v for k, v in cnt.items() if k.startswith('留底'))
                P(f"  {a}~{b_} {'身边有内置 AI' if scene == 'AI邻居' else '身边只剩敌方真人（没有 AI、没有无主地）'}：{len(rows)} 个决策拍；出手 {cnt.get('出手', 0)}；留底卡住合计 {floor_n}（{100 * floor_n / len(rows):.0f}%）")
                for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
                    if k == '出手':
                        continue
                    tops = '、'.join(f"{b} {n}" for b, n in sorted(who[k].items(), key=lambda kv: -kv[1])[:5])
                    P(f"      {k}：{v}（{tops}）")
                J['early'][f"{a}~{b_} {scene}"] = {'dec': len(rows), 'fired': cnt.get('出手', 0), 'floor': floor_n, 'cls': dict(cnt)}
    # ---- 迟到 ≥60 拍的落地指令：按（号，落地拍）并成一批
    late = defaultdict(list)
    for b in bots:
        for g in got[b]:
            if g['hit'] is not None and not g['re'] and g['T'] - g['hit'] >= LATE_MIN:
                late[(g['T'], b)].append(g)
    P('')
    P(f'H. 迟到 ≥{LATE_MIN} 拍才落地的指令（精确配上的；延迟按下限）：按（落地拍，号）并批 | 条数 | 影子发令拍（最早~最晚）| 延迟（最小~最大）| 指令 | 落地前一拍余额 → 落地后一拍余额')
    J['late'] = []
    if not late:
        P('  没有')
    tot_n = 0
    for (T, b), gs in sorted(late.items()):
        it = [g['hit'] for g in gs]
        kinds = defaultdict(int)
        for g in gs:
            kinds[f"{'捐兵' if g['kind'] == 'donate' else '进攻'} {g['pct']}→{'无主地' if g['target'] == 512 else g['tname']}"] += 1
        ks = '、'.join(f"{k}{' ×' + str(n) if n > 1 else ''}" for k, n in kinds.items())
        same_tick = sum(1 for g in got[b] if g['T'] == T)
        P(f"  t={T} {b}\t{len(gs)} 条（同拍一共落地 {same_tick} 条）\t{min(it)}~{max(it)}\t{T - max(it)}~{T - min(it)}\t{ks}\t{gs[0]['b0']:,} → {gs[0]['b1']:,}")
        J['late'].append({'T': T, 'bot': b, 'n': len(gs), 'sameTick': same_tick, 'intentMin': min(it), 'intentMax': max(it), 'b0': gs[0]['b0'], 'b1': gs[0]['b1']})
        tot_n += len(gs)
    if late:
        byb = defaultdict(int)
        for (T, b), gs in late.items():
            byb[b] += len(gs)
        P(f"  合计 {tot_n} 条 / {len(late)} 批；各号：" + '、'.join(f"{b} {n}" for b, n in sorted(byb.items(), key=lambda kv: -kv[1])))
    with open(os.path.join(out, 'delay_periods.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    with open(os.path.join(out, 'delay_periods.json'), 'w', encoding='utf-8') as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print('\n'.join(L))


if __name__ == '__main__':
    main()
