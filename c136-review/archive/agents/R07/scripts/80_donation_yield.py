#!/usr/bin/env python3
"""80_donation_yield.py — R07：每一笔到账的捐款，落地当拍让「捐方 + 收方」每 10 拍的利息合计变了多少（统筹广播 0005-④）。

做法：利率按引擎公式（game.js L41、L739-746、L778-790，与 75_interest.py 同一个函数；那个脚本逐桶核对过和引擎真值相同）：
  利率 = 表值（只看个人领土占全图份额） → t<1920 的开局下限 → 余额过软上限（100×领土）后按超出比例扣减。
  一笔捐款：捐方余额 b0 → b1（扣掉到账额 + 手续费），收方余额 tBal → tBal + 到账额；领土不变。
  Δ利息（每 10 拍）= 利率(捐方, b1)×b1 + 利率(收方, 后)×后 − 利率(捐方, b0)×b0 − 利率(收方, 前)×前，再除以 10000。
  这是「落地当拍」的瞬时量：不含收方拿到兵之后去打地、也不含捐方本来会不会把这些兵花掉。
输入：out/<mid>/cmd_effect.tsv（67_troop_flow.mjs：引擎里每条生效指令的扣款 / 到账）、quota_logs.tsv（69_quota_truth.mjs：日志里的调度类别与落地拍）、
      bundles/<mid>/card.json（全图陆地）
用法：python3 80_donation_yield.py <matchId> [--span t0:t1]…
  --span：再按时间段各出一段（笔数、到账、手续费、Δ利息、收方落地后过软上限 / 顶到硬上限的笔数、按「捐方→收方」的合计、接力笔数）
输出：out/<mid>/donation_yield.txt / .json
"""
import csv, importlib.util, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/agent/repos/c136-data'
spec = importlib.util.spec_from_file_location('interest75', os.path.join(HERE, '75_interest.py'))
I75 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(I75)
rate = I75.rate

KIND_CN = {'defense_dispatch': '协防', 'offense_dispatch': '进攻余粮', 'yield_opt_dispatch': '生息余粮', '?': '没有对应日志'}


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    mid = sys.argv[1]
    out = os.path.join(HERE, '..', 'out', mid)
    land = json.load(open(os.path.join(DATA, 'bundles', mid, 'card.json')))['mapLand']
    kinds = {}
    qf = os.path.join(out, 'quota_logs.tsv')
    if os.path.exists(qf):
        for r in csv.DictReader(open(qf, encoding='utf-8'), delimiter='\t'):
            if r.get('execT'):
                kinds[(int(r['execT']), r['bot'], r['to'])] = (r['kind'], int(r['t']))
    rows = []
    for r in csv.DictReader(open(os.path.join(out, 'cmd_effect.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['kind'] != 'donate' or r['ok'] != '1':
            continue
        t = int(r['t']); b0 = int(r['b0']); b1 = int(r['b1']); fee = int(r['fee']); got = int(r['troops'])
        terr = int(r['terr']); tT = int(r['tTerr']); tB = int(r['tBal'])
        if got <= 0 and b0 == b1:
            continue
        to = r['tname']
        to_s = to.split('] ')[-1].split('#')[0] if '] ' in to else to.split('#')[0]
        kd = kinds.get((t, r['bot'], to_s), ('?', None))
        rd0, _ = rate(t, terr, b0, land, 0); rd1, _ = rate(t, terr, b1, land, 0)
        rr0, _ = rate(t, tT, tB, land, 0); rr1, _ = rate(t, tT, tB + got, land, 0)
        dI = (rd1 * b1 + rr1 * (tB + got) - rd0 * b0 - rr0 * tB) / 10000
        rows.append(dict(t=t, donor=r['bot'], to=to_s, kind=kd[0], logT=kd[1], got=got, fee=fee, lost=b0 - b1 - fee - got,
                         dDonor0=b0 / max(1, terr), dDonor1=b1 / max(1, terr), dRecv0=tB / max(1, tT), dRecv1=(tB + got) / max(1, tT),
                         rd0=rd0, rd1=rd1, rr0=rr0, rr1=rr1, dI=dI, terrD=terr, terrR=tT))
    T = []
    P = T.append
    P(f'# {mid} 捐款的瞬时利息账（80_donation_yield.py）：到账 {len(rows)} 笔')
    P('# 利率单位：每 10 拍万分之；Δ利息 = 落地当拍「捐方 + 收方」每 10 拍利息合计的变化（正 = 两边合计多生息）')
    P('')
    P('A. 按类别')
    by = defaultdict(list)
    for r in rows:
        by[r['kind']].append(r)
    J = {'n': len(rows), 'byKind': {}}
    for k, L in sorted(by.items(), key=lambda kv: -len(kv[1])):
        got = sum(r['got'] for r in L); fee = sum(r['fee'] for r in L); dI = sum(r['dI'] for r in L)
        neg = [r for r in L if r['dI'] < 0]
        inv = [r for r in L if r['dDonor0'] < r['dRecv0']]
        over = [r for r in L if r['dRecv1'] > 100]
        P(f"   {KIND_CN.get(k, k)}: {len(L)} 笔，到账 {got:,}，手续费 {fee:,}；Δ利息合计 {dI:+,.0f} / 10 拍（其中为负的 {len(neg)} 笔 {sum(r['dI'] for r in neg):+,.0f}）；"
          f"捐方密度低于收方的 {len(inv)} 笔（到账 {sum(r['got'] for r in inv):,}）；落地后收方过软上限的 {len(over)} 笔（到账 {sum(r['got'] for r in over):,}）")
        J['byKind'][k] = dict(n=len(L), got=got, fee=fee, dI=round(dI), neg=len(neg), negDI=round(sum(r['dI'] for r in neg)), inverted=len(inv), invertedGot=sum(r['got'] for r in inv), recvOver=len(over), recvOverGot=sum(r['got'] for r in over))
    got = sum(r['got'] for r in rows); fee = sum(r['fee'] for r in rows); dI = sum(r['dI'] for r in rows)
    pos = sum(r['dI'] for r in rows if r['dI'] > 0)
    P(f"   合计: 到账 {got:,}，手续费 {fee:,}，Δ利息合计 {dI:+,.0f} / 10 拍" + (f"；按这个速度手续费要 {fee / dI * 10:,.0f} 拍才生得回来" if dI > 0 else '；两边合计的利息没有变多，手续费生不回来'))
    J['total'] = dict(got=got, fee=fee, dI=round(dI))
    P('')
    P('B. 逐笔（落地拍 捐方→收方 类别 | 到账 手续费 | 捐方密度 前→后（利率 前→后） | 收方密度 前→后（利率 前→后） | Δ利息/10拍）')
    for r in rows:
        P(f"   t={r['t']} {r['donor']}→{r['to']} {KIND_CN.get(r['kind'], r['kind'])} | {r['got']:,} {r['fee']:,} | {r['dDonor0']:.0f}→{r['dDonor1']:.0f}（{r['rd0']}→{r['rd1']}） | "
          f"{r['dRecv0']:.0f}→{r['dRecv1']:.0f}（{r['rr0']}→{r['rr1']}） | {r['dI']:+,.0f}")
    spans = []
    av = sys.argv[2:]
    for i, x in enumerate(av):
        if x == '--span' and i + 1 < len(av):
            t0, t1 = av[i + 1].split(':'); spans.append((int(t0), int(t1)))
    J['spans'] = []
    if spans:
        P('')
        P('C. 按时间段（--span；「接力」= 这笔的捐方在此前 300 拍内收过我方的捐款；「硬上限」= 落地后收方余额 ≥149.5×领土）')
    for t0, t1 in spans:
        L = [r for r in rows if t0 <= r['t'] <= t1]
        if not L:
            P(f'   t={t0}~{t1}: 0 笔'); continue
        got = sum(r['got'] for r in L); fee = sum(r['fee'] for r in L); dI = sum(r['dI'] for r in L)
        over = [r for r in L if r['dRecv1'] > 100]
        hard = [r for r in L if r['dRecv1'] >= 149.5]
        dcap = [r for r in L if r['dDonor0'] >= 149.5]
        lost = sum(r['lost'] for r in L)
        relay = []
        for r in L:
            if any(q['to'] == r['donor'] and 0 <= r['t'] - q['t'] <= 300 for q in rows):
                relay.append(r)
        pair = defaultdict(lambda: [0, 0, 0])
        for r in L:
            pr = pair[(r['donor'], r['to'])]; pr[0] += 1; pr[1] += r['got']; pr[2] += r['fee']
        P(f"   t={t0}~{t1}: {len(L)} 笔，到账 {got:,}，手续费 {fee:,}（手续费 ÷ 到账 = {100 * fee / max(1, got):.1f}%）；Δ利息合计 {dI:+,.0f} / 10 拍（为负的 {sum(1 for r in L if r['dI'] < 0)} 笔）；"
          f"落地后收方过软上限 {len(over)} 笔（到账 {sum(r['got'] for r in over):,}），其中顶到硬上限 {len(hard)} 笔；捐方发令时自己就在硬上限的 {len(dcap)} 笔；"
          f"扣了款却没到账的兵 {lost:,}；接力 {len(relay)} 笔（到账 {sum(r['got'] for r in relay):,}，手续费 {sum(r['fee'] for r in relay):,}）")
        P('      捐方→收方：' + '；'.join(f"{a}→{b} {v[0]} 笔 {v[1]:,}（费 {v[2]:,}）" for (a, b), v in sorted(pair.items(), key=lambda kv: -kv[1][1])[:12]))
        J['spans'].append(dict(t0=t0, t1=t1, n=len(L), got=got, fee=fee, dI=round(dI), recvOver=len(over), recvHard=len(hard), donorHard=len(dcap), lost=lost, relayN=len(relay), relayGot=sum(r['got'] for r in relay), relayFee=sum(r['fee'] for r in relay),
                               pairs=[dict(donor=a, to=b, n=v[0], got=v[1], fee=v[2]) for (a, b), v in sorted(pair.items(), key=lambda kv: -kv[1][1])]))
    J['rows'] = rows
    open(os.path.join(out, 'donation_yield.txt'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
    json.dump(J, open(os.path.join(out, 'donation_yield.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n'.join(T[:9]))
    print('...')
    print('\n'.join(x for x in T if x.startswith('C.') or x.startswith('   t=') and '笔，到账' in x or x.startswith('      捐方→收方')))


if __name__ == '__main__':
    main()
