#!/usr/bin/env python3
"""spawn_exec.py — 「出生点执行」机械检测（可对全部对局包跑）：协调器/策略给出的出生坐标，有没有变成录像里的出生指令。

输入（每局）：
  /agent/repos/c136-data/bundles/<id>/{in_game.log, spawn.csv, traj.csv, results.csv}
  /tmp/c136-r05/cmds/<id>.tsv   录像原始命令流（没有就先跑：node scripts/replay_cmds.mjs <id> --out /tmp/c136-r05/cmds/<id>.tsv；只解码，不重放）
口径：
  号 ↔ 录像玩家：录像玩家名去掉 [标签] 后与号名相同（大小写不敏感）；对不上的号 = 不在这一盘录像里（拆盘局的另一盘）。
  地图宽：日志 `[BACKEND-SPAWN-COORD] … (map=宽x高` 或 `[HL-SPAWN…] W=`；都没有时用「我方出生指令解出的坐标落在日志指派点集合里的条数最多」的宽度（枚举 400…4096）。
  求解轮数 = `[BACKEND-SPAWN-COORD] Solved` 的行数；不同的解 = 这些行里指派串去重后的个数。
  每个号的结论：
      最终坐标落地   录像里它最后一条出生指令 = 日志里它最后一次指派（±2 格）
      停在旧坐标     最后一条出生指令 = 日志里更早的某次指派
      日志外坐标     有出生指令，但不等于日志里任何一次指派
      0 条落地       录像里没有它的出生指令（选点期结束时由引擎随机落子）
  本地发送数（近似）= results.csv 的 accepted − 最后一条 [HL-TICK] 的 cmds（accepted 含出生发送；只有有结算行的号才有）。
输出：每局一行（TSV，可 --tsv），或带 --detail 逐号。
用法：python3 scripts/spawn_exec.py <matchId> [...] [--detail] [--tsv]
"""
import csv
import math
import os
import re
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
ids = [x for x in a if not x.startswith('--')]
detail, tsv = '--detail' in a, '--tsv' in a
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()
COLS = ['matchId', 'logBots', 'inReplay', 'solveRounds', 'distinctSolutions', 'finalLanded', 'stuckOld', 'offLog', 'zeroLanded', 'spawnCmdTicks', 'phaseStart', 'othersWithSpawn', 'others', 'localSends(min-max)', 'sendsMinusLanded(min/med/max)', 'firstLandedTickMin', 'assignMinusLanded(med)']
if tsv:
    print('\t'.join(COLS))
for mid in ids:
    B = f'/agent/repos/c136-data/bundles/{mid}'
    cp = f'/tmp/c136-r05/cmds/{mid}.tsv'
    if not os.path.exists(cp):
        alt = f'/tmp/c136-r05/work/{mid}-cmds.tsv'
        cp = alt if os.path.exists(alt) else cp
    if not os.path.exists(cp):
        print(f'{mid}\t缺命令流：node scripts/replay_cmds.mjs {mid} --out /tmp/c136-r05/cmds/{mid}.tsv')
        continue
    assign = defaultdict(list)
    if os.path.exists(f'{B}/spawn.csv'):
        for r in csv.DictReader(open(f'{B}/spawn.csv', encoding='utf-8')):
            assign[r['bot']].append((int(r['x']), int(r['y']), r['role']))
    solves, W = [], 0
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.search(r'\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+).*?\): (.*)', ln)
        if m:
            solves.append(m.group(5).strip())
            W = int(m.group(3))
    bots = set(assign)
    lastcmds = {}
    if os.path.exists(f'{B}/traj.csv'):
        for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
            bots.add(r['bot'])
            lastcmds[r['bot']] = int(r['cmds'])
    res = {}
    if os.path.exists(f'{B}/results.csv'):
        for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
            res[r['bot']] = r
            bots.add(r['bot'])
    names, sp, humans = {}, defaultdict(list), set()
    phase0 = 0
    for r in csv.DictReader(open(cp, encoding='utf-8'), delimiter='\t'):
        p = int(r['player'])
        if r['name']:
            names[p] = r['name']
        if r['kind'] == 'spawn':
            sp[p].append((int(r['tick']), int(r['a'])))
            phase0 = min(phase0, int(r['tick']))
    byname = defaultdict(list)
    for p, n in names.items():
        byname[bare(n)].append(p)
    pid = {b: byname[b.lower()][0] for b in bots if len(byname.get(b.lower(), [])) == 1}
    if not W:
        pts = {(x, y) for v in assign.values() for x, y, _ in v}
        best = (0, 0)
        for w in range(400, 4097):
            n = sum(1 for b, p in pid.items() for t, px in sp.get(p, []) if (px % w, px // w) in pts)
            if n > best[0]:
                best = (n, w)
        W = best[1]
    verd = Counter()
    rows = []
    ticks = []
    for b in sorted(bots):
        if b not in pid:
            rows.append((b, '不在这一盘录像里', None))
            continue
        R = [(t, px % W, px // W) for t, px in sp.get(pid[b], [])] if W else []
        A = assign.get(b, [])
        if not sp.get(pid[b]):
            v = '0 条落地'
        elif not W:
            v = '有出生指令（地图宽未知）'
        else:
            ex = R[-1][1:]
            if A and math.hypot(ex[0] - A[-1][0], ex[1] - A[-1][1]) <= 2:
                v = '最终坐标落地'
            elif any(math.hypot(ex[0] - x, ex[1] - y) <= 2 for x, y, _ in A[:-1]):
                v = '停在旧坐标'
            else:
                v = '日志外坐标'
        verd[v] += 1
        ticks += [t for t, _ in sp.get(pid[b], [])]
        sends = int(res[b]['accepted']) - lastcmds[b] if b in res and res[b].get('accepted') and b in lastcmds else None
        rows.append((b, v, {'assign': A, 'replay': R, 'sends': sends}))
    inrep = [r for r in rows if r[2] is not None]
    others = [p for p in names if p not in pid.values() and (sp.get(p) or True)]
    humans_with_names = [p for p in names if p not in set(pid.values())]
    oth_sp = sum(1 for p in sp if p not in set(pid.values()))
    sends = [r[2]['sends'] for r in inrep if r[2]['sends'] is not None]
    diff = sorted(r[2]['sends'] - len(r[2]['replay']) for r in inrep if r[2]['sends'] is not None)
    adiff = sorted(len(r[2]['assign']) - len(r[2]['replay']) for r in inrep)
    line = [mid, len(bots), len(inrep), len(solves), len(set(solves)), verd['最终坐标落地'], verd['停在旧坐标'], verd['日志外坐标'], verd['0 条落地'],
            f'{min(ticks)}..{max(ticks)}' if ticks else '-', phase0, oth_sp, len(humans_with_names), f'{min(sends)}-{max(sends)}' if sends else '-',
            f'{diff[0]}/{diff[len(diff) // 2]}/{diff[-1]}' if diff else '-', min(ticks) if ticks else '-', adiff[len(adiff) // 2] if adiff else '-']
    if tsv:
        print('\t'.join(str(x) for x in line))
    else:
        print(f'{mid}: 号 {len(bots)} 个（在这盘录像里 {len(inrep)}）｜求解 {len(solves)} 轮、不同的解 {len(set(solves))} 个｜最终坐标落地 {verd["最终坐标落地"]}、停在旧坐标 {verd["停在旧坐标"]}、日志外坐标 {verd["日志外坐标"]}、0 条落地 {verd["0 条落地"]}'
              f'｜我方出生指令落地拍 {line[9]}（选点期从 {phase0} 起）｜其他玩家有出生指令的 {oth_sp} 个｜本地发送数 {line[13]}｜每号 本地发送 − 录像落地（最小/中位/最大）{line[14]}｜每号 日志指派次数 − 录像落地 中位 {line[16]}')
    if detail:
        for b, v, d in rows:
            if d is None:
                print(f'   {b}: {v}')
                continue
            print(f'   {b}: {v}｜日志指派 {len(d["assign"])} 次' + (f'（最后 ({d["assign"][-1][0]},{d["assign"][-1][1]}) {d["assign"][-1][2]}）' if d['assign'] else '')
                  + f'｜录像出生指令 {len(d["replay"])} 条' + (('：' + '、'.join(f'拍 {t} ({x},{y})' for t, x, y in d['replay'][-3:])) if d['replay'] else '')
                  + (f'｜本地发送约 {d["sends"]} 条' if d['sends'] is not None else ''))
