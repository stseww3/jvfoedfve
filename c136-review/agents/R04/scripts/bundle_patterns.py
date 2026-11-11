#!/usr/bin/env python3
# bundle_patterns.py — 对全部对局包（/agent/repos/c136-data/bundles/*）机械地数 R04 复盘里反复出现的失分模式。
# 只读对局包里的 card.json / traj.csv / results.csv / events.csv / in_game.log，和统筹给的号名对照表
# src/tools/identity-map-discovery.csv（B 组的号名中途会换，按座位号 me 把同一个号的几个名字并成一条轨迹）。不重放、不跑影子策略。
#
# 用法：python3 scripts/bundle_patterns.py [局号 …] [--tsv out/bundle_patterns.tsv] [--list 检测器名]
#   不给局号 = 全部对局包；--tsv 另存每局一行的原始计数；--list 逐条列出某个检测器命中的事件（核对用）。
#
# 「号」= 一条轨迹（同一个座位号）；「快照」= traj.csv 的一行（每 90 拍一行，来自 [HL-TICK] 日志）；密度 = 余额 ÷ 领土。
# 出局拍 = results.csv 里 event=died 那一行的 tick（客户端自己报告的拍数）。
#
# 检测器（括号里是对应的模式编号；定义全部写死在这里）：
#   STACK70  （NEW-IO-DRAINBATCH / NEW-AT-PARTALLIN / NEW-IO-STRIKELAG）
#            同一个号相邻两行快照（相隔正好 90 拍），前一行 拍 ≥600、余额 ≥2 万，后一行领土 >0、余额 ≤ 前一行的 30%。
#            「地没少」= 后一行领土 ≥ 前一行的 95%（兵是自己花出去的，不是被打掉的）；「自己打出去」= 地没少，并且这 90 拍里
#            events.csv 没有这个号的 DISPATCH / DONATE 行（不是送给队友的）；「有发令」= 这 90 拍里指令计数 cmds 增加了
#            （指令迟到几百拍才落地的摞，计数是早先涨的，这一栏会是 0，所以它只是下限）；「打薄」= 后一行密度 <5；
#            「600 拍内出局」= 出局拍 ≤ 后一行的拍 + 600。
#            对照 = 同样条件（拍 ≥600、余额 ≥2 万、后一行领土 >0）但没有跌到 30% 以下的相邻快照对。
#            「同局同拍对照」= 只取和某次事件同一局、同一拍的对照对（别的号在同一时刻没有摞），用来扣掉「越到后面越容易出局」的时间效应。
#   CAP150   （NEW-EC-CAPFLOOR）拍 ≥1500、领土 >0、密度 ≥149 的快照；「顶住的号」= 连续 ≥6 行（首尾相隔 ≥450 拍）都这样的号；
#            最长一段按首尾两行相隔的拍数记。
#   OVER100  拍 ≥1500、领土 >0 的快照里密度 ≥100 的占比（过软上限，利息打折）。
#   FLAT600  （NEW-AT-STANDOFF / NEW-EC-LANDLOCK / NEW-AT-SOLEHOLD）拍 ≥1500 起，领土相对段首变化 ≤4%、指令计数增加 ≤12、
#            持续 ≥600 拍的段（每个号从左到右、互不重叠）；另记段末余额 ≥ 100×领土的段。
#   SEALED   （NEW-EC-LANDLOCK）拍 ≥1500、领土 >0 的快照里 nb=0 且 neut=0（没有邻居也没有无主地）的占比；其中密度 ≥100 的行数。
#   LAG180   （NEW-IO-LAGLOSS）客户端落后：同一个房间的号的 [HL-TICK] 行按日志入库顺序排，落后量 = 此刻已出现的最大拍 − 这一行的拍；
#            「落后的号」= 最大落后量 ≥180 拍的号。只在单房间、非 1v1 的局里算（多房间的局各房间的钟不同）。
#   SLOW     日志里 [HL-SLOW-TICK]（一次决策 ≥25 毫秒）的行数和最大毫秒。
#   SHARE1530（NEW-EC-HOARD / NEW-SP-DISC）每个号取离 1530 拍最近的一行快照（相差 ≤90 拍、领土 >0；落后的客户端会跳过整 90 拍的
#            打印点，所以不能只取正好 1530 的行）：领土合计 ÷ 地图陆地 = 占地；这些号的个数 ÷ seededPlayers = 人头占比；
#            两者相除 = 「占地 ÷ 人头」；余额合计 ÷ 领土合计 = 编队密度。已经离场、没有日志的号不在里面。多房间的局和 1v1 不算。
#   LEFT     （NEW-EX-LEAVER）results.csv 里 event=left 且 tick ≤ 对局卡 endTick − 300 的号（提前离场）；
#            以及没有结果行、最后一行快照 ≤ endTick − 600 的号（日志中断）。
#   SPLIT    （NEW-EX-SPLITTEAMS）对局卡 distinctSquadTeams ≥2。
#   SPAWNGAP （NEW-SP-DISC / NEW-SP-SPREAD）spawn.csv 里每个号最后一行（最后一轮选点结果，角色不是 RANK_*）的坐标，
#            到最近的另一个我方号的距离取中位，除以 rCell = sqrt(地图陆地 ÷ (π × seededPlayers))。这是「想去的点」，不是真落点
#            （落没落到要看录像）；c110 的日志不打印选点坐标，算不了；多房间的局和 1v1 不算。
#   REJ      （NEW-DN-QUOTABLIND / NEW-DN-CAPLOOP）events.csv 里 DISPATCH / DONATE 行数，和其中 likelyRejected=True 的行数
#            （对局包自带的推断：35 拍内再次发起且余额没降；统筹的 HYPOTHESIS-AUDIT §2.4 拿录像对过，10 号编队可用、c110 不准）；
#            「顶着上限还在送」= 其中 dMe ≥100（送出方密度已过软上限）的被拒行数。
#   COLLAPSE （mid-collapse）任意 600 拍窗口里出局的号数的最大值；「崩盘」= 这个最大值 ≥ 有快照的号数的一半（且 ≥3）。
#
# 版本：A001~A017 Va，A018~A095 Vb，A097~A099 Vc，B 组 c110，G 组 g09（src/strategy/VERSION-TIMELINE.md）。
# 结果：W = 对局卡 primaryTeamWon；S = resultLabel 是 split_straggler_won（拆队后别的队里有号赢了）；L = 其余。
import sys, os, re, csv, json, math, collections, statistics
sys.dont_write_bytecode = True
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
B = os.path.join(DATA, 'bundles')
IDMAP = os.path.join(DATA, 'src', 'tools', 'identity-map-discovery.csv')
RX_TICK = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+) ')
RX_SLOW = re.compile(r'\[HL-SLOW-TICK\].*?took (\d+(?:\.\d+)?)ms')


def version(mid):
    if mid[0] == 'A':
        n = int(mid[1:])
        return 'Va' if n <= 17 else ('Vb' if n <= 95 else 'Vc')
    return 'c110' if mid[0] == 'B' else 'g09'


def load_idmap():
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(IDMAP, encoding='utf8')):
        out[r['matchId']].append(dict(room=r['roomIdx'], me=r['me'], event=r['event'], tick=int(r['resultTick']) if r['resultTick'] else None,
                                      names=r['nameChain'].split('→')))
    return out


def scan(mid, idmap, listing=None):
    d = os.path.join(B, mid)
    card = json.load(open(os.path.join(d, 'card.json'), encoding='utf8'))
    o = card['outcome']
    end = o.get('endTick') or 0
    res = 'W' if o.get('primaryTeamWon') else ('S' if o.get('resultLabel') == 'split_straggler_won' else 'L')
    recs = idmap.get(mid, [])
    if not recs:
        # 对照表里没有这一局（比如别的数据集）：退回到「一个号名一条轨迹」，出局拍取 results.csv
        ev_ = {}
        with open(os.path.join(d, 'results.csv'), encoding='utf8') as f:
            for r in csv.DictReader(f):
                ev_[r['bot']] = (r['event'], int(r['tick']) if r['tick'] else None)
        names = []
        with open(os.path.join(d, 'traj.csv'), encoding='utf8') as f:
            for r in csv.DictReader(f):
                if r['bot'] not in names:
                    names.append(r['bot'])
        recs = [dict(room='0', me='', event=ev_.get(n, ('', None))[0], tick=ev_.get(n, ('', None))[1], names=[n]) for n in names]
    name2k = {}
    for i, r in enumerate(recs):
        for n in r['names']:
            name2k[n] = i
    rooms = sorted({r['room'] for r in recs})
    tr = collections.defaultdict(list)
    unk = 0
    with open(os.path.join(d, 'traj.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            k = name2k.get(r['bot'])
            if k is None:
                unk += 1
                continue
            tr[k].append((int(r['t']), int(r['terr']), float(r['bal']), float(r['dens']), int(r['cmds']), int(r['nb']), int(r['neut'])))
    for k in tr:
        tr[k].sort()
    death = {k: recs[k]['tick'] for k in tr if recs[k]['event'] == 'died' and recs[k]['tick'] is not None}
    R = collections.OrderedDict(mid=mid, cohort=card['cohort'], ver=version(mid), mode=card.get('mode'), res=res, endTick=end, rooms=len(rooms),
                                bots=len(tr), seeded=card.get('seededPlayers'), unkRows=unk)

    def nm(k):
        return '→'.join(recs[k]['names'])

    # ---- STACK70 ----
    ev = ctl = evd = ctld = evcmd = evthin = evcmdd = evself = evselfd = evatk = evatkd = 0
    give = collections.defaultdict(list)
    with open(os.path.join(d, 'events.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            if r['type'] in ('DISPATCH', 'DONATE') and r['bot'] in name2k:
                give[name2k[r['bot']]].append(int(r['t']))
    evtracks = set()
    evt = set()
    ctl_at = collections.defaultdict(lambda: [0, 0])
    for k, rows in tr.items():
        for a, b in zip(rows, rows[1:]):
            if b[0] - a[0] != 90 or a[0] < 600 or a[2] < 20000 or b[1] <= 0:
                continue
            dead = k in death and death[k] <= b[0] + 600
            if b[2] <= 0.30 * a[2]:
                evt.add(a[0])
                ev += 1
                evd += dead
                evtracks.add(k)
                c = b[4] > a[4]
                evcmd += c
                evcmdd += (c and dead)
                thin = b[2] / b[1] < 5
                evthin += thin
                self_ = b[1] >= 0.95 * a[1]
                evself += self_
                evselfd += (self_ and dead)
                atk = self_ and not any(a[0] < t <= b[0] for t in give[k])
                evatk += atk
                evatkd += (atk and dead)
                if listing == 'STACK70':
                    print('  %s %s 拍 %d→%d 余额 %d→%d（剩 %.0f%%）领土 %d→%d%s 指令 +%d 密度 %.1f→%.1f %s' % (
                        mid, nm(k), a[0], b[0], a[2], b[2], 100 * b[2] / a[2], a[1], b[1], ('（自己打出去）' if atk else '（地没少，有捐款 / 调度）') if self_ else '（地少了）', b[4] - a[4], a[3], b[2] / b[1],
                        ('出局拍 %d（%d 拍后）' % (death[k], death[k] - b[0])) if k in death else '没有出局'))
            else:
                ctl += 1
                ctld += dead
                ctl_at[a[0]][0] += 1
                ctl_at[a[0]][1] += dead
    mctl = sum(ctl_at[t][0] for t in evt)
    mctld = sum(ctl_at[t][1] for t in evt)
    R.update(mctlPairs=mctl, mctlDead600=mctld)
    R.update(stack70Atk=evatk, stack70AtkDead600=evatkd)
    R.update(stack70=ev, stack70Bots=len(evtracks), stack70Self=evself, stack70Cmd=evcmd, stack70Thin=evthin, stack70Dead600=evd, stack70SelfDead600=evselfd,
             stack70CmdDead600=evcmdd, ctlPairs=ctl, ctlDead600=ctld)

    # ---- CAP150 / OVER100 / SEALED ----
    n15 = over = cap = sealed = sealedHi = 0
    capBots = 0
    capLong = 0
    for k, rows in tr.items():
        run = best = 0
        prev_t = None
        for t, terr, bal, dens, cmds, nb, neut in rows:
            if t < 1500 or terr <= 0:
                run = 0
                prev_t = None
                continue
            n15 += 1
            over += dens >= 100
            if nb == 0 and neut == 0:
                sealed += 1
                sealedHi += dens >= 100
            if dens >= 149:
                cap += 1
                run = run + 1 if (prev_t is not None and t - prev_t == 90) else 1
                best = max(best, run)
                prev_t = t
            else:
                run = 0
                prev_t = None
        if best >= 6:
            capBots += 1
            if listing == 'CAP150':
                print('  %s %s 连续 %d 行（首尾相隔 %d 拍）密度 ≥149' % (mid, nm(k), best, (best - 1) * 90))
        capLong = max(capLong, max(0, best - 1) * 90)
    R.update(snaps1500=n15, over100=over, cap150=cap, cap150Bots=capBots, cap150Longest=capLong, sealed=sealed, sealedHi=sealedHi)

    # ---- FLAT600 ----
    segs = segTicks = segOver = 0
    flatBots = 0
    for k, rows in tr.items():
        rs = [x for x in rows if x[0] >= 1500]
        i = 0
        had = False
        while i < len(rs):
            t0, terr0, bal0, d0, c0 = rs[i][:5]
            if terr0 <= 0:
                i += 1
                continue
            j = i
            while j + 1 < len(rs) and abs(rs[j + 1][1] - terr0) <= 0.04 * terr0 and rs[j + 1][4] - c0 <= 12:
                j += 1
            if rs[j][0] - t0 >= 600:
                segs += 1
                segTicks += rs[j][0] - t0
                segOver += rs[j][2] >= 100 * rs[j][1]
                had = True
                if listing == 'FLAT600':
                    print('  %s %s 拍 %d~%d（%d 拍）领土 %d→%d 指令 +%d 余额 %d→%d 密度 %.1f→%.1f' % (
                        mid, nm(k), t0, rs[j][0], rs[j][0] - t0, terr0, rs[j][1], rs[j][4] - c0, bal0, rs[j][2], d0, rs[j][3]))
                i = j + 1
            else:
                i += 1
        flatBots += had
    R.update(flat600=segs, flat600Bots=flatBots, flat600Ticks=segTicks, flat600Over=segOver)

    # ---- LAG180 / SLOW ----
    lagBots = lagMax = None
    slow = 0
    slowMax = 0.0
    ticks = []
    with open(os.path.join(d, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for line in f:
            m = RX_TICK.match(line)
            if m:
                k = name2k.get(m.group(2))
                if k is not None:
                    ticks.append((int(m.group(1)), k, int(m.group(3))))
                continue
            if '[HL-SLOW-TICK]' in line:
                slow += 1
                m2 = RX_SLOW.search(line)
                if m2:
                    slowMax = max(slowMax, float(m2.group(1)))
    if len(rooms) == 1 and card.get('mode') != 8:
        ticks.sort()
        front = 0
        mx = collections.Counter()
        for seq, k, t in ticks:
            front = max(front, t)
            mx[k] = max(mx[k], front - t)
        lagBots = sum(1 for k in mx if mx[k] >= 180)
        lagMax = max(mx.values(), default=0)
        if listing == 'LAG180':
            for k in mx:
                if mx[k] >= 180:
                    print('  %s %s 最大落后 %d 拍' % (mid, nm(k), mx[k]))
    R.update(lag180Bots=lagBots, lagMax=lagMax, slow=slow, slowMax=round(slowMax))

    # ---- SHARE1530 ----
    share = ratio = dens = None
    if len(rooms) == 1 and card.get('mode') != 8 and card.get('mapLand') and card.get('seededPlayers'):
        at = []
        for rows in tr.values():
            near = [x for x in rows if abs(x[0] - 1530) <= 90 and x[1] > 0]
            if near:
                x = min(near, key=lambda x: (abs(x[0] - 1530), x[0]))
                at.append((x[1], x[2]))
        if at:
            terr = sum(a for a, _ in at)
            share = 100.0 * terr / card['mapLand']
            ratio = (terr / card['mapLand']) / (len(at) / card['seededPlayers'])
            dens = sum(b for _, b in at) / terr
    R.update(n1530=len(at) if share is not None else None, share1530=None if share is None else round(share, 2), ratio1530=None if ratio is None else round(ratio, 3),
             dens1530=None if dens is None else round(dens, 1))

    # ---- LEFT ----
    leftEarly = silent = 0
    for k in tr:
        r = recs[k]
        if r['event'] == 'left' and r['tick'] is not None and r['tick'] <= end - 300:
            leftEarly += 1
            if listing == 'LEFT':
                print('  %s %s 第 %d 拍离场（对局卡 endTick %d）' % (mid, nm(k), r['tick'], end))
        elif r['event'] == '' and tr[k][-1][0] <= end - 600:
            silent += 1
            if listing == 'LEFT':
                print('  %s %s 没有结果行，最后一行快照在 %d 拍（对局卡 endTick %d）' % (mid, nm(k), tr[k][-1][0], end))
    R.update(leftEarly=leftEarly, silent=silent, squadTeams=card.get('distinctSquadTeams'))

    # ---- REJ ----
    tot = rej = rejcap = 0
    with open(os.path.join(d, 'events.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            if r['type'] in ('DISPATCH', 'DONATE'):
                tot += 1
                if r['likelyRejected'] == 'True':
                    rej += 1
                    try:
                        rejcap += float(r['dMe']) >= 100
                    except ValueError:
                        pass
    R.update(transfers=tot, rejected=rej, rejectedAtCap=rejcap)

    # ---- SPAWNGAP ----
    gap = None
    if len(rooms) == 1 and card.get('mode') != 8 and card.get('mapLand') and card.get('seededPlayers'):
        last = {}
        with open(os.path.join(d, 'spawn.csv'), encoding='utf8') as f:
            for r in csv.DictReader(f):
                last[r['me']] = (r['role'], int(r['x']), int(r['y']))
        pts = [(x, y) for role, x, y in last.values() if not role.startswith('RANK_')]
        if len(pts) >= 2:
            rc = math.sqrt(card['mapLand'] / (math.pi * card['seededPlayers']))
            ds = [min(math.hypot(p[0] - q[0], p[1] - q[1]) for j, q in enumerate(pts) if j != i) for i, p in enumerate(pts)]
            gap = round(statistics.median(ds) / rc, 3)
    R.update(spawnGap=gap, headShare=round(R['n1530'] / card['seededPlayers'], 3) if R.get('n1530') else None)

    # ---- COLLAPSE ----
    ds = sorted(death.values())
    best = 0
    start = None
    for i, t in enumerate(ds):
        n = sum(1 for u in ds if t <= u <= t + 600)
        if n > best:
            best, start = n, t
    R.update(died=len(ds), firstDeath=ds[0] if ds else None, collapseN=best, collapseAt=start, collapse=int(best >= 3 and best * 2 >= len(tr)))
    return R


def pct(a, b):
    return '%.0f%%' % (100.0 * a / b) if b else '—'


def main():
    a = sys.argv[1:]
    listing = a[a.index('--list') + 1] if '--list' in a else None
    tsv = a[a.index('--tsv') + 1] if '--tsv' in a else None
    skip = set()
    for f in ('--list', '--tsv'):
        if f in a:
            skip.update((a.index(f), a.index(f) + 1))
    mids = [x for i, x in enumerate(a) if i not in skip]
    if not mids:
        mids = sorted(os.listdir(B))
    idmap = load_idmap()
    rows = [scan(m, idmap, listing) for m in mids]
    if listing:
        return
    if tsv:
        with open(tsv, 'w', encoding='utf8') as f:
            f.write('\t'.join(rows[0].keys()) + '\n')
            for r in rows:
                f.write('\t'.join('' if v is None else str(v) for v in r.values()) + '\n')

    print('# 全量对局包的模式计数（%d 局；定义见脚本开头）' % len(rows))
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault((r['cohort'], r['ver']), []).append(r)
    groups[('全部', '')] = rows

    def line(label, rs):
        n = len(rs)
        if not n:
            return
        S = lambda k: sum((r[k] or 0) for r in rs)
        has = lambda k, th=1: sum(1 for r in rs if (r[k] or 0) >= th)
        ev, evd, ctl, ctld = S('stack70'), S('stack70Dead600'), S('ctlPairs'), S('ctlDead600')
        lagrs = [r for r in rs if r['lag180Bots'] is not None]
        shr = [r for r in rs if r['ratio1530'] is not None]
        print('  %s：%d 局，号 %d 个' % (label, n, S('bots')))
        print('    STACK70：%d 局有（%s），共 %d 次、%d 个号；其中地没少 %d 次（自己打出去 %d 次）、有发令 %d 次、打薄 %d 次；600 拍内出局 %d 次（%s），自己打出去的 %d 次里 %d 次（%s），对照 %d 对里 %d 对（%s）' % (
            has('stack70'), pct(has('stack70'), n), ev, S('stack70Bots'), S('stack70Self'), S('stack70Atk'), S('stack70Cmd'), S('stack70Thin'), evd, pct(evd, ev),
            S('stack70Atk'), S('stack70AtkDead600'), pct(S('stack70AtkDead600'), S('stack70Atk')), ctl, ctld, pct(ctld, ctl)))
        print('    CAP150：%d 局有顶住 ≥450 拍的号（%s），共 %d 个号；密度 ≥149 的快照 %d 行；OVER100：1500 拍后快照 %d 行里密度 ≥100 的 %d 行（%s）' % (
            has('cap150Bots'), pct(has('cap150Bots'), n), S('cap150Bots'), S('cap150'), S('snaps1500'), S('over100'), pct(S('over100'), S('snaps1500'))))
        print('    FLAT600：%d 局有（%s），共 %d 段、%d 个号、%d 号·拍；段末已过 100×领土的 %d 段；SEALED：1500 拍后快照里没有邻居也没有无主地的 %d 行（%s），其中密度 ≥100 的 %d 行' % (
            has('flat600'), pct(has('flat600'), n), S('flat600'), S('flat600Bots'), S('flat600Ticks'), S('flat600Over'), S('sealed'), pct(S('sealed'), S('snaps1500')), S('sealedHi')))
        if lagrs:
            print('    LAG180：可算的 %d 局里 %d 局有落后 ≥180 拍的号（%s），共 %d 个号（占这些局的号 %s）；各局最大落后量的中位 %d 拍；SLOW：%d 局有慢拍行，共 %d 行' % (
                len(lagrs), sum(1 for r in lagrs if r['lag180Bots']), pct(sum(1 for r in lagrs if r['lag180Bots']), len(lagrs)), sum(r['lag180Bots'] for r in lagrs),
                pct(sum(r['lag180Bots'] for r in lagrs), sum(r['bots'] for r in lagrs)), statistics.median(r['lagMax'] for r in lagrs), has('slow'), S('slow')))
        if shr:
            print('    SHARE1530：可算的 %d 局，「占地 ÷ 人头」中位 %.2f（<0.6 的 %d 局，≥1 的 %d 局）；编队密度中位 %.1f（≥20 的 %d 局）' % (
                len(shr), statistics.median(r['ratio1530'] for r in shr), sum(1 for r in shr if r['ratio1530'] < 0.6), sum(1 for r in shr if r['ratio1530'] >= 1),
                statistics.median(r['dens1530'] for r in shr), sum(1 for r in shr if r['dens1530'] >= 20)))
        gp = [r for r in rs if r['spawnGap'] is not None]
        if gp:
            print('    SPAWNGAP：可算的 %d 局，想去的点到最近我方号的距离 ÷ rCell 中位 %.2f（<0.9 的 %d 局，≥1.5 的 %d 局）' % (
                len(gp), statistics.median(r['spawnGap'] for r in gp), sum(1 for r in gp if r['spawnGap'] < 0.9), sum(1 for r in gp if r['spawnGap'] >= 1.5)))
        print('    LEFT：%d 局有提前离场的号（%s），共 %d 个；日志中断的号 %d 个（%d 局）；SPLIT：%d 局拆队（%s）；REJ：调度 / 捐款 %d 行，likelyRejected %d 行（%s），其中顶着上限还在送 %d 行；COLLAPSE：%d 局（%s）；出局 %d 个号' % (
            has('leftEarly'), pct(has('leftEarly'), n), S('leftEarly'), S('silent'), has('silent'), sum(1 for r in rs if (r['squadTeams'] or 0) >= 2),
            pct(sum(1 for r in rs if (r['squadTeams'] or 0) >= 2), n), S('transfers'), S('rejected'), pct(S('rejected'), S('transfers')), S('rejectedAtCap'),
            has('collapse'), pct(has('collapse'), n), S('died')))

    print('## 1 按编队 × 版本')
    for (coh, ver), rs in groups.items():
        line('%s %s' % (coh, ver), rs)
    print('## 2 按结果（W = 主队赢；S = 拆队后别的队里有号赢；L = 输）')
    for coh in ('squad10', 'squad20', 'squad8'):
        for res in ('W', 'S', 'L'):
            line('%s %s' % (coh, res), [r for r in rows if r['cohort'] == coh and r['res'] == res])
    print('## 3 STACK70 之后 600 拍内出局：分版本（事件 对 对照）')
    for (coh, ver), rs in groups.items():
        ev, evd, ctl, ctld = (sum(r[k] for r in rs) for k in ('stack70', 'stack70Dead600', 'ctlPairs', 'ctlDead600'))
        evs, evsd = sum(r['stack70Atk'] for r in rs), sum(r['stack70AtkDead600'] for r in rs)
        mc, mcd = sum(r['mctlPairs'] for r in rs), sum(r['mctlDead600'] for r in rs)
        rr = (evd / ev) / (mcd / mc) if ev and mc and mcd else float('nan')
        rs_ = (evsd / evs) / (mcd / mc) if evs and mc and mcd else float('nan')
        print('  %s %s：事件 %d 次里 %d 次（%s）；其中自己打出去的 %d 次里 %d 次（%s）；全部对照 %d 对里 %d 对（%s）；同局同拍对照 %d 对里 %d 对（%s）；对同局同拍对照的比值：全部 %.1f、自己打出去的 %.1f' % (
            coh, ver, ev, evd, pct(evd, ev), evs, evsd, pct(evsd, evs), ctl, ctld, pct(ctld, ctl), mc, mcd, pct(mcd, mc), rr, rs_))
    print('## 4 同上，按结果')
    for coh in ('squad10', 'squad20', 'squad8'):
        for res in ('W', 'S', 'L'):
            rs = [r for r in rows if r['cohort'] == coh and r['res'] == res]
            if not rs:
                continue
            ev, evd, ctl, ctld = (sum(r[k] for r in rs) for k in ('stack70', 'stack70Dead600', 'ctlPairs', 'ctlDead600'))
            evs, evsd = sum(r['stack70Atk'] for r in rs), sum(r['stack70AtkDead600'] for r in rs)
            mc, mcd = sum(r['mctlPairs'] for r in rs), sum(r['mctlDead600'] for r in rs)
            print('  %s %s（%d 局）：事件 %d 次里 %d 次（%s）；自己打出去的 %d 次里 %d 次（%s）；全部对照 %d 对里 %d 对（%s）；同局同拍对照 %d 对里 %d 对（%s）' % (
                coh, res, len(rs), ev, evd, pct(evd, ev), evs, evsd, pct(evsd, evs), ctl, ctld, pct(ctld, ctl), mc, mcd, pct(mcd, mc)))

    def spearman(xs, ys):
        def rank(v):
            o = sorted(range(len(v)), key=lambda i: v[i])
            rk = [0.0] * len(v)
            i = 0
            while i < len(o):
                j = i
                while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                    j += 1
                for q in range(i, j + 1):
                    rk[o[q]] = (i + j) / 2.0 + 1
                i = j + 1
            return rk
        rx, ry = rank(xs), rank(ys)
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
        sy = math.sqrt(sum((b - my) ** 2 for b in ry))
        return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy) if sx and sy else float('nan')

    print('## 5 局与局之间的秩相关（Spearman；只是相关，不是因果）')
    for coh in ('squad10', 'squad20', 'squad8'):
        rs = [r for r in rows if r['cohort'] == coh]
        for xk, yk, label in (('spawnGap', 'ratio1530', '出生间距 ÷ rCell  对  1530 拍占地 ÷ 人头'),
                              ('headShare', 'ratio1530', '我方号数 ÷ 真人位  对  1530 拍占地 ÷ 人头'),
                              ('dens1530', 'ratio1530', '1530 拍编队密度  对  1530 拍占地 ÷ 人头'),
                              ('lagMax', 'ratio1530', '最大客户端落后量  对  1530 拍占地 ÷ 人头'),
                              ('ratio1530', 'firstDeath', '1530 拍占地 ÷ 人头  对  第一个号出局的拍')):
            pr = [(r[xk], r[yk]) for r in rs if r[xk] is not None and r[yk] is not None]
            if len(pr) >= 8 and len({p[0] for p in pr}) > 1:
                print('  %s %s：%d 局，ρ = %+.2f' % (coh, label, len(pr), spearman([p[0] for p in pr], [p[1] for p in pr])))
        tri = [(r['spawnGap'], r['ratio1530'], r['headShare']) for r in rs if None not in (r['spawnGap'], r['ratio1530'], r['headShare'])]
        if len(tri) >= 8:
            x, y, z = ([t[i] for t in tri] for i in range(3))
            rxy, rxz, ryz = spearman(x, y), spearman(x, z), spearman(y, z)
            den = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
            print('  %s 出生间距 ÷ rCell 对 1530 拍占地 ÷ 人头，扣掉「我方号数 ÷ 真人位」之后的偏相关：%d 局，ρ = %+.2f（间距与人头占比本身的 ρ = %+.2f）' % (
                coh, len(tri), (rxy - rxz * ryz) / den if den else float('nan'), rxz))
    if any(r['unkRows'] for r in rows):
        print('号名对照表里找不到的快照行：' + '、'.join('%s %d 行' % (r['mid'], r['unkRows']) for r in rows if r['unkRows']))


if __name__ == '__main__':
    main()
