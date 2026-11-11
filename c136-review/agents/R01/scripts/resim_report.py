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
  donflow   本队内部落地的捐款：4284 拍前后、按 捐出方→受赠方 的 名义/到账/手续费/被上限截掉；到账后 --window（默认 300）拍内又被转捐的笔数
  events    全部人类号阵亡/离场按队统计 + 本队逐条
  top       指定拍领土前 10 的人类号
  percap    指定拍的人均领土：本队 / 同队其他人类号 / 其他各队人类号（--ticks 180,630,...）
  front     --bot 某号每 30 拍的进攻/被攻/邻居明细 ([t0,t1])
  spawnseq  出生排位的变动：协调器发过几版位置、相邻两版位移、录像里最后落地的是倒数第几版、实际出生点的重叠与空位
  capidle   满仓闲置：本队各号在 resim_squad.csv 每个采样点（默认 30 拍）的密度（余额/领土）落在 >=100、>=125、>=149.5 的点数，
            以及按引擎利率公式算出的“因超过 100 倍领土而少拿的利息”（interestRate：n1 -= 2*n1*(bal-cap)/cap；150 倍时为 0）。
            同时给出每个采样点 nb（敌邻）=0 的号数。[t0,t1] 可限定区间；--win 分窗宽度（默认 900 拍）
  spawn     本队各号的出生点（录像里最后一条出生指令）、离最近队友的距离、--radius（默认 250）像素内的其他人类号（队伍、距离）
  drops     本队各号相邻两个 90 拍快照之间余额下降 >=30% 的点（数字来自整局重演，不依赖日志）：
            区间内落地的本号指令（进攻/船/捐款条数与 pct 合计）、同拍落地 >=3 条的批次、被谁拿走多少格，并归类
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

    if 'drops' in sections:
        drops_section(mid, meta, squad)
    if 'spawn' in sections:
        sp = {int(k): v for k, v in meta['spawn'].items()}
        R = float(opt('radius', 250))
        dist = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        print(f'== spawn（号 席位 出生点 | 最近队友 | {R:.0f} 像素内的其他人类号：名字/队/距离）')
        for b, p in sorted(squad.items(), key=lambda kv: kv[1]):
            if p not in sp:
                print(f'  {b:<8} #{p} 没有出生指令'); continue
            ally = sorted((dist(sp[p], sp[q]), lab[q]) for q in sq_ids if q != p and q in sp)
            oth = sorted((dist(sp[p], sp[q]), q) for q in sp if q not in sq_ids and q < H)
            near = ' '.join(f"{names[q] if isinstance(names, list) else names.get(str(q))}/T{teams.get(str(q), '?')}/{d:.0f}" for d, q in oth if d <= R)
            print(f"  {b:<8} #{p} ({sp[p][0]},{sp[p][1]}) | 最近队友 {ally[0][1] + ' ' + format(ally[0][0], '.0f') if ally else '-'} | {near or '无'}")
        # 协调器给“不在这个实例里”的号排的位置（日志最后一条 [HL-SPAWN-BACKEND]）附近，这个实例里实际站着谁
        import re
        plan = {}
        lp = f'/agent/repos/c136-data/bundles/{mid}/in_game.log'
        if os.path.exists(lp):
            for line in open(lp, encoding='utf8'):
                m = re.search(r'\[([a-z0-9_]+)\] \[HL-SPAWN-BACKEND\] me=\d+ slot=(\d+) role=(\w+) -> \((\d+),(\d+)\)', line)
                if m:
                    plan[m.group(1)] = (int(m.group(4)), int(m.group(5)), m.group(3))
        absent = {b: v for b, v in plan.items() if b not in squad}
        if absent:
            print('   协调器排了位、但不在这个实例里的号（计划位 | 这个实例里 100 像素内的人类号）：')
            for b, (x, y, role) in sorted(absent.items()):
                oth = sorted((dist((x, y), sp[q]), q) for q in sp if q < H)
                near = ' '.join(f"{lab.get(q) or (names[q] if isinstance(names, list) else names.get(str(q)))}/T{teams.get(str(q), '?')}/{d:.0f}" for d, q in oth if d <= 100)
                print(f"   {b:<8} {role:<18} ({x},{y}) | {near or '无'}")
    if 'spawnseq' in sections:
        spawnseq_section(mid, meta, squad)
    if 'capidle' in sections:
        capidle_section(mid, meta, squad, t0, t1, int(opt('win', 900)))
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

    if 'donflow' in sections:
        # 本队内部的捐款指令（录像里落地的）：按 4284 拍前后、按 捐出方→受赠方 汇总；并列出“往返”——A 给 B 之后 --window 拍内 B 又给 A 或给了第三个本队号
        tr = [r for r in load(mid, 'resim_transfers.csv') if r['kind'] == 'cmd' and r['ok'] == '1' and int(r['from']) in sq_ids and int(r['to']) in sq_ids and t0 <= int(r['t']) <= t1]
        def parts(r):
            B = int(r['fromBal']); fee = 64 * B // 1024
            nominal = min(B * (int(r['pct']) + 1) // 1024, B - fee)
            return B, nominal, int(r['received']), fee, max(0, nominal - int(r['received']))
        def line(rows):
            n = len(rows); nom = sum(parts(r)[1] for r in rows); rec = sum(parts(r)[2] for r in rows); fee = sum(parts(r)[3] for r in rows); clip = sum(parts(r)[4] for r in rows)
            nclip = sum(1 for r in rows if parts(r)[4] > 0)
            return f"{n} 笔 名义 {nom} 到账 {rec} 手续费 {fee}（手续费/到账 {100 * fee / max(1, rec):.1f}%） 被受赠者上限截掉 {clip}（{nclip} 笔）"
        print(f"== donflow 本队内部落地的捐款指令 [{t0},{t1}]")
        print('  全部    ' + line(tr))
        print('  t<4284  ' + line([r for r in tr if int(r['t']) < 4284]))
        print('  t>=4284 ' + line([r for r in tr if int(r['t']) >= 4284]))
        pair = defaultdict(list)
        for r in tr: pair[(int(r['from']), int(r['to']))].append(r)
        for (f, to), rows in sorted(pair.items(), key=lambda kv: -sum(parts(r)[2] for r in kv[1])):
            print(f"  {nm(f):>8} -> {nm(to):<8} {line(rows)} 拍 {rows[0]['t']}–{rows[-1]['t']}")
        recv = defaultdict(int); give = defaultdict(int); feeBy = defaultdict(int)
        for r in tr:
            recv[int(r['to'])] += parts(r)[2]; give[int(r['from'])] += parts(r)[2]; feeBy[int(r['from'])] += parts(r)[3]
        print('  各号 收到/捐出/付手续费: ' + ' | '.join(f"{b} {recv[p]}/{give[p]}/{feeBy[p]}" for b, p in sorted(squad.items(), key=lambda kv: -recv[kv[1]])))
        win = int(opt('window', 300))
        rt_n = 0; rt_amt = 0
        for i, r in enumerate(tr):
            to = int(r['to']); t = int(r['t'])
            nxt = [x for x in tr[i + 1:] if int(x['from']) == to and int(x['t']) - t <= win]
            if nxt:
                rt_n += 1; rt_amt += min(parts(r)[2], sum(parts(x)[2] for x in nxt))
        print(f"  到账后 {win} 拍内受赠者自己又捐出去的：{rt_n}/{len(tr)} 笔，涉及兵力（取 到账额 与 再捐出额 的较小者）{rt_amt}")
        # 每笔捐款落地当拍，捐出方 + 受赠方每 10 拍利息的净变化（引擎利率公式；捐出方领土取 resim_squad.csv 里不晚于落地拍的最近采样）。
        # 按 dispatch_audit.csv 的 kind 分类（没有该文件时只给合计）。净变化 > 0 时“回本拍数”= 手续费 / 净变化 × 10。
        sqrows = defaultdict(list)
        for r in load(mid, 'resim_squad.csv'):
            if r['bot'] in squad:
                sqrows[squad[r['bot']]].append((int(r['t']), int(r['terr'])))
        def terr_at(pid, t):
            best = None
            for tt, te in sqrows.get(pid, []):
                if tt <= t:
                    best = te
                else:
                    break
            return best
        kind_of = {}
        dpath = os.path.join(HERE, '..', 'out', mid, 'dispatch_audit.csv')
        if os.path.exists(dpath):
            for r in csv.DictReader(open(dpath)):
                if r.get('executed') == '1' and r.get('execTick'):
                    kind_of[(r['bot'].split(':')[-1], int(r['execTick']), int(r['to']))] = r['kind']
        land_all = meta['land']
        agg_k = defaultdict(lambda: [0, 0, 0, 0, 0, 0])   # kind -> 笔数, 净变化合计, 净变化为负的笔数, 手续费, 到账, 低密度给高密度的笔数
        det = []
        for r in tr:
            t = int(r['t']); f = int(r['from']); to = int(r['to'])
            B, nominal, rec, fee, _ = parts(r)
            fterr = terr_at(f, t); tterr = int(r['toTerr']); tb = int(r['toBal'])
            if not fterr or not tterr:
                continue
            def inc(terr, bal):
                return interest_rates(t, terr, bal, land_all)[1] * bal // 10 ** 4
            before = inc(fterr, B) + inc(tterr, tb)
            after = inc(fterr, B - fee - rec) + inc(tterr, tb + rec)
            k = kind_of.get((lab[f], t, to), '?')
            x = agg_k[k]; x[0] += 1; x[1] += after - before; x[2] += (after < before); x[3] += fee; x[4] += rec; x[5] += (B / fterr < tb / tterr)
            det.append((t, lab[f], lab[to], k, B / fterr, tb / tterr, rec, fee, after - before))
        print('  落地当拍 双方每 10 拍利息的净变化（按调度类型）：')
        for k, x in sorted(agg_k.items(), key=lambda kv: -kv[1][0]):
            pay = f"{10 * x[3] / x[1]:.0f} 拍回本" if x[1] > 0 else '不回本'
            print(f"    {k:22s} {x[0]:3d} 笔 到账 {x[4]:9d} 手续费 {x[3]:8d} 利息净变化 {x[1]:+8d}/10拍（{x[2]} 笔为负；{pay}） 捐出方密度<受赠方 {x[5]} 笔")
        if '--list' in sys.argv:
            for d in det:
                print(f"    t={d[0]} {d[1]}→{d[2]} {d[3]} 密度 {d[4]:.0f}→{d[5]:.0f} 到账 {d[6]} 手续费 {d[7]} 利息净变化 {d[8]:+d}/10拍")

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


def _isqrt_e(h):
    if h < 1:
        return 0
    x = (h + 1) // 2
    for _ in range(9):
        x = (x + h // x) // 2
    return x


_ITABLE = [100 + _isqrt_e((25600 * i) // 508) for i in range(512)]


def interest_rates(t, terr, bal, land):
    """引擎 interestRate（src/sim/sim/game.js L739–752）：返回 (不考虑超额扣减的利率, 实际利率)，单位 1e-4/10 拍。"""
    n1 = _ITABLE[min(511, 511 * terr // land)]
    if t < 1920:
        n1 = max(100 * (13440 - 6 * t) // 1920, n1)
    full = min(max(n1, 0), 700)
    cap = min(100 * terr, 10 ** 9)
    if bal > cap and cap > 0:
        n1 -= 2 * n1 * (bal - cap) // cap
    return full, min(max(n1, 0), 700)


def capidle_section(mid, meta, squad, t0, t1, win):
    """引擎利息（src/sim/sim/game.js interestRate/economyTick）：每 10 拍 bal += max(floor(rate*bal/1e4), 1)，
    rate = TABLE[floor(511*terr/land)]（t<1920 时不低于 floor(100*(13440-6t)/1920)），bal > 100*terr 时 rate -= floor(2*rate*(bal-cap)/cap)，下限 0、上限 700。
    这里对每个采样点算 满额利率下的利息 − 实际利率下的利息，乘以采样间隔/10，得到“少拿的利息”（近似：把采样点的状态当作整个间隔的状态）。"""
    land = meta['land']
    rows = [r for r in load(mid, 'resim_squad.csv') if r['bot'] in squad and r['alive'] == '1' and t0 <= int(r['t']) <= t1]
    ts = sorted({int(r['t']) for r in rows})
    step = ts[1] - ts[0] if len(ts) > 1 else 30
    def rates(t, terr, bal):
        return interest_rates(t, terr, bal, land)
    per = defaultdict(lambda: [0, 0, 0, 0, 0, 0])   # bot -> 采样点数, >=100, >=125, >=149.5, 少拿的利息, 实拿的利息
    wins = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])  # 窗口 -> 采样点数, >=100, >=149.5, 少拿, 实拿, nb=0 的号·点, 号·点
    for r in rows:
        t, terr, bal = int(r['t']), int(r['terr']), int(r['bal'])
        if terr <= 0:
            continue
        d = bal / terr
        full, act = rates(t, terr, bal)
        lost = (full - act) * bal // 10 ** 4 * step // 10
        got = act * bal // 10 ** 4 * step // 10
        x = per[r['bot']]; x[0] += 1; x[1] += d >= 100; x[2] += d >= 125; x[3] += d >= 149.5; x[4] += lost; x[5] += got
        w = wins[t // win * win]; w[0] += 1; w[1] += d >= 100; w[2] += d >= 149.5; w[3] += lost; w[4] += got; w[5] += (r['enemyNb'] == ''); w[6] += 1
    print(f"== capidle 满仓闲置（采样间隔 {step} 拍，区间 [{t0},{t1}]）")
    print("   号        采样点  密度>=100  >=125  >=149.5 | 少拿的利息   实拿的利息  少拿/应拿")
    tot = [0, 0, 0, 0, 0, 0]
    for b in sorted(per, key=lambda k: -per[k][4]):
        x = per[b]
        for i in range(6):
            tot[i] += x[i]
        print(f"   {b:<8} {x[0]:>6} {x[1]:>9} {x[2]:>6} {x[3]:>8} | {x[4]:>10} {x[5]:>12}  {100 * x[4] / max(1, x[4] + x[5]):.1f}%")
    print(f"   合计     {tot[0]:>6} {tot[1]:>9} {tot[2]:>6} {tot[3]:>8} | {tot[4]:>10} {tot[5]:>12}  {100 * tot[4] / max(1, tot[4] + tot[5]):.1f}%")
    print("   窗口起点  号·采样点  密度>=100  >=149.5  没有敌邻的号·点 | 少拿的利息  实拿的利息  少拿/应拿")
    for k in sorted(wins):
        w = wins[k]
        print(f"   {k:>8} {w[0]:>10} {w[1]:>9} {w[2]:>8} {w[5]:>10}/{w[6]:<5} | {w[3]:>10} {w[4]:>11}  {100 * w[3] / max(1, w[3] + w[4]):.1f}%")


def spawnseq_section(mid, meta, squad):
    """出生排位的变动：协调器给每个号发过多少版位置（日志 [HL-SPAWN-BACKEND]），录像里这个号实际落地了几条出生指令、最后站在哪一版上。"""
    import re
    W = meta['W']
    lp = f'/agent/repos/c136-data/bundles/{mid}/in_game.log'
    plans = defaultdict(list)
    for line in open(lp, encoding='utf8'):
        m = re.search(r'^(\d+)\t\[([^\]]+)\] \[HL-SPAWN-BACKEND\] me=\d+ slot=(\d+) role=(\w+) -> \((\d+),(\d+)\)', line)
        if m:
            plans[m.group(2)].append((int(m.group(1)), int(m.group(5)), int(m.group(6)), m.group(4)))
    cmds = defaultdict(list)
    for r in load(mid, 'replay_cmds.csv'):
        if r['kind'] == 'spawn':
            px = int(r['dX'])
            cmds[int(r['player'])].append((int(r['step']), int(r['tick']), px % W, px // W))
    dist = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    print('== spawnseq（号 | 协调器发过几版位置 / 不同位置数 / 相邻两版的位移 中位·最大 | 录像里落地的出生指令条数 | 最后落地的位置 = 倒数第几版 | 最后一版位置）')
    final = {}; lastplan = {}; stale = 0
    for b, p in sorted(squad.items(), key=lambda kv: kv[1]):
        pl = plans.get(b, []); cm = cmds.get(p, [])
        if not pl or not cm:
            print(f'  {b:<8} 版数 {len(pl)} 落地 {len(cm)}'); continue
        jumps = sorted(dist(pl[i][1:3], pl[i + 1][1:3]) for i in range(len(pl) - 1))
        fx = cm[-1][2:4]; final[b] = fx; lastplan[b] = pl[-1][1:3]
        back = next((k for k in range(1, len(pl) + 1) if pl[-k][1:3] == fx), None)
        if back != 1: stale += 1
        print(f"  {b:<8} {len(pl):>3} 版 / {len(set(x[1:3] for x in pl)):>2} 个位置 / 位移 {jumps[len(jumps) // 2] if jumps else 0:.0f}·{jumps[-1] if jumps else 0:.0f} | 落地 {len(cm):>2} 条（最后一条在出生阶段第 {cm[-1][0]} 步）| ({fx[0]},{fx[1]}) = "
              + (f'倒数第 {back} 版' if back else '不在任何一版里') + f" | 最后一版 ({pl[-1][1]},{pl[-1][2]}) {pl[-1][3]}")
    bots = sorted(final)
    close = [(dist(final[x], final[y]), x, y) for i, x in enumerate(bots) for y in bots[i + 1:]]
    close.sort()
    empty = [f'({v[0]},{v[1]})' for b, v in sorted(lastplan.items()) if all(dist(v, f) > 20 for f in final.values())]
    print(f"  最后落地位置不是最后一版的号：{stale}/{len(final)}；实际出生点相距最近的 3 对：" + ' '.join(f'{x}-{y} {d:.0f}' for d, x, y in close[:3])
          + f"；最后一版里 20 像素内没有任何本队号的位置：{' '.join(empty) or '无'}")
    # 最后一版本身（各号最后一条）是不是同一次求解：最后一版的位置有没有重复
    lp_list = sorted(lastplan.values())
    dup = sorted({v for v in lp_list if lp_list.count(v) > 1})
    print(f"  各号“最后一版”之间重复的位置：{' '.join(f'({v[0]},{v[1]})' for v in dup) or '无'}（有重复 = 各号手里的最后一版不是同一次求解的结果）")


def drops_section(mid, meta, squad):
    lab = {p: b for b, p in squad.items()}
    players = load(mid, 'resim_players.csv'); cmds = load(mid, 'replay_cmds.csv'); pairs = load(mid, 'resim_pairs.csv')
    names = meta['names']
    nm = lambda p: lab.get(p) or (names[p] if isinstance(names, list) else names.get(str(p), str(p))) if p < meta['humans'] else f'AI#{p}'
    by = defaultdict(list)
    for r in players:
        if int(r['p']) in lab:
            by[int(r['p'])].append(r)
    print('== drops（号 t0→t1 余额 领土 | 区间内落地的本号指令：进攻条数/Σ(pct+1)/1024、船、捐款 | 同拍 >=3 条的批次 | 被拿走的地 | 归类）')
    cnt = defaultdict(int)
    for p, rs in by.items():
        for x, y in zip(rs, rs[1:]):
            b0, b1 = int(x['bal']), int(y['bal'])
            if x['alive'] != '1' or x['state'] == '2' or b0 <= 0 or b1 > 0.7 * b0:
                continue
            t0, t1 = int(x['t']), int(y['t'])
            mine = [c for c in cmds if int(c['player']) == p and t0 < int(c['tick']) <= t1]
            at = [c for c in mine if c['kind'] == 'attack']; bo = [c for c in mine if c['kind'] == 'boat']; dn = [c for c in mine if c['kind'] == 'donate']
            frac = sum((int(c['dX']) + 1) / 1024 for c in at + bo)
            ticks = defaultdict(int)
            for c in at:
                ticks[int(c['tick'])] += 1
            batch = {t: n for t, n in ticks.items() if n >= 3}
            lost = defaultdict(int)
            for r in pairs:
                if int(r['victim']) == p and int(r['t0']) >= t0 and int(r['t1']) <= t1:
                    lost[int(r['attacker'])] += int(r['px'])
            lostPx = sum(lost.values())
            kind = '捐款' if dn else '过期指令成批落地' if batch and frac >= 0.3 else '自己出兵' if frac >= 0.3 else '挨打' if lostPx >= 0.03 * int(x['terr']) else '自己出兵（小额多次）' if at else '不明'
            cnt[kind] += 1
            print(f"  {lab[p]:<8} {t0:>5}→{t1:<5} {b0:>8}→{b1:<8} ({100 * (b1 - b0) / b0:.0f}%) 领土 {x['terr']}→{y['terr']} | 进攻 {len(at)} 条/{frac:.2f} 船 {len(bo)} 捐 {len(dn)} | "
                  f"批次 {' '.join(f'{t}×{n}' for t, n in sorted(batch.items())) or '-'} | 丢地 {' '.join(f'{nm(a)}:{v}' for a, v in sorted(lost.items(), key=lambda kv: -kv[1])[:3]) or '-'} | {kind}")
    print('  归类合计：' + '；'.join(f'{k} {v}' for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])))


if __name__ == '__main__':
    main()
