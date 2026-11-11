#!/usr/bin/env python3
"""resim_report.py — 把 resim.mjs 导出的全局事实表整理成复盘要用的数字。
用法: python3 resim_report.py <matchId> [--section meta,timeline,bots,pairs,transfers,events,top,front] [--ticks 180,600,...]
                               [--t0 N --t1 N] [--bot name] [--prefix B039:]
各节:
  meta      重演与日志的核对结果、队伍人数
  timeline  指定拍: 本队(日志里的号)存活/领土/占比/兵力/密度 + 各队占全图陆地比例
  bots      每个号: 出生点、峰值领土、首次碰到敌人/AI 的拍、被围死(无敌无中立)的拍、顶到 150x 上限的拍、离场/阵亡与夺地最多的对手
  pairs     [t0,t1] 内本队各号被谁拿走多少格、从谁手里拿到多少格
  transfers 本队相关转账: 指令捐款(名义/到账/手续费/被上限截掉)、离场号自动捐款、船靠岸捐款
  events    全部人类号阵亡/离场按队统计 + 本队逐条
  top       指定拍领土前 10 的人类号
  percap    指定拍的人均领土：本队 / 同队其他人类号 / 其他各队人类号（--ticks 180,630,...）
  front     --bot 某号每 30 拍的进攻/被攻/邻居明细 ([t0,t1])
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def load(mid, name):
    p = os.path.join(HERE, '..', 'out', mid, name)
    if not os.path.exists(p):
        return []
    with open(p, newline='') as f:
        return list(csv.DictReader(f))


def main():
    a = sys.argv[1:]
    mid = a[0]
    def opt(k, d=None):
        return a[a.index('--' + k) + 1] if '--' + k in a else d
    sections = opt('section', 'meta,timeline,bots,events').split(',')
    meta = json.load(open(os.path.join(HERE, '..', 'out', mid, 'resim_meta.json')))
    names = meta['names']; teams = meta['teams'] or {}; H = meta['humans']; land = meta['land']
    prefix = opt('prefix', '')
    squad = {b: p for b, p in meta['squad'].items() if (b.startswith(prefix) if prefix else ':' not in b)}
    sq_ids = set(squad.values()); lab = {p: b for b, p in squad.items()}
    def nm(p):
        p = int(p)
        if p >= 512: return 'NEUTRAL'
        if p in lab: return lab[p]
        if p < H: return f"{names[p]}#{p}/T{teams.get(str(p), '?')}"
        return f"AI#{p}"
    t0 = int(opt('t0', 0)); t1 = int(opt('t1', 10**9))
    my_team = None
    for p in sq_ids:
        my_team = teams.get(str(p)); break

    if 'meta' in sections:
        print(f"== {mid} 重演核对: ok={meta['checkOk']} bad={meta['checkBad']} firstBadTick={meta['firstBadTick']} firstBad={meta['firstBad']}")
        print(f"   map={meta['map']} {meta['W']}x{meta['Hh']} land={land} humans={H} nTeams={meta['nTeams']} teamCounts={meta['teamCounts']} lastTick={meta['lastTick']} myTeam=T{my_team}")
        print(f"   cmds applied={meta['applied']} rejected={meta['rejected']}")

    players = load(mid, 'resim_players.csv') if any(s in sections for s in ('timeline', 'top', 'events', 'percap')) else []
    teams_rows = load(mid, 'resim_teams.csv') if 'timeline' in sections else []

    if 'timeline' in sections:
        ticks_avail = sorted({int(r['t']) for r in teams_rows})
        want = opt('ticks')
        if want:
            want = [int(x) for x in want.split(',')]
        else:
            last = ticks_avail[-1]
            want = [180, 630, 1530, 2250, 3060] + list(range(3960, last, 900)) + [last]
        want = sorted({min(ticks_avail, key=lambda x: abs(x - w)) for w in want if w <= ticks_avail[-1] + 300})
        byt = defaultdict(dict)
        for r in teams_rows:
            byt[int(r['t'])][int(r['team'])] = r
        pbt = defaultdict(list)
        for r in players:
            if int(r['p']) in sq_ids:
                pbt[int(r['t'])].append(r)
        print("== timeline (t | 本队存活(未离场)/离场壳/已死 | 本队领土 占比% | 本队兵力 密度 | 各队占比% T0=AI ...)")
        for t in want:
            rows = pbt.get(t, [])
            alive = [r for r in rows if r['alive'] == '1' and r['state'] != '2']
            husk = [r for r in rows if r['alive'] == '1' and r['state'] == '2']
            dead = [r for r in rows if r['alive'] != '1']
            terr = sum(int(r['terr']) for r in alive); bal = sum(int(r['bal']) for r in alive)
            hterr = sum(int(r['terr']) for r in husk)
            tm = byt[t]
            shares = ' '.join(f"T{k}={tm[k]['sharePct']}({tm[k]['alive']})" for k in sorted(tm))
            print(f"  t={t:5d} alive={len(alive)} husk={len(husk)} dead={len(dead)} | terr={terr} share={100*terr/land:.2f}% (+壳{hterr}) | bal={bal} dens={bal/terr if terr else 0:.1f} | {shares}")

    if 'percap' in sections:
        # 人均领土：本队（日志里的号，含离场壳）对 同队其他人类号 对 其他队人类号；只算仍存活的席位
        pl = players or load(mid, 'resim_players.csv')
        H = meta.get('humans') or meta.get('H') or 0
        want = [int(x) for x in (opt('ticks') or '180,630,900,1530,2250,3060').split(',')]
        ticks_avail = sorted({int(r['t']) for r in pl})
        my_team = None
        print("== percap (t | 本队 n 人均 | 同队其他人 n 人均 | 其他各队 n 人均)")
        for w in want:
            t = min(ticks_avail, key=lambda x: abs(x - w))
            rows = [r for r in pl if int(r['t']) == t and r['alive'] == '1' and int(r['team']) > 0 and (not H or int(r['p']) < H)]
            if my_team is None:
                my_team = next((int(r['team']) for r in rows if int(r['p']) in sq_ids), None)
            grp = defaultdict(list)
            for r in rows:
                k = 'squad' if int(r['p']) in sq_ids else ('mates' if int(r['team']) == my_team else f"T{r['team']}")
                grp[k].append(int(r['terr']))
            def f(k):
                v = grp.get(k, [])
                return f"{k} n={len(v)} 人均={sum(v) / len(v):.0f}" if v else f"{k} n=0"
            others = ' | '.join(f(k) for k in sorted(grp) if k.startswith('T'))
            print(f"  t={t:5d} | {f('squad')} | {f('mates')} | {others}")

    if 'bots' in sections:
        sq = load(mid, 'resim_squad.csv'); ev = load(mid, 'resim_events.csv')
        evp = defaultdict(list)
        for e in ev:
            evp[int(e['p'])].append(e)
        print("== bots (号 席位 出生点 | 峰值领土@拍 | 首次接敌(人类)@ 首次接AI@ | 首次无敌无AI无中立@ | 首次 room150<=0@ | 结局)")
        by = defaultdict(list)
        for r in sq:
            if int(r['p']) in sq_ids:
                by[int(r['p'])].append(r)
        for p in sorted(by, key=lambda x: lab[x]):
            rows = by[p]
            peak = max(rows, key=lambda r: int(r['terr']))
            first_en = next((r['t'] for r in rows if r['enemyNb']), '-')
            first_ai = next((r['t'] for r in rows if r['aiNb'] and not r['aiNb'].startswith('0:')), '-')
            boxed = next((r['t'] for r in rows if r['alive'] == '1' and int(r['t']) > 200 and not r['enemyNb'] and (not r['aiNb'] or r['aiNb'].startswith('0:')) and int(r['neutralC']) == 0), '-')
            capped = next((r['t'] for r in rows if r['alive'] == '1' and int(r['t']) > 200 and int(r['room150']) <= 0), '-')
            sp = meta['spawn'].get(str(p))
            fate = '; '.join(f"{e['ev']}@{e['t']} terr={e['terr']} bal={e['bal']} " + ' '.join(
                (k.split('=')[0] + '=' + '|'.join(nm(x.split(':')[0]) + ':' + ':'.join(x.split(':')[1:]) for x in k.split('=')[1].split('|') if x)) for k in e['detail'].split(';') if '=' in k) for e in evp.get(p, [])) or 'alive-to-end'
            print(f"  {lab[p]:10s} #{p:3d} spawn={sp} | peak={peak['terr']}@{peak['t']} | en@{first_en} ai@{first_ai} | boxed@{boxed} | cap@{capped} | {fate}")

    if 'pairs' in sections:
        pr = load(mid, 'resim_pairs.csv')
        lost = defaultdict(int); won = defaultdict(int)
        for r in pr:
            if int(r['t1']) <= t0 or int(r['t0']) >= t1: continue
            v, at, px = int(r['victim']), int(r['attacker']), int(r['px'])
            if v in sq_ids: lost[(v, at)] += px
            if at in sq_ids: won[(at, v)] += px
        print(f"== pairs [{t0},{t1}] 本队丢地 (号 <- 对手: 格)")
        for (v, at), px in sorted(lost.items(), key=lambda x: -x[1])[:40]:
            print(f"  {lab[v]:10s} <- {nm(at):40s} {px}")
        print(f"== pairs [{t0},{t1}] 本队夺地 (号 -> 对手: 格)")
        for (at, v), px in sorted(won.items(), key=lambda x: -x[1])[:40]:
            print(f"  {lab[at]:10s} -> {nm(v):40s} {px}")

    if 'transfers' in sections:
        tr = load(mid, 'resim_transfers.csv')
        print(f"== transfers [{t0},{t1}] 涉及本队")
        agg = defaultdict(lambda: [0, 0, 0, 0, 0])
        for r in tr:
            t = int(r['t'])
            if t < t0 or t > t1: continue
            f, to = int(r['from']), int(r['to'])
            if f not in sq_ids and to not in sq_ids: continue
            paid, rec = int(r['paid']), int(r['received'])
            if r['kind'] == 'cmd':
                B = int(r['fromBal']); nominal = min(B * (int(r['pct']) + 1) // 1024, B - 64 * B // 1024); fee = 64 * B // 1024 if r['ok'] == '1' else 0
                room = 150 * int(r['toTerr']) - int(r['toBal'])
                clip = max(0, nominal - rec) if r['ok'] == '1' else 0
                k = ('cmd', 'sq->sq' if (f in sq_ids and to in sq_ids) else ('sq->other' if f in sq_ids else 'other->sq'))
                x = agg[k]; x[0] += 1; x[1] += nominal if r['ok'] == '1' else 0; x[2] += rec; x[3] += fee; x[4] += clip
                if '--list' in a:
                    print(f"  t={t} cmd {nm(f)} -> {nm(to)} pct={r['pct']} donorBal={B} nominal={nominal} received={rec} fee={fee} room={room} clipped={clip} ok={r['ok']} dDonor={B/max(1,1):.0f} dAllyBefore={int(r['toBal'])/max(1,int(r['toTerr'])):.1f}")
            else:
                k = (r['kind'], 'sq->sq' if (f in sq_ids and to in sq_ids) else ('sq->other' if f in sq_ids else 'other->sq'))
                x = agg[k]; x[0] += 1; x[1] += paid; x[2] += rec; x[3] += paid - rec if r['kind'] == 'auto' else 0; x[4] += (paid - rec) if r['kind'] == 'boat' else 0
                if '--list' in a:
                    print(f"  t={t} {r['kind']} {nm(f)} -> {nm(to)} paid={paid} received={rec}")
        for k, x in sorted(agg.items()):
            print(f"  {k[0]:5s} {k[1]:10s} n={x[0]} nominal/paid={x[1]} received={x[2]} fee={x[3]} clippedOrLost={x[4]}")

    if 'events' in sections:
        ev = load(mid, 'resim_events.csv')
        cnt = defaultdict(lambda: defaultdict(int))
        for e in ev:
            cnt[e['team']][e['ev']] += 1
        print("== events 按队: " + ' | '.join(f"T{k}: " + ' '.join(f"{x}={n}" for x, n in sorted(v.items())) for k, v in sorted(cnt.items())))
        for e in ev:
            if int(e['p']) in sq_ids:
                det = ' '.join((k.split('=')[0] + '=' + '|'.join(nm(x.split(':')[0]) + ':' + ':'.join(x.split(':')[1:]) for x in k.split('=')[1].split('|') if x)) for k in e['detail'].split(';') if '=' in k)
                print(f"  t={e['t']} {e['ev']} {lab[int(e['p'])]} terr={e['terr']} bal={e['bal']} {det}")

    if 'top' in sections:
        want = [int(x) for x in opt('ticks', '1530,3060').split(',')]
        ticks_avail = sorted({int(r['t']) for r in players})
        for w in want:
            t = min(ticks_avail, key=lambda x: abs(x - w))
            rows = sorted([r for r in players if int(r['t']) == t and r['alive'] == '1'], key=lambda r: -int(r['terr']))
            print(f"== top@{t} (alive humans={len(rows)})")
            for i, r in enumerate(rows[:10]):
                print(f"  {i+1:2d}. {nm(r['p']):36s} terr={r['terr']} ({100*int(r['terr'])/land:.1f}%) bal={r['bal']} dens={int(r['bal'])/max(1,int(r['terr'])):.0f} state={r['state']}")
            for r in rows:
                if int(r['p']) in sq_ids:
                    print(f"   · rank {rows.index(r)+1}: {nm(r['p'])} terr={r['terr']} bal={r['bal']} state={r['state']}")

    if 'front' in sections:
        sq = load(mid, 'resim_squad.csv'); bot = opt('bot')
        step = int(opt('step', 30))
        def exp(s, n=3):
            out = []
            for x in (s.split('|') if s else []):
                f = x.split(':')
                out.append(nm(f[0]) + ':' + ':'.join(f[1:]))
            return ' '.join(out[:n])
        print(f"== front {bot} [{t0},{t1}] (t terr bal dens room150 | atkOut 目标:兵 | atkIn 对手:兵 | enemyNb 号:接触:领土:兵力 | ally/husk/ai | neutral water boats)")
        for r in sq:
            if r['bot'] != bot: continue
            t = int(r['t'])
            if t < t0 or t > t1 or t % step: continue
            print(f"  t={t} terr={r['terr']} bal={r['bal']} dens={r['dens']} room={r['room150']} | out[{exp(r['atkOut'])}] | in[{exp(r['atkIn'])}] | en[{exp(r['enemyNb'])}] | al={len(r['allyNb'].split('|')) if r['allyNb'] else 0} hu={len(r['huskNb'].split('|')) if r['huskNb'] else 0} ai={r['aiNb']} | n={r['neutralC']} w={r['waterC']} b={r['boats']}")


if __name__ == '__main__':
    main()
