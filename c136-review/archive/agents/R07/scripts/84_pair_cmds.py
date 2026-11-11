#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""84_pair_cmds.py — 指定的人在指定窗口里「挨了谁的兵」/「把兵发给了谁」的逐对合计。R07

用法（在 scripts/ 目录下）：
    python3 84_pair_cmds.py <matchId> [--on 谁[:t0:t1]]... [--by 谁[:t0:t1]]... [--tag 名字]

    谁 = 我方号名（kaito9）、玩家编号（29）或名字里的一段（Norman）。不给窗口就是全程。

输入：out/<matchId>/humans_cmd.tsv（74_side_flow.mjs 按真引擎重放记下的全场真人逐条指令：
      t、p、名字、队、是否我方号、kind、pct、tt（N 无主地 / A 内置 AI / L 已离开的真人席位 / H 真人 / B 船 / D 捐款）、
      target、发令前后余额 b0 / b1、spent、fee、troops（发出的兵）、发令方领土、目标当时领土 / 余额、recv（捐款到账））
      与 truth_players.tsv（编号 → 名字 / 队）。
口径：
  --on：目标是这个人的陆上进攻（tt=H 或 L），按进攻方合计条数、发兵、手续费、pct 范围、拍号范围、最重的一条；
        另列别人捐给他的捐款（tt=D）。船不算（船的落点要看 76_boat_targets.mjs）。
  --by：这个人发出的全部指令，按（种类, 目标）合计条数、发兵、手续费、拍号范围；捐款列到账（recv）。
输出：out/<matchId>/pair_cmds[_<tag>].txt
"""
import csv
import os
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    on, by, tag = [], [], ''
    i = 1
    while i < len(args):
        if args[i] == '--on':
            on.append(args[i + 1]); i += 2
        elif args[i] == '--by':
            by.append(args[i + 1]); i += 2
        elif args[i] == '--tag':
            tag = args[i + 1]; i += 2
        else:
            i += 1
    out_dir = os.path.join(HERE, '..', 'out', mid)
    players = {}
    with open(os.path.join(out_dir, 'truth_players.tsv'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            players[int(r['p'])] = r
    rows = []
    with open(os.path.join(out_dir, 'humans_cmd.tsv'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            for k in ('t', 'p', 'pct', 'target', 'b0', 'b1', 'spent', 'fee', 'troops', 'terr', 'tTerr', 'tBal', 'recv'):
                r[k] = int(float(r[k] or 0))
            r['_i'] = len(rows)
            rows.append(r)

    def label(p):
        r = players.get(p)
        if not r:
            return f'AI#{p}'
        star = '*' if r.get('squad') else ''
        return f"{star}{r['name']}#{p}[T{r['team']}]"

    def resolve(spec):
        parts = spec.split(':')
        who = parts[0]
        t0 = int(parts[1]) if len(parts) > 1 and parts[1] != '' else 0
        t1 = int(parts[2]) if len(parts) > 2 and parts[2] != '' else 10 ** 9
        cand = []
        if who.isdigit():
            cand = [int(who)]
        else:
            cand = [p for p, r in players.items() if r.get('squad') == who]
            if not cand:
                cand = [p for p, r in players.items() if who in r['name']]
        if len(cand) != 1:
            print(f'指不清是谁：{who} → {cand}')
            sys.exit(2)
        return cand[0], t0, t1

    L = [f'# {mid} 逐对指令合计（humans_cmd.tsv：真引擎重放的全场真人逐条指令；我方号标 *）']
    for spec in on:
        p, t0, t1 = resolve(spec)
        span = '全程' if t1 >= 10 ** 9 and t0 == 0 else f't={t0}~{t1}'
        L.append('')
        L.append(f'## 谁在打 {label(p)}（{span}；只算陆上进攻）')
        g = OrderedDict()
        for r in rows:
            if r['kind'] != 'attack' or r['tt'] not in ('H', 'L') or r['target'] != p or not (t0 <= r['t'] <= t1):
                continue
            g.setdefault(r['p'], []).append(r)
        tot_n = tot_x = 0
        for a, rs in sorted(g.items(), key=lambda kv: -sum(r['troops'] for r in kv[1])):
            x = sum(r['troops'] for r in rs)
            fee = sum(r['fee'] for r in rs)
            big = max(rs, key=lambda r: r['troops'])
            pcts = sorted(set(r['pct'] for r in rs))
            L.append(f"  {label(a)}：{len(rs)} 条，发兵 {fmt(x)}，手续费 {fmt(fee)}，pct {pcts[0]}~{pcts[-1]}，t={rs[0]['t']}~{rs[-1]['t']}；"
                     f"最重一条 t={big['t']} pct={big['pct']} 发兵 {fmt(big['troops'])}（发令前余额 {fmt(big['b0'])}、自己 {fmt(big['terr'])} 格；目标当时 {fmt(big['tTerr'])} 格 / {fmt(big['tBal'])} 兵）")
            tot_n += len(rs); tot_x += x
        L.append(f'  合计 {tot_n} 条，发兵 {fmt(tot_x)}')
        d = [r for r in rows if r['kind'] == 'donate' and r['target'] == p and t0 <= r['t'] <= t1]
        if d:
            byd = defaultdict(list)
            for r in d:
                byd[r['p']].append(r)
            L.append('  收到的捐款：' + '；'.join(f"{label(a)} {len(rs)} 笔到账 {fmt(sum(r['recv'] for r in rs))}（手续费 {fmt(sum(r['fee'] for r in rs))}，t={rs[0]['t']}~{rs[-1]['t']}）" for a, rs in byd.items()))
        else:
            L.append('  收到的捐款：0 笔')
    for spec in by:
        p, t0, t1 = resolve(spec)
        span = '全程' if t1 >= 10 ** 9 and t0 == 0 else f't={t0}~{t1}'
        L.append('')
        L.append(f'## {label(p)} 把兵发给了谁（{span}）')
        g = OrderedDict()
        for r in rows:
            if r['p'] != p or not (t0 <= r['t'] <= t1):
                continue
            if r['tt'] == 'N':
                key = ('attack', 'N', -1)
            elif r['tt'] == 'A':
                key = ('attack', 'A', -1)
            elif r['tt'] == 'B':
                key = (r['kind'], 'B', -1)
            else:
                key = (r['kind'], r['tt'], r['target'])
            g.setdefault(key, []).append(r)
        names = {'N': '无主地', 'A': '内置 AI（合计）', 'B': '船（合计）'}
        for (kind, tt, tg), rs in sorted(g.items(), key=lambda kv: -sum(r['troops'] for r in kv[1])):
            x = sum(r['troops'] for r in rs)
            fee = sum(r['fee'] for r in rs)
            who = names.get(tt) or (label(tg) + ('（已离开的席位）' if tt == 'L' else ''))
            pcts = sorted(set(r['pct'] for r in rs))
            extra = ''
            if tt == 'D':
                extra = f"，到账 {fmt(sum(r['recv'] for r in rs))}"
            elif tt in ('H', 'L'):
                extra = f"；首条时目标 {fmt(rs[0]['tTerr'])} 格 / {fmt(rs[0]['tBal'])} 兵，末条时 {fmt(rs[-1]['tTerr'])} 格 / {fmt(rs[-1]['tBal'])} 兵"
            L.append(f"  {kind} → {who}：{len(rs)} 条，发兵 {fmt(x)}，手续费 {fmt(fee)}，pct {pcts[0]}~{pcts[-1]}，t={rs[0]['t']}~{rs[-1]['t']}{extra}")
        allr = sorted((r for rs in g.values() for r in rs), key=lambda r: r['_i'])  # 按录像里的先后（不是按分组）
        if allr:
            L.append(f"  合计 {len(allr)} 条：发兵 {fmt(sum(r['troops'] for r in allr))}，手续费 {fmt(sum(r['fee'] for r in allr))}；窗口首条发令前余额 {fmt(allr[0]['b0'])}（{fmt(allr[0]['terr'])} 格），末条发令后余额 {fmt(allr[-1]['b1'])}（{fmt(allr[-1]['terr'])} 格）")
        else:
            L.append('  窗口内没有指令')
    path = os.path.join(out_dir, f"pair_cmds{'_' + tag if tag else ''}.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
