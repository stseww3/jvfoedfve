#!/usr/bin/env python3
# split_roster.py — 拆队局（squad20 没有队标、被大厅分进几个队）的结构账：
#   谁是编队号、谁打到出局、谁中途掉线、同局还有没有另一支我方编队、哪些真人撞了编队名单（被 c110 当成兄弟保护），
#   以及这几类玩家之间互相出了多少兵、换了多少地。
# 用法：python3 scripts/split_roster.py <局号> [--win 0,1500,2600,4500,末拍] [--at 拍,拍,…（第 3 节多列几个时刻）] [--drop 队号:拍数 …（第 7b 节：别的队掉得最多的一段）]
# 数据：tmp/truth/<局号>/{meta.json,state.tsv,cmd.tsv,ev.tsv,flow.tsv}（engine_truth_all.sh）+ 对局包 in_game.log、results.csv
#       + src/strategy/v27-team-c110.js 第 1 行的 SQUAD_POOL_SET（c110 认「编队兄弟」只看名字在不在这张表里：Policy.isOurSquadBot L3973~3976）。
# 分类：
#   S  打到出局的编队号（results.csv 里有它的 meId）
#   L  中途掉线的编队号（日志里有 [HL-GAME-INIT] me=…，results.csv 里没有）
#   X  同局的另一支我方编队（名字以 [APEX] 开头）
#   P  撞名单的真人（名字在 SQUAD_POOL_SET 里，但日志里没有它）
#   H  其余真人
import sys, os, re, csv, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')


def tsv(fp):
    with open(fp, encoding='utf8') as f:
        rd = csv.reader(f, delimiter='\t')
        head = next(rd)
        return head, [r for r in rd]


def wan(v):
    return '%.1f万' % (v / 1e4) if abs(v) >= 1e4 else format(int(v), ',')


def main():
    a = sys.argv[1:]
    mid = a[0]
    d = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf8'))
    ku, ke, last = meta['info']['ku'], meta['info']['ke'], meta['lastTick']
    name = {p['p']: p['name'] for p in meta['players']}
    team = {p['p']: p['team'] for p in meta['players']}
    wins = [int(x) if x.isdigit() else last for x in (a[a.index('--win') + 1].split(',') if '--win' in a else '0,1500,2600,4500,末拍'.split(','))]

    line1 = open(os.path.join(DATA, 'src', 'strategy', 'v27-team-c110.js'), encoding='utf8').readline()
    pool = set(json.loads(re.search(r'new Set\((\[.*?\])\)', line1).group(1)))

    init, lastlog = {}, {}
    rx_init = re.compile(r'\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)')
    rx_tick = re.compile(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+) ')
    rx_slot = re.compile(r'\[HL-SPAWN\] me=(\d+) slot=(\d+) \(squad=(\d+)')
    slot, squadn = {}, set()
    with open(os.path.join(DATA, 'bundles', mid, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for line in f:
            m = rx_init.search(line)
            if m:
                init[int(m.group(2))] = m.group(1)
                continue
            m = rx_slot.search(line)
            if m:
                slot[int(m.group(1))] = int(m.group(2))
                squadn.add(int(m.group(3)))
                continue
            m = rx_tick.search(line)
            if m:
                lastlog[m.group(1)] = max(lastlog.get(m.group(1), 0), int(m.group(2)))
    res = {}
    with open(os.path.join(DATA, 'bundles', mid, 'results.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            res[int(r['meId'])] = r

    cls = {}
    for p in range(ku):
        raw = name[p].strip()
        if p in init:
            cls[p] = 'S' if p in res else 'L'
        elif raw.startswith('[APEX] '):
            cls[p] = 'X'
        elif raw.lower() in pool or '[NPL]' in raw.upper() or '[NOPE]' in raw.upper():
            cls[p] = 'P'
        else:
            cls[p] = 'H'
    CL = {'S': '打到出局的编队号', 'L': '掉线的编队号', 'X': '另一支我方编队（[APEX]）', 'P': '撞名单的真人', 'H': '其余真人'}

    def nm(p):
        if p == 512:
            return '无主地'
        if p >= ku:
            return 'AI#%d' % p
        return '%s#%d(队%d)' % (name[p], p, team[p])

    _, rows = tsv(os.path.join(d, 'state.tsv'))
    state = collections.defaultdict(dict)
    for r in rows:
        state[int(r[0])][int(r[1])] = (int(r[2]), int(r[3]), int(r[9]), int(r[10]))
    samples = sorted(state)

    def at(t):
        t = min(t, last)
        t -= t % meta['step']
        while t not in state and t > 0:
            t -= meta['step']
        return t

    _, rows = tsv(os.path.join(d, 'ev.tsv'))
    left, dead, gifts = {}, {}, collections.defaultdict(list)
    for r in rows:
        t, kind, p = int(r[0]), r[1], int(r[2])
        if kind == 'state' and r[4] == '2':
            left[p] = t
        elif kind in ('dead', 'dead-other') and p not in dead:
            by = ''
            m = re.search(r'by:([0-9:,]*)', r[5] if len(r) > 5 else '')
            if m and m.group(1):
                by = int(m.group(1).split(',')[0].split(':')[0])
            dead[p] = (t, by)
        elif kind == 'aigift':
            gifts[p].append((t, int(r[3]), int(r[4])))
    # atk = 发起的进攻：陆攻指令落地时真正出的兵（cmd.tsv 的 sub = atk:目标:兵）+ 船登陆时转成的进攻（ev.tsv 的 land … |atk:目标:兵）。
    # （tmp/truth 的 atk.tsv 是每 10 拍一张「在途进攻」快照，同一发会出现很多次，不能拿来数出兵。）
    atk = []
    for r in rows:
        if r[1] == 'land' and '|' in r[5]:
            tail = r[5].split('|', 1)[1]
            if tail.startswith('atk:'):
                _, tg, tr = tail.split(':')
                atk.append((int(r[0]), int(r[2]), int(tg), int(tr)))
    _, rows = tsv(os.path.join(d, 'cmd.tsv'))
    lastcmd = {}
    for r in rows:
        if int(r[1]) >= 0:
            continue
        if r[2] != '9':
            lastcmd[int(r[3])] = max(lastcmd.get(int(r[3]), 0), int(r[0]))
        if r[2] == '1' and len(r) > 16 and r[16].startswith('atk:'):
            for sub in r[16].split(';'):
                k = sub.split(':')
                if k[0] == 'atk' and int(k[2]) > 0:
                    atk.append((int(r[0]), int(r[3]), int(k[1]), int(k[2])))
    atk.sort()
    _, rows = tsv(os.path.join(d, 'flow.tsv'))
    flow = [(int(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in rows]

    print('# %s 拆队局的结构账（真人位 %d 个；陆地 %s 格；录像到 %d 拍）' % (mid, ku, format(ke, ','), last))
    print('## 1 谁是谁')
    cnt = collections.Counter(cls.values())
    print('  ' + '；'.join('%s %d 个' % (CL[k], cnt[k]) for k in 'SLXPH'))
    print('  真人位里我方的号（S+L+X）%d 个 = %d%%；c110 按名字认的「编队兄弟」= S+L+P 共 %d 个' % (
        cnt['S'] + cnt['L'] + cnt['X'], round(100 * (cnt['S'] + cnt['L'] + cnt['X']) / ku), cnt['S'] + cnt['L'] + cnt['P']))
    teams = sorted(set(team.values()))
    for tm in teams:
        ps = [p for p in range(ku) if team[p] == tm]
        parts = []
        for k in 'SLXPH':
            xs = [p for p in ps if cls[p] == k]
            if xs:
                parts.append('%s %d：%s' % (CL[k], len(xs), '、'.join('%s#%d' % (name[p], p) for p in xs)))
        print('  队 %d（%d 人）：%s' % (tm, len(ps), '；'.join(parts)))

    if slot:
        sl = lambda k: '、'.join('%d(%s)' % (slot[p], name[p]) for p in sorted((q for q in slot if cls.get(q) == k), key=lambda q: slot[q]))
        allslots = set(range(max(20, max(squadn) if squadn else 20)))
        print('  编队槽位（日志 [HL-SPAWN] 的 slot=；日志里 squad=%s 是 c110 按名字数出来的「兄弟」个数，含撞名单的真人）：' % '/'.join(str(x) for x in sorted(squadn)))
        print('    打到出局的：%s' % sl('S'))
        print('    掉线的：%s' % sl('L'))
        print('    本局没有出现的槽位：%s' % ('、'.join(str(k) for k in sorted(allslots - set(slot.values()))) or '无'))
        lo = [p for p in slot if slot[p] <= 9]
        hi = [p for p in slot if slot[p] >= 10]
        print('    槽位 0~9：在场 %d 个，掉线 %d 个；槽位 10~19：在场 %d 个，掉线 %d 个' % (len(lo), sum(1 for p in lo if cls.get(p) == 'L'), len(hi), sum(1 for p in hi if cls.get(p) == 'L')))
    lv = collections.defaultdict(list)
    _, crow0 = tsv(os.path.join(d, 'cmd.tsv'))
    for r in crow0:
        if r[2] == '9' and int(r[1]) < 0 and int(r[3]) < ku:
            lv[int(r[0])].append(int(r[3]))
    print('  录像里的离场指令（id=9；拍：谁，括号里是类别）：%s' % '；'.join('%d：%s' % (t, '、'.join('%s[%s]' % (name[p], cls[p]) for p in ps)) for t, ps in sorted(lv.items())))
    print('## 2 掉线的编队号（日志停在哪一拍、最后一条指令哪一拍落地、哪一拍被判离场、之后怎样）')
    for p in sorted(p for p in range(ku) if cls[p] == 'L'):
        lt = left.get(p)
        st = state[at(lt)].get(p) if lt is not None else None
        dt = dead.get(p)
        took = collections.Counter()
        if lt is not None:
            for (t, x, y, px) in flow:
                if x == p and t > lt:
                    took[y] += px
        g = gifts.get(p, [])
        gsum = collections.Counter()
        for (t, q, v) in g:
            gsum[q] += v
        print('  %s：日志最后一行 HL-TICK t=%s；最后一条非离场指令落地在 %s 拍；%s 拍被判离场（当时 %s 格 / %s 兵）；%s；离场后它的地去了：%s%s' % (
            nm(p), lastlog.get(init[p], '—'), lastcmd.get(p, '—'), lt if lt is not None else '—',
            format(st[0], ',') if st else '—', wan(st[1]) if st else '—',
            ('%d 拍出局（最后压在它身上的是 %s）' % (dt[0], nm(dt[1]) if dt[1] != '' else '—')) if dt else '到录像结束还在',
            '、'.join('%s %s' % (nm(q), format(v, ',')) for q, v in took.most_common(4)) or '—',
            ('；离场后引擎替它捐了 %d 笔 %s：%s' % (len(g), wan(sum(v for _, _, v in g)), '、'.join('%s %s' % (nm(q), wan(v)) for q, v in gsum.most_common(4)))) if g else ''))
    lcells = sum(state[at(left[p])].get(p, (0, 0))[0] for p in range(ku) if cls[p] == 'L' and p in left)
    lbal = sum(state[at(left[p])].get(p, (0, 0))[1] for p in range(ku) if cls[p] == 'L' and p in left)
    print('  合计：离场那一刻这 %d 个号一共 %s 格（全图 %.1f%%）、%s 兵' % (cnt['L'], format(lcells, ','), 100 * lcells / ke, wan(lbal)))

    # 内置 AI 的领土在 team.tsv 里（队号 100）；state.tsv 只有真人位
    aiterr = {}
    _, trows = tsv(os.path.join(d, 'team.tsv'))
    for r in trows:
        if int(r[1]) >= 100:
            aiterr[int(r[0])] = aiterr.get(int(r[0]), 0) + int(r[2])
    print('## 3 各类玩家的领土占比（%，全图陆地）与兵')
    pts = [630, 1080, 1500, 1800, 2100, 2600, 3000, 4500, 6000, 7500, 9000, last]
    a_ = sys.argv[1:]
    if '--at' in a_:
        pts += [int(x) for x in a_[a_.index('--at') + 1].split(',')]
    pts = sorted(set(at(t) for t in pts if t <= last))
    print('  拍 | ' + ' | '.join('%s 地%% / 兵 / 在场' % k for k in 'SLXPH') + ' | 内置 AI 地% | S + 还在线的 L 地%')
    for t in pts:
        st = state[t]
        cells = []
        for k in 'SLXPH':
            ps = [p for p in range(ku) if cls[p] == k and st.get(p) and st[p][2] and st[p][0] > 0]
            cells.append('%.1f / %s / %d' % (100 * sum(st[p][0] for p in ps) / ke, wan(sum(st[p][1] for p in ps)), len(ps)))
        onl = sum(st[p][0] for p in range(ku) if st.get(p) and (cls[p] == 'S' or (cls[p] == 'L' and t < left.get(p, 10 ** 9))))
        print('  %d | %s | %.1f | %.1f' % (t, ' | '.join(cells), 100 * aiterr.get(t, 0) / ke, 100 * onl / ke))
    print('  各队占比里编队号（S）占多少：')
    for t in pts:
        st = state[t]
        parts = []
        for tm in teams:
            tt = sum(st[p][0] for p in range(ku) if team[p] == tm and st.get(p))
            ss = sum(st[p][0] for p in range(ku) if team[p] == tm and cls[p] == 'S' and st.get(p))
            tb = sum(st[p][1] for p in range(ku) if team[p] == tm and st.get(p))
            parts.append('队%d %.1f%%（S %.1f%%，全队兵 %s）' % (tm, 100 * tt / ke, 100 * ss / ke, wan(tb)))
        print('    %d：%s' % (t, '；'.join(parts)))

    def peak(sel):
        best = (0, 0)
        for t in sorted(state):
            v = sum(state[t][p][0] for p in range(ku) if state[t].get(p) and sel(p, t))
            if v > best[0]:
                best = (v, t)
        return '%s 格 = %.2f%%（%d 拍）' % (format(best[0], ','), 100 * best[0] / ke, best[1])
    print('  峰值（10 拍一采）：S %s；S + 还在线的 L %s；S + L（含离场后还占着的地）%s；X %s；S + L + X %s' % (
        peak(lambda p, t: cls[p] == 'S'),
        peak(lambda p, t: cls[p] == 'S' or (cls[p] == 'L' and t < left.get(p, 10 ** 9))),
        peak(lambda p, t: cls[p] in 'SL'),
        peak(lambda p, t: cls[p] == 'X'),
        peak(lambda p, t: cls[p] in 'SLX')))

    def kind_of(p, t):
        if p == 512:
            return '无主地'
        if p >= ku:
            return 'AI'
        k = cls[p]
        if k == 'L' and p in left and t > left[p]:
            return 'L离场后'
        return k

    order = ['S', 'L', 'L离场后', 'X', 'P', 'H', 'AI', '无主地']
    print('## 4 这几类玩家之间的出兵（落地并出了兵的陆攻指令 + 船登陆转成的进攻；条 / 兵）和换地（格）')
    for i in range(len(wins) - 1):
        t0, t1 = wins[i], wins[i + 1]
        m = collections.defaultdict(lambda: [0, 0])
        for (t, x, y, tr) in atk:
            if t0 < t <= t1 and x < ku:
                e = m[(kind_of(x, t), kind_of(y, t))]
                e[0] += 1
                e[1] += tr
        fm = collections.Counter()
        for (t, x, y, px) in flow:
            if t0 < t <= t1:
                fm[(kind_of(x, t), kind_of(y, t))] += px
        print('  (%d,%d]：' % (t0, t1))
        for src in ('S', 'X', 'P', 'H', 'L'):
            parts = []
            for dst in order:
                e = m.get((src, dst))
                if e and e[1] > 0:
                    net = fm.get((dst, src), 0) - fm.get((src, dst), 0)
                    if src == 'X' and dst in ('AI', '无主地'):
                        # flow.tsv 只记和「有编队号的队」有关的易手，[APEX] 那一队和 AI / 无主地之间的不在表里
                        parts.append('→%s %d 条 %s' % (dst, e[0], wan(e[1])))
                    else:
                        parts.append('→%s %d 条 %s（净得地 %+d）' % (dst, e[0], wan(e[1]), net))
            if parts:
                print('    %s %s' % (src, '；'.join(parts)))

    print('## 5 编队兄弟之间（S、L、P 互相）的出兵——c110 的规则是外人活着时互不出手（isProtectedSquadMate L3993~3996）')
    bro = [(t, x, y, tr) for (t, x, y, tr) in atk if x < ku and y < ku and cls[x] in 'SLP' and cls[y] in 'SLP' and team[x] != team[y]]
    by = collections.defaultdict(lambda: [0, 0, 10 ** 9, 0])
    for (t, x, y, tr) in bro:
        e = by[(x, y)]
        e[0] += 1
        e[1] += tr
        e[2] = min(e[2], t)
        e[3] = max(e[3], t)
    if not by:
        print('  没有')
    for (x, y), e in sorted(by.items(), key=lambda kv: -kv[1][1]):
        back = by.get((y, x), [0, 0])
        net = sum(px for (t, a_, b_, px) in flow if a_ == y and b_ == x) - sum(px for (t, a_, b_, px) in flow if a_ == x and b_ == y)
        print('  %s[%s] → %s[%s]：%d 条 %s 兵（%d~%d 拍），全场从它净拿 %+d 格；反方向 %d 条 %s 兵' % (
            nm(x), cls[x], nm(y), cls[y], e[0], wan(e[1]), e[2], e[3], net, back[0], wan(back[1])))

    print('## 6 S 号和别的队里的人：谁打了谁（全场；兵 / 净得地）')
    S = [p for p in range(ku) if cls[p] == 'S']
    for p in S:
        out = collections.defaultdict(lambda: [0, 0])
        inc = collections.defaultdict(lambda: [0, 0])
        for (t, x, y, tr) in atk:
            if x == p and y < ku:
                out[y][0] += 1
                out[y][1] += tr
            elif y == p and x < ku:
                inc[x][0] += 1
                inc[x][1] += tr
        got = collections.Counter()
        lost = collections.Counter()
        for (t, x, y, px) in flow:
            if y == p and x < ku:
                got[x] += px
            elif x == p and y < ku:
                lost[y] += px
        def cl(q):
            return cls[q] + ('·同队' if team[q] == team[p] else '')
        print('  %s[队%d]：打出去 %s；挨的打 %s' % (
            name[p], team[p],
            '、'.join('%s[%s] %d 条 %s（净 %+d 格）' % (nm(q), cl(q), e[0], wan(e[1]), got[q] - lost[q]) for q, e in sorted(out.items(), key=lambda kv: -kv[1][1])[:6]) or '—',
            '、'.join('%s[%s] %d 条 %s' % (nm(q), cl(q), e[0], wan(e[1])) for q, e in sorted(inc.items(), key=lambda kv: -kv[1][1])[:6]) or '—'))
    tot = collections.defaultdict(lambda: [0, 0])
    for (t, x, y, tr) in atk:
        if x < ku and y < ku and cls[x] == 'S':
            k = cls[y] if cls[y] != 'H' else ('H·主队' if team[y] == collections.Counter(team[p] for p in S).most_common(1)[0][0] else 'H·其他队')
            tot[k][0] += 1
            tot[k][1] += tr
    print('  S 号全场对真人位出兵合计：' + '；'.join('%s %d 条 %s' % (k, e[0], wan(e[1])) for k, e in sorted(tot.items(), key=lambda kv: -kv[1][1])))

    # 7 某一队掉得最多的一段：地去了谁手里（默认：主力队 = S 号最多的那个队，300 拍；--drop 队号:拍数 可以多看几个）
    prim0 = collections.Counter(team[p] for p in S).most_common(1)[0][0]
    ts = sorted(state)

    def drop_window(prim, win, title):
        tt = {t: sum(state[t][p][0] for p in range(ku) if team[p] == prim and state[t].get(p)) for t in ts}
        worst = None
        for t in ts:
            t1 = t + win
            if t1 in tt and (worst is None or tt[t1] - tt[t] < worst[0]):
                worst = (tt[t1] - tt[t], t, t1)
        print(title)
        if worst:
            dv, t0, t1 = worst
            print('  (%d,%d]：%s 格（%.1f%%）→ %s 格（%.1f%%），少了 %s 格' % (t0, t1, format(tt[t0], ','), 100 * tt[t0] / ke, format(tt[t1], ','), 100 * tt[t1] / ke, format(-dv, ',')))
            lost = collections.Counter()
            got = collections.Counter()
            for (t, x, y, px) in flow:
                if not (t0 < t <= t1):
                    continue
                if x < ku and team[x] == prim and not (y < ku and team[y] == prim):
                    lost[y] += px
                elif y < ku and team[y] == prim and not (x < ku and team[x] == prim):
                    got[x] += px
            net = collections.Counter({q: lost[q] - got[q] for q in set(lost) | set(got)})
            def who(q):
                if q >= ku:
                    return '无主地' if q == 512 else 'AI#%d' % q
                return '%s[%s]' % (nm(q), cls[q] + ('·离场后' if cls[q] == 'L' and t0 >= left.get(q, 10 ** 9) else ''))
            print('  净拿走队 %d 的地最多的：%s' % (prim, '、'.join('%s %s' % (who(q), format(v, ',')) for q, v in net.most_common(10) if v > 0)))
            bycls = collections.Counter()
            for q, v in net.items():
                k = ('无主地' if q == 512 else 'AI') if q >= ku else cls[q]
                bycls[k] += v
            print('  按类别净拿走：%s' % '；'.join('%s %s' % (k, format(v, ',')) for k, v in bycls.most_common()))
            mem = []
            for p in range(ku):
                if team[p] == prim and state[t0].get(p) and state[t0][p][0] > 0:
                    mem.append('%s[%s] %s → %s' % (name[p], cls[p], format(state[t0][p][0], ','), format(state[t1].get(p, (0, 0))[0], ',')))
            print('  队 %d 各号这一段的领土：%s' % (prim, '；'.join(mem)))

    drop_window(prim0, 300, '## 7 主力队（队 %d，S 号最多的队）掉得最多的 300 拍' % prim0)
    a_ = sys.argv[1:]
    for k_, v_ in enumerate(a_):
        if v_ == '--drop' and k_ + 1 < len(a_):
            tm_, w_ = a_[k_ + 1].split(':')
            drop_window(int(tm_), int(w_), '## 7b 队 %s 掉得最多的 %s 拍' % (tm_, w_))

    # 8 出生：c110 的号各自选点（chooseSpawn L4007~4154），不经协调器
    print('## 8 出生点（最后一条出生指令在选点阶段第几步；最近的人是谁、它最后一条出生指令在第几步）')
    import math
    spawn = {p['p']: p.get('spawn') for p in meta['players'] if p['p'] < ku}
    box = {p['p']: p.get('box') for p in meta['players'] if p['p'] < ku}
    here = [p for p in range(ku) if box.get(p) and box[p][0] <= box[p][2]]
    laststep, nspawn = {}, collections.Counter()
    _, crow = tsv(os.path.join(d, 'cmd.tsv'))
    for r in crow:
        if r[2] == '0' and int(r[1]) >= 0:
            laststep[int(r[3])] = max(laststep.get(int(r[3]), -1), int(r[1]))
            nspawn[int(r[3])] += 1
    def dist(a_, b_):
        return math.hypot(spawn[a_][0] - spawn[b_][0], spawn[a_][1] - spawn[b_][1])
    dn, db = [], []
    for p in here:
        if cls[p] not in 'SL':
            continue
        near = min((dist(p, q), q) for q in here if q != p)
        bros = [(dist(p, q), q) for q in here if q != p and cls[q] in 'SLP']
        nb_ = min(bros) if bros else (0, p)
        dn.append(near[0]); db.append(nb_[0])
        q = near[1]
        print('  %s[%s]：%d 条出生指令，最后一条第 %s 步，落在 (%d,%d)；最近的人 %s[%s%s] %d 像素（它最后一条第 %s 步，%s）；最近的「兄弟」%s[%s] %d 像素' % (
            nm(p), cls[p], nspawn[p], laststep.get(p, '—'), spawn[p][0], spawn[p][1],
            nm(q), cls[q], '·同队' if team[q] == team[p] else '', near[0], laststep.get(q, '—'),
            '它后到' if laststep.get(q, -1) > laststep.get(p, -1) else '它先到', nm(nb_[1]), cls[nb_[1]], nb_[0]))
    oth = [min(dist(p, q) for q in here if q != p) for p in here if cls[p] not in 'SL']
    med = lambda v: sorted(v)[len(v) // 2] if v else 0
    print('  S+L 到最近的人：中位 %d 像素（其他到场真人 %d）；到最近的「兄弟」：中位 %d、最小 %d（chooseSpawn 的 minSep = 145）' % (med(dn), med(oth), med(db), min(db) if db else 0))


if __name__ == '__main__':
    main()
