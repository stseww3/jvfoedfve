#!/usr/bin/env python3
# pre_human_floor_tally.py — 核心期之前（t < 1500）「贴着真人没出手」的决策拍里，对真人的出兵底线是被哪一项顶住的、
# 参照对象是谁（影子策略的逐拍记录 rows.tsv 的 hbind / href / havail / hneed / htgt 列，由 shadow_diag.preHumanBind 给出）。
#
# 用法：python3 scripts/pre_human_floor_tally.py <局号> [t0 t1] [--only-human] [--list N]
#   默认拍段 [630,1500)。先要有 tmp/shadow/<局号>/rows.tsv（bash scripts/shadow_all.sh <局号>；旧的 rows.tsv 没有这几列，要重跑）。
#   --only-human  只统计「非队友邻居全是真人、没有内置 AI、没有无主地」的决策拍（window_tally.py 的「只贴真人」类）
#   --list N      另外列出 N 个样例（号、拍、余额、对目标的底线、参照对象）
#
# 口径（照抄的源码行号见 shadow_diag.mjs 的 preHumanBind）：
#   对真人目标 q 的底线 = floorFor(q, floorAt(单价))；真人且不是 food、motive 为 null 时 = preyFloor×floorAt（V13.floorFor0 L2233~2240）。
#   floorAt = floorK×min(keepCap×100×地, max(reserve×100×地×min(1, 单价/cRef), ref×邻居均兵, defenseNeed))（General.floors L819~830）。
#   defenseNeed = 对每个邻居 q0 取 kDef×max(altOf(q0).minBal − 我打它的兵, denW×(altOf(q0).minPrice−2)×k/2)（General.defenseNeed L899~913）；
#   altOf(q0) 遍历 q0 的边界上除了 q0 和我以外的所有邻居，队友也算（General.altOf L918~940）。
#   hbind：ok = 底线没卡住；def = floorAt 被 defenseNeed 顶住；res = 被 reserve 项顶住；ref = 被 ref×邻居均兵 顶住；cap = 顶到 keepCap×100×地。
#   href（hbind 为 def / cap 时）：squad = 参照的是我方编队的号；ally = 同队其他真人或同队内置 AI；enemy = 外队真人；ai = 外队内置 AI；
#     price = 取的是密度那一项（q0 别的邻居里密度最低者的密度 × 我的地）；alone = q0 没有别的邻居。
#   第二道门「一次吃到出局」（V13.amount0 L2347~2349）：真人目标、motive 为 null（没打过我、我也没到闲置线；rows 里记成 prey）时，
#     要 sendFrac×(余额 − 底线) ≥ preyKill×出局价 才出手，否则这一拍 amount = 0。出局价 hkneed = elimCost(q) + 它正在打我的兵 − 我正在打它的兵
#     （elimCost = 2×对方余额×(1 − x^1.6) + 2×对方领土×(1 − x)，x = 对方峰值领土/4 ÷ 对方领土，Strategy.elimCost L464~469）。
#     四个版本的 sendFrac 都是 0.746、preyKill 都是 1（policy_params.mjs）。
#   每个决策拍分到四类：两道门都过不了（底线卡住，且就算底线为 0 余额的 74.6% 也不够出局价）/ 只差底线（底线为 0 就够出局价）/
#     底线过了但一次吃不到出局 / 其他。另按「同一拍、同一个目标」把我方号归组：组内余额合计的 74.6% ≥ 出局价的组数（合起来够、各算各的不够）。
import sys, os, csv, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)


def fmt(n):
    n = float(n)
    a = abs(n)
    if a >= 1e7:
        return '%.1fM' % (n / 1e6)
    if a >= 1e6:
        return '%.0fk' % (n / 1e3)
    if a >= 1e4:
        return '%.1fk' % (n / 1e3)
    return '%d' % round(n)


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit('用法：python3 scripts/pre_human_floor_tally.py <局号> [t0 t1] [--only-human] [--list N]')
    mid = a[0]
    nums = [int(x) for x in a[1:] if x.lstrip('-').isdigit() and (a[a.index(x) - 1] != '--list')]
    t0, t1 = (nums[0], nums[1]) if len(nums) >= 2 else (630, 1500)
    only = '--only-human' in a
    nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
    path = os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv')
    rows = list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))
    if not rows or 'hbind' not in rows[0]:
        raise SystemExit('tmp/shadow/%s/rows.tsv 没有 hbind 列：先重跑 bash scripts/shadow_all.sh %s' % (mid, mid))
    names = {}
    try:
        from match_digest import Match
        M = Match(mid)
        names = {p: M.nm(p) for p in M.team}
        ours = set(M.ours)
    except Exception:
        M, ours = None, set()

    def nm(p):
        try:
            p = int(p)
        except Exception:
            return str(p)
        return names.get(p, ('AI#%d' % p) if (M is not None and p >= M.ku) else '#%d' % p)

    SEND_FRAC, PREY_KILL = 0.746, 1.0
    gate = collections.Counter()
    groups = collections.defaultdict(list)
    tot = collections.Counter()
    per = collections.defaultdict(collections.Counter)
    refc = collections.Counter()
    tgtc = collections.Counter()
    order = []
    samples = []
    n_all = 0
    for r in rows:
        t = int(r['t'])
        if not (t0 <= t < t1) or t >= 1500:
            continue
        n_all += 1
        nb, nAI, nHum, neut, ints = int(float(r['nb'])), int(float(r['nAI'])), int(float(r['nHum'])), int(float(r['neut'])), int(float(r['intents']))
        if ints > 0 or nHum == 0:
            continue
        if only and not (nAI == 0 and neut == 0):
            continue
        b = r['bot']
        if b not in per:
            order.append(b)
        hb = r['hbind'] or '?'
        kind = ''
        if hb in ('def', 'cap') and r['href']:
            kind = r['href'].split(':')[0]
            refc[(kind, r['href'].split(':')[1])] += 1
        key = hb + ('/' + kind if kind else '')
        tot[key] += 1
        per[b][key] += 1
        per[b]['n'] += 1
        tot['n'] += 1
        if r['htgt']:
            tgtc[r['htgt']] += 1
        bal = float(r['bal'])
        kneed = float(r['hkneed']) if r.get('hkneed') else None
        prey = r.get('hmot') == 'prey'
        if kneed is not None and prey:
            if hb != 'ok':
                g2 = '两道门都过不了' if SEND_FRAC * bal < PREY_KILL * kneed else '只差底线'
            else:
                g2 = '底线过了但一次吃不到出局' if SEND_FRAC * float(r['havail'] or 0) < PREY_KILL * kneed else '其他'
            groups[(t, r['htgt'])].append((bal, kneed, b))
        else:
            g2 = '目标打过我或没算出来' if hb != 'ok' else '其他'
        gate[g2] += 1
        if hb != 'ok' and len(samples) < 4000:
            samples.append((t, b, int(float(r['bal'])), int(float(r['havail'] or 0)), int(float(r['hneed'] or 0)), r['htgt'], key, r['href']))
    label = {'ok': '底线没卡住', 'def/squad': 'defenseNeed·参照我方编队的号', 'def/ally': 'defenseNeed·参照同队其他真人/同队AI',
             'def/enemy': 'defenseNeed·参照外队真人', 'def/ai': 'defenseNeed·参照外队内置AI', 'def/price': 'defenseNeed·密度项',
             'def/alone': 'defenseNeed·对方没有别的邻居', 'res': 'reserve 项', 'ref': 'ref×邻居均兵', 'cap': '封顶 keepCap×100×地',
             'cap/squad': '封顶·defenseNeed 参照我方编队的号', 'cap/ally': '封顶·defenseNeed 参照同队', 'cap/enemy': '封顶·defenseNeed 参照外队真人',
             'cap/ai': '封顶·defenseNeed 参照外队内置AI', 'cap/price': '封顶·defenseNeed 密度项', 'cap/alone': '封顶·对方没有别的邻居', '?': '没算出来'}
    n = tot['n']
    print('# %s 拍段 [%d,%d)：核心期前贴着真人、这一拍没出手的决策拍 %d 个%s（该拍段全部决策拍 %d 个）' % (
        mid, t0, min(t1, 1500), n, '（只算「只贴真人」的）' if only else '（含同时还贴着内置 AI / 无主地的）', n_all))
    if not n:
        return
    keys = [k for k, _ in tot.most_common() if k != 'n']
    print('对底线最低的那个真人，底线是被哪一项顶住的：' + '；'.join('%s %d（%d%%）' % (label.get(k, k), tot[k], round(100 * tot[k] / n)) for k in keys))
    sq = sum(v for k, v in tot.items() if k.endswith('/squad'))
    al = sum(v for k, v in tot.items() if k.endswith('/ally'))
    en = sum(v for k, v in tot.items() if k.endswith('/enemy'))
    blocked = n - tot['ok']
    print('被底线卡住的 %d 个里：参照对象是我方编队的号 %d（%d%%）、同队其他真人/同队AI %d、外队真人 %d' % (
        blocked, sq, round(100 * sq / max(1, blocked)), al, en))
    for b in order:
        c = per[b]
        print('  %-8s %4d 拍：%s' % (b, c['n'], '，'.join('%s %d' % (label.get(k, k), c[k]) for k in keys if c[k])))
    print('两道门（底线 / 一次吃到出局）：' + '；'.join('%s %d（%d%%）' % (k, v, round(100 * v / n)) for k, v in gate.most_common()))
    ng = len(groups)
    multi = [(k, v) for k, v in groups.items() if len(v) >= 2]
    enough = [(k, v) for k, v in multi if SEND_FRAC * sum(x[0] for x in v) >= PREY_KILL * max(x[1] for x in v)]
    solo = [(k, v) for k, v in groups.items() if any(SEND_FRAC * x[0] >= PREY_KILL * x[1] for x in v)]
    print('按「同一拍、同一个真人目标」归组 %d 组，其中 ≥2 个我方号贴着同一个目标的 %d 组；这些组里余额合计的 74.6%% ≥ 出局价的 %d 组（%d%%）；任何一个号单独的 74.6%% 余额就够出局价的 %d 组' % (
        ng, len(multi), len(enough), round(100 * len(enough) / max(1, len(multi))), len(solo)))
    if enough:
        ts = sorted(k[0] for k, _ in enough)
        byt = collections.Counter(k[1] for k, _ in enough)
        print('  合起来够的组：拍 %d~%d；目标 %s' % (ts[0], ts[-1], '；'.join('%s %d 组' % (nm(p), v) for p, v in byt.most_common(4))))
        k, v = enough[len(enough) // 2]
        print('  样例：拍 %d 目标 %s 出局价 %s；%s' % (k[0], nm(k[1]), fmt(max(x[1] for x in v)), '、'.join('%s %s' % (x[2], fmt(x[0])) for x in v)))
    top = refc.most_common(8)
    if top:
        print('参照对象（次数）：' + '；'.join('%s %d' % (nm(p), v) for (k, p), v in top))
    if tgtc:
        print('底线最低的真人目标（次数）：' + '；'.join('%s %d' % (nm(p), v) for p, v in tgtc.most_common(6)))
    if nlist and samples:
        step = max(1, len(samples) // nlist)
        print('样例（拍 号 余额 / 余额−底线 / 出手至少要的可用兵 / 目标 / 顶住的项 / 参照）：')
        for s in samples[::step][:nlist]:
            ref = s[7]
            refs = (nm(ref.split(':')[1]) if ref and ':' in ref else '')
            print('  拍 %5d %-8s 余额 %s，余额−底线 %s（要 > %s），目标 %s，%s%s' % (
                s[0], s[1], fmt(s[2]), fmt(s[3]), fmt(s[4]), nm(s[5]), label.get(s[6], s[6]), ('：' + refs) if refs else ''))


if __name__ == '__main__':
    main()
