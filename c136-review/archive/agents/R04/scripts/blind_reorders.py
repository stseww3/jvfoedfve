#!/usr/bin/env python3
# blind_reorders.py — 「上一条还没生效就又下了一条」的陆攻有多少（总部广播 0004 的第 3 条）。
#
# 用法：python3 scripts/blind_reorders.py <局号> [--ours id,id,…] [--list N] [--lag] [--from 拍]
#   只需要 tmp/truth/<局号>/cmd.tsv 和 meta.json（engine_truth.cjs）；--lag 另需 tmp/shadow/<局号>/intents.tsv。
# 背景（--lag 会把这两条在本局重新量一遍）：
#   · 录像里所有指令都在 7 的倍数拍执行（7 拍一个回合）；
#   · 一条指令从策略发出到执行要 7~15 拍（落后时更久）。策略每 5 拍决策一次，
#     所以发出一条之后的下一个决策拍（+5）一定还看不到它的效果：余额没扣，进攻槽里也没有这支兵。
# 定义（只用录像里落地的指令，不依赖影子策略的配对）：
#   出兵串 = 同一个号对同一个目标（真人或内置 AI，不含无主地）的陆攻，每一条和上一条落在同一拍或相邻回合（相隔 ≤7 拍）；
#   串里第 2 条起叫「跟发」：它发出时上一条还没执行（延迟 ≥7 拍 > 决策间隔 5 拍）。
#   串里有某一拍落了 ≥3 条的，算「积压串」（正常情况下一个回合最多落两个决策拍的指令，≥3 条说明指令在路上积压过：
#   客户端落后追帧，或者指令迟迟没被排进回合）；
#   其余算「正常串」。
#   再用影子策略（tmp/shadow/<局号>/intents.tsv，有才算）把 ≥2 条的串分成两种：
#     关闸串 = 串首那条执行后的两个决策拍（T首 < t ≤ T首+10）里，影子策略对这个目标不再下单
#              → 策略一看到第一条生效就停手，后面几条是看不到第一条时多下的（重复单）；
#     续单串 = 第一条生效后策略还在继续对它下单（比如追打离场的号）→ 后面几条不能算多下的。
# 输出：
#   落地的陆攻（打人/AI）条数和兵；正常串里跟发的条数和兵、占比（分时段、分号）；积压串的条数和兵；
#   关闸串里的重复单（条、兵、占比，分时段、分号）；
#   正常串的长度分布；每串出兵占「串首那条执行前余额」的比例（单发 vs 连发）。
#   兵用录像里实际出征的兵（cmd.tsv 的 sub），不含手续费。
import sys, os, csv, json, collections
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def band(t):
    return '<1500' if t < 1500 else '1500~2999' if t < 3000 else '3000~4283' if t < 4284 else '≥4284'


def k(v):
    return '%.1f万' % (v / 1e4) if v >= 1e4 else str(int(v))


def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else 0


def main():
    a = sys.argv[1:]
    mid = a[0]
    nlist = int(a[a.index('--list') + 1]) if '--list' in a else 0
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json'), encoding='utf8'))
    ours = {int(p): n for p, n in meta['ours'].items()}
    if '--ours' in a:
        want = [int(x) for x in a[a.index('--ours') + 1].split(',')]
        names = {p['p']: p['name'] for p in meta['players']}
        ours = {p: names.get(p, '#%d' % p) for p in want}
    rows = []
    allticks = collections.Counter()
    with open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8') as f:
        for i, r in enumerate(csv.DictReader(f, delimiter='\t')):
            if int(r['spawnStep']) >= 0:
                continue
            allticks[int(r['t']) % 7] += 1
            if int(r['id']) != 1 or int(r['p']) not in ours or int(r['b']) == 512:
                continue
            s = r['sub'] or ''
            if not s.startswith('atk:'):
                continue
            rows.append(dict(i=i, t=int(r['t']), p=int(r['p']), q=int(r['b']), bal0=int(r['bal0']), v=int(s.split(':')[2])))
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['p'], r['q'])].append(r)
    chains = []
    for key, v in by.items():
        v.sort(key=lambda r: (r['t'], r['i']))
        cur = None
        for r in v:
            if cur is not None and r['t'] - cur['last'] <= 7:
                cur['rows'].append(r)
                cur['last'] = r['t']
            else:
                cur = dict(p=key[0], q=key[1], rows=[r], last=r['t'])
                chains.append(cur)
    for c in chains:
        per = collections.Counter(r['t'] for r in c['rows'])
        c['flush'] = max(per.values()) >= 3
        c['n'] = len(c['rows'])
        c['v'] = sum(r['v'] for r in c['rows'])
        t0 = c['rows'][0]['t']
        c['t0'] = t0
        c['bal0'] = max(r['bal0'] for r in c['rows'] if r['t'] == t0)
    shadow = None
    sp = os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv')
    if os.path.exists(sp):
        shadow = collections.defaultdict(list)
        with open(sp, encoding='utf8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r['kind'] == 'attack':
                    shadow[(int(r['p']), int(r['target']))].append(int(r['t']))
    for c in chains:
        c['closed'] = None
        if shadow is not None and c['n'] >= 2:
            c['closed'] = not any(c['t0'] < t <= c['t0'] + 10 for t in shadow.get((c['p'], c['q']), []))
    tot_n, tot_v = len(rows), sum(r['v'] for r in rows)
    norm = [c for c in chains if not c['flush']]
    flush = [c for c in chains if c['flush']]
    fol_n = sum(c['n'] - 1 for c in norm)
    fol_v = sum(sum(r['v'] for r in c['rows'][1:]) for c in norm)
    print('%s：录像里指令执行拍对 7 取余的分布 %s。我方落地的陆攻（打真人或内置 AI，不含无主地、不含没产生进攻的）%d 条 %s 兵' % (mid, dict(sorted(allticks.items())), tot_n, k(tot_v)))
    print('  正常串 %d 个 %d 条 %s 兵：其中跟发（上一条落地后 7 拍内又落一条）%d 条 %s 兵，占全部打人/AI 出征兵的 %.0f%%；积压串（某一拍落 ≥3 条）%d 个 %d 条 %s 兵' % (
        len(norm), sum(c['n'] for c in norm), k(sum(c['v'] for c in norm)), fol_n, k(fol_v), 100.0 * fol_v / max(1, tot_v),
        len(flush), sum(c['n'] for c in flush), k(sum(c['v'] for c in flush))))
    ffol_n = sum(c['n'] - 1 for c in flush)
    ffol_v = sum(sum(r['v'] for r in c['rows'][1:]) for c in flush)
    print('  两类合计：出兵串里第 2 条起的陆攻 %d 条 %s 兵，占全部打人/AI 出征兵的 %.0f%%（正常串 %s + 积压串 %s）' % (
        fol_n + ffol_n, k(fol_v + ffol_v), 100.0 * (fol_v + ffol_v) / max(1, tot_v), k(fol_v), k(ffol_v)))
    if shadow is not None:
        cl = [c for c in chains if c['closed']]
        op = [c for c in chains if c['closed'] is False]
        dup_n = sum(c['n'] - 1 for c in cl)
        dup_v = sum(sum(r['v'] for r in c['rows'][1:]) for c in cl)
        print('  用影子策略分：关闸串（第一条一生效策略就停手）%d 个，其中的重复单（第 2 条起）%d 条 %s 兵，占全部打人/AI 出征兵的 %.0f%%；续单串（生效后还在继续下单）%d 个 %d 条 %s 兵' % (
            len(cl), dup_n, k(dup_v), 100.0 * dup_v / max(1, tot_v), len(op), sum(c['n'] for c in op), k(sum(c['v'] for c in op))))
        for lab, sel in (('正常延迟的串', [c for c in cl if not c['flush']]), ('积压过的串（某一拍落 ≥3 条）', [c for c in cl if c['flush']])):
            early = [c for c in sel if c['t0'] < 3000]
            late = [c for c in sel if c['t0'] >= 3000]
            print('    关闸串里%s %d 个，重复单 %d 条 %s 兵（串首在 3000 拍前的 %d 个 %s 兵，之后 %d 个 %s 兵）' % (
                lab, len(sel), sum(c['n'] - 1 for c in sel), k(sum(sum(r['v'] for r in c['rows'][1:]) for c in sel)),
                len(early), k(sum(sum(r['v'] for r in c['rows'][1:]) for c in early)), len(late), k(sum(sum(r['v'] for r in c['rows'][1:]) for c in late))))
        db = collections.defaultdict(lambda: [0, 0])
        dbot = collections.defaultdict(lambda: [0, 0])
        for c in cl:
            for r in c['rows'][1:]:
                for d, key in ((db, band(r['t'])), (dbot, ours[c['p']])):
                    d[key][0] += 1
                    d[key][1] += r['v']
        print('    重复单按时段（条/兵）：' + '；'.join('%s %d/%s' % (b, db[b][0], k(db[b][1])) for b in ('<1500', '1500~2999', '3000~4283', '≥4284') if b in db))
        print('    重复单按号（条/兵）：' + '；'.join('%s %d/%s' % (b, v[0], k(v[1])) for b, v in sorted(dbot.items(), key=lambda kv: -kv[1][1])))
        bigc = [c for c in cl if c['bal0'] >= 100000]
        if bigc:
            fr = [100.0 * c['v'] / c['bal0'] for c in bigc]
            f1 = [100.0 * c['rows'][0]['v'] / c['bal0'] for c in bigc]
            print('    串首执行前余额 ≥10 万的关闸串 %d 个：第一条出兵占余额的中位 %.0f%%，整串占余额的中位 %.0f%%、最大 %.0f%%；串长分布 %s' % (
                len(bigc), med(f1), med(fr), max(fr), dict(sorted(collections.Counter(min(c['n'], 6) for c in bigc).items()))))
    bb = collections.defaultdict(lambda: [0, 0, 0, 0])
    bot = collections.defaultdict(lambda: [0, 0, 0, 0])
    for c in chains:
        for j, r in enumerate(c['rows']):
            for d, key in ((bb, band(r['t'])), (bot, ours[c['p']])):
                d[key][0] += 1
                d[key][1] += r['v']
                if not c['flush'] and j >= 1:
                    d[key][2] += 1
                    d[key][3] += r['v']
    print('  按时段（落地 条/兵 → 正常串里的跟发 条/兵）：' + '；'.join('%s %d/%s → %d/%s' % (b, bb[b][0], k(bb[b][1]), bb[b][2], k(bb[b][3])) for b in ('<1500', '1500~2999', '3000~4283', '≥4284') if b in bb))
    print('  按号（落地 条/兵 → 正常串里的跟发 条/兵）：' + '；'.join('%s %d/%s → %d/%s' % (b, v[0], k(v[1]), v[2], k(v[3])) for b, v in sorted(bot.items(), key=lambda kv: -kv[1][3])))
    fb = collections.defaultdict(lambda: [0, 0, 0])
    for c in flush:
        x = fb[band(c['t0'])]
        x[0] += 1
        x[1] += c['n']
        x[2] += c['v']
    if fb:
        print('  积压串按串首所在时段（个/条/兵）：' + '；'.join('%s %d/%d/%s' % (b, fb[b][0], fb[b][1], k(fb[b][2])) for b in ('<1500', '1500~2999', '3000~4283', '≥4284') if b in fb))
    dist = collections.Counter(min(c['n'], 6) for c in norm)
    print('  正常串的长度分布 %s（6 表示 ≥6）' % dict(sorted(dist.items())))
    big = [c for c in norm if c['bal0'] >= 100000]
    one = [100.0 * c['v'] / c['bal0'] for c in big if c['n'] == 1]
    many = [100.0 * c['v'] / c['bal0'] for c in big if c['n'] >= 2]
    if one and many:
        print('  串首执行前余额 ≥10 万的正常串：单发 %d 个，出兵占余额的中位 %.0f%%；连发（≥2 条）%d 个，合计 %s 兵，每串出兵占余额的中位 %.0f%%、最大 %.0f%%' % (
            len(one), med(one), len(many), k(sum(c['v'] for c in big if c['n'] >= 2)), med(many), max(many)))
    t_from = int(a[a.index('--from') + 1]) if '--from' in a else 0
    bigb = collections.defaultdict(lambda: [0, 0, 0, 0])
    for c in chains:
        if c['t0'] < t_from or c['v'] < 200000:
            continue
        x = bigb[ours[c['p']]]
        if c['n'] == 1:
            x[0] += 1
            x[1] += c['v']
        else:
            x[2] += 1
            x[3] += c['v']
    if bigb:
        print('  出兵 ≥20 万的串（串首在 %d 拍及以后；单发 个/兵 → 连发 个/兵）：' % t_from + '；'.join(
            '%s %d/%s → %d/%s' % (b, v[0], k(v[1]), v[2], k(v[3])) for b, v in sorted(bigb.items(), key=lambda kv: -(kv[1][1] + kv[1][3]))))
    names = {p['p']: p['name'] for p in meta['players']}
    for c in sorted([c for c in chains if c['n'] >= 2], key=lambda c: -c['v'])[:nlist]:
        print('    拍 %5d %-7s → %s#%d：%s%s%d 条连发（落地拍 %s），合计 %s 兵，占串首执行前余额 %s 的 %.0f%%' % (
            c['t0'], ours[c['p']], names.get(c['q'], 'AI'), c['q'], '[积压] ' if c['flush'] else '', {True: '[关闸] ', False: '[续单] ', None: ''}[c['closed']],
            c['n'], '、'.join(str(r['t']) for r in c['rows']), k(c['v']), k(c['bal0']), 100.0 * c['v'] / max(1, c['bal0'])))
    if '--lag' in a:
        sys.path.insert(0, HERE)
        from exec_gap import load, match
        intents, cmds, check = load(mid)
        byp = collections.defaultdict(list)
        for x in intents:
            byp[x['p']].append(x)
        pairs, rest, lone = match(intents, cmds)
        lags = []
        for x, c in pairs:
            if x['kind'] != 'attack':
                continue
            if any(y is not x and y['kind'] == 'attack' and y['pct'] == x['pct'] and abs(y['t'] - x['t']) <= 150 for y in byp[x['p']]):
                continue
            lags.append(c['t'] - x['t'])
        lags.sort()
        n = len(lags)
        if n:
            print('  延迟（影子策略的决策拍 → 录像里的执行拍；只取前后 150 拍内比例唯一、配对没有歧义的陆攻 %d 条）：最小 %d，5%% 位 %d，25%% 位 %d，中位 %d，75%% 位 %d；≤6 拍的 %d 条，7~15 拍的 %d 条，16~25 拍的 %d 条，>25 拍的 %d 条' % (
                n, lags[0], lags[int(0.05 * n)], lags[int(0.25 * n)], lags[n // 2], lags[int(0.75 * n)],
                sum(1 for x in lags if x <= 6), sum(1 for x in lags if 7 <= x <= 15), sum(1 for x in lags if 16 <= x <= 25), sum(1 for x in lags if x > 25)))


if __name__ == '__main__':
    main()
