#!/usr/bin/env python3
"""prey_hazard.py — 敌方真人什么时候对我方号动手：按我方号当时的密度、是否刚把兵花掉分档的「开打率」。

给模拟器里的强敌模型定参数用（COUNCIL-PROPOSAL 议题 1）。只读 13 局逐拍重演真值 /tmp/c136-r05/truth/<局>.json
（match_truth.mjs 产出；events 里有别人打我方号的每条陆攻、每条登陆的船，以及执行前一刻双方的兵和地）。

口径
  敌方真人   座位号 < 真人数、不是我方号、与我方不同队、当时没有离场。
  暴露       每个我方号每 30 拍一条采样（C30）：t ≥ 1500、这个号活着且没离场、陆地边界上贴着至少一个在场的敌方真人。
             一条采样记 30 拍。密度 = 那一拍的兵 ÷ 地（S10）。
  刚花掉     采样前 100 拍内这个号自己执行的陆攻 + 出船 + 捐兵（含手续费 / 税）合计 ≥ 100 拍前存兵的 30%。
  开打       敌方真人 p 对我方号 b 执行的一条陆攻，且此前 100 拍内 p 没有对 b 执行过陆攻。归到开打前最近的一条采样。
             那条采样不在「暴露」里的（比如两条采样之间才接上壤）单列，不进开打率。
  开打率     开打次数 ÷（暴露拍数 ÷ 100）= 每个号每 100 拍被多少个新的敌人开打。
  登陆       敌方真人的船在我方号的地上靠岸（boat-land）；同一个 p 对同一个 b 100 拍内只算第一条。
用法：python3 scripts/prey_hazard.py [--out reports/PREY-HAZARD.md]
"""
import json
import os
import statistics as st
import sys

TRUTH = os.environ.get('C136_TRUTH', '/tmp/c136-r05/truth')
MATCHES = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']
T0 = 1500
BUCKETS = [(0, 30, '<30'), (30, 50, '30–50'), (50, 70, '50–70'), (70, 90, '70–90'), (90, 1e9, '≥90')]


def bucket(d):
    for lo, hi, name in BUCKETS:
        if lo <= d < hi:
            return name
    return BUCKETS[-1][2]


def med(v):
    return st.median(v) if v else None


def fmt(x, nd=2):
    if x is None:
        return '–'
    return f'{x:.{nd}f}'


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '–'


def load(m):
    with open(os.path.join(TRUTH, m + '.json'), encoding='utf-8') as f:
        return json.load(f)


def analyse(m):
    d = load(m)
    H = d['humans']
    players = {p['id']: p for p in d['players']}
    squad = {s['p'] for s in d['squad']}
    our_team = d['ourTeam']

    def enemy_human(p, t):
        if p >= H or p in squad or p not in players:
            return False
        pl = players[p]
        if pl['team'] == our_team and our_team != 0:
            return False
        return pl['leftT'] < 0 or t < pl['leftT']

    ev = d['events']
    own = {b: [] for b in squad}            # 我方号自己花出去的兵 (t, 兵, 种类, 对象)
    for e in ev:
        if e['p'] in squad and e.get('ok', True):
            if e['type'] in ('attack', 'boat'):
                own[e['p']].append((e['t'], e.get('troops', 0) + e.get('fee', 0), 'atk', e.get('q', -1)))
            elif e['type'] == 'donate':
                own[e['p']].append((e['t'], e.get('got', 0) + e.get('fee', 0), 'don', e.get('q', -1)))

    exposure = []      # (局, 号, t, 密度, 刚花掉)
    samples = {}       # (号, t) -> (密度, 刚花掉, 是否暴露)
    for b in squad:
        s10 = d['S10'].get(str(b))
        c30 = d['C30'].get(str(b))
        if not s10 or not c30:
            continue
        idx = {t: i for i, t in enumerate(s10['t'])}
        left_t = players[b]['leftT'] if b in players else -1
        for i, t in enumerate(c30['t']):
            if t < T0 or t not in idx:
                continue
            j = idx[t]
            L, B = s10['terr'][j], s10['bal'][j]
            if L <= 0 or (left_t >= 0 and t >= left_t):
                continue
            dens = B / L
            j0 = idx.get(t - 100)
            rec = [x for x in own[b] if t - 100 < x[0] <= t]
            spent = sum(x[1] for x in rec)
            don = sum(x[1] for x in rec if x[2] == 'don')
            emptied = j0 is not None and s10['bal'][j0] > 0 and spent >= 0.30 * s10['bal'][j0]
            kind = ('don' if don >= 0.5 * spent else 'atk') if emptied else 'none'
            exposed = c30['eh'][i] > 0
            samples[(b, t)] = (dens, emptied, exposed, kind)
            if exposed:
                exposure.append((m, b, t, dens, emptied, kind))

    onsets, unexposed, sea = [], 0, []
    last_atk, last_sea = {}, {}
    death = {b: players[b]['deathT'] for b in squad if b in players}
    for e in ev:
        t, p, q = e['t'], e['p'], e.get('q', -1)
        if q not in squad or not enemy_human(p, t):
            continue
        if e['type'] == 'attack' and e.get('ok', True):
            prev = last_atk.get((p, q))
            last_atk[(p, q)] = t
            if t < T0 or (prev is not None and t - prev < 100):
                continue
            ts = (t // 30) * 30
            s = samples.get((q, ts))
            if s is None or not s[2]:
                unexposed += 1
                continue
            tB, tL, B0, L0 = e.get('tB', 0), e.get('tL', 0), e.get('B0', 0), e.get('L0', 0)
            dt = death.get(q, -1)
            hit_back = any(x[2] == 'atk' and x[3] == p and t - 100 < x[0] <= t for x in own[q])
            onsets.append({
                'm': m, 'b': q, 't': t, 'dens': s[0], 'emptied': s[1], 'kind': s[3], 'hitBack': hit_back,
                'atkDens': B0 / L0 if L0 else None,
                'ratio': B0 / tB if tB else None,
                'volley': (e.get('troops', 0) / tB) if tB else None,
                'pct': e.get('pct', -1),
                'died300': 0 <= dt - t <= 300,
            })
        elif e['type'] == 'boat-land':
            prev = last_sea.get((p, q))
            last_sea[(p, q)] = t
            if t < T0 or (prev is not None and t - prev < 100):
                continue
            ts = (t // 30) * 30
            s = samples.get((q, ts))
            j = None
            s10 = d['S10'].get(str(q))
            if s10:
                idx = {tt: i for i, tt in enumerate(s10['t'])}
                j = idx.get((t // 10) * 10)
            bal = s10['bal'][j] if (s10 and j is not None) else None
            lost = None
            if s10 and j is not None and s10['terr'][j] > 0:
                after = [s10['terr'][k] for k in range(j + 1, len(s10['t'])) if s10['t'][k] <= t + 300]
                lost = (min(after) <= 0.8 * s10['terr'][j]) if after else True
            sea.append({'m': m, 'b': q, 't': t, 'troops': e.get('troops', 0), 'bal': bal, 'lost': lost,
                        'landNb': None if s is None else s[2], 'dens': None if s is None else s[0]})
    # 我方号打真人的一轮（同号同目标、相邻两条间隔 ≤21 拍）之后，对方还不还手
    rounds = []
    by_pair = {}
    for e in ev:
        if e['type'] == 'attack' and e.get('ok', True) and e['p'] in squad and 0 <= e.get('q', -1) < H and e['t'] >= T0:
            if enemy_human(e['q'], e['t']):
                by_pair.setdefault((e['p'], e['q']), []).append(e)
    foe_hits = {}
    for e in ev:
        if e['type'] == 'attack' and e.get('ok', True) and e.get('q', -1) in squad and e['p'] < H and e['p'] not in squad:
            foe_hits.setdefault((e['p'], e['q']), []).append(e['t'])
    for (b, q), lst in by_pair.items():
        lst.sort(key=lambda x: x['t'])
        cur = [lst[0]]
        groups = []
        for e in lst[1:]:
            if e['t'] - cur[-1]['t'] <= 21:
                cur.append(e)
            else:
                groups.append(cur)
                cur = [e]
        groups.append(cur)
        hits = foe_hits.get((q, b), [])
        dt = death.get(b, -1)
        for g in groups:
            t0, t1 = g[0]['t'], g[-1]['t']
            B0, tB = g[0].get('B0', 0), g[0].get('tB', 0)
            if not B0:
                continue
            rounds.append({
                'm': m, 'b': b, 'q': q, 't': t0, 'ratio': tB / B0, 'spent': sum(x.get('troops', 0) + x.get('fee', 0) for x in g) / B0,
                'prior': any(t0 - 300 <= h < t0 for h in hits),
                'back100': any(t0 < h <= t1 + 100 for h in hits),
                'backTroops': None,
                'died600': 0 <= dt - t0 <= 600,
            })
    # 对照：贴着一个存兵 ≥2 倍于己的敌方真人、双方 300 拍内都没动手的采样（相安无事）之后 600 拍内阵亡的比例
    hs = d.get('HS') or {'t': [], 'bal': []}
    hs_t = hs['t']

    def foe_bal(o, t):
        k = -1
        for i, tt in enumerate(hs_t):
            if tt <= t:
                k = i
        return hs['bal'][k][o] if k >= 0 and o < len(hs['bal'][k]) else None

    my_hits = {}
    for (b, q), lst in by_pair.items():
        my_hits[(b, q)] = [e['t'] for e in lst]
    first_strikes = {(r['b'], r['q'], (r['t'] // 30) * 30) for r in rounds if not r['prior'] and r['ratio'] >= 2}
    ctrl = {'quiet': 0, 'quietDead': 0, 'strike': 0, 'strikeDead': 0}
    for b in squad:
        s10 = d['S10'].get(str(b))
        c30 = d['C30'].get(str(b))
        if not s10 or not c30:
            continue
        idx = {t: i for i, t in enumerate(s10['t'])}
        dt = death.get(b, -1)
        for i, t in enumerate(c30['t']):
            if t < T0 or t not in idx or not c30['eh'][i]:
                continue
            B = s10['bal'][idx[t]]
            if s10['terr'][idx[t]] <= 0 or B <= 0:
                continue
            for o, _cnt in c30['top'][i]:
                fb = foe_bal(o, t)
                if fb is None or fb < 2 * B or not enemy_human(o, t):
                    continue
                dead = 0 <= dt - t <= 600
                if (b, o, t) in first_strikes:
                    ctrl['strike'] += 1
                    ctrl['strikeDead'] += dead
                elif not any(t - 300 <= h <= t + 30 for h in my_hits.get((b, o), [])) and not any(t - 300 <= h <= t for h in foe_hits.get((o, b), [])):
                    ctrl['quiet'] += 1
                    ctrl['quietDead'] += dead
    return exposure, onsets, unexposed, sea, rounds, ctrl


def main():
    out = None
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    EXP, ONS, SEA, RND = [], [], [], []
    CTRL = {'quiet': 0, 'quietDead': 0, 'strike': 0, 'strikeDead': 0}
    unexp = 0
    per_match = {}
    for m in MATCHES:
        if not os.path.exists(os.path.join(TRUTH, m + '.json')):
            continue
        e, o, u, s, r, c = analyse(m)
        for k in CTRL:
            CTRL[k] += c[k]
        EXP += e
        ONS += o
        SEA += s
        RND += r
        unexp += u
        per_match[m] = (e, o)
    lines = []
    w = lines.append
    w('# PREY-HAZARD — 敌方真人什么时候对我方号动手（13 局逐拍重演真值）')
    w('')
    w('> 本文件由 `python3 scripts/prey_hazard.py --out reports/PREY-HAZARD.md` 生成，不手改。口径见脚本头注。')
    w('> 暴露 = t ≥ 1500、活着、陆地边界上贴着至少一个在场敌方真人的（我方号 × 30 拍）；开打 = 某个敌方真人 100 拍内第一次对这个号执行陆攻。')
    w('> 开打率 = 每个号每 100 拍被多少个新的敌人开打。这是相关，不是因果：密度低的号本来就多在前线。')
    w('')
    tot_ticks = 30 * len(EXP)
    w(f'合计 {len(per_match)} 局：暴露 {len(EXP):,} 条采样（{tot_ticks:,} 号·拍），开打 {len(ONS):,} 次，开打率 {fmt(100 * len(ONS) / tot_ticks if tot_ticks else None)} 次/百拍；'
      f'另有 {unexp:,} 次开打前最近的采样不在暴露里（两条采样之间才接壤），不计。')
    w('')

    def table(title, rows_key, exp_filter=lambda x: True, ons_filter=lambda x: True):
        w(f'## {title}')
        w('')
        w('| 我方号密度 | 暴露（号·百拍） | 开打（次） | 开打率（次/百拍） | 开打后 300 拍内阵亡 |')
        w('| --: | --: | --: | --: | --: |')
        for lo, hi, name in BUCKETS:
            ex = [x for x in EXP if exp_filter(x) and lo <= x[3] < hi]
            on = [x for x in ONS if ons_filter(x) and lo <= x['dens'] < hi]
            ticks = 30 * len(ex)
            dead = sum(1 for x in on if x['died300'])
            w(f'| {name} | {ticks / 100:,.0f} | {len(on):,} | {fmt(100 * len(on) / ticks if ticks else None)} | {dead}（{pct(dead, len(on))}） |')
        ex = [x for x in EXP if exp_filter(x)]
        on = [x for x in ONS if ons_filter(x)]
        ticks = 30 * len(ex)
        dead = sum(1 for x in on if x['died300'])
        w(f'| 合计 | {ticks / 100:,.0f} | {len(on):,} | {fmt(100 * len(on) / ticks if ticks else None)} | {dead}（{pct(dead, len(on))}） |')
        w('')

    table('1. 按我方号的密度（t ≥ 1500 全程）', None)
    table('2. 1500–4284 拍', None, lambda x: x[2] < 4284, lambda x: x['t'] < 4284)
    table('3. 4284 拍以后', None, lambda x: x[2] >= 4284, lambda x: x['t'] >= 4284)

    w('## 4. 刚把兵花掉的号（前 100 拍自己打出 / 捐出 ≥ 30% 存兵）')
    w('')
    w('| 密度 | 刚花掉 | 暴露（号·百拍） | 开打（次） | 开打率（次/百拍） |')
    w('| --: | --: | --: | --: | --: |')
    for (lo, hi, name) in [(0, 50, '<50'), (50, 90, '50–90'), (90, 1e9, '≥90')]:
        for flag, fname in ((True, '是'), (False, '否')):
            ex = [x for x in EXP if lo <= x[3] < hi and x[4] == flag]
            on = [x for x in ONS if lo <= x['dens'] < hi and x['emptied'] == flag]
            ticks = 30 * len(ex)
            w(f'| {name} | {fname} | {ticks / 100:,.0f} | {len(on):,} | {fmt(100 * len(on) / ticks if ticks else None)} |')
    for flag, fname in ((True, '是'), (False, '否')):
        ex = [x for x in EXP if x[4] == flag]
        on = [x for x in ONS if x['emptied'] == flag]
        ticks = 30 * len(ex)
        w(f'| 合计 | {fname} | {ticks / 100:,.0f} | {len(on):,} | {fmt(100 * len(on) / ticks if ticks else None)} |')
    w('')
    w('按兵是怎么花掉的再分（捐 = 这 100 拍花掉的兵里捐兵占一半以上；其余算打）。「被打的人还手」= 开打的敌人正是这个号前 100 拍打过的人。')
    w('')
    w('| 前 100 拍 | 暴露（号·百拍） | 开打（次） | 开打率（次/百拍） | 其中被打的人还手 | 其中别的敌人 | 别的敌人的开打率 |')
    w('| --: | --: | --: | --: | --: | --: | --: |')
    for kind, kname in (('don', '捐掉 ≥30%'), ('atk', '打掉 ≥30%'), ('none', '没有花掉 30%')):
        ex = [x for x in EXP if x[5] == kind]
        on = [x for x in ONS if x['kind'] == kind]
        hb = sum(1 for x in on if x['hitBack'])
        ticks = 30 * len(ex)
        w(f'| {kname} | {ticks / 100:,.0f} | {len(on):,} | {fmt(100 * len(on) / ticks if ticks else None)} | {hb} | {len(on) - hb} | {fmt(100 * (len(on) - hb) / ticks if ticks else None)} |')
    w('')

    w('## 5. 逐局：密度 <50 的开打率 对 密度 ≥70 的开打率')
    w('')
    w('| 局 | <50：暴露（号·百拍） | 开打 | 开打率 | ≥70：暴露（号·百拍） | 开打 | 开打率 | 比值 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    higher = comparable = 0
    for m, (e, o) in per_match.items():
        lo_t = 30 * sum(1 for x in e if x[3] < 50)
        hi_t = 30 * sum(1 for x in e if x[3] >= 70)
        lo_n = sum(1 for x in o if x['dens'] < 50)
        hi_n = sum(1 for x in o if x['dens'] >= 70)
        lo_h = 100 * lo_n / lo_t if lo_t else None
        hi_h = 100 * hi_n / hi_t if hi_t else None
        ratio = None
        if lo_h is not None and hi_h is not None and lo_t >= 1000 and hi_t >= 1000:
            comparable += 1
            if lo_h > hi_h:
                higher += 1
            ratio = lo_h / hi_h if hi_h else None
        w(f'| {m} | {lo_t / 100:,.0f} | {lo_n} | {fmt(lo_h)} | {hi_t / 100:,.0f} | {hi_n} | {fmt(hi_h)} | {fmt(ratio, 1) if ratio is not None else "–"} |')
    w('')
    w(f'- 两档各有 ≥10 号·百拍暴露的 {comparable} 局里，密度 <50 的开打率高于 ≥70 的 {higher} 局。')
    w('')

    w('## 6. 动手的敌人长什么样（开打那一条陆攻执行前一刻）')
    w('')
    ad = [x['atkDens'] for x in ONS if x['atkDens'] is not None]
    ra = [x['ratio'] for x in ONS if x['ratio'] is not None]
    vo = [x['volley'] for x in ONS if x['volley'] is not None]
    n = len(ONS)
    if n:
        q = st.quantiles(ad, n=4) if len(ad) >= 4 else [None] * 3
        w(f'- 敌人自己的密度：中位 {fmt(med(ad), 0)}（四分位 {fmt(q[0], 0)}–{fmt(q[2], 0)}）；≥90 的 {pct(sum(1 for v in ad if v >= 90), len(ad))}，<50 的 {pct(sum(1 for v in ad if v < 50), len(ad))}。')
        w(f'- 敌人存兵 ÷ 我方号存兵：中位 {fmt(med(ra), 2)}；≥1 的 {pct(sum(1 for v in ra if v >= 1), len(ra))}，≥2 的 {pct(sum(1 for v in ra if v >= 2), len(ra))}，≥4 的 {pct(sum(1 for v in ra if v >= 4), len(ra))}。')
        w(f'- 第一条打出的兵 ÷ 我方号存兵：中位 {fmt(med(vo), 2)}；≥0.5 的 {pct(sum(1 for v in vo if v >= 0.5), len(vo))}，≥1 的 {pct(sum(1 for v in vo if v >= 1), len(vo))}。')
        full = sum(1 for x in ONS if x['pct'] >= 1000)
        w(f'- 第一条的千分比：中位 {fmt(med([x["pct"] + 1 for x in ONS if x["pct"] >= 0]), 0)}；≥1000（全兵）的 {full} 条（{pct(full, n)}）。')
        for lo, hi, name in [(0, 50, '<50'), (50, 90, '50–90'), (90, 1e9, '≥90')]:
            sub = [x for x in ONS if lo <= x['dens'] < hi]
            r2 = [x['ratio'] for x in sub if x['ratio'] is not None]
            w(f'- 我方号密度 {name} 时开打的 {len(sub)} 次：敌人存兵 ÷ 我方号存兵 中位 {fmt(med(r2), 2)}，≥2 的 {pct(sum(1 for v in r2 if v >= 2), len(r2))}。')
    w('')

    w('## 7. 登陆（敌方真人的船在我方号的地上靠岸，t ≥ 1500）')
    w('')
    ns = len(SEA)
    known = [x for x in SEA if x['landNb'] is not None]
    no_nb = [x for x in known if not x['landNb']]
    rel = [x['troops'] / x['bal'] for x in SEA if x['bal']]
    by_m = {}
    for x in SEA:
        by_m[x['m']] = by_m.get(x['m'], 0) + 1
    w(f'- 共 {ns} 次（同一个敌人对同一个号 100 拍内只算第一条），有登陆的 {len(by_m)} 局：' + '、'.join(f'{m} {c}' for m, c in sorted(by_m.items())) + '。')
    w(f'- 登陆时这个号陆地上没有贴着任何在场敌方真人的：{len(no_nb)}/{len(known)}（{pct(len(no_nb), len(known))}）。')
    w(f'- 船上的兵 ÷ 这个号当时的存兵：中位 {fmt(med(rel), 2)}；≥0.5 的 {pct(sum(1 for v in rel if v >= 0.5), len(rel))}。')
    dn = [x['dens'] for x in known]
    w(f'- 被登陆的号当时的密度：中位 {fmt(med(dn), 0)}；<50 的 {pct(sum(1 for v in dn if v < 50), len(dn))}。')
    for flag, name in ((False, '陆上没有贴着敌方真人的号'), (True, '陆上已经贴着敌方真人的号')):
        sub_ = [x for x in known if x['landNb'] == flag and x['lost'] is not None]
        lost = sum(1 for x in sub_ if x['lost'])
        w(f'- {name}被登陆 {len(sub_)} 次：之后 300 拍内地掉到 80% 以下（含阵亡）的 {lost} 次（{pct(lost, len(sub_))}）。')
    w('')
    w('## 8. 我方号打真人的一轮之后，对方还不还手（t ≥ 1500）')
    w('')
    w('一轮 = 同一个号对同一个敌方真人、相邻两条间隔 ≤21 拍的陆攻。先手 = 这一轮开始前 300 拍内对方没有对这个号执行过陆攻。')
    w('还手 = 这一轮开始后、到最后一条之后 100 拍为止，对方对这个号执行了陆攻。目标强弱 = 第一条执行前一刻 对方存兵 ÷ 我方号存兵。')
    w('')
    w('| 目标强弱 | 轮数 | 其中先手 | 先手里对方还手 | 先手里这个号 600 拍内阵亡 | 不是先手（对方已在打）的轮 | 其中 600 拍内阵亡 | 每轮花掉的存兵（中位） |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    for lo, hi, name in [(0, 0.5, '<0.5 倍'), (0.5, 1, '0.5–1 倍'), (1, 2, '1–2 倍'), (2, 4, '2–4 倍'), (4, 1e12, '≥4 倍')]:
        sub_ = [x for x in RND if lo <= x['ratio'] < hi]
        first = [x for x in sub_ if not x['prior']]
        back = sum(1 for x in first if x['back100'])
        dead = sum(1 for x in first if x['died600'])
        late = [x for x in sub_ if x['prior']]
        dead2 = sum(1 for x in late if x['died600'])
        w(f'| {name} | {len(sub_):,} | {len(first):,} | {back}（{pct(back, len(first))}） | {dead}（{pct(dead, len(first))}） | {len(late):,} | {dead2}（{pct(dead2, len(late))}） | {pct(med([x["spent"] for x in sub_]) or 0, 1) if sub_ else "–"} |')
    first = [x for x in RND if not x['prior']]
    back = sum(1 for x in first if x['back100'])
    dead = sum(1 for x in first if x['died600'])
    late = [x for x in RND if x['prior']]
    dead2 = sum(1 for x in late if x['died600'])
    w(f'| 合计 | {len(RND):,} | {len(first):,} | {back}（{pct(back, len(first))}） | {dead}（{pct(dead, len(first))}） | {len(late):,} | {dead2}（{pct(dead2, len(late))}） | {pct(med([x["spent"] for x in RND]) or 0, 1) if RND else "–"} |')
    w('')
    for lo, hi, name in [(0, 2, '<2 倍'), (2, 1e12, '≥2 倍')]:
        first = [x for x in RND if lo <= x['ratio'] < hi and not x['prior']]
        back = sum(1 for x in first if x['back100'])
        dead = sum(1 for x in first if x['died600'])
        w(f'- 全程、目标{name}：先手 {len(first)} 轮，对方还手 {back}（{pct(back, len(first))}），这个号 600 拍内阵亡 {dead}（{pct(dead, len(first))}）。')
    for nm, cond in (('1500–4284 拍', lambda x: x['t'] < 4284), ('4284 拍以后', lambda x: x['t'] >= 4284)):
        for lo, hi, name in [(0, 1, '比自己弱'), (1, 2, '1–2 倍'), (2, 1e12, '≥2 倍')]:
            first = [x for x in RND if cond(x) and lo <= x['ratio'] < hi and not x['prior']]
            back = sum(1 for x in first if x['back100'])
            dead = sum(1 for x in first if x['died600'])
            w(f'- {nm}、目标{name}：先手 {len(first)} 轮，对方还手 {back}（{pct(back, len(first))}），这个号 600 拍内阵亡 {dead}（{pct(dead, len(first))}）。')
    w('')
    w('对照（同样贴着一个存兵 ≥2 倍于己的敌方真人；对方存兵取最近一次 300 拍采样，只看接触最多的两个敌邻）：')
    w('')
    w(f'- 相安无事的采样（双方前 300 拍都没对对方动手，这个号之后 30 拍也没动手）：{CTRL["quiet"]:,} 条，之后 600 拍内这个号阵亡的 {CTRL["quietDead"]:,} 条（{pct(CTRL["quietDead"], CTRL["quiet"])}）。')
    w(f'- 这个号先手打它的那条采样：{CTRL["strike"]:,} 条，之后 600 拍内阵亡的 {CTRL["strikeDead"]:,} 条（{pct(CTRL["strikeDead"], CTRL["strike"])}）。')
    w('- 采样每 30 拍一条，同一个号连续的采样不独立；这两行只比方向。')
    w('')
    text = '\n'.join(lines) + '\n'
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text)
        print('→', out)
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
