#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""96_enemy_boats.py — 敌方的船靠到我方号身上的记录（发船拍 → 进攻槽第一次出现的采样拍）。R07

用法（在 scripts/ 目录下）：
    python3 96_enemy_boats.py <matchId> [--max-voyage 600]

输入（都在 out/<matchId>/）：
    humans_cmd.tsv   真引擎重放的全场真人逐条指令（60_truth.cjs 之后的 63_replay_ledger.py / 67_troop_flow.mjs 产物）；kind=boat 的行没有目标
    truth_atk.tsv    每 10 拍采样一次的进攻槽（dir=in：from 打我方号 to，troops = 槽里的兵）
    truth_players.tsv

口径：humans_cmd.tsv 里发船指令不带目标。这里用进攻槽倒推：
    一条敌方发船指令（发船拍 T、玩家 P、带兵 N）之后 (T, T+max-voyage] 内，P 对某个我方号 b 的进攻槽「新出现」
    （上一采样拍没有 P→b 的槽），并且这个新槽出现前 12 拍内 P 没有对 b 的陆上进攻指令，就把这条船记到 b 头上。
    船在海上每 5 拍掉 1/128 的兵（引擎 boats.js decayBoats L360-366：t%5==3 时 `v - max(1, v >> 7)`），所以发船带兵 N 的船在 t 拍靠岸时应有约 N×(127/128)^((t−T)/5)；
    新槽第一次采样到的兵不能比这个数多（留 3% 的余量：采样拍和靠岸拍最多差 10 拍）。
    每个新槽在满足条件的船里取「应有的兵」和采样值最接近的那一条；一条船只配一次。
    配不上的船 = 去了别处（无主地 / 别的队 / 自己的地）、并进了已有的槽，或途中沉了。
输出：out/<matchId>/enemy_boats.txt
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    max_voy = 600
    if '--max-voyage' in args:
        max_voy = int(args[args.index('--max-voyage') + 1])
    out_dir = os.path.join(HERE, '..', 'out', mid)
    players = {}
    squad = {}
    for r in csv.DictReader(open(os.path.join(out_dir, 'truth_players.tsv'), encoding='utf-8'), delimiter='\t'):
        p = int(r['p'])
        players[p] = (r['name'], r['team'])
        if r.get('squad'):
            squad[p] = r['name'].replace('[APEX] ', '')
    boats = []      # 敌方真人的发船指令
    land = {}       # (P, b) -> [t...] 陆上进攻指令的落地拍
    for r in csv.DictReader(open(os.path.join(out_dir, 'humans_cmd.tsv'), encoding='utf-8'), delimiter='\t'):
        p = int(r['p'])
        if p in squad:
            continue
        if r['kind'] == 'boat':
            boats.append({'t': int(r['t']), 'p': p, 'pct': int(r['pct']), 'troops': int(r['troops']), 'fee': int(r['fee']),
                          'b0': int(r['b0']), 'terr': int(r['terr'])})
        elif r['kind'] == 'attack' and r['tt'] == 'H' and int(r['target']) in squad:
            land.setdefault((p, int(r['target'])), []).append(int(r['t']))
    slots = {}      # (P, b) -> {t: troops}
    for r in csv.DictReader(open(os.path.join(out_dir, 'truth_atk.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['dir'] != 'in':
            continue
        slots.setdefault((int(r['from']), int(r['to'])), {})[int(r['t'])] = int(r['troops'])
    # 新出现的槽（上一采样拍没有），且出现前 12 拍内没有 P→b 的陆上进攻指令
    fresh = []
    for (p, b), d in slots.items():
        if p in squad or p not in players:
            continue
        for t in sorted(d):
            if (t - 10) in d:
                continue
            if any(t - 12 < x <= t for x in land.get((p, b), [])):
                continue
            # 这个槽连续存在到哪一拍、峰值
            t1 = t
            peak = d[t]
            while (t1 + 10) in d:
                t1 += 10
                peak = max(peak, d[t1])
            fresh.append({'t': t, 'p': p, 'b': b, 'troops': d[t], 't1': t1, 'peak': peak, 'used': False})
    fresh.sort(key=lambda x: x['t'])
    boats.sort(key=lambda x: x['t'])
    rows = []
    for bt in boats:
        bt['used'] = False
    for f in fresh:
        best = None
        for bt in boats:
            if bt['used'] or bt['p'] != f['p'] or not (bt['t'] < f['t'] <= bt['t'] + max_voy):
                continue
            expect = bt['troops'] * (127 / 128) ** ((f['t'] - bt['t']) / 5)
            if expect < 0.97 * f['troops']:
                continue
            gap = abs(expect - f['troops'])
            if best is None or gap < best[0]:
                best = (gap, bt, expect)
        if best:
            best[1]['used'] = True
            f['used'] = True
            f['expect'] = best[2]
            rows.append((best[1], f))
    rows.sort(key=lambda x: x[0]['t'])
    L = [f'# {mid} 敌方的船靠到我方号身上（96_enemy_boats.py；发船指令来自 humans_cmd.tsv，靠岸用 truth_atk.tsv 的进攻槽倒推；航行上限 {max_voy} 拍）',
         f'# 全场敌方真人发船 {len(boats)} 条、带兵合计 {fmt(sum(b["troops"] for b in boats))}；配到我方号身上的 {len(rows)} 条、带兵合计 {fmt(sum(b["troops"] for b, _ in rows))}',
         '# 「新槽首次采样」= 靠岸后第一次被 10 拍一次的采样看到的槽内兵（已经打掉一部分）；「槽持续到」= 这个槽连续存在的最后一个采样拍（期间如果又有陆上进攻并进来，峰值会更高）',
         '',
         'A. 逐条（按发船拍）',
         '发船拍\t发船方\tpct\t带兵（船费）\t发船前 余额 / 领土\t落到谁身上\t新槽首次采样拍（距发船）\t按海上损耗应有的兵\t新槽首次采样的兵\t槽持续到 / 峰值']
    for bt, f in rows:
        nm, tm = players[bt['p']]
        L.append(f"{bt['t']}\t{nm}#{bt['p']}[T{tm}]\t{bt['pct']}\t{fmt(bt['troops'])}（{fmt(bt['fee'])}）\t{fmt(bt['b0'])} / {fmt(bt['terr'])}\t{squad[f['b']]}\t"
                 f"{f['t']}（{f['t'] - bt['t']}）\t{fmt(f['expect'])}\t{fmt(f['troops'])}\t{f['t1']} / {fmt(f['peak'])}")
    L.append('')
    L.append('B. 按我方号合计')
    per = {}
    for bt, f in rows:
        per.setdefault(f['b'], []).append((bt, f))
    for b, xs in sorted(per.items(), key=lambda kv: kv[1][0][0]['t']):
        who = {}
        for bt, f in xs:
            k = bt['p']
            who.setdefault(k, [0, 0, []])
            who[k][0] += 1
            who[k][1] += bt['troops']
            who[k][2].append(bt['t'])
        parts = [f"{players[k][0]}#{k}[T{players[k][1]}] {v[0]} 条 {fmt(v[1])} 兵（发船拍 {'、'.join(str(t) for t in v[2])}）" for k, v in who.items()]
        L.append(f"  {squad[b]}：{len(xs)} 条船、带兵合计 {fmt(sum(bt['troops'] for bt, _ in xs))} | " + '；'.join(parts))
    if not per:
        L.append('  （没有配到我方号身上的船）')
    L.append('')
    L.append('C. 没有配上陆上进攻指令、也没有配上船的新槽（多半是船在采样间隔里靠岸又被并进了已有的槽，或对方的盟友转交；只列峰值 ≥ 20,000 的）')
    n = 0
    for f in fresh:
        if f['used'] or f['peak'] < 20000:
            continue
        nm, tm = players[f['p']]
        L.append(f"  t={f['t']} {nm}#{f['p']}[T{tm}] → {squad[f['b']]}：首次采样 {fmt(f['troops'])}，持续到 {f['t1']}，峰值 {fmt(f['peak'])}")
        n += 1
    if n == 0:
        L.append('  （无）')
    out = os.path.join(out_dir, 'enemy_boats.txt')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
