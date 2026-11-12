#!/usr/bin/env python3
# bundle_humans.py — 发现集（bundles/）里有录像的局：「别的真人」实际是怎么下指令的。给模拟器写对手用的画像。
#
# 用法（只读 c136-data/bundles/；纯 Python 解码录像，不跑引擎）：
#   python3 scripts/bundle_humans.py            # 逐局解码并缓存到 tmp/humans/<局>.json；一次最多跑 85 秒，没跑完就再跑一次
#   python3 scripts/bundle_humans.py --report > out/bundle_humans.txt     # 全部缓存好之后出表
#
# 分组：我方 = 身份表（identity-map-discovery.csv）里对上名字的号；姐妹编队 = 带 [APEX] 前缀且名字在我方用过的名字里、
#       或名字在 c110 名池里的其他真人（同 bundle_cmdstream.py）；别人 = 其余真人。
# 量什么（都按落地拍分段；比例 = (pct+1)/1024，是落地那一拍余额的比例）：
#   ATK   陆攻：条数，比例的分位数，目标是无主地 / 内置 AI / 真人各占多少，比例 ≥ 1000/1024 的条数
#   HIT   打真人的陆攻：比例的分位数；同一个人相邻两次打真人隔几拍（先取每人的中位，再看人与人之间的分位数）
#   DON   捐款：条数、有捐款的局数、比例的分位数、比例 ≥ 1000/1024 的条数；3213 拍以后每局收到别人捐款最多的那个号占几成（条数）
#   BOAT  船：条数、比例的分位数
#   RATE  每人落地的指令条数（陆攻 + 捐款 + 船）的分位数
# 看不到的：录像只有指令，没有余额和领土——出了多少兵、捐款有没有被配额拒掉、打的是不是比自己弱的人，这里都不知道；
#           这些在 13 局的真引擎事实表里才有（各局复盘的 winnerNotes）。
import sys, os, json, time, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_stream as rs
import bundle_cmdstream as bc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'tmp', 'humans')
PH = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3213, '1500~3212'), (3213, 4284, '3213~4283'), (4284, 10 ** 9, '≥4284')]
GROUPS = [('other', '别人'), ('ours', '我方'), ('sib', '姐妹编队')]


def phase(t):
    for lo, hi, lab in PH:
        if lo <= t < hi:
            return lab
    return PH[-1][2]


def scan(mid, idmap, sib_names):
    r = rs.load(mid)
    if not r:
        return None
    vu, cmds = r
    H = vu['humanCount']
    names = [bc.norm(n) for n in vu['names'][:H]]
    ours = set()
    for me, chain in idmap.get(mid, []):
        if me == '' or int(me) >= H or int(me) >= len(names):
            continue
        if names[int(me)] in {bc.norm(n) for n in chain}:
            ours.add(int(me))
    sib = set()
    for p in range(min(H, len(names))):
        if p in ours:
            continue
        raw = bc.fix(vu['names'][p]).strip()
        if (raw.startswith('[APEX]') and names[p] in sib_names[0]) or (not raw.startswith('[') and raw.lower() in sib_names[1]):
            sib.add(p)
    grp = lambda p: 'ours' if p in ours else ('sib' if p in sib else 'other')
    out = dict(mid=mid, ver=bc.version(mid), H=H, ticks=vu['totalTicks'],
               players={g: 0 for g, _ in GROUPS}, rows=[])
    for p in range(H):
        out['players'][grp(p)] += 1
    # rows: [组, 号, 拍, 种类(1 陆攻 2 捐款 3 船), 比例, 目标类(N 无主 / A 内置 AI / H 真人 / -), 目标号]
    for t, cid, p, a, b in cmds:
        if p >= H or t <= 0 or cid not in (1, 2, 3):
            continue
        if cid == 1:
            cls = 'N' if b >= 512 else ('H' if b < H else 'A')
        elif cid == 2:
            cls = 'H' if b < H else 'A'
        else:
            cls = '-'
        out['rows'].append([grp(p), p, t, cid, a, cls, b if cid != 3 else -1])
    return out


def build():
    os.makedirs(CACHE, exist_ok=True)
    idmap = bc.load_idmap()
    sib_names = bc.load_sibling_names(idmap)
    mids = sorted(d for d in os.listdir(bc.B) if os.path.isdir(os.path.join(bc.B, d)))
    t0 = time.time()
    done = todo = 0
    for mid in mids:
        fp = os.path.join(CACHE, mid + '.json')
        if os.path.exists(fp):
            done += 1
            continue
        if time.time() - t0 > 85:
            todo += 1
            continue
        r = scan(mid, idmap, sib_names)
        json.dump(r, open(fp, 'w', encoding='utf8'))
        done += 1
    print('缓存 %d 局，还剩 %d 局%s' % (done, todo, '（再跑一次）' if todo else '；可以 --report 了'))


def q(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * len(s)))]


def frac(a):
    return 100.0 * (a + 1) / 1024


def qs(xs, f='%.1f%%'):
    if not xs:
        return '—'
    return ' / '.join(f % q(xs, p) for p in (.1, .25, .5, .75, .9))


def pc(a, b):
    return '%d%%' % round(100.0 * a / b) if b else '—'


def report():
    files = sorted(f for f in os.listdir(CACHE) if f.endswith('.json'))
    data = []
    for f in files:
        r = json.load(open(os.path.join(CACHE, f), encoding='utf8'))
        if r:
            data.append(r)
    nrep = len(data)
    stub = [r['mid'] for r in data if r['ticks'] < 600]
    data = [r for r in data if r['ticks'] >= 600 and r['players']['ours'] > 0]
    print('# 发现集里别的真人怎么下指令（bundle_humans.py）：包目录 %d 个，有录像的 %d 局；录像不到 600 拍的 %d 局不计入（%s）；计入 %d 局（和 bundle_cmdstream.py 同一批）' % (
        len(files), nrep, len(stub), '、'.join(stub), len(data)))
    print('#   注意：c110 的局里有录像没录到终局的（见 bundle_cmdstream.txt 开头的清单），后段的条数只算录到的那一段')
    for g, lab in GROUPS:
        print('#   %s：%d 个号（%d 局里有）' % (lab, sum(r['players'][g] for r in data), sum(1 for r in data if r['players'][g])))
    print('# 比例都是「落地那一拍余额的百分之几」；分位数的顺序是 P10 / P25 / P50 / P75 / P90')
    for g, lab in GROUPS:
        rows = [(r['mid'], x) for r in data for x in r['rows'] if x[0] == g]
        if not rows:
            continue
        print()
        print('## %s' % lab)
        # ATK
        print('ATK 陆攻（按落地拍分段）：')
        for lo, hi, pl in PH:
            a = [x for _, x in rows if x[3] == 1 and lo <= x[2] < hi]
            if not a:
                continue
            c = collections.Counter(x[5] for x in a)
            print('  %-10s %6d 条；目标 无主地 %s、内置 AI %s、真人 %s；比例 %s；比例 ≥1000/1024 的 %d 条（%s）；≤12/1024 的 %d 条（%s）' % (
                pl, len(a), pc(c['N'], len(a)), pc(c['A'], len(a)), pc(c['H'], len(a)), qs([frac(x[4]) for x in a]),
                sum(x[4] >= 1000 for x in a), pc(sum(x[4] >= 1000 for x in a), len(a)),
                sum(x[4] <= 12 for x in a), pc(sum(x[4] <= 12 for x in a), len(a))))
        # 按目标类的比例
        print('  按目标类的比例（全程）：' + '；'.join('%s %d 条 %s' % (nm, len(v), qs(v)) for k, nm in (('N', '无主地'), ('A', '内置 AI'), ('H', '真人'))
                                           for v in [[frac(x[4]) for _, x in rows if x[3] == 1 and x[5] == k]]))
        # HIT
        print('HIT 打真人的陆攻（按落地拍分段）：')
        for lo, hi, pl in PH:
            a = [(m, x) for m, x in rows if x[3] == 1 and x[5] == 'H' and lo <= x[2] < hi]
            if not a:
                continue
            per = collections.defaultdict(list)
            for m, x in a:
                per[(m, x[1])].append(x[2])
            meds = []
            for k, ts in per.items():
                ts = sorted(set(ts))
                gaps = [b_ - a_ for a_, b_ in zip(ts, ts[1:])]
                if len(gaps) >= 2:
                    meds.append(q(gaps, .5))
            sizes = [frac(x[4]) for _, x in a]
            print('  %-10s %6d 条（%d 个号）；比例 %s；≥5%% 的 %s、≥10%% 的 %s、≥20%% 的 %s、≥50%% 的 %s；同一个号相邻两次隔的拍数（每号取中位，%d 个号）%s' % (
                pl, len(a), len(per), qs(sizes), pc(sum(s >= 5 for s in sizes), len(sizes)), pc(sum(s >= 10 for s in sizes), len(sizes)),
                pc(sum(s >= 20 for s in sizes), len(sizes)), pc(sum(s >= 50 for s in sizes), len(sizes)), len(meds), qs(meds, '%d')))
        # 每号打真人的条数与目标数
        per = collections.defaultdict(list)
        for m, x in rows:
            if x[3] == 1 and x[5] == 'H':
                per[(m, x[1])].append(x[6])
        if per:
            n_t = [len(set(v)) for v in per.values()]
            top = [max(collections.Counter(v).values()) / float(len(v)) for v in per.values() if len(v) >= 5]
            print('  打过真人的号 %d 个：每号打过的真人数 %s；打过 ≥5 条的 %d 个号里，打得最多的那个目标占 %s' % (
                len(per), qs(n_t, '%d'), len(top), qs([100 * t for t in top], '%.0f%%')))
        # DON
        print('DON 捐款（按落地拍分段；录像里只有指令，看不到被没被配额拒掉）：')
        for lo, hi, pl in PH:
            a = [(m, x) for m, x in rows if x[3] == 2 and lo <= x[2] < hi]
            if not a:
                continue
            print('  %-10s %6d 条（%d 局、%d 个号）；比例 %s；比例 ≥1000/1024 的 %d 条（%s）；≥50%% 的 %s' % (
                pl, len(a), len({m for m, _ in a}), len({(m, x[1]) for m, x in a}), qs([frac(x[4]) for _, x in a]),
                sum(x[4] >= 1000 for _, x in a), pc(sum(x[4] >= 1000 for _, x in a), len(a)),
                pc(sum(frac(x[4]) >= 50 for _, x in a), len(a))))
        late = collections.defaultdict(list)
        for m, x in rows:
            if x[3] == 2 and x[2] >= 3213:
                late[m].append(x[6])
        tops = [max(collections.Counter(v).values()) / float(len(v)) for v in late.values() if len(v) >= 5]
        nrec = [len(set(v)) for v in late.values() if len(v) >= 5]
        if tops:
            print('  3213 拍以后有 ≥5 条捐款的 %d 局：收得最多的那个号占的条数 %s；收款人数 %s' % (len(tops), qs([100 * t for t in tops], '%.0f%%'), qs(nrec, '%d')))
        # BOAT
        print('BOAT 船（按落地拍分段）：')
        for lo, hi, pl in PH:
            a = [(m, x) for m, x in rows if x[3] == 3 and lo <= x[2] < hi]
            if not a:
                continue
            print('  %-10s %6d 条（%d 局、%d 个号）；比例 %s；比例 <32/1024（不够船费）的 %d 条（%s）' % (
                pl, len(a), len({m for m, _ in a}), len({(m, x[1]) for m, x in a}), qs([frac(x[4]) for _, x in a]),
                sum(x[4] < 32 for _, x in a), pc(sum(x[4] < 32 for _, x in a), len(a))))
        # RATE
        per = collections.Counter((m, x[1]) for m, x in rows)
        nplay = sum(r['players'][g] for r in data)
        zero = nplay - len(per)
        cnts = list(per.values()) + [0] * zero
        boats = {(m, x[1]) for m, x in rows if x[3] == 3}
        dons = {(m, x[1]) for m, x in rows if x[3] == 2}
        hits = {(m, x[1]) for m, x in rows if x[3] == 1 and x[5] == 'H'}
        print('RATE 每号落地的指令条数（陆攻 + 捐款 + 船）：%s；一条都没有的 %d 个号（%s）；发过船的 %d 个号（%s）、捐过款的 %d 个号（%s）、打过真人的 %d 个号（%s）' % (
            qs(cnts, '%d'), zero, pc(zero, nplay), len(boats), pc(len(boats), nplay), len(dons), pc(len(dons), nplay), len(hits), pc(len(hits), nplay)))


def main():
    if '--report' in sys.argv:
        report()
    else:
        build()


if __name__ == '__main__':
    main()
