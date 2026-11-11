#!/usr/bin/env python3
"""seat_table.py — 一局里本队每个席位的“户口本”：日志、RESULT、录像、重演四处的记录并排，先看清哪些号真的在打。

B 组（squad20）的日志行首名字会在局中轮换（同一个席位先叫 Bohemia，后来叫 ErenYeager），所以一律按席位号（me / meId）串。

读：
  bundles/<局号>/in_game.log    [HL-GAME-INIT] me=、[HL-SPAWN]/[HL-SPAWN-BACKEND]、[HL-TICK]（第一/最后一行的拍、应有/实有行数、最后的 cmds/boats）
  bundles/<局号>/results.csv    RESULT 行（按 meId；没有 meId 列时按名字）
  out/<局号>/replay_cmds.csv    录像里该席位落地的指令：出生、进攻、捐款、船、leave（拍号）
  out/<局号>/resim_meta.json    席位 ↔ 名字 ↔ 队、阵亡拍
  out/<局号>/resim_events.csv   阵亡 / 离场事件（当时的领土、余额、谁打的）
  out/<局号>/resim_players.csv  每 90 拍的领土（取峰值、离场时的领土）

用法：python3 scripts/seat_table.py <局号> [--grid 112]
输出：每个席位一行 + 汇总（几个号从没有 HL-TICK、几个被 leave、leave 拍对 --grid 取余、日志缺的快照行数）。
"""
import csv
import json
import os
import re
import sys

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
DATA = '/agent/repos/c136-data/bundles'
CLOCK_A, CLOCK_B = 23.0, 0.05598  # 秒 = 23.0 + 0.05598 × 拍（tick_clock.py 的拟合）


def main():
    a = sys.argv[1:]
    mid = a[0]
    grid = int(a[a.index('--grid') + 1]) if '--grid' in a else 112
    meta = json.load(open(os.path.join(OUT, mid, 'resim_meta.json')))
    squad = {k: v for k, v in meta['squad'].items() if ':' not in k}
    teams = {int(k): v for k, v in meta['teams'].items()}
    seat_label = {}
    for b, p in squad.items():
        seat_label.setdefault(p, b)

    # 日志
    info = {p: {'labels': [b], 'spawnLines': 0, 'ticks': [], 'lastCmds': None, 'lastBoats': None, 'otherLines': {}} for p, b in seat_label.items()}
    label_seat = dict(squad)
    res_rows = []
    rp = os.path.join(DATA, mid, 'results.csv')
    if os.path.exists(rp):
        res_rows = list(csv.DictReader(open(rp, encoding='utf8')))
    by_seat_res = {}
    for r in res_rows:
        p = None
        if r.get('meId', '') != '':
            p = int(r['meId'])
        elif r['bot'] in label_seat:
            p = label_seat[r['bot']]
        if p is None or p not in info:
            continue
        by_seat_res[p] = r
        if r['bot'] not in info[p]['labels']:
            info[p]['labels'].append(r['bot'])
            label_seat[r['bot']] = p
    lp = os.path.join(DATA, mid, 'in_game.log')
    for line in open(lp, encoding='utf8', errors='replace'):
        m = re.search(r'\[([^\]]+)\] \[(HL-[A-Z-]+)\] (.*)$', line)
        if not m or m.group(1) not in label_seat:
            continue
        p = label_seat[m.group(1)]
        if p not in info:
            continue
        d = info[p]
        k = m.group(2)
        if k in ('HL-SPAWN', 'HL-SPAWN-BACKEND'):
            d['spawnLines'] += 1
        elif k == 'HL-TICK':
            mm = re.match(r't=(\d+) .*cmds=(\d+) boats=(\d+)', m.group(3))
            if mm:
                d['ticks'].append(int(mm.group(1)))
                d['lastCmds'], d['lastBoats'] = int(mm.group(2)), int(mm.group(3))
        elif k not in ('HL-GAME-INIT',):
            d['otherLines'][k] = d['otherLines'].get(k, 0) + 1

    # 录像
    rc = {p: {'spawn': 0, 'spawnLast': None, 'attack': 0, 'donate': 0, 'boat': 0, 'first': None, 'last': None, 'leave': None} for p in info}
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'replay_cmds.csv'), encoding='utf8')):
        p = int(r['player'])
        if p not in rc:
            continue
        k = r['kind']
        t = int(r['tick'])
        if k == 'spawn':
            rc[p]['spawn'] += 1
            rc[p]['spawnLast'] = int(r['step'])
        elif k == 'leave':
            rc[p]['leave'] = t
        elif k in ('attack', 'donate', 'boat'):
            rc[p][k] += 1
            if rc[p]['first'] is None:
                rc[p]['first'] = t
            rc[p]['last'] = t

    # 重演：领土序列
    terr = {p: {} for p in info}
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'resim_players.csv'))):
        p = int(r['p'])
        if p in terr:
            terr[p][int(r['t'])] = (int(r['terr']), int(r['bal']), int(r['state']), int(r['alive']))
    deathT = {}
    for r in csv.DictReader(open(os.path.join(OUT, mid, 'resim_events.csv'))):
        if r['ev'] == 'died':
            deathT[int(r['p'])] = int(r['t'])

    print(f'== {mid} 本队席位户口本（{len(info)} 个席位；时间 = 开局后秒数，名义时刻 = {CLOCK_A} + {CLOCK_B}×拍）')
    print('席位 队 名字(轮换) | 出生: 日志行/落地指令(最后一步) | HL-TICK 第一–最后 实有/应有 | 日志 cmds/boats | 录像落地 进攻/捐/船 第一–最后拍 | leave 拍(名义秒, 对%d取余) | RESULT 事件 拍 秒 | 阵亡拍 | 领土峰值@拍 → leave 时' % grid)
    n_notick = n_leave = n_res = 0
    miss_tot = have_tot = 0
    leaves = []
    for p in sorted(info, key=lambda q: (teams.get(q, 0), q)):
        d = info[p]
        r = rc[p]
        ts = d['ticks']
        if ts:
            expect = (max(ts) - min(ts)) // 90 + 1
            have = len(set(ts))
            miss_tot += expect - have
            have_tot += have
            tk = f'{min(ts)}–{max(ts)} {have}/{expect}'
        else:
            tk = '无'
            n_notick += 1
        lv = '-'
        if r['leave'] is not None:
            n_leave += 1
            leaves.append(r['leave'])
            lv = f"{r['leave']}({CLOCK_A + CLOCK_B * r['leave']:.1f}s, {r['leave'] % grid})"
        rr = by_seat_res.get(p)
        rs = '-'
        if rr:
            n_res += 1
            rs = f"{rr['event']} {rr['tick']} {rr['seconds']}s"
        # 峰值只算还在自己手里的时候（leave 之前；离场壳由内置 AI 接管后长出来的地不算）
        own = {t: v for t, v in terr[p].items() if r['leave'] is None or t <= r['leave']}
        pk = max(own.items(), key=lambda kv: kv[1][0]) if own else None
        at_leave = ''
        if r['leave'] is not None and terr[p]:
            tt = max([t for t in terr[p] if t <= r['leave']] or [min(terr[p])])
            at_leave = f" → {terr[p][tt][0]}格/{terr[p][tt][1]}兵@{tt}"
        other = ' '.join(f'{k[3:]}×{v}' for k, v in sorted(d['otherLines'].items()))
        print(f"  #{p:<3d} T{teams.get(p, 0)} {'→'.join(d['labels']):28s} | {d['spawnLines']}/{r['spawn']}({r['spawnLast']}) | {tk:18s} | {d['lastCmds']}/{d['lastBoats']} | "
              f"{r['attack']}/{r['donate']}/{r['boat']} {r['first']}–{r['last']} | {lv} | {rs} | {deathT.get(p, '-')} | "
              f"{pk[1][0] if pk else '-'}@{pk[0] if pk else '-'}{at_leave} | {other}")
    print(f'# 从没有 HL-TICK 行的席位 {n_notick}；录像里被 leave 的 {n_leave}；有 RESULT 行的 {n_res}；HL-TICK 实有 {have_tot} 行、按第一–最后一行算应有 {have_tot + miss_tot} 行（缺 {miss_tot}）')
    if leaves:
        res = {}
        for t in leaves:
            res.setdefault(t % grid, []).append(t)
        print(f'# leave 拍对 {grid} 取余：' + '；'.join(f'余 {k}: {sorted(v)}' for k, v in sorted(res.items(), key=lambda kv: -len(kv[1]))))


if __name__ == '__main__':
    main()
