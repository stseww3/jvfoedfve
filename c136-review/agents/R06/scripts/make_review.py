#!/usr/bin/env python3
"""make_review.py — 把「脚本重算的事实」和「人工写的分析」合成一份复盘 JSON，并用汇总脚本的清单自检。

用法：
    python3 make_review.py <matchId>           # 读 ../reviews_src/<matchId>.py（变量 A），写 ../reviews/<matchId>.json
    python3 make_review.py <matchId> --facts   # 只打印脚本算出的事实骨架（写分析前先看）

事实骨架（context / outcome / timeline / deaths 的数字部分）全部由 r06lib + digest 从对局包重算；
分析部分（phases / turningPoints / 死因 / decisions / newPatterns / …）来自 reviews_src/<matchId>.py。
"""
import importlib.util
import sys as _sys
_sys.dont_write_bytecode = True  # 不往 c136-review/tools/__pycache__ 里写东西（只许写自己的目录）
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import load_match, pname, pteam, donation_truth  # noqa: E402
import digest as D  # noqa: E402

ROOT = os.path.dirname(HERE)
PROTO_TICKS = [90, 180, 270, 630, 1170, 1530, 2070, 3060, 4050, 4500, 5040, 6030, 7020, 8010, 9000, 9990, 10980, 11970, 12960, 13950]


def team_rank(tot, team):
    """结算快照里 team 的名次（不含 0 队=内置 AI）。"""
    items = sorted(((v, k) for k, v in tot.items() if str(k) != '0'), reverse=True)
    for i, (_, k) in enumerate(items):
        if str(k) == str(team):
            return i + 1
    return None


def facts(M):
    card = M.card
    pres = D.presence(M)
    primary = card.get('ourPrimaryTeam')
    split_true = Counter(M.bots[me].team for me in M.squad if M.bots[me].team)
    how = Counter(p['how'] for p in pres.values())
    lv = {me: p['leaveT'] for me, p in pres.items() if p['how'] == 'left'}
    never_played = [me for me in M.squad if pres[me]['how'] == 'left' and not any(c['player'] == me and c['id'] == 1 for c in M.cmds)] if M.cmds else []
    ctx = dict(
        time=card.get('timeUtc'), squad=card.get('cohort'), bots=len(M.squad), strategyVersion='v27-team-c110', gameVersion='2.17.1',
        map=card.get('mapId'), mapSeed=card.get('mapSeed'), mapLand=M.land, teams=card.get('actualTeams'), humans=M.humans or card.get('seededPlayers'),
        ourTeam=primary,
        teamSplitTrue={str(k): v for k, v in sorted(split_true.items(), key=lambda kv: str(kv[0]))},
        teamSplitSource='replay-header-recompute' if M.teamInfo else 'results-only',
        teamSplitCard=card.get('teamSplitCounts'),
        presence=dict(how),
        leftTicks={M.bots[me].name: t for me, t in sorted(lv.items(), key=lambda kv: kv[1] or 0)},
        neverPlayed=[M.bots[me].name for me in never_played],
        sameMatchPeer=(card.get('sameMatchPeer') or {}).get('peerMatchId'),
        dataCompleteness=dict(results=bool(M.results), squadLog=True,
                              truth=(f"replay({M.replaySrc}) to t={M.replayLast}" if M.cmds else ('replay spawn-phase only' if M.replay else 'none'))),
        contamination=[],
    )
    oc = card.get('outcome') or {}
    final_snap = M.teamSnaps[-1] if M.teamSnaps else None
    result = 'won' if oc.get('primaryTeamWon') else ('lost' if oc.get('winnerTeam') else 'over')
    outcome = dict(result=result, resultLabel=oc.get('resultLabel'), anyBotWon=oc.get('anyBotWon'), ourTeamRank=team_rank(final_snap['totals'], primary) if final_snap else None,
                   winnerTeam=oc.get('winnerTeam'), endTick=M.endTick, ourFinalShare=oc.get('ourFinalTeamShare'),
                   peakSquadLandShare=oc.get('peakSquadLandShare'), peakPrimaryTeamShareSeen=oc.get('peakPrimaryTeamShareSeen'))
    deaths_t = sorted({p['outT'] for p in pres.values() if p['how'] == 'died' and p['outT']})
    ticks = sorted(set([t for t in PROTO_TICKS if t <= M.endTick + 60]) | set(deaths_t) | {M.endTick})
    tl = []
    for r in D.timeline_rows(M, ticks):
        row = dict(t=r['t'], alive=r['active'], seen=r['seen'], squadLand=r['terr'], squadLandShare=round(r['share'], 4), teamTroops=r['bal'],
                   squadDens=round(r['dens'], 1), boxed=r['boxed'],
                   perTeam={str(k): dict(bots=v[0], land=v[1], troops=v[2]) for k, v in sorted(r['perTeam'].items(), key=lambda kv: str(kv[0]))},
                   teamLandShare=None, teamRank=None, topEnemyTeam=None, topEnemyShare=None)
        s = r['teamSnap']
        if s:
            tot = s['totals']
            row['teamSnapT'] = s['t']
            if primary is not None and str(primary) in {str(k) for k in tot}:
                mine = [v for k, v in tot.items() if str(k) == str(primary)][0]
                row['teamLandShare'] = round(mine / M.land, 4)
                row['teamRank'] = team_rank(tot, primary)
            en = sorted(((v, k) for k, v in tot.items() if str(k) not in ('0', str(primary))), reverse=True)
            if en:
                row['topEnemyTeam'] = int(en[0][1]) if str(en[0][1]).isdigit() else en[0][1]
                row['topEnemyShare'] = round(en[0][0] / M.land, 4)
        tl.append(row)
    deaths = []
    for me in M.squad:
        p = pres[me]
        if p['how'] != 'died':
            continue
        b = M.bots[me]
        T = p['outT']
        win = [s for s in b.traj if T - 620 <= s['t'] <= T]
        inc = defaultdict(list)
        for c in D.cmds_on(M, me, T - 620, T + 5):
            if c['id'] == 1:
                inc[c['player']].append(c)
        killers = [f"{pname(M, k)}/T{pteam(M, k)}×{len(v)}(t{v[0]['t']}~{v[-1]['t']},均{sum(100 * (c['dX'] + 1) / 1024 for c in v) / len(v):.0f}%)"
                   for k, v in sorted(inc.items(), key=lambda kv: -len(kv[1]))]
        mine = D.cmds_of(M, me, T - 620, T + 5)
        rcv = [c for c in D.cmds_on(M, me, T - 620, T + 5) if c['id'] == 2]
        dons = [e for e in b.donations if T - 620 <= e['t'] <= T]
        resc = []
        for o in M.squad:
            for e in M.bots[o].donations:
                if e['to'] == me and T - 620 <= e['t'] <= T:
                    resc.append(f"{M.bots[o].name}@{e['t']}{e['kind'][0]}{e['pct']}")
        ast = []
        for o in M.squad:
            for e in M.bots[o].assists:
                if e['ally'] == me and T - 620 <= e['t'] <= T:
                    ast.append(f"{M.bots[o].name}@{e['t']}→{e['enemyName']}")
        deaths.append(dict(
            bot=b.name, me=me, team=b.team, t=T, peakLand=max([s['terr'] for s in b.traj], default=0),
            killers=killers if (inc or M.replayLast >= T) else ['录像没覆盖'],
            densityLast500=[[s['t'], s['terr'], s['bal'], round(s['dens'])] for s in win],
            lastDecisions=[D.fmt_cmd(M, c) for c in mine[-10:]] if M.replayLast >= T - 300 else [f"cmds {win[0]['cmds']}→{win[-1]['cmds']} boats {win[0]['boats']}→{win[-1]['boats']}"] if win else [],
            donationsReceivedReplay=[f"{pname(M, c['player'])}@{c['t']}p{c['dX']}" for c in rcv] if M.replayLast >= T else None,
            rescueLogsForMe=resc, assistsForMe=ast,
            stillDonating=[f"{e['kind'][0]}{e['pct']}→{pname(M, e['to'])}@{e['t']}" for e in dons],
            balanceAtDeath=(b.result or {}).get('balance'),
            cause='', patternIds=[]))
    return dict(context=ctx, outcome=outcome, timeline=tl, deaths=deaths)


def load_collector():
    path = os.path.join(os.path.dirname(os.path.dirname(ROOT)), 'tools', 'collect-reviews.py')
    spec = importlib.util.spec_from_file_location('collect_reviews', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    M = load_match(mid)
    F = facts(M)
    if '--facts' in sys.argv:
        print(json.dumps(F, ensure_ascii=False, indent=1, default=str))
        return 0
    src = os.path.join(ROOT, 'reviews_src', f'{mid}.py')
    spec = importlib.util.spec_from_file_location(f'src_{mid}', src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    A = mod.A
    doc = dict(matchId=mid, reviewer='R06', protocol='v2.0')
    ctx = F['context']
    ctx['contamination'] = A.get('contamination', [])
    ctx.update(A.get('contextExtra', {}))
    doc['context'] = ctx
    oc = F['outcome']
    oc.update(A.get('outcomeExtra', {}))
    doc['outcome'] = oc
    doc['timeline'] = F['timeline']
    doc['phases'] = A['phases']
    doc['turningPoints'] = A['turningPoints']
    dc = A.get('deathCauses', {})
    for d in F['deaths']:
        a = dc.get(d['me']) or dc.get(d['bot']) or {}
        d['cause'] = a.get('cause', '')
        d['patternIds'] = a.get('patternIds', [])
        if a.get('statementType'):
            d['statementType'] = a['statementType']
    doc['deaths'] = F['deaths']
    doc['decisions'] = A['decisions']
    doc['newPatterns'] = A['newPatterns']
    doc['lossArchetype'] = A['lossArchetype']
    for k in ('secondaryArchetype', 'teamSplit', 'externalFactors'):
        if k in A:
            doc[k] = A[k]
    doc['winnerNotes'] = A['winnerNotes']
    doc['wentWell'] = A['wentWell']
    doc['unknowns'] = A['unknowns']
    doc['mechanicsQuestions'] = A['mechanicsQuestions']
    doc['scripts'] = A.get('scripts') or [
        f"node c136-review/agents/R06/scripts/replay_decode.mjs {mid}（套 run-heavy.sh）",
        f"python3 c136-review/agents/R06/scripts/team_assign.py {mid}",
        f"python3 c136-review/agents/R06/scripts/digest.py {mid} roster|teams|timeline|deaths|donations -v|drops|spawn|boxed|attacks|lag|teamwar|bot <me>|json",
        f"python3 c136-review/agents/R06/scripts/make_review.py {mid}",
    ]
    doc['confidenceOverall'] = A['confidenceOverall']
    os.makedirs(os.path.join(ROOT, 'reviews'), exist_ok=True)
    out = os.path.join(ROOT, 'reviews', f'{mid}.json')
    with open(out, 'w') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, default=str)
    md_path = os.path.join(ROOT, 'reviews', f'{mid}.md')
    md = open(md_path).read() if os.path.exists(md_path) else None
    col = load_collector()
    fails, stats = col.check_review(doc, md)
    print(f"写入 reviews/{mid}.json；自检未过项 {len(fails)}：{fails}")
    print(f"统计：{json.dumps(stats, ensure_ascii=False)}")
    if md is not None:
        print(f"md 行数 {md.count(chr(10))}")
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
