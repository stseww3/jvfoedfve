#!/usr/bin/env python3
# doomed_pocket.py — 「弃子线」对账（hub 0005 第 5 项）：我方号挨真人打、压在它身上的兵 > 1.65×它的余额 的时段。
# 这是 tryDonateToTeammate 里 isDoomedPocket 的第一个条件（Vb L4455：inHumanAtk > 1.65 * Bp，且不是滩头）——
# 条件一成立，这个号就不再是任何队友的调度对象。本脚本只用真引擎的状态表，不跑策略，所以数的是「条件成立的时段」，
# 不是策略真的走到那一行的次数（策略还有入口门槛、相位、滩头例外；逐拍的判定看 shadow.mjs --at 的 [tryDonateToTeammate] 段）。
# 用法：python3 scripts/doomed_pocket.py <局号> [<局号> …] [--ours id,id,…] [--list] [--k 1.65]
# 数据：tmp/truth/<局号>/{state.tsv,atk.tsv,cmd.tsv,ev.tsv,meta.json}（engine_truth.cjs 导出；捐款 = cmd.tsv 里 id=2 且收款人余额增加的行）
# 输出（每局）：
#   段数 = 同一个号连续满足条件的时段（中断 ≤30 拍算同一段）；每段给出：起止拍、号当时的地 / 余额 / 密度、压在身上的真人兵的峰值、
#   此前 600 拍它捐出去多少、这一段里它收到的捐款、段开始时其余我方号「余额 − 88×领土」的正数部分合计（救急调度的可用兵上限）、
#   300 拍内是否出局。
import sys, os, csv, json, collections
sys.dont_write_bytecode = True
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def w(n):
    return f'{n / 1e4:.1f}万'


def load(mid, ours_opt):
    d = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(d, 'meta.json')))
    ours = set(int(x) for x in ours_opt.split(',')) if ours_opt else set(int(k) for k in meta['ours'])
    name = {p['p']: p['name'].replace('[APEX] ', '') for p in meta['players']}
    humans = set(p['p'] for p in meta['players'])
    st = collections.defaultdict(dict)
    with open(os.path.join(d, 'state.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            p = int(r['p'])
            if p in ours:
                st[p][int(r['t'])] = (int(r['terr']), int(r['bal']), int(r['alive']))
    # 压在我方号身上的真人在途兵：atk.tsv 每 10 拍一行（attacker,target,troops）
    inc = collections.defaultdict(lambda: collections.defaultdict(int))
    with open(os.path.join(d, 'atk.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            a, q = int(r['attacker']), int(r['target'])
            if q in ours and a in humans and a not in ours:
                inc[q][int(r['t'])] += int(r['troops'])
    don_out = collections.defaultdict(list)
    don_in = collections.defaultdict(list)
    with open(os.path.join(d, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['id'] != '2' or not r['q'] or not r['balQ1']:
                continue
            v = int(r['balQ1']) - int(r['balQ0'])
            if v <= 0:
                continue
            don_out[int(r['p'])].append((int(r['t']), v))
            don_in[int(r['q'])].append((int(r['t']), v))
    dead = {}
    with open(os.path.join(d, 'ev.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['kind'] == 'dead':
                dead[int(r['p'])] = int(r['t'])
    return meta, ours, name, st, inc, don_out, don_in, dead


def main():
    a = sys.argv[1:]
    k = 1.65
    ours_opt = None
    lst = '--list' in a
    mids = []
    i = 0
    while i < len(a):
        if a[i] == '--k':
            k = float(a[i + 1]); i += 2
        elif a[i] == '--ours':
            ours_opt = a[i + 1]; i += 2
        elif a[i].startswith('--'):
            i += 1
        else:
            mids.append(a[i]); i += 1
    tot = collections.Counter()
    for mid in mids:
        meta, ours, name, st, inc, don_out, don_in, dead = load(mid, ours_opt)
        segs = []
        for p in sorted(ours):
            ts = sorted(t for t in inc[p] if t in st[p] and st[p][t][2] and inc[p][t] > k * max(1, st[p][t][1]))
            cur = None
            for t in ts:
                if cur and t - cur[1] <= 30:
                    cur[1] = t
                else:
                    if cur:
                        segs.append((p, cur[0], cur[1]))
                    cur = [t, t]
            if cur:
                segs.append((p, cur[0], cur[1]))
        segs.sort(key=lambda s: s[1])
        n_dead = 0
        lines = []
        sum_peak = 0
        sum_spare = 0
        for p, t0, t1 in segs:
            terr, bal, _ = st[p][t0]
            peak = max(inc[p][t] for t in range(t0, t1 + 1, 10) if t in inc[p])
            out600 = sum(v for t, v in don_out[p] if t0 - 600 <= t < t0)
            got = sum(v for t, v in don_in[p] if t0 - 10 <= t <= t1 + 30)
            spare = 0
            rich = []
            for q in ours:
                if q == p or t0 not in st[q] or not st[q][t0][2]:
                    continue
                s = st[q][t0][1] - 88 * st[q][t0][0]
                if s > 0:
                    spare += s
                    rich.append((s, name.get(q, q)))
            others = sum(st[q][t0][1] for q in ours if q != p and t0 in st[q] and st[q][t0][2])
            died = p in dead and dead[p] <= t1 + 300
            n_dead += died
            sum_peak += peak
            sum_spare += spare
            lines.append(f'    拍 {t0}~{t1} {name.get(p, p)}：地 {terr} 余额 {w(bal)}（密度 {bal / max(1, terr):.0f}），压在身上的真人兵峰值 {w(peak)}（余额的 {peak / max(1, bal):.1f} 倍）；'
                         f'此前 600 拍捐出 {w(out600)}，这一段收到捐款 {w(got)}；其余我方号合计 {w(others)} 兵，其中「余额 − 88×领土」的正数部分 {w(spare)}'
                         + (f'（{"、".join(n for _, n in sorted(rich, reverse=True)[:3])}）' if rich else '') + f'；{"300 拍内出局（拍 " + str(dead[p]) + "）" if died else "没出局"}')
        print(f'{mid}：压在身上的真人兵 > {k}×余额 的时段 {len(segs)} 段（涉及 {len(set(s[0] for s in segs))} 个号），其中 300 拍内出局 {n_dead} 段；'
              f'各段峰值合计 {w(sum_peak)}，段开始时其余我方号「余额 − 88×领土」正数部分合计 {w(sum_spare)}；这些段里收到的捐款合计 {w(sum(sum(v for t, v in don_in[p] if t0 - 10 <= t <= t1 + 30) for p, t0, t1 in segs))}')
        if lst:
            for l in lines:
                print(l)
        tot['segs'] += len(segs); tot['dead'] += n_dead; tot['games'] += 1
    if len(mids) > 1:
        print(f'合计 {tot["games"]} 局：{tot["segs"]} 段，其中 300 拍内出局 {tot["dead"]} 段')


if __name__ == '__main__':
    main()
