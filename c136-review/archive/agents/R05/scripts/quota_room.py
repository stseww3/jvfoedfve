#!/usr/bin/env python3
"""quota_room.py — 调度日志对配额：每条没落地的捐兵，当拍差多少配额、同一拍别的我方号还剩多少额度。

用法：python3 quota_room.py <matchId> [--list] [--sec win,rec,alt,donor,fill]
输入：/tmp/c136-r05/truth/<id>.json（match_truth.mjs 的产物：dispatch、S10、C30、map、squad）
口径：
  - 配额点数按引擎公式复算（game.js donationCost L348–357、donationCapTick L379–383、donationFree L360）：
      t<357: 2+100v/uw；<714: 2+100v/(4uw)；<1071: 2+100v/(10uw)；<2142: 2+100v/(30uw)；<3213: 2+100v/(100uw)；
      t≥3213: 4+100v/软上限(受赠方)（软上限 = 100×地）；uw = 1+陆地/300；t≥4284 不限。
  - 想捐 v = min(存兵×(pct+1)/1024, 存兵−手续费)，手续费 = 64/1024×存兵（game.js donate L404–416）；
    存兵取日志拍重放出来的值（dispatch[].sim[0].B），受赠方已用配额取 S10 里日志拍前最近一个 10 拍采样。
  - 「落地」= 录像里有对应的已执行捐兵（dispatch[].exec）。
  - 「有前线」= C30 里日志拍前最近一个 30 拍采样的 敌方真人邻格 eh > 0。
"""
import json
import sys
from collections import defaultdict

args = sys.argv[1:]
mid = args[0]
LIST = '--list' in args
SEC = set((args[args.index('--sec') + 1] if '--sec' in args else 'win,rec,alt,donor,fill').split(','))
J = json.load(open(f'/tmp/c136-r05/truth/{mid}.json'))
LAND = J['map']['land']
UW = 1 + LAND // 300
S10 = J['S10']
C30 = J['C30']
SQ = {s['p']: s['bot'] for s in J['squad']}
PL = {p['id']: p for p in J['players']}


def cap_at(t):
    """t 拍时的配额上限（每个 t%100==99 的拍结束时加一次）。"""
    c = 15
    k = 99
    while k < t:
        c += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return c


def unit(t, terr_q):
    """每点配额换多少兵。"""
    if t >= 3213:
        return max(terr_q, 1)
    if t < 357:
        return UW / 100
    if t < 714:
        return 4 * UW / 100
    if t < 1071:
        return 10 * UW / 100
    if t < 2142:
        return 30 * UW / 100
    return UW


def cost(t, v, terr_q):
    if t >= 3213:
        return 4 + (100 * v) // max(100 * terr_q, 1)
    div = UW if t < 357 else 4 * UW if t < 714 else 10 * UW if t < 1071 else 30 * UW if t < 2142 else 100 * UW
    return 2 + (100 * v) // div


def base(t):
    return 4 if t >= 3213 else 2


def s10(p, t, key):
    s = S10.get(str(p))
    if not s:
        return 0
    i = min(len(s['t']) - 1, max(0, t // 10 - 1))
    while i > 0 and s['t'][i] > t:
        i -= 1
    return s[key][i]


def c30(p, t, key):
    s = C30.get(str(p))
    if not s:
        return 0
    i = min(len(s['t']) - 1, max(0, t // 30 - 1))
    while i > 0 and s['t'][i] > t:
        i -= 1
    return s[key][i]


def alive(p, t):
    d = PL[p]['deathT']
    return d is None or d < 0 or t < d


def k(v):
    return f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k'


rows = []
for d in J['dispatch']:
    t, p, q = d['t'], d['p'], d['q']
    B = d['sim'][0]['B'] if d.get('sim') else d['myBal']
    fee = 64 * B // 1024
    want = min(B * (d['pct'] + 1) // 1024, B - fee)
    Lq = s10(q, t, 'terr') or 1
    Bq = s10(q, t, 'bal')
    room_recv = max(0, min(150 * Lq - Bq, want))
    used = s10(q, t, 'quota')
    cp = cap_at(t)
    need = cost(t, room_recv, Lq)
    free = t >= 4284
    if d.get('exec'):
        cls = 'exec'
    elif free:
        cls = 'free-not-exec'
    elif need > cp:
        cls = 'single>cap'
    elif used + need > cp:
        cls = 'used+need>cap'
    else:
        cls = 'fits-but-not-exec'
    # 同一拍别的我方号的额度
    alts = []
    for a in SQ:
        if a in (p, q) or not alive(a, t) or s10(a, t, 'terr') < 150:
            continue
        La = s10(a, t, 'terr')
        ua = s10(a, t, 'quota')
        room_pts = cp - ua
        fit = max(0, (room_pts - base(t) + 1)) * unit(t, La) - 1 if room_pts >= base(t) else 0
        fit = max(0, min(fit, 150 * La - s10(a, t, 'bal')))
        alts.append({'p': a, 'room': room_pts, 'fit': fit, 'front': c30(a, t, 'eh') > 0, 'dens': s10(a, t, 'bal') / max(La, 1)})
    rows.append({'t': t, 'p': p, 'q': q, 'kind': d['kind'], 'pct': d['pct'], 'B': B, 'want': want, 'need': need, 'used': used, 'cap': cp,
                 'cls': cls, 'alts': alts, 'exec': d.get('exec'), 'Lq': Lq, 'qfront': c30(q, t, 'eh') > 0,
                 'dMe': B / max(s10(p, t, 'terr'), 1), 'Lp': s10(p, t, 'terr')})

WINS = [(0, 1071), (1071, 2142), (2142, 3213), (3213, 4284), (4284, 99999)]

if 'win' in SEC:
    print(f'== win {mid} 调度日志按配额时段（陆地 {LAND} → uw = {UW}；每点配额：1071–2141 拍 {30 * UW / 100:.0f} 兵、2142–3212 拍 {UW} 兵、3213 拍起 = 受赠方的地）==')
    for a, b in WINS:
        R = [r for r in rows if a <= r['t'] < b]
        if not R:
            continue
        cl = defaultdict(int)
        for r in R:
            cl[r['cls']] += 1
        ex = [r for r in R if r['cls'] == 'exec']
        rej = [r for r in R if r['cls'] in ('single>cap', 'used+need>cap')]
        ratio = sorted(r['need'] / r['cap'] for r in R if r['cls'] == 'single>cap')
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0
        print(f'  t∈[{a},{b}): 日志 {len(R)}｜落地 {len(ex)}（到账 {k(sum(r["exec"]["got"] for r in ex))}）｜单笔所需 > 上限 {cl["single>cap"]}'
              f'（所需÷上限 {ratio[0]:.2f}–{ratio[-1]:.2f}）' if ratio else
              f'  t∈[{a},{b}): 日志 {len(R)}｜落地 {len(ex)}（到账 {k(sum(r["exec"]["got"] for r in ex))}）｜单笔所需 > 上限 0', end='')
        print(f'｜已用+所需 > 上限 {cl["used+need>cap"]}｜放得进却没落地 {cl["fits-but-not-exec"]}｜不限额却没落地 {cl["free-not-exec"]}'
              f'｜被拒的：想捐中位 {k(med([r["want"] for r in rej]))}、所需中位 {med([r["need"] for r in rej])} 点、对方剩余中位 {med([r["cap"] - r["used"] for r in rej])} 点')
        cap_a, cap_b = cap_at(a if a > 0 else 1), cap_at(min(b, 4284) - 1)
        print(f'      上限 {cap_a}→{cap_b} 点；一个受赠方累计最多能收：窗口头 {k(cap_a * unit(a, 0) if a < 3213 else 0)}、窗口尾 {k(cap_b * unit(b - 1, 0) if b <= 3213 else 0)}（3213 拍起按受赠方的地折算）')

if 'rec' in SEC:
    print('== rec 每个受赠方：日志/落地、配额账 ==')
    for q in sorted({r['q'] for r in rows}, key=lambda q: -sum(1 for r in rows if r['q'] == q)):
        R = [r for r in rows if r['q'] == q]
        out = []
        for a, b in WINS:
            W = [r for r in R if a <= r['t'] < b]
            if not W:
                continue
            ex = [r for r in W if r['cls'] == 'exec']
            pts = sum(cost(r['exec']['t'], r['exec']['got'], s10(q, r['exec']['t'], 'terr') or 1) for r in ex) if b <= 4284 else 0
            out.append(f'[{a},{b}) 日志 {len(W)} 落地 {len(ex)} 到账 {k(sum(r["exec"]["got"] for r in ex))} 花 {pts} 点')
        u3213, u4284 = s10(q, 3212, 'quota'), s10(q, 4283, 'quota')
        print(f'  {SQ.get(q, q)}: ' + '；'.join(out))
        print(f'      已用配额：t=2142 {s10(q, 2141, "quota")}/{cap_at(2142)}｜t=3213 {u3213}/{cap_at(3213)}（剩 {cap_at(3213) - u3213} 点；按当时 {s10(q, 3213, "terr")} 格地可再收 {k(max(0, cap_at(3213) - u3213 - 4) * s10(q, 3213, "terr"))}）'
              f'｜t=4284 {u4284}/{cap_at(4284)}')

if 'alt' in SEC:
    print('== alt 被配额拒的那一拍，别的我方号还剩多少额度（只算活着、地 ≥150 的我方号；不含捐出方和原受赠方）==')
    for a, b in WINS[1:4]:
        R = [r for r in rows if a <= r['t'] < b and r['cls'] in ('single>cap', 'used+need>cap')]
        if not R:
            continue
        n_any = sum(1 for r in R if any(x['fit'] >= r['want'] for x in r['alts']))
        n_front = sum(1 for r in R if any(x['fit'] >= r['want'] and x['front'] for x in r['alts']))
        n_half = sum(1 for r in R if any(x['fit'] >= 0.5 * r['want'] and x['front'] for x in r['alts']))
        best_front = sorted(max([x['fit'] for x in r['alts'] if x['front']] or [0]) for r in R)
        best_same = sorted(max(0, (r['cap'] - r['used'] - base(r['t']) + 1) * unit(r['t'], r['Lq']) - 1) if r['cap'] - r['used'] >= base(r['t']) else 0 for r in R)
        n_q_front = sum(1 for r in R if r['qfront'])
        print(f'  t∈[{a},{b}): 被拒 {len(R)} 条｜原受赠方当拍有前线的 {n_q_front} 条｜原受赠方剩余额度能收的兵 中位 {k(best_same[len(best_same) // 2])}'
              f'｜别的我方号里有人放得下整笔的 {n_any} 条，其中那个号有前线的 {n_front} 条；有前线的号放得下半笔的 {n_half} 条｜有前线的号里最大可收 中位 {k(best_front[len(best_front) // 2])}')
        # 哪些号是「放得下整笔、有前线」的
        cnt = defaultdict(int)
        for r in R:
            for x in r['alts']:
                if x['front'] and x['fit'] >= r['want']:
                    cnt[SQ[x['p']]] += 1
        if cnt:
            print('      放得下整笔且有前线的号（被拒条数）：' + ' '.join(f'{b_}:{n}' for b_, n in sorted(cnt.items(), key=lambda kv: -kv[1])))

if 'donor' in SEC:
    print('== donor 每个捐出方：日志/落地/被拒；被拒时自己的密度 ==')
    for p in sorted({r['p'] for r in rows}, key=lambda p: -sum(1 for r in rows if r['p'] == p)):
        R = [r for r in rows if r['p'] == p and r['t'] < 4284]
        if not R:
            continue
        rej = [r for r in R if r['cls'] in ('single>cap', 'used+need>cap')]
        ex = [r for r in R if r['cls'] == 'exec']
        dens = sorted(r['dMe'] for r in rej)
        tg = defaultdict(int)
        for r in R:
            tg[SQ.get(r['q'], r['q'])] += 1
        first_ex = min([r['exec']['t'] for r in ex] or [-1])
        print(f'  {SQ[p]}: t<4284 日志 {len(R)}（首条 t={R[0]["t"]}）落地 {len(ex)}（首笔 t={first_ex}，到账 {k(sum(r["exec"]["got"] for r in ex))}）被拒 {len(rej)}'
              f'｜被拒时密度 中位 {dens[len(dens) // 2] if dens else 0:.0f} 最大 {dens[-1] if dens else 0:.0f}，≥100 的 {sum(1 for x in dens if x >= 100)} 条、≥140 的 {sum(1 for x in dens if x >= 140)} 条｜对象 {dict(tg)}')

if 'fill' in SEC:
    print('== fill 配额上限下最多能流多少（每个受赠方 上限×每点兵数；3213 前）与实际 ==')
    for tt in (2141, 2500, 3000, 3212):
        cp = cap_at(tt)
        mx = cp * unit(tt, 0)
        got = defaultdict(int)
        for r in rows:
            if r['cls'] == 'exec' and r['exec']['t'] <= tt:
                got[r['q']] += r['exec']['got']
        print(f'  t={tt}: 上限 {cp} 点 × {unit(tt, 0):.0f} 兵/点 = 每个受赠方累计最多 {k(mx)}｜实际累计到账：' + (' '.join(f'{SQ[q]}:{k(v)}' for q, v in got.items()) or '无')
              + f'｜我方号合计存兵 {k(sum(s10(p, tt, "bal") for p in SQ))}')

if LIST:
    print('== list ==')
    for r in rows:
        best = max(r['alts'], key=lambda x: (x['front'], x['fit']), default=None)
        print(f'  t={r["t"]} {SQ[r["p"]]}→{SQ.get(r["q"], r["q"])} {r["kind"][:7]} pct={r["pct"]} 想捐 {k(r["want"])} 需 {r["need"]} 点｜对方已用 {r["used"]}/{r["cap"]}｜{r["cls"]}'
              + (f'｜别的号最大可收 {SQ[best["p"]]} {k(best["fit"])}{"（有前线）" if best["front"] else ""}' if best and r['cls'] != 'exec' else ''))
