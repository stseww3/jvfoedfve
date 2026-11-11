#!/usr/bin/env python3
# 没落地的调度，用真引擎里的配额账重新判一遍「为什么没落地」。
# 用法：python3 scripts/quota_truth.py <局号> [--list N] [--all] [--ours id,id,…]
#   --list N 列出前 N 条「仍解释不了」的；--all 把每一条没落地的调度都列出来（拍、谁给谁、要几点、已用/上限、判定）
# 背景：donation_ledger.py（里程碑 1 的工具）是从录像里的捐款指令按估算金额累加配额点数的，
#   漏了船移交占的点数，金额也是估的，所以会多出一批「公式解释不了」。
#   真引擎重放（engine_truth.cjs）在每笔落地的捐款和每次船移交上都记了收款人配额的 已用点数 / 上限，
#   本脚本用它当真值：
#     已用点数 = 该收款人在这一拍之前最后一次入账（捐款指令或船移交）之后的 used；
#     上限     = 15 起步，每逢 t%100==99 加 4 / 6 / 8 / 10（t<1071 / <2142 / <3213 / 之后）；
#     这一笔要的点数 = t≥3213 时 4 + floor(到账兵/收款人领土)，之前 2 + floor(100×到账兵 /(倍数×(1+陆地/300)))；
#     到账兵 = min(余额×(比例+1)/1024, 余额−税)，再受收款人 150×领土 的余量限制；余额、领土取真引擎该拍的值。
# 判定：收款方到顶（余量 <1）/ 单笔就超上限 / 累计用满 / 仍解释不了（多半是指令根本没发出去：客户端落后、同拍只发一条等）。
import sys, os, csv, json, math, collections, bisect
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def iV(a, b):
    return int(math.floor((a + 0.5) / b))


def cap_at(t):
    cap = 15
    for k in range(99, t, 100):
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
    return cap


def cost_of(t, v, land, terr_q):
    if t >= 3213:
        return 4 + iV(100 * v, max(1, min(100 * terr_q, 10 ** 9)))
    uv = 1 + iV(land, 300)
    m = 1 if t < 357 else 4 if t < 714 else 10 if t < 1071 else 30 if t < 2142 else 100
    return 2 + iV(100 * v, m * uv)


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
    M = Match(mid, ours)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta = json.load(open(os.path.join(here, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    land = meta['info']['ke']
    # 真值配额时间线：收款人 -> [(拍, used 之后)]
    tl = collections.defaultdict(list)
    capchk = [0, 0]
    with open(os.path.join(here, 'tmp', 'truth', mid, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['id'] == '2' and r['used1'] not in ('', None) and r['q'] not in ('', None):
                t = int(r['t']); q = int(r['q'])
                tl[q].append((t, int(r['used1'])))
                if r['cap'] not in ('', None) and t < 4284:
                    capchk[0 if int(r['cap']) == cap_at(t) else 1] += 1
    for (t, kind, pl, x, y, det) in M.ev:
        if kind == 'land' and 'give:' in det:
            f = det.split('|', 1)[1].split(':')
            if len(f) >= 7:
                tl[int(f[1])].append((t, int(f[5])))
    for q in tl:
        tl[q].sort()

    def used_at(q, t):
        arr = tl.get(q, [])
        i = bisect.bisect_left(arr, (t, -1)) - 1
        return arr[i][1] if i >= 0 else 0
    path = os.path.join(here, 'out', 'ledger', mid + '.donations.tsv')
    rows = [r for r in csv.DictReader(open(path, encoding='utf8'), delimiter='\t') if r['t'] != '' and r['donor'] not in ('', 'None')]
    mine = [r for r in rows if r['kind'] != '(日志无此行)']
    rej = [r for r in mine if r['accepted'] != 'True']
    bands = [(0, 2142, '<2142'), (2142, 3213, '2142~3212'), (3213, 4284, '3213~4283'), (4284, 10 ** 9, '≥4284')]
    out = collections.defaultdict(collections.Counter)
    ex = []
    allrej = []
    slack_un = []
    for r in rej:
        t = int(r['t']); te = int(r['execTick']); q = int(r['q']); p = int(r['donor']); pct = int(r['pct'])
        sp = M.state[M.at(te)].get(p); sq = M.state[M.at(te)].get(q)
        band = next(b[2] for b in bands if b[0] <= t < b[1])
        if not sp or not sq or sq[0] <= 0:
            out[band]['收款人或捐款人已不在场'] += 1
            continue
        B = sp[1]; fee = iV(64 * B, 1024)
        v0 = min(iV(B * (pct + 1), 1024), B - fee)
        room = max(0, min(150 * sq[0] - sq[1], 15 * 10 ** 8 - sq[1]))
        v = min(v0, room)
        cap = cap_at(te); used = used_at(q, te)
        if v < 1:
            why = '收款方到顶'
        elif te >= 4284:
            why = '仍解释不了（配额已解除）'
        else:
            c = cost_of(te, v, land, sq[0])
            if c > cap:
                why = '单笔就超上限'
            elif used + c > cap:
                why = '累计用满'
            else:
                why = '仍解释不了'
                slack_un.append(cap - used - c)
                if len(ex) < nlist:
                    ex.append('    拍 %d %s→%s 比例 %d 余额 %s 到账应为 %s，要 %d 点；真引擎已用 %d / 上限 %d（还剩 %d）；旧表记的已用 %s' % (
                        t, r['bot'], r['qname'], pct, fmt(B), fmt(v), c, used, cap, cap - used, r['usedBefore']))
        out[band][why] += 1
        if '--all' in a:
            cc = cost_of(te, v, land, sq[0]) if (v >= 1 and te < 4284) else 0
            allrej.append('    拍 %d（落地拍 %d）%s→%s 比例 %d/1024 余额 %s 应到账 %s，要 %d 点；收款人已用 %d / 上限 %d ⇒ %s' % (
                t, te, r['bot'], r['qname'], pct, fmt(B), fmt(v), cc, used, cap, why))
    print('%s：我方调度 %d 次，落地 %d，没落地 %d。真引擎配额上限与本脚本公式一致 %d 次、不一致 %d 次。' % (
        mid, len(mine), len(mine) - len(rej), len(rej), capchk[0], capchk[1]))
    tot = collections.Counter()
    for b in bands:
        c = out.get(b[2])
        n_all = sum(1 for r in mine if b[0] <= int(r['t']) < b[1])
        n_rej = sum(c.values()) if c else 0
        if n_all:
            print('  %-10s 调度 %3d 次，没落地 %3d：%s' % (b[2], n_all, n_rej, '，'.join('%s %d' % kv for kv in c.most_common()) if c else '—'))
        if c:
            tot.update(c)
    n = sum(tot.values())
    if n:
        print('  合计没落地 %d：%s' % (n, '，'.join('%s %d（%.0f%%）' % (k, v, 100.0 * v / n) for k, v in tot.most_common())))
    if slack_un:
        s = sorted(slack_un)
        print('  「仍解释不了」的 %d 次里，按真引擎的账还剩的点数：中位 %d，最小 %d，最大 %d' % (len(s), s[len(s) // 2], s[0], s[-1]))
    for line in ex:
        print(line)
    if allrej:
        print('  没落地的调度逐条（--all）：')
        for line in allrej:
            print(line)
    # 每个收款人配额用到了哪
    for q in sorted(tl, key=lambda q: -len(tl[q])):
        if q not in M.ours:
            continue
        arr = [x for x in tl[q] if x[0] < 4284]
        if not arr:
            continue
        print('  收款人 %-7s 4284 拍前入账 %d 次（捐款指令 + 船移交），最后一次在拍 %d，已用 %d 点 / 当时上限 %d' % (
            M.nm(q), len(arr), arr[-1][0], arr[-1][1], cap_at(arr[-1][0])))


if __name__ == '__main__':
    main()
