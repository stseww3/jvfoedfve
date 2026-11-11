#!/usr/bin/env python3
"""probe_view.py — 把 shadow.mjs --probe 打出的 shadow_probe[_tag].txt 压成每个决策拍一行：
状态（余额/领土/密度）、offers() 里每个报价（目标、单价 c、要的兵 need、onMe、来袭兵 inAtk、nearCollapse/bleeding/crowdedHard），
以及 buyLand()/tryDonateToTeammate()/idleBoats() 的返回值。
用法：python3 probe_view.py <matchId> [--tag x] [--t0 a --t1 b] [--every 5] [--names]
      python3 probe_view.py <matchId> --tag x --gate <席位> [--t0 a --t1 b]
        --gate：只看对某个目标的报价，逐决策拍复算 buyLand 的几道闸门（v27-team-c116-vb.js L5350–5359、L5414–5447、L5594–5605）：
        worth = 0.5×winRatio×refDens（refDens：2500 拍起取 max(自己密度, 0.85×其他真人密度中位)）；
        预算 = max(0, (worthOwn×领土 − 手续费×m − c×领土)/(1+m))，m = 0.5×winRatio，worthOwn 在 4000 拍后（目标不是 nearCollapse 时）取 m×自己密度；
        价格 keep = max(c×领土/m（nearCollapse 的真人打 7 折）, 余额 − 手续费 − 预算)，c < cheap(=0.1/baseRate) 时为 0；c ≥ worth 时没有价格 keep（记 inf，除非 over）；
        over（余额 > 100×领土）时 keep 不超过 0.9×100×领土（密度 ≥122 时 0.82；isSoleHealthyBuffer 的 1.12 探针里看不到，没有算）；
        保底 = safeAt(目标)，非真人 / nearCollapse / bleeding / tD<0.45 的目标再封顶 88×领土；keep = max(价格 keep, 保底)；avail = 余额 − 手续费 − keep；
        20% 线 = chunk(0.2)×余额：非真人分支和预算分支凑不够 want 且 x 低于它就不发；脉冲想出的兵 ≥ 1.2×need（不含 3×接壤格数）；最小出兵量 = max(4×手续费, 0.04×余额)。
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
mid = a[0]
opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
tag = opt('tag', '')
t0, t1, every = int(opt('t0', 0)), int(opt('t1', 10**9)), int(opt('every', 5))
fn = os.path.join(HERE, '..', 'out', mid, 'shadow_probe' + ('_' + tag if tag else '') + '.txt')
meta = json.load(open(os.path.join(HERE, '..', 'out', mid, 'resim_meta.json')))
names = meta['names']
def nm(q):
    q = int(q)
    return (names[q].replace('[APEX] ', '')[:14] if q < len(names) else 'AI#%d' % q)
cur = {}
order = []
for line in open(fn, encoding='utf8'):
    m = re.match(r't=(\d+) (.*)', line.rstrip('\n'))
    if not m: continue
    t = int(m.group(1)); rest = m.group(2)
    if t < t0 or t > t1: continue
    d = cur.setdefault(t, {})
    if t not in order: order.append(t)
    if rest.startswith('offers() -> '):
        try: d['offers'] = json.loads(rest[len('offers() -> '):])
        except Exception: d['offers_raw'] = rest[:200]
    elif rest.startswith('buyLand() -> '): d['buy'] = rest[len('buyLand() -> '):]
    elif rest.startswith('tryDonateToTeammate() -> '): d['don'] = rest[len('tryDonateToTeammate() -> '):]
    elif rest.startswith('状态 '): d.setdefault('state', rest[3:])
    elif rest.startswith('safeAt('):
        d.setdefault('safe', []).append(rest)
    elif rest.startswith('send('):
        d.setdefault('send', []).append(rest[:120])
    elif rest.startswith('winRatio() -> '): d.setdefault('wr', float(rest.split('-> ')[1]))
    elif rest.startswith('otherHumanMedDens() -> '): d.setdefault('med', float(rest.split('-> ')[1]))
    elif rest.startswith('baseRate() -> '): d.setdefault('br', float(rest.split('-> ')[1]))
gate = opt('gate')
if gate is not None:
    gq = int(gate)
    INF = float('inf')
    print(f"== {mid} 探针[{tag}] 对 {nm(gq)}（席位 {gq}）的闸门复算")
    print("      t     余额   领土  密度 |  单价c  worth |    need | safeAt(封顶后)    预算  价格keep |    avail    20%线  最小出兵量 | 标记 | buyLand")
    for t in order:
        d = cur[t]
        if 'offers' not in d: continue
        o = [x for x in d['offers'] if int(x['q']) == gq]
        ms = re.match(r'bal=(\d+) terr=(\d+) dens=([\d.]+)', d.get('state', ''))
        if not o or not ms: continue
        o = o[0]
        B, L = int(ms.group(1)), max(1, int(ms.group(2)))
        dMe = B / L
        fee = 12 * B // 1024
        m = 0.5 * d.get('wr', 0)
        ref = max(dMe, 0.85 * d.get('med', 0)) if t >= 2500 else dMe
        worth = m * ref
        over = B > 100 * L
        cheap = 0.1 / d['br'] if d.get('br') else 0
        c, person, nc = o['c'], o.get('person', True), o.get('nearCollapse')
        sv = None
        for s in d.get('safe', []):
            m2 = re.match(r'safeAt\((\d+)\) -> ([\d.eE+-]+)', s)
            if m2 and int(m2.group(1)) == gq: sv = float(m2.group(2)); break
        safe = sv
        if safe is not None and (not person or nc or o.get('bleeding') or o.get('tD', 9) < 0.45):
            safe = min(safe, 88 * L)
        keep = INF; budget = None
        if c < cheap: keep = 0
        if c < worth and m > 0:
            worth_own = m * dMe if (t >= 4000 and not nc) else worth
            budget = max(0, (worth_own * L - fee * m - c * L) / (1 + m))
            min_keep = (0.7 if (person and nc) else 1.0) * c * L / m
            keep = min(keep, max(min_keep, B - fee - budget))
        if over:
            keep = min(keep, (0.82 if dMe >= 122 else 0.9) * 100 * L)
        pk = keep
        if safe is not None: keep = max(keep, safe)
        avail = (B - fee - keep) if keep != INF else None
        fl = ''.join(k for k, f in (('M', o.get('onMe')), ('N', nc), ('B', o.get('bleeding')), ('H', o.get('isCrowdedHard')), ('O', over), ('A', not person)) if f)
        f0 = lambda v, w: (f"{v:{w}.0f}" if v is not None and v != INF else f"{'-':>{w}s}")
        print(f"  {t:5d} {B:8d} {L:6d} {dMe:5.1f} | {c:6.1f} {worth:6.1f} | {o['need']:7.0f} | {f0(safe, 14)} {f0(budget, 7)} {f0(pk, 9)} | {f0(avail, 8)} {0.2 * B:8.0f} {max(4 * fee, 0.04 * B):9.0f} | {fl:4s} | {d.get('buy')}")
    print('（标记：M=对方正在打我 N=nearCollapse B=bleeding H=isCrowdedHard O=余额过 100 倍领土 A=非真人（离场壳或 AI）；c ≥ worth 且不 over 时 buyLand 在 L5359 直接退出）')
    sys.exit(0)
for t in order:
    d = cur[t]
    if 'offers' not in d and 'buy' not in d: continue
    if t % every: continue
    st = d.get('state', '')
    ms = re.match(r'bal=(\d+) terr=(\d+) dens=([\d.]+)', st)
    head = f"t={t} " + (f"余额 {ms.group(1)} 领土 {ms.group(2)} 密度 {ms.group(3)}" if ms else st[:60])
    offs = []
    for o in d.get('offers', []):
        fl = ''.join(k for k, f in (('M', o.get('onMe')), ('N', o.get('nearCollapse')), ('B', o.get('bleeding')), ('H', o.get('isCrowdedHard')), ('S', o.get('isDoorSea'))) if f)
        offs.append(f"{nm(o['q'])}:c={o['c']:.0f},need={o['need']:.0f},in={o.get('inAtk', 0):.0f}{',' + fl if fl else ''}")
    print(head + ' | buy=' + str(d.get('buy')) + ' don=' + str(d.get('don')) + ' | ' + ' ; '.join(offs) + (' | ' + ' '.join(d['send']) if d.get('send') else ''))
print('（报价标记：M=对方正在打我 N=nearCollapse B=bleeding H=isCrowdedHard S=隔海门）')
