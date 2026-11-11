#!/usr/bin/env python3
"""lag_probe.py — 用“日志里的发令拍(本地拍)”对“录像里的执行拍(服务器拍)”：
  (1) 测每个机器人的客户端滞后；(2) 给每笔 HL-DISPATCH/HL-DONATE 定“引擎是否真的接受”。
原理：
  * HL-OPENING t=.. spend=S/B  →  Strategy.send() 里 pct = ceil(S*1024/B)-1（v27-team-c116.js L479-487），
    录像里同一玩家的陆攻指令 (id=1, dX=pct, dZ=512) 就是这条命令被服务器排进回合的拍。
  * HL-DISPATCH/HL-DONATE t=.. pct=.. target=..  →  录像 (id=2, dX=pct, dZ=target)。引擎只把通过全部校验
    （队友存活 rn、到账≥1 rD、配额 ao.ei）的捐款写入录像（live_game_js.js qj.qv），所以匹配不到 = 引擎没执行。
  * lag = 录像拍 - 日志拍。正常联机 ≈ 7~20 拍（服务器回合 7 拍）；持续增大 = 客户端模拟落后于服务器。
  * 捐款匹配用保序动态规划（同号、同 pct、同目标、0<=lag<=MAXLAG，总滞后最小，允许日志条目落空=被拒）。
用法: python3 lag_probe.py <matchId> [--replay <otherMatchId>] [--maxlag N] [--quiet]
      （需要先跑 replay_cmds.mjs 生成 out/<replayMatch>/replay_cmds.csv；同局对手包可用 --replay 借录像）
输出: out/<matchId>/lag_probe.csv + 概要
"""
import csv, json, math, os, sys, collections
mid = sys.argv[1]
rmid = mid
MAXLAG = 400
quiet = '--quiet' in sys.argv
for i, a in enumerate(sys.argv):
    if a == '--replay': rmid = sys.argv[i + 1]
    if a == '--maxlag': MAXLAG = int(sys.argv[i + 1])
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
ROUT = os.path.join(HERE, '..', 'out', rmid)
os.makedirs(OUT, exist_ok=True)
B = f'/agent/repos/c136-data/bundles/{mid}'
meta = json.load(open(os.path.join(ROUT, 'replay_meta.json')))
rep = list(csv.DictReader(open(os.path.join(ROUT, 'replay_cmds.csv'))))
last_tick = meta['lastTick']
by_player = collections.defaultdict(list)
for r in rep:
    by_player[int(r['player'])].append(r)
me = {}
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        bot = line.split('\t', 1)[1].split(']')[0].strip('[')
        me[bot] = int(line.rsplit('me=', 1)[1].split()[0])
rp = os.path.join(B, 'results.csv')
if os.path.exists(rp):
    for r in csv.DictReader(open(rp)):
        if r.get('meId'):
            me.setdefault(r['bot'], int(r['meId']))
rows = []
# ---- openings: distinct pct per command, simple forward match
used = set()
op = os.path.join(B, 'opening.csv')
if os.path.exists(op):
    for r in csv.DictReader(open(op)):
        bot = r['bot']
        if bot not in me or not r['spend'] or not r['bal']:
            continue
        S, Bal, t = int(r['spend']), int(r['bal']), int(r['t'])
        if Bal <= 0:
            continue
        pct = max(0, min(1023, math.ceil(S * 1024 / Bal) - 1))
        m = None
        for x in by_player.get(me[bot], []):
            if x['kind'] == 'attack' and id(x) not in used and int(x['dX']) == pct and int(x['dZ']) == 512 and t <= int(x['tick']) <= t + 1500:
                m = x; used.add(id(x)); break
        rows.append(dict(bot=bot, kind='OPENING', t=t, pct=pct, target=512, replayTick=int(m['tick']) if m else '', lag=(int(m['tick']) - t) if m else '', likelyRejected=''))
# ---- dispatch / donate: order-preserving DP per bot
ev = os.path.join(B, 'events.csv')
logs = collections.defaultdict(list)
if os.path.exists(ev):
    for r in csv.DictReader(open(ev)):
        if r['type'] in ('DISPATCH', 'DONATE') and r['bot'] in me and r['pct'] and r['target']:
            logs[r['bot']].append(r)
SKIP_R = 10 ** 6
for bot, L in logs.items():
    L.sort(key=lambda r: int(r['t']))
    R = [x for x in by_player.get(me[bot], []) if x['kind'] == 'donate']
    n, m = len(L), len(R)
    INF = float('inf')
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = dp[i][j]
            if c == INF:
                continue
            if i < n and c < dp[i + 1][j]:
                dp[i + 1][j] = c; bk[i + 1][j] = ('skipL', i, j)
            if j < m and c + SKIP_R < dp[i][j + 1]:
                dp[i][j + 1] = c + SKIP_R; bk[i][j + 1] = ('skipR', i, j)
            if i < n and j < m:
                lag = int(R[j]['tick']) - int(L[i]['t'])
                if 0 <= lag <= MAXLAG and int(R[j]['dX']) == int(L[i]['pct']) and int(R[j]['dZ']) == int(L[i]['target']):
                    if c + lag < dp[i + 1][j + 1]:
                        dp[i + 1][j + 1] = c + lag; bk[i + 1][j + 1] = ('match', i, j)
    i, j = n, m
    matched = {}
    orphan_r = 0
    while (i, j) != (0, 0) and bk[i][j] is not None:
        op_, pi, pj = bk[i][j]
        if op_ == 'match':
            matched[pi] = R[pj]
        elif op_ == 'skipR':
            orphan_r += 1
        i, j = pi, pj
    for k, r in enumerate(L):
        x = matched.get(k)
        t = int(r['t'])
        truth = 'accepted' if x else ('beyond-replay' if t > last_tick - 30 else 'rejected')
        rows.append(dict(bot=bot, kind=r['type'] + ':' + (r['kind'] or ''), t=t, pct=int(r['pct']), target=int(r['target']),
                         replayTick=int(x['tick']) if x else '', lag=(int(x['tick']) - t) if x else '', likelyRejected=r.get('likelyRejected', ''), truth=truth,
                         myBal=r.get('myBal', ''), dMe=r.get('dMe', ''), dAlly=r.get('dAlly', ''), boxedIn=r.get('boxedIn', ''), targetName=r.get('targetName', '')))
    if orphan_r and not quiet:
        print(f'  note: {bot} has {orphan_r} replay donations without a logged dispatch')
rows.sort(key=lambda r: (r['bot'], r['t']))
fields = ['bot', 'kind', 't', 'pct', 'target', 'replayTick', 'lag', 'likelyRejected', 'truth', 'myBal', 'dMe', 'dAlly', 'boxedIn', 'targetName']
with open(os.path.join(OUT, 'lag_probe.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields, restval='')
    w.writeheader(); w.writerows(rows)
print(f'== {mid} (replay from {rmid}, lastTick={last_tick}): lag = replayTick - logTick; OPENING = neutral expand cmds')
leave = {int(r['player']): int(r['tick']) for r in rep if r['kind'] in ('leave', 'surrender')}
for bot in sorted(me, key=lambda b: me[b]):
    rs = [r for r in rows if r['bot'] == bot and r['kind'] == 'OPENING']
    s = ' '.join(f"{r['t']}:{r['lag'] if r['lag'] != '' else 'x'}" for r in rs)
    print(f"  {bot:12s} me={me[bot]:3d} leaveCmdTick={leave.get(me[bot])} | {s}")
d = [r for r in rows if r['kind'] != 'OPENING']
if d:
    acc = [r for r in d if r['truth'] == 'accepted']
    rej = [r for r in d if r['truth'] == 'rejected']
    byd = [r for r in d if r['truth'] == 'beyond-replay']
    lags = sorted(r['lag'] for r in acc)
    print(f'  dispatch/donate logged={len(d)} acceptedByEngine={len(acc)} rejected={len(rej)} beyondReplay={len(byd)}')
    if lags:
        print(f'  accepted lag: min={lags[0]} med={lags[len(lags)//2]} p90={lags[int(0.9*(len(lags)-1))]} max={lags[-1]}')
    known = [r for r in d if r['truth'] != 'beyond-replay']
    lr = [r for r in known if r.get('likelyRejected') == 'True']
    tp_ = sum(1 for r in known if r.get('likelyRejected') == 'True' and r['truth'] == 'rejected')
    fp_ = sum(1 for r in known if r.get('likelyRejected') == 'True' and r['truth'] == 'accepted')
    fn_ = sum(1 for r in known if r.get('likelyRejected') != 'True' and r['truth'] == 'rejected')
    print(f'  bundle likelyRejected=True: {len(lr)} | vs replay truth: flagged&rejected={tp_} flagged-but-accepted={fp_} unflagged-but-rejected={fn_}')
    kk = collections.Counter((r['kind'], r['truth']) for r in d)
    for k, v in sorted(kk.items()):
        print(f'     {k[0]:36s} {k[1]:14s} {v}')
    q0 = [r for r in known if r['t'] < 4284]; q1 = [r for r in known if r['t'] >= 4284]
    for nm_, q in (('t<4284 (quota active)', q0), ('t>=4284 (no quota)', q1)):
        if q:
            print(f"     {nm_}: logged={len(q)} rejected={sum(1 for r in q if r['truth']=='rejected')}")
    if not quiet:
        for r in rej[:40]:
            print(f"    REJECTED {r['bot']} t={r['t']} {r['kind']} pct={r['pct']} -> {r['target']}({r['targetName']}) myBal={r['myBal']} dMe={r['dMe']} dAlly={r['dAlly']} flagged={r.get('likelyRejected')}")
