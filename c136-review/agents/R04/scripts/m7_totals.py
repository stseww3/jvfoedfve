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


if __name__ == '__main__':
    main()
