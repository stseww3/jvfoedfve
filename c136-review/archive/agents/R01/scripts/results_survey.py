#!/usr/bin/env python3
"""results_survey.py — 机械统计所有 discovery 局 results.csv 的结局事件（left/died/won…）。
目的：区分“被打死(died)”“主动/被动离场(left)”“无结果行(日志中断)”，并量化
  (a) 早期离场（tick<coreFrom=1500）——疑似客户端掉线/卡顿，非策略死亡；
  (b) 末期离场（tick>8500）——疑似 Policy.act 自动离场分支（v27-team-c116.js L4912-4927）。
用法: python3 results_survey.py [--mine] [matchId ...]
输出: 每局一行 + 汇总；同时写 out/results_survey.csv
"""
import csv, json, os, sys, collections
DATA = '/agent/repos/c136-data/bundles'
MINE = ['A057','A059','A094','A055','A075','A054','A031','A019','A009','A023','A050','A003','A005','B039','B043']
args = [a for a in sys.argv[1:] if not a.startswith('--')]
ids = args or (MINE if '--mine' in sys.argv else sorted(os.listdir(DATA)))
out_rows = []
tot = collections.Counter()
for mid in ids:
    d = os.path.join(DATA, mid)
    cp = os.path.join(d, 'card.json')
    if not os.path.exists(cp):
        continue
    card = json.load(open(cp))
    res = []
    rp = os.path.join(d, 'results.csv')
    if os.path.exists(rp):
        res = list(csv.DictReader(open(rp)))
    # bots seen in the log (HL-GAME-INIT)
    bots = set()
    lp = os.path.join(d, 'in_game.log')
    if os.path.exists(lp):
        for line in open(lp, errors='replace'):
            if '[HL-GAME-INIT]' in line:
                try:
                    bots.add(line.split('\t', 1)[1].split(']')[0].strip('['))
                except Exception:
                    pass
    ev = collections.Counter(r['event'] for r in res)
    left_early = [r for r in res if r['event'] == 'left' and int(r['tick']) < 1500]
    left_late = [r for r in res if r['event'] == 'left' and int(r['tick']) > 8500]
    left_mid = [r for r in res if r['event'] == 'left' and 1500 <= int(r['tick']) <= 8500]
    nores = len(bots) - len(res) if bots else None
    o = card['outcome']
    row = dict(matchId=mid, cohort=card['cohort'], teams=card['nominalTeams'], label=o['resultLabel'], endTick=o['endTick'],
               peakTeamShare=round(100 * o['peakPrimaryTeamShareSeen'], 1), botsInLog=len(bots), resultRows=len(res), noResult=nores,
               died=ev.get('died', 0), left=ev.get('left', 0), other=sum(v for k, v in ev.items() if k not in ('died', 'left')),
               leftEarly=len(left_early), leftMid=len(left_mid), leftLate=len(left_late),
               leftTicks=' '.join(f"{r['bot']}@{r['tick']}/{r['seconds']}s" for r in res if r['event'] == 'left'))
    out_rows.append(row)
    for k in ('died', 'left', 'other', 'leftEarly', 'leftMid', 'leftLate'):
        tot[(card['cohort'], k)] += row[k]
    tot[(card['cohort'], 'noResult')] += nores or 0
    tot[(card['cohort'], 'bots')] += len(bots)
    tot[(card['cohort'], 'matches')] += 1
od = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')
os.makedirs(od, exist_ok=True)
with open(os.path.join(od, 'results_survey.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader(); w.writerows(out_rows)
for r in out_rows:
    print(f"{r['matchId']} {r['cohort']:8s} T={r['teams']} {r['label']:10s} end={r['endTick']:6d} peak={r['peakTeamShare']:5.1f}% bots={r['botsInLog']:2d} rows={r['resultRows']:2d} noRes={r['noResult']} died={r['died']} left={r['left']}(early {r['leftEarly']}, mid {r['leftMid']}, late {r['leftLate']}) other={r['other']} | {r['leftTicks']}")
print('--- totals by cohort')
for c in sorted(set(k[0] for k in tot)):
    print(c, {k[1]: v for k, v in tot.items() if k[0] == c})
