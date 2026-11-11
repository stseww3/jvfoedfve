#!/usr/bin/env python3
# bundle_cmdstream.py — 只用对局包里的 replay.txt（落地的指令流）对全量对局机械计数，并拿同一局里的「其他真人」做对照。
# 不跑引擎、不跑影子策略、不读别的复盘员的结论。哪些座位是我方号：统筹的 identity-map-discovery.csv（座位号 me + 名字链）。
# 用法：python3 scripts/bundle_cmdstream.py [局号 …] [--tsv out/bundle_cmdstream.tsv] [--mine]
#       --mine 只打印 R04 复盘过的 13 局各一行（用来和真引擎事实表的数对账）
#
# 检测器（都只看落地的指令；拍 >0）：
#   BATCH3   同一个号同一拍落地 ≥3 条陆攻的「批」。正常情况下策略每 5 拍决策一次、每 7 拍执行一次，一个执行拍最多攒到 2 条；
#            ≥3 条只能是指令在路上被攒起来了（追帧）。BATCH8 = 一批 8~9 条（引擎每号每拍最多 9 条）。对应 NEW-IO-STACK9 / DRAINBATCH。
#   REPEAT   同一个号对同一个目标（不含无主地）相隔 ≤14 拍（两个执行拍）再下的陆攻，从第 2 条起算重复单。
#            对应 NEW-IO-ACKREPEAT 的落地侧代理口径（复盘里的口径要影子策略：第一条一生效策略就停手的串；这里没有影子，只按间隔）。
#   TINY     比例 <12/1024 的陆攻：陆攻手续费是余额的 12/1024，比例低于它 = 出的兵比手续费少。TINY4 = 比例 ≤4/1024。对应 NEW-AT-TINYFEE。
#            这是上界：目标已经出局、没产生进攻的指令不收手续费，要真引擎才分得出来（13 局里真引擎的数是 196 条，这里数到的更多）。
#   BOATLOW  比例 <32/1024 的船（船费是余额的 32/1024）。对应 NEW-SE-BOATWASTE 里「手续费比载兵多」的那一类。
#   SPAWN    选点阶段每个号落地的出生指令条数、最后一条是不是落在选点的最后 5 步里、一条都没有的号。对应 NEW-SP-RESOLVE / NOEXEC。
#   DONLAND  调度 / 捐款「发出 → 落地」：发出 = events.csv 里 DISPATCH / DONATE 行（策略日志里下的单，按客户端拍号分档）；
#            落地 = 录像里我方的捐款指令（按服务器拍号分档）。被反喂养配额或收款人上限拒掉的单不会进录像
#            （13 局里录像的捐款条数和真引擎入账的笔数对得上：A013 10、A038 74、A083 102），所以两者之比就是落地率。
#            只算录像这个房间里的号。不依赖 events.csv 的 likelyRejected 标记（它在 c110 上不可靠）。对应 NEW-DN-QUOTABLIND。
#   对照组 = 同一局里既不是本编队的号、也不是另一支本方编队的号的真人位。真人手点和程序发令本来就不同，对照只说明
#            「这不是同一局里所有玩家都有的现象」，不说明成因。
#   另一支本方编队的号（不进对照组，单独数）：带 [APEX] 标签、名字是 squad10 / squad8 那几个号名的；或者不带标签、名字在
#            c110 的默认名池（策略文件第 1 行 SQUAD_POOL_SET，740 个）里的。名字撞池的真人也会被划到这一组（宁可少算对照）。
import sys, os, re, csv, json, collections, statistics
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_stream as rs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
B = os.path.join(DATA, 'bundles')
IDMAP = os.path.join(DATA, 'src', 'tools', 'identity-map-discovery.csv')
C110 = os.path.join(DATA, 'src', 'strategy', 'v27-team-c110.js')
MINE = ['A013', 'A015', 'A022', 'A029', 'A038', 'A047', 'A073', 'A078', 'A081', 'A083', 'A086', 'A099', 'B034']
PHASES = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3000, '1500~2999'), (3000, 10 ** 9, '3000+')]
BANDS = [(0, 2142, '<2142'), (2142, 3213, '2142~3212'), (3213, 4284, '3213~4283'), (4284, 10 ** 9, '≥4284')]


def version(mid):
    if mid[0] == 'A':
        n = int(mid[1:])
        return 'Va' if n <= 17 else ('Vb' if n <= 95 else 'Vc')
    return 'c110' if mid[0] == 'B' else 'g09'


def norm(s):
    try:
        s = s.encode('utf-16', 'surrogatepass').decode('utf-16')
    except Exception:
        pass
    return re.sub(r'^\[[^\]]*\]\s*', '', s).strip()


def load_idmap():
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(IDMAP, encoding='utf8')):
        out[r['matchId']].append((r['me'], r['nameChain'].split('→')))
    return out


def load_sibling_names(idmap):
    tagged = set()
    for mid, recs in idmap.items():
        if mid[0] in 'AG':
            for _, chain in recs:
                tagged.update(chain)
    line1 = open(C110, encoding='utf8').readline()
    m = re.search(r'SQUAD_POOL_SET\s*=\s*new Set\(\[(.*?)\]\)', line1)
    pool = set(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))) if m else set()
    return tagged, pool


def fix(s):
    try:
        return s.encode('utf-16', 'surrogatepass').decode('utf-16')
    except Exception:
        return s


def new_group():
    g = collections.Counter()
    g['spawnCounts'] = []
    g['gaps'] = []
    return g


def scan(mid, idmap, sib_names=(set(), set())):
    r = rs.load(mid)
    if not r:
        return None
    vu, cmds = r
    card = json.load(open(os.path.join(B, mid, 'card.json'), encoding='utf8'))
    o = card['outcome']
    res = 'W' if o.get('primaryTeamWon') else ('S' if o.get('resultLabel') == 'split_straggler_won' else 'L')
    H = vu['humanCount']
    names = [norm(n) for n in vu['names'][:H]]
    ours = set()
    our_names = set()
    for me, chain in idmap.get(mid, []):
        if me == '' or int(me) >= H or int(me) >= len(names):
            continue
        if names[int(me)] in {norm(n) for n in chain}:
            ours.add(int(me))
            our_names.update(chain)
    sib = set()
    for p in range(min(H, len(names))):
        if p in ours:
            continue
        raw = fix(vu['names'][p]).strip()
        if (raw.startswith('[APEX]') and names[p] in sib_names[0]) or (not raw.startswith('[') and raw.lower() in sib_names[1]):
            sib.add(p)
    G = {'ours': new_group(), 'sib': new_group(), 'other': new_group()}
    G['ours']['players'] = len(ours)
    G['sib']['players'] = len(sib)
    G['other']['players'] = H - len(ours) - len(sib)
    grp = lambda p: 'ours' if p in ours else ('sib' if p in sib else 'other')
    atk = collections.defaultdict(list)
    spawn = collections.defaultdict(list)
    don = collections.defaultdict(list)
    for t, cid, p, a, b in cmds:
        if p >= H:
            continue
        if cid == 0 and t <= 0:
            spawn[p].append(t)
        elif t > 0 and cid == 1:
            atk[p].append((t, a, b))
        elif t > 0 and cid == 3:
            g = G[grp(p)]
            g['boat'] += 1
            g['boatLow'] += a < 32
        elif t > 0 and cid == 2:
            don[p].append((t, a, b))
    for p in range(H):
        g = G[grp(p)]
        n = len(spawn.get(p, []))
        g['spawnCounts'].append(n)
        g['spawnNone'] += n == 0
        g['spawnLate'] += bool(n) and max(spawn[p]) >= -5
    for p, lst in atk.items():
        g = G[grp(p)]
        lst.sort()
        per_tick = collections.Counter(t for t, _, _ in lst)
        for t, k in per_tick.items():
            ph = next(lab for lo, hi, lab in PHASES if lo <= t < hi)
            g['atk'] += k
            g['atk@' + ph] += k
            if k >= 3:
                g['b3'] += 1
                g['b3cmd'] += k
                g['b3@' + ph] += 1
                g['b3cmd@' + ph] += k
            if k >= 8:
                g['b8'] += 1
            g['kmax'] = max(g['kmax'], k)
            if 600 <= t < 3000:
                g['k%d' % min(k, 9)] += 1
        bt = sorted(t for t, k in per_tick.items() if k >= 3 and 600 <= t < 3000)
        g['gaps'] += [b_ - a_ for a_, b_ in zip(bt, bt[1:])]
        last = {}
        for t, a, b in lst:
            g['tiny12'] += a < 12
            g['tiny4'] += a <= 4
            if b >= 512:
                continue
            g['atkNN'] += 1
            g['atkNNpct'] += a
            if b in last and t - last[b] <= 14:
                g['rep'] += 1
                g['repPct'] += a
            last[b] = t
    for p, lst in don.items():
        if p not in ours:
            G[grp(p)]['don'] += len(lst)
            continue
        g = G['ours']
        for t, a, b in lst:
            bd = next(lab for lo, hi, lab in BANDS if lo <= t < hi)
            g['don'] += 1
            g['don@' + bd] += 1
    with open(os.path.join(B, mid, 'events.csv'), encoding='utf8') as f:
        for e in csv.DictReader(f):
            if e['type'] in ('DISPATCH', 'DONATE') and e['bot'] in our_names and e['t']:
                bd = next(lab for lo, hi, lab in BANDS if lo <= int(e['t']) < hi)
                G['ours']['sent'] += 1
                G['ours']['sent@' + bd] += 1
    return dict(mid=mid, cohort=card['cohort'], ver=version(mid), res=res, H=H, ticks=vu['totalTicks'], G=G)


def pct(a, b):
    return '%.0f%%' % (100.0 * a / b) if b else '—'


def med(xs):
    return ('%g' % statistics.median(xs)) if xs else '—'


def merge(rows, key):
    g = new_group()
    for r in rows:
        for k, v in r['G'][key].items():
            if k in ('spawnCounts', 'gaps'):
                g[k] = g[k] + v
            elif k == 'kmax':
                g[k] = max(g[k], v)
            else:
                g[k] += v
    return g


def report(label, rows):
    o, x, sb = merge(rows, 'ours'), merge(rows, 'other'), merge(rows, 'sib')
    print('  %s：有录像的 %d 局；我方号 %d 个、其他真人 %d 个；另一支本方编队的号 %d 个（%d 局里有；陆攻 %d 条，≥3 条的批占 %s；不进对照组）' % (
        label, len(rows), o['players'], x['players'], sb['players'], sum(1 for r in rows if r['G']['sib']['players']), sb['atk'], pct(sb['b3cmd'], sb['atk'])))
    for nm, g in (('我方', o), ('其他真人', x)):
        print('    %s BATCH3：陆攻 %d 条，同号同拍 ≥3 条的批 %d 个 / %d 条（占陆攻 %s），其中 8~9 条的批 %d 个，一拍最多 %d 条' % (
            nm, g['atk'], g['b3'], g['b3cmd'], pct(g['b3cmd'], g['atk']), g['b8'], g['kmax']))
    print('    BATCH3 按时段（批里的条数占陆攻；我方 | 其他真人）：' + '；'.join(
        '%s %s | %s' % (lab, pct(o['b3cmd@' + lab], o['atk@' + lab]), pct(x['b3cmd@' + lab], x['atk@' + lab])) for _, _, lab in PHASES))
    for nm, key, g in (('我方', 'ours', o), ('其他真人', 'other', x)):
        sh = sorted(100.0 * r['G'][key]['boatLow'] / r['G'][key]['boat'] for r in rows if r['G'][key]['boat'])
        rp = sorted(100.0 * r['G'][key]['rep'] / r['G'][key]['atkNN'] for r in rows if r['G'][key]['atkNN'])
        print('    %s REPEAT：打真人 / 内置 AI 的陆攻 %d 条，重复单 %d 条（%s；按比例加总占 %s；各局占比的中位 %s）；TINY：比例 <12/1024 的陆攻 %d 条（占全部陆攻 %s），其中 ≤4/1024 的 %d 条；'
              'BOATLOW：船 %d 条，比例 <32/1024 的 %d 条（%s；各局占比的中位 %s，≥50%% 的 %d 局）' % (
            nm, g['atkNN'], g['rep'], pct(g['rep'], g['atkNN']), pct(g['repPct'], g['atkNNpct']), ('%.0f%%' % statistics.median(rp)) if rp else '—',
            g['tiny12'], pct(g['tiny12'], g['atk']), g['tiny4'],
            g['boat'], g['boatLow'], pct(g['boatLow'], g['boat']), ('%.0f%%' % statistics.median(sh)) if sh else '—', sum(1 for v in sh if v >= 50)))
    for nm, g in (('我方', o), ('其他真人', x)):
        n = len(g['spawnCounts'])
        print('    %s SPAWN：每号落地的出生指令中位 %s 条（≥10 条的号 %d 个，%s）；最后一条落在选点最后 5 步里的号 %d 个（%s）；一条都没有的号 %d 个（%s）' % (
            nm, med(g['spawnCounts']), sum(1 for v in g['spawnCounts'] if v >= 10), pct(sum(1 for v in g['spawnCounts'] if v >= 10), n),
            g['spawnLate'], pct(g['spawnLate'], n), g['spawnNone'], pct(g['spawnNone'], n)))
    print('    我方 DONLAND：调度 / 捐款发出 %d 次，录像里落地 %d 条（%s）；按档（发出 → 落地）：%s' % (
        o['sent'], o['don'], pct(o['don'], o['sent']),
        '；'.join('%s %d → %d（%s）' % (lab, o['sent@' + lab], o['don@' + lab], pct(o['don@' + lab], o['sent@' + lab])) for _, _, lab in BANDS)))


def main():
    args = sys.argv[1:]
    tsv = None
    if '--tsv' in args:
        i = args.index('--tsv')
        tsv = args[i + 1]
        del args[i:i + 2]
    mine = '--mine' in args
    mids = [a for a in args if not a.startswith('--')] or (MINE if mine else sorted(os.listdir(B)))
    idmap = load_idmap()
    sib_names = load_sibling_names(idmap)
    rows = []
    norep = []
    for mid in mids:
        r = scan(mid, idmap, sib_names)
        if r is None:
            norep.append(mid)
        else:
            rows.append(r)
    if mine:
        print('# R04 复盘过的局：只用 replay.txt 数出来的我方指令（和真引擎事实表的数对账用）')
        for r in rows:
            g = r['G']['ours']
            print('  %s：我方号 %d 个；陆攻 %d 条；同号同拍 ≥3 条的批：600~1499 拍 %d 批 %d 条，1500~2999 拍 %d 批 %d 条，3000+ 拍 %d 批 %d 条；8~9 条的批 %d 个；打真人 / AI 的陆攻 %d 条，重复单 %d 条（%s）；比例 <12/1024 的陆攻 %d 条；船 %d 条（比例 <32/1024 的 %d 条）；调度 / 捐款发出 %d 次、录像里落地 %d 条' % (
                r['mid'], g['players'], g['atk'], g['b3@600~1499'], g['b3cmd@600~1499'], g['b3@1500~2999'], g['b3cmd@1500~2999'], g['b3@3000+'], g['b3cmd@3000+'],
                g['b8'], g['atkNN'], g['rep'], pct(g['rep'], g['atkNN']), g['tiny12'], g['boat'], g['boatLow'], g['sent'], g['don']))
        return
    print('# 全量对局包的落地指令流计数（%d 局有 replay.txt；没有的 %d 局：%s）' % (len(rows), len(norep), '、'.join(norep) or '无'))
    stub = [r['mid'] for r in rows if r['ticks'] < 600]
    if stub:
        print('# replay.txt 只有开头、不到 600 拍的局（不计入）：%d 局：%s' % (len(stub), '、'.join(stub)))
    rows = [r for r in rows if r['ticks'] >= 600]
    zero = [r['mid'] for r in rows if r['G']['ours']['players'] == 0]
    if zero:
        print('# 录像里认不出我方号的局（不计入）：' + '、'.join(zero))
    rows = [r for r in rows if r['G']['ours']['players'] > 0]
    print('# 计入 %d 局' % len(rows))
    print('## 1 按编队 × 版本')
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault((r['cohort'], r['ver']), []).append(r)
    for (coh, ver), rs_ in groups.items():
        report('%s %s' % (coh, ver), rs_)
    report('全部', rows)
    print('## 2 按结果（W = 主队赢；S = 拆队后别的队里有号赢；L = 输）')
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault((r['cohort'], r['res']), []).append(r)
    for (coh, res), rs_ in sorted(groups.items()):
        report('%s %s' % (coh, res), rs_)
    print('## 3 每局「我方陆攻里落在 ≥3 条的批里的占比」的分布')
    for (coh, ver), rs_ in collections.OrderedDict(((k, [r for r in rows if (r['cohort'], r['ver']) == k]) for k in
                                                    dict.fromkeys((r['cohort'], r['ver']) for r in rows))).items():
        sh = sorted(100.0 * r['G']['ours']['b3cmd'] / r['G']['ours']['atk'] for r in rs_ if r['G']['ours']['atk'])
        oth = sorted(100.0 * r['G']['other']['b3cmd'] / r['G']['other']['atk'] for r in rs_ if r['G']['other']['atk'])
        if sh:
            print('  %s %s：%d 局，我方中位 %.0f%%（最小 %.0f%%，最大 %.0f%%；≥20%% 的 %d 局，<5%% 的 %d 局）；其他真人中位 %.1f%%（最大 %.0f%%）' % (
                coh, ver, len(sh), statistics.median(sh), sh[0], sh[-1], sum(1 for v in sh if v >= 20), sum(1 for v in sh if v < 5),
                statistics.median(oth) if oth else 0, oth[-1] if oth else 0))
    print('## 4 600~2999 拍：同一个号同一拍落地的陆攻条数的分布，以及同一个号相邻两批（≥3 条）之间隔多少拍')
    for label, rs_ in [('%s %s' % k, [r for r in rows if (r['cohort'], r['ver']) == k]) for k in dict.fromkeys((r['cohort'], r['ver']) for r in rows)] + [('全部', rows)]:
        for nm, key in (('我方', 'ours'), ('其他真人', 'other')):
            g = merge(rs_, key)
            tot = sum(g['k%d' % k] * k for k in range(1, 10))
            if not tot:
                continue
            gp = sorted(g['gaps'])
            q = lambda f: gp[min(len(gp) - 1, int(f * len(gp)))] if gp else 0
            print('  %s %s：落地拍 %d 个；按一拍几条分（落地拍数 / 占陆攻条数）：%s；相邻两批相隔（%d 个间隔）P25 / 中位 / P75 = %s' % (
                label, nm, sum(g['k%d' % k] for k in range(1, 10)),
                '，'.join('%d 条 %d / %s' % (k, g['k%d' % k], pct(g['k%d' % k] * k, tot)) for k in range(1, 10) if g['k%d' % k]),
                len(gp), ('%d / %d / %d 拍' % (q(0.25), q(0.5), q(0.75))) if gp else '—'))
    if tsv:
        keys = ['players', 'atk', 'b3', 'b3cmd', 'b8', 'kmax', 'atkNN', 'rep', 'tiny12', 'tiny4', 'boat', 'boatLow', 'spawnNone', 'spawnLate', 'sent', 'don']
        with open(tsv, 'w', encoding='utf8') as f:
            f.write('\t'.join(['mid', 'cohort', 'ver', 'res', 'humans', 'ticks'] + ['our_' + k for k in keys] + ['our_spawnMedian'] +
                              ['oth_' + k for k in keys] + ['oth_spawnMedian']) + '\n')
            for r in rows:
                o, x = r['G']['ours'], r['G']['other']
                f.write('\t'.join(str(v) for v in [r['mid'], r['cohort'], r['ver'], r['res'], r['H'], r['ticks']] + [o[k] for k in keys] + [med(o['spawnCounts'])] +
                                  [x[k] for k in keys] + [med(x['spawnCounts'])]) + '\n')


if __name__ == '__main__':
    main()
