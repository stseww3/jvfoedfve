#!/usr/bin/env python3
"""pattern_scan.py — 高频失分模式的机械计数：对全部 bundles/ 可跑，只读对局包文件和录像命令流，不跑引擎、不跑影子策略。

前置（一次）：bash ../../tools/run-heavy.sh node scripts/replay_dump_all.mjs      → /tmp/c136-r05/cmds/<局>.tsv、headers.json
用法：python3 scripts/pattern_scan.py [局…] [--tsv out/pattern-scan.tsv] [--json FILE] [--detail] [--sum] [--classes] [--only A|B|G]
      不给局号 = 全部对局包；--detail 逐号明细；--sum 末尾按「组别×结局」汇总；
      --classes 把各局按每个检测项分成「有/没有」两类，列每类的局数、赢的局数、按队数算的期望赢局数（card.json 的 baseWinExpectation 之和）；
      --agg 每个组别一段：各检测项的全量合计与分布。

输入（每局）：card.json（组别、结局、终局拍）、traj.csv（每号每 90 本地拍一条 [HL-TICK]：地、兵、密度、邻居数、累计发令数 cmds）、
      events.csv（[HL-DISPATCH]/[HL-DONATE] 捐兵日志行）、results.csv（结果行：事件、本地拍）、in_game.log（[HL-GAME-INIT] me=座位号）、
      src/tools/identity-map-discovery.csv（B 组日志前缀名轮换链，换回第一个名字）、录像命令流（只含引擎执行了的指令）。
号 ↔ 录像玩家：座位号 me < 真人数，且录像名单里该座位的名字去掉 [标签] 后 = 号名。对不上的号 = 不在这一盘录像里（拆盘），只进「日志类」检测。
录像长度：有的对局包里录像比对局短（B 组 22 局里有的只录到选点期）。replayTicks = 录像总拍数；covered = 录像至少到终局前 120 拍。
          录像没盖到的拍不参与 L/N/M/B/R/X：采样拍 t 之后录像不足 600 拍的采样不判「没到」；N 只数到「录像结束前 600 拍」为止的已发指令（covered 的局数到最后）。

检测项（每项对应 cards/ 下一张假设卡；时段按本地拍：0–600 / 600–1500 / 1500–3000 / 3000+）：
 L 指令迟到   每条 [HL-TICK] 采样（号, 本地拍 t, 累计发令 cmds）：已发陆攻/出船/撤回数 k = cmds − 截至 t 的捐兵日志条数
              （没有捐兵日志的版本：k = cmds，执行侧也把捐兵算上）。录像里这个号第 k 条执行的拍 T_k。
              只看「上一条采样以来有新指令」的采样：迟到 = max(0, T_k − t)（最新一条指令在采样之后还要多少拍才执行）；k 超过全程执行数 = 永远没到。
              丢失再同步：指令丢了以后，第 k 条执行对应的是更晚发出的指令，直接配会一直偏大。所以每个号维护「已确认丢失数」Λ：
              某个 90 拍窗口里既没发新指令、也没有指令执行（通道空了），就把 Λ 设成当时的积压（已发 − 已执行）；
              之后若积压降到 Λ 以下（原来以为丢了的又到了），Λ 跟着降。配对用第 k − Λ 条执行。
              没有丢失时误差 < 90 拍；连续发令、通道一直不空的波段里 Λ 不更新，这时仍是上界。
              列：采样数、迟到中位/P90/最大、迟到 ≥90 拍的采样占比、永远没到的占比；积压 = k − 截至 t 已执行数（最大值）。
 O 开局基线   [HL-OPENING] 每行 = 一条打中立的陆攻（pct = ceil(spend×1024÷bal) − 1）；录像里同号、目标中立、pct 相同、拍 ≥ 日志拍的第一条：
              延迟 = 执行拍 − 日志拍。列：配上的条数、中位、最大（这是通道在选点刚结束时的基线）。
 M 捐兵延迟   逐条精确：[HL-DISPATCH]/[HL-DONATE] 每行（号, 本地拍 t, pct, 对象）对 录像里同号、同 pct、同对象、拍 ≥ t 的捐兵指令；
              同样的指令重复发时取最晚的那条日志（延迟取下界），每条日志只配一次。延迟 = 执行拍 − t，按执行拍分段。
              列：配上的条数、中位、P90、最大。只量得到「执行了的捐兵」；与 L 互补（L 是上界、M 是下界，M 只在有捐兵的时段有数）。
 N 没落地     每号：最后一条采样的 k − 全程执行数（负数按 0）；全局合计 ÷ 合计已发。
 D 捐兵没执行 捐兵日志条数 − 录像里这些号执行的捐兵条数（只对有捐兵日志的版本）。
 B 同拍批     一个号同一拍执行 ≥3 条陆攻/出船：批数、批内指令数、最大一批、占全部执行的份额。
 R 连续重单   同一个号对同一个非中立目标的陆攻，相邻两条间隔 ≤21 拍连成一串；≥3 条的串数、串内条数。
 F 有兵不动   窗口 = 同一个号相邻两条 [HL-TICK] 之间（90 本地拍）。没出手 = 这个窗口里没有发出任何陆攻/出船（cmds 的增量 − 捐兵日志条数 ≤ 0）。
              列：窗口数、没出手的窗口、其中窗口开头贴着别的玩家（nb≥1）的、其中四面无中立（neut=0 且 nb≥1，「被围」）的；
              另列采样里密度（兵÷地）≥100 的条数、其中没出手的，和「被围」的采样数。全部日志号都算（含不在录像盘里的）。
              这是「留底锁 + 结构锁 + 冷却」的合计上界：只用日志分不出是哪一种（分得出的口径见 tick_attrib.py，要跑影子策略）。
 C 时钟落后   同一盘里各号 [HL-TICK] 按日志行号排序，每条：领先号当时的本地拍 − 本号本地拍（≥0，90 拍一档）。
              列：中位、P90、最大；落后 ≥180 拍的号数。只反映「号与号之间」的差，全体一起慢看不出来。
 X 中途离场   录像里我方号的离场指令（早于终局前 60 拍）；results.csv 的 left 行；离场时客户端落后 = 离场指令拍 − 结果行本地拍。
 P 回合容量   服务器每 7 拍一个回合，指令只在回合的第一拍执行（录像里全部指令的执行拍都是 7 的倍数）。
              统计「一个玩家在一个回合里执行了几条指令」（选点、离场除外）的分布，我方号和其他真人分开。只进 --agg。
 G 中段增长   timeline.csv：编队合计地 630 拍 → 1500 拍的倍数；1500 拍编队份额 ÷ 人数份额（在录像盘的号数 ÷ 真人数；拆盘局不算）。
              自围 = 采样里 nb=0 且 neut=0（四周只有队友和水，= 策略 `tryDonateToTeammate` L4355 的 boxedIn、`idleBoats` L5023 的被围）；列自围的采样数和其后 90 拍没出手的窗口数。
 S 不在这一盘 日志里有轨迹的号数 − 这一盘录像名单里对得上的号数。差 ≥2 个 = 编队被分到了不止一个平行实例（拆盘），或有号没进房；只进 --agg / --classes。
"""
import bisect
import collections
import csv
import json
import os
import re
import statistics
import sys

SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
BUN = os.environ.get('C136_BUNDLES', 'bundles')   # 验证集：C136_BUNDLES=validation_bundles
CMDS = os.environ.get('C136_CMDS', '/tmp/c136-r05/cmds')
a = sys.argv[1:]
opt = lambda k: a[a.index(k) + 1] if k in a else None
ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--tsv', '--json', '--only'))]
detail, dosum, doclasses, doagg = '--detail' in a, '--sum' in a, '--classes' in a, '--agg' in a
if not ids:
    ids = sorted(d for d in os.listdir(f'{SRC}/{BUN}') if os.path.exists(f'{SRC}/{BUN}/{d}/replay.txt'))
if opt('--only'):
    ids = [x for x in ids if x[0] in opt('--only')]
HEAD = json.load(open(f'{CMDS}/headers.json'))
PER = [(0, 600), (600, 1500), (1500, 3000), (3000, 10 ** 9)]
PN = ['0-600', '600-1500', '1500-3000', '3000+']
per = lambda t: next(i for i, (lo, hi) in enumerate(PER) if lo <= max(0, t) < hi)
bare = lambda n: re.sub(r'\[[^\]]*\]', '', n or '').strip().lower()
IDMAP = collections.defaultdict(list)
_idmap = os.environ.get('C136_IDMAP', f'{SRC}/src/tools/identity-map-discovery.csv')   # 验证集没有这份表时：C136_IDMAP=''（B 组轮换名就不换回）
for r in (csv.DictReader(open(_idmap, encoding='utf-8')) if _idmap and os.path.exists(_idmap) else []):
    IDMAP[r['matchId']].append(r)


def q(v, f):
    if not v:
        return None
    s = sorted(v)
    if f == 0.5:
        return statistics.median(s)
    return s[min(len(s) - 1, int(f * len(s)))]


def ver_of(mid):
    if mid[0] == 'B':
        return 'c110'
    if mid[0] == 'G':
        return 'g09'
    n = int(mid[1:])
    return 'Va' if n <= 17 else 'Vb' if n <= 95 else 'Vc'


def scan(mid):
    B = f'{SRC}/{BUN}/{mid}'
    card = json.load(open(f'{B}/card.json'))
    hd = HEAD.get(mid) or {}
    if 'error' in hd or not os.path.exists(f'{CMDS}/{mid}.tsv'):
        return {'matchId': mid, 'error': hd.get('error', '缺命令流')}
    H, names, total = hd['humans'], hd['names'], hd['totalTicks']
    endT = card['outcome'].get('endTick') or 0
    covered = total >= endT - 120
    margin = 0 if covered else 600
    alias = {}
    for r in IDMAP.get(mid, []):
        ch = [x for x in (r.get('nameChain') or '').split('→') if x]
        for n in ch[1:]:
            alias[n] = ch[0]
    al = lambda n: alias.get(n, n)
    # ---- 座位号 ----
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
    # ---- 轨迹 ----
    traj = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{B}/traj.csv', encoding='utf-8')):
        try:
            traj[al(r['bot'])].append((int(r['t']), int(r['cmds']), float(r['dens']), int(r['nb']), int(r['neut']), int(r['terr']), int(r['line'])))
        except (ValueError, KeyError):
            continue
    for b in traj:
        traj[b].sort()
    don = collections.defaultdict(list)
    donrows = collections.defaultdict(list)      # 号 → [(t, pct, 对象)]
    if os.path.exists(f'{B}/events.csv'):
        for r in csv.DictReader(open(f'{B}/events.csv', encoding='utf-8')):
            if r['type'] in ('DISPATCH', 'DONATE'):
                try:
                    don[al(r['bot'])].append(int(r['t']))
                    donrows[al(r['bot'])].append((int(r['t']), int(r['pct']), int(r['target'])))
                except ValueError:
                    pass
    openrows = collections.defaultdict(list)     # 号 → [(t, pct)]
    if os.path.exists(f'{B}/opening.csv'):
        for r in csv.DictReader(open(f'{B}/opening.csv', encoding='utf-8')):
            try:
                sp, bl = int(r['spend']), int(r['bal'])
                if bl > 0:
                    openrows[al(r['bot'])].append((int(r['t']), max(0, min(1023, -(-sp * 1024 // bl) - 1))))
            except (ValueError, KeyError):
                pass
    for b in don:
        don[b].sort()
    don_logged = sum(len(v) for v in don.values()) > 0
    inrep = {b: p for b, p in me.items() if p < H and p < len(names) and bare(names[p]) == b.lower()}
    pid2bot = {p: b for b, p in inrep.items()}
    # ---- 录像命令流 ----
    ab = collections.defaultdict(list)      # 号 → 执行的陆攻/出船/撤回（没有捐兵日志的版本含捐兵）的拍
    dn = collections.defaultdict(list)
    dnx = collections.defaultdict(list)     # 号 → [(拍, pct, 对象)]
    natk = collections.defaultdict(list)    # 号 → [(拍, pct)] 打中立
    atk = collections.defaultdict(list)     # 号 → (拍, 目标)
    leave = {}
    rnd = (collections.Counter(), collections.Counter())      # (我方号, 其他真人)：(玩家, 执行拍) → 这一个回合执行了几条
    for r in csv.DictReader(open(f'{CMDS}/{mid}.tsv', encoding='utf-8'), delimiter='\t'):
        p = int(r['player'])
        b = pid2bot.get(p)
        t, i = int(r['tick']), int(r['id'])
        if t >= 0 and i not in (0, 8, 9) and p < H:
            rnd[0 if b is not None else 1][(p, t)] += 1
        if b is None:
            continue
        if i in (1, 3, 5):
            ab[b].append(t)
            if i == 1:
                atk[b].append((t, int(r['b'])))
                if int(r['b']) >= 512:
                    natk[b].append((t, int(r['a'])))
        elif i == 2:
            dn[b].append(t)
            dnx[b].append((t, int(r['a']), int(r['b'])))
            if not don_logged:
                ab[b].append(t)
        elif i in (8, 9):
            leave.setdefault(b, t)
    for b in ab:
        ab[b].sort()
    # ---- L / N ----
    lag = [[] for _ in PER]
    never = [0] * len(PER)
    nsamp = [0] * len(PER)
    backlog = [[] for _ in PER]
    bots_late = set()
    w300 = collections.defaultdict(lambda: [0, 0])      # 300 拍窗 → [有新指令的采样, 其中迟到 ≥90 拍或没到]
    issued_tot = exec_tot = never_tot = 0
    perbot = {}
    for b in inrep:
        ex = ab.get(b, [])
        dl = don.get(b, [])
        kprev = 0
        klast = 0
        lam = 0            # 已确认丢失数 Λ
        eprev = 0
        first = True
        for (t, c, *_rest) in traj.get(b, []):
            if t > total:
                break
            kraw = c - (bisect.bisect_right(dl, t) if don_logged else 0)
            i = per(t)
            enow = bisect.bisect_right(ex, t)
            bl = kraw - enow
            backlog[i].append(bl)
            if t <= total - margin:
                klast = max(klast, kraw)
            if not first and kraw <= kprev and enow == eprev:
                lam = max(0, bl)
            elif bl < lam:
                lam = max(0, bl)
            first = False
            eprev = enow
            knew = kraw > kprev
            kprev = max(kprev, kraw)
            k = kraw - lam
            if knew and k > 0:
                if k > len(ex):
                    if t <= total - margin:
                        nsamp[i] += 1
                        never[i] += 1
                        w300[t // 300 * 300][0] += 1
                        w300[t // 300 * 300][1] += 1
                else:
                    nsamp[i] += 1
                    d = max(0, ex[k - 1] - t)
                    lag[i].append(d)
                    w300[t // 300 * 300][0] += 1
                    if d >= 90:
                        bots_late.add(b)
                        w300[t // 300 * 300][1] += 1
        nv = max(0, klast - len(ex))
        issued_tot += klast
        exec_tot += len(ex)
        never_tot += nv
        perbot[b] = {'issued': klast, 'executed': len(ex), 'never': nv, 'lastT': traj[b][-1][0] if traj.get(b) else None, 'leave': leave.get(b)}
    # ---- O ----
    obase = []
    for b in inrep:
        ex = sorted(natk.get(b, []))
        used = set()
        for t, pct in sorted(openrows.get(b, [])):
            for j, (te, pe) in enumerate(ex):
                if j not in used and pe == pct and te >= t:
                    used.add(j)
                    obase.append(te - t)
                    break
    # ---- M ----
    mdel = [[] for _ in PER]
    for b in inrep:
        cand = collections.defaultdict(list)
        for t, pct, tg in sorted(donrows.get(b, [])):
            cand[(pct, tg)].append(t)
        for te, pct, tg in sorted(dnx.get(b, [])):
            L = cand.get((pct, tg))
            if not L:
                continue
            j = bisect.bisect_right(L, te) - 1
            if j < 0:
                continue
            mdel[per(te)].append(te - L.pop(j))
    # ---- D ----
    don_issued = sum(len(don.get(b, [])) for b in inrep)
    don_exec = sum(len(dn.get(b, [])) for b in inrep)
    # ---- B ----
    bt = [[0, 0] for _ in PER]
    bmax = 0
    for b, ex in ab.items():
        for t, n in collections.Counter(ex).items():
            if n >= 3:
                bt[per(t)][0] += 1
                bt[per(t)][1] += n
                bmax = max(bmax, n)
    # ---- R ----
    rp = [[0, 0] for _ in PER]
    for b, L in atk.items():
        bytgt = collections.defaultdict(list)
        for t, tg in L:
            if tg < 512:
                bytgt[tg].append(t)
        for tg, ts in bytgt.items():
            ts.sort()
            run = [ts[0]]
            for t in ts[1:] + [None]:
                if t is not None and t - run[-1] <= 21:
                    run.append(t)
                else:
                    if len(run) >= 3:
                        rp[per(run[0])][0] += 1
                        rp[per(run[0])][1] += len(run)
                    run = [t]
    # ---- F ----
    fl = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for _ in PER]     # 采样数, 密度≥100, 其中没出手, 被围, 窗口数, 没出手窗口, 其中 nb≥1, 其中被围, 自围采样, 自围且没出手的窗口
    for b, L in traj.items():
        dl = don.get(b, [])
        for j, (t, c, dens, nb, neut, terr, _ln) in enumerate(L):
            i = per(t)
            fl[i][0] += 1
            boxed = neut == 0 and nb >= 1
            selfbox = neut == 0 and nb == 0      # 四周只有队友和水（策略里的 boxedIn）
            if boxed:
                fl[i][3] += 1
            if selfbox:
                fl[i][8] += 1
            idle = None
            if j + 1 < len(L) and L[j + 1][0] - t <= 180:
                t2, c2 = L[j + 1][0], L[j + 1][1]
                newab = (c2 - c) - ((bisect.bisect_right(dl, t2) - bisect.bisect_right(dl, t)) if don_logged else 0)
                idle = newab <= 0
                fl[i][4] += 1
                if idle:
                    fl[i][5] += 1
                    if nb >= 1:
                        fl[i][6] += 1
                    if boxed:
                        fl[i][7] += 1
                    if selfbox:
                        fl[i][9] += 1
            if dens >= 100:
                fl[i][1] += 1
                if idle:
                    fl[i][2] += 1
    # ---- C ----
    rows = sorted((ln, t, b) for b in inrep for (t, *_x, ln) in traj.get(b, []))
    front = -1
    cl = [[] for _ in PER]
    cl_bots = set()
    for ln, t, b in rows:
        front = max(front, t)
        d = front - t
        cl[per(front)].append(d)
        if d >= 180:
            cl_bots.add(b)
    # ---- X ----
    mid_leave = {b: t for b, t in leave.items() if t < endT - 60}
    left_rows = [b for b, r in res.items() if r.get('event') == 'left']
    lag_at_leave = []
    for b, t in mid_leave.items():
        r = res.get(b)
        if r and r.get('tick'):
            lag_at_leave.append(t - int(r['tick']))
    # ---- G ----
    g630 = g1500 = sh1500 = None
    if os.path.exists(f'{B}/timeline.csv'):
        tl = list(csv.DictReader(open(f'{B}/timeline.csv', encoding='utf-8')))
        def at(T, col):
            best = None
            for r in tl:
                if int(r['t']) <= T:
                    best = r
            return float(best[col]) if best and best.get(col) not in (None, '') else None
        g630, g1500, sh1500 = at(630, 'squadTerr'), at(1500, 'squadTerr'), at(1500, 'squadShare')
    nlog = len(traj)
    split = len(inrep) < nlog
    fair = len(inrep) / H if H else None
    out = {
        'matchId': mid, 'cohort': card['cohort'], 'ver': ver_of(mid), 'result': card['outcome']['resultLabel'], 'endTick': card['outcome'].get('endTick'),
        'humans': H, 'logBots': nlog, 'inReplay': len(inrep), 'split': split, 'donLogged': don_logged, 'replayTicks': total, 'covered': covered,
        'baseWin': card.get('baseWinExpectation'), 'won': card['outcome']['resultLabel'] == 'won',
        'L': [{'period': PN[i], 'samples': nsamp[i], 'p50': q(lag[i], 0.5), 'p90': q(lag[i], 0.9), 'max': max(lag[i]) if lag[i] else None,
               'late90': sum(1 for d in lag[i] if d >= 90) + never[i], 'never': never[i], 'backlogMax': max(backlog[i]) if backlog[i] else None} for i in range(len(PER))],
        'P': [{str(k): v for k, v in sorted(collections.Counter(c.values()).items())} for c in rnd],
        'lateBots': len(bots_late), 'L300': sorted([w, v[0], v[1]] for w, v in w300.items()),
        'O': {'n': len(obase), 'p50': q(obase, 0.5), 'max': max(obase) if obase else None},
        'M': [{'period': PN[i], 'n': len(mdel[i]), 'p50': q(mdel[i], 0.5), 'p90': q(mdel[i], 0.9), 'max': max(mdel[i]) if mdel[i] else None} for i in range(len(PER))],
        'N': {'issued': issued_tot, 'executed': exec_tot, 'never': never_tot},
        'D': {'issued': don_issued, 'executed': don_exec} if don_logged else None,
        'B': [{'period': PN[i], 'batches': bt[i][0], 'cmds': bt[i][1]} for i in range(len(PER))], 'batchMax': bmax,
        'R': [{'period': PN[i], 'runs': rp[i][0], 'cmds': rp[i][1]} for i in range(len(PER))],
        'F': [{'period': PN[i], 'samples': fl[i][0], 'dens100': fl[i][1], 'dens100idle': fl[i][2], 'boxed': fl[i][3],
               'windows': fl[i][4], 'idle': fl[i][5], 'idleNb': fl[i][6], 'idleBoxed': fl[i][7], 'selfBoxed': fl[i][8], 'idleSelf': fl[i][9]} for i in range(len(PER))],
        'C': [{'period': PN[i], 'p50': q(cl[i], 0.5), 'p90': q(cl[i], 0.9), 'max': max(cl[i]) if cl[i] else None} for i in range(len(PER))], 'clockBots': len(cl_bots),
        'X': {'midLeaves': len(mid_leave), 'leftRows': len(left_rows), 'firstLeave': min(mid_leave.values()) if mid_leave else None,
              'lagAtLeave': sorted(lag_at_leave)},
        'G': {'terr630': g630, 'terr1500': g1500, 'x': (g1500 / g630 if g630 and g1500 else None), 'share1500': sh1500,
              'shareVsHead1500': (sh1500 / fair if (sh1500 is not None and fair and not split) else None)},
        'bots': perbot,
    }
    return out


COLS = ['matchId', 'cohort', 'ver', 'result', 'endTick', 'replayTicks', 'covered', 'humans', 'logBots', 'inReplay',
        'L1.samples', 'L1.p50', 'L1.p90', 'L1.max', 'L1.late90', 'L1.never', 'L1.backlogMax',
        'L2.samples', 'L2.p50', 'L2.p90', 'L2.max', 'L2.late90', 'L2.never', 'L2.backlogMax', 'L3.samples', 'L3.p50', 'L3.late90', 'L3.never', 'lateBots',
        'O.n', 'O.p50', 'O.max', 'M1.n', 'M1.p50', 'M1.p90', 'M1.max', 'M2.n', 'M2.p50', 'M2.p90', 'M2.max', 'M3.n', 'M3.p50', 'M3.p90',
        'N.issued', 'N.executed', 'N.never', 'D.issued', 'D.executed',
        'B1.batches', 'B1.cmds', 'B2.batches', 'B2.cmds', 'Ball.batches', 'Ball.cmds', 'batchMax',
        'R1.runs', 'R1.cmds', 'Rall.runs', 'Rall.cmds',
        'F1.windows', 'F1.idle', 'F1.idleNb', 'F1.idleBoxed', 'F1.samples', 'F1.dens100', 'F1.dens100idle', 'F1.boxed',
        'F2.windows', 'F2.idle', 'F2.idleNb', 'F2.idleBoxed', 'F2.samples', 'F2.dens100', 'F2.dens100idle', 'F2.boxed',
        'C1.p50', 'C1.p90', 'C1.max', 'C2.p90', 'C2.max', 'clockBots',
        'X.midLeaves', 'X.leftRows', 'X.firstLeave', 'X.lagAtLeaveMax',
        'G.terr630', 'G.terr1500', 'G.x', 'G.shareVsHead1500',
        'F1.selfBoxed', 'F1.idleSelf', 'F2.selfBoxed', 'F2.idleSelf', 'F3.samples', 'F3.selfBoxed']


def flat(o):
    if 'error' in o:
        return {'matchId': o['matchId'], 'cohort': 'ERR:' + o['error']}
    L, Bx, R, F, C = o['L'], o['B'], o['R'], o['F'], o['C']
    d = {k: o[k] for k in ('matchId', 'cohort', 'ver', 'result', 'endTick', 'replayTicks', 'humans', 'logBots', 'inReplay', 'lateBots', 'batchMax', 'clockBots')}
    d['covered'] = 1 if o['covered'] else 0
    for tag, i in (('L1', 1), ('L2', 2), ('L3', 3)):
        for k in ('samples', 'p50', 'p90', 'max', 'late90', 'never', 'backlogMax'):
            d[f'{tag}.{k}'] = L[i][k]
    d.update({'O.n': o['O']['n'], 'O.p50': o['O']['p50'], 'O.max': o['O']['max']})
    for tag, i in (('M1', 1), ('M2', 2), ('M3', 3)):
        for k in ('n', 'p50', 'p90', 'max'):
            d[f'{tag}.{k}'] = o['M'][i][k]
    d.update({'N.issued': o['N']['issued'], 'N.executed': o['N']['executed'], 'N.never': o['N']['never'],
              'D.issued': o['D']['issued'] if o['D'] else None, 'D.executed': o['D']['executed'] if o['D'] else None,
              'B1.batches': Bx[1]['batches'], 'B1.cmds': Bx[1]['cmds'], 'B2.batches': Bx[2]['batches'], 'B2.cmds': Bx[2]['cmds'],
              'Ball.batches': sum(x['batches'] for x in Bx), 'Ball.cmds': sum(x['cmds'] for x in Bx),
              'R1.runs': R[1]['runs'], 'R1.cmds': R[1]['cmds'], 'Rall.runs': sum(x['runs'] for x in R), 'Rall.cmds': sum(x['cmds'] for x in R)})
    for tag, i in (('F1', 1), ('F2', 2)):
        for k in ('windows', 'idle', 'idleNb', 'idleBoxed', 'samples', 'dens100', 'dens100idle', 'boxed', 'selfBoxed', 'idleSelf'):
            d[f'{tag}.{k}'] = F[i][k]
    d['F3.samples'], d['F3.selfBoxed'] = F[3]['samples'], F[3]['selfBoxed']
    d.update({'C1.p50': C[1]['p50'], 'C1.p90': C[1]['p90'], 'C1.max': C[1]['max'], 'C2.p90': C[2]['p90'], 'C2.max': C[2]['max'],
              'X.midLeaves': o['X']['midLeaves'], 'X.leftRows': o['X']['leftRows'], 'X.firstLeave': o['X']['firstLeave'],
              'X.lagAtLeaveMax': max(o['X']['lagAtLeave']) if o['X']['lagAtLeave'] else None,
              'G.terr630': o['G']['terr630'], 'G.terr1500': o['G']['terr1500'], 'G.x': round(o['G']['x'], 2) if o['G']['x'] else None,
              'G.shareVsHead1500': round(o['G']['shareVsHead1500'], 2) if o['G']['shareVsHead1500'] is not None else None})
    return d


fmt = lambda v: '' if v is None else (f'{v:g}' if isinstance(v, float) else str(v))
ALL = []
for mid in ids:
    try:
        o = scan(mid)
    except Exception as e:  # noqa: BLE001
        o = {'matchId': mid, 'error': f'{type(e).__name__}: {e}'}
    ALL.append(o)
rows = [flat(o) for o in ALL]
if opt('--tsv'):
    with open(opt('--tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(COLS) + '\n')
        for d in rows:
            f.write('\t'.join(fmt(d.get(c)) for c in COLS) + '\n')
    print('→', opt('--tsv'), len(rows), '局')
if opt('--json'):
    json.dump(ALL, open(opt('--json'), 'w'), ensure_ascii=False)
if not opt('--tsv') or detail:
    for o in ALL:
        if 'error' in o:
            print(o['matchId'], '出错：', o['error'])
            continue
        d = flat(o)
        print(f"===== {o['matchId']} {o['cohort']} {o['ver']} {o['result']} 终局 {o['endTick']} 拍（录像 {o['replayTicks']} 拍{'' if o['covered'] else '，没录全'}）｜真人 {o['humans']}｜日志号 {o['logBots']}、在录像盘 {o['inReplay']} =====")
        for x in o['L']:
            if x['samples']:
                print(f"  L {x['period']:>9}: 有新指令的采样 {x['samples']:>3}｜迟到 中位 {fmt(x['p50'])} / P90 {fmt(x['p90'])} / 最大 {fmt(x['max'])}｜≥90 拍或没到 {x['late90']}（没到 {x['never']}）｜积压最大 {x['backlogMax']}")
        print(f"  O 开局基线：配上 {o['O']['n']} 条，延迟中位 {fmt(o['O']['p50'])}、最大 {fmt(o['O']['max'])}｜M 捐兵延迟（逐条配）："
              + ('；'.join(f"{x['period']} {x['n']} 条 中位 {fmt(x['p50'])}/P90 {fmt(x['p90'])}/最大 {fmt(x['max'])}" for x in o['M'] if x['n']) or '没有执行的捐兵'))
        n = o['N']
        print(f"  N 已发 {n['issued']}、录像执行 {n['executed']}、没落地 {n['never']}（{100 * n['never'] / max(1, n['issued']):.0f}%）；迟到 ≥90 拍的号 {o['lateBots']}/{o['inReplay']}"
              + (f"｜D 捐兵日志 {o['D']['issued']}、执行 {o['D']['executed']}" if o['D'] else ''))
        print('  B 同拍批 ' + '；'.join(f"{x['period']} {x['batches']} 批 {x['cmds']} 条" for x in o['B'] if x['batches']) + f"（最大一批 {o['batchMax']}）" if o['batchMax'] else '  B 同拍批 0')
        print('  R 连续重单 ' + ('；'.join(f"{x['period']} {x['runs']} 串 {x['cmds']} 条" for x in o['R'] if x['runs']) or '0'))
        print('  F ' + '；'.join(f"{x['period']} 窗口 {x['windows']}、没出手 {x['idle']}（贴着别人 {x['idleNb']}、被围 {x['idleBoxed']}）｜密度≥100 {x['dens100']}（没出手 {x['dens100idle']}）" for x in o['F'] if x['samples']))
        print('  C 时钟落后（号与号之间） ' + '；'.join(f"{x['period']} 中位 {fmt(x['p50'])}/P90 {fmt(x['p90'])}/最大 {fmt(x['max'])}" for x in o['C'] if x['max'] is not None) + f"；落后 ≥180 拍的号 {o['clockBots']}")
        x = o['X']
        print(f"  X 中途离场指令 {x['midLeaves']}（最早 {fmt(x['firstLeave'])} 拍；离场时客户端落后 {x['lagAtLeave']}）｜results 的 left 行 {x['leftRows']}")
        g = o['G']
        print(f"  G 编队地 630 拍 {fmt(g['terr630'])} → 1500 拍 {fmt(g['terr1500'])}（×{fmt(round(g['x'], 2) if g['x'] else None)}）｜1500 拍份额÷人数份额 {fmt(round(g['shareVsHead1500'], 2) if g['shareVsHead1500'] is not None else None)}")
        if detail:
            for b, v in sorted(o['bots'].items()):
                print(f"      {b:<12} 已发 {v['issued']:>4} 执行 {v['executed']:>4} 没落地 {v['never']:>4}｜最后采样 {v['lastT']}｜离场指令 {fmt(v['leave'])}")
if dosum:
    good = [o for o in ALL if 'error' not in o]
    grp = collections.defaultdict(list)
    for o in good:
        grp[(o['matchId'][0] + ' ' + o['ver'], o['result'])].append(o)
        grp[(o['matchId'][0] + ' 合计', o['result'])].append(o)
    med = lambda v: (statistics.median(v) if v else None)
    f = lambda v, n=0: '–' if v is None else f'{v:.{n}f}'
    print('\n===== 按 组别·版本 × 结局 汇总 =====')
    print('口径：每格先写「满足条件的局数/可判的局数」，再写各局数值的中位。600–1500 拍的列只算录像盖到 1500 拍的局；「没落地」只算录像录全的局。')
    hdr = ['组别·版本', '结局', '局数', '录像到1500拍', '600–1500 迟到采样≥25% 的局', '迟到采样占比中位', '600–1500 有同拍批的局', '批内指令占执行(中位)', '开局基线延迟(中位)',
           '捐兵延迟1500–3000 P90(中位)', '录全的局', '没落地≥10% 的局', '没落地占已发(中位)', '有中途离场的局', '630→1500 地的倍数(中位)', '1500拍份额÷人数份额(中位)',
           '600–1500 没出手窗口占比(中位)', '其中被围(中位)', '1500–3000 没出手窗口占比(中位)', '1500–3000 密度≥100 采样占比(中位)']
    print('\t'.join(hdr))
    for key in sorted(grp):
        G = grp[key]
        G1 = [o for o in G if o['replayTicks'] >= 1500 and o['inReplay'] > 0]
        Gc = [o for o in G if o['covered'] and o['inReplay'] > 0]
        l1s = [100 * o['L'][1]['late90'] / o['L'][1]['samples'] for o in G1 if o['L'][1]['samples']]
        nl = sum(1 for v in l1s if v >= 25)
        b1 = sum(1 for o in G1 if o['B'][1]['batches'] > 0)
        bs = [100 * sum(x['cmds'] for x in o['B']) / o['N']['executed'] for o in G1 if o['N']['executed']]
        ob = [o['O']['p50'] for o in G1 if o['O']['p50'] is not None]
        m2 = [o['M'][2]['p90'] for o in G1 if o['M'][2]['p90'] is not None]
        nv = [100 * o['N']['never'] / o['N']['issued'] for o in Gc if o['N']['issued']]
        nn = sum(1 for v in nv if v >= 10)
        xl = sum(1 for o in G1 if o['X']['midLeaves'] > 0)
        gx = [o['G']['x'] for o in G if o['G']['x']]
        gs = [o['G']['shareVsHead1500'] for o in G if o['G']['shareVsHead1500'] is not None]
        f2 = [100 * o['F'][2]['dens100'] / o['F'][2]['samples'] for o in G if o['F'][2]['samples']]
        i1 = [100 * o['F'][1]['idle'] / o['F'][1]['windows'] for o in G if o['F'][1]['windows']]
        i1b = [100 * o['F'][1]['idleBoxed'] / o['F'][1]['windows'] for o in G if o['F'][1]['windows']]
        i2 = [100 * o['F'][2]['idle'] / o['F'][2]['windows'] for o in G if o['F'][2]['windows']]
        print('\t'.join([key[0], key[1], str(len(G)), str(len(G1)), f'{nl}/{len(l1s)}', f(med(l1s)) + '%', f'{b1}/{len(G1)}', f(med(bs)) + '%', f(med(ob), 1),
                         f(med(m2)), str(len(Gc)), f'{nn}/{len(nv)}', f(med(nv)) + '%', f'{xl}/{len(G1)}', f(med(gx), 2), f(med(gs), 2),
                         f(med(i1)) + '%', f(med(i1b)) + '%', f(med(i2)) + '%', f(med(f2)) + '%']))

if doclasses:
    good = [o for o in ALL if 'error' not in o and o['inReplay'] > 0]
    share = lambda o, i: (o['L'][i]['late90'] / o['L'][i]['samples']) if o['L'][i]['samples'] else None
    TESTS = [
        ('L 600–1500 拍迟到采样 ≥25%', lambda o: o['replayTicks'] >= 1500 and share(o, 1) is not None, lambda o: share(o, 1) >= 0.25),
        ('L 600–1500 拍迟到采样 ≥50%', lambda o: o['replayTicks'] >= 1500 and share(o, 1) is not None, lambda o: share(o, 1) >= 0.50),
        ('L 1500–3000 拍迟到采样 ≥25%', lambda o: o['replayTicks'] >= 3000 and share(o, 2) is not None, lambda o: share(o, 2) >= 0.25),
        ('N 全程没落地 ≥10%', lambda o: o['covered'] and o['N']['issued'] > 0, lambda o: o['N']['never'] / o['N']['issued'] >= 0.10),
        ('N 全程没落地 ≥30%', lambda o: o['covered'] and o['N']['issued'] > 0, lambda o: o['N']['never'] / o['N']['issued'] >= 0.30),
        ('B 600–1500 拍同拍批 ≥10 批', lambda o: o['replayTicks'] >= 1500, lambda o: o['B'][1]['batches'] >= 10),
        ('B 批内指令 ≥ 执行数的 40%', lambda o: o['covered'] and o['N']['executed'] > 0, lambda o: sum(x['cmds'] for x in o['B']) / o['N']['executed'] >= 0.40),
        ('X 3000 拍前有中途离场指令', lambda o: o['replayTicks'] >= 3000, lambda o: o['X']['firstLeave'] is not None and o['X']['firstLeave'] < 3000),
        ('C 有号的时钟比领先号落后 ≥180 拍', lambda o: o['replayTicks'] >= 1500 and o['inReplay'] >= 2, lambda o: o['clockBots'] > 0),
        ('F 600–1500 拍没出手窗口 ≥40%', lambda o: o['F'][1]['windows'] > 0, lambda o: o['F'][1]['idle'] / o['F'][1]['windows'] >= 0.40),
        ('F 600–1500 拍被围且没出手窗口 ≥20%', lambda o: o['F'][1]['windows'] > 0, lambda o: o['F'][1]['idleBoxed'] / o['F'][1]['windows'] >= 0.20),
        ('F 1500–3000 拍自围的采样 ≥30%', lambda o: o['F'][2]['samples'] > 0, lambda o: o['F'][2]['selfBoxed'] / o['F'][2]['samples'] >= 0.30),
        ('S 日志里的号有 ≥2 个不在这一盘录像里', lambda o: o['logBots'] > 0, lambda o: o['logBots'] - o['inReplay'] >= 2),
        ('G 630→1500 拍编队地不到 2 倍', lambda o: o['G']['x'] is not None, lambda o: o['G']['x'] < 2.0),
        ('G 1500 拍份额÷人数份额 < 0.5', lambda o: o['G']['shareVsHead1500'] is not None, lambda o: o['G']['shareVsHead1500'] < 0.5),
    ]
    print('\n===== 各检测项把对局分成两类：局数 / 赢的局数 / 期望赢局数（各局 1÷队数 之和）=====')
    print('只算在录像盘里至少有 1 个我方号的局；赢 = card.json 的 resultLabel=won（B 组的 split_straggler_won 不算赢）。')
    print('组别\t检测项\t可判的局\t有：局数\t有：赢\t有：期望赢\t没有：局数\t没有：赢\t没有：期望赢')
    for grp_name, sel in (('A', lambda o: o['matchId'][0] == 'A'), ('B', lambda o: o['matchId'][0] == 'B'), ('A+B', lambda o: True)):
        G = [o for o in good if sel(o)]
        for name, ok, hit in TESTS:
            J = [o for o in G if ok(o)]
            yes = [o for o in J if hit(o)]
            no = [o for o in J if not hit(o)]
            ew = lambda L: sum(o['baseWin'] or 0 for o in L)
            print('\t'.join([grp_name, name, str(len(J)), str(len(yes)), str(sum(1 for o in yes if o['won'])), f'{ew(yes):.1f}', str(len(no)), str(sum(1 for o in no if o['won'])), f'{ew(no):.1f}']))

if doagg:
    good = [o for o in ALL if 'error' not in o and o['inReplay'] > 0]
    md = statistics.median
    for grp in sorted({o['matchId'][0] for o in good}):
        G = [o for o in good if o['matchId'][0] == grp]
        print(f"\n===== {grp} 组全量合计：{len(G)} 局（录像盘里至少有 1 个我方号；其中录像录全的 {sum(1 for o in G if o['covered'])} 局）=====")
        O = [o['O'] for o in G if o['O']['n'] >= 10]
        if O:
            print(f"O 开局基线（配上 ≥10 条的 {len(O)} 局）：各局中位的中位 {md(x['p50'] for x in O):g} 拍（{min(x['p50'] for x in O):g}–{max(x['p50'] for x in O):g}）；中位 ≥20 拍的 {sum(1 for x in O if x['p50'] >= 20)} 局。")
        for i, pn in enumerate(PN):
            need = [600, 1500, 3000, 4500][i]
            S = [o for o in G if o['replayTicks'] >= need and o['L'][i]['samples']]
            if not S:
                continue
            sh = [o['L'][i]['late90'] / o['L'][i]['samples'] for o in S]
            M = [o['M'][i] for o in G if o['M'][i]['n'] >= 5]
            line = f"L {pn} 拍：可判 {len(S)} 局，迟到采样占比的中位 {100 * md(sh):.0f}%，≥25% 的 {sum(1 for x in sh if x >= 0.25)} 局，≥50% 的 {sum(1 for x in sh if x >= 0.5)} 局"
            if M:
                line += f"｜M 捐兵延迟（执行 ≥5 条的 {len(M)} 局）：P50 的中位 {md(m['p50'] for m in M):g} 拍、P90 的中位 {md(m['p90'] for m in M):g} 拍，P90 ≥90 拍的 {sum(1 for m in M if m['p90'] >= 90)} 局，最大 {max(m['max'] for m in M)} 拍"
            print(line + '。')
        pool = collections.defaultdict(lambda: [0, 0, 0, 0])
        for o in G:
            for w, n, late in o['L300']:
                if w <= 5700 and n:
                    pool[w][0] += n
                    pool[w][1] += late
                    pool[w][2] += 1
                    pool[w][3] += 1 if late / n >= 0.25 else 0
        print('L 每 300 拍（各局采样合并；括号里 = 该窗迟到采样 ≥25% 的局数/有采样的局数）：'
              + '；'.join(f"{w}: {100 * v[1] / v[0]:.0f}%（{v[3]}/{v[2]}）" for w, v in sorted(pool.items())) + '。')
        for who, idx in (('我方号', 0), ('其他真人', 1)):
            cc = collections.Counter()
            for o in G:
                for kk, v in o['P'][idx].items():
                    cc[int(kk)] += v
            tot = sum(cc.values())
            if tot:
                print(f"P 回合容量·{who}：有指令的（玩家×回合）{tot:,} 个；一个回合执行的条数 → 个数：" + '、'.join(f"{kk} 条 {cc[kk]:,}" for kk in sorted(cc))
                      + f"；≥3 条的占 {100 * sum(v for kk, v in cc.items() if kk >= 3) / tot:.2f}%，8–9 条的 {sum(v for kk, v in cc.items() if kk >= 8):,} 个，最大 {max(cc)} 条。")
        C = [o for o in G if o['covered'] and o['N']['issued']]
        if C:
            nv = [o['N']['never'] / o['N']['issued'] for o in C]
            ti, te, tn = sum(o['N']['issued'] for o in C), sum(o['N']['executed'] for o in C), sum(o['N']['never'] for o in C)
            print(f"N 没落地（录全的 {len(C)} 局）：已发陆攻/出船 {ti:,} 条、录像执行 {te:,} 条、没落地 {tn:,} 条（{100 * tn / ti:.0f}%）；各局占比的中位 {100 * md(nv):.0f}%；"
                  f"≥10% 的 {sum(1 for x in nv if x >= .1)} 局、≥30% 的 {sum(1 for x in nv if x >= .3)} 局、≥50% 的 {sum(1 for x in nv if x >= .5)} 局。")
            Dg = [o for o in C if o['D'] and o['D']['issued']]
            if Dg:
                di, de = sum(o['D']['issued'] for o in Dg), sum(o['D']['executed'] for o in Dg)
                print(f"D 捐兵（有捐兵日志且录全的 {len(Dg)} 局）：日志 {di:,} 条、录像执行 {de:,} 条（{100 * de / di:.0f}%）；执行率 <50% 的 {sum(1 for o in Dg if o['D']['executed'] < 0.5 * o['D']['issued'])} 局。")
            allb = sum(sum(x['cmds'] for x in o['B']) for o in C)
            print(f"B 同拍批（录全的局）：批内指令 {allb:,} 条 = 全部执行的 {100 * allb / te:.0f}%。")
        Bx = [o for o in G if o['replayTicks'] >= 1500]
        if Bx:
            sizes = collections.Counter(o['batchMax'] for o in Bx)
            print(f"B 600–1500 拍（录像到 1500 拍的 {len(Bx)} 局）：有同拍批的 {sum(1 for o in Bx if o['B'][1]['batches'])} 局、≥10 批的 {sum(1 for o in Bx if o['B'][1]['batches'] >= 10)} 局；共 {sum(o['B'][1]['batches'] for o in Bx):,} 批 "
                  f"{sum(o['B'][1]['cmds'] for o in Bx):,} 条。各局最大一批的条数：" + '、'.join(f"{kk} 条 {v} 局" for kk, v in sorted(sizes.items())) + '。')
            print(f"R 连续重单（同号同目标、间隔 ≤21 拍、≥3 条一串）600–1500 拍：{sum(o['R'][1]['runs'] for o in Bx):,} 串 {sum(o['R'][1]['cmds'] for o in Bx):,} 条，有的局 {sum(1 for o in Bx if o['R'][1]['runs'])}/{len(Bx)}。")
            Cc = [o for o in Bx if o['inReplay'] >= 2]
            print(f"C 时钟（录像盘里 ≥2 个号的 {len(Cc)} 局）：有号比领先号落后 ≥180 拍的 {sum(1 for o in Cc if o['clockBots'])} 局，这样的号 {sum(o['clockBots'] for o in Cc)} 个。")
        X = [o for o in G if o['replayTicks'] >= 3000]
        if X:
            lags = [x for o in X for x in o['X']['lagAtLeave']]
            print(f"X 中途离场（录像到 3000 拍的 {len(X)} 局）：3000 拍前有离场指令的 {sum(1 for o in X if o['X']['firstLeave'] is not None and o['X']['firstLeave'] < 3000)} 局；全程有的 {sum(1 for o in X if o['X']['midLeaves'])} 局、"
                  f"共 {sum(o['X']['midLeaves'] for o in X)} 个号" + (f"；离场指令拍 − 结果行本地拍 的中位 {md(lags):g} 拍（{len(lags)} 个号有结果行）" if lags else '') + '。')
        fs = [[100 * o['F'][i]['selfBoxed'] / o['F'][i]['samples'] for o in G if o['F'][i]['samples']] for i in (1, 2, 3)]
        fi = [100 * o['F'][2]['idleSelf'] / o['F'][2]['selfBoxed'] for o in G if o['F'][2]['selfBoxed'] >= 10 and o['F'][2]['windows']]
        print(f"F 自围（采样里 nb=0 且 neut=0：四周只有队友和水）：占采样的比例，各局中位 600–1500 拍 {md(fs[0]):.0f}%、1500–3000 拍 {md(fs[1]):.0f}%、3000+ 拍 {md(fs[2]):.0f}%；"
              f"1500–3000 拍 ≥30% 的 {sum(1 for x in fs[1] if x >= 30)}/{len(fs[1])} 局、≥50% 的 {sum(1 for x in fs[1] if x >= 50)} 局"
              + (f"；1500–3000 拍自围采样之后 90 拍没出手的比例，各局中位 {md(fi):.0f}%（自围采样 ≥10 个的 {len(fi)} 局）" if fi else '') + '。')
        Sm = [o for o in G if o['logBots'] > o['inReplay']]
        print(f"S 不在这一盘（日志里有、这一盘录像的名单里没有的号）：有的局 {len(Sm)}/{len(G)}，其中差 1 个号的 {sum(1 for o in Sm if o['logBots'] - o['inReplay'] == 1)} 局、差 ≥2 个号的 {sum(1 for o in Sm if o['logBots'] - o['inReplay'] >= 2)} 局"
              + ('：' + '、'.join(f"{o['matchId']}（{o['inReplay']}/{o['logBots']}）" for o in Sm if o['logBots'] - o['inReplay'] >= 2) if any(o['logBots'] - o['inReplay'] >= 2 for o in Sm) else '') + '。')
        Gx = [o['G']['x'] for o in G if o['G']['x']]
        Gs = [o['G']['shareVsHead1500'] for o in G if o['G']['shareVsHead1500'] is not None]
        if Gx:
            print(f"G 中段增长：630→1500 拍编队地的倍数 中位 {md(Gx):.2f}（{len(Gx)} 局）" + (f"；1500 拍编队份额÷人数份额 中位 {md(Gs):.2f}（{len(Gs)} 局，<1 的 {sum(1 for x in Gs if x < 1)} 局）" if Gs else '') + '。')
