#!/usr/bin/env python3
# m7_totals.py — 把 out/m7/*.txt（m7_collect.py 收来的各单局脚本汇总行）排成跨局的表并加总，写到 out/m7/TABLES.md。
# 用法：python3 scripts/m7_totals.py            （先把 m7_collect.py 的各个名字跑一遍）
# 不算新数：只解析那些汇总行里的数字，再按列相加。A073 是 1v1（对手就是自己人），合计行分「13 局」和「去掉 A073 的 12 局」两种。
import sys, os, re, collections
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'out', 'm7')
MIDS = ['A013', 'A015', 'A022', 'A029', 'A038', 'A047', 'A073', 'A078', 'A081', 'A083', 'A086', 'A099', 'B034']


def num(s):
    s = s.strip().replace(',', '').replace(' ', '')
    m = re.match(r'^([+-]?\d+(?:\.\d+)?)(万|k|M)?$', s)
    if not m:
        raise ValueError(s)
    v = float(m.group(1))
    return int(round(v * {'万': 1e4, 'k': 1e3, 'M': 1e6, None: 1}[m.group(2)]))


def wan(v):
    return '%.1f 万' % (v / 1e4)


def load(name):
    out = collections.defaultdict(list)
    fp = os.path.join(D, name + '.txt')
    if not os.path.exists(fp):
        return out
    for ln in open(fp, encoding='utf8'):
        if ln.startswith('#'):
            continue
        m, _, rest = ln.rstrip('\n').partition('  ')
        out[m].append(rest)
    return out


def table(title, head, rows, note=None):
    print('### ' + title)
    print()
    print('| ' + ' | '.join(head) + ' |')
    print('|' + '|'.join([' :-- '] + [' --: '] * (len(head) - 1)) + '|')
    for r in rows:
        print('| ' + ' | '.join(str(x) for x in r) + ' |')
    if note:
        print()
        print(note)
    print()


def sums(rows, cols, skip=('A073',)):
    a = [sum(r[c] for r in rows) for c in cols]
    b = [sum(r[c] for r in rows if r[0] not in skip) for c in cols]
    return a, b


def main():
    print('# R04 十三局跨局合计表（由 scripts/m7_totals.py 从 out/m7/*.txt 排出来；每个数都是对应单局脚本印的）')
    print()

    # ---- 1 floor_bind ----
    fb = load('floor_bind')
    rows = []
    for m in MIDS:
        for ln in fb.get(m, []):
            g = re.match(r'合计\s+(\d+) \| (\d+)（\d+%） \| (\d+)（\d+%） \| (\d+)（\d+%） \| (\d+)（\d+%） \| (\d+)（\d+%）\[(\d+)/(\d+)/(\d+)/(\d+)\] \| (\d+)（\d+%） \| (\d+)', ln)
            if g:
                rows.append([m] + [int(x) for x in g.groups()])
    if rows:
        a, b = sums(rows, range(1, 13))
        body = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[12]] for r in rows]
        body.append(['13 局合计'] + [a[i] for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 11)])
        body.append(['去掉 A073'] + [b[i] for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 11)])
        table('1 核心期前 [630,1500) 贴着内置 AI 的决策拍：底线被哪一项顶住（floor_bind_tally.py）',
              ['局', '决策拍', '出手', '没有 AI 邻居', '项 1', '项 2（dpKeep）', '项 3（safeFinite）', '其中参照编队号', '参照同队真人', '参照外队真人', '底线没卡住也没出手'], body,
              '项 3 占全部决策拍：13 局 %.0f%%；其中参照对象是我方编队号的占 %.0f%%。' % (100.0 * a[5] / a[0], 100.0 * a[6] / a[5]))

    # ---- 2 same_tick ----
    st = load('same_tick')
    rows = []
    for m in MIDS:
        n = land = miss = unk = late_n = late_tr = 0
        for ln in st.get(m, []):
            g = re.search(r'同一个决策拍出 ≥2 条的有 (\d+) 个号·拍', ln)
            if g:
                n = int(g.group(1))
            g = re.search(r'组内第 2 条：落地 (\d+)，没落地 (\d+)，分不清 (\d+)', ln)
            if g:
                land, miss, unk = (int(x) for x in g.groups())
                for band, c, tr in re.findall(r'(<630|630~1499|1500~2999|3000~4283|≥4284) (\d+) 次 (\d+) 兵', ln):
                    if band not in ('<630', '630~1499'):
                        late_n += int(c)
                        late_tr += int(tr)
        rows.append([m, n, land, miss, unk, late_n, late_tr])
    a, b = sums(rows, range(1, 7))
    body = [[r[0], r[1], r[2], r[3], r[4], r[5], wan(r[6])] for r in rows]
    body.append(['13 局合计', a[0], a[1], a[2], a[3], a[4], wan(a[5])])
    table('2 同一个决策拍出两条指令，第 2 条有没有落地（same_tick.py）',
          ['局', '同拍 ≥2 条的号·拍', '第 2 条落地', '确定没落地', '分不清', '1500 拍以后确定没落地', '这些想出的兵'], body)

    # ---- 3 blind_reorders ----
    br = load('blind_reorders')
    rows = []
    for m in MIDS:
        tot_n = tot_tr = k = rn = rtr = share = None
        first = whole = mx = None
        for ln in br.get(m, []):
            g = re.search(r'不含没产生进攻的）(\d+) 条 ([\d.]+万|\d+) 兵', ln)
            if g:
                tot_n, tot_tr = int(g.group(1)), num(g.group(2))
            g = re.search(r'关闸串（第一条一生效策略就停手）(\d+) 个，其中的重复单（第 2 条起）(\d+) 条 ([\d.]+万|\d+) 兵，占全部打人/AI 出征兵的 (\d+)%', ln)
            if g:
                k, rn, rtr, share = int(g.group(1)), int(g.group(2)), num(g.group(3)), int(g.group(4))
            g = re.search(r'单发 (\d+) 个，出兵占余额的中位 (\d+)%；连发（≥2 条）(\d+) 个，合计 ([\d.]+万|\d+) 兵，每串出兵占余额的中位 (\d+)%、最大 (\d+)%', ln)
            if g:
                first, whole, mx = int(g.group(2)), int(g.group(5)), int(g.group(6))
        rows.append([m, tot_n, tot_tr, k, rn, rtr, share, first, whole, mx])
    a, b = sums(rows, (1, 2, 3, 4, 5))
    body = [[r[0], r[1], wan(r[2]), r[3], r[4], wan(r[5]), '%d%%' % r[6], '%s%%' % r[7], '%s%%' % r[8], '%s%%' % r[9]] for r in rows]
    body.append(['13 局合计', a[0], wan(a[1]), a[2], a[3], wan(a[4]), '%.0f%%' % (100.0 * a[4] / a[1]), '', '', ''])
    body.append(['去掉 A073', b[0], wan(b[1]), b[2], b[3], wan(b[4]), '%.0f%%' % (100.0 * b[4] / b[1]), '', '', ''])
    table('3 上一条没生效又下一条的重复单（blind_reorders.py，按影子策略分出的关闸串）',
          ['局', '落地的打人 / AI 陆攻', '出征兵', '关闸串', '重复单', '重复单的兵', '占出征兵', '串首余额 ≥10 万的正常串：单发的出兵占余额中位', '连发的整串占余额中位', '连发的整串最大'], body)

    # ---- 4 nfs ----
    nf = load('nfs_blocked')
    rows = []
    for m in MIDS:
        for ln in nf.get(m, []):
            g = re.search(r'(\d+)/(\d+) 个号上过锁（上锁拍 (\d+)~(\d+)）；被守卫拦掉的出兵 (\d+) 次，想出的兵合计 ([\d.]+) 万', ln)
            if g:
                rows.append([m, int(g.group(1)), int(g.group(2)), '%s~%s' % (g.group(3), g.group(4)), int(g.group(5)), int(round(float(g.group(6)) * 1e4))])
    a, b = sums(rows, (1, 2, 4, 5))
    body = [[r[0], '%d / %d' % (r[1], r[2]), r[3], r[4], wan(r[5])] for r in rows]
    body.append(['13 局合计', '%d / %d' % (a[0], a[1]), '', a[2], wan(a[3])])
    body.append(['去掉 A073', '%d / %d' % (b[0], b[1]), '', b[2], wan(b[3])])
    table('4 isNoFullSend 上锁与被守卫拦掉的出兵（nfs_blocked.py；影子策略里的状态）', ['局', '上过锁的号 / 我方号', '上锁拍', '被拦次数', '想出的兵（同一笔每 5 拍重下，有重复）'], body)

    # ---- 5 quota ----
    qt = load('quota_truth')
    bands = ['<2142', '2142~3212', '3213~4283', '≥4284']
    acc = {bd: [0, 0, collections.Counter()] for bd in bands}
    rows = []
    for m in MIDS:
        per = {bd: (0, 0) for bd in bands}
        for ln in qt.get(m, []):
            g = re.match(r'(<2142|2142~3212|3213~4283|≥4284)\s+调度\s+(\d+) 次，没落地\s+(\d+)：(.*)', ln)
            if g:
                bd, n, miss = g.group(1), int(g.group(2)), int(g.group(3))
                per[bd] = (n, miss)
                acc[bd][0] += n
                acc[bd][1] += miss
                for why, c in re.findall(r'([^，\d—]+?) (\d+)(?:，|$)', g.group(4)):
                    acc[bd][2][why.strip()] += int(c)
        if m in qt and not qt[m][0].startswith('（不适用'):
            rows.append([m] + ['%d → %d' % (per[bd][0], per[bd][0] - per[bd][1]) for bd in bands])
    rows.append(['合计'] + ['%d → %d（%.0f%%）' % (acc[bd][0], acc[bd][0] - acc[bd][1], 100.0 * (acc[bd][0] - acc[bd][1]) / acc[bd][0] if acc[bd][0] else 0) for bd in bands])
    rows.append(['没落地的原因'] + ['；'.join('%s %d' % kv for kv in acc[bd][2].most_common()) or '—' for bd in bands])
    table('5 调度（捐款）发出 → 落地，按反喂养配额的四个档（quota_truth.py；没落地的用真引擎的配额账重判）', ['局'] + ['%s 拍' % bd for bd in bands], rows)

    # ---- 6 hollow ----
    hr = load('hollow_rear')
    rows = []
    for m in MIDS:
        v = {}
        for ln in hr.get(m, []):
            g = re.match(r'按 (NEW-DN-HOLLOWREAR|NEW-DF-SEAFLANK) 的口径（.*?(400|700) 拍内没地）：(\d+) 个号', ln)
            if g:
                v[(g.group(1), g.group(2))] = int(g.group(3))
        if v:
            rows.append([m, v.get(('NEW-DN-HOLLOWREAR', '400'), 0), v.get(('NEW-DN-HOLLOWREAR', '700'), 0), v.get(('NEW-DF-SEAFLANK', '400'), 0), v.get(('NEW-DF-SEAFLANK', '700'), 0)])
    a, b = sums(rows, (1, 2, 3, 4))
    rows.append(['12 局合计'] + a)
    table('6 捐到三成密度后被打穿的后排号 / 被船登陆的后排号（hollow_rear.py）', ['局', '捐薄后 400 拍内没地', '放宽到 700 拍', '船登陆 400 拍内没地', '放宽到 700 拍'], rows)

    # ---- 7 boats ----
    bl = load('boat_list')
    rows = []
    for m in MIDS:
        n = load_ = fee = void_n = void_tr = fn = ffee = ln_n = ln_tr = net = low_n = low_tr = 0
        for ln in bl.get(m, []):
            g = re.match(r'合计 (\d+) 条船，载兵 ([\d.]+[kM万]?)，手续费 ([\d.]+[kM万]?)。', ln)
            if g:
                n, load_, fee = int(g.group(1)), num(g.group(2)), num(g.group(3))
                g2 = re.search(r'回到自己地上作废 (\d+) 条 ([\d.]+[kM万]?) 兵', ln)
                if g2:
                    void_n, void_tr = int(g2.group(1)), num(g2.group(2))
            g = re.match(r'手续费比载兵多的船：(\d+) 条，载兵合计 ([\d.]+[kM万]?)，手续费合计 ([\d.]+[kM万]?)', ln)
            if g:
                fn, ffee = int(g.group(1)), num(g.group(3))
            g = re.match(r'登陆打敌方/AI 的 (\d+) 条：载兵 ([\d.]+[kM万]?)，到岸 ([\d.]+[kM万]?)；登陆后 300 拍从目标净得地合计 ([+-]?\d+).*?单条净得地 ≤100 的 (\d+) 条 ([\d.]+[kM万]?) 兵', ln)
            if g:
                ln_n, ln_tr, net, low_n, low_tr = int(g.group(1)), num(g.group(2)), int(g.group(4)), int(g.group(5)), num(g.group(6))
        rows.append([m, n, load_, fee, void_n, void_tr, fn, ffee, ln_n, ln_tr, net, low_n, low_tr])
    a, b = sums(rows, range(1, 13))
    body = [[r[0], r[1], wan(r[2]), wan(r[3]), '%d 条 %s' % (r[4], wan(r[5])), '%d 条 %s' % (r[6], wan(r[7])), '%d 条 %s' % (r[8], wan(r[9])), '%+d' % r[10], '%d 条 %s' % (r[11], wan(r[12]))] for r in rows]
    for lab, s in (('13 局合计', a), ('去掉 A073', b)):
        body.append([lab, s[0], wan(s[1]), wan(s[2]), '%d 条 %s' % (s[3], wan(s[4])), '%d 条 %s' % (s[5], wan(s[6])), '%d 条 %s' % (s[7], wan(s[8])), '%+d' % s[9], '%d 条 %s' % (s[10], wan(s[11]))])
    table('7 船（boat_list.py）', ['局', '船', '载兵', '船手续费', '回到自己地上作废', '手续费比载兵多的船（付的手续费）', '登陆打敌方 / AI', '登陆后 300 拍净得地', '其中单条净得 ≤100 格'], body)

    # ---- 8 fee ----
    fl = load('fee_ledger')
    rows = []
    for m in MIDS:
        for ln in fl.get(m, []):
            g = re.match(r'合计：(\d+) 条，出征 ([\d.]+[kM万]?) 兵，手续费 ([\d.]+[kM万]?)（([\d.]+)%）；出兵<手续费的指令 (\d+) 条，白付手续费 ([\d.]+[kM万]?)', ln)
            if g:
                rows.append([m, int(g.group(1)), num(g.group(2)), num(g.group(3)), int(g.group(5)), num(g.group(6))])
    a, b = sums(rows, (1, 2, 3, 4, 5))
    body = [[r[0], r[1], wan(r[2]), wan(r[3]), '%.1f%%' % (100.0 * r[3] / r[2]), r[4], wan(r[5])] for r in rows]
    for lab, s in (('13 局合计', a), ('去掉 A073', b)):
        body.append([lab, s[0], wan(s[1]), wan(s[2]), '%.1f%%' % (100.0 * s[2] / s[1]), s[3], wan(s[4])])
    table('8 陆攻手续费（fee_ledger.py；引擎按余额的 12/1024 收，与出多少兵无关）', ['局', '陆攻指令', '出征兵', '手续费', '手续费 ÷ 出征兵', '出兵 < 手续费的指令', '这些指令付的手续费'], body)

    # ---- 9 human strikes ----
    hs = load('human_strikes')
    rows = []
    for m in MIDS:
        v = dict(u=(0, 0, 0, 0), o=(0, 0, 0, 0), ob=(0, 0, 0, 0), os=(0, 0, 0, 0))
        for ln in hs.get(m, []):
            g = re.match(r'余额(不超过|超过) 100×领土(?:（over）)?：(\d+) 次，出兵 ([\d.]+万|\d+)；.*?净得地 >0 的 (\d+) 次；净得地合计 ([+-]?\d+)', ln)
            if g:
                v['u' if g.group(1) == '不超过' else 'o'] = (int(g.group(2)), num(g.group(3)), int(g.group(4)), int(g.group(5)))
            g = re.match(r'over 的出手里，出手时地(不比对方少|比对方少)的：(\d+) 次，出兵 ([\d.]+万|\d+)；随后 300 拍净得地 >0 的 (\d+) 次、<0 的 (\d+) 次', ln)
            if g:
                v['ob' if g.group(1) == '不比对方少' else 'os'] = (int(g.group(2)), num(g.group(3)), int(g.group(4)), int(g.group(5)))
        rows.append([m] + list(v['u']) + list(v['o']) + list(v['ob']) + list(v['os']))
    a, b = sums(rows, range(1, 17))
    def fmt(s):
        return [s[0], wan(s[1]), s[2], '%+d' % s[3], s[4], wan(s[5]), s[6], '%+d' % s[7], '%d 次 %s：正 %d / 负 %d' % (s[8], wan(s[9]), s[10], s[11]), '%d 次 %s：正 %d / 负 %d' % (s[12], wan(s[13]), s[14], s[15])]
    body = [[r[0]] + fmt(r[1:]) for r in rows]
    body.append(['13 局合计'] + fmt(a))
    body.append(['去掉 A073'] + fmt(b))
    note = '每万兵换的地（去掉 A073）：没过线 %.0f 格，过线 %.0f 格。过线且地不比对方少：%d 次里净得地为正 %d 次（%.0f%%）；过线且地比对方少：%d 次里为正 %d 次（%.0f%%）。' % (
        b[3] / (b[1] / 1e4), b[7] / (b[5] / 1e4), b[8], b[10], 100.0 * b[10] / b[8], b[12], b[14], 100.0 * b[14] / b[12])
    table('9 对真人的出手：过没过 100×领土（human_strikes.py；一个出兵串算一次，净得地 = 随后 300 拍从目标净流入、重叠窗口只算一次）',
          ['局', '没过线：次数', '出兵', '净得地 >0 的次数', '净得地', '过线：次数', '出兵', '净得地 >0 的次数', '净得地', '过线且地不比对方少', '过线且地比对方少'], body, note)

    # ---- 10 thin ----
    th = load('thin_after_spend')
    rows = []
    for m in MIDS:
        for ln in th.get(m, []):
            g = re.match(r'合计：自己花薄的 (\d+) 次，其中随后 300 拍内出局或丢地 ≥25% 的 (\d+) 次', ln)
            if g:
                rows.append([m, int(g.group(1)), int(g.group(2))])
    a, b = sums(rows, (1, 2))
    rows.append(['13 局合计'] + a)
    table('10 自己花兵把密度压到 20 以下，随后 300 拍的后果（thin_after_spend.py）', ['局', '自己花薄的次数', '随后 300 拍出局或丢地 ≥25%'], rows,
          '13 局合计 %d 次里 %d 次（%.0f%%）。' % (a[0], a[1], 100.0 * a[1] / a[0]))

    # ---- 11 cap ----
    ct = load('cap_time')
    rows = []
    for m in MIDS:
        for ln in ct.get(m, []):
            g = re.match(r'合计（号·拍） \| (\d+) / (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+) \| (\d+) / (\d+)', ln)
            if g:
                rows.append([m] + [int(x) for x in g.groups()])
    a, b = sums(rows, range(1, 9))
    body = [[r[0]] + ['%d / %d' % (r[i], r[i + 1]) for i in (1, 3, 5, 7)] + ['%d / %d' % (r[1] + r[3] + r[5] + r[7], r[2] + r[4] + r[6] + r[8])] for r in rows]
    body.append(['13 局合计'] + ['%d / %d' % (a[i], a[i + 1]) for i in (0, 2, 4, 6)] + ['%d / %d' % (a[0] + a[2] + a[4] + a[6], a[1] + a[3] + a[5] + a[7])])
    table('11 压在上限上的时间（cap_time.py）：密度 >100 的号·拍 / 其中密度 ≥149.5（硬上限，利息为 0）的号·拍', ['局', '(0,1500]', '(1500,3000]', '(3000,4284]', '4284 拍以后', '全场'], body)

    # ---- 12 first strike ----
    fs = load('first_strike_lag')
    rows = []
    for m in MIDS:
        for ln in fs.get(m, []):
            g = re.match(r'合计：(\d+) 对，其中落地 (\d+) 对；晚的拍数 最小 (\d+)、中位 (\d+)、最大 (\d+)', ln)
            if g:
                rows.append([m] + [int(x) for x in g.groups()])
    table('12 对真人的第一次出手：影子策略第一次想打（≥2 万兵）到录像里第一条真出兵的陆攻（first_strike_lag.py）', ['局', '（号, 目标）对数', '落地的对数', '晚的拍数：最小', '中位', '最大'], rows)

    # ---- 13 pre-human ----
    ph = load('pre_human_floor')
    rows = []
    for m in MIDS:
        for ln in ph.get(m, []):
            g = re.search(r'没出手的决策拍 (\d+) 个.*?全部决策拍 (\d+) 个', ln)
            if g:
                rows.append([m, int(g.group(1)), int(g.group(2)), '%.0f%%' % (100.0 * int(g.group(1)) / int(g.group(2)))])
            elif ln.startswith('（'):
                rows.append([m, '—', '—', ln])
    table('13 核心期前 [630,1500) 贴着真人、这一拍没出手的决策拍（pre_human_floor_tally.py）', ['局', '没出手的决策拍', '全部决策拍', '占比'], rows)

    # ---- 14 hub0007 表里能相加的行 ----
    fp = os.path.join(ROOT, 'out', 'hub0007', 'm7_table.md')
    if os.path.exists(fp):
        tsv = {}
        hdr = None
        for ln in open(fp, encoding='utf8'):
            c = ln.rstrip('\n').split('\t')
            if c[0] == '指标':
                hdr = c[1:]
            elif hdr and len(c) == len(hdr) + 1:
                tsv[c[0]] = dict(zip(hdr, c[1:]))

        def ints(cell):
            return [num(x) for x in re.findall(r'-?\d[\d,]*(?:\.\d+)?(?: ?万)?', cell.replace('（', ' ').replace('%', ' '))]

        rows = []
        for lab, cols, names in (
                ('想发 → 受理 → 落地，630~1530 拍', 3, '想发 / 受理 / 落地'),
                ('想发 → 受理 → 落地，1530~3060 拍', 3, '想发 / 受理 / 落地'),
                ('想发 → 受理 → 落地，>3060 拍', 3, '想发 / 受理 / 落地'),
                ('600~1499 拍落地时目标已出局：条 / 想出的兵 / 占瞄 AI、真人落地单', 2, '条 / 想出的兵'),
                ('600~1499 拍瞄 AI、真人的意图 → 打到原目标', 2, '意图 / 打到原目标'),
                ('清仓批 600~1499 拍：批 / 条 / 第 2 条起的兵', 3, '批 / 条 / 第 2 条起的兵'),
                ('清仓批 1500~2999 拍：批 / 条 / 第 2 条起的兵', 3, '批 / 条 / 第 2 条起的兵'),
                ('清仓批 3000+ 拍：批 / 条 / 第 2 条起的兵', 3, '批 / 条 / 第 2 条起的兵'),
                ('装满的批（8~9 条）：个数 / 后面紧跟着丢掉意图的', 2, '个数 / 后面紧跟着丢掉意图的'),
                ('不到 8 条的批：个数 / 后面紧跟着丢掉意图的', 2, '个数 / 后面紧跟着丢掉意图的'),
                ('贴着内置 AI 的号·决策拍 600~1499 拍：总数 / 出手 / 被闸门卡住', 3, '总数 / 出手 / 被闸门卡住'),
                ('贴着内置 AI 的号·决策拍 1500~2999 拍：总数 / 出手 / 被闸门卡住', 3, '总数 / 出手 / 被闸门卡住'),
                ('出生：落在最后一轮的点上 / 停在旧坐标 / 没落地 / 其他；同点对数', 5, '落在最后一轮的点上 / 停在旧坐标 / 没落地 / 其他 / 同点对数')):
            if lab not in tsv:
                continue
            tot = [0] * cols
            tot12 = [0] * cols
            for m in MIDS:
                v = ints(tsv[lab].get(m, ''))
                v = (v + [0] * cols)[:cols]
                for i in range(cols):
                    tot[i] += v[i]
                    if m != 'A073':
                        tot12[i] += v[i]
            f = lambda t: ' / '.join(wan(x) if ('兵' in names.split(' / ')[i]) else str(x) for i, x in enumerate(t))
            rows.append([lab, names, f(tot), f(tot12)])
        table('14 延迟账 / 好地账里能逐局相加的行（out/hub0007/m7_table.md 的合计；分位数、占比不能相加，不在这里）', ['行', '各格', '13 局合计', '去掉 A073'], rows)

    # ---- 19~21 hub0007 表转置成每局一行（原表一局一列，13 列太宽）----
    if os.path.exists(fp):
        def trans(title, picks, note=None):
            head = ['局'] + [short for _, short in picks]
            body = []
            for m in MIDS:
                body.append([m] + [tsv.get(lab, {}).get(m, '—').replace('　', '；') for lab, _ in picks])
            table(title, head, body, note)

        trans('19 延迟账·一：出生指令与落地延迟（每局一行；out/hub0007/m7_table.md 转置）', [
            ('协调器求解轮数 / 点位最后一次变动的轮', '求解轮数 / 点位最后变动的轮'),
            ('出生：落在最后一轮的点上 / 停在旧坐标 / 没落地 / 其他；同点对数', '落在最后一轮的点 / 停在旧点 / 没落地 / 其他；同点对数'),
            ('执行拍 − 决策拍 P50/P90/Max，0~599 拍', '延迟 P50/P90/Max：0~599'),
            ('执行拍 − 决策拍 P50/P90/Max，600~1499 拍', '600~1499'),
            ('执行拍 − 决策拍 P50/P90/Max，1500~2999 拍', '1500~2999'),
            ('执行拍 − 决策拍 P50/P90/Max，3000+ 拍', '3000+'),
            ('客户端落后最大（相对最快的队友）', '客户端相对落后最大'),
            ('慢拍行数（一次决策 ≥25 毫秒）/ 最大毫秒', '慢拍行 / 最大毫秒'),
            ('墙上时钟：报告出局时落后服务器 ≥35 拍 / ≥90 拍的号（共几个号）；最大', '出局时墙上时钟落后 ≥35 / ≥90 拍的号（共几个）；最大')])
        trans('20 延迟账·二：漏斗与两类直接损失（每局一行）', [
            ('想发 → 受理 → 落地，630~1530 拍', '想发 → 受理 → 落地：630~1530'),
            ('想发 → 受理 → 落地，1530~3060 拍', '1530~3060'),
            ('想发 → 受理 → 落地，>3060 拍', '>3060'),
            ('全局 落地 ÷ 受理', '全局落地 ÷ 受理'),
            ('600~1499 拍落地时目标已出局：条 / 想出的兵 / 占瞄 AI、真人落地单', '600~1499 落地时目标已出局：条 / 兵 / 占比'),
            ('600~1499 拍瞄 AI、真人的意图 → 打到原目标', '600~1499 意图 → 打到原目标'),
            ('重复单：条 / 兵 / 占打人和 AI 的出征兵', '重复单：条 / 兵 / 占出征兵'),
            ('清仓批 600~1499 拍：批 / 条 / 第 2 条起的兵', '清仓批 600~1499：批 / 条 / 第 2 条起的兵'),
            ('清仓批 1500~2999 拍：批 / 条 / 第 2 条起的兵', '1500~2999'),
            ('清仓批 3000+ 拍：批 / 条 / 第 2 条起的兵', '3000+'),
            ('装满的批（8~9 条）：个数 / 后面紧跟着丢掉意图的', '装满的批 / 其后丢意图的')])
        trans('21 好地账（每局一行）', [
            ('到场真人 / 我方号', '到场真人 / 我方号'),
            ('天然地盘占全图 ÷ 人头占比 = 倍数（欧氏）', '天然地盘占全图 ÷ 人头占比'),
            ('单号天然地盘中位：我方 / 其他真人', '单号天然地盘中位：我方 / 其他真人'),
            ('实际 ÷ 天然，630 拍：我方 / 其他真人', '实际 ÷ 天然 630：我方 / 其他'),
            ('实际 ÷ 天然，1500 拍：我方 / 其他真人', '1500'),
            ('实际 ÷ 天然，3000 拍：我方 / 其他真人', '3000'),
            ('630 拍身边的内置 AI：个 / 格', '630 拍身边的内置 AI：个 / 格'),
            ('这些格 1500 拍在谁手里：我方 / 同队其他真人 / 敌方真人 / 内置 AI', '这些格 1500 拍：我方 / 同队真人 / 敌方真人 / AI'),
            ('这些格 3000 拍在谁手里：我方 / 同队其他真人 / 敌方真人 / 内置 AI', '3000 拍')])
        trans('22 没抢到好地的三层归因（每局一行）', [
            ('三层归因 600~1499 拍：出生 / 策略闸门 / 迟到（对数占比）', '600~1499：出生 / 策略闸门 / 迟到'),
            ('贴着内置 AI 的号·决策拍 600~1499 拍：总数 / 出手 / 被闸门卡住', '贴着 AI 的号·决策拍：总数 / 出手 / 被闸门卡住'),
            ('三层归因 1500~2999 拍：出生 / 策略闸门 / 迟到（对数占比）', '1500~2999：出生 / 策略闸门 / 迟到'),
            ('贴着内置 AI 的号·决策拍 1500~2999 拍：总数 / 出手 / 被闸门卡住', '贴着 AI 的号·决策拍'),
            ('同上的四个折扣：出生 × 没被锁 × 受理后落地 × 到站时目标还在', '四个折扣：出生 × 没被锁 × 受理后落地 × 到站时目标还在')],
              '三层归因 = 四个折扣取对数后各自占的份额（受理后落地、到站时目标还在 两项合成「迟到」）。只是把观察到的四个比例摆在一起，不是反事实。')

    # ---- 15~18 早先的跨局脚本产物（out/*_all.txt） ----
    def lines(name):
        fp2 = os.path.join(ROOT, 'out', name)
        return [x.rstrip('\n') for x in open(fp2, encoding='utf8')] if os.path.exists(fp2) else []

    rows = []
    for ln in lines('doomed_pocket_all.txt'):
        g = re.match(r'(\w+)：压在身上的真人兵 > 1.65×余额 的时段 (\d+) 段（涉及 (\d+) 个号），其中 300 拍内出局 (\d+) 段；各段峰值合计 ([\d.]+)万，段开始时其余我方号「余额 − 88×领土」正数部分合计 ([\d.]+)万；这些段里收到的捐款合计 ([\d.]+)万', ln)
        if g:
            rows.append([g.group(1), int(g.group(2)), int(g.group(3)), int(g.group(4)), float(g.group(5)), float(g.group(6)), float(g.group(7))])
    if rows:
        a = [sum(r[i] for r in rows) for i in range(1, 7)]
        body = [[r[0], r[1], r[2], r[3], '%.1f 万' % r[4], '%.1f 万' % r[5], '%.1f 万' % r[6]] for r in rows]
        body.append(['%d 局合计' % len(rows), a[0], a[1], a[2], '%.1f 万' % a[3], '%.1f 万' % a[4], '%.1f 万' % a[5]])
        table('15 被判成弃子的时段：压在身上的真人兵 > 1.65×余额（doomed_pocket.py；B034 的 c110 没有这条规则，不在表里）',
              ['局', '时段', '涉及的号', '300 拍内出局', '各段峰值合计', '段开始时其余我方号高出 88×领土 的兵', '段内收到的捐款'], body,
              '%d 段里 %d 段（%.0f%%）300 拍内出局；段内收到的捐款是各段峰值的 %.1f%%。' % (a[0], a[2], 100.0 * a[2] / a[0], 100.0 * a[5] / a[3]))

    rows = []
    for ln in lines('allin_strikes_all.txt'):
        g = re.match(r'(\w+)：我方对真人的出兵串 (\d+) 个；全压（≥60% 余额）(\d+) 个 ([\d.]+)万 兵；其中目标 300 拍内没出局 (\d+) 个 ([\d.]+)万 兵；其中 450 拍后本号的地比出手前少或已出局（NEW-AT-PARTALLIN）(\d+) 个 ([\d.]+|0)(?:万)? 兵', ln)
        if g:
            rows.append([g.group(1), int(g.group(2)), int(g.group(3)), float(g.group(4)), int(g.group(5)), float(g.group(6)), int(g.group(7)), float(g.group(8))])
    if rows:
        def tot(rs):
            return [sum(r[i] for r in rs) for i in range(1, 8)]
        body = [[r[0], r[1], '%d 个 %.1f 万' % (r[2], r[3]), '%d 个 %.1f 万' % (r[4], r[5]), '%d 个 %.1f 万' % (r[6], r[7])] for r in rows]
        for lab, rs in (('13 局合计', rows), ('去掉 A073', [r for r in rows if r[0] != 'A073'])):
            t = tot(rs)
            body.append([lab, t[0], '%d 个 %.1f 万' % (t[1], t[2]), '%d 个 %.1f 万' % (t[3], t[4]), '%d 个 %.1f 万' % (t[5], t[6])])
        t = tot(rows)
        table('16 对真人一串出掉 ≥60% 余额的全压（allin_strikes.py）', ['局', '对真人的出兵串', '全压', '其中目标 300 拍内没出局', '其中 450 拍后本号的地比出手前少或已出局'], body,
              '13 局：全压 %d 个里目标没出局 %d 个（%.0f%%），其中 %d 个之后自己的地变少或出局。' % (t[1], t[3], 100.0 * t[3] / t[1], t[5]))

    rows = []
    for ln in lines('seal_floor_all.txt'):
        g = re.match(r'(\w+)：被封住（陆上邻居 0、无主地 0）的号·行动拍 (\d+)（(\d+) 个号）；没有海岸的 (\d+)（\d+%，其中密度 ≥100 的 (\d+)）；有海岸的 (\d+)：密度 <68（低于保底线，发不了船）(\d+)（\d+%），68~90.7（过了保底线但不够打 AI/真人的最小船量）(\d+)（\d+%），≥90.7 (\d+)（\d+%）；全队活着的号同时被封住的行动拍 (\d+)；封住期间发的船 (\d+) 条', ln)
        if g:
            rows.append([g.group(1)] + [int(x) for x in g.groups()[1:]])
    if rows:
        a = [sum(r[i] for r in rows) for i in range(1, 11)]
        rows.append(['%d 局合计' % len(rows)] + a)
        table('17 被封住的号（陆上没有非队友邻居、没有无主地）能不能发船（seal_floor.py；只跑了这 7 局）',
              ['局', '封住的号·行动拍', '号', '没有海岸', '其中密度 ≥100', '有海岸', '密度 <68（发不了船）', '68~90.7', '≥90.7', '全队同时封住的行动拍', '封住期间发的船'], rows,
              '有海岸的 %d 个行动拍里 %d 个（%.0f%%）密度低于 68。' % (a[4], a[5], 100.0 * a[5] / a[4]))

    rows = []
    mid = None
    for ln in lines('neutral_pickup_all.txt'):
        g = re.match(r'# (\w+) 捡无主地的账', ln)
        if g:
            mid = g.group(1)
        g = re.match(r'\s+合计：(\d+) 轮 (\d+) 条，出征 ([\d,]+) 兵，手续费 ([\d,]+)，捡到 ([\d,]+) 格', ln)
        if g and mid:
            rows.append([mid] + [num(x) for x in g.groups()])
    if rows:
        body = [[r[0], r[1], r[2], wan(r[3]), wan(r[4]), r[5], '%.1f' % (r[4] / r[5]) if r[5] else '—'] for r in rows]
        for lab, rs in (('13 局合计', rows), ('去掉 A073', [r for r in rows if r[0] != 'A073'])):
            t = [sum(r[i] for r in rs) for i in range(1, 6)]
            body.append([lab, t[0], t[1], wan(t[2]), wan(t[3]), t[4], '%.1f' % (t[3] / t[4])])
        table('18 3000 拍以后捡无主地（neutral_pickup.py；捡到的地 = 这一轮之后 150 拍内从无主地流到这个号的格数）', ['局', '轮', '指令', '出征兵', '手续费', '捡到的格', '每格摊的手续费'], body)


if __name__ == '__main__':
    main()
