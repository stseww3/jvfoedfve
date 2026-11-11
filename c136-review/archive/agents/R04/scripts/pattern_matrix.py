#!/usr/bin/env python3
# pattern_matrix.py — 把 R04 的全部复盘（reviews/*.json）并排：对局一览表 + 「模式 × 对局」矩阵。
# 只读 reviews/*.json 和 scripts/patterns_r04.json，不重放、不读对局包。
# 用法：python3 scripts/pattern_matrix.py [--md]
#   --md  输出 markdown 表（给 reports/CROSS-MATCH-SUMMARY.md 用）；不带就是对齐的纯文本。
# 口径：
#   · 一局里同一个模式可以有多条决策；格子里写 判定字母 + 条数（E=错 G=对 U=不明），例 E2G1。
#   · 「出现的局数」= 这个模式在多少局的决策表里出现过；「判错的局数」= 其中至少一条判为错的局数。
#   · 占地 / 密度取各局 timeline 里离 630、1530、3060 拍最近的那个点（相差 >120 拍的不取）。
#   · 真人位 = 录像里登记的真人位；到场 = 出生了的真人（goodLand.humansPresent）；人头占比 = 我方号 ÷ 到场；队数 = 录像里的队数 / 对局卡 actualTeams；
#     基准胜率 = context.baselineWinRate（1 ÷ 录像里的队数）；出局 / 离场 = outcome.botsDead / botsLeft 的个数。
import sys, os, json, glob, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORDER = ['A013', 'A015', 'A022', 'A029', 'A038', 'A047', 'A073', 'A078', 'A081', 'A083', 'A086', 'A099', 'B034']
LET = {'error': 'E', 'good': 'G', 'unclear': 'U'}


def near(tl, t, tol=120):
    best = None
    for p in tl:
        if abs(p['t'] - t) <= tol and (best is None or abs(p['t'] - t) < abs(best['t'] - t)):
            best = p
    return best


def main():
    md = '--md' in sys.argv
    revs = {}
    for fp in glob.glob(os.path.join(ROOT, 'reviews', '*.json')):
        d = json.load(open(fp, encoding='utf8'))
        revs[d['matchId']] = d
    mids = [m for m in ORDER if m in revs] + sorted(m for m in revs if m not in ORDER)
    pats = json.load(open(os.path.join(HERE, 'patterns_r04.json'), encoding='utf8'))

    # ---------- 1 对局一览 ----------
    head = ['局', '版本', '真人位', '到场', '队数（录像/对局卡）', '我方号', '人头占比（到场）', '基准胜率', '结果', '分型', '我方占地峰值', '录像末拍', '出局 / 离场', '首个出局拍', '630 拍占地', '1530 拍占地', '1530 拍密度', '3060 拍占地', '决策 错/对/不明']
    rows = []
    for m in mids:
        d = revs[m]
        c, o = d['context'], d['outcome']
        tl = d['timeline']
        ver = c['strategyVersion'].split('（')[0]
        humans = c.get('humans')
        ours = c.get('ourBots')
        deaths = [x for x in d.get('deaths', [])]
        ourdead = o.get('botsDead')
        left = len(o.get('botsLeft') or [])
        # deaths 里先列本局本房间出局的号（outcome.botsDead 个），后面才是别的房间 / 掉线号：首个出局拍只看前者
        dts = sorted(x['t'] for x in deaths[:ourdead or 0] if isinstance(x.get('t'), (int, float)))
        p630, p1530, p3060 = near(tl, 630), near(tl, 1530), near(tl, 3060)
        v = collections.Counter(x['verdict'] for x in d['decisions'])
        present = (d.get('goodLand') or {}).get('humansPresent')
        base = c.get('baselineWinRate')
        rows.append([m, ver, humans, present if present is not None else '—', '%s/%s' % (c.get('actualTeams'), c.get('cardActualTeams')), ours,
                     ('%.0f%%' % (100.0 * ours / present)) if present else '—', ('%.0f%%' % (100.0 * base)) if base else '—', o['result'], d.get('lossArchetype') or '—',
                     ('%.1f%%' % o['squadPeakSharePct']) if o.get('squadPeakSharePct') is not None else '—', o.get('endTick'),
                     '%s / %s' % (ourdead, left), dts[0] if dts else '—',
                     ('%.1f%%' % p630['squadSharePct']) if p630 else '—', ('%.1f%%' % p1530['squadSharePct']) if p1530 else '—',
                     ('%.1f' % p1530['squadDens']) if p1530 else '—', ('%.1f%%' % p3060['squadSharePct']) if p3060 else '—',
                     '%d/%d/%d' % (v['error'], v['good'], v['unclear'])])
    print('## 1 对局一览（%d 局）' % len(mids))
    table(head, rows, md)

    # ---------- 2 模式 × 对局 ----------
    cell = collections.defaultdict(lambda: collections.Counter())
    for m in mids:
        for x in revs[m]['decisions']:
            cell[(x['patternId'], m)][LET[x['verdict']]] += 1
    pids = sorted({k[0] for k in cell})
    stat = {}
    for p in pids:
        nm = sum(1 for m in mids if cell.get((p, m)))
        ne = sum(1 for m in mids if cell.get((p, m), {}).get('E'))
        ng = sum(1 for m in mids if cell.get((p, m), {}).get('G'))
        tot = collections.Counter()
        for m in mids:
            tot.update(cell.get((p, m), {}))
        stat[p] = (nm, ne, ng, tot)
    pids.sort(key=lambda p: (-stat[p][1], -stat[p][0], p))
    print()
    print('## 2 模式 × 对局（%d 个模式；按「判错的局数」排）' % len(pids))
    head = ['模式', '出现局数', '判错局数', '判对局数', '决策 E/G/U'] + mids
    rows = []
    for p in pids:
        nm, ne, ng, tot = stat[p]
        r = [p, nm, ne, ng, '%d/%d/%d' % (tot['E'], tot['G'], tot['U'])]
        for m in mids:
            c = cell.get((p, m))
            r.append(''.join('%s%s' % (k, c[k] if c[k] > 1 else '') for k in 'EGU' if c.get(k)) if c else ('' if md else '·'))
        rows.append(r)
    table(head, rows, md)

    # ---------- 3 模式的名字（出现 ≥2 局的） ----------
    print()
    print('## 3 出现在 ≥2 局的模式：名字 / 局')
    for p in pids:
        nm, ne, ng, tot = stat[p]
        if nm < 2:
            continue
        name = pats.get(p, {}).get('name', '（patterns_r04.json 里没有这个编号）')
        print('- `%s`（%d 局，判错 %d 局）%s —— %s' % (p, nm, ne, name, '、'.join(
            '%s:%s' % (m, ''.join('%s%s' % (k, cell[(p, m)][k] if cell[(p, m)][k] > 1 else '') for k in 'EGU' if cell[(p, m)].get(k))) for m in mids if cell.get((p, m)))))
    print()
    print('## 4 只出现在 1 局的模式')
    print('、'.join('`%s`（%s）' % (p, next(m for m in mids if cell.get((p, m)))) for p in pids if stat[p][0] == 1))
    print()
    tot = collections.Counter()
    for m in mids:
        tot.update(x['verdict'] for x in revs[m]['decisions'])
    print('合计：%d 局 %d 条决策：错 %d、对 %d、不明 %d；用到的模式 %d 个（模式表共 %d 个）' % (
        len(mids), sum(tot.values()), tot['error'], tot['good'], tot['unclear'], len(pids), len(pats)))
    unused = [p for p in pats if p not in stat]
    if unused:
        print('模式表里有、决策表没用到的：' + '、'.join(unused))
    missing = [p for p in pids if p not in pats]
    if missing:
        print('决策表用到、模式表里没有的：' + '、'.join(missing))


def table(head, rows, md):
    rows = [[('' if v is None else str(v)) for v in r] for r in rows]
    if md:
        print('| ' + ' | '.join(head) + ' |')
        print('| ' + ' | '.join(':--' if i == 0 else '--:' for i in range(len(head))) + ' |')
        for r in rows:
            print('| ' + ' | '.join(r) + ' |')
        return

    def w(s):
        return sum(2 if ord(ch) > 0x2e80 else 1 for ch in s)
    wid = [max(w(head[i]), max((w(r[i]) for r in rows), default=0)) for i in range(len(head))]
    for r in [head] + rows:
        print('  '.join(r[i] + ' ' * (wid[i] - w(r[i])) for i in range(len(head))))


if __name__ == '__main__':
    main()
