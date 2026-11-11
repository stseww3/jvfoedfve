#!/usr/bin/env python3
# review_base.py — 生成一局复盘 JSON 里「纯数字」的部分（context / outcome / timeline / deaths 骨架），
# 数字全部来自真引擎重放的真相表（tmp/truth/<局号>/）和对局包，不手抄。
# 用法：python3 scripts/review_base.py <局号> [--ours 1,2,3] > tmp/review/<局号>.base.json
# 复盘正文（阶段判断、转折点、决策审计）由 scripts/review_write.py 读这个骨架再合并人工写的部分。
import sys, os, json, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match  # noqa: E402


def pct(a, b):
    return round(100.0 * a / b, 2) if b else 0.0


def main():
    a = sys.argv[1:]
    mid = a[0]
    ov = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ov)
    ku, ke = M.ku, M.ke
    info = M.meta['info']
    teams = sorted(t for t in set(M.team[p] for p in range(ku)) if t > 0)
    tsz = collections.Counter(M.team[p] for p in range(ku))
    card = M.card
    our = M.our_ids
    # 时间线检查拍：规程点 + 每 ~750 拍一个 + 我方号出局拍 + 终局
    pts = [90, 180, 270, 450, 630, 1080, 1530, 2250, 3060, 3780, 4500, 5220, 6030, 6750, 7500, 8250, 9000, 9750, 10500, 11250, 12000]
    pts = [t for t in pts if t <= M.last]
    for p in our:
        if p in M.dead:
            pts.append(M.dead[p][0])
    pts.append(M.last)
    pts = sorted(set(M.at(t) for t in pts))
    tl = []
    for t in pts:
        st = M.state[t]
        tt = M.teamts.get(t, {})
        alive = [p for p in our if st.get(p) and st[p][7] and st[p][0] > 0]
        sq_terr = sum(st[p][0] for p in alive)
        sq_bal = sum(st[p][1] for p in alive)
        playing = [p for p in alive if st[p][8] != 2]
        row = {
            't': t,
            'squadAlive': len(alive),
            'squadPlaying': len(playing),
            'squadTerr': sq_terr,
            'squadSharePct': pct(sq_terr, ke),
            'squadBal': sq_bal,
            'squadDens': round(sq_bal / sq_terr, 1) if sq_terr else 0,
            'teamSharePct': {str(k): pct(tt[k][0], ke) for k in teams if k in tt},
            'teamBal': {str(k): tt[k][1] for k in teams if k in tt},
            'teamHumansPlaying': {str(k): tt[k][3] for k in teams if k in tt},
        }
        if M.our_team in tt:
            row['ourTeamSharePct'] = pct(tt[M.our_team][0], ke)
            others = [(tt[k][0], k) for k in teams if k in tt and k != M.our_team]
            if others:
                top = max(others)
                row['topEnemyTeam'] = top[1]
                row['topEnemySharePct'] = pct(top[0], ke)
            row['squadShareOfTeamPct'] = pct(sq_terr, tt[M.our_team][0])
        # 我方号在全部在场真人里的名次中位
        hum = sorted(((st[p][0], p) for p in range(ku) if st.get(p) and st[p][7] and st[p][0] > 0), reverse=True)
        rank = {p: i + 1 for i, (_, p) in enumerate(hum)}
        rk = sorted(rank[p] for p in alive)
        if rk:
            row['squadRankMedian'] = rk[len(rk) // 2]
            row['humansAlive'] = len(hum)
        tl.append(row)
    # 出局骨架
    deaths = []
    for p in our:
        if p not in M.dead:
            continue
        t, terr, bal, det = M.dead[p]
        fl = M.flows(max(0, t - 300), t)
        takers = collections.Counter()
        for (x, y), px in fl.items():
            if x == p and y != p:
                takers[y] += px
        peak = max((v[0] for tt2, v in M.our[p].items() if tt2 <= t), default=0)
        peak_t = min((tt2 for tt2, v in M.our[p].items() if v[0] == peak and tt2 <= t), default=0)
        don_in = [c for c in M.cmd if c['id'] == 2 and c.get('q') == p and t - 500 <= c['t'] <= t]
        don_out = [c for c in M.cmd if c['id'] == 2 and c['p'] == p and t - 500 <= c['t'] <= t]
        deaths.append({
            'bot': M.nm(p), 'p': p, 't': t, 'detail': det,
            'peakTerr': peak, 'peakTick': peak_t,
            'last300Takers': [{'who': M.nm(q), 'px': v} for q, v in takers.most_common(4)],
            'donationsIn500': {'n': len(don_in), 'credited': sum(c['balQ1'] - c['balQ0'] for c in don_in)},
            'donationsOut500': {'n': len(don_out), 'left': sum(c['bal0'] - c['bal1'] for c in don_out)},
            'cause': '',
        })
    left = [{'bot': M.nm(p), 'p': p, 't': M.left[p][0]} for p in our if p in M.left]
    res = card.get('outcome') or {}
    fin = M.teamts.get(M.at(M.last), {})
    out = {
        'matchId': mid,
        'reviewer': 'R04',
        'protocol': '2.0',
        'context': {
            'strategyVersion': None,
            'cohort': card.get('cohort') or card.get('squad'),
            'map': info.get('map'), 'mapSize': [info.get('w'), info.get('h')], 'mapLand': ke,
            'humans': ku, 'players': info.get('players'),
            'teams': {str(k): tsz[k] for k in teams},
            'actualTeams': len(teams), 'cardActualTeams': card.get('actualTeams'),
            'ourTeam': M.our_team, 'ourBots': len(our),
            'teamSplit': dict(collections.Counter(str(M.team[p]) for p in our)),
            'baselineWinRate': round(1.0 / len(teams), 3) if teams else None,
        },
        'outcome': {
            'result': None, 'endTick': M.last,
            'cardOutcome': res if isinstance(res, (str, dict)) else str(res),
            'ourTeamFinalSharePct': pct(fin[M.our_team][0], ke) if M.our_team in fin else None,
            'squadPeakSharePct': max(r['squadSharePct'] for r in tl) if tl else None,
            'botsDead': len(deaths), 'botsLeft': left,
        },
        'timeline': tl,
        'deaths': deaths,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == '__main__':
    main()
