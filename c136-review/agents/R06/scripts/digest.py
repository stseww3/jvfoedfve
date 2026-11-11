#!/usr/bin/env python3
"""digest.py — 单局复盘用的事实摘要（全部数字由此脚本从对局包重算）。

用法：
    python3 digest.py <matchId> roster      # 20 个号的身份、队号、出生点、在场区间（离开/阵亡/终局）、指令数
    python3 digest.py <matchId> teams       # 全员分队（引擎算法重算）、各队里我方号与战队、结算时刻的各队领土
    python3 digest.py <matchId> timeline [t ...]   # 里程碑拍（或指定拍）的编队合计 + 分队小计
    python3 digest.py <matchId> outsiders   # 结算行的各队份额拆成「我方在场号」+「其余」
    python3 digest.py <matchId> snap [t ...]       # 指定拍的横截面：每个在场号的地/兵/密度/nb/neut，加中位、最小、最大
    python3 digest.py <matchId> bot <me> [t0 t1]   # 单号逐快照故事 + 录像指令（出兵/被打/捐款收发/船）
    python3 digest.py <matchId> deaths      # 每个阵亡号死前 600 拍
    python3 digest.py <matchId> donations   # 捐款台账：录像真值（接受/被拒）、手续费、到账、额度点
    python3 digest.py <matchId> drops       # 兵力跌 30% 以上的区间与去向
    python3 digest.py <matchId> spawn       # 出生几何
    python3 digest.py <matchId> picks       # 选点指令（录像真值）：每号改点次数、最后两步的改点、撞点
    python3 digest.py <matchId> spawnlog    # 有录像的局：日志最后一条 HL-SPAWN 是不是真正的出生点（给没有录像的局校准）
    python3 digest.py <matchId> boxed       # 被围（nb=0,neut=0）高密度滞留
    python3 digest.py <matchId> attacks [t0 t1]    # 我方各号被谁打 / 打了谁（录像）
    python3 digest.py <matchId> json        # 写 out/<matchId>/digest.json（复盘 JSON 的数字来源）
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import (OUT, load_match, pname, pteam, donation_truth, heuristic_rejected, donation_fee, donation_amount,  # noqa: E402
                    donation_efficiency, quota_limit, quota_points, attack_amount, attack_fee, interest_rate, is_squad_name, clan_tag)

MILESTONES = [90, 180, 270, 450, 630, 900, 1170, 1530, 2070, 2520, 3060, 3510, 4050, 4500, 5040, 6030, 7020, 8010, 9000, 9990, 10980, 11970, 12960, 13950]


def presence(M):
    """每个号的在场区间：leaveT（录像里的离开指令，或结算 left）、deathT、endT、lastSnap。"""
    leave_cmd = {}
    for c in M.cmds:
        if c['id'] in (8, 9) and c['player'] not in leave_cmd:
            leave_cmd[c['player']] = c['t']
    out = {}
    for me in M.squad:
        b = M.bots[me]
        r = b.result
        last_snap = b.traj[-1]['t'] if b.traj else 0
        rec = dict(lastSnap=last_snap, leaveT=None, deathT=None, endT=None, how='?', leaveSrc=None)
        if me in leave_cmd:
            rec['leaveT'] = leave_cmd[me]
            rec['leaveSrc'] = 'replay'
            rec['how'] = 'left'
        if r:
            if r['event'] == 'died':
                rec['deathT'] = r['tick']
                rec['how'] = 'died'
            elif r['event'] == 'end':
                rec['endT'] = r['tick']
                rec['how'] = 'end'
            elif r['event'] == 'left' and rec['leaveT'] is None:
                rec['leaveT'] = max(r['tick'], last_snap)
                rec['leaveSrc'] = 'result(本机拍,偏早)'
                rec['how'] = 'left'
        if rec['how'] == '?':
            # 没有结算也没有离开指令：录像没覆盖时只能说「日志到某拍为止」
            rec['how'] = 'silent'
        rec['outT'] = rec['leaveT'] if rec['how'] == 'left' else rec['deathT'] if rec['how'] == 'died' else rec['endT'] if rec['how'] == 'end' else None
        out[me] = rec
    return out


def active_at(M, pres, me, t):
    """t 拍时这个号是否还在打（没离开、没阵亡）。silent 的号按最后快照 + 180 拍算。"""
    p = pres[me]
    if p['how'] == 'silent':
        return t <= p['lastSnap'] + 180 and p['lastSnap'] > 0
    if p['outT'] is None:
        return True
    if p['how'] == 'end':
        return t <= p['outT'] + 60      # 活到终局的号在终局那一行仍算在场
    return t < p['outT']


def cmd_counts(M):
    by = defaultdict(Counter)
    first, last = {}, {}
    for c in M.cmds:
        by[c['player']][c['id']] += 1
        first.setdefault(c['player'], c['t'])
        last[c['player']] = c['t']
    return by, first, last


def opening_check(M):
    out = {}
    for raw in M.other:
        if '[OPENING-CHECK' not in raw:
            continue
        head, _, body = raw.partition('] ')
        for part in body.split(' | '):
            name, _, rest = part.partition(':')
            out[name.strip()] = rest.strip()
        out['__head__'] = head.split('\t')[-1] + ']'
    return out


def sec_roster(M):
    pres = presence(M)
    by, first, last = cmd_counts(M)
    oc = opening_check(M)
    print(f"== {M.id} roster：INIT {len([b for b in M.bots.values() if b.init])} 个号；录像源 {M.replaySrc} 覆盖到 t={M.replayLast}（终局 {M.endTick}）；真人 {M.humans}；地图陆地 {M.land}；mapW={M.mapW}")
    print(f"   开局检查：{oc.get('__head__', '无')}；改名推断：{M.inferredRenames}；解析不出的名字：{ {k: len(v) for k, v in M.unresolved.items()} }")
    hdr = "me  名字(曾用名)                 队 出生(x,y)    开局检查                 快照 末快照t   末地  峰值地  去向        指令[攻/捐/船/撤]  结算"
    print(hdr)
    for me in M.squad:
        b = M.bots[me]
        p = pres[me]
        r = b.result
        xy = M.spawnXY.get(me) or ((b.spawns[-1]['x'], b.spawns[-1]['y']) if b.spawns else None)
        peak = max([s['terr'] for s in b.traj], default=0)
        if r and r.get('peak'):
            peak = max(peak, r['peak'])
        c = by.get(me, {})
        where = f"{p['how']}@{p['outT']}" if p['outT'] is not None else p['how']
        ocs = next((oc[n] for n in b.names if n in oc), '-')
        res = f"{r['event']}@{r['tick']} {r['seconds']}s sent={r['sent']}/{r['accepted']} place={r['place']}" if r else '-'
        ls = b.traj[-1] if b.traj else None
        print(f"{me:<3} {('/'.join(b.names))[:28]:<28} {str(b.team):<2} {str(xy):<12} {ocs[:24]:<24} {len(b.traj):>3} {ls['t'] if ls else '-':>6} {ls['terr'] if ls else '-':>6} {peak:>6}  {where:<11} {c.get(1, 0)}/{c.get(2, 0)}/{c.get(3, 0)}/{c.get(5, 0) + c.get(6, 0)} 末指令t={last.get(me, '-')}  {res}")
    hows = Counter(p['how'] for p in pres.values())
    early = sorted((p['outT'], M.bots[me].name) for me, p in pres.items() if p['how'] == 'left')
    print(f"   去向统计：{dict(hows)}；离开时刻：{early}")


def team_table(M):
    """各队：真人数、我方号、带标签战队（>=2 人）、名字在 c110 名字池里的外人。"""
    if not M.teamInfo:
        return None
    ti = M.teamInfo
    T = ti['teams']
    rows = {}
    for t in range(1, T + 1):
        mem = [p for p in range(M.humans) if ti['team'][p] == t]
        ours = [p for p in mem if p in M.bots]
        clans = Counter(clan_tag(M.names[p]) for p in mem if clan_tag(M.names[p]))
        pool_out = [M.names[p] for p in mem if p not in M.bots and is_squad_name(M.names[p])]
        rows[t] = dict(humans=len(mem), ours=ours, clans={k: v for k, v in clans.items() if v >= 2}, poolOutsiders=pool_out)
    return rows


def sec_teams(M):
    pres = presence(M)
    tt = team_table(M)
    if tt:
        ti = M.teamInfo
        print(f"== {M.id} teams：实际 {ti['teams']} 队，每队上限 {ti['border']} 真人，内置 AI 入队={ti['botsTeamed']}")
        for t, r in tt.items():
            ours = ' '.join(f"{M.bots[p].name}({pres[p]['how'][0]}{pres[p]['outT'] if pres[p]['outT'] is not None else ''})" for p in r['ours'])
            print(f"  队{t}: 真人 {r['humans']}，我方 {len(r['ours'])} 个 [{ours}]，战队 {r['clans']}，名字池外人 {r['poolOutsiders']}")
        how = Counter(ti['how'][p] for p in M.bots if p < M.humans)
        print(f"  我方入队方式：{dict(how)}（first=第一志愿色，second=第二志愿色，fill=硬塞补位）")
    else:
        obs = Counter(b.teamObserved for b in M.bots.values() if b.teamObserved)
        print(f"== {M.id} teams：没有录像头，只有结算里的队号：{dict(obs)}")
        for me, x in sorted(getattr(M, 'teamInferred', {}).items()):
            print(f"  结算行没带队号、按捐款日志补的：{M.bots[me].name}({me}) → 队{x['team']}（{x['n']} 条捐款日志的另一头都是队{x['team']}：{'、'.join(x['evidence'])}）")
        full = Counter(b.team for b in M.bots.values())
        print(f"  补完后：{dict(sorted(full.items(), key=lambda kv: str(kv[0])))}")
    print("  结算时刻各队领土（份额%）：")
    for s in M.teamSnaps:
        tot = s['totals']
        sm = sum(tot.values())
        desc = ' '.join(f"T{k}={100 * v / M.land:.1f}" for k, v in sorted(tot.items()))
        rr = next((r for r in M.results if r.get('bot') == s['by'] and r.get('tick') == s['t']), None)
        extra = f" 存活玩家 {rr['alivePlayers']} 名次 {rr['place']}" if rr and rr.get('alivePlayers') is not None else ''
        print(f"   t={s['t']:<6} {desc}  (合计 {100 * sm / M.land:.1f}%)  ← {s['by']} 队{s['mine']} {s['event']}{extra}")


def outsider_rows(M):
    """每条结算行（带全场各队领土）：各队份额拆成「我方在场号」与「其余（外人 + 该队内置 AI）」。
    我方部分取各号在结算拍前 200 拍内最近的一条快照（阵亡的那个号按 0 算）。"""
    pres = presence(M)
    rows = []
    for s in M.teamSnaps:
        t = s['t']
        ours = defaultdict(int)
        n = defaultdict(int)
        for me in M.squad:
            if not active_at(M, pres, me, t):
                continue
            x = M.bots[me].at(t, max_age=200)
            r = M.bots[me].result
            if pres[me]['how'] == 'end' and t >= pres[me]['outT'] and r and r.get('territory') is not None:
                x = dict(terr=int(r['territory']))
            if not x:
                continue
            ours[str(M.bots[me].team)] += x['terr']
            n[str(M.bots[me].team)] += 1
        per = {}
        for k, v in s['totals'].items():
            per[str(k)] = dict(total=v, ours=ours.get(str(k), 0), bots=n.get(str(k), 0), others=v - ours.get(str(k), 0))
        rows.append(dict(t=t, by=s['by'], per=per))
    return rows


def sec_outsiders(M):
    print(f"== {M.id} outsiders：结算行的各队领土 = 我方在场号 + 其余（外人和该队内置 AI）。每格：队份额% = 我方%（号数）+ 其余%")
    for r in outsider_rows(M):
        parts = []
        for k, v in sorted(r['per'].items()):
            if k == '0' or v['total'] <= 0:
                continue
            parts.append(f"T{k} {100 * v['total'] / M.land:.1f}={100 * v['ours'] / M.land:.1f}({v['bots']})+{100 * v['others'] / M.land:.1f}")
        print(f"   t={r['t']:<6} " + '  '.join(parts) + f"   ← {r['by']}")


def timeline_rows(M, ticks=None):
    pres = presence(M)
    if ticks is None:
        ticks = [t for t in MILESTONES if t <= M.endTick + 60]
        extra = sorted({p['outT'] for p in pres.values() if p['how'] == 'died' and p['outT']})
        ticks = sorted(set(ticks) | set(extra) | {M.endTick})
    rows = []
    for t in ticks:
        act = [me for me in M.squad if active_at(M, pres, me, t)]
        terr = bal = 0
        seen = 0
        per_team = defaultdict(lambda: [0, 0, 0])
        boxed = 0
        for me in act:
            s = M.bots[me].at(t, max_age=200)
            r = M.bots[me].result
            if pres[me]['how'] == 'end' and t >= pres[me]['outT'] and r and r.get('territory') is not None and r.get('balance') is not None:
                # 终局行：用结算行的领土/余额（最后一条快照可能早几十拍）
                s = dict(s or {}, terr=int(r['territory']), bal=int(r['balance']), nb=(s or {}).get('nb', 1), neut=(s or {}).get('neut', 0))
            if not s:
                continue
            seen += 1
            terr += s['terr']
            bal += s['bal']
            tm = M.bots[me].team
            per_team[tm][0] += 1
            per_team[tm][1] += s['terr']
            per_team[tm][2] += s['bal']
            if s['nb'] == 0 and s['neut'] == 0:
                boxed += 1
        snap = None
        for s in M.teamSnaps:
            if abs(s['t'] - t) <= 150 and (snap is None or abs(s['t'] - t) < abs(snap['t'] - t)):
                snap = s
        rows.append(dict(t=t, active=len(act), seen=seen, terr=terr, share=terr / M.land, bal=bal, dens=(bal / terr if terr else 0), boxed=boxed,
                         perTeam={k: v for k, v in per_team.items()}, teamSnap=snap))
    return rows


def sec_timeline(M, ticks=None):
    rows = timeline_rows(M, ticks)
    print(f"== {M.id} timeline（在场=没离开没阵亡；有读数=200 拍内有快照；合计只算有读数的号）")
    print("t      在场 有读数  编队地   份额%   编队兵      密度  被围  分队小计(队:号数/地/兵)                      结算快照各队份额%")
    for r in rows:
        pt = ' '.join(f"T{k}:{v[0]}/{v[1]}/{v[2]}" for k, v in sorted(r['perTeam'].items(), key=lambda kv: str(kv[0])))
        ts = ''
        if r['teamSnap']:
            tot = r['teamSnap']['totals']
            ts = f"@{r['teamSnap']['t']} " + ' '.join(f"T{k}={100 * v / M.land:.1f}" for k, v in sorted(tot.items()))
        print(f"{r['t']:<6} {r['active']:>3} {r['seen']:>4} {r['terr']:>8} {100 * r['share']:>6.2f} {r['bal']:>10} {r['dens']:>6.1f} {r['boxed']:>3}   {pt:<44} {ts}")


def cmds_of(M, me, t0, t1):
    return [c for c in M.cmds if c['player'] == me and t0 < c['t'] <= t1]


def cmds_on(M, me, t0, t1):
    return [c for c in M.cmds if c['id'] in (1, 2) and c['dZ'] == me and c['player'] != me and t0 < c['t'] <= t1]


def fmt_cmd(M, c, me=None):
    i = c['id']
    if i == 1:
        tgt = c['dZ']
        tm = pteam(M, tgt) if tgt != 512 else ''
        return f"t{c['t']} 攻{pname(M, tgt)}{'/T' + str(tm) if tm not in ('', None) else ''} {100 * (c['dX'] + 1) / 1024:.0f}%"
    if i == 2:
        return f"t{c['t']} 捐→{pname(M, c['dZ'])} pct={c['dX']}"
    if i == 3:
        return f"t{c['t']} 船 {100 * (c['dX'] + 1) / 1024:.0f}%"
    if i == 4:
        return f"t{c['t']} {'召回船' if c['dX'] in (849, 850) else '追船'}"
    if i in (5, 6):
        return f"t{c['t']} 撤回{pname(M, c['dX']) if i == 5 else ''}"
    if i in (8, 9):
        return f"t{c['t']} 离开"
    return f"t{c['t']} id{i}"


def sec_bot(M, me, t0=0, t1=10 ** 9):
    b = M.bots[me]
    pres = presence(M)[me]
    dt = {(e['line']): e for e in donation_truth(M)}
    print(f"== {M.id} bot {me} {b.names} 队{b.team} 去向 {pres['how']}@{pres['outT']} 出生 {M.spawnXY.get(me)}")
    if t0 <= 0 and b.opening:
        print("  开局扩张：" + ' '.join(f"t{o['t']}c{o['cyc']}r{o['rings']}:{o['spend']}/{o['bal']}→{o['terr']}" for o in b.opening))
    prev = None
    for s in b.traj:
        if s['t'] < t0 or s['t'] > t1:
            prev = s
            continue
        a = prev['t'] if prev else 0
        mine = cmds_of(M, me, a, s['t'])
        onme = cmds_on(M, me, a, s['t'])
        atk = Counter()
        for c in mine:
            if c['id'] == 1:
                atk[c['dZ']] += 1
        atk_s = ' '.join(f"{pname(M, k)}{'/T' + str(pteam(M, k)) if k != 512 and pteam(M, k) is not None else ''}×{v}" for k, v in atk.most_common(6))
        boats = sum(1 for c in mine if c['id'] == 3)
        inc = Counter()
        for c in onme:
            if c['id'] == 1:
                inc[c['player']] += 1
        inc_s = ' '.join(f"{pname(M, k)}/T{pteam(M, k)}×{v}" for k, v in inc.most_common(6))
        rcv = [c for c in onme if c['id'] == 2]
        rcv_s = ' '.join(f"{pname(M, c['player'])}@{c['t']}p{c['dX']}" for c in rcv)
        dons = [e for e in b.donations if a < e['t'] <= s['t']]
        don_s = ' '.join(f"{'✓' if dt[e['line']]['accepted'] else '✗' if dt[e['line']]['accepted'] is False else '?'}{e['kind'][0]}{e['pct']}→{pname(M, e['to'])}@{e['t']}(bal{e['myBal']})" for e in dons)
        ast = [e for e in b.assists if a < e['t'] <= s['t']]
        ast_s = ' '.join(f"戳{pname(M, e['enemy'])}为{pname(M, e['ally'])}@{e['t']}" for e in ast)
        dB = (s['bal'] - prev['bal']) if prev else 0
        dT = (s['terr'] - prev['terr']) if prev else 0
        gap = f"(GAP{s['t'] - prev['t']})" if prev and s['t'] - prev['t'] > 90 else ''
        flag = ' DROP30' if prev and prev['bal'] > 0 and dB <= -0.3 * prev['bal'] else ''
        ev = ' | '.join(x for x in [('出兵 ' + atk_s) if atk_s else '', f'船×{boats}' if boats else '', ('被攻 ' + inc_s) if inc_s else '',
                                     ('收捐 ' + rcv_s) if rcv_s else '', ('捐出 ' + don_s) if don_s else '', ast_s] if x)
        print(f"  t{s['t']:<5}{gap} 地{s['terr']:<6}({dT:+d}) 兵{s['bal']:<8}({dB:+d}) 密{s['dens']:<5} nb{s['nb']} neut{s['neut']} cmds{s['cmds']} 船{s['boats']}{flag}  {ev}")
        prev = s
    r = b.result
    if r:
        print(f"  结算：{r['event']}@{r['tick']} territory={r['territory']} peak={r['peak']} balance={r['balance']} sent/accepted={r['sent']}/{r['accepted']} place={r['place']}")
        tail = cmds_of(M, me, (b.traj[-1]['t'] if b.traj else 0), 10 ** 9)
        ontail = cmds_on(M, me, (b.traj[-1]['t'] if b.traj else 0), 10 ** 9)
        if tail or ontail:
            print("  末快照之后：我发 " + '; '.join(fmt_cmd(M, c) for c in tail[:12]) + " ｜ 打我 " + '; '.join(f"t{c['t']} {pname(M, c['player'])}/T{pteam(M, c['player'])} {100 * (c['dX'] + 1) / 1024:.0f}%" for c in ontail if c['id'] == 1)[:600])


def sec_deaths(M):
    pres = presence(M)
    print(f"== {M.id} deaths")
    for me in M.squad:
        p = pres[me]
        if p['how'] != 'died':
            continue
        b = M.bots[me]
        T = p['outT']
        win = [s for s in b.traj if T - 620 <= s['t'] <= T]
        peak500 = max([s['terr'] for s in win], default=0)
        print(f"-- {b.name}({me}) 队{b.team} 阵亡 t={T}；全局峰值地 {max([s['terr'] for s in b.traj], default=0)}；死前 600 拍峰值地 {peak500}")
        print("   快照 t/地/兵/密/nb/neut：" + ' '.join(f"{s['t']}/{s['terr']}/{s['bal']}/{s['dens']:.0f}/{s['nb']}/{s['neut']}" for s in win))
        inc = defaultdict(list)
        for c in cmds_on(M, me, T - 620, T + 5):
            if c['id'] == 1:
                inc[c['player']].append(c)
        if inc:
            print("   死前 600 拍打我的（录像）：" + '; '.join(
                f"{pname(M, k)}/T{pteam(M, k)}×{len(v)}[t{v[0]['t']}~{v[-1]['t']},均{sum(100 * (c['dX'] + 1) / 1024 for c in v) / len(v):.0f}%]" for k, v in sorted(inc.items(), key=lambda kv: -len(kv[1]))))
        elif M.replayLast >= T:
            print("   死前 600 拍录像里没有真人对我下陆攻指令（→ 被内置 AI 或船登陆打死，或领土被切断）")
        else:
            print("   录像没覆盖到这段")
        mine = cmds_of(M, me, T - 620, T + 5)
        if mine:
            print("   我死前 600 拍的指令：" + '; '.join(fmt_cmd(M, c) for c in mine[-14:]))
        rcv = [c for c in cmds_on(M, me, T - 620, T + 5) if c['id'] == 2]
        print(f"   死前 600 拍收到捐款（录像真值）：{len(rcv)} 笔 " + ' '.join(f"{pname(M, c['player'])}@{c['t']}p{c['dX']}" for c in rcv))
        dons = [e for e in b.donations if T - 620 <= e['t'] <= T]
        if dons:
            print("   我死前 600 拍还在捐：" + ' '.join(f"{e['kind']}{e['pct']}→{pname(M, e['to'])}@{e['t']}" for e in dons))
        # 队友针对我的救援捐款日志（含被拒的）
        resc = []
        for o in M.squad:
            for e in M.bots[o].donations:
                if e['to'] == me and T - 620 <= e['t'] <= T:
                    resc.append((e['t'], M.bots[o].name, e['kind'], e['pct'], e['myBal']))
        if resc:
            print("   队友给我发的捐款日志：" + ' '.join(f"{n}@{t}{k[0]}{pc}(bal{bl})" for t, n, k, pc, bl in sorted(resc)))
        ast = []
        for o in M.squad:
            for e in M.bots[o].assists:
                if e['ally'] == me and T - 620 <= e['t'] <= T:
                    ast.append((e['t'], M.bots[o].name, e['enemyName']))
        if ast:
            print("   队友为我发的协防戳：" + ' '.join(f"{n}@{t}→{en}" for t, n, en in sorted(ast)))
        if M.teamSnaps:
            near = min(M.teamSnaps, key=lambda s: abs(s['t'] - T))
            print("   当时各队份额%：" + ' '.join(f"T{k}={100 * v / M.land:.1f}" for k, v in sorted(near['totals'].items())) + f" (t={near['t']})")


def donation_rows(M):
    rows = donation_truth(M)
    for e in rows:
        B = e['myBal']
        e['fee'] = donation_fee(B)
        e['amount'] = donation_amount(B, e['pct'])
        e['eff'] = donation_efficiency(e['pct'])
        rb = M.bots.get(e['to'])
        rs = rb.at(e['t'], max_age=400) if rb else None
        e['recvTerr'] = rs['terr'] if rs else None
        e['recvBal'] = rs['bal'] if rs else None
        e['limit'] = quota_limit(e['t']) if e['t'] < 4284 else None
        if e['t'] < 4284 and (e['t'] < 3213 or rs):
            e['points'] = quota_points(e['t'], e['amount'], M.land, rs['terr'] if rs else 1)
        else:
            e['points'] = None
        e['heur'] = heuristic_rejected(M, e['me'], e)
        e['toSquad'] = e['to'] in M.bots
        e['toTeam'] = pteam(M, e['to'])
    return rows


def pingpong_rows(rows, gap=150):
    """来回对捐：A→B（未被判拒）之后 gap 拍内 B→A（未被判拒）。每组取最近的一笔回捐。"""
    ok = sorted([e for e in rows if e['accepted'] is not False], key=lambda e: e['t'])
    out, used = [], set()
    for e in ok:
        for f in ok:
            if id(f) in used or f is e:
                continue
            if f['me'] == e['to'] and f['to'] == e['me'] and 0 < f['t'] - e['t'] <= gap:
                used.add(id(f))
                out.append(dict(t1=e['t'], a=e['me'], b=e['to'], fwd=e['amount'], fee1=e['fee'], t2=f['t'], back=f['amount'], fee2=f['fee'],
                                fees=e['fee'] + f['fee'], kind1=e['kind'], kind2=f['kind']))
                break
    return out


def sec_donations(M, verbose=False):
    rows = donation_rows(M)
    print(f"== {M.id} donations：日志 {len(rows)} 笔；录像覆盖到 t={M.replayLast}")
    if not rows:
        return
    acc = [e for e in rows if e['accepted'] is True]
    rej = [e for e in rows if e['accepted'] is False]
    unk = [e for e in rows if e['accepted'] is None]
    print(f"  录像真值：接受 {len(acc)}，被拒 {len(rej)}，录像未覆盖 {len(unk)}；延迟(执行拍-日志拍) 中位 {sorted([e['execT'] - e['t'] for e in acc])[len(acc) // 2] if acc else '-'}")
    if unk:
        hr = Counter(e['heur'] for e in unk)
        print(f"  未覆盖部分的启发式（40 拍内下一次余额读数 >= 0.97×原余额 → 被拒）：被拒 {hr.get(True, 0)}，接受 {hr.get(False, 0)}，判不了 {hr.get(None, 0)}")
    known = [e for e in rows if e['accepted'] is not None and e['heur'] is not None]
    if known:
        tp = sum(1 for e in known if e['heur'] and not e['accepted'])
        fp = sum(1 for e in known if e['heur'] and e['accepted'])
        fn = sum(1 for e in known if not e['heur'] and not e['accepted'])
        tn = sum(1 for e in known if not e['heur'] and e['accepted'])
        print(f"  启发式对照真值：判拒且真拒 {tp}，判拒但真接受 {fp}，判接受但真拒 {fn}，判接受且真接受 {tn}")
    for label, grp in (('接受', acc), ('被拒', rej)):
        if not grp:
            continue
        kinds = Counter(e['kind'] for e in grp)
        byphase = Counter('t<1071' if e['t'] < 1071 else 't<2142' if e['t'] < 2142 else 't<3213' if e['t'] < 3213 else 't<4284' if e['t'] < 4284 else 't>=4284' for e in grp)
        print(f"  {label}：类型 {dict(kinds)}；分期 {dict(sorted(byphase.items()))}")
    if acc:
        fee = sum(e['fee'] for e in acc)
        amt = sum(e['amount'] for e in acc)
        print(f"  已接受的 {len(acc)} 笔（按日志余额估算）：到账合计 {amt}，手续费合计 {fee}，损耗率 {100 * fee / max(1, fee + amt):.1f}%；pct 分布 {dict(sorted(Counter(e['pct'] for e in acc).items()))}")
        small = [e for e in acc if e['pct'] < 150]
        if small:
            print(f"  其中 pct<150 的 {len(small)} 笔：到账 {sum(e['amount'] for e in small)}，手续费 {sum(e['fee'] for e in small)}，损耗率 {100 * sum(e['fee'] for e in small) / max(1, sum(e['fee'] + e['amount'] for e in small)):.1f}%")
    if rej:
        over = [e for e in rej if e['points'] is not None and e['limit'] is not None and e['points'] > e['limit']]
        late = [e for e in rej if e['t'] >= 4284]
        print(f"  被拒 {len(rej)} 笔里：单笔所需额度点就超过当时全场上限的 {len(over)} 笔；t>=4284（已不查额度）仍被拒 {len(late)} 笔")
    # 收款人当时是否已经离开（变成 AI 托管的空壳）
    lv = leave_ticks(M)
    husk_acc = [e for e in acc if e['to'] in lv and e['execT'] >= lv[e['to']][0]]
    husk_rej = [e for e in rej if e['to'] in lv and e['t'] >= lv[e['to']][0]]
    if husk_acc or husk_rej:
        print(f"  收款人当时已离开（空壳）的捐款：执行了 {len(husk_acc)} 笔（到账≈{sum(e['amount'] for e in husk_acc)}，手续费≈{sum(e['fee'] for e in husk_acc)}），未执行 {len(husk_rej)} 笔")
        for e in husk_acc:
            print(f"    ✓ t{e['execT']} {pname(M, e['me'])}→{pname(M, e['to'])}(离开@{lv[e['to']][0]}) pct={e['pct']} 到账≈{e['amount']} 费≈{e['fee']}")
    pp = pingpong_rows(rows)
    if pp:
        print(f"  来回对捐（A→B 之后 150 拍内 B→A；没有录像的局按日志算）{len(pp)} 组：回流合计≈{sum(x['back'] for x in pp)}，两笔手续费合计≈{sum(x['fees'] for x in pp)}")
        for x in pp[:12]:
            print(f"    t{x['t1']} {pname(M, x['a'])}→{pname(M, x['b'])} 到账≈{x['fwd']}(费{x['fee1']}) ；t{x['t2']} 回捐≈{x['back']}(费{x['fee2']}) 间隔 {x['t2'] - x['t1']} 拍 [{x['kind2']}]")
    late_exec = [e for e in acc if e.get('late')]
    if late_exec:
        print(f"  晚到执行（日志拍后 90 拍以上才执行）{len(late_exec)} 笔：" + '; '.join(f"{pname(M, e['me'])}→{pname(M, e['to'])} 日志t{e['t']} 执行t{e['execT']}" for e in late_exec))
    pairs = Counter((e['me'], e['to']) for e in rows)
    print("  主要捐款对（笔数 接受/被拒/未知）：" + '; '.join(
        f"{pname(M, a)}→{pname(M, b)} {n}笔({sum(1 for e in rows if e['me'] == a and e['to'] == b and e['accepted'] is True)}/{sum(1 for e in rows if e['me'] == a and e['to'] == b and e['accepted'] is False)}/{sum(1 for e in rows if e['me'] == a and e['to'] == b and e['accepted'] is None)})"
        for (a, b), n in pairs.most_common(12)))
    to_out = [e for e in rows if not e['toSquad']]
    if to_out:
        print(f"  收款方不是我方 20 个号的捐款 {len(to_out)} 笔：" + ', '.join(sorted({e['toName'] for e in to_out})))
    if M.unloggedDonations:
        print(f"  录像里有、日志里没配上的我方捐款 {len(M.unloggedDonations)} 笔：" + '; '.join(f"{pname(M, p)}@{x['t']}p{x['pct']}→{pname(M, x['to'])}" for p, x in M.unloggedDonations[:10]))
    if verbose:
        for e in sorted(rows, key=lambda e: e['t']):
            st = '✓' if e['accepted'] else '✗' if e['accepted'] is False else ('?拒' if e['heur'] else '?收' if e['heur'] is False else '??')
            print(f"   t{e['t']:<5} {st} {pname(M, e['me'])}→{pname(M, e['to'])} {e['kind']} pct={e['pct']} bal={e['myBal']} dMe={e['dMe']} dAlly={e['dAlly']} box={e['boxedIn']} 到账≈{e['amount']} 费≈{e['fee']} 点={e['points']}/{e['limit']} 收款方地={e['recvTerr']}")


def drop_rows(M, thr=0.30):
    rows = []
    dt = donation_truth(M)
    for me in M.squad:
        b = M.bots[me]
        for a, s in zip(b.traj, b.traj[1:]):
            if a['bal'] <= 0 or s['bal'] > (1 - thr) * a['bal']:
                continue
            mine = cmds_of(M, me, a['t'], s['t'])
            onme = cmds_on(M, me, a['t'], s['t'])
            bal = a['bal']
            spent_atk = spent_boat = 0
            n_atk = n_boat = 0
            tg = Counter()
            for c in mine:
                if c['id'] == 1:
                    x = attack_amount(bal, c['dX']) + attack_fee(bal)
                    spent_atk += x
                    bal = max(0, bal - x)
                    n_atk += 1
                    tg[c['dZ']] += 1
                elif c['id'] == 3:
                    x = (bal * (c['dX'] + 1)) // 1024 + (32 * bal) // 1024
                    spent_boat += x
                    bal = max(0, bal - x)
                    n_boat += 1
            dons = [e for e in dt if e['me'] == me and a['t'] < e['t'] <= s['t']]
            don_acc = [e for e in dons if e['accepted'] is True or (e['accepted'] is None and heuristic_rejected(M, me, e) is False)]
            spent_don = sum(donation_fee(e['myBal']) + donation_amount(e['myBal'], e['pct']) for e in don_acc)
            inc = Counter(c['player'] for c in onme if c['id'] == 1)
            drop = a['bal'] - s['bal']
            covered = M.replayLast >= s['t']
            if covered:
                parts = []
                if spent_atk:
                    parts.append(('陆攻', spent_atk))
                if spent_boat:
                    parts.append(('发船', spent_boat))
                if spent_don:
                    parts.append(('捐款', spent_don))
                cause = '+'.join(k for k, v in sorted(parts, key=lambda kv: -kv[1]) if v >= 0.15 * drop) or ('被打' if inc or s['terr'] < a['terr'] else '不明')
                if (inc or s['terr'] < a['terr']) and '被打' not in cause and spent_atk + spent_boat + spent_don < 0.6 * drop:
                    cause += '+被打'
            else:
                dc = s['cmds'] - a['cmds']
                dbt = s['boats'] - a['boats']
                parts = []
                if spent_don >= 0.15 * drop:
                    parts.append('捐款')
                if dc > 0:
                    parts.append('出兵(日志cmds+%d)' % dc)
                if dbt > 0:
                    parts.append('船+%d' % dbt)
                if s['terr'] < a['terr']:
                    parts.append('被打(地%+d)' % (s['terr'] - a['terr']))
                cause = '+'.join(parts) or '不明'
            rows.append(dict(me=me, name=b.name, t0=a['t'], t1=s['t'], bal0=a['bal'], bal1=s['bal'], dropPct=100 * drop / a['bal'], terr0=a['terr'], terr1=s['terr'],
                             nAtk=n_atk, nBoat=n_boat, estAtk=spent_atk, estBoat=spent_boat, estDon=spent_don, targets=dict(tg), attackers=dict(inc), cause=cause,
                             covered=covered, dens0=a['dens'], nb0=a['nb']))
    return rows


def sec_drops(M):
    rows = drop_rows(M)
    print(f"== {M.id} drops：相邻快照兵力跌 >=30% 的区间 {len(rows)} 个；去向统计 {dict(Counter(r['cause'] for r in rows))}")
    for r in sorted(rows, key=lambda r: (r['me'], r['t0'])):
        tg = ' '.join(f"{pname(M, k)}{'/T' + str(pteam(M, k)) if k != 512 and pteam(M, k) is not None else ''}×{v}" for k, v in sorted(r['targets'].items(), key=lambda kv: -kv[1])[:5])
        ak = ' '.join(f"{pname(M, k)}/T{pteam(M, k)}×{v}" for k, v in sorted(r['attackers'].items(), key=lambda kv: -kv[1])[:4])
        print(f"  {r['name']:<14} t{r['t0']}→{r['t1']} 兵{r['bal0']}→{r['bal1']} (-{r['dropPct']:.0f}%) 地{r['terr0']}→{r['terr1']} 密{r['dens0']:.0f} | {r['cause']} | 估:攻{r['estAtk']} 船{r['estBoat']} 捐{r['estDon']} | 目标 {tg} | 被攻 {ak}")


def sec_spawn(M):
    print(f"== {M.id} spawn：mapW={M.mapW}")
    if not M.spawnXY:
        print('  没有录像：下面是每个号日志里最后一条 HL-SPAWN，未必是生效的那一条（有录像的 5 局 90 个号里只有 15 个号对得上，见 spawnlog），不能当出生点用')
        for me in M.squad:
            b = M.bots[me]
            if b.spawns:
                s = b.spawns[-1]
                print(f"  {b.name}({me}) slot={s['slot']} 日志最后一次选点=({s['x']},{s['y']}) chosen={s['chosen']}/{s['cand']} minSep={s['minSep']} 选点次数={len(b.spawns)}")
        return
    pts = M.spawnXY
    humans = [p for p in range(M.humans) if p in pts]
    for me in M.squad:
        if me not in pts:
            continue
        x, y = pts[me]
        ds = sorted((math.hypot(x - pts[p][0], y - pts[p][1]), p) for p in humans if p != me)
        near = ds[:4]
        mate = next(((d, p) for d, p in ds if p in M.bots), None)
        enemy = next(((d, p) for d, p in ds if pteam(M, p) != pteam(M, me)), None)
        tm = next(((d, p) for d, p in ds if pteam(M, p) == pteam(M, me)), None)
        b = M.bots[me]
        s270 = b.at(270, 0)   # 只取恰好在该拍的快照（缺快照就打印 -，不拿更早的顶替）
        s630 = b.at(630, 0)
        within = sum(1 for d, p in ds if d <= 150)
        print(f"  {b.name}({me}) 队{b.team} ({x},{y}) 选点{len(b.spawns)}次 | 150px 内真人 {within} 个 | 最近: " +
              ' '.join(f"{pname(M, p)}/T{pteam(M, p)}:{d:.0f}" for d, p in near) +
              f" | 最近我方号 {mate[0]:.0f} 最近敌队真人 {enemy[0]:.0f} 最近同队真人 {tm[0]:.0f}" +
              f" | 地@270={s270['terr'] if s270 else '-'} @630={s630['terr'] if s630 else '-'}")


def picks_rows(M):
    """选点指令（录像真值）：每号生效的选点次数、落在哪一步、最后两步的改点、坐标被几个号选过、最终落点两两相距 <80 的。"""
    d = M.replay
    if not d or not M.mapW:
        return None
    W = M.mapW
    c0 = [c for c in d['cmds'] if c['id'] == 0]
    steps = max((c['step'] for c in c0), default=0)
    by = defaultdict(list)
    for c in c0:
        by[c['player']].append((c['step'], c['dX'] % W, c['dX'] // W))
    per = {me: by.get(me, []) for me in M.squad}
    pts = defaultdict(set)
    for me, v in per.items():
        for _, x, y in v:
            pts[(x, y)].add(me)
    late = [(me, st, x, y) for me, v in per.items() for st, x, y in v if st >= steps - 1]
    near = []
    sq = sorted(M.squad)
    for i, a in enumerate(sq):
        for b in sq[i + 1:]:
            if per[a] and per[b]:
                dd = math.hypot(per[a][-1][1] - per[b][-1][1], per[a][-1][2] - per[b][-1][2])
                if dd < 80:
                    near.append(dict(a=a, b=b, dist=round(dd), stepA=per[a][-1][0], stepB=per[b][-1][0], xyA=per[a][-1][1:], xyB=per[b][-1][1:],
                                     teamA=M.bots[a].team, teamB=M.bots[b].team))
    return dict(steps=steps + 1, per=per, logPicks={me: len(M.bots[me].spawns) for me in M.squad}, distinct=len(pts),
                shared2=sum(1 for v in pts.values() if len(v) >= 2), shared3=sum(1 for v in pts.values() if len(v) >= 3),
                late=sorted(late, key=lambda r: (r[1], r[0])), near=near, allCmds=len(c0), pts=pts)


def sec_picks(M):
    R = picks_rows(M)
    if not R:
        print('（没有录像，选点指令看不到；日志侧见 spawn）')
        return
    n = [len(v) for v in R['per'].values()]
    print(f"== {M.id} 选点指令（录像真值）：选点阶段 {R['steps']} 步；我方 {len(n)} 个号生效选点 {sum(n)} 条（每号 {min(n)}~{max(n)}，中位 {sorted(n)[len(n) // 2]}），"
          f"日志 HL-SPAWN {sum(R['logPicks'].values())} 行；全场选点指令 {R['allCmds']} 条")
    print(f"   我方选过的不同坐标 {R['distinct']} 个，其中被 >=2 个号先后选过的 {R['shared2']} 个、>=3 个号的 {R['shared3']} 个")
    for me in sorted(M.squad):
        v = R['per'][me]
        print(f"   {M.bots[me].name:14s} 队{M.bots[me].team} 生效 {len(v):2d} 条（日志 {R['logPicks'][me]:2d} 行）：" + ' '.join(f"{st}:({x},{y})" for st, x, y in v))
    print(f"   最后两步（第 {R['steps'] - 2}、{R['steps'] - 1} 步）的改点 {len(R['late'])} 条：" + '；'.join(f"{M.bots[me].name} 步{st}→({x},{y})" for me, st, x, y in R['late']))
    for r in R['near']:
        print(f"   最终落点相距 <80：{M.bots[r['a']].name}(队{r['teamA']}) {tuple(r['xyA'])} 步{r['stepA']} ↔ {M.bots[r['b']].name}(队{r['teamB']}) {tuple(r['xyB'])} 步{r['stepB']}：{r['dist']} 格"
              + ('（同队）' if r['teamA'] == r['teamB'] else '（异队）'))
    # 最终落点那个坐标之前还被谁选过
    for me in sorted(M.squad):
        v = R['per'][me]
        if not v:
            continue
        xy = (v[-1][1], v[-1][2])
        others = [o for o in R['pts'][xy] if o != me]
        if others:
            print(f"   {M.bots[me].name} 的最终坐标 {xy} 还被这些号选过：" + '、'.join(
                f"{M.bots[o].name}(步{','.join(str(st) for st, x, y in R['per'][o] if (x, y) == xy)})" for o in others))


def spawnlog_rows(M):
    """有录像的局：每个号「日志里最后一条 HL-SPAWN 的坐标」是不是「录像里最后一条生效选点」。
    用来给没有录像的局校准：只看日志的最后一条选点有多大可能不是真正的出生点。"""
    R = picks_rows(M)
    if not R:
        return None
    out = []
    for me in sorted(M.squad):
        v = R['per'][me]
        lg = [(s['x'], s['y']) for s in M.bots[me].spawns]
        if not v or not lg:
            continue
        true = (v[-1][1], v[-1][2])
        # 真正的出生点是日志里倒数第几条（1 = 最后一条；None = 日志里没有这一条）
        back = next((i + 1 for i, xy in enumerate(reversed(lg)) if xy == true), None)
        out.append(dict(me=me, name=M.bots[me].name, logPicks=len(lg), effective=len(v), lastLog=list(lg[-1]), true=list(true),
                        lastIsTrue=(lg[-1] == true), trueBack=back, dist=round(math.hypot(lg[-1][0] - true[0], lg[-1][1] - true[1]), 1)))
    return out


def sec_spawnlog(M):
    rows = spawnlog_rows(M)
    if rows is None:
        print(f"== {M.id} spawnlog：没有录像，没法核对")
        return
    ok = sum(1 for r in rows if r['lastIsTrue'])
    print(f"== {M.id} spawnlog：日志最后一条 HL-SPAWN 的坐标 = 录像里最后一条生效选点 的号 {ok} / {len(rows)}")
    for r in rows:
        if not r['lastIsTrue']:
            print(f"   {r['name']:14s} 日志 {r['logPicks']} 行 / 生效 {r['effective']} 条：日志最后一条 {tuple(r['lastLog'])}，真正出生点 {tuple(r['true'])}（相距 {r['dist']} 格；"
                  + (f"是日志倒数第 {r['trueBack']} 条" if r['trueBack'] else '日志里没有这一条') + '）')


def boxed_rows(M, dens=95):
    rows = []
    for me in M.squad:
        b = M.bots[me]
        n = sum(1 for s in b.traj if s['nb'] == 0 and s['neut'] == 0 and s['t'] >= 630)
        hi = [s for s in b.traj if s['nb'] == 0 and s['neut'] == 0 and s['dens'] >= dens]
        early = [s for s in b.traj if s['neut'] == 0 and s['t'] < 630]
        if n or hi or early:
            rows.append(dict(me=me, name=b.name, boxedSnaps=n, hiDensSnaps=len(hi), first=(hi[0]['t'] if hi else None), last=(hi[-1]['t'] if hi else None),
                             maxDens=max([s['dens'] for s in hi], default=0), maxBal=max([s['bal'] for s in hi], default=0),
                             earlyNoNeutral=[s['t'] for s in early], total=len(b.traj)))
    return rows


def sec_boxed(M):
    rows = boxed_rows(M)
    print(f"== {M.id} boxed：nb=0 且 neut=0（四周只有队友/受保护的号/水）")
    for r in rows:
        print(f"  {r['name']:<14}({r['me']}) 被围快照 {r['boxedSnaps']}/{r['total']}（t>=630），其中密度>=95 的 {r['hiDensSnaps']} 个 [{r['first']}~{r['last']}] 最高密度 {r['maxDens']:.0f} 最高兵 {r['maxBal']}；开局(t<630)已无中立地的快照 {r['earlyNoNeutral']}")


def sec_attacks(M, t0=0, t1=10 ** 9):
    if not M.cmds:
        print(f"== {M.id} attacks：没有对局指令录像")
        return
    print(f"== {M.id} attacks（录像，t∈({t0},{t1}]）")
    out_h = defaultdict(Counter)
    inn = defaultdict(Counter)
    for c in M.cmds:
        if c['id'] != 1 or not (t0 < c['t'] <= t1):
            continue
        p, q = c['player'], c['dZ']
        if p in M.bots:
            kind = '无主地' if q == 512 else 'AI' if q >= M.humans else '我方' if q in M.bots else '真人'
            out_h[p][(kind, q if kind in ('我方', '真人') else None)] += 1
        if q in M.bots and p != q:
            inn[q][p] += 1
    for me in M.squad:
        if me not in out_h and me not in inn:
            continue
        o = out_h.get(me, Counter())
        tot = sum(o.values())
        neutral = o.get(('无主地', None), 0)
        ai = o.get(('AI', None), 0)
        ppl = [(k[1], v) for k, v in o.items() if k[0] in ('真人', '我方')]
        ppl.sort(key=lambda kv: -kv[1])
        ps = ' '.join(f"{pname(M, k)}/T{pteam(M, k)}×{v}" for k, v in ppl[:8])
        i = inn.get(me, Counter())
        is_ = ' '.join(f"{pname(M, k)}/T{pteam(M, k)}×{v}" for k, v in i.most_common(8))
        print(f"  {M.bots[me].name:<14}({me}) 队{M.bots[me].team} 出兵 {tot}: 无主地 {neutral} / AI {ai} / 人 {tot - neutral - ai} [{ps}] ｜ 被真人攻 {sum(i.values())}: [{is_}]")
    # 我方号之间的互打（拆队后的内耗）
    ff = [(c['t'], c['player'], c['dZ']) for c in M.cmds if c['id'] == 1 and c['player'] in M.bots and c['dZ'] in M.bots and t0 < c['t'] <= t1]
    if ff:
        pair = Counter((a, b) for _, a, b in ff)
        print(f"  我方号互打 {len(ff)} 条（首条 t={ff[0][0]}）：" + '; '.join(f"{pname(M, a)}/T{pteam(M, a)}→{pname(M, b)}/T{pteam(M, b)}×{n}" for (a, b), n in pair.most_common(12)))
    else:
        print("  我方号互打 0 条")


def lag_table(M):
    """用日志行号（落盘先后≈墙上时间先后）估算每个号的客户端落后量：
    某条 HL-TICK 落盘时，全编队已出现过的最大拍号 − 这条的拍号。领头的号≈服务器进度，所以这是落后量的下界。"""
    import re
    rows = []
    with open(os.path.join('/agent/repos/c136-data/bundles', M.id, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for raw in f:
            m = re.match(r'^(\d+)\t\[(.+?)\] \[(HL-[A-Z-]+)\] (.*)$', raw.rstrip('\n'))
            if not m or m.group(3) == 'HL-SPAWN':
                continue
            mt = re.search(r'\bt=(\d+)', m.group(4))
            if mt:
                rows.append((int(m.group(1)), m.group(2), m.group(3), int(mt.group(1))))
    runmax = 0
    per = defaultdict(list)
    for line, name, tag, t in rows:
        runmax = max(runmax, t)
        me = M.name2me.get(name)
        if me is not None and tag == 'HL-TICK':
            per[me].append((t, runmax - t))
    return per


def burst_table(M):
    """录像里同一拍同一个号有 >=4 条指令 = 客户端攒了一段进度后一次补发（或一拍内连发）。"""
    per = defaultdict(Counter)
    for c in M.cmds:
        if c['player'] in M.bots and c['id'] in (1, 2, 3):
            per[c['player']][c['t']] += 1
    out = {}
    for me, cnt in per.items():
        tot = sum(cnt.values())
        b = {t: n for t, n in cnt.items() if n >= 4}
        out[me] = dict(total=tot, burstTicks=len(b), inBurst=sum(b.values()), bursts=sorted(b.items()))
    return out


def sec_lag(M):
    per = lag_table(M)
    print(f"== {M.id} lag：按日志落盘顺序估算的客户端落后量（拍；18 拍≈1 秒）。落后量 = 当时全编队最大拍号 − 本号拍号")
    bins = defaultdict(list)
    for me, v in per.items():
        for t, lag in v:
            bins[(t // 450) * 450].append(lag)
    print("  分段(本地拍)  快照数 落后>=90 的占比  落后>=180 的占比  中位  最大")
    for b in sorted(bins):
        v = sorted(bins[b])
        print(f"  {b:>5}~{b + 449:<5} {len(v):>5} {100 * sum(1 for x in v if x >= 90) / len(v):>10.0f}% {100 * sum(1 for x in v if x >= 180) / len(v):>12.0f}% {v[len(v) // 2]:>6} {v[-1]:>6}")
    bt = burst_table(M)
    print("  各号：最大落后 / 落后>=180 的快照区间 / 录像里攒发(同拍>=4 条)占全部指令")
    for me in M.squad:
        v = per.get(me)
        if not v:
            continue
        big = [t for t, lag in v if lag >= 180]
        b = bt.get(me)
        bs = f"{b['inBurst']}/{b['total']} 条在 {b['burstTicks']} 次攒发里" if b else '-'
        print(f"   {M.bots[me].name:<14}({me}) 最大落后 {max(l for _, l in v):>4} | >=180: {str(big[0]) + '~' + str(big[-1]) + ' 共' + str(len(big)) + '个' if big else '无':<18} | {bs}")
    dts = [e for e in donation_truth(M) if e['accepted']]
    if dts:
        lat = sorted(e['execT'] - e['t'] for e in dts)
        print(f"  已接受捐款的「日志拍→执行拍」延迟：中位 {lat[len(lat) // 2]}，90 分位 {lat[int(0.9 * len(lat))]}，最大 {lat[-1]}（共 {len(lat)} 笔）")
    ol = opening_latency(M)
    if ol:
        print("  开局周期指令「日志拍→执行拍」延迟序列（本地拍:延迟；x = 录像里没有同千分比的指令）：")
        for me in M.squad:
            if me in ol:
                ser = ol[me]
                got = [d for _, d in ser if d is not None]
                print(f"   {M.bots[me].name:<14}({me}) " + ' '.join(f"{t}:{'x' if d is None else d}" for t, d in ser) + (f" | 最大 {max(got)}" if got else '') + (f" | 没进录像 {len(ser) - len(got)} 条" if len(got) < len(ser) else ''))


def leave_ticks(M):
    """录像里每个玩家（不只我方）的离开拍（指令 8=认输离开，9=断线）。"""
    out = {}
    for c in M.cmds:
        if c['id'] in (8, 9) and c['player'] not in out:
            out[c['player']] = (c['t'], c['id'])
    return out


def opening_latency(M):
    """每条 HL-OPENING 日志（本地拍）按「同号、同千分比、还没配过、不早于下令拍」配到录像里的无主地出兵（执行拍）→ 延迟序列。
    千分比按引擎的整数规则由日志的 spend/bal 还原；配不上记 None（这条指令没进录像）。与 logdigest.py oplag 同一规则。"""
    out = {}
    for me in M.squad:
        b = M.bots[me]
        neu = [(c['t'], c['dX']) for c in M.cmds if c['player'] == me and c['id'] == 1 and c['dZ'] == 512]
        used, ser = set(), []
        for o in b.opening:
            pct = max(0, min(1023, math.ceil(o['spend'] * 1024 / max(1, o['bal'])) - 1))
            hit = None
            for i, (t, x) in enumerate(neu):
                if i in used or t < o['t']:
                    continue
                if x == pct:
                    hit = i
                    break
            if hit is None:
                ser.append((o['t'], None))
            else:
                used.add(hit)
                ser.append((o['t'], neu[hit][0] - o['t']))
        if ser:
            out[me] = ser
    return out


def sec_teamwar(M, win=900):
    """全场真人的陆攻指令按「攻方队→守方队」分窗统计（只有录像覆盖的拍）。Σpct = 每条指令的 (pct+1)/1024 之和，粗略代表投入的兵力份额。"""
    if not M.cmds:
        print(f"== {M.id} teamwar：没有录像")
        return
    lv = leave_ticks(M)
    print(f"== {M.id} teamwar：录像到 t={M.replayLast}；窗口 {win} 拍；格式 攻方队→守方队:指令数(Σpct%)。T0=内置AI/无队，N=无主地")
    wins = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    per_player = defaultdict(lambda: dict(n=0, s=0.0, tg=Counter(), first=None, last=None))
    for c in M.cmds:
        if c['id'] != 1 or c['player'] >= M.humans:
            continue
        a = pteam(M, c['player'])
        d = 'N' if c['dZ'] == 512 else pteam(M, c['dZ'])
        w = (c['t'] // win) * win
        cell = wins[w][(a, d)]
        cell[0] += 1
        cell[1] += (c['dX'] + 1) / 1024
        if d not in ('N', 0):
            pp = per_player[c['player']]
            pp['n'] += 1
            pp['s'] += (c['dX'] + 1) / 1024
            pp['tg'][d] += 1
            pp['first'] = c['t'] if pp['first'] is None else pp['first']
            pp['last'] = c['t']
    for w in sorted(wins):
        cells = wins[w]
        hum = sorted(((k, v) for k, v in cells.items() if k[1] not in ('N', 0)), key=lambda kv: -kv[1][1])
        s = ' '.join(f"T{a}→T{d}:{n}({100 * sp:.0f})" for (a, d), (n, sp) in hum[:8])
        neu = sum(v[0] for k, v in cells.items() if k[1] in ('N', 0))
        print(f"  t{w:>5}~{w + win - 1:<5} 打无主地/AI {neu:>4} 条 | 队间: {s}")
    print("  打真人最多的 14 个玩家（指令数 / Σpct% / 平均单条% / 目标队 / 起止拍 / 是否我方 / 离开拍）：")
    for p, pp in sorted(per_player.items(), key=lambda kv: -kv[1]['s'])[:14]:
        tg = ' '.join(f"T{k}×{v}" for k, v in pp['tg'].most_common(3))
        print(f"   {pname(M, p):<26} T{pteam(M, p)} {pp['n']:>4} 条 Σ{100 * pp['s']:>6.0f}% 平均 {100 * pp['s'] / pp['n']:>4.1f}% → {tg:<18} t{pp['first']}~{pp['last']}{' 离开@' + str(lv[p][0]) if p in lv else ''}")
    # 各队离开人数
    by_team = defaultdict(list)
    for p, (t, cid) in lv.items():
        if p < M.humans:
            by_team[pteam(M, p)].append((t, p, cid))
    print("  各队中途离开的真人（认输 8 / 断线 9）：" + '; '.join(
        f"T{k}: {len(v)} 人（我方 {sum(1 for _, p, _ in v if p in M.bots)}，断线 {sum(1 for _, _, c in v if c == 9)}）" for k, v in sorted(by_team.items())))


def snap_rows(M, t):
    """t 拍的横截面：每个在场号 t 及之前最近的一条快照（200 拍内）。"""
    pres = presence(M)
    rows = []
    for me in M.squad:
        b = M.bots[me]
        if not active_at(M, pres, me, t):
            continue
        s = b.at(t, 200)
        if s:
            rows.append(dict(me=me, name=b.name, team=b.team, t=s['t'], terr=s['terr'], bal=s['bal'], dens=s['dens'], nb=s['nb'], neut=s['neut'], cmds=s['cmds'], boats=s['boats']))
    return rows


def sec_snap(M, ticks):
    for t in ticks:
        rows = snap_rows(M, t)
        if not rows:
            print(f"== {M.id} snap t={t}：没有在场号的快照")
            continue
        terr = sorted(r['terr'] for r in rows)
        dens = sorted(r['dens'] for r in rows)
        med = lambda v: v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
        print(f"== {M.id} snap t={t}：在场 {len(rows)} 个号；领土 合计 {sum(terr)}、中位 {med(terr):.0f}、最小 {terr[0]}、最大 {terr[-1]}；密度 中位 {med(dens):.1f}、最小 {dens[0]:.1f}、最大 {dens[-1]:.1f}；"
              f"nb=0 的 {sum(1 for r in rows if r['nb'] == 0)} 个（其中 neut=0 的 {sum(1 for r in rows if r['nb'] == 0 and r['neut'] == 0)} 个）；密度>=100 的 {sum(1 for r in rows if r['dens'] >= 100)} 个")
        for r in sorted(rows, key=lambda r: (str(r['team']), -r['terr'])):
            print(f"   {r['name']:14s} 队{r['team']} 地 {r['terr']:>6} 兵 {r['bal']:>8} 密度 {r['dens']:>6.1f} nb={r['nb']:<2} neut={r['neut']:<3} cmds={r['cmds']:<4} boats={r['boats']}")
        # 分队小计；「吃光要花」= 把每个号打到清地的兵（c110 L2756-2757 的口径：1.78×兵 + 1.5×地，不计期间利息和对方的在途兵）
        for tm in sorted({str(r['team']) for r in rows}):
            rs = [r for r in rows if str(r['team']) == tm]
            L, B = sum(r['terr'] for r in rs), sum(r['bal'] for r in rs)
            print(f"   队{tm} 小计：{len(rs)} 个号 地 {L}（{100 * L / M.land:.2f}%） 兵 {B} 密度 {B / max(1, L):.1f}；有邻居（nb>=1）的 {sum(1 for r in rs if r['nb'] >= 1)} 个；吃光要花 ≈ {int(1.78 * B + 1.5 * L)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mid, sec = sys.argv[1], sys.argv[2]
    M = load_match(mid)
    a = sys.argv[3:]
    if sec == 'roster':
        sec_roster(M)
    elif sec == 'snap':
        sec_snap(M, [int(x) for x in a] or [630])
    elif sec == 'teams':
        sec_teams(M)
    elif sec == 'timeline':
        sec_timeline(M, [int(x) for x in a] or None)
    elif sec == 'outsiders':
        sec_outsiders(M)
    elif sec == 'bot':
        sec_bot(M, int(a[0]), int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 10 ** 9)
    elif sec == 'deaths':
        sec_deaths(M)
    elif sec == 'donations':
        sec_donations(M, verbose='-v' in a)
    elif sec == 'drops':
        sec_drops(M)
    elif sec == 'spawn':
        sec_spawn(M)
    elif sec == 'picks':
        sec_picks(M)
    elif sec == 'spawnlog':
        sec_spawnlog(M)
    elif sec == 'boxed':
        sec_boxed(M)
    elif sec == 'attacks':
        sec_attacks(M, int(a[0]) if a else 0, int(a[1]) if len(a) > 1 else 10 ** 9)
    elif sec == 'lag':
        sec_lag(M)
    elif sec == 'teamwar':
        sec_teamwar(M, int(a[0]) if a else 900)
    elif sec == 'json':
        pres = presence(M)
        out = dict(matchId=mid, replaySrc=M.replaySrc, replayLast=M.replayLast, endTick=M.endTick, land=M.land, humans=M.humans,
                   presence={str(k): v for k, v in pres.items()},
                   roster={str(me): dict(names=M.bots[me].names, team=M.bots[me].team, spawn=M.spawnXY.get(me), snaps=len(M.bots[me].traj)) for me in M.squad},
                   teams=team_table(M), teamSnaps=M.teamSnaps,
                   timeline=[{k: v for k, v in r.items() if k != 'teamSnap'} | {'teamSnapT': r['teamSnap']['t'] if r['teamSnap'] else None} for r in timeline_rows(M)],
                   donations=[{k: v for k, v in e.items() if k not in ('name',)} for e in donation_rows(M)],
                   drops=drop_rows(M), boxed=boxed_rows(M))
        os.makedirs(os.path.join(OUT, mid), exist_ok=True)
        with open(os.path.join(OUT, mid, 'digest.json'), 'w') as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=str)
        print(f"写入 out/{mid}/digest.json")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
