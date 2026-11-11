#!/usr/bin/env python3
"""cmd_audit.py — 策略自己数的发令数（HL-TICK cmds=）对录像里引擎实际记录的指令数。
引擎只把通过前置校验的指令写进录像（陆攻：目标存活且非队友、有空闲战线槽；捐款：配额/上限全过）。
所以  “日志 cmds 增量” − “录像同一窗口内该玩家的 attack+boat(+donate) 条数”  ≈ 被引擎静默丢弃/拒绝的指令。
由于客户端可能落后服务器（见 lag_probe.py），按窗口比较只是近似；末行的累计值不受滞后影响。
用法: python3 cmd_audit.py <matchId> [bot ...]
"""
import csv, json, os, sys, collections
mid = sys.argv[1]
only = set(sys.argv[2:])
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
B = f'/agent/repos/c136-data/bundles/{mid}'
rep = list(csv.DictReader(open(os.path.join(OUT, 'replay_cmds.csv'))))
me = {}
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        bot = line.split('\t', 1)[1].split(']')[0].strip('[')
        me[bot] = int(line.rsplit('me=', 1)[1].split()[0])
traj = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(B, 'traj.csv'))):
    traj[r['bot']].append((int(r['t']), int(r['cmds']), int(r['boats'])))
ev = collections.defaultdict(list)
ep = os.path.join(B, 'events.csv')
if os.path.exists(ep):
    for r in csv.DictReader(open(ep)):
        if r['type'] in ('DISPATCH', 'DONATE'):
            ev[r['bot']].append(int(r['t']))
print(f'== {mid}: issued (log) vs recorded (replay)')
print('bot       me  lastT  cmdsLog dispatchLog | replay: attack donate boat chase retreat | attackGap(cmdsLog-attack-boat)')
for bot in sorted(me):
    if only and bot not in only:
        continue
    pid = me[bot]
    rc = collections.Counter(r['kind'] for r in rep if int(r['player']) == pid)
    tr = sorted(traj.get(bot, []))
    lastT, cmds = (tr[-1][0], tr[-1][1]) if tr else (0, 0)
    gap = cmds - rc.get('attack', 0) - rc.get('boat', 0)
    print(f"{bot:8s} {pid:3d} {lastT:6d} {cmds:7d} {len(ev.get(bot, [])):11d} | {rc.get('attack',0):6d} {rc.get('donate',0):6d} {rc.get('boat',0):4d} {rc.get('chase',0):5d} {rc.get('retreat',0):7d} | {gap}")
if only:
    for bot in sorted(only):
        pid = me[bot]
        mine = sorted(int(r['tick']) for r in rep if int(r['player']) == pid and r['kind'] in ('attack', 'boat'))
        tr = sorted(traj.get(bot, []))
        print(f'-- {bot}: per HL-TICK window: t, dCmds(log), recorded attack+boat with replayTick in (prevT, t] (unshifted)')
        prev_t, prev_c = 0, 0
        for t, c, b in tr:
            n = sum(1 for x in mine if prev_t < x <= t)
            if c - prev_c or n:
                print(f'   t={t:6d} dCmds={c - prev_c:3d} recorded={n:3d}')
            prev_t, prev_c = t, c
