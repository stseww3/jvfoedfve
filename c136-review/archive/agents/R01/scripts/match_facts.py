#!/usr/bin/env python3
"""match_facts.py — 一局的“事实底稿”：复盘里引用的数字都从这里出（或从 lag_probe/cmd_audit/dispatch_survey）。
输入: /agent/repos/c136-data/bundles/<matchId>/{card.json,results.csv,traj.csv,timeline.csv,events.csv,spawn.csv,anomalies.json,in_game.log}
      + out/<matchId>/{replay_cmds.csv,replay_meta.json,teams.json}（先跑 replay_cmds.mjs、team_infer.py；没有录像则跳过相关段）
用法: python3 match_facts.py <matchId> [--section a,b,...]
段: card results spawn timeline bots teams replay drops dispatch
输出: 文本到 stdout，同时写 out/<matchId>/facts.json
"""
import csv, json, math, os, sys, collections, re
mid = sys.argv[1]
want = None
for i, a in enumerate(sys.argv):
    if a == '--section':
        want = set(sys.argv[i + 1].split(','))
def on(s):
    return want is None or s in want
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
os.makedirs(OUT, exist_ok=True)
B = f'/agent/repos/c136-data/bundles/{mid}'
card = json.load(open(os.path.join(B, 'card.json')))
land = card['mapLand']
facts = {'matchId': mid}
def rd(name):
    p = os.path.join(B, name)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []
results = rd('results.csv'); traj = rd('traj.csv'); events = rd('events.csv'); spawn = rd('spawn.csv')
me = {}; init_line = {}
W = Hh = None
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        bot = line.split('\t', 1)[1].split(']')[0].strip('[')
        me[bot] = int(line.rsplit('me=', 1)[1].split()[0])
    if W is None:
        m = re.search(r'map=(\d+)x(\d+)', line)
        if m:
            W, Hh = int(m.group(1)), int(m.group(2))
for r in results:
    if r.get('meId'):
        me.setdefault(r['bot'], int(r['meId']))
id2bot = {v: k for k, v in me.items()}
has_rep = os.path.exists(os.path.join(OUT, 'replay_cmds.csv'))
rep = list(csv.DictReader(open(os.path.join(OUT, 'replay_cmds.csv')))) if has_rep else []
meta = json.load(open(os.path.join(OUT, 'replay_meta.json'))) if has_rep else {}
names = meta.get('names', [])
teams = {}
tp = os.path.join(OUT, 'teams.json')
if os.path.exists(tp):
    teams = {int(k): v for k, v in json.load(open(tp))['team'].items()}
def nm(p):
    p = int(p)
    if p == 512: return 'NEUTRAL'
    if p in id2bot: return id2bot[p]
    if p < len(names): return names[p]
    return f'bot#{p}'
def tm(p):
    p = int(p)
    return f"T{teams[p]}" if p in teams else ('AI' if p >= meta.get('humans', 10**9) else 'T?')

if on('card'):
    o = card['outcome']
    print(f"== {mid} card: cohort={card['cohort']} map={card['mapId']} seed={card['mapSeed']} land={land} teams={card['nominalTeams']}/{card['actualTeams']} seeded={card['seededPlayers']} "
          f"ourTeam={card['ourPrimaryTeam']} split={card['teamSplitCounts']} label={o['resultLabel']} winnerTeam={o['winnerTeam']} endTick={o['endTick']} "
          f"peakSquadShare={100*o['peakSquadLandShare']:.2f}% peakTeamShare={100*o['peakPrimaryTeamShareSeen']:.2f}% finalTeamShare={100*o['ourFinalTeamShare']:.2f}% peer={card.get('sameMatchPeer')}")
    print(f"   anomalies: {card['anomaliesSummary']}")
    print(f"   bots in log: {len(me)} -> " + ' '.join(f'{b}={i}' for b, i in sorted(me.items(), key=lambda x: x[1])))
    if has_rep:
        print(f"   replay: humans={meta['humans']} players={meta['players']} teams={meta['numberTeams']} lastTick={meta['lastTick']} cmds={meta['cmds']}")

if on('results'):
    print('-- results.csv (tick = harness status snapshot, may lag the true event)')
    for r in sorted(results, key=lambda r: int(r['tick'])):
        tt = r.get('teamTotals') or ''
        sh = ''
        if tt:
            d = json.loads(tt); s = sum(d.values())
            sh = ' teamShare%=' + '/'.join(f"T{k}:{100*v/land:.1f}" for k, v in sorted(d.items()))
        print(f"   {r['bot']:10s} id={r['meId']:>3s} {r['event']:5s}/{r['result']:5s} tick={int(r['tick']):6d} sec={r['seconds']:>4s} place={r['place']:>3s} alive={r['alivePlayers']:>3s} "
              f"terr={r['territory']:>6s} last={r['lastTerritory']:>6s} peak={r['peak']:>6s} bal={r['balance']:>8s} sent={r['sent']} acc={r['accepted']} team={r['teamMine'] or '-'}{sh}")

if on('spawn') and has_rep:
    # final spawn pixel per human from the replay (last id=0 cmd), W inferred from spawn.csv if not logged
    last = {}; nsp = collections.Counter()
    for r in rep:
        if r['kind'] == 'spawn':
            last[int(r['player'])] = int(r['dX']); nsp[int(r['player'])] += 1
    if W is None:
        cand = collections.Counter()
        lastrow = {}
        for r in spawn:
            lastrow[r['bot']] = r
        for b, r in lastrow.items():
            if b in me and me[b] in last and int(r['y']) > 0:
                w = (last[me[b]] - int(r['x'])) / int(r['y'])
                if abs(w - round(w)) < 1e-9: cand[int(round(w))] += 1
        if cand: W = cand.most_common(1)[0][0]
    if W:
        pos = {p: (d % W, d // W) for p, d in last.items()}
        sq = [p for p in me.values() if p in pos]
        print(f'-- spawn (replay final spawn cmd; W={W}): squad bots')
        dists = []
        for p in sorted(sq):
            x, y = pos[p]
            others = sorted((math.hypot(x - pos[q][0], y - pos[q][1]), q) for q in pos if q != p)
            ally = [(d, q) for d, q in others if q in sq]
            hum = [(d, q) for d, q in others if q not in sq]
            near_h = [(round(d), nm(q)[:14], tm(q)) for d, q in hum[:3]]
            n80 = sum(1 for d, q in others if d <= 80)
            print(f"   {nm(p):8s} id={p:3d} ({x:3d},{y:3d}) respawnCmds={nsp[p]:2d} nearestAlly={ally[0][0]:.0f}px({nm(ally[0][1])}) humansWithin80px={n80} nearestOthers={near_h}")
            dists.append(ally[0][0])
        xs = [pos[p][0] for p in sq]; ys = [pos[p][1] for p in sq]
        print(f"   squad bbox x[{min(xs)},{max(xs)}] y[{min(ys)},{max(ys)}] = {max(xs)-min(xs)}x{max(ys)-min(ys)} px; nearest-ally dist min/med/max = {min(dists):.0f}/{sorted(dists)[len(dists)//2]:.0f}/{max(dists):.0f}")
        facts['spawn'] = {nm(p): pos[p] for p in sq}

snap = collections.defaultdict(dict)
for r in traj:
    snap[r['bot']][int(r['t'])] = r
if on('timeline'):
    tl = rd('timeline.csv')
    pick = [90, 180, 270, 450, 630, 720, 900, 1080, 1260, 1530, 2070, 3060, 4050, 4500, 5040, 6030, 7020, 8010, 9000, 10080, 11070, 11790, 11880, 11970]
    print('-- squad timeline (timeline.csv): t alive sqTerr share% sqBal sqDens')
    rows = {int(r['t']): r for r in tl}
    ts = sorted(rows)
    use = sorted(set([t for t in pick if t in rows] + ts[-2:]))
    peak = max(tl, key=lambda r: float(r['squadShare']))
    for t in use:
        r = rows[t]
        print(f"   t={t:6d} alive={r['alive']:>2s} sqTerr={int(float(r['squadTerr'])):7d} share={100*float(r['squadShare']):5.2f}% sqBal={int(float(r['squadBal'])):9d} sqDens={float(r['squadDens']):6.1f}")
    print(f"   PEAK squad share {100*float(peak['squadShare']):.2f}% at t={peak['t']} (terr {peak['squadTerr']})")
    facts['peakSquad'] = {'t': int(peak['t']), 'share': float(peak['squadShare'])}

if on('bots'):
    print('-- per bot (traj.csv): lastT peakTerr@t firstBoxed(nb=0&neut=0) boxedHighDens(dens>=95) atCap(dens>=149.5) passivePre1500(nb>0,dCmds=0) cmds boats')
    for b in sorted(snap, key=lambda b: me.get(b, 0)):
        s = snap[b]; ts = sorted(s)
        pk = max(ts, key=lambda t: int(s[t]['terr']))
        boxed = [t for t in ts if int(s[t]['nb']) == 0 and int(s[t]['neut']) == 0]
        bhd = [t for t in boxed if float(s[t]['dens']) >= 95]
        cap = [t for t in ts if float(s[t]['dens']) >= 149.5]
        pas = 0
        for i in range(1, len(ts)):
            if ts[i] <= 1500 and int(s[ts[i]]['nb']) > 0 and int(s[ts[i]]['cmds']) == int(s[ts[i - 1]]['cmds']):
                pas += 1
        print(f"   {b:8s} lastT={ts[-1]:6d} peak={int(s[pk]['terr']):6d}@{pk:<6d} firstBoxed={boxed[0] if boxed else '-'} boxedSnaps={len(boxed)} boxedHighDens={len(bhd)} atCap={len(cap)}"
              f"{' ['+str(cap[0])+'..'+str(cap[-1])+']' if cap else ''} passivePre1500={pas} cmds={s[ts[-1]]['cmds']} boats={s[ts[-1]]['boats']}")

if on('teams'):
    print('-- team totals seen (results.csv of this bundle + peer): tick T1/T2/... share% of land')
    seen = {}
    def add(m):
        p = f'/agent/repos/c136-data/bundles/{m}/results.csv'
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                if r.get('teamTotals'):
                    seen[int(r['tick'])] = (json.loads(r['teamTotals']), m, r['bot'])
    add(mid)
    peer = (card.get('sameMatchPeer') or {}).get('peerMatchId')
    if peer: add(peer)
    for t in sorted(seen):
        d, m, b = seen[t]
        print(f"   t={t:6d} " + ' '.join(f"T{k}={v}({100*v/land:.1f}%)" for k, v in sorted(d.items())) + f"   [{m}:{b}]")
    facts['teamTotals'] = {t: seen[t][0] for t in seen}

if on('replay') and has_rep:
    sq = set(me.values())
    print('-- replay: leave/surrender cmds of squad bots (server tick)')
    for r in rep:
        if r['kind'] in ('leave', 'surrender') and int(r['player']) in sq:
            print(f"   {nm(r['player']):8s} {r['kind']} @ {r['tick']}")
    lv = collections.Counter((int(r['tick']) // 500) * 500 for r in rep if r['kind'] in ('leave', 'surrender'))
    print('   all-human leave cmds per 500-tick bucket:', dict(sorted(lv.items())))
    print('-- replay: attack cmds BY squad bots: target(team) n first..last')
    for p in sorted(sq):
        agg = collections.OrderedDict()
        for r in rep:
            if int(r['player']) == p and r['kind'] == 'attack':
                k = int(r['dZ']); a = agg.setdefault(k, [0, int(r['tick']), int(r['tick'])]); a[0] += 1; a[2] = int(r['tick'])
        boats = sum(1 for r in rep if int(r['player']) == p and r['kind'] == 'boat')
        s = '; '.join(f"{nm(k)[:16]}({tm(k)})x{v[0]}@{v[1]}..{v[2]}" for k, v in agg.items())
        print(f"   {nm(p):8s} boats={boats} | {s}")
    print('-- replay: attack cmds ON squad bots (only humans appear in replays): attacker(team) -> bot n first..last')
    agg = collections.OrderedDict()
    for r in rep:
        if r['kind'] == 'attack' and int(r['dZ']) in sq:
            k = (int(r['player']), int(r['dZ'])); a = agg.setdefault(k, [0, int(r['tick']), int(r['tick']), 0]); a[0] += 1; a[2] = int(r['tick']); a[3] += int(r['dX'])
    for (a, b), v in agg.items():
        print(f"   {nm(a)[:18]:18s} id={a:3d} ({tm(a)}) -> {nm(b):8s} x{v[0]} @{v[1]}..{v[2]} sumPct/1024={v[3]}")
    print('-- replay: accepted donations involving squad bots: donor -> recipient n first..last')
    agg = collections.OrderedDict()
    for r in rep:
        if r['kind'] == 'donate' and (int(r['player']) in sq or int(r['dZ']) in sq):
            k = (int(r['player']), int(r['dZ'])); a = agg.setdefault(k, [0, int(r['tick']), int(r['tick'])]); a[0] += 1; a[2] = int(r['tick'])
    for (a, b), v in agg.items():
        print(f"   {nm(a)[:16]:16s} -> {nm(b)[:16]:16s} x{v[0]} @{v[1]}..{v[2]}")

if on('drops'):
    an = json.load(open(os.path.join(B, 'anomalies.json'))) if os.path.exists(os.path.join(B, 'anomalies.json')) else {}
    print(f"-- DROP30 reconciliation ({an.get('drop30Count')} events): per event: logged dispatches, replay-accepted donations, recorded attacks(sum pct/1024), boats, humans attacking the bot in window")
    for e in an.get('drop30Events', []):
        b, t0, t1 = e['bot'], e['t0'], e['t1']
        pid = me.get(b)
        dl = [r for r in events if r['bot'] == b and r['type'] in ('DISPATCH', 'DONATE') and t0 < int(r['t']) <= t1]
        nominal = sum(int(r['myBal']) * (int(r['pct']) + 1) // 1024 for r in dl if r['myBal'] and r['pct'])
        fee = sum(64 * int(r['myBal']) // 1024 for r in dl if r['myBal'])
        acc = [r for r in rep if int(r['player']) == pid and r['kind'] == 'donate' and t0 < int(r['tick']) <= t1 + 20]
        at = [r for r in rep if int(r['player']) == pid and r['kind'] == 'attack' and t0 < int(r['tick']) <= t1 + 20]
        bo = [r for r in rep if int(r['player']) == pid and r['kind'] == 'boat' and t0 < int(r['tick']) <= t1 + 20]
        inc = collections.Counter(nm(r['player'])[:14] + '(' + tm(r['player']) + ')' for r in rep if r['kind'] == 'attack' and int(r['dZ']) == pid and t0 - 60 < int(r['tick']) <= t1 + 20)
        tg = collections.Counter(nm(r['dZ'])[:14] for r in at)
        print(f"   {b:8s} {t0}-{t1} bal {e['bal0']}->{e['bal1']} (-{e['dropPct']}%) terr {e['terr0']}->{e['terr1']} | dispatchLogged={len(dl)} nominal={nominal} fee={fee} accepted={len(acc)} | "
              f"attacks={len(at)} sumPct={sum(int(r['dX']) for r in at)} targets={dict(tg)} boats={len(bo)} | incomingHumans={dict(inc)}")

if on('dispatch'):
    d = [r for r in events if r['type'] in ('DISPATCH', 'DONATE')]
    lr = sum(1 for r in d if r.get('likelyRejected') == 'True')
    print(f"-- dispatch/donate logged={len(d)} likelyRejected(bundle heuristic)={lr}; ASSIST={sum(1 for r in events if r['type']=='ASSIST')} INTERCEPT={sum(1 for r in events if r['type']=='INTERCEPT')}")
    k = collections.Counter((r['type'], r['kind'], r['boxedIn']) for r in d)
    for kk, v in sorted(k.items()):
        print(f"   {kk}: {v}")
    tgt = collections.Counter(r['targetName'] for r in d)
    print('   recipients:', dict(tgt.most_common(8)))
    if d:
        print(f"   t range {min(int(r['t']) for r in d)}..{max(int(r['t']) for r in d)}; before t=4284 (quota active): {sum(1 for r in d if int(r['t']) < 4284)}")
json.dump(facts, open(os.path.join(OUT, 'facts.json'), 'w'), ensure_ascii=False, indent=1, default=str)
