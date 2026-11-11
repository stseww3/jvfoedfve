#!/usr/bin/env python3
"""team_infer.py — 从录像指令流推断每个真人玩家的队伍（不模拟）。
依据（live_game_js.js 指令处理 qj）：
  * 捐款 id=2 只有通过 rn(同队且存活) 才写入录像  →  捐款边 = 同队；
  * 陆攻 id=1 只有通过 rk(目标非队友) 才写入录像   →  真人→真人攻击边 = 异队；
  * 已知锚点：本包与同局对手包 results.csv 里的 meId/teamMine，card.json 的 ourPrimaryTeam（本编队各号）。
做法：捐款边并查集 → 用锚点给连通块定队 → 对未定块按“与已定各队都有攻击边则只剩一队可选”做排除法传播。
用法: python3 team_infer.py <matchId>      → out/<matchId>/teams.json + 概要
"""
import csv, json, os, sys, collections
mid = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
DATA = '/agent/repos/c136-data/bundles'
meta = json.load(open(os.path.join(OUT, 'replay_meta.json')))
H, nT, names = meta['humans'], meta['numberTeams'], meta['names']
rep = list(csv.DictReader(open(os.path.join(OUT, 'replay_cmds.csv'))))
card = json.load(open(os.path.join(DATA, mid, 'card.json')))
parent = list(range(H))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
don = collections.Counter()
atk = collections.Counter()
for r in rep:
    p = int(r['player'])
    if r['kind'] == 'donate':
        q = int(r['dZ'])
        if p < H and q < H:
            union(p, q); don[(p, q)] += 1
    elif r['kind'] == 'attack':
        q = int(r['dZ'])
        if p < H and q < H:
            atk[(p, q)] += 1
anchors = {}
def add_anchor(p, t, why):
    if t and p is not None:
        anchors.setdefault(p, (int(t), why))
# our squad bots
for line in open(os.path.join(DATA, mid, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        add_anchor(int(line.rsplit('me=', 1)[1].split()[0]), card.get('ourPrimaryTeam'), 'card.ourPrimaryTeam')
def read_results(m):
    p = os.path.join(DATA, m, 'results.csv')
    if not os.path.exists(p):
        return
    for r in csv.DictReader(open(p)):
        if r.get('teamMine') and r.get('meId'):
            anchors[int(r['meId'])] = (int(r['teamMine']), f'{m}/results.csv teamMine')
read_results(mid)
peer = (card.get('sameMatchPeer') or {}).get('peerMatchId')
if peer:
    read_results(peer)
comp_team = {}
conflicts = []
for p, (t, why) in anchors.items():
    c = find(p)
    if c in comp_team and comp_team[c][0] != t:
        conflicts.append((p, t, comp_team[c]))
    else:
        comp_team.setdefault(c, (t, why))
team = {}
basis = {}
for p in range(H):
    c = find(p)
    if c in comp_team:
        team[p] = comp_team[c][0]
        basis[p] = 'anchor' if p in anchors else 'donation-link'
# elimination by attack edges
changed = True
while changed:
    changed = False
    comps = collections.defaultdict(set)
    for p in range(H):
        comps[find(p)].add(p)
    for c, members in comps.items():
        if any(m in team for m in members):
            continue
        enemy_teams = set()
        for (a, b), n in atk.items():
            if a in members and b in team:
                enemy_teams.add(team[b])
            if b in members and a in team:
                enemy_teams.add(team[a])
        cand = [t for t in range(1, nT + 1) if t not in enemy_teams]
        if len(cand) == 1 and enemy_teams:
            for m in members:
                team[m] = cand[0]; basis[m] = 'attack-elimination'
            changed = True
out = {'matchId': mid, 'numberTeams': nT, 'humans': H, 'known': len(team), 'conflicts': [str(c) for c in conflicts],
       'team': {str(p): team[p] for p in sorted(team)}, 'basis': {str(p): basis[p] for p in sorted(basis)}}
json.dump(out, open(os.path.join(OUT, 'teams.json'), 'w'), ensure_ascii=False, indent=0)
cnt = collections.Counter(team.values())
bc = collections.Counter(basis.values())
print(f'{mid}: teams={nT} humans={H} inferred={len(team)} by team={dict(sorted(cnt.items()))} basis={dict(bc)} conflicts={len(conflicts)}')
# sanity: attack edges inside same inferred team (should be 0)
bad = [(a, b, n) for (a, b), n in atk.items() if a in team and b in team and team[a] == team[b]]
print('  same-team attack edges (should be 0):', len(bad), bad[:5])
if len(sys.argv) > 2:
    for p in map(int, sys.argv[2:]):
        print(f'  player {p} {names[p] if p < len(names) else ""}: team={team.get(p)} basis={basis.get(p)}')
