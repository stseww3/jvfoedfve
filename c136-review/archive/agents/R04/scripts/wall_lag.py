#!/usr/bin/env python3
# wall_lag.py — 用 results.csv 里的墙上时钟量「客户端落后服务器多少拍」（不依赖录像、不依赖影子策略）。
#
# 原理：results.csv 每个号一行，记了这个号结束时（出局 / 离场 / 对局结束）客户端自己的拍数 tick，和这一行写下的墙上时间 at（毫秒）。
#   服务器每拍 56 毫秒（engine-evidence [T1]）。同一局里取 T0 = min(at − 56ms×tick)，当作「0 拍的墙上时间」；
#   每个号的落后量 = (at − T0)/56ms − tick，即它报告结束的那一刻，服务器已经比它的客户端多走了多少拍。
#   T0 取的是全局最小值，所以这是相对「报告时最跟得上的那个号」的落后量——是下限（如果连最跟得上的号也落后，大家一起被低估）。
#   拆进多个房间的局（src/tools/instance-split.tsv 的 SPLIT）按 rep=Y / rep=N 分开各取一个 T0，少于 3 个号的一组不算。
# 有 tmp/truth/<局号>/ev.tsv 时，再给：录像里的出局拍、客户端报告拍 − 出局拍、(at − T0)/56ms − 出局拍（服务器上出局之后多少拍客户端才报告）。
# 有 tmp/shadow/<局号>/intents.tsv 时，再给：这个号最后 5 条配上对的指令的「执行拍 − 决策拍」中位数，和上面的落后量对照。
#
# 用法：python3 scripts/wall_lag.py <局号> [<局号> …]         逐号列出
#       python3 scripts/wall_lag.py --all [--tsv]              全部对局包汇总（只读每局的 results.csv）：按报告拍分段的落后量分位数
# 输出：tmp/wall/<局号>.json；--all 写 tmp/wall/_all.json
import sys, os, csv, json, re, collections, datetime
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
TICK = 0.056
BANDS = [(0, 600, '0~599'), (600, 1500, '600~1499'), (1500, 3000, '1500~2999'), (3000, 4284, '3000~4283'), (4284, 10 ** 9, '≥4284')]


def band(t):
    for lo, hi, nm in BANDS:
        if lo <= t < hi:
            return nm
    return BANDS[-1][2]


def pq(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def parse_at(s):
    s = s.strip()
    if not s:
        return None
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        return datetime.datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


_SPLIT = None


def split_groups(mid):
    """返回 {bot: 组名}；没拆房间的局全部是 'one'。"""
    global _SPLIT
    if _SPLIT is None:
        _SPLIT = {}
        fp = os.path.join(DATA, 'src', 'tools', 'instance-split.tsv')
        if os.path.exists(fp):
            with open(fp, encoding='utf8') as f:
                for r in csv.DictReader(f, delimiter='\t'):
                    g = {}
                    if r.get('split') == 'SPLIT':
                        for m in re.finditer(r'\{seen=[^|]*\|rep=([YN?]):([^}]*)\}', r.get('groups') or ''):
                            for b in re.finditer(r'\s*(.+?)#\d+\[[^\]]*\]', m.group(2)):
                                g[b.group(1).strip()] = 'rep=' + m.group(1)
                    _SPLIT[r['matchId']] = g
    return _SPLIT.get(mid, {})


def load(mid):
    fp = os.path.join(DATA, 'bundles', mid, 'results.csv')
    if not os.path.exists(fp):
        return []
    grp = split_groups(mid)
    rows = []
    with open(fp, encoding='utf8') as f:
        for r in csv.DictReader(f):
            try:
                tick = int(r['tick'])
            except (ValueError, KeyError, TypeError):
                continue
            at = parse_at(r.get('at') or '')
            if at is None or tick <= 0:
                continue
            if (r.get('event') or '') == 'left':
                continue        # 离场的号这一行是事后补写的（at 不是它停下来的时刻），不能当时钟用
            rows.append(dict(bot=r['bot'], me=r.get('meId'), event=r.get('event'), result=r.get('result'), tick=tick, at=at,
                             seconds=r.get('seconds'), group=grp.get(r['bot'], 'one')))
    return rows


def lags(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[r['group']].append(r)
    out = []
    for g, v in by.items():
        if len(v) < 3:
            continue
        t0 = min(r['at'] - TICK * r['tick'] for r in v)
        for r in v:
            r = dict(r)
            r['t0'] = t0
            r['server'] = (r['at'] - t0) / TICK
            r['lag'] = r['server'] - r['tick']
            out.append(r)
    return out


def truth_deaths(mid):
    d = os.path.join(ROOT, 'tmp', 'truth', mid)
    if not os.path.exists(os.path.join(d, 'ev.tsv')):
        return None
    meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf8'))
    names = {p['p']: p['name'] for p in meta['players']}
    dead = {}
    with open(os.path.join(d, 'ev.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['kind'] == 'dead':
                dead[int(r['p'])] = int(r['t'])
    return names, dead, meta.get('lastTick')


def last_delays(mid):
    sd = os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv')
    if not os.path.exists(sd):
        return {}
    sys.path.insert(0, HERE)
    import exec_gap
    intents, cmds, _ = exec_gap.load(mid)
    pairs, _, _ = exec_gap.match(intents, cmds)
    by = collections.defaultdict(list)
    for x, c in pairs:
        by[x['bot']].append((c['t'], c['t'] - x['t'], x['t']))
    return {b: sorted(v) for b, v in by.items()}


def one(mid):
    rows = lags(load(mid))
    if not rows:
        print('# %s 没有可用的 results.csv 行' % mid)
        return None
    td = truth_deaths(mid)
    ld = last_delays(mid)
    print('# %s 客户端落后服务器多少拍（墙上时钟；每拍 56 毫秒；T0 取本局各号 at − 56ms×tick 的最小值，所以是下限）' % mid)
    out = dict(match=mid, bots=[])
    for r in sorted(rows, key=lambda r: r['tick']):
        s = '  %-8s %-5s 客户端 %5d 拍时报告，那一刻服务器约 %5.0f 拍 → 落后 %4.0f 拍（%4.1f 秒）' % (r['bot'], r['event'], r['tick'], r['server'], r['lag'], r['lag'] * TICK)
        rec = dict(bot=r['bot'], event=r['event'], tick=r['tick'], server=round(r['server'], 1), lag=round(r['lag'], 1), group=r['group'])
        if td:
            names, dead, _ = td
            p = next((k for k, n in names.items() if n.strip().lower().endswith(r['bot'].lower())), None)
            if p is not None and p in dead:
                dt = dead[p]
                s += '；录像里 %d 拍出局，客户端报告拍比它晚 %d 拍，服务器上已经过了 %.0f 拍' % (dt, r['tick'] - dt, r['server'] - dt)
                rec.update(deathTick=dt, reportAfterDeath=r['tick'] - dt, serverAfterDeath=round(r['server'] - dt, 1))
        v = [x for x in ld.get(r['bot'], []) if x[0] <= r['tick'] + 400]
        if v:
            tail = v[-5:]
            med = pq([x[1] for x in tail], .5)
            s += '；最后 %d 条配上对的指令（落地 %d~%d 拍）执行拍 − 决策拍 中位 %d、最大 %d' % (len(tail), tail[0][0], tail[-1][0], med, max(x[1] for x in tail))
            rec.update(lastCmdDelayP50=med, lastCmdDelayMax=max(x[1] for x in tail), lastCmdFrom=tail[0][0], lastCmdTo=tail[-1][0])
        if r['group'] != 'one':
            s += '（拆房间：%s）' % r['group']
        print(s)
        out['bots'].append(rec)
    v = [r['lag'] for r in rows]
    print('  合计 %d 个号：落后 ≥35 拍的 %d 个、≥90 拍的 %d 个；最大 %.0f 拍' % (len(v), sum(1 for x in v if x >= 35), sum(1 for x in v if x >= 90), max(v)))
    out.update(n=len(v), ge35=sum(1 for x in v if x >= 35), ge90=sum(1 for x in v if x >= 90), max=round(max(v), 1))
    d = os.path.join(ROOT, 'tmp', 'wall')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    return out


def all_bundles(tsv):
    bd = os.path.join(DATA, 'bundles')
    mids = sorted(x for x in os.listdir(bd) if os.path.exists(os.path.join(bd, x, 'results.csv')))
    allr = []
    per = {}
    for mid in mids:
        rows = lags(load(mid))
        if not rows:
            continue
        per[mid] = rows
        for r in rows:
            r['match'] = mid
            allr.append(r)
    if tsv:
        print('match\tbot\tevent\tgroup\ttick\tserver\tlag')
        for r in allr:
            print('%s\t%s\t%s\t%s\t%d\t%.0f\t%.0f' % (r['match'], r['bot'], r['event'], r['group'], r['tick'], r['server'], r['lag']))
        return
    print('# 全部对局包：客户端在报告结束那一刻落后服务器多少拍（%d 局、%d 个号·报告；下限口径）' % (len(per), len(allr)))
    out = dict(matches=len(per), reports=len(allr), bands={}, events={})
    print('  按客户端报告拍分段：')
    for lo, hi, nm in BANDS:
        v = [r['lag'] for r in allr if lo <= r['tick'] < hi]
        if not v:
            continue
        print('    %-10s %4d 个：落后 P50 %4.0f、P90 %4.0f、最大 %5.0f 拍；≥35 拍 %3d 个（%2.0f%%），≥90 拍 %3d 个（%2.0f%%），≥180 拍 %3d 个（%2.0f%%）' % (
            nm, len(v), pq(v, .5), pq(v, .9), max(v), sum(1 for x in v if x >= 35), 100.0 * sum(1 for x in v if x >= 35) / len(v),
            sum(1 for x in v if x >= 90), 100.0 * sum(1 for x in v if x >= 90) / len(v), sum(1 for x in v if x >= 180), 100.0 * sum(1 for x in v if x >= 180) / len(v)))
        out['bands'][nm] = dict(n=len(v), p50=round(pq(v, .5)), p90=round(pq(v, .9)), max=round(max(v)), ge35=sum(1 for x in v if x >= 35),
                                ge90=sum(1 for x in v if x >= 90), ge180=sum(1 for x in v if x >= 180))
    print('  按结束方式：')
    for ev in sorted(set(r['event'] for r in allr)):
        v = [r['lag'] for r in allr if r['event'] == ev]
        print('    %-6s %4d 个：落后 P50 %4.0f、P90 %4.0f、最大 %5.0f 拍；≥90 拍 %3d 个（%2.0f%%）' % (ev, len(v), pq(v, .5), pq(v, .9), max(v), sum(1 for x in v if x >= 90), 100.0 * sum(1 for x in v if x >= 90) / len(v)))
        out['events'][ev] = dict(n=len(v), p50=round(pq(v, .5)), p90=round(pq(v, .9)), max=round(max(v)), ge90=sum(1 for x in v if x >= 90))
    # 每局里「不是最后一个报告」的号：最后报告的号按定义接近 0，单看其余的
    worst = sorted(((max(r['lag'] for r in rows), mid) for mid, rows in per.items()), reverse=True)[:12]
    print('  单局最大落后量最大的 12 局：' + '；'.join('%s %.0f 拍' % (m, x) for x, m in worst))
    nbig = sum(1 for mid, rows in per.items() if max(r['lag'] for r in rows) >= 90)
    print('  至少有一个号报告时落后 ≥90 拍的局：%d / %d' % (nbig, len(per)))
    out['matchesWithGe90'] = nbig
    d = os.path.join(ROOT, 'tmp', 'wall')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, '_all.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)


def main():
    a = sys.argv[1:]
    if '--all' in a:
        all_bundles('--tsv' in a)
        return
    for mid in [x for x in a if not x.startswith('--')]:
        one(mid)


if __name__ == '__main__':
    main()
