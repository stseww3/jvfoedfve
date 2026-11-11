#!/usr/bin/env python3
"""delay_account.py — 一局的「延迟硬账」（广播 0007 第 2 条）：出生点执行、指令延迟、两笔直接损失。全部机械计数。

输入（先各跑一次）：
  node scripts/match_truth.mjs <id>                          → /tmp/c136-r05/truth/<id>.json   （录像逐拍重放真值）
  node scripts/shadow.mjs <id> --quiet --json /tmp/c136-r05/work/<id>-shadow.json           （影子决策：零延迟策略每拍想发什么）
  node scripts/replay_cmds.mjs <id> --out /tmp/c136-r05/work/<id>-cmds.tsv                  （录像原始命令流，含选点期）
  node scripts/atk_fate.mjs <id> --json /tmp/c136-r05/work/<id>-atkfate.json                （每一场进攻的下场；没有这个文件时不出「退回/拿地」列）
  对局包 /agent/repos/c136-data/bundles/<id>/{in_game.log, spawn.csv, traj.csv, results.csv}

口径：
  t_intent（决策拍）= 影子决策的拍号。游戏是锁步的：客户端本地第 t 拍看到的局面 = 录像第 t 拍的局面，
      所以影子在第 t 拍算出的指令就是真实客户端在它本地第 t 拍下的那条（各局影子指令数与号自报 cmds= 逐号相等或差 1–2 条）。
  t_exec（落地拍）= 录像里这条指令被执行的拍。延迟 = t_exec − t_intent（含：客户端落后服务器的拍数 + 传输 + 等下一个 7 拍帧）。
  配对（每个号独立做，每条决策最多用一次）：
      同一拍落地 ≥2 条 = 一批：把这一批的 (类型, pct) 序列倒过来，在决策流里找「连续的一段」完全相同的（倒序 = 实测的落地次序）；
          倒序找不到再试顺序。只有一处 → 唯一；多处 → 先用前后已唯一配上的批夹住（决策次序不能倒流），还多处就取最晚的一处
          （延迟取下界），并记下最早那一处给出的上界。
          夹住的区间里找不到时放开次序再找一次（先落地新决策、后落地旧决策的批），仍取最晚一处、算「下界」。
  单条：决策拍 < 落地拍、类型与 pct 相同、目标相同或落地目标是中立（原目标已死会被改写成中立）的决策里取最晚的一条；
          候选只有一条 → 唯一，否则算「下界」。
      都找不到 → 「没配上」（单列，不进分位数）。
  分位数：P50 = 中位；P90 = 第 ceil(0.9n) 小的值（最近秩）。
  时段：0–600 / 600–1500 / 1500–3000 / 3000+（按落地拍分；漏斗按决策拍分）。
  落空 = 录像里执行了但 ok=False（目标/中立已不接壤，一个兵没打出去）。改写 = 决策目标是机器人/真人，落地时目标已是中立。
  同拍批 = 同一个号同一拍落地 ≥3 条陆攻/出船。批前存兵 = 这一批第一条执行前的存兵；抽干比例 = 这一批（兵 + 手续费）÷ 批前存兵。
  在途重复 = 一条已落地的陆攻（决策拍 t1、落地拍 T1）在途期间（t1 < t ≤ T1），同一个号又对同一目标下的陆攻决策。
  退回 / 拿地 / 被打掉：按「场」（同一个进攻槽从开到关）记账，再按各条指令的兵数占这一场总投入的比例摊回每条指令。

用法：python3 scripts/delay_account.py <matchId> [--json FILE] [--bots a,b] [--list-batches]
"""
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

a = sys.argv[1:]
mid = a[0]
val = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
only = set((val('--bots', '') or '').split(',')) - {''}
B = os.environ.get('C136_DATA', '/agent/repos/c136-data') + f'/bundles/{mid}'
W = '/tmp/c136-r05/work'
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
S = json.load(open(f'{W}/{mid}-shadow.json'))
H = J['humans']
MW = J['map']['W']
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {v: k for k, v in sq.items()}
P = {p['id']: p for p in J['players']}
PER = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
PN = ['0–600', '600–1500', '1500–3000', '3000+']
per = lambda t: next(i for i, (lo, hi) in enumerate(PER) if lo <= max(0, t) < hi)
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
pc = lambda x, y: f'{100 * x / y:.0f}%' if y else '-'


def q50(v):
    v = sorted(v)
    n = len(v)
    return None if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def q90(v):
    v = sorted(v)
    return None if not v else v[max(0, math.ceil(0.9 * len(v)) - 1)]


f0 = lambda x: '-' if x is None else f'{x:.0f}'
cls = lambda q: 'N' if q >= 512 else ('H' if q < H else 'B')
CN = {'N': '中立', 'B': '机器人', 'H': '真人', 'S': '船', 'D': '捐'}
OUT = {'matchId': mid, 'periods': PN}

# ---------- 决策流、执行流 ----------
D = defaultdict(list)
for r in S['ticks']:
    for c in r['cmds']:
        kk = {'attack': 'attack', 'boat': 'boat', 'boatTo': 'boat', 'donate': 'donate'}.get(c['k'])
        if kk:
            D[r['bot']].append({'t': r['t'], 'k': kk, 'pct': c['pct'], 'q': c.get('q', -1), 'troops': c.get('troops', 0), 'bal': r['bal'], 'terr': r['terr'],
                                'c': 'D' if kk == 'donate' else 'S' if kk == 'boat' else cls(c.get('q', 512)), 'x': None})
# 客户端本地最后一拍：有结算行（results.csv）的取它的 tick；没有的（中途离场的号）、或结算行比最后一条日志还早的，取最后一条日志的拍 + 89（下一条日志没写出来）。
# 影子在这之后算出的决策，真实客户端没有跑到，不算「想发」。
LASTLOC = {}
_tj = defaultdict(int)
if os.path.exists(f'{B}/traj.csv'):
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        _tj[r['bot']] = max(_tj[r['bot']], int(r['t']))
_rs = {}
if os.path.exists(f'{B}/results.csv'):
    for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
        _rs[r['bot']] = int(r['tick'])
PHANTOM = defaultdict(list)
for b_ in list(D):
    rt_, lt_ = _rs.get(b_), _tj.get(b_)
    if rt_ is None and lt_ is None:
        cap = 10 ** 9
    elif rt_ is None or (lt_ is not None and lt_ > rt_):
        cap = lt_ + 89   # 没有结算行，或结算行的拍号早于最后一条日志（A058 四个失联的号：结算行 805–987，日志写到 1080–1350）：按日志算
    else:
        cap = rt_
    LASTLOC[b_] = cap
    PHANTOM[b_] = [d for d in D[b_] if d['t'] > cap]
    D[b_] = [d for d in D[b_] if d['t'] <= cap]
E = defaultdict(list)
for i, e in enumerate(J['events']):
    if e['type'] in ('attack', 'boat', 'donate') and e.get('p') in sq:
        E[sq[e['p']]].append({**e, 'T': e['t'], 'k': e['type'], 'i': i, 'd': None, 'm': '没配上'})
bots = [b for b in sorted(set(D) | set(E), key=lambda b: pid.get(b, 999)) if not only or b in only]


def compat(d, e):
    if d['k'] != e['k'] or d['pct'] != e['pct'] or d['x'] is not None:
        return False
    return e['k'] != 'attack' or d['q'] == e['q'] or e['q'] >= 512


def match_bot(bot):
    Ds, Es = D[bot], E[bot]
    groups = []
    for e in Es:
        if groups and groups[-1][0] == e['T']:
            groups[-1][1].append(e)
        else:
            groups.append((e['T'], [e]))
    fixed = {}  # 组序号 -> (起始决策下标, 长度)

    def cands(gi, lo, hi):
        T, es = groups[gi]
        n = len(es)
        res = []
        for order in ('rev', 'fwd'):
            seq = es[::-1] if order == 'rev' else es
            got = []
            for i in range(max(0, lo), min(len(Ds), hi) - n + 1):
                if Ds[i + n - 1]['t'] >= T:
                    break
                if all(compat(Ds[i + j], seq[j]) for j in range(n)):
                    got.append(i)
            if got:
                res = [(i, order) for i in got]
                break
            if n == 1:
                break
        return res

    def bounds(gi):
        lo, hi = 0, len(Ds)
        for g2, (i0, n0) in fixed.items():
            if g2 < gi:
                lo = max(lo, i0 + n0)
            elif g2 > gi:
                hi = min(hi, i0)
        return lo, hi

    def fix(gi, i0, order, tag, alt=None):
        T, es = groups[gi]
        seq = es[::-1] if order == 'rev' else es
        for j, e in enumerate(seq):
            d = Ds[i0 + j]
            d['x'] = e
            e['d'] = d
            e['m'] = tag
            e['order'] = order
            if alt is not None:
                e['alt'] = T - Ds[alt + j]['t']
        fixed[gi] = (i0, len(es))

    # 第一遍：批（≥2 条）里全局唯一的先钉住；再反复用已钉住的夹出新的唯一
    multi = [gi for gi, (T, es) in enumerate(groups) if len(es) >= 2]
    changed = True
    first = True
    while changed:
        changed = False
        for gi in multi:
            if gi in fixed:
                continue
            lo, hi = (0, len(Ds)) if first else bounds(gi)
            c = cands(gi, lo, hi)
            if len(c) == 1:
                fix(gi, c[0][0], c[0][1], '唯一')
                changed = True
        if first:
            first, changed = False, True
    # 第二遍：按落地先后处理剩下的（批取最晚一处；单条取最晚一条）
    for gi, (T, es) in enumerate(groups):
        if gi in fixed:
            continue
        lo, hi = bounds(gi)
        c = cands(gi, lo, hi)
        if c:
            fix(gi, c[-1][0], c[-1][1], '唯一' if len(c) == 1 else '下界', alt=None if len(c) == 1 else c[0][0])
            continue
        # 夹住的区间里没有：放开「决策次序不能倒流」再找一次（实测有先落地新决策、后落地旧决策的批），取最晚一处，记成「下界」
        c = cands(gi, 0, len(Ds))
        if c:
            i0, order = c[-1]
            seq = es[::-1] if order == 'rev' else es
            for j, e in enumerate(seq):
                d = Ds[i0 + j]
                d['x'] = e
                e['d'] = d
                e['m'] = '下界'
                e['order'] = order
                e['ooo'] = True
            continue
        if len(es) >= 2:
            # 整批连续配不上：逐条各找最晚的一条（记成「逐条」）
            for e in es[::-1]:
                best = None
                for i in range(min(len(Ds), hi) - 1, max(0, lo) - 1, -1):
                    if Ds[i]['t'] < T and compat(Ds[i], e):
                        best = i
                        break
                if best is not None:
                    Ds[best]['x'] = e
                    e['d'] = Ds[best]
                    e['m'] = '逐条'


for b in bots:
    match_bot(b)
allE = [e for b in bots for e in E[b]]
allD = [d for b in bots for d in D[b]]
for b in bots:
    for e in E[b]:
        e['bot'] = b
    for d in D[b]:
        d['bot'] = b
ab = [e for e in allE if e['k'] in ('attack', 'boat')]
dab = [d for d in allD if d['k'] in ('attack', 'boat')]

# ---------- 每一场进攻的下场（可选） ----------
EP = None
fp = f'{W}/{mid}-atkfate.json'
if os.path.exists(fp):
    EP = json.load(open(fp))['episodes']
    idx = defaultdict(list)
    for ep in EP:
        for t, tr in ep.get('adds', []):
            idx[(ep['p'], t, tr)].append(ep)
    for e in ab:
        if e['k'] != 'attack' or not e.get('ok') or not e.get('troops'):
            continue
        c = [ep for ep in idx.get((e['p'], e['T'], e['troops']), []) if min(ep['target'], 512) == min(e['q'], 512)] or idx.get((e['p'], e['T'], e['troops']), [])
        if c:
            ep = c[0]
            sh = e['troops'] / max(1, ep['sent'])
            e['ret'] = ep['ret'] * sh
            e['tiles'] = (ep['tiles'] + ep['neutTiles']) * sh
            e['burnt'] = ep.get('burnt', 0) * sh
            e['epd'] = ep.get('t1', ep['t0']) - ep['t0']


def fate(es):
    """一组已执行指令：打出（兵）、手续费、退回、被打掉、拿地"""
    out = sum(e.get('troops', 0) for e in es if e.get('ok'))
    fee = sum(e.get('fee', 0) for e in es if e.get('ok'))
    ret = sum(e.get('ret', 0) for e in es)
    burnt = sum(e.get('burnt', 0) for e in es)
    tiles = sum(e.get('tiles', 0) for e in es)
    return out, fee, ret, burnt, tiles


# =====================================================================
print(f'===== {mid} 延迟硬账（{J["map"]["W"]}×{J["map"]["H"]}，真人 {H}，我方号 {len(sq)} 个在录像里；影子版本 {S.get("ver")}）=====')

# ---------- ① 出生点执行 ----------
print('\n== ① 出生点执行（协调器给的坐标有没有落到录像里）==')
solves = []
logp = f'{B}/in_game.log'
if os.path.exists(logp):
    for ln in open(logp, encoding='utf-8', errors='replace'):
        m = re.search(r'\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \((.*?)\): (.*)', ln)
        if m:
            solves.append((int(m.group(1)), float(m.group(2)), m.group(3), m.group(4).strip()))
assign = defaultdict(list)
sp_csv = f'{B}/spawn.csv'
if os.path.exists(sp_csv):
    for r in csv.DictReader(open(sp_csv, encoding='utf-8')):
        assign[r['bot']].append((int(r['x']), int(r['y']), r['role'], int(r['line'])))
rsp = defaultdict(list)  # 录像里的出生指令
phase0 = 0
cp = f'{W}/{mid}-cmds.tsv'
others_sp = defaultdict(list)
if os.path.exists(cp):
    for r in csv.DictReader(open(cp, encoding='utf-8'), delimiter='\t'):
        if r['kind'] != 'spawn':
            continue
        t, p, px = int(r['tick']), int(r['player']), int(r['a'])
        phase0 = min(phase0, t)
        (rsp[sq[p]] if p in sq else others_sp[p]).append((t, px % MW, px // MW))
else:
    print(f'   （缺 {cp}：先跑 node scripts/replay_cmds.mjs {mid} --out {cp}）')
res_rows = {}
if os.path.exists(f'{B}/results.csv'):
    for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
        res_rows[r['bot']] = r
lastcmds = {}
traj = defaultdict(list)
if os.path.exists(f'{B}/traj.csv'):
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        traj[r['bot']].append((int(r['t']), int(r['cmds']), int(r['line'])))
        lastcmds[r['bot']] = int(r['cmds'])
distinct = len(set(s[3] for s in solves))
print(f'   协调器求解 {len(solves)} 轮（不同的解 {distinct} 个；每轮耗时 中位 {f0(q50([s[1] for s in solves]))} 毫秒）'
      + (f'；求解对象 {solves[-1][0]} 个号，{solves[-1][2]}' if solves else '')
      + f'｜选点期 = 录像拍 {phase0}…0｜其他真人里有出生指令的 {len(others_sp)}/{H - len(sq)} 个')
SP = []
verd = Counter()
for b in bots:
    p = pid[b]
    act = P[p]['spawn']
    A = assign.get(b, [])
    R = rsp.get(b, [])
    fin = A[-1][:2] if A else None
    near = lambda pt, lst: min((math.hypot(pt[0] - x, pt[1] - y) for x, y in lst), default=None)
    if not R:
        v = '0 条落地→引擎随机落子'
    else:
        ex = R[-1][1:]
        if fin and math.hypot(ex[0] - fin[0], ex[1] - fin[1]) <= 2:
            v = '最终坐标落地'
        elif any(math.hypot(ex[0] - x, ex[1] - y) <= 2 for x, y, *_ in A[:-1]):
            v = '停在旧坐标'
        else:
            v = '落在日志里没有的坐标'
    verd[v] += 1
    rr = res_rows.get(b)
    sends = (int(rr['accepted']) - lastcmds.get(b, 0)) if rr and rr.get('accepted') and b in lastcmds else None
    dfin = math.hypot(act[0] - fin[0], act[1] - fin[1]) if fin else None
    SP.append({'bot': b, 'assignN': len(A), 'final': fin, 'replaySpawnN': len(R), 'replayTicks': [r[0] for r in R], 'exec': list(R[-1][1:]) if R else None,
               'actual': act, 'verdict': v, 'distActualToFinal': dfin, 'localSendsApprox': sends})
    print(f'   {b}: 日志指派 {len(A)} 次，最后 {fin}（{A[-1][2] if A else "-"}）｜录像里出生指令 {len(R)} 条'
          + (f'（拍 {",".join(str(r[0]) for r in R)}；最后一条 ({R[-1][1]},{R[-1][2]})）' if R else '')
          + f'｜实际出生 {tuple(act)}，离最后指派 {f0(dfin)} 格｜{v}'
          + (f'｜本地受理的非进攻发送约 {sends} 条（accepted − 最后一条日志的 cmds）' if sends is not None else ''))
acts = {b: P[pid[b]]['spawn'] for b in bots}
stack = []
bl = list(acts)
for i in range(len(bl)):
    for j in range(i + 1, len(bl)):
        d = math.hypot(acts[bl[i]][0] - acts[bl[j]][0], acts[bl[i]][1] - acts[bl[j]][1])
        if d <= 12:
            stack.append((bl[i], bl[j], round(d, 1)))
nn = []
for b in bl:
    ds = [math.hypot(acts[b][0] - acts[o][0], acts[b][1] - acts[o][1]) for o in bl if o != b]
    nn.append(min(ds) if ds else 0)
landed_ticks = [r[0] for b in bots for r in rsp.get(b, [])]
print(f'   合计：' + '；'.join(f'{v} {n} 个号' for v, n in verd.most_common())
      + f'｜叠点（实际出生点相距 ≤12 格）{len(stack)} 对{("：" + "、".join(f"{x}/{y} {d}格" for x, y, d in stack)) if stack else ""}'
      + f'｜实际出生点到最近我方号 中位 {f0(q50(nn))} 格（最小 {f0(min(nn) if nn else None)}，最大 {f0(max(nn) if nn else None)}）'
      + (f'｜我方出生指令落地拍 {min(landed_ticks)}…{max(landed_ticks)}（选点期第 {min(landed_ticks) - phase0}…{max(landed_ticks) - phase0} 拍）' if landed_ticks else '｜我方没有任何出生指令落地'))
OUT['spawn'] = {'solveRounds': len(solves), 'distinctSolutions': distinct, 'phaseStart': phase0, 'bots': SP, 'verdicts': dict(verd), 'stackPairs': stack,
                'nearestAllyMedian': q50(nn), 'othersWithSpawnCmd': len(others_sp), 'others': H - len(sq)}

# ---------- ② 指令延迟 ----------
print('\n== ② 指令延迟 t_exec − t_intent（陆攻 + 出船；按落地拍分时段）==')
T2 = []
for i, nm in enumerate(PN):
    es = [e for e in ab if per(e['T']) == i]
    mt = [e for e in es if e['d']]
    st = [e['T'] - e['d']['t'] for e in mt]
    un = [e['T'] - e['d']['t'] for e in mt if e['m'] == '唯一']
    ub = [e.get('alt', e['T'] - e['d']['t']) for e in mt]
    row = {'period': nm, 'landed': len(es), 'matched': len(mt), 'unique': len(un), 'p50': q50(st), 'p90': q90(st), 'max': max(st) if st else None,
           'uP50': q50(un), 'uP90': q90(un), 'uMax': max(un) if un else None, 'hiP50': q50(ub), 'ge35': sum(1 for x in st if x >= 35), 'ge90': sum(1 for x in st if x >= 90), 'ge300': sum(1 for x in st if x >= 300)}
    T2.append(row)
    print(f'   {nm}: 落地 {len(es)} 条，配上 {len(mt)}（唯一 {len(un)}）｜延迟 P50 {f0(row["p50"])} / P90 {f0(row["p90"])} / 最大 {f0(row["max"])} 拍'
          f'｜只算唯一：P50 {f0(row["uP50"])} / P90 {f0(row["uP90"])} / 最大 {f0(row["uMax"])}｜上界口径 P50 {f0(row["hiP50"])}'
          f'｜≥35 拍 {row["ge35"]} 条、≥90 拍 {row["ge90"]} 条、≥300 拍 {row["ge300"]} 条')
w300 = defaultdict(list)
for e in ab:
    if e['d']:
        w300[e['T'] // 300 * 300].append(e['T'] - e['d']['t'])
print('   每 300 拍（落地拍）延迟中位/最大：' + '；'.join(f'{w}: {f0(q50(v))}/{max(v)}（{len(v)} 条）' for w, v in sorted(w300.items())))
OUT['delayBy300'] = [{'t': w, 'p50': q50(v), 'max': max(v), 'n': len(v)} for w, v in sorted(w300.items())]
base = T2[0]['uP50'] if T2[0]['uP50'] is not None else T2[0]['p50']
print(f'   基线（0–600 的唯一配对中位）= {f0(base)} 拍：传输 + 等下一个 7 拍帧；高出基线的部分 = 客户端落后服务器的拍数。1 拍 ≈ 56 毫秒。')
OUT['delayByPeriod'] = T2
OUT['baseline'] = base

print('   -- 每个号落后服务器多少拍（延迟中位 − 基线；括号里是 最大延迟 / 落地条数；「-」= 这一段没有落地的指令）')
PB = {}
for b in bots:
    cells = []
    PB[b] = []
    for i in range(4):
        st = [e['T'] - e['d']['t'] for e in E[b] if e['k'] in ('attack', 'boat') and e['d'] and per(e['T']) == i]
        n = sum(1 for e in E[b] if e['k'] in ('attack', 'boat') and per(e['T']) == i)
        PB[b].append({'n': n, 'p50': q50(st), 'max': max(st) if st else None})
        cells.append(f'{PN[i]} {f0(None if not st else q50(st) - (base or 0))}（{f0(max(st) if st else None)}/{n}）')
    print(f'      {b}: ' + '｜'.join(cells))
OUT['lagByBot'] = PB

# 日志先后：各号的 [HL-TICK] 行按写入先后排，领头的号写到第几拍 − 自己这一行的拍
order_rows = sorted(((ln, t, b) for b, v in traj.items() for t, c, ln in v))
lead = 0
LL = defaultdict(lambda: [[] for _ in range(4)])
for ln, t, b in order_rows:
    lead = max(lead, t)
    LL[b][per(t)].append(lead - t)
if order_rows:
    print('   -- 旁证：日志先后（同一刻各号本地拍与领头号的差；每 90 拍一个样本，只能看到 ≥90 拍的落后）')
    for b in bots:
        if b in LL:
            print(f'      {b}: ' + '｜'.join(f'{PN[i]} 中位 {f0(q50(LL[b][i]))} 最大 {f0(max(LL[b][i]) if LL[b][i] else None)}（{sum(1 for x in LL[b][i] if x >= 90)}/{len(LL[b][i])} 行 ≥90）' for i in range(4)))
    OUT['logOrderLag'] = {b: [{'p50': q50(v[i]), 'max': max(v[i]) if v[i] else None, 'ge90': sum(1 for x in v[i] if x >= 90), 'n': len(v[i])} for i in range(4)] for b, v in LL.items()}

print('   -- 漏斗（按决策拍分时段）：影子想发（已过每拍一条的闸）→ 号自报受理 cmds= → 录像里落地')
FN = []
for i, nm in enumerate(PN):
    ds = [d for d in dab if per(d['t']) == i]
    ld = [d for d in ds if d['x']]
    okx = lambda d: bool(d['x'].get('ok') and d['x'].get('troops'))
    dead = lambda d: d['k'] == 'attack' and d['q'] < 512 and d['x']['q'] >= 512
    hit = [d for d in ld if okx(d) and not dead(d)]
    rew_ok = [d for d in ld if dead(d) and okx(d)]
    rew_void = [d for d in ld if dead(d) and not okx(d)]
    void = [d for d in ld if not dead(d) and not okx(d)]
    row = {'period': nm, 'intended': len(ds), 'intendedTroops': sum(d['troops'] for d in ds), 'landed': len(ld), 'asIntended': len(hit), 'deadToNeutral': len(rew_ok), 'deadVoid': len(rew_void), 'void': len(void),
           'neverLanded': len(ds) - len(ld), 'neverLandedTroops': sum(d['troops'] for d in ds if not d['x'])}
    FN.append(row)
    print(f'   {nm}: 想发 {len(ds)} 条 → 落地 {len(ld)}（{pc(len(ld), len(ds))}）＝ 照原目标打出 {len(hit)}（{pc(len(hit), len(ds))}）＋ 目标已死改打中立 {len(rew_ok)} ＋ 目标已死且落空 {len(rew_void)} ＋ 目标在但不接壤落空 {len(void)}'
          f'｜始终没落地 {row["neverLanded"]} 条（{pc(row["neverLanded"], len(ds))}）')
nph = sum(len(v) for b_, v in PHANTOM.items() if not only or b_ in only)
if nph:
    print('   不计入「想发」的：客户端没跑到的拍上影子算出的决策 ' + str(nph) + ' 条（' + '、'.join(f'{b_} 本地最后一拍 ≤{LASTLOC[b_]}：{len(v)} 条' for b_, v in PHANTOM.items() if v and (not only or b_ in only)) + '）')
OUT['phantom'] = {b_: {'lastLocalTick': LASTLOC[b_], 'n': len(v)} for b_, v in PHANTOM.items() if v}
nm_exec = Counter(per(e['T']) for e in ab if not e['d'])
print(f'   全程：想发 {len(dab)} 条 → 落地并配上 {sum(1 for d in dab if d["x"])}；录像里落地 {len(ab)} 条，其中没配上决策的 {sum(nm_exec.values())} 条（按落地时段 '
      + '、'.join(f'{PN[i]} {nm_exec.get(i, 0)}' for i in range(4)) + '）')
cm = []
for b in bots:
    if b not in traj:
        continue
    tl, cl, _ = traj[b][-1]
    sh = sum(1 for d in D[b] if d['t'] <= tl)
    ex = sum(1 for e in E[b] if e['T'] <= tl)
    cm.append((b, tl, sh, cl, ex))
print('   号自报对账（到各号最后一条日志为止）：' + '；'.join(f'{b} 影子 {sh}/自报 {cl}/落地 {ex}' for b, tl, sh, cl, ex in cm))
tot_sh, tot_cl, tot_ex = sum(x[2] for x in cm), sum(x[3] for x in cm), sum(x[4] for x in cm)
print(f'   合计：影子 {tot_sh}｜自报 {tot_cl}｜落地 {tot_ex}（{pc(tot_ex, tot_cl)}）')
OUT['funnel'] = FN
# 条数口径的校正：配对失败的落地指令（录像里有、没找到对应决策）会让「没落地」多算；真正没落地的条数上限 = 想发 − 录像里落地
OUT['funnelTotals'] = {'intended': len(dab), 'matched': sum(1 for d in dab if d['x']), 'executed': len(ab), 'unmatchedExec': sum(nm_exec.values()),
                       'unmatchedExecByPeriod': [nm_exec.get(i, 0) for i in range(4)], 'neverLandedByMatch': sum(1 for d in dab if not d['x']),
                       'neverLandedByCount': max(0, len(dab) - len(ab))}
ex_all = sum(len(E[b]) for b in bots)
print(f'   录像里这些号全程执行 {ex_all} 条（陆攻/出船/捐兵）；其中落在各号最后一条日志的拍号之后的 {ex_all - tot_ex} 条（落后的号的指令晚到）')
OUT['selfReport'] = {'shadow': tot_sh, 'cmds': tot_cl, 'landed': tot_ex, 'executedAll': ex_all,
                     'byBot': [{'bot': b, 'lastLogT': tl, 'shadow': sh, 'cmds': cl, 'landed': ex, 'executedAll': len(E[b])} for b, tl, sh, cl, ex in cm]}

# ---------- ③(a) 迟到落空 / 目标已死 ----------
print('\n== ③(a) 迟到落空与目标已死（按落地拍分时段；决策目标 = 配上的那条影子决策的目标）==')
LA = []
for i, nm in enumerate(PN):
    es = [e for e in ab if per(e['T']) == i and e['k'] == 'attack']
    row = {'period': nm}
    parts = []
    for c in ('B', 'H', 'N'):
        cs = [e for e in es if e['d'] and e['d']['c'] == c]
        if not cs:
            continue
        hit = [e for e in cs if e.get('ok') and e.get('troops') and e['q'] == e['d']['q']]
        rw_ok = [e for e in cs if c != 'N' and e['q'] >= 512 and e.get('ok') and e.get('troops')]
        rw_void = [e for e in cs if c != 'N' and e['q'] >= 512 and not (e.get('ok') and e.get('troops'))]
        void = [e for e in cs if e['q'] == e['d']['q'] and not (e.get('ok') and e.get('troops'))]
        o1, f1, r1, b1, t1 = fate(hit)
        o2, f2, r2, b2, t2 = fate(rw_ok)
        st_rw = [e['T'] - e['d']['t'] for e in rw_ok + rw_void]
        row[c] = {'landed': len(cs), 'hit': len(hit), 'hitOut': o1, 'hitRet': r1, 'hitTiles': t1, 'rewrittenOk': len(rw_ok), 'rewrittenOut': o2, 'rewrittenFee': f2, 'rewrittenRet': r2,
                  'rewrittenTiles': t2, 'rewrittenVoid': len(rw_void), 'void': len(void), 'intendedTroopsDead': sum(e['d']['troops'] for e in rw_ok + rw_void), 'staleRewrittenP50': q50(st_rw)}
        s = f'决策打{CN[c]} {len(cs)} 条：照打 {len(hit)}（打出 {k(o1)}' + (f'，退回 {k(r1)}＝{pc(r1, o1)}，拿 {t1:.0f} 格' if EP else '') + '）'
        if c != 'N':
            s += f'；目标已死→改写中立 {len(rw_ok) + len(rw_void)} 条（延迟中位 {f0(q50(st_rw))} 拍）：其中落空 {len(rw_void)}、打出去 {len(rw_ok)} 条 {k(o2)} 兵＋手续费 {k(f2)}' + (f'，退回 {k(r2)}＝{pc(r2, o2)}，拿中立 {t2:.0f} 格' if EP else '')
        s += f'；目标还在但已不接壤→落空 {len(void)}'
        parts.append(s)
    um = [e for e in es if not e['d']]
    if um:
        o, f, r, b_, t_ = fate(um)
        row['unmatched'] = {'n': len(um), 'void': sum(1 for e in um if not (e.get('ok') and e.get('troops'))), 'toNeutral': sum(1 for e in um if e['q'] >= 512), 'out': o, 'ret': r}
        parts.append(f'没配上决策 {len(um)} 条（目标中立 {row["unmatched"]["toNeutral"]}、落空 {row["unmatched"]["void"]}、打出 {k(o)}' + (f'、退回 {k(r)}' if EP else '') + '）')
    LA.append(row)
    print(f'   {nm}: ' + ('\n            '.join(parts) if parts else '没有落地的陆攻'))
OUT['lateVoid'] = LA

# ---------- ③(b) 同拍批与在途重复 ----------
print('\n== ③(b) 同拍批（同一个号同一拍落地 ≥3 条）与在途重复下单 ==')
batches = []
for b in bots:
    g = defaultdict(list)
    for e in E[b]:
        if e['k'] in ('attack', 'boat'):
            g[e['T']].append(e)
    for T, es in sorted(g.items()):
        if len(es) >= 3:
            o, f, r, bu, tl = fate(es)
            B0 = es[0]['B0']
            st = [e['T'] - e['d']['t'] for e in es if e['d']]
            intent = sum(e['d']['troops'] for e in es if e['d'])
            tg = Counter(('改写中立' if (e['d'] and e['d']['c'] in 'BH' and e['q'] >= 512) else CN['S' if e['k'] == 'boat' else cls(e['q'])]) for e in es)
            batches.append({'bot': b, 'T': T, 'n': len(es), 'void': sum(1 for e in es if not (e.get('ok') and e.get('troops'))), 'B0': B0, 'out': o, 'fee': f, 'drain': (o + f) / max(1, B0),
                            'ret': r, 'burnt': bu, 'tiles': tl, 'staleMin': min(st) if st else None, 'staleMax': max(st) if st else None, 'intended': intent, 'matched': len(st), 'targets': dict(tg)})
BT = []
for i, nm in enumerate(PN):
    bs = [x for x in batches if per(x['T']) == i]
    allv = [x for x in bs if x['void'] == x['n']]
    big = [x for x in bs if x['drain'] >= 0.5]
    row = {'period': nm, 'batches': len(bs), 'cmds': sum(x['n'] for x in bs), 'void': sum(x['void'] for x in bs), 'allVoidBatches': len(allv), 'out': sum(x['out'] for x in bs), 'fee': sum(x['fee'] for x in bs),
           'ret': sum(x['ret'] for x in bs), 'burnt': sum(x['burnt'] for x in bs), 'tiles': sum(x['tiles'] for x in bs), 'drain50': len(big), 'drain50Out': sum(x['out'] + x['fee'] for x in big),
           'drain50Bank': sum(x['B0'] for x in big), 'landedAll': sum(1 for e in ab if per(e['T']) == i)}
    BT.append(row)
    print(f'   {nm}: {len(bs)} 批 {row["cmds"]} 条（占这一段全部落地指令 {pc(row["cmds"], row["landedAll"])}）｜整批落空 {len(allv)} 批、落空共 {row["void"]} 条｜打出 {k(row["out"])}＋手续费 {k(row["fee"])}'
          + (f'｜退回 {k(row["ret"])}（{pc(row["ret"], row["out"])}）、付不起被打掉 {k(row["burnt"])}、拿地 {row["tiles"]:.0f} 格' if EP else '')
          + f'｜一批抽干 ≥50% 存兵的 {len(big)} 批（批前存兵合计 {k(row["drain50Bank"])} → 打出 {k(row["drain50Out"])}）')
if '--list-batches' in a:
    for x in batches:
        print(f'      {x["bot"]} t={x["T"]} ×{x["n"]}（落空 {x["void"]}）批前 {k(x["B0"])} 打出 {k(x["out"] + x["fee"])}＝{100 * x["drain"]:.0f}%｜决策时名义合计 {k(x["intended"])}（配上 {x["matched"]} 条，延迟 {f0(x["staleMin"])}–{f0(x["staleMax"])}）'
              + (f'｜退回 {k(x["ret"])} 拿地 {x["tiles"]:.0f}' if EP else '') + '｜' + '、'.join(f'{kk}×{v}' for kk, v in x['targets'].items()))
sizes = Counter(x['n'] for x in batches)
print(f'   批的条数分布：' + '、'.join(f'{n} 条×{c}' for n, c in sorted(sizes.items())) + f'｜全程 {len(batches)} 批 {sum(x["n"] for x in batches)} 条，占全部落地陆攻/出船 {pc(sum(x["n"] for x in batches), len(ab))}')
over = [(x['out'] + x['fee'], x['intended']) for x in batches if x['matched'] == x['n'] and x['intended'] > 0]
if over:
    print(f'   整批都配上决策的 {len(over)} 批：决策时名义合计 {k(sum(o[1] for o in over))} → 落地时实际打出 {k(sum(o[0] for o in over))}（{sum(o[0] for o in over) / max(1, sum(o[1] for o in over)):.2f} 倍；pct 是按落地那一刻的存兵重新折算的）')
OUT['batches'] = BT
OUT['batchList'] = batches
OUT['batchSizes'] = dict(sizes)

# 在途重复：一条陆攻决策 d2 算「在途重复」，当且仅当同一个号此前有一条同目标、已落地的陆攻决策 d1，且 d1.t < d2.t ≤ d1 的落地拍
# （客户端要到本地第 T1 拍才看得到 d1 生效，这之前的决策都看不到它）。
for b in bots:
    Ds = [d for d in D[b] if d['k'] == 'attack']
    openw = {}  # 目标 -> 最晚的在途落地拍
    for d in Ds:
        T1 = openw.get(d['q'], -1)
        d['rep'] = d['t'] <= T1
        if d['x']:
            openw[d['q']] = max(T1, d['x']['T'])
RP = []
for i, nm in enumerate(PN):
    dd = [d for d in allD if d['k'] == 'attack' and per(d['t']) == i]
    rep = [d for d in dd if d.get('rep')]
    le = [e for e in ab if e['k'] == 'attack' and per(e['T']) == i and e['d'] and e['d'].get('rep')]
    le_all = [e for e in ab if e['k'] == 'attack' and per(e['T']) == i and e['d']]
    o, f, r, bu, tl = fate(le)
    oa = sum(e.get('troops', 0) for e in le_all if e.get('ok'))
    RP.append({'period': nm, 'attackDecisions': len(dd), 'repeatDecisions': len(rep), 'landedRepeats': len(le), 'landedMatched': len(le_all), 'repeatOut': o, 'repeatFee': f, 'repeatRet': r, 'repeatTiles': tl, 'allOut': oa})
    print(f'   在途重复 {nm}: 按决策拍，陆攻决策 {len(dd)} 条里 {len(rep)} 条（{pc(len(rep), len(dd))}）是在同目标的前一条还没落地时下的'
          f'｜按落地拍，落地并配上的陆攻 {len(le_all)} 条里 {len(le)} 条是在途重复：打出 {k(o)}（占这一段配上的陆攻打出 {pc(o, oa)}）＋手续费 {k(f)}' + (f'，退回 {k(r)}（{pc(r, o)}），拿地 {tl:.0f} 格' if EP else ''))
OUT['inflightRepeats'] = RP

# 录像口径的「一轮」：同号同目标、相邻落地间隔 ≤21 拍（3 帧）的已执行陆攻，不同拍 ≥2 条
RD = []
for i, nm in enumerate(PN):
    rounds = []
    for b in bots:
        es = [e for e in E[b] if e['k'] == 'attack' and e.get('ok') and e.get('troops')]
        byq = defaultdict(list)
        for e in es:
            byq[e['q']].append(e)
        for q, L in byq.items():
            cur = [L[0]]
            for e in L[1:]:
                if e['T'] - cur[-1]['T'] <= 21:
                    cur.append(e)
                else:
                    rounds.append(cur)
                    cur = [e]
            rounds.append(cur)
    rs = [r for r in rounds if per(r[0]['T']) == i and len({e['T'] for e in r}) >= 2]
    RD.append({'period': nm, 'rounds': len(rs), 'cmds': sum(len(r) for r in rs), 'out': sum(e['troops'] + e['fee'] for r in rs for e in r), 'firstOut': sum(r[0]['troops'] + r[0]['fee'] for r in rs),
               'drainP50': q50([sum(e['troops'] + e['fee'] for e in r) / max(1, r[0]['B0']) for r in rs])})
    x = RD[-1]
    print(f'   连续下单 {nm}: 同号同目标相邻 ≤21 拍、跨 ≥2 个落地拍的 {x["rounds"]} 轮 {x["cmds"]} 条：合计打出 {k(x["out"])}（每轮第一条合计 {k(x["firstOut"])}）｜一轮打出占轮前存兵 中位 {f0(None if x["drainP50"] is None else 100 * x["drainP50"])}%')
OUT['rounds'] = RD

# 始终没落地的决策
print('\n== 始终没落地的决策（按决策拍；名义兵数 = 决策当拍按 pct 折算）==')
for i, nm in enumerate(PN):
    ds = [d for d in dab if per(d['t']) == i and not d['x']]
    cc = Counter(d['c'] for d in ds)
    tt = defaultdict(int)
    for d in ds:
        tt[d['c']] += d['troops']
    print(f'   {nm}: {len(ds)} 条｜' + '、'.join(f'打{CN[c]} {n} 条（{k(tt[c])}）' for c, n in cc.most_common()))
OUT['neverLanded'] = [{'period': nm, **{c: {'n': sum(1 for d in dab if per(d['t']) == i and not d['x'] and d['c'] == c), 'troops': sum(d['troops'] for d in dab if per(d['t']) == i and not d['x'] and d['c'] == c)} for c in 'NBHS'}} for i, nm in enumerate(PN)]

# 每条决策的下场（tick_attrib.py 用）：[号, 决策拍, 类型, 目标类别, 状态, 落地拍, 延迟]；状态 = hit 照原目标打出 / dead 目标已死（改打中立或落空）/ void 目标在但落空 / lost 始终没落地
def _st(d):
    x = d['x']
    if not x:
        return 'lost'
    okx = bool(x.get('ok') and x.get('troops'))
    if d['k'] == 'attack' and d['q'] < 512 and x['q'] >= 512:
        return 'dead'
    return 'hit' if okx else 'void'


OUT['decisions'] = [[d['bot'], d['t'], d['k'], d['c'], _st(d), d['x']['T'] if d['x'] else None, (d['x']['T'] - d['t']) if d['x'] else None, d['troops'],
                     (d['x'].get('troops', 0) if d['x'] and d['x'].get('ok') else 0), round(d['x'].get('ret', 0)) if d['x'] else 0] for d in allD]
OUT['lastLocalTick'] = LASTLOC
jo = val('--json')
if jo:
    json.dump(OUT, open(jo, 'w'), ensure_ascii=False)
    print(f'\n→ {jo}')
