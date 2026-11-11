#!/usr/bin/env python3
"""probe_view.py — 把 shadow.mjs --probe 打出的 shadow_probe[_tag].txt 压成每个决策拍一行：
状态（余额/领土/密度）、offers() 里每个报价（目标、单价 c、要的兵 need、onMe、来袭兵 inAtk、nearCollapse/bleeding/crowdedHard），
以及 buyLand()/tryDonateToTeammate()/idleBoats() 的返回值。
用法：python3 probe_view.py <matchId> [--tag x] [--t0 a --t1 b] [--every 5] [--names]
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
