#!/usr/bin/env python3
"""review_skel.py — 从逐拍重演真值（match_truth.mjs 产出的 /tmp/c136-r05/truth/<id>.json）和对局卡生成一局复盘的机械骨架。

用法：python3 review_skel.py <matchId> [--dir /tmp/c136-r05/truth] [--out /tmp/c136-r05/skel]
产出 <out>/<matchId>.json，字段：
  context / outcome / timeline / deathsSkel / drop30 / dispatch / bursts / cmp / winner
复盘 JSON 里所有数字都从这里或 truth_digest.py 抄，不手算。
"""
import json
import os
import re
import statistics
import sys
from collections import defaultdict

args = sys.argv[1:]
mid = args[0]
tdir = args[args.index('--dir') + 1] if '--dir' in args else '/tmp/c136-r05/truth'
odir = args[args.index('--out') + 1] if '--out' in args else '/tmp/c136-r05/skel'
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
J = json.load(open(f'{tdir}/{mid}.json'))
card = json.load(open(f'{DATA}/bundles/{mid}/card.json'))
H = J['humans']
land = J['map']['land']
P = J['players']
nT = J['humanTeams']
our = J['ourTeam']
squad = [s['p'] for s in J['squad']]
sqname = {s['p']: s['bot'] for s in J['squad']}
PEER = {b['p'] for b in (J.get('peer') or {}).get('bots', [])}
CATS = J['cats']
T30, HS, S10, F30, EV = J['T30'], J['HS'], J['S10'], J['F30'], J['events']
end = J['endTick']
num = int(mid[1:])
ver = ('Va(v27-team-c116-va.js)' if num <= 17 else 'Vb(v27-team-c116-vb.js)' if num <= 95 else 'Vc(v27-team-c116.js)') if mid[0] == 'A' else 'c110(v27-team-c110.js)'


def nm(p):
    if p >= 512:
        return '中立'
    if p >= H:
        return f'机器人#{p}'
    if p in sqname:
        return sqname[p]
    return f"{P[p]['name'][:18]}(#{p},T{P[p]['team']}{',同房另一编队号' if p in PEER else ''})"


def sh(x):
    return round(100.0 * x / land, 1)


def idx_at(ts, t):
    lo, hi, r = 0, len(ts) - 1, -1
    while lo <= hi:
        m = (lo + hi) // 2
        if ts[m] <= t:
            r, lo = m, m + 1
        else:
            hi = m - 1
    return r


def flows_between(p, t0, t1):
    f = F30[str(p)]
    i0, i1 = idx_at(f['t'], t0), idx_at(f['t'], t1)
    if i0 < 0 or i1 < 0:
        return None
    return [f['flows'][i1][c] - f['flows'][i0][c] for c in range(len(CATS))]


# ---------- context / outcome ----------
def _cls(p):
    return 'squad' if p in sqname else 'peer' if p in PEER else 'real'


sizes = J['teamSizes']
context = {
    'cohort': card.get('cohort'), 'strategyVersion': ver, 'timeUtc': card.get('timeUtc'),
    'map': f"{J['map']['idx']}({J['map']['W']}x{J['map']['H']})", 'mapLand': land, 'humans': H,
    'headerTeams': J['headerTeams'], 'actualTeams': nT, 'teamSizes': sizes, 'baseWinExpectation': round(1 / nT, 3) if nT else None,
    'ourTeam': our, 'ourTeamSize': sizes[our - 1] if our else None,
    'squadBotsInReplay': [f"{sqname[p]}#{p}" for p in squad], 'squadBotsNotInReplay': [b for b in J['logBots'] if b not in sqname.values()],
    'teamSplit': card.get('teamSplitCounts'),
    'sameRoomPeer': {'matchId': (J.get('peer') or {}).get('matchId'), 'cohort': (J.get('peer') or {}).get('cohort'),
                     'botsByTeam': {str(t): sum(1 for p in PEER if P[p]['team'] == t) for t in range(1, nT + 1)}} if PEER else None,
    'realHumansExcludingBothSquads': H - len(squad) - len(PEER),
    # 三类账号各自的掉线（被引擎标 left）数：我方编队号 / 同房另一编队号 / 其余真人
    'leftByT1000': {k: sum(1 for p in J['players'] if _cls(p['id']) == k and p['leftT'] is not None and 0 <= p['leftT'] <= 1000) for k in ('squad', 'peer', 'real')},
    'leftByT2000': {k: sum(1 for p in J['players'] if _cls(p['id']) == k and p['leftT'] is not None and 0 <= p['leftT'] <= 2000) for k in ('squad', 'peer', 'real')},
    'classSizes': {k: sum(1 for p in J['players'] if _cls(p['id']) == k) for k in ('squad', 'peer', 'real')},
    'replayEndTick': end, 'simCheck': None,
}
# 赢家：录像末拍份额最大的队
li = len(T30['t']) - 1
fin = [T30['land'][li][t] for t in range(nT + 1)]
winner = max(range(1, nT + 1), key=lambda t: fin[t]) if nT else None
tsq = [sh(x) for x in T30['squadLand']]
tour = [sh(T30['land'][i][our]) for i in range(len(T30['t']))] if our else []
pk = max(range(len(tour)), key=lambda i: tour[i]) if tour else 0
pks = max(range(len(tsq)), key=lambda i: tsq[i])
outcome = {
    'result': 'won' if card['outcome'].get('primaryTeamWon') else 'lost', 'endTick': card['outcome'].get('endTick'), 'replayEndTick': end,
    'winnerTeam': card['outcome'].get('winnerTeam'), 'winnerTeamByReplay': winner,
    'ourTeamPeakShare': tour[pk] if tour else None, 'ourTeamPeakT': T30['t'][pk] if tour else None,
    'squadPeakShare': tsq[pks], 'squadPeakT': T30['t'][pks],
    'finalShares': {f'T{t}': sh(fin[t]) for t in range(1, nT + 1)},
}

# ---------- timeline ----------
want = [90, 180, 360, 600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400, 5700, 6000, 6300, 6600, 6900, 7200, 7500, 7800, 8100, 8400, 8700, 9000, 9300]
cend = card['outcome'].get('endTick') or end
want = [t for t in want if t <= end]
for extra in (min(cend, end) - (min(cend, end) % 30), end - end % 30):
    if extra not in want and extra > 0:
        want.append(extra)
want = sorted(set(want))
timeline = []
for t in want:
    i = idx_at(T30['t'], t)
    if i < 0:
        continue
    shares = {f'T{x}': sh(T30['land'][i][x]) for x in range(1, nT + 1)}
    order = sorted(range(1, nT + 1), key=lambda x: -T30['land'][i][x])
    timeline.append({
        't': T30['t'][i], 'teamShare': shares, 'ourTeamRank': (order.index(our) + 1) if our else None, 'botsShare': sh(T30['land'][i][0]),
        'squadShare': sh(T30['squadLand'][i]), 'squadBal': T30['squadBal'][i], 'squadDens': round(T30['squadBal'][i] / max(1, T30['squadLand'][i]), 1),
        'squadActive': T30['squadActive'][i], 'squadAlive': T30['squadAlive'][i],
        'ourTeamActiveHumans': T30['active'][i][our] if our else None, 'note': '',
    })

# ---------- deaths skeleton ----------
pairs = J['pairs']
lastCmd = defaultdict(lambda: -1)
for e in EV:
    if e['p'] in sqname and e['type'] in ('attack', 'boat', 'donate'):
        lastCmd[e['p']] = max(lastCmd[e['p']], e['t'])
lastLog = defaultdict(lambda: -1)   # 该号最后一条带拍号的日志（本地拍）
lagMax = defaultdict(lambda: (0, 0))  # 按日志行序估计的最大落后拍数（该号打 HL-TICK t=X 时，全队已见到的最大拍号 − X）
lagN = defaultdict(lambda: [0, 0])
name2p = {v: k for k, v in sqname.items()}
tmax = 0
rx = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-(TICK|DISPATCH)\] t=(\d+)')
for line in open(f'{DATA}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
    m = rx.match(line)
    if not m:
        continue
    bot, kind, t = m.group(2), m.group(3), int(m.group(4))
    if bot not in name2p:
        continue
    tmax = max(tmax, t)
    p = name2p[bot]
    lastLog[p] = max(lastLog[p], t)
    if kind == 'TICK':
        lagN[p][1] += 1
        if tmax - t >= 90:
            lagN[p][0] += 1
        if tmax - t > lagMax[p][0]:
            lagMax[p] = (tmax - t, t)
deaths = []
for p in squad:
    pl = P[p]
    takers = sorted([(r['tiles'], r['sent'], r['a']) for r in pairs if r['b'] == p and r['a'] < 512 and r['tiles'] > 0], reverse=True)[:3]
    s = S10[str(p)]
    lt = pl['leftT']
    i = idx_at(s['t'], lt) if lt >= 0 else -1
    deaths.append({
        'bot': sqname[p], 'pid': p, 'leftT': lt if lt >= 0 else None, 'diedT': pl['deathT'] if pl['deathT'] >= 0 else None,
        'lastCmdT': lastCmd[p] if lastCmd[p] >= 0 else None, 'lastLogT': lastLog[p] if lastLog[p] >= 0 else None,
        'terrAtLeave': s['terr'][i] if i >= 0 else None, 'balAtLeave': s['bal'][i] if i >= 0 else None,
        'peakTerr': pl['peakTerr'], 'peakT': pl['peakT'],
        'logOrderLagMax': lagMax[p][0], 'logOrderLagMaxAtT': lagMax[p][1], 'tickLinesLagGE90': f"{lagN[p][0]}/{lagN[p][1]}",
        'takers': [{'who': nm(a), 'tiles': tl, 'sent': sn} for tl, sn, a in takers], 'cause': '',
    })

# ---------- DROP30（90 拍窗、跌 ≥30%，离场后不计）----------
drop30 = []
for p in squad:
    s = S10[str(p)]
    pl = P[p]
    stop = pl['leftT'] if pl['leftT'] >= 0 else (pl['deathT'] if pl['deathT'] >= 0 else end)
    t = 90
    while t + 90 <= stop:
        i0, i1 = idx_at(s['t'], t), idx_at(s['t'], t + 90)
        if i0 >= 0 and i1 >= 0 and s['t'][i0] == t and s['t'][i1] == t + 90:
            b0, b1 = s['bal'][i0], s['bal'][i1]
            if b0 >= 2000 and b1 <= 0.7 * b0:
                fl = flows_between(p, t, t + 90) or []
                neg = sorted([(v, CATS[c]) for c, v in enumerate(fl) if v < 0])
                drop30.append({'bot': sqname[p], 't0': t, 't1': t + 90, 'bal0': b0, 'bal1': b1, 'terr0': s['terr'][i0], 'terr1': s['terr'][i1],
                               'mainSink': neg[0][1] if neg else '?', 'flows': {CATS[c]: v for c, v in enumerate(fl) if abs(v) >= max(1, 0.02 * b0)},
                               'residual': (b1 - b0) - sum(fl) if fl else None})
        t += 90
sink = defaultdict(int)
for d in drop30:
    sink[d['mainSink']] += 1

# ---------- dispatch ----------
D = [d for d in J['dispatch'] if d['p'] >= 0]
ex = [d for d in D if d['exec']]
rs = defaultdict(int)
for d in D:
    if d['exec']:
        continue
    r = [x['reason'] for x in d['sim']]
    if all(x != 'ok' for x in r):
        rs['试算四拍全被拒:' + (r[2] if len(r) > 2 else r[-1])] += 1
    elif all(x == 'ok' for x in r):
        rs['试算四拍全通过(指令没落地)'] += 1
    else:
        rs['试算有通过有被拒'] += 1
dons = [e for e in EV if e['type'] == 'donate' and e['ok']]
outd = [e for e in dons if e['p'] in sqname]
ind = [e for e in dons if e['q'] in sqname and e['p'] not in sqname]
lags = sorted(d['exec']['t'] - d['t'] for d in ex)
perbot = defaultdict(lambda: [0, 0])
for d in D:
    perbot[d['bot']][0] += 1
    perbot[d['bot']][1] += 1 if d['exec'] else 0
bur = defaultdict(list)
for e in outd:
    bur[(e['p'], e['t'])].append(e)
dispatch = {
    'logged': len(D), 'executed': len(ex), 'notExecuted': len(D) - len(ex), 'notExecutedReasons': dict(rs),
    'perBotLoggedExecuted': {b: v for b, v in perbot.items()},
    'execLagMedian': lags[len(lags) // 2] if lags else None, 'execLagMax': lags[-1] if lags else None, 'execLagGE25': sum(1 for x in lags if x >= 25),
    'squadDonationsExecuted': len(outd), 'arrived': sum(e['got'] for e in outd), 'tax': sum(e['fee'] for e in outd),
    'toSquadMates': sum(1 for e in outd if e['q'] in sqname), 'toOtherTeammates': sum(1 for e in outd if e['q'] not in sqname),
    'fromOtherTeammates': {'n': len(ind), 'arrived': sum(e['got'] for e in ind)},
    'sameTickBatches': [{'bot': sqname[p], 't': t, 'n': len(v), 'bal0': v[0]['B0'], 'outTotal': sum(e['got'] + e['fee'] for e in v)} for (p, t), v in sorted(bur.items(), key=lambda kv: kv[0][1]) if len(v) >= 2],
    'cardLikelyRejected': card.get('anomaliesSummary', {}).get('likelyRejectedTransfers'), 'cardTotalTransfers': card.get('anomaliesSummary', {}).get('totalTransfers'),
}

# ---------- 同拍连发（陆攻+出船 ≥3 条）----------
bursts = {}
tot_c = tot_b = 0
for p in squad:
    by = defaultdict(list)
    for e in EV:
        if e['p'] == p and e['type'] in ('attack', 'boat'):
            by[e['t']].append(e)
    n = sum(len(v) for v in by.values())
    bb = [(t, v) for t, v in by.items() if len(v) >= 3]
    tot_c += n
    tot_b += sum(len(v) for _, v in bb)
    if bb:
        bursts[sqname[p]] = {'cmds': n, 'burstTicks': len(bb), 'cmdsInBursts': sum(len(v) for _, v in bb), 'list': [
            {'t': t, 'n': len(v), 'targets': dict((nm(q), c) for q, c in defaultdict(int, {q: sum(1 for e in v if e['q'] == q) for q in {e['q'] for e in v}}).items()),
             'spentPctOfBal': round(100 * sum((e.get('troops') or 0) + (e.get('fee') or 0) for e in v if e['ok']) / max(1, v[0]['B0'])),
             'firstCmdPctOfBal': round(100 * (v[0].get('troops') or 0) / max(1, v[0]['B0'])), 'noFront': sum(1 for e in v if not e['ok'])}
            for t, v in sorted(bb, key=lambda x: -len(x[1]))[:8]]}
bursts['_total'] = {'squadCmds': tot_c, 'cmdsInBursts': tot_b}

# ---------- 指令落地率：策略自报已发指令数（[HL-TICK] 的 cmds=）对 录像里真正执行的条数 ----------
# cmds 在策略里只有「g.attack / g.boatTo / g.donate 返回 true」时才加一；捐兵那部分等于 [HL-DISPATCH] 日志条数，
# 所以「陆攻+出船已发」= cmds − 该号到那一拍为止的调度日志条数。录像侧：陆攻/出船/捐兵各自实际执行的条数。
rxc = re.compile(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*? cmds=(\d+)')
crow = defaultdict(list)
for line in open(f'{DATA}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
    m = rxc.search(line)
    if m and m.group(1) in name2p:
        crow[name2p[m.group(1)]].append((int(m.group(2)), int(m.group(3))))
evt = defaultdict(list)
evd = defaultdict(list)
for e in EV:
    if e['p'] in sqname and e['type'] in ('attack', 'boat'):
        evt[e['p']].append(e['t'])
    if e['p'] in sqname and e['type'] == 'donate':
        evd[e['p']].append(e['t'])
dlog = defaultdict(list)
for d in J['dispatch']:
    if d.get('p', -1) >= 0:
        dlog[d['p']].append(d['t'])
delivery = {}
ti = te = tdi = tde = 0
for p, arr in crow.items():
    arr.sort()
    t, c = arr[-1]
    nd = sum(1 for x in dlog[p] if x <= t)
    ex_n = sum(1 for x in evt[p] if x <= t + 14)
    exd = sum(1 for x in evd[p] if x <= t + 14)
    dead = []
    prev_d = 0
    for (t0, c0), (t1, c1) in zip(arr, arr[1:]):
        d_n = sum(1 for x in dlog[p] if t0 < x <= t1)
        e_n = sum(1 for x in evt[p] if t0 + 10 < x <= t1 + 10)
        iss = c1 - c0 - d_n
        if iss >= 9 and e_n <= 1:
            dead.append({'t0': t0, 't1': t1, 'issued': iss, 'executed': e_n})
    delivery[sqname[p]] = {'lastLogT': t, 'atkBoatIssued': c - nd, 'atkBoatExecuted': ex_n, 'atkBoatRate': round(ex_n / max(1, c - nd), 2),
                          'donIssued': nd, 'donExecuted': exd,
                          'deadWindows': dead, 'issuedInDeadWindows': sum(d['issued'] for d in dead)}
    ti += c - nd
    te += ex_n
    tdi += nd
    tde += exd
delivery['_total'] = {'atkBoatIssued': ti, 'atkBoatExecuted': te, 'atkBoatRate': round(te / max(1, ti), 2), 'donIssued': tdi, 'donExecuted': tde,
                      'issuedInDeadWindows': sum(v['issuedInDeadWindows'] for v in delivery.values())}

# ---------- 影子策略的下发对账（shadow.mjs --match --match-json 的产物，若已生成就并进来） ----------
shadow = None
_mp = os.path.join(odir, f'{mid}.match.json')
if os.path.exists(_mp):
    shadow = json.load(open(_mp))

# ---------- 我方号 vs 其他在场真人（不含同房另一编队）----------
cmp_rows = []
for t in (300, 600, 900, 1200, 1500, 1800, 2100, 2400, 3000, 3600, 4500):
    if t not in HS['t']:
        continue
    i = HS['t'].index(t)
    terr, bal = HS['terr'][i], HS['bal'][i]

    def active(p):
        return terr[p] > 0 and not (0 <= P[p]['leftT'] <= t)
    oth = [p for p in range(H) if active(p) and p not in sqname and p not in PEER]
    sa = [p for p in squad if active(p)]
    sall = [p for p in squad if terr[p] > 0]
    if len(oth) < 2:
        continue
    q = statistics.quantiles([terr[p] for p in oth], n=4)
    cmp_rows.append({'t': t, 'realHumansActive': len(oth), 'realTerrMedian': int(q[1]), 'realTerrUpperQ': int(q[2]),
                     'realDensMedian': round(statistics.median([bal[p] / terr[p] for p in oth]), 1),
                     'squadActive': len(sa), 'squadTerrMedianActive': int(statistics.median([terr[p] for p in sa])) if sa else None,
                     'squadTerrMedianAllAlive': int(statistics.median([terr[p] for p in sall])) if sall else None,
                     'squadDensMedianActive': round(statistics.median([bal[p] / terr[p] for p in sa]), 1) if sa else None})

# ---------- 赢家 ----------
tops = sorted(P, key=lambda x: -x['peakTerr'])[:3]
win = []
for tp in tops:
    vic = defaultdict(int)
    for w, a_, b_, v in J['pairAll']:
        if a_ == tp['id']:
            vic[b_] += v
    don = defaultdict(lambda: [0, 0])
    for t_, p_, q_, got, fee in J['allDon']:
        if q_ == tp['id']:
            don[p_][0] += 1
            don[p_][1] += got
    traj = {}
    for t in (600, 1500, 3000, 4500, 6000, 7500):
        if t in HS['t']:
            i = HS['t'].index(t)
            traj[str(t)] = {'terr': HS['terr'][i][tp['id']], 'bal': HS['bal'][i][tp['id']]}
    win.append({'who': nm(tp['id']), 'peakShare': sh(tp['peakTerr']), 'peakT': tp['peakT'], 'diedT': tp['deathT'] if tp['deathT'] >= 0 else None,
                'tilesFrom': [{'who': ('中立' if x == 512 else '机器人' if x == 600 else nm(x)), 'share': sh(v)} for x, v in sorted(vic.items(), key=lambda kv: -kv[1])[:6]],
                'donationsIn': [{'who': nm(x), 'n': n, 'arrived': v} for x, (n, v) in sorted(don.items(), key=lambda kv: -kv[1][1])[:4]], 'traj': traj})

out = {'matchId': mid, 'context': context, 'outcome': outcome, 'timeline': timeline, 'deathsSkel': deaths, 'drop30': drop30, 'drop30MainSink': dict(sink),
       'dispatch': dispatch, 'bursts': bursts, 'delivery': delivery, 'cmp': cmp_rows, 'winner': win, 'shadow': shadow}
os.makedirs(odir, exist_ok=True)
json.dump(out, open(f'{odir}/{mid}.json', 'w'), ensure_ascii=False, indent=1)
print(f"{mid} 骨架 → {odir}/{mid}.json｜时间线 {len(timeline)} 点｜DROP30 {len(drop30)} 个 {dict(sink)}｜调度 日志 {dispatch['logged']} 执行 {dispatch['executed']}｜连发 {tot_b}/{tot_c}｜陆攻出船落地 {te}/{ti}｜捐兵落地 {tde}/{tdi}")
