#!/usr/bin/env python3
"""75_interest.py — R07：按引擎公式重算每个真人当拍的利率，分组对照「同样的兵，谁的利息高」。

引擎（/agent/repos/c136-data/src/sim/sim/game.js L41、L739-746、L778-790）：
  利率（每 10 拍，万分比）= INTEREST_TABLE[floor(511×领土/全图陆地)]，表值 = 100 + isqrt(25600×i/508)
    —— 也就是 100 + 约 160×sqrt(个人领土占全图的份额)：一个人的地越大，他每个兵生的利息越多；
  t<1920 时利率不低于 100×(13440−6t)/1920（开局所有人一样高，随时间降到 100）；
  余额超过软上限（100×领土）后利率按 2×(超出部分/软上限) 的比例扣减，到 150×领土时为 0；离开的席位为 0；
  每 10 拍利息 = 利率×余额/10000；另每 100 拍每格地 +1 兵。

用法：python3 75_interest.py <matchId> --at 990,1530,…
输入：out/<mid>/truth_all.tsv、truth_players.tsv（60_truth.cjs 的产物）；bundles/<mid>/card.json（全图陆地）
输出：out/<mid>/interest.txt / interest.json
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/agent/repos/c136-data'


def iV(a, b):
    return (2 * a + 1) // (2 * b)


def mn(h, cs):
    a = iV(h + 1, 2)
    for _ in range(cs):
        a = iV(a + iV(h, a), 2)
    return a


TABLE = []
for i in range(512):
    h = iV(25600 * i, 508)
    TABLE.append(100 + (0 if h < 1 else mn(h, 9)))


def rate(t, terr, bal, land, state):
    if state == 2 or terr <= 0:
        return 0, 0
    base = TABLE[min(511, iV(511 * terr, land))]
    n1 = base
    if t < 1920:
        n1 = max(iV(100 * (13440 - 6 * t), 1920), n1)
    cap = min(100 * terr, 10 ** 9)
    if bal > cap and cap > 0:
        n1 -= iV(2 * n1 * (bal - cap), cap)
    return min(max(n1, 0), 700), base


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    at = []
    if '--at' in sys.argv:
        at = [int(x) for x in sys.argv[sys.argv.index('--at') + 1].split(',')]
    out = os.path.join(HERE, '..', 'out', mid)
    land = json.load(open(os.path.join(DATA, 'bundles', mid, 'card.json')))['mapLand']
    players = {int(r['p']): r for r in csv.DictReader(open(os.path.join(out, 'truth_players.tsv')), delimiter='\t')}
    humans = {p for p, r in players.items() if r['human'] == '1'}
    squad = {p for p, r in players.items() if r.get('squad')}
    sq_teams = {players[p]['team'] for p in squad}
    rows = {}
    ticks = set()
    for r in csv.DictReader(open(os.path.join(out, 'truth_all.tsv')), delimiter='\t'):
        p = int(r['p'])
        if p not in humans:
            continue
        t = int(r['t'])
        ticks.add(t)
        rows[(t, p)] = (int(r['terr']), int(r['bal']), int(r['alive']), int(r['state']))
    ticks = sorted(ticks)
    if not at:
        at = ticks[::10]

    def grp(p):
        if p in squad:
            return '我方号'
        tm = players[p]['team']
        return f'T{tm} 其他真人' if tm in sq_teams else f'T{tm} 真人'

    groups = sorted({grp(p) for p in humans}, key=lambda g: (g != '我方号', g))
    L = []
    P = L.append
    P(f'# {mid} 利率对照（按引擎公式逐人重算；全图陆地 {land:,} 格）')
    P('# 利率单位：每 10 拍、万分比。「表值」= 只看个人领土份额的基础利率（100 + 约 160×sqrt(份额)）；「实际」= 再算上 t<1920 的开局下限和超软上限扣减。')
    P('# 「加权利率」= 组内每人 实际利率×余额 之和 ÷ 组内余额合计；「合成一个人」= 假如这组的地和兵都在一个人手里、且不超软上限时的表值（只作对照，不是建议）。')
    P('')
    P('A. 分组 × 时刻')
    P('t\t组\t在场\t领土(占全图)\t余额\t密度\t加权利率\t每 10 拍利息\t合成一个人的表值\t组内最大的号：领土份额 / 表值 / 实际利率 / 余额占组内')
    J = {'land': land, 'at': at, 'groups': {}, 'players': {}}
    for t in at:
        tt = max([x for x in ticks if x <= t] or [ticks[0]])
        for g in groups:
            mem = [p for p in humans if grp(p) == g and (tt, p) in rows and rows[(tt, p)][2] and rows[(tt, p)][0] > 0 and rows[(tt, p)][3] != 2]
            if not mem:
                continue
            terr = sum(rows[(tt, p)][0] for p in mem)
            bal = sum(rows[(tt, p)][1] for p in mem)
            inc = 0
            for p in mem:
                te, b, _, st = rows[(tt, p)]
                r, _b = rate(tt, te, b, land, st)
                inc += max(iV(r * b, 10 ** 4), 1)
            wr = 10000 * inc / max(1, bal)
            one, _ = rate(max(tt, 1920), terr, 0, land, 0)
            top = max(mem, key=lambda p: rows[(tt, p)][0])
            te, b, _, st = rows[(tt, top)]
            r, base = rate(tt, te, b, land, st)
            P(f"{tt}\t{g}\t{len(mem)}\t{terr:,}（{100 * terr / land:.1f}%）\t{bal:,}\t{bal / max(1, terr):.0f}\t{wr:.0f}\t{inc:,}\t{one}\t{players[top]['name'][:16]}#{top}：{100 * te / land:.1f}% / {base} / {r} / {100 * b / max(1, bal):.0f}%")
            J['groups'].setdefault(g, []).append({'t': tt, 'n': len(mem), 'terr': terr, 'bal': bal, 'wRate': round(wr, 1), 'inc10': inc, 'oneRate': one, 'top': players[top]['name'], 'topShare': round(100 * te / land, 2), 'topBase': base, 'topRate': r, 'topBalShare': round(100 * b / max(1, bal), 1)})
    P('')
    P('B. 逐人（我方号 + 领土最大的 4 个其他真人）：领土份额% / 表值 / 实际利率 / 密度')
    for t in at:
        tt = max([x for x in ticks if x <= t] or [ticks[0]])
        alive = [p for p in humans if (tt, p) in rows and rows[(tt, p)][2] and rows[(tt, p)][0] > 0]
        others = sorted([p for p in alive if p not in squad], key=lambda p: -rows[(tt, p)][0])[:4]
        mine = sorted([p for p in alive if p in squad], key=lambda p: -rows[(tt, p)][0])
        cells = []
        for p in mine + others:
            te, b, _, st = rows[(tt, p)]
            r, base = rate(tt, te, b, land, st)
            nm = players[p].get('squad') or players[p]['name'][:12]
            cells.append(f"{'' if p in squad else '['}{nm}{'' if p in squad else ']'} {100 * te / land:.1f}%/{base}/{r}/{b / max(1, te):.0f}")
            J['players'].setdefault(str(p), []).append({'t': tt, 'terr': te, 'bal': b, 'base': base, 'rate': r})
        P(f"t={tt}\t" + '\t'.join(cells))
    # C. 公式核对：用 67_troop_flow.mjs 的 tick_net.tsv（我方每号每 10 拍的利息地租真值）逐桶重算。
    #    只比「这 10 拍里除了利息地租没有别的进出」的桶：期初余额 = 上一桶的期末余额，领土不变。
    tn = os.path.join(out, 'tick_net.tsv')
    if os.path.exists(tn):
        by = {}
        for r in csv.DictReader(open(tn), delimiter='\t'):
            by.setdefault(r['bot'], []).append(r)
        ok = bad = 0
        worst = None
        for b, rs in by.items():
            rs.sort(key=lambda r: int(r['t0']))
            for a, c in zip(rs, rs[1:]):
                t0 = int(c['t0'])
                if t0 != int(a['t0']) + 10 or a['terr'] != c['terr']:
                    continue
                if any(int(c[k]) for k in ('refund', 'giftIn', 'boatIn', 'giftOut', 'hit')):
                    continue
                b0, b1, eco, te = int(a['bal']), int(c['bal']), int(c['eco']), int(c['terr'])
                if b1 - b0 != eco or te <= 0:
                    continue
                r, _ = rate(t0 + 9, te, b0, land, 0)
                exp = max(iV(r * b0, 10 ** 4), 1)
                if (t0 + 9) % 100 == 99:
                    exp += iV(32 * te, 32)
                if min(exp, 150 * te - b0) == eco:
                    ok += 1
                else:
                    bad += 1
                    if worst is None or abs(exp - eco) > abs(worst[3] - worst[4]):
                        worst = (b, t0, b0, exp, eco)
        P('')
        P(f'C. 公式核对（tick_net.tsv 里只有利息地租进出的 10 拍桶）：重算与引擎真值相同 {ok} 桶，不同 {bad} 桶' + (f'；差得最多的一桶 {worst[0]} t={worst[1]} 余额 {worst[2]:,}：重算 {worst[3]:,}、真值 {worst[4]:,}' if worst else ''))
        J['check'] = {'ok': ok, 'bad': bad}
    # D. 复利示意：同一笔兵按某个利率放 1,000 拍（100 次结息；不计地租、软上限、进出）变成原来的多少倍
    P('')
    P('D. 复利示意（同一笔兵放 1,000 拍 = 100 次结息；不计地租 / 软上限 / 进出）：利率（每 10 拍万分之）→ 倍数')
    P('   ' + '；'.join(f'{r} → {(1 + r / 1e4) ** 100:.2f} 倍' for r in (100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220)))
    J['compound1000'] = {r: round((1 + r / 1e4) ** 100, 3) for r in (100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220)}
    open(os.path.join(out, 'interest.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(J, open(os.path.join(out, 'interest.json'), 'w'), ensure_ascii=False)
    print('\n'.join(L[:40] + L[-2:]))


if __name__ == '__main__':
    main()
