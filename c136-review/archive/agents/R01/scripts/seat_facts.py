#!/usr/bin/env python3
"""seat_facts.py — 一局里“本队各号和身边对手”的几张机械小表（只读 out/<matchId>/ 下的重演产物）。
依赖：resim_meta.json、resim_players.csv（全体席位每 90 拍的领土/余额）、resim_pairs.csv（谁在哪个采样窗口从谁手里拿了多少格）、
      resim_events.csv（阵亡事件）、resim_squad.csv（本队号每 30 拍的邻居）、replay_cmds.csv（录像里落地的全部指令；先跑 replay_cmds.mjs）。
用法：python3 seat_facts.py <matchId> --section a,b,... [参数]
  foecmds   人类席位对本队各号下的每一条进攻令：落地拍、席位/队、pct、按对方上一采样点余额估的出兵量 [--bot 号名] [--t0 a --t1 b] [--brief 只打每个号的小计]
  who       指定席位自己落地的进攻/船/捐兵令 --seats 11,74 [--t0 a --t1 b]：落地拍、pct、目标、自己和目标在上一采样点的领土/余额/密度
  flows     本队某个号在若干窗口里从谁手里拿了几格、被谁拿走几格 --flows 号:t0:t1,号:t0:t1,...（只累加完全落在 [t0,t1] 里的 90 拍采样窗口）
  series    某个号和几个席位在指定采样点的 领土/余额(k)/密度 并排 --series '号:席位+席位+...:t,t,t;...'
  squad     本队各号在指定采样点的 领土/余额(k)/密度 --ticks t,t,...
  kills     本队参与过的敌方阵亡：阵亡拍、对方一生被夺的格数、其中本队各号夺得的格数、另外夺得最多的两个席位
  cmdcount  --t0 a --t1 b：窗口内每个在 t1 仍存活的人类席位落地的进攻令条数（本队 vs 其他；另列 t1 领土前 10 名）
  teamdon   全场落地的捐兵令按捐出方所在队汇总：笔数、付出、到账，到账最多的三个席位 [--team N 逐笔列出该队]
  adjacency --from t：从 t 拍起各号的采样点数、其中有同队邻居的点数（邻居是谁）、人类敌邻个数的中位/最大
说明：pct 是指令里的千分比（实际出兵 = 落地当拍余额 × (pct+1)/1024，这里用上一采样点余额估，只作量级）。
"""
import csv, json, os, re, statistics, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
D = os.path.join(HERE, '..', 'out', mid)
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding='utf8')))
meta = json.load(open(os.path.join(D, 'resim_meta.json')))
names, teams, H = meta['names'], meta['teams'], meta['humans']
squad = meta['squad']                      # 号名 -> 席位
seat2bot = {int(v): k for k, v in squad.items()}
tm = lambda p: teams[str(p)] if isinstance(teams, dict) else teams[p]
nm = lambda p: seat2bot.get(p) or (f'{names[p]}/T{tm(p)}' if p < H else f'AI#{p}')
secs = opt('section', '').split(',')

_pl = None
def players():
    global _pl
    if _pl is None:
        _pl = {(int(r['p']), int(r['t'])): (int(r['terr']), int(r['bal'])) for r in rd('resim_players.csv')}
    return _pl
def at(p, t):
    return players().get((p, (t // 90) * 90))
def tbd(s):
    return '-' if not s or s[0] == 0 else f'{s[0]}/{s[1] // 1000}k/{s[1] / max(1, s[0]):.0f}'

if 'foecmds' in secs:
    only = opt('bot')
    by = defaultdict(list)
    for r in rd('replay_cmds.csv'):
        if r['kind'] != 'attack': continue
        try: q = int(r['dZ'])
        except ValueError: continue
        p = int(r['player'])
        if q in seat2bot and p < H and p not in seat2bot: by[q].append((int(r['tick']), p, int(r['dX'])))
    ft0, ft1 = int(opt('t0', 0)), int(opt('t1', 10**9))
    brief = '--brief' in a
    print(f'== {mid} 人类席位对本队各号下的进攻令 [{ft0},{ft1}]（落地拍 | 席位 | pct | 估算出兵 = 对方上一采样点余额×(pct+1)/1024 | 对方上一采样点 领土/余额）')
    gn = ge = 0; gs = set()
    for q, lst in sorted(by.items(), key=lambda x: x[1][0][0]):
        if only and seat2bot[q] != only: continue
        lst = [x for x in lst if ft0 <= x[0] <= ft1]
        if not lst: continue
        est = lambda x: int((at(x[1], x[0]) or (0, 0))[1] * (x[2] + 1) / 1024)
        tot = sum(est(x) for x in lst); gn += len(lst); ge += tot; gs |= {x[1] for x in lst}
        print(f'  {seat2bot[q]}：{len(lst)} 条，来自 {len({p for _, p, _ in lst})} 个席位，估算出兵合计 {tot}')
        if brief: continue
        for t, p, pct in lst:
            s = at(p, t)
            print(f'     t={t} {nm(p)} pct={pct} 约 {est((t, p, pct))} 兵（领土 {s[0] if s else "?"} 余额 {s[1] if s else "?"}）')
    print(f'  合计 {gn} 条，来自 {len(gs)} 个席位，估算出兵 {ge}')

if 'who' in secs:
    seats = [int(x) for x in opt('seats').split(',')]
    t0, t1 = int(opt('t0', 0)), int(opt('t1', 10**9))
    rows = rd('replay_cmds.csv')
    print(f'== {mid} 指定席位落地的指令（落地拍 | 种类 | pct | 目标 | 自己上一采样点 领土/余额/密度 | 目标上一采样点 领土/余额/密度）')
    for pid in seats:
        mine = [r for r in rows if int(r['player']) == pid and r['kind'] in ('attack', 'boat', 'donate') and t0 <= int(r['tick']) <= t1]
        print(f'  {nm(pid)}：{len(mine)} 条（进攻 {sum(r["kind"] == "attack" for r in mine)}、船 {sum(r["kind"] == "boat" for r in mine)}、捐兵 {sum(r["kind"] == "donate" for r in mine)}）')
        for r in mine:
            t = int(r['tick']); s = at(pid, t); ts = None; tgt = r['tname'] or ''
            if r['kind'] != 'boat':
                try:
                    q = int(r['dZ']); ts = at(q, t) if q < H else None; tgt = nm(q) if q < H else (r['tname'] or f'AI#{q}')
                except ValueError: pass
            else: tgt = '（出海）'
            print(f'     t={t} {r["kind"]} pct={r["dX"]} -> {tgt} | {tbd(s)} | {tbd(ts) if ts else ""}')

if 'flows' in secs:
    pairs = rd('resim_pairs.csv')
    print(f'== {mid} 领土流向（窗口内 夺得：从谁手里拿了几格 | 失去：被谁拿走几格；按 90 拍采样窗口累加）')
    for spec in opt('flows').split(','):
        b, t0, t1 = spec.split(':'); p = int(squad[b]); t0, t1 = int(t0), int(t1)
        g, l = defaultdict(int), defaultdict(int)
        for r in pairs:
            if int(r['t0']) < t0 or int(r['t1']) > t1: continue
            if int(r['attacker']) == p: g[int(r['victim'])] += int(r['px'])
            if int(r['victim']) == p: l[int(r['attacker'])] += int(r['px'])
        f = lambda d: ' '.join(f'{nm(k)}:{v}' for k, v in sorted(d.items(), key=lambda x: -x[1])[:6]) or '-'
        print(f'  {b} [{t0},{t1}] 夺得 {sum(g.values())}：{f(g)} | 失去 {sum(l.values())}：{f(l)}')

if 'series' in secs:
    print(f'== {mid} 并排序列（每格 = 领土/余额(千)/密度）')
    for spec in opt('series').split(';'):
        b, others, ts = spec.split(':')
        ps = [int(squad[b])] + [int(x) for x in others.split('+') if x]
        print('  t     ' + ' '.join(f'{nm(p)[-18:]:>20}' for p in ps))
        for t in [int(x) for x in ts.split(',')]:
            print(f'  {t:<5} ' + ' '.join(f'{tbd(at(p, t)):>20}' for p in ps))

if 'squad' in secs:
    ticks = [int(x) for x in opt('ticks').split(',')]
    bots = list(squad.keys())
    print(f'== {mid} 本队各号（每格 = 领土/余额(千)/密度；- = 已不在场）')
    print('  t     ' + ' '.join(f'{b:>15}' for b in bots))
    for t in ticks:
        print(f'  {t:<5} ' + ' '.join(f'{tbd(at(int(squad[b]), t)):>15}' for b in bots))

if 'kills' in secs:
    print(f'== {mid} 本队参与过的敌方阵亡（阵亡拍 | 席位 | 死时剩 | 一生被夺格数 | 本队各号夺得（格数@最后一次夺地的拍）| 另外夺得最多的两个席位）')
    for e in rd('resim_events.csv'):
        if e['ev'] != 'died' or int(e['p']) in seat2bot or int(e['p']) >= H: continue
        m = re.search(r'tookLife=([^;]*)', e['detail'])
        if not m: continue
        tk = [x.split(':') for x in m.group(1).split('|') if x]
        mine = [(seat2bot[int(x[0])], int(x[1]), int(x[2])) for x in tk if int(x[0]) in seat2bot]
        if not mine: continue
        oth = [(nm(int(x[0])), int(x[1])) for x in tk if int(x[0]) not in seat2bot][:2]
        print(f'  t={e["t"]} {nm(int(e["p"]))} 剩 {e["terr"]} 格 {e["bal"]} 兵 | 被夺 {sum(int(x[1]) for x in tk)} | ' +
              ' '.join(f'{b}:{n}@{t}' for b, n, t in mine) + ' | ' + ' '.join(f'{n}:{v}' for n, v in oth))

if 'cmdcount' in secs:
    t0, t1 = int(opt('t0')), int(opt('t1'))
    cnt = defaultdict(int)
    for r in rd('replay_cmds.csv'):
        if r['kind'] == 'attack' and t0 <= int(r['tick']) < t1 and int(r['player']) < H: cnt[int(r['player'])] += 1
    te = (t1 // 90) * 90
    alive = [p for p in range(H) if (at(p, te) or (0, 0))[0] > 0]
    oth = [cnt[p] for p in alive if p not in seat2bot]
    our = sorted(cnt[p] for p in alive if p in seat2bot)
    print(f'== {mid} [{t0},{t1}) 落地的进攻令条数：{te} 拍仍存活的人类席位 {len(alive)} 个')
    print(f'  其他席位 {len(oth)} 个：中位 {statistics.median(oth)}，均值 {sum(oth) / len(oth):.1f}，最多 {max(oth)} | 本队存活 {len(our)} 个号：{our}，中位 {statistics.median(our) if our else "-"}')
    for p in sorted(alive, key=lambda p: -at(p, te)[0])[:10]:
        print(f'     {nm(p)}：{te} 拍领土 {at(p, te)[0]}，{(t0 // 90) * 90 + (90 if t0 % 90 else 0)} 拍领土 {(at(p, t0 + 89) or (0, 0))[0]}，进攻令 {cnt[p]} 条')

if 'adjacency' in secs:
    t0 = int(opt('from', 0))
    n, ally, who, en = defaultdict(int), defaultdict(int), defaultdict(set), defaultdict(list)
    for r in rd('resim_squad.csv'):
        if r['alive'] != '1' or int(r['terr']) == 0 or int(r['t']) < t0: continue
        b = r['bot']; n[b] += 1
        if r['allyNb']:
            ally[b] += 1
            for x in r['allyNb'].split('|'): who[b].add(nm(int(x.split(':')[0])))
        en[b].append(len([x for x in r['enemyNb'].split('|') if x]))
    print(f'== {mid} {t0} 拍起的邻居（号 | 采样点数 | 有同队邻居的点数（是谁）| 人类敌邻个数 中位/最大；enemyNb 一栏最多列 5 个）')
    for b in squad:
        if n[b]: print(f'  {b:8s} | {n[b]:3d} | {ally[b]:3d} {sorted(who[b]) or ""} | {statistics.median(en[b]):g}/{max(en[b])}')

if 'teamdon' in secs:
    by = defaultdict(lambda: [0, 0, 0, defaultdict(int)])
    for r in rd('resim_transfers.csv'):
        if r['ok'] != '1': continue
        f, to = int(r['from']), int(r['to'])
        if f >= H: continue
        b = by[tm(f)]; b[0] += 1; b[1] += int(float(r['paid'])); b[2] += int(float(r['received'])); b[3][to] += int(float(r['received']))
    print(f'== {mid} 全场落地的捐兵令（按捐出方的队）：笔数 | 付出 | 到账 | 到账最多的席位')
    for t in sorted(by):
        n, paid, got, rec = by[t]
        print(f'  T{t}：{n} 笔 | {paid} | {got} | ' + ' '.join(f'{nm(k)}:{v}' for k, v in sorted(rec.items(), key=lambda x: -x[1])[:3]))
    only_t = opt('team', None)
    if only_t is not None:
        print(f'  T{only_t} 各笔（落地拍 | 捐出方 -> 受赠方 | 付出 | 到账）：')
        for r in rd('resim_transfers.csv'):
            if r['ok'] != '1' or int(r['from']) >= H or tm(int(r['from'])) != int(only_t): continue
            print(f"     t={r['t']} {nm(int(r['from']))} -> {nm(int(r['to']))} | {int(float(r['paid']))} | {int(float(r['received']))}")
