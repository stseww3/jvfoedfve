#!/usr/bin/env python3
"""boat_landings.py — 录像里的出海指令(id=3)落点对账。
引擎事实（live_game_js.js）：
  出海 qj.iB：兵 = floor(B*(pct+1)/1024)，手续费 = floor(32*B/1024)（余额的 3.125%）；
  航行 acW：每 5 拍（t%5==3）船上兵力减 max(1, 兵>>7)（≈0.78%/5 拍）；
  靠岸 acN：落点邻格是中立 → 打中立；是自己 → 兵回余额（超上限部分作废）；
            是队友 → qm.rE：免 6.25% 税直接入账（受赠者余量 a6a 截断；余量<1 或配额 ao.ei 不过则整船作废）；
            其余 → 对该玩家开战。
本脚本不模拟航行，只按“落点坐标离谁的出生点最近”给出线索：
  - 我方 bot 出生点半径 R 内的落点：来船者是队友 → 可能是船运输血；是敌人 → 海上登陆进攻。
  - 我方 bot 自己的出海指令。
用法: python3 boat_landings.py <matchId> [--replay <otherMatchId>] [--r 70] [--t0 a --t1 b]
输出: out/<matchId>/boat_landings.csv + 屏幕汇总
"""
import csv, json, math, os, re, sys, collections
mid = sys.argv[1]
rmid = mid; R = 70; T0 = 0; T1 = 10 ** 9
for i, a in enumerate(sys.argv):
    if a == '--replay': rmid = sys.argv[i + 1]
    if a == '--r': R = int(sys.argv[i + 1])
    if a == '--t0': T0 = int(sys.argv[i + 1])
    if a == '--t1': T1 = int(sys.argv[i + 1])
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid); ROUT = os.path.join(HERE, '..', 'out', rmid)
os.makedirs(OUT, exist_ok=True)
B = f'/agent/repos/c136-data/bundles/{mid}'
me = {}; W = None
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        bot = line.split('\t', 1)[1].split(']')[0].strip('[')
        me[bot] = int(line.rsplit('me=', 1)[1].split()[0])
    if W is None:
        m = re.search(r'map=(\d+)x(\d+)', line)
        if m: W = int(m.group(1))
rp = os.path.join(B, 'results.csv')
if os.path.exists(rp):
    for r in csv.DictReader(open(rp)):
        if r.get('meId'): me.setdefault(r['bot'], int(r['meId']))
id2bot = {v: k for k, v in me.items()}
rep = list(csv.DictReader(open(os.path.join(ROUT, 'replay_cmds.csv'))))
meta = json.load(open(os.path.join(ROUT, 'replay_meta.json')))
names = meta['names']; H = meta['humans']
teams = {}
tp = os.path.join(OUT, 'teams.json')
if os.path.exists(tp): teams = {int(k): v for k, v in json.load(open(tp))['team'].items()}
last = {}
for r in rep:
    if r['kind'] == 'spawn': last[int(r['player'])] = int(r['dX'])
if W is None:
    cand = collections.Counter(); lastrow = {}
    sp = os.path.join(B, 'spawn.csv')
    if os.path.exists(sp):
        for r in csv.DictReader(open(sp)): lastrow[r['bot']] = r
    for b, r in lastrow.items():
        if b in me and me[b] in last and int(r['y']) > 0:
            w = (last[me[b]] - int(r['x'])) / int(r['y'])
            if abs(w - round(w)) < 1e-9: cand[int(round(w))] += 1
    if cand: W = cand.most_common(1)[0][0]
if not W:
    print('cannot infer map width'); sys.exit(1)
pos = {p: (d % W, d // W) for p, d in last.items()}
sq = {p: pos[p] for p in me.values() if p in pos}
def nm(p):
    return id2bot.get(p) or (names[p] if p < len(names) else f'bot#{p}')
def tm(p):
    return f"T{teams[p]}" if p in teams else ('AI' if p >= H else 'T?')
our = collections.Counter(teams[p] for p in sq if p in teams).most_common(1)
ourT = our[0][0] if our else None
rows = []
for r in rep:
    if r['kind'] != 'boat': continue
    t = int(r['tick']); p = int(r['player']); pct = int(r['dX']); qx = int(r['dZ'])
    if t < T0 or t > T1: continue
    fl = qx >> 3; x, y = fl % W, fl // W
    best = min(((math.hypot(x - sx, y - sy), q) for q, (sx, sy) in sq.items()), default=(9e9, -1))
    rel = 'squad' if p in sq else ('teammate' if ourT is not None and teams.get(p) == ourT else ('enemy' if p in teams else 'unknown'))
    rows.append(dict(tick=t, player=p, pname=nm(p), team=tm(p), rel=rel, pct=pct, x=x, y=y, nearSquadBot=nm(best[1]) if best[1] >= 0 else '', distToSpawn=round(best[0])))
with open(os.path.join(OUT, 'boat_landings.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['tick', 'player', 'pname', 'team', 'rel', 'pct', 'x', 'y', 'nearSquadBot', 'distToSpawn'])
    w.writeheader(); w.writerows(rows)
print(f'{mid}: W={W} boat cmds={len(rows)} (humans {sum(1 for r in rows if r["player"] < H)}); by relation: {dict(collections.Counter(r["rel"] for r in rows))}')
print(f'-- boats by squad bots: {sum(1 for r in rows if r["rel"] == "squad")}')
for r in rows:
    if r['rel'] == 'squad':
        print(f"   t={r['tick']:5d} {r['pname']:10s} pct={r['pct']:4d} -> ({r['x']},{r['y']}) nearest squad spawn {r['nearSquadBot']} {r['distToSpawn']}px")
near = [r for r in rows if r['rel'] != 'squad' and r['distToSpawn'] <= R]
print(f'-- boats by others whose target is within {R}px of a squad spawn: {len(near)} ({dict(collections.Counter(r["rel"] for r in near))})')
for r in near:
    print(f"   t={r['tick']:5d} {r['pname'][:20]:20s} {r['team']:3s} {r['rel']:8s} pct={r['pct']:4d} -> ({r['x']},{r['y']}) near {r['nearSquadBot']} {r['distToSpawn']}px")
