#!/usr/bin/env python3
# bundle_join.py — 把两张全量表按局拼起来看：out/bundle_patterns.tsv（日志 / 快照侧）和 out/bundle_cmdstream.tsv（录像指令流侧）。
# 用法：python3 scripts/bundle_join.py            （先跑 bundle_patterns.py --tsv 和 bundle_cmdstream.py --tsv）
# 只做三件事：
#   1 两个互相独立的「指令成摞」信号对不对得上：日志侧的 LAG180（客户端相对落后 ≥180 拍）对 录像侧的 BATCH3 占比；
#   2 BATCH3 占比、REPEAT 占比、出生指令条数 与 1530 拍「占地 ÷ 人头」、第一个号出局拍 的秩相关（只是相关）；
#   3 按 BATCH3 占比把 squad10 的局分三档，看每档的结果。
import sys, os, csv, statistics
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, 'out', name), encoding='utf8') as f:
        return {r['mid']: r for r in csv.DictReader(f, delimiter='\t')}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def spearman(pairs):
    if len(pairs) < 8 or len({p[0] for p in pairs}) < 2 or len({p[1] for p in pairs}) < 2:
        return None
    a, b = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va, vb = sum((x - ma) ** 2 for x in a), sum((y - mb) ** 2 for y in b)
    return cov / (va * vb) ** 0.5 if va and vb else None


def main():
    P, C = load('bundle_patterns.tsv'), load('bundle_cmdstream.tsv')
    rows = []
    for mid, c in C.items():
        p = P.get(mid)
        if not p or not num(c['our_atk']):
            continue
        rows.append(dict(mid=mid, cohort=p['cohort'], ver=p['ver'], res=p['res'], rooms=int(p['rooms']), mode=p['mode'],
                         batch=100.0 * num(c['our_b3cmd']) / num(c['our_atk']),
                         rep=100.0 * num(c['our_rep']) / num(c['our_atkNN']) if num(c['our_atkNN']) else None,
                         spawn=num(c['our_spawnMedian']), lag=num(p['lagMax']), ratio=num(p['ratio1530']), first=num(p['firstDeath']),
                         slow=num(p['slow']), collapse=p['collapse'], crowd=num(p['crowd']), head=num(p['headShare']), seeded=num(p['seeded']),
                         gap=num(p['spawnGap'])))
    print('# 两张全量表拼起来（%d 局两边都有）' % len(rows))
    print('## 1 日志侧的客户端相对落后（LAG180）对 录像侧的成摞占比（BATCH3）；只算单房间、非 1v1 的局')
    for coh in ('squad10', 'squad20'):
        rs = [r for r in rows if r['cohort'] == coh and r['lag'] is not None and r['rooms'] == 1 and r['mode'] != '8']
        for lab, f in (('最大落后 0 拍', lambda r: r['lag'] == 0), ('最大落后 90 拍', lambda r: r['lag'] == 90), ('最大落后 ≥180 拍', lambda r: r['lag'] >= 180)):
            g = [r['batch'] for r in rs if f(r)]
            if g:
                print('  %s %s：%d 局，我方陆攻里落在 ≥3 条的批里的占比 中位 %.0f%%（最小 %.0f%%，最大 %.0f%%）' % (coh, lab, len(g), statistics.median(g), min(g), max(g)))
        sp = spearman([(r['lag'], r['batch']) for r in rs])
        if sp is not None:
            print('  %s 两者的秩相关：%d 局，ρ = %+.2f' % (coh, len(rs), sp))
    print('## 2 秩相关（Spearman；只是相关，不是因果）')
    for coh in ('squad10', 'squad20'):
        rs = [r for r in rows if r['cohort'] == coh]
        for xk, xl in (('batch', 'BATCH3 占比'), ('rep', 'REPEAT 占比'), ('spawn', '每号出生指令中位条数')):
            for yk, yl in (('ratio', '1530 拍占地 ÷ 人头'), ('first', '第一个号出局的拍')):
                pr = [(r[xk], r[yk]) for r in rs if r[xk] is not None and r[yk] is not None]
                sp = spearman(pr)
                if sp is not None:
                    print('  %s %s  对  %s：%d 局，ρ = %+.2f' % (coh, xl, yl, len(pr), sp))
    print('## 2b BATCH3 占比 对 1530 拍占地 ÷ 人头：扣掉别的因素之后的偏相关（squad10）')
    rs = [r for r in rows if r['cohort'] == 'squad10']
    for zk, zl in (('crowd', '房间拥挤度（真人位 ÷ 地图陆地）'), ('head', '我方号数 ÷ 真人位'), ('seeded', '真人位数'), ('gap', '出生间距 ÷ rCell')):
        tri = [(r['batch'], r['ratio'], r[zk]) for r in rs if None not in (r['batch'], r['ratio'], r[zk])]
        rxy = spearman([(a, b) for a, b, _ in tri])
        rxz = spearman([(a, c) for a, _, c in tri])
        ryz = spearman([(b, c) for _, b, c in tri])
        if None not in (rxy, rxz, ryz):
            den = ((1 - rxz ** 2) * (1 - ryz ** 2)) ** 0.5
            print('  扣掉「%s」：%d 局，偏相关 ρ = %+.2f（原始 %+.2f；BATCH3 占比与它 %+.2f，占地 ÷ 人头与它 %+.2f）' % (zl, len(tri), (rxy - rxz * ryz) / den, rxy, rxz, ryz))
    print('## 3 squad10 按 BATCH3 占比分三档')
    rs = sorted([r for r in rows if r['cohort'] == 'squad10'], key=lambda r: r['batch'])
    n = len(rs)
    for i, lab in enumerate(('低', '中', '高')):
        g = rs[i * n // 3:(i + 1) * n // 3]
        ra = [r['ratio'] for r in g if r['ratio'] is not None]
        fd = [r['first'] for r in g if r['first'] is not None]
        print('  %s（%.0f%%~%.0f%%）：%d 局，主队赢 %d 局；1530 拍占地 ÷ 人头 中位 %s（%d 局可算）；第一个号出局拍 中位 %s（%d 局有出局）；600 拍内连垮（COLLAPSE）%d 局' % (
            lab, g[0]['batch'], g[-1]['batch'], len(g), sum(1 for r in g if r['res'] == 'W'),
            ('%.2f' % statistics.median(ra)) if ra else '—', len(ra), ('%d' % statistics.median(fd)) if fd else '—', len(fd),
            sum(1 for r in g if r['collapse'] in ('1', 'True'))))


if __name__ == '__main__':
    main()
