#!/usr/bin/env python3
# latency_ledger.py — 一局的「延迟 / 执行延迟」硬账（hub 0007 第 2 节的口径），一张表看完：
#   §1 出生执行：协调器求解了几轮、最后一次改点在第几轮；我方各号落地了几条出生指令、最后一条在选点阶段第几步、
#       最后落点离「最后一轮求解给它的点」多远 → 落在最后一轮的点上 / 停在旧坐标（哪一轮的）/ 一条都没落地 / 哪一轮的点都不是；
#       两个号落在同一点（≤10 像素）的对数。
#   §2 指令延迟：执行拍 − 决策拍（t_exec − t_intent），按决策拍分 0~599 / 600~1499 / 1500~2999 / 3000+ 四段，给 P50 / P90 / Max。
#       宽配对 = exec_gap.match（同号同类同比例，取离落地拍最近的一条未配对意图 → 延迟是下限）；
#       严配对 = 只取前后 150 拍内比例唯一的陆攻（没有歧义）；
#       成批配对 = 同号同拍落地 ≥3 条的批，整段倒序对到连续的意图上（burst_runs.find_run），取批里最新 / 最老一条的延迟。
#       漏斗：影子策略想发的条数 → 客户端日志的 cmds 计数增量（桥受理的条数）→ 录像里落地的条数（按快照对齐的 630 / 1530 / 3060 分段）。
#       各号客户端落后量（相对最快的队友，日志行序，client_lag.py 的口径）。
#   §3 两笔直接损耗：
#       a) 晚到打错：落地时目标已出局、被引擎改成无主地的陆攻（batch_targets.py 的配对）：条数、当初想出的兵、
#          改打无主地实际出的兵和手续费、没产生进攻的条数；按落地拍分段。
#       b) 重复单与清仓批：关闸串里的重复单（blind_reorders.py 的口径：同号同目标相邻回合连续落地、第一条生效后策略就停手，第 2 条起算重复）；
#          同号同拍落地 ≥3 条陆攻的批：批数、条数、批里合计出兵、第 2 条起的出兵、把余额抽到四成以下的批数。
# 用法：python3 scripts/latency_ledger.py <局号> [--ours id,id,…]
#   先要有 tmp/truth/<局号>/（engine_truth_all.sh）和 tmp/shadow/<局号>/（shadow_all.sh）。结果另写 tmp/latency/<局号>.json。
import sys, os, re, csv, json, math, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from match_digest import Match  # noqa: E402
import exec_gap  # noqa: E402
import client_lag  # noqa: E402
import batch_targets  # noqa: E402
from burst_runs import find_run  # noqa: E402

BUNDLES = '/agent/repos/c136-data/bundles'
BANDS = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3000, '1500~2999'), (3000, 10 ** 9, '3000+')]
SNAP = [(0, 630, '≤630'), (630, 1530, '630~1530'), (1530, 3060, '1530~3060'), (3060, 10 ** 9, '>3060')]


def band(t):
    for lo, hi, lab in BANDS:
        if lo <= t < hi:
            return lab


def wan(v):
    return '%.1f万' % (v / 1e4) if abs(v) >= 1e4 else str(int(v))


def pq(v, p):
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def p3(v):
    return '—' if not v else '%d / %d / %d' % (pq(v, .5), pq(v, .9), max(v))


def spawn_part(mid, M, meta, out):
    W = meta['info']['w']
    solves = []
    log = os.path.join(BUNDLES, mid, 'in_game.log')
    if os.path.exists(log):
        with open(log, encoding='utf8', errors='replace') as f:
            for line in f:
                if '[BACKEND-SPAWN-COORD] Solved' not in line:
                    continue
                pts = {}
                for m in re.finditer(r'(?:\[[^\]]*\]\s*)?([^\s|(\[\]]+)\([A-Z_]+\)->\((\d+),(\d+)\)', line):
                    pts[m.group(1)] = (int(m.group(2)), int(m.group(3)))
                if pts:
                    solves.append(pts)
    last_change = 0
    for i in range(1, len(solves)):
        p0, p1 = solves[i - 1], solves[i]
        if any(b in p0 and math.hypot(p1[b][0] - p0[b][0], p1[b][1] - p0[b][1]) > 20 for b in p1):
            last_change = i + 1
    steps = meta.get('spawnSteps')
    print('## 1 出生执行')
    print('  选点阶段 %s 步；协调器整体求解 %d 轮，点位最后一次变动在第 %s 轮%s' % (
        steps, len(solves), last_change or '1', '（之后 %d 轮点位不变）' % (len(solves) - last_change) if last_change else '（各轮点位都一样）'))
    final = {x['p']: tuple(x['spawn']) for x in meta['players']}
    present = {x['p'] for x in meta['players'] if x['box'][0] <= x['box'][2]}
    cls = collections.Counter()
    rows = []
    for p in M.our_ids:
        nm = M.nm(p)
        seq = [(c['sp'], c['a'] % W, c['a'] // W) for c in M.cmd if c['id'] == 0 and c['p'] == p]
        fx, fy = final.get(p, (None, None))
        d_last = near = None
        if solves and fx is not None and p in present:
            if nm in solves[-1]:
                t = solves[-1][nm]
                d_last = math.hypot(fx - t[0], fy - t[1])
            best = None
            for i, pts in enumerate(solves[:-1]):
                for b, t in pts.items():
                    d = math.hypot(fx - t[0], fy - t[1])
                    if best is None or d <= best[0]:
                        best = (d, i + 1, b)
            near = best
        if not seq:
            kind = '一条出生指令都没落地'
        elif d_last is not None and d_last <= 20:
            kind = '落在最后一轮的点上'
        elif near is not None and near[0] <= 20:
            kind = '停在旧坐标'
        elif d_last is None:
            kind = '协调器日志里没有它的点'
        else:
            kind = '哪一轮的点都不是'
        cls[kind] += 1
        rows.append((nm, len(seq), seq[-1][0] if seq else None, d_last, near, kind))
    same = []
    ids = [p for p in M.our_ids if p in present]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if math.hypot(final[a][0] - final[b][0], final[a][1] - final[b][1]) <= 10:
                same.append((M.nm(a), M.nm(b)))
    lasts = [r[2] for r in rows if r[2] is not None]
    print('  我方 %d 个号：' % len(rows) + '，'.join('%s %d 个' % kv for kv in cls.most_common()) + '；两个号落在同一点（≤10 像素）%d 对%s' % (
        len(same), ('（' + '，'.join('%s=%s' % s for s in same) + '）') if same else ''))
    if lasts:
        print('  各号最后一条出生指令落地的步数：最早 %d、中位 %d、最晚 %d（选点阶段共 %s 步）；各号落地的出生指令条数：%s' % (
            min(lasts), pq(lasts, .5), max(lasts), steps, dict(sorted(collections.Counter(r[1] for r in rows).items()))))
    bad = [r for r in rows if r[5] != '落在最后一轮的点上']
    for nm, n, last, d_last, near, kind in bad:
        print('    %-8s %s：出生指令 %d 条，最后一条在第 %s 步，离最后一轮的点 %s 像素%s' % (
            nm, kind, n, last if last is not None else '—', ('%.0f' % d_last) if d_last is not None else '—',
            ('，离第 %d 轮给 %s 的点 %.0f 像素' % (near[1], near[2], near[0])) if near and kind == '停在旧坐标' else ''))
    out['spawn'] = dict(steps=steps, solves=len(solves), lastChange=last_change, classes=dict(cls), samePoint=len(same),
                        lastStepMin=min(lasts) if lasts else None, lastStepMax=max(lasts) if lasts else None)


def delay_part(mid, M, out):
    intents, cmds, check = exec_gap.load(mid)
    ours = {b['p']: b['bot'] for b in check['bots']}
    cmds = [c for c in cmds if c['p'] in ours]
    pairs, rest, lone = exec_gap.match(intents, cmds)
    byp = collections.defaultdict(list)
    for x in intents:
        byp[x['p']].append(x)
    strict = []
    for x, c in pairs:
        if x['kind'] != 'attack':
            continue
        if any(y is not x and y['kind'] == 'attack' and y['pct'] == x['pct'] and abs(y['t'] - x['t']) <= 150 for y in byp[x['p']]):
            continue
        strict.append((x, c))
    print('## 2 指令延迟（执行拍 − 决策拍；按决策拍分段；P50 / P90 / Max）')
    print('  时段        想发（陆攻/捐款/船）  落地（陆攻/捐款/船）  落地率   宽配对延迟        严配对（条数：延迟）')
    out['delay'] = {}
    for lo, hi, lab in BANDS:
        e = collections.Counter(x['kind'] for x in intents if lo <= x['t'] < hi)
        l = collections.Counter(x['kind'] for x, c in pairs if lo <= x['t'] < hi)
        lag = [c['t'] - x['t'] for x, c in pairs if lo <= x['t'] < hi]
        sl = [c['t'] - x['t'] for x, c in strict if lo <= x['t'] < hi]
        ne = sum(e[k] for k in ('attack', 'donate', 'boat'))
        nl = sum(l[k] for k in ('attack', 'donate', 'boat'))
        print('  %-10s  %4d（%d/%d/%d）      %4d（%d/%d/%d）      %3.0f%%    %-16s  %d 条：%s' % (
            lab, ne, e['attack'], e['donate'], e['boat'], nl, l['attack'], l['donate'], l['boat'], 100.0 * nl / max(1, ne), p3(lag), len(sl), p3(sl)))
        out['delay'][lab] = dict(intents=ne, landed=nl, attackIntents=e['attack'], attackLanded=l['attack'],
                                 p50=pq(lag, .5), p90=pq(lag, .9), max=max(lag) if lag else None,
                                 strictN=len(sl), strictP50=pq(sl, .5), strictP90=pq(sl, .9), strictMax=max(sl) if sl else None)
    print('  各号宽配对延迟（各时段 P50 / P90 / Max）：')
    for p, b in ours.items():
        cells = []
        for lo, hi, lab in BANDS:
            lag = [c['t'] - x['t'] for x, c in pairs if x['p'] == p and lo <= x['t'] < hi]
            cells.append('%s：%s' % (lab, p3(lag)))
        print('    %-8s %s' % (b, '；'.join(cells)))
    # 成批配对
    names, bints, bcmds, life, ku = batch_targets.load(mid)
    newest = collections.defaultdict(list)
    oldest = collections.defaultdict(list)
    nb = collections.Counter()
    nmatch = collections.Counter()
    for (p, T), cs in sorted(bcmds.items()):
        if len(cs) < 3 or p not in names:
            continue
        ints = [(x[0], x[1], x[2]) for x in bints[p]]
        seq = [c[0] for c in cs]
        r = find_run(seq, ints, T, False) or find_run(seq, ints, T, True)
        nb[band(T)] += 1
        if r is None:
            continue
        nmatch[band(T)] += 1
        i0, i1, sk = r
        newest[band(T)].append(T - ints[i1][0])
        oldest[band(T)].append(T - ints[i0][0])
    if nb:
        print('  成批落地（同号同拍 ≥3 条陆攻；按落地拍分段）：' + '；'.join(
            '%s %d 批、对上 %d 批（批里最新一条晚 中位 %s 最大 %s 拍，最老一条晚 中位 %s 最大 %s 拍）' % (
                lab, nb[lab], nmatch[lab], pq(newest[lab], .5), max(newest[lab]) if newest[lab] else None,
                pq(oldest[lab], .5), max(oldest[lab]) if oldest[lab] else None) for _, _, lab in BANDS if nb[lab]))
    out['batchLag'] = {lab: dict(batches=nb[lab], matched=nmatch[lab], newestP50=pq(newest[lab], .5), oldestP50=pq(oldest[lab], .5),
                                 oldestMax=max(oldest[lab]) if oldest[lab] else None) for _, _, lab in BANDS if nb[lab]}
    # 漏斗
    traj = collections.defaultdict(list)
    tp = os.path.join(BUNDLES, mid, 'traj.csv')
    if os.path.exists(tp):
        with open(tp, encoding='utf8') as f:
            for r in csv.DictReader(f):
                try:
                    traj[r['bot']].append((int(r['t']), int(r['cmds'])))
                except ValueError:
                    pass
    print('  漏斗（影子想发 → 桥受理（日志 cmds 计数的增量，不含出生指令）→ 录像落地；影子与录像按服务器拍、日志按各号本地拍，快照对齐分段；影子只数到各号日志的最后一个快照）：')
    out['funnel'] = {}
    lastlog = {p: max([t for t, c in traj.get(b, [])], default=0) for p, b in ours.items()}
    tot = [0, 0, 0]
    perbot = collections.defaultdict(lambda: [0, 0, 0])
    for lo, hi, lab in SNAP:
        want = acc = land = 0
        for p, b in ours.items():
            v = sorted(traj.get(b, []))
            if not v:
                continue
            w = sum(1 for x in byp[p] if lo < x['t'] <= min(hi, lastlog[p]))
            l = sum(1 for c in cmds if c['p'] == p and lo < c['t'] <= hi and c['id'] in (1, 2, 3, 4, 5))
            a0 = max([c for t, c in v if t <= lo], default=0) if lo else 0
            a1 = max([c for t, c in v if t <= hi], default=0)
            want += w; acc += max(0, a1 - a0); land += l
            perbot[b][0] += w; perbot[b][1] += max(0, a1 - a0); perbot[b][2] += l
        tot[0] += want; tot[1] += acc; tot[2] += land
        print('    %-10s 想发 %4d → 受理 %4d → 落地 %4d（受理 ÷ 想发 %3.0f%%，落地 ÷ 受理 %3.0f%%）' % (
            lab, want, acc, land, 100.0 * acc / max(1, want), 100.0 * land / max(1, acc)))
        out['funnel'][lab] = dict(want=want, accepted=acc, landed=land)
    res = {}
    rp = os.path.join(BUNDLES, mid, 'results.csv')
    if os.path.exists(rp):
        with open(rp, encoding='utf8') as f:
            for r in csv.DictReader(f):
                if r['bot'] in ours.values():
                    try:
                        res[r['bot']] = (int(r['sent']), int(r['accepted']))
                    except ValueError:
                        pass
    print('    合计 想发 %d → 受理 %d → 落地 %d（落地 ÷ 受理 %.0f%%）' % (tot[0], tot[1], tot[2], 100.0 * tot[2] / max(1, tot[1])) + (
        '；结算行（results.csv，含出生阶段的指令）里这几个号 发出 %d、被受理 %d 条' % (sum(v[0] for v in res.values()), sum(v[1] for v in res.values())) if res else ''))
    print('    各号 想发 → 受理 → 落地（日志最后一个快照的拍）：' + '；'.join('%s %d → %d → %d（%d）' % (b, v[0], v[1], v[2], lastlog[p]) for p, b in ours.items() for v in [perbot[b]]))
    out['funnel']['total'] = dict(want=tot[0], accepted=tot[1], landed=tot[2], resSent=sum(v[0] for v in res.values()), resAccepted=sum(v[1] for v in res.values()))
    out['funnel']['perBot'] = {b: dict(want=v[0], accepted=v[1], landed=v[2]) for b, v in perbot.items()}
    # 客户端落后
    L = client_lag.lags(client_lag.load(mid))
    print('  各号客户端落后（相对最快的队友，拍；中位 / 最大）：')
    out['clientLag'] = {}
    for b in ours.values():
        v = L.get(b, [])
        cells = []
        for lo, hi, lab in BANDS:
            x = [lag for t, lag, _ in v if lo <= t < hi]
            cells.append('%s：%s' % (lab, ('%d / %d' % (pq(x, .5), max(x))) if x else '—'))
        print('    %-8s %s' % (b, '；'.join(cells)))
        allx = [lag for t, lag, _ in v]
        out['clientLag'][b] = dict(max=max(allx) if allx else None, n180=sum(1 for x in allx if x >= 180))
    return intents, cmds, ours, bints, bcmds, life, ku, names


def loss_part(mid, M, intents, cmds, ours, bints, bcmds, life, ku, names, out):
    NEUTRAL = 512
    print('## 3 两笔直接损耗')
    # a) 晚到打错：照 batch_targets.py 的配对
    S = collections.defaultdict(collections.Counter)
    for p in sorted(names):
        ints = bints[p]
        used = set()
        for T in sorted(t for (q, t) in bcmds if q == p):
            cs = bcmds[(p, T)]
            pr = []
            if len(cs) >= 3:
                seq = [c[0] for c in cs]
                r = find_run(seq, [(x[0], x[1], x[2]) for x in ints], T, False) or find_run(seq, [(x[0], x[1], x[2]) for x in ints], T, True)
                if r is None:
                    pr = [(c, None) for c in cs]
                else:
                    i0, i1, sk = r
                    idx = [i for i in range(i1, i0 - 1, -1) if i != sk]
                    for c, i in zip(cs, idx):
                        used.add(i)
                        pr.append((c, ints[i]))
            else:
                for c in cs:
                    best = None
                    for i in range(len(ints) - 1, -1, -1):
                        if ints[i][0] > T or i in used:
                            continue
                        if T - ints[i][0] > 400:
                            break
                        if ints[i][1] == c[0]:
                            best = i
                            break
                    if best is None:
                        pr.append((c, None))
                    else:
                        used.add(best)
                        pr.append((c, ints[best]))
            for c, it in pr:
                a, b, bal0, bal1, sent = c
                fee = max(0, bal0 - bal1 - sent)
                s = S[band(T)]
                s['落地'] += 1
                if it is None:
                    s['配不上'] += 1
                    continue
                if it[2] < NEUTRAL:
                    s['瞄AI或真人'] += 1
                    s['瞄AI或真人 想出的兵'] += it[3]
                if b == it[2]:
                    if it[2] < NEUTRAL:
                        s['打到原目标'] += 1
                        s['打到原目标 兵'] += sent
                elif b >= NEUTRAL and it[2] < NEUTRAL:
                    s['改成无主地'] += 1
                    s['改成无主地 想出的兵'] += it[3]
                    s['改成无主地 瞄真人' if it[2] < ku else '改成无主地 瞄AI'] += 1
                    s['改成无主地 延迟'] += T - it[0]
                    if sent > 0:
                        s['改打无主地'] += 1
                        s['改打无主地 兵'] += sent
                        s['改打无主地 手续费'] += fee
                    else:
                        s['没产生进攻'] += 1
                        s['没产生进攻 想出的兵'] += it[3]
    print('  a) 晚到打错（落地时目标已出局、被引擎改成无主地；按落地拍分段）：')
    out['lateWrong'] = {}
    for lo, hi, lab in BANDS:
        s = S[lab]
        if not s['落地']:
            continue
        n_ai = sum(1 for x in intents if x['kind'] == 'attack' and lo <= x['t'] < hi and x['target'] < NEUTRAL)
        conv = s['改成无主地']
        print('    %-10s 落地陆攻 %d 条（配不上任何意图的 %d 条；配得上「瞄 AI/真人」意图的 %d 条，当初想出 %s 兵）；其中改成无主地 %d 条（瞄 AI %d、瞄真人 %d；平均晚 %s 拍），当初想出 %s 兵（占 %.0f%%）→ 改打无主地 %d 条 实出 %s 兵、手续费 %s；没产生进攻 %d 条（想出 %s 兵，兵留在家里）；本段影子「瞄 AI/真人」的意图 %d 条 → 打到原目标 %d 条（%.0f%%）%s 兵' % (
            lab, s['落地'], s['配不上'], s['瞄AI或真人'], wan(s['瞄AI或真人 想出的兵']), conv, s['改成无主地 瞄AI'], s['改成无主地 瞄真人'],
            ('%.0f' % (s['改成无主地 延迟'] / conv)) if conv else '—', wan(s['改成无主地 想出的兵']),
            100.0 * s['改成无主地 想出的兵'] / max(1, s['瞄AI或真人 想出的兵']),
            s['改打无主地'], wan(s['改打无主地 兵']), wan(s['改打无主地 手续费']), s['没产生进攻'], wan(s['没产生进攻 想出的兵']),
            n_ai, s['打到原目标'], 100.0 * s['打到原目标'] / max(1, n_ai), wan(s['打到原目标 兵'])))
        out['lateWrong'][lab] = dict(landed=s['落地'], aimed=s['瞄AI或真人'], aimedTroops=s['瞄AI或真人 想出的兵'], retargeted=conv, wantTroops=s['改成无主地 想出的兵'],
                                     toNeutralN=s['改打无主地'], toNeutralTroops=s['改打无主地 兵'], toNeutralFee=s['改打无主地 手续费'],
                                     noAttackN=s['没产生进攻'], noAttackTroops=s['没产生进攻 想出的兵'],
                                     aimedIntents=n_ai, onTarget=s['打到原目标'], onTargetTroops=s['打到原目标 兵'])
    # b) 重复单（关闸串）与清仓批
    rows = []
    for i, c in enumerate(cmds):
        if c['id'] != 1 or c['b'] == NEUTRAL:
            continue
        s = c['sub'] or ''
        if not s.startswith('atk:'):
            continue
        rows.append(dict(i=i, t=c['t'], p=c['p'], q=c['b'], bal0=c['bal0'], v=int(s.split(':')[2])))
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['p'], r['q'])].append(r)
    chains = []
    for key, v in by.items():
        v.sort(key=lambda r: (r['t'], r['i']))
        cur = None
        for r in v:
            if cur is not None and r['t'] - cur['last'] <= 7:
                cur['rows'].append(r); cur['last'] = r['t']
            else:
                cur = dict(p=key[0], q=key[1], rows=[r], last=r['t'])
                chains.append(cur)
    shadow = collections.defaultdict(list)
    for x in intents:
        if x['kind'] == 'attack':
            shadow[(x['p'], x['target'])].append(x['t'])
    dup = collections.defaultdict(lambda: [0, 0])
    tot_v = collections.Counter()
    for r in rows:
        tot_v[band(r['t'])] += r['v']
    for c in chains:
        if len(c['rows']) < 2:
            continue
        t0 = c['rows'][0]['t']
        if any(t0 < t <= t0 + 10 for t in shadow.get((c['p'], c['q']), [])):
            continue
        for r in c['rows'][1:]:
            d = dup[band(r['t'])]
            d[0] += 1; d[1] += r['v']
    print('  b) 重复单（关闸串里第 2 条起；按落地拍分段；括号里是占本段打人/AI 出征兵的比例）：' + '；'.join(
        '%s %d 条 %s 兵（%.0f%%）' % (lab, dup[lab][0], wan(dup[lab][1]), 100.0 * dup[lab][1] / max(1, tot_v[lab])) for _, _, lab in BANDS if dup[lab][0]) + (
        '；全局 %d 条 %s 兵（%.0f%%）' % (sum(d[0] for d in dup.values()), wan(sum(d[1] for d in dup.values())),
                                    100.0 * sum(d[1] for d in dup.values()) / max(1, sum(tot_v.values())))))
    out['repeat'] = {lab: dict(n=dup[lab][0], troops=dup[lab][1], sharePct=round(100.0 * dup[lab][1] / max(1, tot_v[lab]), 1)) for _, _, lab in BANDS if dup[lab][0]}
    out['repeat']['total'] = dict(n=sum(d[0] for d in dup.values()), troops=sum(d[1] for d in dup.values()),
                                  sharePct=round(100.0 * sum(d[1] for d in dup.values()) / max(1, sum(tot_v.values())), 1))
    B = collections.defaultdict(lambda: collections.Counter())
    sizes = collections.Counter()
    for (p, T), cs in bcmds.items():
        if len(cs) < 3 or p not in names:
            continue
        s = B[band(T)]
        sent = [c[4] for c in cs]
        bal0 = max(c[2] for c in cs)
        bal1 = min(c[3] for c in cs)
        s['批'] += 1; s['条'] += len(cs); s['兵'] += sum(sent)
        first = next((v for v in sent if v > 0), 0)
        s['第2条起的兵'] += sum(sent) - first
        s['手续费'] += max(0, bal0 - bal1 - sum(sent))
        if bal0 > 0 and bal1 < 0.4 * bal0:
            s['抽到四成以下'] += 1
        if sum(sent) == 0:
            s['一兵没出'] += 1
        sizes[len(cs)] += 1
    print('     清仓批（同号同拍落地 ≥3 条陆攻，含打无主地的；按落地拍分段）：' + ('；'.join(
        '%s %d 批 %d 条，合计出 %s 兵（第 2 条起 %s 兵），手续费 %s，把余额抽到四成以下的 %d 批，一兵没出的 %d 批' % (
            lab, B[lab]['批'], B[lab]['条'], wan(B[lab]['兵']), wan(B[lab]['第2条起的兵']), wan(B[lab]['手续费']), B[lab]['抽到四成以下'], B[lab]['一兵没出'])
        for _, _, lab in BANDS if B[lab]['批']) or '没有') + '；批的大小（条数: 批数）%s' % dict(sorted(sizes.items())))
    out['drain'] = {lab: dict(B[lab]) for _, _, lab in BANDS if B[lab]['批']}
    out['drain']['sizes'] = dict(sizes)


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    out = dict(match=mid)
    print('# %s 延迟账（录像里的我方号 %d 个；决策每 5 拍一次，指令只在 7 的倍数拍执行）' % (mid, len(M.our_ids)))
    spawn_part(mid, M, meta, out)
    args = delay_part(mid, M, out)
    loss_part(mid, M, *args, out)
    d = os.path.join(ROOT, 'tmp', 'latency')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
