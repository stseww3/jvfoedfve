#!/usr/bin/env python3
"""m6_all_replay.py — 全量机械计数（所有带录像的对局包；只用对局包里的日志/CSV + 展开好的录像指令流，不模拟）。

先决条件：每个带录像的包先跑一遍 `bash ../../tools/run-heavy.sh node scripts/replay_cmds.mjs <局号>`（只解码），
          产物 out/<局号>/replay_cmds.csv、replay_meta.json。成批跑见 scripts/steps/m6-replays.txt + scripts/batch_loop.sh。

每局一行，数下面几类（括号里是对应的模式编号）：
  覆盖       录像最后一拍 lastTick（录像由本队一个页面记录，到它退出为止）对 card.endTick。
  漏斗(IO01/IO02)  页面自己数的受理条数（traj.csv 的 cmds，取本地拍 ≤ lastTick 的最后一个快照）减去日志里的捐兵行数（events.csv 的 DISPATCH/DONATE）
             = 页面放行的陆攻+船；录像里本队席位落地的陆攻+船；二者之比 ndRatio。按本地拍/落地拍 600、1500、3000 另给累计值。
             捐兵单列：日志里的捐兵行数 → 录像里落地的捐兵条数（donRatio；不落地 = 引擎拒收或没到服务器）。
  成批落地(IO02)   同一个席位同一拍落地 ≥3 条陆攻的批次数、条数；单席位单拍最多落地几条（所有指令）。其他真人的同一指标作对照。
  重复下令(IO04)   同一席位对同一目标、同一 pct 的陆攻，在上一条落地后 21 拍内又落地一条的条数。
  离场(EG02)       本队席位在 1500 / 2500 拍前有 leave 指令的个数；其他真人席位的同一比例作对照。
  给离场席位捐兵(DN14)  本队席位落地的捐兵里，对象在此之前已有 leave 指令的条数。
  出生(SP03/SP04)  每个本队席位落地的出生指令条数；0 条的席位数（引擎随机安放）；收场时两个号的最后一条出生指令是同一个像素的对数、相距 < 10 像素的对数；
             c116：协调器第一份落点表（[BACKEND-SPAWN-COORD] 第一行）的各点在录像里有没有同像素的出生指令（v1 落地几条）、求解几次、几份不同的表。
用法：python3 scripts/m6_all_replay.py [局号 ...] [--csv] [--quiet]
      不给局号 = 全部有 out/<局号>/replay_cmds.csv 的包；--csv 写 out/_all/replay_facts.csv；末尾按编队汇总。
说明：
  * 席位号取日志里的 `[号] [HL-GAME-INIT] … me=N` / `[HL-SPAWN…] me=N`。一个包里不是同一场对局的标 multi=1，不进汇总：
    先后两场（一个名字先后对上两个席位、开局行参数不止一种、某个号的快照拍号倒退、或 card.seededPlayers 和录像头的人数对不上），
    或平行两场（编队的页面分进了同时开局的两间房：日志里的席位号在录像名单里是别人，或各页面的开局时刻差 3 秒以上；
    见 m6_match_split.py，表在 out/_all/match_split.csv）。
  * 同一场对局有两个包时（A057/B038、A058/B039、A062/B043…：地图、种子相同，开局时间差 < 5 分钟，录像里的席位名单相同），用录像更长的那一份。
  * 延迟让落地跨时段，所以累计比值是“到这一拍为止”，不是严格的同一批指令；只当漏斗的粗筛，逐条的延迟要用影子策略（lag_periods.py）。
"""
import csv, gzip, json, os, re, statistics, struct, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m6_match_split  # noqa: E402

OUT = os.path.join(HERE, '..', 'out')
DATA = '/agent/repos/c136-data/bundles'
MAPS = '/agent/repos/c136-data/src/sim/maps'
PAT_ME = re.compile(r'^\d+\t\[([^\]]+)\] \[HL-(?:GAME-INIT|SPAWN|SPAWN-BACKEND)\].*?\bme=(\d+)')
PAT_SOLVE = re.compile(r'^(\d+)\t.*\[BACKEND-SPAWN-COORD\] Solved (\d+) bots .*?minSep=(\d+)px.*?\): (.*)$')
CUTS = (600, 1500, 3000)
WIN = 14   # 快照拍之后再等几拍算“已落地”


def map_width(map_id, seed):
    for key in (f'{map_id}_{seed}', f'{map_id}_0'):
        f = os.path.join(MAPS, key + '.bin.gz')
        if os.path.exists(f):
            b = gzip.open(f).read(8)
            if b[:4] == b'TMAP':
                return struct.unpack('<HH', b[4:8])[0]
    return None


def load_replay(mid):
    f = os.path.join(OUT, mid, 'replay_cmds.csv')
    if not os.path.exists(f):
        return None
    meta = json.load(open(os.path.join(OUT, mid, 'replay_meta.json')))
    rows = list(csv.DictReader(open(f, encoding='utf8')))
    return meta, rows


PAT_INIT = re.compile(r'\[HL-GAME-INIT\] mode=(\d+) map=(\d+) mapSeed=(\d+) seeded=(\d+)')


def read_log(mid):
    seats, multi, solves = {}, False, []
    games = set()
    for line in open(os.path.join(DATA, mid, 'in_game.log'), errors='replace'):
        g = PAT_INIT.search(line)
        if g:
            games.add(g.groups())
            if len(games) > 1:
                multi = True   # 同一个包里出现两种开局参数 = 混了两场（A094）
        m = PAT_ME.match(line)
        if m:
            b, p = m.group(1), int(m.group(2))
            if b in seats and seats[b] != p:
                multi = True
            seats.setdefault(b, p)
            continue
        m = PAT_SOLVE.match(line)
        if m:
            solves.append({b: (int(x), int(y)) for b, x, y in re.findall(r'\[\w+\] (\w+)\(\w+\)->\((\d+),(\d+)\)', m.group(4))})
    return seats, multi, solves


def same_match(mid, cards):
    """同一场对局的另一个包（另一支编队的视角）：地图、种子相同，开局时间差 < 300 秒。"""
    card = cards[mid]
    return [o for o, c in cards.items() if o != mid and c['mapId'] == card['mapId'] and c['mapSeed'] == card['mapSeed']
            and abs(c['timestampMs'] - card['timestampMs']) < 300000]


def pick_replay(mid, cards, replays):
    """这个包用哪一份录像：自己的；同一场的另一个包的录像名单相同且更长时用那一份；自己没有录像时用同场的。都没有返回 None。"""
    best = mid
    for o in same_match(mid, cards):
        if o not in replays:
            continue
        if mid not in replays or (replays[o][0]['names'] == replays[mid][0]['names'] and replays[o][0]['lastTick'] > replays[best][0]['lastTick']):
            best = o
    return best if best in replays else None


def load_all():
    cards = {m: json.load(open(os.path.join(DATA, m, 'card.json'))) for m in sorted(os.listdir(DATA))}
    replays = {}
    for m in cards:
        x = load_replay(m)
        if x:
            replays[m] = x
    return cards, replays


def one(mid, cards, replays):
    card = cards[mid]
    best = pick_replay(mid, cards, replays)
    if best is None:
        return None
    meta, rows = replays[best]
    # B039/B043 的 out/ 目录里放的就是同局 A 包的录像（replayOf）
    H, L = meta['humans'], meta['lastTick']
    seats, multi, solves = read_log(mid)
    if card.get('seededPlayers') != H:
        multi = True   # 日志开局行的人数和录像头对不上：录像不是日志里这一场（A094 的录像是第二场）
    if mid in SPLIT:
        multi = True   # 平行两场或先后两场（m6_match_split.py）
    S = set(seats.values())
    r = {'mid': mid, 'cohort': card['cohort'], 'result': card['outcome']['resultLabel'], 'won': int(bool(card['outcome']['primaryTeamWon'])),
         'replay': meta.get('replayOf') or best, 'endTick': card['outcome']['endTick'], 'lastTick': L, 'humans': H, 'squad': len(S), 'multi': int(multi)}
    r['teams'] = 0 if card.get('mode') in (7, 8) else card.get('nominalTeams')   # 引擎的队数（含没有真人的队）；有真人的队数见 joined.csv 的 teams

    by_seat = defaultdict(list)
    leave = {}
    for c in rows:
        p = int(c['player'])
        t = int(c['tick'])
        if c['kind'] == 'leave':
            leave.setdefault(p, t)
        by_seat[p].append((t, c['kind'], int(c['dX']), int(c['dZ'])))

    # —— 漏斗 ——
    traj = defaultdict(list)   # seat -> [(t, cmds)]
    unmapped = 0
    for x in csv.DictReader(open(os.path.join(DATA, mid, 'traj.csv'))):
        if x['bot'] not in seats:
            unmapped += 1
            continue
        try:
            traj[seats[x['bot']]].append((int(x['t']), int(x['cmds'])))
        except ValueError:
            pass
    don_log = defaultdict(list)  # seat -> [t]
    ev_path = os.path.join(DATA, mid, 'events.csv')
    if os.path.exists(ev_path):
        for e in csv.DictReader(open(ev_path)):
            if e['type'] in ('DISPATCH', 'DONATE') and e['bot'] in seats:
                try:
                    don_log[seats[e['bot']]].append(int(e['t']))
                except ValueError:
                    pass

    # 一个号的快照拍号倒退 = 这个包里混了两场（A094）
    for p, snaps in traj.items():
        if any(snaps[i][0] < snaps[i - 1][0] for i in range(1, len(snaps))):
            multi = True
    r['multi'] = int(multi)
    r['split'] = SPLIT.get(mid, '')

    def funnel(T):
        """逐席位对齐：取该席位本地拍 ≤ T（且 ≤ lastTick）的最后一个快照 ts，页面放行的陆攻+船 = cmds(ts) − 捐兵行数(≤ ts)；
        录像里该席位落地拍 < ts + WIN 的陆攻+船（WIN = 14：正常延迟中位 11–14 拍，页面不落后的局这个比值 ≈ 1）。
        页面落后时本地拍 ts 对应的服务器拍更晚，所以分段比值低 = “晚到”和“没到”合在一起；全程比值（ndRatio）低 = 真没到。返回（放行合计，落地合计）。"""
        acc = land = 0
        for p, snaps in traj.items():
            ok = [(t, c) for t, c in snaps if t <= T and t <= L]
            if not ok:
                continue
            ts_, c = max(ok)
            acc += c - sum(1 for t in don_log.get(p, []) if t <= ts_)
            land += sum(1 for t, k, _, _ in by_seat.get(p, []) if k in ('attack', 'boat') and 0 <= t < ts_ + WIN)
        return acc, land

    INF = 10 ** 9
    r['logND'], r['landND'] = funnel(INF)
    r['ndRatio'] = round(r['landND'] / r['logND'], 3) if r['logND'] > 0 else None
    cum = {}
    for T in CUTS:
        cum[T] = funnel(T)
        a, b = cum[T]
        r[f'nd{T}'] = round(b / a, 3) if a > 0 and L >= T + 30 else None
    # 分段：本地拍 (600, 1500] 放行的，对落地拍 [600+WIN, 1500+WIN) 的
    a = cum[1500][0] - cum[600][0]
    b = cum[1500][1] - cum[600][1]
    r['nd600_1500'] = round(b / a, 3) if a > 0 and L >= 1530 else None
    r['logDon'] = sum(1 for p in S for t in don_log.get(p, []) if t <= L)
    r['landDon'] = sum(1 for p in S for t, k, _, _ in by_seat.get(p, []) if k == 'donate')
    r['donRatio'] = round(r['landDon'] / r['logDon'], 3) if r['logDon'] > 0 else None
    r['unmappedTrajRows'] = unmapped

    # —— 成批落地 / 重复 ——
    def burst_stats(seat_set):
        batches = rows_n = 0
        mx = 0
        rep = 0
        for p in seat_set:
            per = defaultdict(int)
            per_all = defaultdict(int)
            last = {}
            for t, k, dx, dz in sorted(by_seat.get(p, [])):
                if t < 0:
                    continue
                per_all[t] += 1
                if k == 'attack':
                    per[t] += 1
                    key = (dz, dx)
                    if key in last and 0 < t - last[key] <= 21:
                        rep += 1
                    last[key] = t
            for t, n in per.items():
                if n >= 3:
                    batches += 1
                    rows_n += n
            if per_all:
                mx = max(mx, max(per_all.values()))
        return batches, rows_n, mx, rep

    r['batches'], r['batchRows'], r['maxPerTick'], r['repeats'] = burst_stats(S)
    others = set(range(H)) - S
    ob, orows, omx, orep = burst_stats(others)
    r['oBatches'], r['oBatchRows'], r['oMaxPerTick'] = ob, orows, omx
    r['atkLanded'] = sum(1 for p in S for t, k, _, _ in by_seat.get(p, []) if k == 'attack' and t >= 0)
    r['oAtkLanded'] = sum(1 for p in others for t, k, _, _ in by_seat.get(p, []) if k == 'attack' and t >= 0)

    # —— 离场 ——
    for T in (1500, 2500):
        if L >= T:
            r[f'left{T}'] = sum(1 for p in S if p in leave and leave[p] < T)
            r[f'oLeft{T}'] = sum(1 for p in others if p in leave and leave[p] < T)
        else:
            r[f'left{T}'] = r[f'oLeft{T}'] = None
    r['others'] = len(others)

    # —— 给离场席位捐兵 ——
    r['donToLeft'] = sum(1 for p in S for t, k, dx, dz in by_seat.get(p, []) if k == 'donate' and dz in leave and leave[dz] < t)

    # —— 出生 ——
    # 只按拍排（稳定排序）：同一步里的多条出生指令保持录像里的先后，最后一条生效
    spawn = {p: [(t, dx) for t, k, dx, dz in sorted(by_seat.get(p, []), key=lambda c: c[0]) if k == 'spawn'] for p in S}
    r['noSpawn'] = sum(1 for p in S if not spawn[p])
    r['spawnCmdsMed'] = statistics.median(len(v) for v in spawn.values()) if spawn else None
    W = map_width(card['mapId'], card['mapSeed'])
    lastpx = {p: v[-1][1] for p, v in spawn.items() if v}
    ps = sorted(lastpx)
    r['samePixelPairs'] = sum(1 for i, x in enumerate(ps) for y in ps[i + 1:] if lastpx[x] == lastpx[y])
    r['near10Pairs'] = None
    if W:
        xy = {p: (px % W, px // W) for p, px in lastpx.items()}
        r['near10Pairs'] = sum(1 for i, x in enumerate(ps) for y in ps[i + 1:] if (xy[x][0] - xy[y][0]) ** 2 + (xy[x][1] - xy[y][1]) ** 2 < 100)
    r['solves'] = len(solves)
    r['layouts'] = len({tuple(sorted(s.items())) for s in solves})
    r['v1Bots'] = r['v1Landed'] = r['onLast'] = None
    if solves and W:
        v1 = {b: q for b, q in solves[0].items() if b in seats}
        r['v1Bots'] = len(v1)
        r['v1Landed'] = sum(1 for b, (x, y) in v1.items() if any(px == y * W + x for _, px in spawn.get(seats[b], [])))
        vl = {b: q for b, q in solves[-1].items() if b in seats}
        r['onLast'] = sum(1 for b, (x, y) in vl.items() if lastpx.get(seats[b]) == y * W + x)
    return r


SPLIT = {}


def main():
    argv = sys.argv[1:]
    SPLIT.update(m6_match_split.load_split())
    cards, replays = load_all()
    mids = [x for x in argv if not x.startswith('--')] or sorted(cards)
    rows = []
    for m in mids:
        r = one(m, cards, replays)
        if r:
            rows.append(r)
    f = lambda x: '-' if x is None else (f'{x:.2f}' if isinstance(x, float) else str(x))
    if '--quiet' not in argv:
        print('局 | 编队 结果 | 录像/终局拍 | 陆攻+船 放行→落地（比值；到 600/1500/3000 拍的累计比值；600–1500 拍这一段）| 捐兵 日志→落地 | 批次/条数/单拍最多（其他真人批次/最多）| 重复 | 1500/2500 拍前离场 本队（其他真人）| 捐给已离场 | 出生：0 条的号/同像素对/v1 落地')
        for r in rows:
            print(f"{r['mid']} | {r['cohort']} {r['result']}{' multi' if r['multi'] else ''} | {r['lastTick']}/{r['endTick']}（{r['replay']}）| {r['logND']}→{r['landND']}（{f(r['ndRatio'])}；{f(r['nd600'])}/{f(r['nd1500'])}/{f(r['nd3000'])}；{f(r['nd600_1500'])}）| "
                  f"{r['logDon']}→{r['landDon']} | {r['batches']}/{r['batchRows']}/{r['maxPerTick']}（{r['oBatches']}/{r['oMaxPerTick']}）| {r['repeats']} | "
                  f"{f(r['left1500'])}/{f(r['left2500'])} of {r['squad']}（{f(r['oLeft1500'])}/{f(r['oLeft2500'])} of {r['others']}）| {r['donToLeft']} | {r['noSpawn']}/{r['samePixelPairs']}/{f(r['v1Landed'])}:{f(r['v1Bots'])}")
    if '--csv' in argv:
        od = os.path.join(OUT, '_all')
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'replay_facts.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/replay_facts.csv（{len(rows)} 局）')
    # —— 汇总 ——
    ok = [r for r in rows if not r['multi']]
    print(f"# 汇总：{len(rows)} 局有录像，其中 {len(rows) - len(ok)} 个包不是同一场对局（不计入下面）：{' '.join(r['mid'] for r in rows if r['multi'])}")
    for co in sorted({r['cohort'] for r in ok}):
        L = [r for r in ok if r['cohort'] == co]
        med = lambda k: (lambda v: f'{statistics.median(v):.2f}' if v else '-')([r[k] for r in L if r[k] is not None])
        # 落地的比页面计数还多的局（A018：日志的 cmds 计数不全）比值不可用，不进分母；和 m6_all_outcomes.py 同一条规则
        full = [r for r in L if r['lastTick'] >= 1530 and r['nd600_1500'] is not None and r['nd600_1500'] <= 1.15]
        low = [r for r in full if r['nd600_1500'] < 0.7]
        print(f"#   {co}：{len(L)} 局；陆攻+船 落地/放行 全程中位 {med('ndRatio')}，到 600 拍 {med('nd600')}，到 1500 拍 {med('nd1500')}，到 3000 拍 {med('nd3000')}；"
              f"600–1500 拍这一段的比值 < 0.7 的 {len(low)}/{len(full)} 局（其中主队赢 {sum(r['won'] for r in low)} 局；≥ 0.7 的 {len(full) - len(low)} 局里赢 {sum(r['won'] for r in full if r not in low)} 局）")
        print(f"#      捐兵 日志 {sum(r['logDon'] for r in L)} 行 → 录像落地 {sum(r['landDon'] for r in L)} 条；给已离场席位的 {sum(r['donToLeft'] for r in L)} 条（{sum(1 for r in L if r['donToLeft'])} 局）")
        print(f"#      同拍 ≥3 条陆攻的批次：本队 {sum(r['batches'] for r in L)} 个 {sum(r['batchRows'] for r in L)} 条（占本队落地陆攻 {100 * sum(r['batchRows'] for r in L) / max(1, sum(r['atkLanded'] for r in L)):.1f}%），有批次的 {sum(1 for r in L if r['batches'])} 局；"
              f"单席位单拍最多 {max(r['maxPerTick'] for r in L)} 条；其他真人 {sum(r['oBatches'] for r in L)} 个批次 {sum(r['oBatchRows'] for r in L)} 条 / {sum(r['oAtkLanded'] for r in L)} 条陆攻（{100 * sum(r['oBatchRows'] for r in L) / max(1, sum(r['oAtkLanded'] for r in L)):.1f}%；同局另一支编队的号也算在“其他真人”里），单拍最多 {max(r['oMaxPerTick'] for r in L)} 条")
        print(f"#      21 拍内对同一目标同一 pct 重复落地 {sum(r['repeats'] for r in L)} 条（占本队落地陆攻 {100 * sum(r['repeats'] for r in L) / max(1, sum(r['atkLanded'] for r in L)):.1f}%）")
        l15 = [r for r in L if r['left1500'] is not None]
        l25 = [r for r in L if r['left2500'] is not None]
        if l15:
            print(f"#      1500 拍前有 leave 指令：本队 {sum(r['left1500'] for r in l15)}/{sum(r['squad'] for r in l15)} 个席位（{100 * sum(r['left1500'] for r in l15) / sum(r['squad'] for r in l15):.1f}%），其他真人 {sum(r['oLeft1500'] for r in l15)}/{sum(r['others'] for r in l15)}（{100 * sum(r['oLeft1500'] for r in l15) / sum(r['others'] for r in l15):.1f}%）")
        if l25:
            print(f"#      2500 拍前：本队 {sum(r['left2500'] for r in l25)}/{sum(r['squad'] for r in l25)}（{100 * sum(r['left2500'] for r in l25) / sum(r['squad'] for r in l25):.1f}%），其他真人 {sum(r['oLeft2500'] for r in l25)}/{sum(r['others'] for r in l25)}（{100 * sum(r['oLeft2500'] for r in l25) / sum(r['others'] for r in l25):.1f}%）")
        print(f"#      出生：没有任何出生指令落地的号 {sum(r['noSpawn'] for r in L)} 个（{sum(1 for r in L if r['noSpawn'])} 局）；最后一条出生指令同像素的对 {sum(r['samePixelPairs'] for r in L)} 对（{sum(1 for r in L if r['samePixelPairs'])} 局）；"
              f"每号落地的出生指令条数中位 {med('spawnCmdsMed')}")
        v = [r for r in L if r['v1Bots']]
        if v:
            print(f"#      协调器：求解次数中位 {med('solves')}，不同落点表中位 {med('layouts')}；第一份表 {sum(r['v1Bots'] for r in v)} 个点里有同像素出生指令落地的 {sum(r['v1Landed'] for r in v)} 个（一条都没落地的 {sum(1 for r in v if r['v1Landed'] == 0)}/{len(v)} 局）；"
                  f"收场时站在最后一份表上的号 {sum(r['onLast'] for r in v)}/{sum(r['v1Bots'] for r in v)}")


if __name__ == '__main__':
    main()
