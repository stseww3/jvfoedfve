#!/usr/bin/env python3
"""boats_near.py — 列出某个号的队友在指定时间之前发的船里，登陆格离这个号出生点不超过 R 像素的那些（录像指令解码）。
登陆格 = 指令里的水格沿指令方向走一步。只说明“船是朝它那片地去的”，不等于确认落在它的地上。
用法：cd c136-review/agents/R04 && timeout 60 python3 scripts/boats_near.py A047 riku_x 2445 80
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_lib import load_replay  # noqa: E402

mid, bot, tmax, R = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
r = load_replay(f'/agent/repos/c136-data/bundles/{mid}/replay.txt')
# 地图宽度：从出生指令的格子下标推不出来，读模拟器地图头（只读）
import gzip, struct
from replay_lib import TEAM_COLOUR_NAMES  # noqa: F401
vu = r['vu']
idx = (10 + vu['mapRealisticIndex'] if vu['mapRealisticIndex'] <= 9 else 12 + vu['mapRealisticIndex']) if vu['mapType'] == 1 else vu['mapProceduralIndex']
seed = 0 if vu['mapType'] == 1 else vu['mapSeed']
buf = gzip.open(f'/agent/repos/c136-data/src/sim/maps/{idx}_{seed}.bin.gz').read(8)
W, H = struct.unpack('<HH', buf[4:8])
me = [p for p, n in enumerate(r['names']) if bot in n][0]
team = r['teams']['fX'][me]
mates = [p for p in range(r['H']) if r['teams']['fX'][p] == team and p != me]
spawn = {}
for step, tick, cid, pl, a, b in r['rows']:
    if cid == 0:
        spawn[pl] = (a % W, a // W)
sx, sy = spawn[me]
D = [(0, -1), (1, 0), (0, 1), (-1, 0)]
print(f'{mid} {bot}（号位 {me}，队 {team}）出生点 ({sx},{sy})，地图 {W}x{H}；t<={tmax} 队友的船里登陆格距它 <= {R:.0f} 像素的：')
n = 0
for step, tick, cid, pl, a, b in r['rows']:
    if cid == 3 and pl in mates and 0 <= tick <= tmax:
        w, d = b >> 3, b & 7
        x, y = w % W + D[d % 4][0], w // W + D[d % 4][1]
        dist = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
        if dist <= R:
            n += 1
            print(f'  t={tick} {r["names"][pl]} 比例 {a}/1024 登陆格 ({x},{y}) 距离 {dist:.0f}')
print(f'共 {n} 条')
