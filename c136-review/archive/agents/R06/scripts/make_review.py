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
import simdigest as SD  # noqa: E402

ROOT = os.path.dirname(HERE)
PROTO_TICKS = [90, 180, 270, 630, 1170, 1530, 2070, 3060, 4050, 4500, 5040, 6030, 7020, 8010, 9000, 9990, 10980, 11970, 12960, 13950]


def team_rank(tot, team):
    """结算快照里 team 的名次（不含 0 队=内置 AI）。"""
    items = sorted(((v, k) for k, v in tot.items() if str(k) != '0'), reverse=True)
    for i, (_, k) in enumerate(items):
        if str(k) == str(team):
            return i + 1
    return None


def truth_timeline_row(X, t, primary):
    """真引擎重放在 t 拍的编队与各队真值。"""
    S = X.S
    i = X.ix(t)
    tt = S['ticks'][i]
    tl, tb, th, tk = S['teamLand'][i], S['teamBal'][i], S['teamHumans'][i], S['teamHusk'][i]
    act = [p for p in X.squad if X.alive_active(p, tt)]
    husk = [p for p in X.squad if not X.alive_active(p, tt) and not (X.deathT[p] >= 0 and tt >= X.deathT[p])]
    land = sum(S['hum'][p]['terr'][i] for p in act)
    troops = sum(S['hum'][p]['bal'][i] for p in act)
    per = defaultdict(lambda: [0, 0, 0])
    for p in act:
        per[X.team[p]][0] += 1
        per[X.team[p]][1] += S['hum'][p]['terr'][i]
        per[X.team[p]][2] += S['hum'][p]['bal'][i]
    boxed = 0
    for p in act:
        ns = [n for n in X.neigh[p] if n['t'] <= tt]
        if ns and tt - ns[-1]['t'] <= 90:
            ec = SD.enemy_contact(X, ns[-1])
            if ec['enemy'] == 0 and ns[-1]['neut'] == 0:
                boxed += 1
    nT = S['nTeams']
    order = sorted(range(1, nT + 1), key=lambda k: -tl[k])
    row = dict(t=tt, alive=len(act), seen=len(act), husks=len(husk), squadLand=land, squadLandShare=round(land / X.land, 4), teamTroops=troops,
               squadDens=round(troops / land, 1) if land else 0, boxed=boxed, squadHuskLand=sum(S['hum'][p]['terr'][i] for p in husk),
               perTeam={str(k): dict(bots=v[0], land=v[1], troops=v[2]) for k, v in sorted(per.items())},
               allTeams={str(k): dict(landShare=round(tl[k] / X.land, 4), troops=tb[k], activeHumans=th[k], huskLandShare=round(tk[k] / X.land, 4)) for k in range(1, nT + 1)},
               aiLandShare=round(tl[0] / X.land, 4), src='engine-replay')
    if primary is not None and 1 <= int(primary) <= nT:
        pr = int(primary)
        row['teamLandShare'] = round(tl[pr] / X.land, 4)
        row['teamRank'] = order.index(pr) + 1
        en = [k for k in order if k != pr]
        row['topEnemyTeam'] = en[0] if en else None
        row['topEnemyShare'] = round(tl[en[0]] / X.land, 4) if en else None
    return row


def truth_death(X, me, T):
    """阵亡号的真值死因链材料。"""
    S = X.S
    tot, tk = SD.takers(X, me, T - 900, T + 1)
    dtot, dk = SD.takers(X, me, T - 900, T + 1, kind='dmg')
    led = SD.ledger_totals(X, me, T - 900, T + 1)
    cm = [c for c in S['squadCmds'] if c['p'] == me and T - 600 <= c['t'] <= T]
    on = defaultdict(lambda: [0, 0, 10 ** 9, 0])
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c.get('to') == me and T - 600 <= c['t'] <= T and c['ok']:
            a = on[c['p']]
            a[0] += 1
            a[1] += c['sent']
            a[2] = min(a[2], c['t'])
            a[3] = max(a[3], c['t'])
    ns = [n for n in X.neigh[me] if T - 400 <= n['t'] < T]
    return dict(
        landTakenLast900=[dict(by=X.name(o), cls=X.cls(me, o, T), cells=v) for o, v in tk],
        troopsKilledLast900=[dict(by=X.name(o), troops=v) for o, v in dk],
        ledgerLast900={SD.KIND_CN[k]: v for k, v in led.items() if v},
        ownCmdsLast600=[f"t{c['t']}:{c['k']}{'→' + X.name(c['to']) if c.get('to') is not None and c['k'] == 'atk' else ''} {c.get('pct', '')}‰ 出{c['sent']}{'' if c['ok'] else '(空)'}" for c in cm[-12:]],
        ownCmdCountLast600=len(cm),
        attackCmdsOnMeLast600=[f"{X.name(a)}[{X.cls(me, a, T)}]×{v[0]} 共{v[1]}兵 t{v[2]}~{v[3]}" for a, v in sorted(on.items(), key=lambda kv: -kv[1][1])],
        donationsInLast900=[f"{X.name(x['from'])}@{x['t']} +{x['delivered']}(费{x['fee']})" for x in S['donations'] if x['to'] == me and x['ok'] and T - 900 <= x['t'] <= T],
        donationsOutLast900=[f"→{X.name(x['to'])}@{x['t']} {x['delivered']}(费{x['fee']})" for x in S['donations'] if x['from'] == me and x['ok'] and T - 900 <= x['t'] <= T],
        neighborsBeforeDeath=[SD.neigh_line(X, n) for n in ns[-2:]],
    )


def facts(M, X=None):
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
        teamSplitSource='replay-header-recompute' if M.teamInfo else ('results+donation-log' if getattr(M, 'teamInferred', None) else 'results-only'),
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
    if X:
        # 真值：分队、离开拍
        split_true = Counter(X.team[p] for p in X.squad)
        ctx['teamSplitTrue'] = {str(k): v for k, v in sorted(split_true.items())}
        ctx['teamSplitSource'] = 'engine-replay(bj.fX)'
        ctx['leftTicks'] = {M.bots[p].name: X.leave[p]['t'] for p in sorted(X.leave, key=lambda q: X.leave[q]['t']) if p in X.squad and p in M.bots}
        ctx['huskDeaths'] = [dict(bot=M.bots[p].name, me=p, team=X.team[p], leftT=X.leave[p]['t'], diedT=X.deathT[p],
                                  landTakenLast900=[dict(by=X.name(o), cls=X.cls(p, o, X.deathT[p]), cells=v) for o, v in SD.takers(X, p, X.deathT[p] - 900, X.deathT[p] + 1)[1][:3]])
                             for p in X.squad if p in X.leave and X.deathT[p] >= 0 and p in M.bots]
        c = X.S['check']
        ctx['dataCompleteness']['truth'] = f"真引擎重放（录像 {M.replaySrc}）到 t={X.endT}；日志快照指纹 {c['exact']}/{c['points']} 逐兵一致"
        ctx['truthEnd'] = X.endT
        # 真值时间线：协议拍 + 在场号的真实阵亡拍 + 重放末拍；同一个采样拍只留一行
        d_truth = sorted({X.deathT[p] for p in X.squad if X.deathT[p] >= 0 and not (p in X.leave and X.leave[p]['t'] <= X.deathT[p])})
        t_truth = sorted(set(t for t in PROTO_TICKS if t <= X.endT) | set(d_truth) | {X.endT})
        seen_t = set()
        for t in t_truth:
            row = truth_timeline_row(X, t, primary)
            if row['t'] in seen_t:
                continue
            seen_t.add(row['t'])
            tl.append(row)
        ticks = [t for t in ticks if t > X.endT + 30]
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
        if X and X.deathT[me] >= 0:
            d = deaths[-1]
            d['tLog'] = d['t']
            d['t'] = X.deathT[me]
            d['truth'] = truth_death(X, me, X.deathT[me])
            d['killers'] = [f"{k['by']}[{k['cls']}] 拿走 {k['cells']} 格" for k in d['truth']['landTakenLast900']]
            pt = X.S.get('perTick') or {}
            if str(me) in (pt.get('terr') or {}):
                # 峰值领土用重放逐拍真值（日志快照 90 拍一条，会漏掉两条快照之间的峰）
                d['peakLandLog'] = d['peakLand']
                d['peakLand'] = max(pt['terr'][str(me)])
                # 清地前一拍的领土/余额（重放逐拍真值；balanceAtDeath 是日志最后一条快照里的余额，会早几拍到几十拍）
                i = d['t'] - 1 - pt.get('t0', 0)
                if 0 <= i < len(pt['terr'][str(me)]):
                    d['landBeforeClear'] = pt['terr'][str(me)][i]
                    d['balanceBeforeClear'] = pt['bal'][str(me)][i]
    out = dict(context=ctx, outcome=outcome, timeline=tl, deaths=deaths)
    if X:
        S = X.S
        ok = [x for x in S['donations'] if x['ok'] and x['from'] in X.squad]
        small = [x for x in ok if x['pct'] < 150]
        husk = [x for x in ok if x['toLeft']]
        G = [g for g in (S.get('boatGifts') or []) if g['from'] in X.squad]
        pr = SD.probe_rows(X)
        out['truthSummary'] = dict(
            source=ctx['dataCompleteness']['truth'],
            donationsExecuted=dict(n=len(ok), delivered=sum(x['delivered'] for x in ok), fee=sum(x['fee'] for x in ok),
                                   smallPctN=len(small), smallPctDelivered=sum(x['delivered'] for x in small), smallPctFee=sum(x['fee'] for x in small),
                                   toHuskN=len(husk), toHuskDelivered=sum(x['delivered'] for x in husk), toHuskFee=sum(x['fee'] for x in husk)),
            donationLogVerdicts=dict(Counter(r['verdict'] for r in pr)),
            boatGiftsOut=dict(n=len(G), troops=sum(g['troops'] for g in G), delivered=sum(g['delivered'] for g in G)),
            ledgerTotals={M.bots[p].name if p in M.bots else str(p): {SD.KIND_CN[k]: v for k, v in SD.ledger_totals(X, p).items() if v} for p in X.squad},
        )
    return out


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
    X = SD.Sim(mid, M) if M.sim else None
    F = facts(M, X)
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
    if 'truthSummary' in F:
        doc['truthSummary'] = F['truthSummary']
    # 延迟账 / 好地账：latency.py <id> json、landcap.py <id> json 的原样输出（有才带）
    for key, fn in (('latencyLedger', 'latency.json'), ('landLedger', 'landcap.json')):
        p = os.path.join(ROOT, 'out', mid, fn)
        if os.path.exists(p):
            doc[key] = json.load(open(p))
    for k in ('latencyNotes', 'landNotes'):
        if k in A:
            doc[k] = A[k]
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
    doc['scripts'] = A.get('scripts') or ([
        f"node c136-review/agents/R06/scripts/replay_decode.mjs {mid}（套 run-heavy.sh）",
        f"python3 c136-review/agents/R06/scripts/team_assign.py {mid}",
    ] + ([
        f"bash c136-review/agents/R06/scripts/run_truth.sh {mid}（sim_prep.py + eng_replay.cjs：真引擎重放，写 out/{mid}/sim_state.json）",
        f"python3 c136-review/agents/R06/scripts/simdigest.py {mid} check|teams|roster|ledger [me]|deaths [me]|don|probe|gifts|boats [me]|landings|fees|nfs|cmds|cmdlist <me> [t0 t1]|pair <me> [t0 t1]|neigh <me>|front|boxed|gaps|husks|poolai|protbox|medians [前缀]|dens [t]|shadow|gates|dups|crowd|bursts|collapse|lumps|top [t] [n]|pokes|boatwar",
        f"node c136-review/agents/R06/scripts/strat_probe.mjs {mid} --me squad --json --tally [--dump 玩家:起拍:止拍:步长,...]（套 run-heavy.sh；影子策略：同一份策略源码逐拍跑在重放局面上，打印 buyLand 逐报价的 c/worth/safe/keep/avail 和出口行号）",
    ] if X else []) + [
        f"python3 c136-review/agents/R06/scripts/digest.py {mid} roster|teams|timeline|deaths|donations -v|drops|spawn|boxed|attacks|lag|teamwar|bot <me>|json",
        f"python3 c136-review/agents/R06/scripts/digest.py {mid} picks（选点指令真值：改点次数、最后两步的改点、撞点）",
        f"python3 c136-review/agents/R06/scripts/logdigest.py {mid} stale|silent|seqlag|wall|overcap|drop30|oplag|issued|json（只用日志快照的事实：发令不见效→集中清仓、零指令时段、本地拍落后、墙上时钟对拍、超软上限、全量 DROP30）",
        f"python3 c136-review/agents/R06/scripts/make_review.py {mid}",
    ])
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
