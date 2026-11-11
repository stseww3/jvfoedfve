#!/usr/bin/env python3
"""pattern_scan2.py — 第二批全量机械检测：捐兵去向 / 打真人的放行口 / 船 / 出生几何 / 每拍一条。

和 pattern_scan.py 一样只读对局包文件与录像命令流（不跑引擎、不跑影子策略），可对全部有录像的对局包跑；
pattern_scan.py 管「指令有没有按时落地」（L/O/M/N/D/B/R/P/C/X/F/G），这里管「落地的指令去了哪」。

输入（每局）：
  /agent/repos/c136-data/bundles/<局>/{card.json, in_game.log, results.csv, traj.csv}
  /tmp/c136-r05/cmds/<局>.tsv、headers.json（replay_dump_all.mjs：录像命令流解码，= 引擎真正执行的指令）
号 ↔ 座位：同 pattern_scan.py（[HL-GAME-INIT] me= / results.csv meId；座位上的录像名去掉 [标签] 后 = 号名才算在这一盘里）。

检测项（每项的「近似」都写明了；带 ≈ 的数是用日志采样估的，不是引擎真值）：
  K 捐兵去向（录像里执行了的、捐出方是我方号的捐兵）
      K.n0 / K.n1 / K.n2      t<3213 / 3213–4283 / ≥4284 的笔数（配额按全图地计价 / 按受赠方地计价 / 不限）
      K.burst3213             [3213, 3513) 的笔数与捐出的号数；K.burst4284 = [4284, 4884) 的笔数与号数
      K.pingpong              同一对号 300 拍内反方向也有一笔的笔数（两个方向都计）
      K.relay                 p→q 之后 100 拍内 q→r（r≠p）的笔数（转手，第二道税）
      K.outside               受赠方不是我方号（路人队友）的笔数
      K.recipLost / recipGrew 受赠方是我方号且有轨迹：到账前最近一次采样的地 L0（≤180 拍内）；之后 300 拍内的采样最小值 ≤0.8×L0
                              或 300 拍内阵亡 → 丢地；否则最大值 ≥1.2×L0 → 长地（K.recipKnown = 可判的笔数）。采样是客户端本地拍，延迟波局里偏晚。
      K.nominal≈ / K.tax≈     每笔 ≈ (pct+1)/1024 × 捐出方最近一次采样的存兵；税 ≈ 存兵/16（没有采样的笔不计）
  V 打真人的放行口（代理）：我方号 t≥1500 执行的、目标是真人座位的陆攻
      V.n / V.known           条数 / 其中发令前 180 拍内有采样的
      V.over                  采样密度 ≥100 的条数（`buyLand` L5352–5359：存兵 > 100×地 时跳过价格门）；V.overNominal≈ / V.nominal≈ 同 K 的估法
  T 船：我方号执行的出船指令
      T.n / T.scout           条数 / 其中 pct=0（只带最小兵力的探路船；船费是当时全部存兵的 3.125%，与 pct 无关）
      T.fee≈ / T.scoutFee≈    船费 ≈ 最近一次采样的存兵/32
  H 出生几何（选点期最后一条出生指令 = 最终出生点；地图宽取日志 `(map=宽x高`，没有就按同一张地图别的局的宽）
      H.sq / H.noSpawn        录像盘里的我方号数 / 其中一条出生指令都没有的（引擎随机落子，坐标未知，不进下面的几何）
      H.stack / H.close       我方号两两距离 ≤2 格的对数 / <20 格的对数
      H.nnMed                 每个我方号到最近我方号的距离，取中位
      H.in40                  其他真人（含路人队友，录像命令流里没有队伍）最终出生点落在任一我方号 40 格内的人数
      H.inHull                其他真人最终出生点落在我方号凸包内的人数（我方号 ≥3 个才算）
  E 每拍一条：results.csv 的 sent − accepted（策略想发、适配层没收的条数；只有有结算行的号）
      E.sent / E.dropped / E.bots
输出：--tsv 每局一行；--json 全部字段；--agg 全量合计 + 「有/没有」对赢局数；--check 用 13 局真值（/tmp/c136-r05/truth）核对 K、V 两个近似。
用法：python3 scripts/pattern_scan2.py [局…] [--tsv out/pattern-scan2.tsv] [--json FILE] [--agg] [--check] [--only A|B]
"""
import bisect
import collections
import csv
import json
import math
import os
import re
import statistics
import sys

a = sys.argv[1:]
opt = lambda k: a[a.index(k) + 1] if k in a else None
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--tsv', '--json', '--only'))]
SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
CMDS = '/tmp/c136-r05/cmds'
HEAD = json.load(open(f'{CMDS}/headers.json'))
if not ids:
    ids = sorted(d for d in os.listdir(f'{SRC}/bundles') if os.path.exists(f'{SRC}/bundles/{d}/replay.txt'))
if opt('--only'):
    ids = [x for x in ids if x[0] in opt('--only')]
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()
IDMAP = collections.defaultdict(list)
for r in csv.DictReader(open(f'{SRC}/src/tools/identity-map-discovery.csv', encoding='utf-8')):
    IDMAP[r['matchId']].append(r)
MAPW = {}            # mapId → 宽（从有 `(map=宽x高` 的局学来）


def ver_of(mid):
    if mid[0] == 'B':
        return 'c110'
    if mid[0] == 'G':
        return 'g09'
    n = int(mid[1:])
    return 'Va' if n <= 17 else 'Vb' if n <= 95 else 'Vc'


def log_width(B):
    with open(f'{B}/in_game.log', encoding='utf-8', errors='replace') as f:
        for i, ln in enumerate(f):
            m = re.search(r'\(map=(\d+)x(\d+)', ln)
            if m:
                return int(m.group(1))
            if i > 60000:
                break
    return None


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cross = lambda o, p, q: (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def inside(h, p):
    if len(h) < 3:
        return False
    s = 0
    for i in range(len(h)):
        o, q = h[i], h[(i + 1) % len(h)]
        c = (q[0] - o[0]) * (p[1] - o[1]) - (q[1] - o[1]) * (p[0] - o[0])
        if c < 0:
            return False
        s += 1
    return True


def scan(mid):
    B = f'{SRC}/bundles/{mid}'
    card = json.load(open(f'{B}/card.json'))
    hd = HEAD.get(mid) or {}
    if 'error' in hd or not os.path.exists(f'{CMDS}/{mid}.tsv'):
        return {'matchId': mid, 'error': hd.get('error', '缺命令流')}
    H, names, total = hd['humans'], hd['names'], hd['totalTicks']
    endT = card['outcome'].get('endTick') or 0
    alias = {}
    for r in IDMAP.get(mid, []):
        ch = [x for x in (r.get('nameChain') or '').split('→') if x]
        for n in ch[1:]:
            alias[n] = ch[0]
    al = lambda n: alias.get(n, n)
    me = {}
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.match(r'\d+\t\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)', ln)
        if m:
            me.setdefault(al(m.group(1)), int(m.group(2)))
    res = {}
    for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
        b = al(r['bot'])
        res[b] = r
        if b not in me and r.get('meId'):
            me[b] = int(r['meId'])
    inrep = {b: p for b, p in me.items() if p < H and p < len(names) and bare(names[p]) == b.lower()}
    pid2bot = {p: b for b, p in inrep.items()}
    traj = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        try:
            traj[al(r['bot'])].append((int(r['t']), int(r['terr']), int(r['bal']), float(r['dens'])))
        except (ValueError, KeyError):
            continue
    tk = {}
    for b in traj:
        traj[b].sort()
        tk[b] = [x[0] for x in traj[b]]
    died = {b: int(r['tick']) for b, r in res.items() if r.get('event') == 'died' and (r.get('tick') or '').lstrip('-').isdigit()}

    def sample(b, t, maxage=180):
        if b not in tk:
            return None
        i = bisect.bisect_right(tk[b], t) - 1
        if i < 0 or t - tk[b][i] > maxage:
            return None
        return traj[b][i]

    don, atk, boats, spawn = [], [], [], {}
    for r in csv.DictReader(open(f'{CMDS}/{mid}.tsv', encoding='utf-8'), delimiter='\t'):
        p, t, i = int(r['player']), int(r['tick']), int(r['id'])
        if i == 0 and p < H:
            spawn[p] = int(r['a'])
            continue
        b = pid2bot.get(p)
        if i == 2 and p < H:
            don.append((t, p, int(r['b']), int(r['a'])))
        if b is None:
            continue
        if i == 1:
            q = int(r['b'])
            if q < H and t >= 1500:
                atk.append((t, b, q, int(r['a'])))
        elif i == 3:
            boats.append((t, b, int(r['a'])))
    o = {'matchId': mid, 'cohort': card.get('cohort'), 'ver': ver_of(mid), 'result': card['outcome']['resultLabel'], 'endTick': endT,
         'replayTicks': total, 'covered': total >= endT - 120, 'humans': H, 'inReplay': len(inrep), 'teams': card.get('actualTeams') or card.get('nominalTeams'),
         'baseWin': card.get('baseWinExpectation')}
    # ---- K ----
    mine = [d for d in don if d[1] in pid2bot]
    rev = collections.defaultdict(list)
    for t, p, q, pct in don:
        rev[(p, q)].append(t)
    K = {'n0': 0, 'n1': 0, 'n2': 0, 'burst3213': 0, 'burst3213Donors': 0, 'burst4284': 0, 'burst4284Donors': 0, 'pingpong': 0, 'pingpong2': 0, 'relay': 0, 'outside': 0,
         'recipKnown': 0, 'recipLost': 0, 'recipGrew': 0, 'recipKnown2': 0, 'recipLost2': 0, 'nominal': 0, 'tax': 0, 'nominal2': 0, 'tax2': 0, 'priced': 0}
    b1, b2 = set(), set()
    out_by = collections.defaultdict(list)
    for t, p, q, pct in mine:
        out_by[p].append((t, q))
    for t, p, q, pct in mine:
        w = 0 if t < 3213 else 1 if t < 4284 else 2
        K[f'n{w}'] += 1
        if 3213 <= t < 3513:
            K['burst3213'] += 1
            b1.add(p)
        if 4284 <= t < 4884:
            K['burst4284'] += 1
            b2.add(p)
        pp = any(abs(t2 - t) <= 300 for t2 in rev.get((q, p), []))
        K['pingpong'] += pp
        K['pingpong2'] += pp and w == 2
        K['relay'] += any(t < t2 <= t + 100 and r_ != p for t2, r_ in out_by.get(q, []))
        K['outside'] += q not in pid2bot
        s = sample(pid2bot[p], t)
        if s:
            K['priced'] += 1
            K['nominal'] += s[2] * (pct + 1) // 1024
            K['tax'] += s[2] // 16
            if w == 2:
                K['nominal2'] += s[2] * (pct + 1) // 1024
                K['tax2'] += s[2] // 16
        rb = pid2bot.get(q)
        s0 = sample(rb, t) if rb else None
        if s0 and s0[1] > 0:
            fut = [x[1] for x in traj[rb] if t < x[0] <= t + 300]
            dead = rb in died and died[rb] <= t + 300
            if fut or dead:
                K['recipKnown'] += 1
                K['recipKnown2'] += w == 2
                if dead or min(fut) <= 0.8 * s0[1]:
                    K['recipLost'] += 1
                    K['recipLost2'] += w == 2
                elif max(fut) >= 1.2 * s0[1]:
                    K['recipGrew'] += 1
    K['burst3213Donors'], K['burst4284Donors'] = len(b1), len(b2)
    o['K'] = K
    # ---- V ----
    V = {'n': len(atk), 'known': 0, 'over': 0, 'nominal': 0, 'overNominal': 0, 'n2': 0, 'known2': 0, 'over2': 0}
    for t, b, q, pct in atk:
        s = sample(b, t)
        late = t >= 4284
        V['n2'] += late
        if not s:
            continue
        V['known'] += 1
        V['known2'] += late
        v = s[2] * (pct + 1) // 1024
        V['nominal'] += v
        if s[3] >= 100:
            V['over'] += 1
            V['over2'] += late
            V['overNominal'] += v
    o['V'] = V
    # ---- T ----
    T = {'n': len(boats), 'scout': 0, 'fee': 0, 'scoutFee': 0, 'priced': 0, 'n1500': 0}
    for t, b, pct in boats:
        T['scout'] += pct == 0
        T['n1500'] += t >= 1500
        s = sample(b, t)
        if s:
            T['priced'] += 1
            T['fee'] += s[2] // 32
            if pct == 0:
                T['scoutFee'] += s[2] // 32
    o['T'] = T
    # ---- H ----
    W = log_width(B)
    if W:
        MAPW.setdefault(card.get('mapId'), W)
    o['_mapId'] = card.get('mapId')
    o['_spawn'] = spawn
    o['_seats'] = sorted(pid2bot)
    o['_W'] = W
    # ---- E ----
    E = {'sent': 0, 'dropped': 0, 'bots': 0}
    for b in inrep:
        r = res.get(b)
        if r and (r.get('sent') or '').isdigit() and (r.get('accepted') or '').isdigit():
            E['sent'] += int(r['sent'])
            E['dropped'] += int(r['sent']) - int(r['accepted'])
            E['bots'] += 1
    o['E'] = E
    return o


def geometry(o):
    W = o.pop('_W') or MAPW.get(o.pop('_mapId'))
    o.pop('_mapId', None)
    spawn, seats = o.pop('_spawn'), o.pop('_seats')
    Hh = {'sq': len(seats), 'noSpawn': sum(1 for p in seats if p not in spawn), 'W': W}
    if W:
        xy = lambda px: (px % W, px // W)
        sq = [xy(spawn[p]) for p in seats if p in spawn]
        ot = [xy(px) for p, px in spawn.items() if p not in seats]
        d = lambda u, v: math.hypot(u[0] - v[0], u[1] - v[1])
        pairs = [d(sq[i], sq[j]) for i in range(len(sq)) for j in range(i + 1, len(sq))]
        Hh['stack'] = sum(1 for x in pairs if x <= 2)
        Hh['close'] = sum(1 for x in pairs if x < 20)
        nn = [min(d(u, v) for j, v in enumerate(sq) if j != i) for i, u in enumerate(sq)] if len(sq) >= 2 else []
        Hh['nnMed'] = round(statistics.median(nn), 1) if nn else None
        Hh['in40'] = sum(1 for u in ot if any(d(u, v) <= 40 for v in sq)) if sq else 0
        hl = hull(sq)
        Hh['inHull'] = sum(1 for u in ot if inside(hl, u)) if len(hl) >= 3 else None
        Hh['others'] = len(ot)
    o['H'] = Hh
    return o


R = [scan(m) for m in ids]
R = [geometry(o) if 'error' not in o else o for o in R]
ok = [o for o in R if 'error' not in o and o['inReplay'] > 0]
if opt('--json'):
    json.dump(R, open(opt('--json'), 'w', encoding='utf-8'), ensure_ascii=False)
COLS = ['matchId', 'cohort', 'ver', 'result', 'endTick', 'covered', 'humans', 'inReplay',
        'K.n0', 'K.n1', 'K.n2', 'K.burst3213', 'K.burst3213Donors', 'K.burst4284', 'K.burst4284Donors', 'K.pingpong', 'K.pingpong2', 'K.relay', 'K.outside',
        'K.recipKnown', 'K.recipLost', 'K.recipGrew', 'K.nominal', 'K.tax', 'K.nominal2', 'K.tax2',
        'V.n', 'V.known', 'V.over', 'V.nominal', 'V.overNominal', 'V.n2', 'V.known2', 'V.over2',
        'T.n', 'T.scout', 'T.fee', 'T.scoutFee', 'T.n1500',
        'H.sq', 'H.noSpawn', 'H.stack', 'H.close', 'H.nnMed', 'H.in40', 'H.inHull', 'H.others',
        'E.sent', 'E.dropped', 'E.bots']


def cell(o, c):
    if '.' in c:
        g, k = c.split('.')
        v = (o.get(g) or {}).get(k)
    else:
        v = o.get(c)
    return '' if v is None else (str(int(v)) if isinstance(v, bool) else str(v))


if opt('--tsv'):
    with open(opt('--tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(COLS) + '\n')
        for o in R:
            if 'error' in o:
                f.write(f"{o['matchId']}\t{o['error']}\n")
            else:
                f.write('\t'.join(cell(o, c) for c in COLS) + '\n')

k_ = lambda x: f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k'
pc = lambda x, y: '–' if not y else f'{100*x/y:.0f}%'
if '--agg' in a:
    for grp in ('A', 'B'):
        S = [o for o in ok if o['matchId'][0] == grp]
        if not S:
            continue
        cov = [o for o in S if o['covered']]
        print(f'===== {grp} 组全量合计：{len(S)} 局（录像盘里至少有 1 个我方号；录全的 {len(cov)} 局）=====')
        t = collections.Counter()
        for o in S:
            for g in 'KVTE':
                for kk, v in o[g].items():
                    t[f'{g}.{kk}'] += v or 0
        n_all = t['K.n0'] + t['K.n1'] + t['K.n2']
        print(f"K 捐兵去向：执行 {n_all:,} 笔（t<3213 {t['K.n0']:,}、3213–4283 {t['K.n1']:,}、≥4284 {t['K.n2']:,}）；有执行的 {sum(1 for o in S if o['K']['n0']+o['K']['n1']+o['K']['n2'])} 局。")
        print(f"K 3213 拍后 300 拍内：{t['K.burst3213']:,} 笔（= 3213–4283 全部的 {pc(t['K.burst3213'], t['K.n1'])}），有的局 {sum(1 for o in S if o['K']['burst3213'])}，≥5 笔的 {sum(1 for o in S if o['K']['burst3213'] >= 5)} 局；"
              f"4284 拍后 600 拍内：{t['K.burst4284']:,} 笔（= ≥4284 全部的 {pc(t['K.burst4284'], t['K.n2'])}），有的局 {sum(1 for o in S if o['K']['burst4284'])}，≥10 笔的 {sum(1 for o in S if o['K']['burst4284'] >= 10)} 局。")
        print(f"K 来回（300 拍内反方向也有一笔）：{t['K.pingpong']:,} 笔 = 全部执行的 {pc(t['K.pingpong'], n_all)}；其中 ≥4284 的 {t['K.pingpong2']:,} 笔 = 该段的 {pc(t['K.pingpong2'], t['K.n2'])}；有的局 {sum(1 for o in S if o['K']['pingpong'])}，≥10 笔的 {sum(1 for o in S if o['K']['pingpong'] >= 10)} 局。")
        print(f"K 转手（收到后 100 拍内又捐给第三个号）：{t['K.relay']:,} 笔（{pc(t['K.relay'], n_all)}），有的局 {sum(1 for o in S if o['K']['relay'])}；捐给路人队友：{t['K.outside']:,} 笔（{pc(t['K.outside'], n_all)}）。")
        print(f"K 受赠方之后 300 拍（可判 {t['K.recipKnown']:,} 笔）：丢地 ≥20% 或阵亡 {t['K.recipLost']:,} 笔（{pc(t['K.recipLost'], t['K.recipKnown'])}），长地 ≥20% {t['K.recipGrew']:,} 笔（{pc(t['K.recipGrew'], t['K.recipKnown'])}）；"
              f"≥4284 的可判 {t['K.recipKnown2']:,} 笔里丢地 {t['K.recipLost2']:,} 笔（{pc(t['K.recipLost2'], t['K.recipKnown2'])}）。")
        for lab, sel in (('输的局', lambda o: o['result'] != 'won'), ('赢的局', lambda o: o['result'] == 'won')):
            SS = [o for o in S if sel(o)]
            if not SS:
                continue
            u = collections.Counter()
            for o in SS:
                for kk, v in o['K'].items():
                    u[kk] += v or 0
                u['fee'] += o['T']['fee']
                u['scoutFee'] += o['T']['scoutFee']
                u['boats'] += o['T']['n']
                u['scout'] += o['T']['scout']
            nn = u['n0'] + u['n1'] + u['n2']
            print(f"K/T 金额≈（{lab} {len(SS)} 局）：捐兵 {nn:,} 笔，捐出 {k_(u['nominal'])}、税 {k_(u['tax'])}（税÷捐出 {pc(u['tax'], u['nominal'])}）；其中 ≥4284：{u['n2']:,} 笔 {k_(u['nominal2'])}、税 {k_(u['tax2'])}，来回 {u['pingpong2']:,} 笔（{pc(u['pingpong2'], u['n2'])}）；"
                  f"船 {u['boats']:,} 条、船费 {k_(u['fee'])}，其中探路船 {u['scout']:,} 条、船费 {k_(u['scoutFee'])}（{pc(u['scoutFee'], u['fee'])}）。")
        print(f"V 打真人（t≥1500；弱代理，逐局误差见 --check，不拿来给对局分类）：{t['V.n']:,} 条，其中有采样的 {t['V.known']:,} 条；采样密度 ≥100 的 {t['V.over']:,} 条（{pc(t['V.over'], t['V.known'])}）；"
              f"≥4284：{t['V.over2']:,}/{t['V.known2']:,}（{pc(t['V.over2'], t['V.known2'])}）。")
        print(f"T 船：{t['T.n']:,} 条（t≥1500 的 {t['T.n1500']:,}），其中 pct=0 的探路船 {t['T.scout']:,} 条（{pc(t['T.scout'], t['T.n'])}）；每局船数中位 {statistics.median([o['T']['n'] for o in S]):.0f}，0 条的 {sum(1 for o in S if not o['T']['n'])} 局；"
              f"每局探路船船费≈ 的中位 {k_(statistics.median([o['T']['scoutFee'] for o in S]))}，≥500k 的 {sum(1 for o in S if o['T']['scoutFee'] >= 500e3)} 局。")
        Hs = [o for o in S if o['H'].get('W')]
        print(f"H 出生几何（知道地图宽的 {len(Hs)} 局）：有我方号 0 条出生指令的 {sum(1 for o in S if o['H']['noSpawn'])} 局（共 {sum(o['H']['noSpawn'] for o in S)} 个号）；"
              f"有同点堆叠（≤2 格）的 {sum(1 for o in Hs if o['H']['stack'])} 局（{sum(o['H']['stack'] for o in Hs)} 对）；有 <20 格的号对的 {sum(1 for o in Hs if o['H']['close'])} 局；"
              f"最近我方号距离中位的中位 {statistics.median([o['H']['nnMed'] for o in Hs if o['H'].get('nnMed') is not None]):.0f} 格；"
              f"40 格内有其他真人的 {sum(1 for o in Hs if o['H']['in40'])} 局（人数中位 {statistics.median([o['H']['in40'] for o in Hs]):.0f}）；"
              f"凸包内有其他真人的 {sum(1 for o in Hs if o['H'].get('inHull'))}/{sum(1 for o in Hs if o['H'].get('inHull') is not None)} 局（人数中位 {statistics.median([o['H']['inHull'] for o in Hs if o['H'].get('inHull') is not None]):.0f}，≥3 人的 {sum(1 for o in Hs if (o['H'].get('inHull') or 0) >= 3)} 局）。")
        print(f"E 每拍一条：有结算行的 {t['E.bots']:,} 个号，想发 {t['E.sent']:,} 条、适配层没收 {t['E.dropped']:,} 条（{100*t['E.dropped']/max(1,t['E.sent']):.1f}%）；没收 ≥5% 的局 {sum(1 for o in S if o['E']['sent'] and o['E']['dropped'] >= 0.05 * o['E']['sent'])}/{sum(1 for o in S if o['E']['sent'])}。")
        print()
    # ---- 有/没有 对 赢 ----
    print('===== 各检测项把对局分成「有 / 没有」两类：赢的局数对期望赢局数 =====')
    print('只算录像盘里至少有 1 个我方号的局；赢 = resultLabel=won；期望赢 = 各局 baseWinExpectation（没有就 1÷队数）之和。')
    print('\t'.join(['组别', '检测项', '可判的局', '有：局数', '有：赢', '有：期望赢', '没有：局数', '没有：赢', '没有：期望赢']))
    TESTS = [
        ('K ≥4284 执行的捐兵 ≥20 笔', lambda o: o['replayTicks'] >= 4884, lambda o: o['K']['n2'] >= 20),
        ('K 4284 拍后 600 拍内 ≥10 笔', lambda o: o['replayTicks'] >= 4884, lambda o: o['K']['burst4284'] >= 10),
        ('K 来回 ≥10 笔', lambda o: o['replayTicks'] >= 4884, lambda o: o['K']['pingpong'] >= 10),
        ('K 受赠方 300 拍内丢地 ≥30%（可判 ≥10 笔）', lambda o: o['K']['recipKnown'] >= 10, lambda o: o['K']['recipLost'] >= 0.3 * o['K']['recipKnown']),
        ('T 全程出船 ≤5 条（录像到 3000 拍）', lambda o: o['replayTicks'] >= 3000, lambda o: o['T']['n'] <= 5),
        ('T 探路船 ≥10 条', lambda o: o['replayTicks'] >= 3000, lambda o: o['T']['scout'] >= 10),
        ('H 有我方号 0 条出生指令', lambda o: True, lambda o: o['H']['noSpawn'] >= 1),
        ('H 同点堆叠 ≥1 对', lambda o: bool(o['H'].get('W')), lambda o: o['H']['stack'] >= 1),
        ('H 凸包内其他真人 ≥3 人', lambda o: o['H'].get('inHull') is not None, lambda o: o['H']['inHull'] >= 3),
        ('H 40 格内其他真人 ≥3 人', lambda o: bool(o['H'].get('W')), lambda o: o['H']['in40'] >= 3),
        ('E 适配层没收 ≥5%', lambda o: o['E']['sent'] > 0, lambda o: o['E']['dropped'] >= 0.05 * o['E']['sent']),
    ]
    for grp in ('A', 'B', 'A+B'):
        S = [o for o in ok if o['matchId'][0] in grp]
        for name, can, has in TESTS:
            C = [o for o in S if can(o)]
            y = [o for o in C if has(o)]
            n = [o for o in C if not has(o)]
            ex = lambda L: sum((o.get('baseWin') or (1 / o['teams'] if o.get('teams') else 0)) for o in L)
            wn = lambda L: sum(1 for o in L if o['result'] == 'won')
            print('\t'.join([grp, name, str(len(C)), str(len(y)), str(wn(y)), f'{ex(y):.1f}', str(len(n)), str(wn(n)), f'{ex(n):.1f}']))
    print()

if '--check' in a:
    print('===== 近似口径对真值（13 局；真值 = match_truth.mjs 逐拍重演）=====')
    print('\t'.join(['局', '捐兵笔数 扫描/真值', '捐出≈/真值到账', '税≈/真值税', '打真人条数(t≥1500) 扫描/真值', '放行口条数占比 扫描/真值', '放行口兵占比 扫描≈/真值']))
    dK, dT, dV = [], [], []
    for o in ok:
        p = f"/tmp/c136-r05/truth/{o['matchId']}.json"
        if not os.path.exists(p):
            continue
        J = json.load(open(p))
        sq = {s['p'] for s in J['squad']}
        ad = [x for x in J['allDon'] if x[1] in sq]
        at = [e for e in J['events'] if e['type'] == 'attack' and e['p'] in sq and e.get('q') is not None and 0 <= e['q'] < J['humans'] and e.get('ok', True) and e['t'] >= 1500]
        ov = [e for e in at if e['B0'] > 100 * e['L0']]
        sp = lambda e: e.get('troops', 0) + e.get('fee', 0)
        K, V = o['K'], o['V']
        print('\t'.join([o['matchId'], f"{K['n0']+K['n1']+K['n2']}/{len(ad)}", f"{k_(K['nominal'])}/{k_(sum(x[3] for x in ad))}", f"{k_(K['tax'])}/{k_(sum(x[4] for x in ad))}",
                         f"{V['n']}/{len(at)}", f"{pc(V['over'], V['known'])}/{pc(len(ov), len(at))}", f"{pc(V['overNominal'], V['nominal'])}/{pc(sum(sp(e) for e in ov), sum(sp(e) for e in at))}"]))
        if ad:
            dK.append(abs(K['nominal'] / sum(x[3] for x in ad) - 1))
            dT.append(abs(K['tax'] / sum(x[4] for x in ad) - 1))
        if at and V['known']:
            dV.append(abs(100 * V['over'] / V['known'] - 100 * len(ov) / len(at)))
    if dK:
        print(f"K 金额近似的相对误差（有捐兵的 {len(dK)} 局）：捐出 中位 {100*statistics.median(dK):.0f}%、最大 {100*max(dK):.0f}%；税 中位 {100*statistics.median(dT):.0f}%、最大 {100*max(dT):.0f}%。捐兵笔数与真值逐局相等。")
    if dV:
        print(f"V 放行口条数占比的绝对误差（{len(dV)} 局）：中位 {statistics.median(dV):.0f} 个百分点、最大 {max(dV):.0f} 个百分点；差 ≥15 个百分点的 {sum(1 for x in dV if x >= 15)} 局。原因：采样每 90 个本地拍一次，密度在两次采样之间被捐兵/出兵改变，延迟波局本地拍还落后于服务器拍。")
