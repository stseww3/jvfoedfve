#!/usr/bin/env python3
"""truth_digest.py — 把 match_truth.mjs 导出的一局真账 JSON 打成可读摘要（供逐局复盘取数；每个数字都来自逐拍重演）。

用法：python3 truth_digest.py <matchId> [--sec 0,1,2,...] [--dir /tmp/c136-r05/truth]
分节：0 局况 ｜1 各队时间线 ｜2 我方号总表 ｜3 路人队友与敌队大号 ｜4 队间抢地流 ｜5 我方号两两战账 ｜
      6 阵亡/离场号最后 600 拍 ｜7 捐兵真账与调度对账 ｜8 兵力骤降窗口(90 拍跌 ≥30%)收支分解 ｜9 每号每 300 拍经济体检 ｜10 客户端落后与指令延迟
可选：--bots a,b 只看这些号（6/8/9 节）；--t0 --t1 限定 9 节的时间范围
"""
import json
import sys
from collections import defaultdict

args = sys.argv[1:]
mid = args[0]
secs = set(range(11))
tdir = '/tmp/c136-r05/truth'
if '--sec' in args:
    secs = set(int(x) for x in args[args.index('--sec') + 1].split(','))
if '--dir' in args:
    tdir = args[args.index('--dir') + 1]
J = json.load(open(f'{tdir}/{mid}.json'))
only = set(args[args.index('--bots') + 1].split(',')) if '--bots' in args else None
T0 = int(args[args.index('--t0') + 1]) if '--t0' in args else 0
T1 = int(args[args.index('--t1') + 1]) if '--t1' in args else 10 ** 9
DATA = '/agent/repos/c136-data'
H = J['humans']
land = J['map']['land']
P = J['players']
nT = J['humanTeams']
our = J['ourTeam']
squad = [s['p'] for s in J['squad']]
sqname = {s['p']: s['bot'] for s in J['squad']}
CATS = J['cats']
PEER = {b['p'] for b in (J.get('peer') or {}).get('bots', [])}


def nm(p):
    if p >= 512:
        return '中立'
    if p >= H:
        return f'机器人#{p}'
    if p in sqname:
        return sqname[p]
    n = P[p]['name']
    return f"{n[:18]}(#{p},T{P[p]['team']}{',同房另一编队号' if p in PEER else ''})"


def pct(x):
    return f'{100.0 * x / land:.1f}'


def k(x):
    return f'{x / 1000:.0f}k' if abs(x) >= 10000 else str(int(x))


def idx_at(ts, t):
    """最后一个 <= t 的下标，没有则 -1"""
    lo, hi = 0, len(ts) - 1
    r = -1
    while lo <= hi:
        m = (lo + hi) // 2
        if ts[m] <= t:
            r = m
            lo = m + 1
        else:
            hi = m - 1
    return r


T30 = J['T30']
end = J['endTick']

if 0 in secs:
    print(f"== 0 局况 {mid} ==")
    print(f"地图 {J['map']['idx']}_{J['map']['seed']} {J['map']['W']}x{J['map']['H']} 陆地 {land}；真人 {H}；录像头队数 {J['headerTeams']} → 实际真人队 {nT}（人数 {'/'.join(map(str, J['teamSizes']))}；队色 {'/'.join(J['teamColor'][1:])}）；重演到 t={end}")
    print(f"我方队 T{our}（{J['teamColor'][our] if our < len(J['teamColor']) else '?'}）；本盘里的我方号 {len(squad)} 个：" + ' '.join(f"{sqname[p]}#{p}" for p in squad))
    miss = [b for b in J['logBots'] if b not in sqname.values()]
    if miss:
        print(f"日志里有、但不在这盘录像里的号（拆盘）：{' '.join(miss)}")
    mates = [p for p in P if p['team'] == our and not p['squad']]
    pe = J.get('peer') or {}
    if pe.get('bots'):
        byT = defaultdict(list)
        for b in pe['bots']:
            byT[P[b['p']]['team']].append(f"{b['name'][:14]}#{b['p']}" + ('' if b['nameOk'] else '(名字对不上)'))
        print(f"同房间另一支编队 {pe['matchId']}（{pe['cohort']}）在本盘 {len(pe['bots'])} 个号：" + '；'.join(f"T{t}: {' '.join(v)}" for t, v in sorted(byT.items())))
    print(f"我方队路人队友 {len(mates)} 人；敌队：" + '；'.join(f"T{t} {J['teamSizes'][t - 1]} 人" for t in range(1, nT + 1) if t != our))
    print(f"指令统计 {J['stats']}（attackFail = 录像里有、但执行时没有接壤战线而落空的进攻）")

if 1 in secs:
    print("\n== 1 各队时间线（地占全图%｜兵｜在场真人/存活真人；机=机器人与无队；我方号=本盘我方号合计）==")
    want = [90, 180, 270, 360, 450, 600, 750, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500]
    want = [t for t in want if t < end] + [T30['t'][-1]]
    hdr = 't\t' + '\t'.join(f"T{t}{'*' if t == our else ''}" for t in range(1, nT + 1)) + '\t机\t中立%\t我方号\t我方队名次'
    print(hdr)
    for t in want:
        i = idx_at(T30['t'], t)
        if i < 0:
            continue
        L, B, A, Ac = T30['land'][i], T30['bal'][i], T30['alive'][i], T30['active'][i]
        cells = [f"{pct(L[tm])}%|{k(B[tm])}|{Ac[tm]}/{A[tm]}" for tm in range(1, nT + 1)]
        neutral = land - sum(L)
        rank = 1 + sum(1 for tm in range(1, nT + 1) if L[tm] > L[our])
        print(f"{T30['t'][i]}\t" + '\t'.join(cells) + f"\t{pct(L[0])}%|{A[0]}\t{pct(neutral)}\t{pct(T30['squadLand'][i])}%|{k(T30['squadBal'][i])}|{T30['squadActive'][i]}/{T30['squadAlive'][i]}\t{rank}/{nT}")
    # 我方队份额峰值
    best = max(range(len(T30['t'])), key=lambda i: T30['land'][i][our])
    print(f"我方队份额峰值 {pct(T30['land'][best][our])}% @t={T30['t'][best]}；我方号合计峰值 {pct(max(T30['squadLand']))}% @t={T30['t'][max(range(len(T30['t'])), key=lambda i: T30['squadLand'][i])]}")
    # 领先队变化
    lead_prev = None
    chg = []
    for i, t in enumerate(T30['t']):
        L = T30['land'][i]
        lead = max(range(1, nT + 1), key=lambda tm: L[tm])
        if lead != lead_prev:
            chg.append(f"t={t}→T{lead}({pct(L[lead])}%)")
            lead_prev = lead
    print('领先队变化：' + ' '.join(chg[:40]))

S10 = J['S10']
C30 = J['C30']
F30 = J['F30']


def s_at(p, t, key):
    s = S10[str(p)]
    i = idx_at(s['t'], t)
    return s[key][i] if i >= 0 else None


if 2 in secs:
    print("\n== 2 我方号总表 ==")
    print("号\t出生点\tt90\tt180\tt270\tt360\tt600\tt900\tt1200\tt1500\t真人中地排名(拍:名次/存活真人)\t峰值地@拍\t离场\t阵亡\t终地\t拿地(中立/机器人/真人)\t丢地\t投兵(中立/机器人/真人)\t陆攻/船\t捐出(笔/到账/税)\t收到(笔/兵)")
    for p in squad:
        pl = P[p]
        ts = [90, 180, 270, 360, 600, 900, 1200, 1500]
        terr = []
        for t in ts:
            v = s_at(p, t, 'terr')
            i = idx_at(S10[str(p)]['t'], t)
            terr.append(str(v) if (v is not None and S10[str(p)]['t'][i] == t) else '-')
        HS = J['HS']
        rk = []
        for tt in (600, 1500, 3000):
            if tt in HS['t']:
                arr = HS['terr'][HS['t'].index(tt)]
                alive_h = sorted([x for x in arr if x > 0], reverse=True)
                if arr[p] > 0:
                    rk.append(f"{tt}:{1 + sum(1 for x in alive_h if x > arr[p])}/{len(alive_h)}")
        terr.append(' '.join(rk))
        print(f"{sqname[p]}#{p}\t({pl['spawn'][0]},{pl['spawn'][1]})\t" + '\t'.join(terr) + f"\t{pl['peakTerr']}@{pl['peakT']}\t{pl['leftT'] if pl['leftT'] >= 0 else '-'}\t{pl['deathT'] if pl['deathT'] >= 0 else '-'}\t{pl['endTerr']}\t{k(pl['tilesN'])}/{k(pl['tilesB'])}/{k(pl['tilesH'])}\t{k(pl['tilesLost'])}\t{k(pl['sentN'])}/{k(pl['sentB'])}/{k(pl['sentH'])}\t{pl['nAtk']}/{pl['nBoat']}\t{pl['donOutN']}/{k(pl['donOutV'])}/{k(pl['donOutFee'])}\t{pl['donInN']}/{k(pl['donInV'])}")

if 3 in secs:
    print("\n== 3 路人队友与各队大号（按峰值地排序，每队前 6）==")
    for tm in range(1, nT + 1):
        ms = sorted([p for p in P if p['team'] == tm], key=lambda p: -p['peakTerr'])
        left = sum(1 for p in ms if p['leftT'] >= 0)
        died = sum(1 for p in ms if p['deathT'] >= 0)
        don = sum(p['donOutN'] for p in ms if not p['squad'])
        print(f"T{tm}{'*' if tm == our else ''}：{len(ms)} 人，离场 {left}，阵亡 {died}，非我方号捐兵 {don} 笔；拿地合计 中立 {k(sum(p['tilesN'] for p in ms))}/机器人 {k(sum(p['tilesB'] for p in ms))}/真人 {k(sum(p['tilesH'] for p in ms))}；投向真人的兵 {k(sum(p['sentH'] for p in ms))}")
        for p in ms[:6]:
            tag = '我方号' if p['squad'] else ''
            print(f"   {p['name'][:22]}#{p['id']} {tag} 峰值 {p['peakTerr']}({pct(p['peakTerr'])}%)@{p['peakT']} 离场 {p['leftT'] if p['leftT'] >= 0 else '-'} 阵亡 {p['deathT'] if p['deathT'] >= 0 else '-'} 终地 {p['endTerr']} 拿地 {k(p['tilesN'])}/{k(p['tilesB'])}/{k(p['tilesH'])} 投真人 {k(p['sentH'])} 陆攻 {p['nAtk']} 船 {p['nBoat']} 捐 {p['donOutN']}")
    # 全场前 4 名随时间
    print('全场地最多的 4 个玩家（每 600 拍）：')
    for i, t in enumerate(T30['t']):
        if t % 600 == 0 and t > 0:
            print(f"   t={t}: " + '  '.join(f"{nm(a)} {pct(b)}%/{k(c)}" for a, b, c in T30['top'][i][:4]))
    HS = J['HS']
    for tt in (600, 1500):
        if tt in HS['t']:
            arr = HS['terr'][HS['t'].index(tt)]
            hs = sorted([x for x in arr if x > 0])
            sqv = sorted([arr[p] for p in squad if arr[p] > 0])
            if hs and sqv:
                print(f"   t={tt} 存活真人地：中位 {hs[len(hs) // 2]} 上四分位 {hs[(3 * len(hs)) // 4]} 最大 {hs[-1]}；我方号：中位 {sqv[len(sqv) // 2]} 最大 {sqv[-1]} 最小 {sqv[0]}")
    # 终局前三名：吃了谁、谁喂了它
    tops = sorted(P, key=lambda x: -x['peakTerr'])[:3]
    for tp in tops:
        vic = defaultdict(int)
        for w, a_, b_, v in J['pairAll']:
            if a_ == tp['id']:
                vic[b_] += v
        def vn(x):
            return '中立' if x == 512 else ('机器人' if x == 600 else nm(x))
        vs = sorted(vic.items(), key=lambda kv: -kv[1])[:7]
        don = defaultdict(lambda: [0, 0])
        for t_, p_, q_, got, fee in J['allDon']:
            if q_ == tp['id']:
                don[p_][0] += 1
                don[p_][1] += got
        ds = sorted(don.items(), key=lambda kv: -kv[1][1])[:5]
        print(f"   {nm(tp['id'])} 峰值 {pct(tp['peakTerr'])}%：拿地来源 " + '；'.join(f"{vn(x)} {pct(v)}%" for x, v in vs) + '｜收到捐兵 ' + ('；'.join(f"{nm(x)} {n}笔 {k(v)}" for x, (n, v) in ds) if ds else '无'))
        byw = defaultdict(int)
        for w, a_, b_, v in J['pairAll']:
            if a_ == tp['id'] and b_ < 512:
                byw[w] += v
        print('      每 600 拍从真人手里拿地：' + ' '.join(f"{w * 600}:{pct(v)}%" for w, v in sorted(byw.items())))
    # 各时刻离场数
    for tm in range(1, nT + 1):
        ms = [p for p in P if p['team'] == tm]
        row = []
        for t in [300, 600, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000]:
            if t > end:
                break
            row.append(f"{t}:{sum(1 for p in ms if 0 <= p['leftT'] <= t)}/{sum(1 for p in ms if 0 <= p['deathT'] <= t)}")
        print(f"T{tm} 累计 离场/阵亡：" + ' '.join(row))

if 4 in secs:
    print("\n== 4 队间抢地流（每 600 拍；A←B = A 从 B 手里拿走的像素；只列 ≥ 全图 0.5% 的流；机=机器人，中=中立）==")
    agg = defaultdict(int)
    for r in J['teamFlow']:
        agg[(r['w'] // 2, r['from'], r['to'])] += r['tiles']
    ws = sorted({a[0] for a in agg})

    def tn(x):
        return '机' if x == 0 else ('中' if x == nT + 1 else f"T{x}{'*' if x == our else ''}")
    for w in ws:
        items = [(v, f, t) for (ww, f, t), v in agg.items() if ww == w and v >= 0.005 * land]
        items.sort(reverse=True)
        print(f"t={w * 600}-{w * 600 + 599}: " + '  '.join(f"{tn(f)}←{tn(t)} {pct(v)}%" for v, f, t in items))

if 5 in secs:
    print("\n== 5 我方号两两战账（全程合计；投兵=进攻投入的兵，拿地=拿走的像素，打掉=直接打掉对方的存兵）==")
    by_def = defaultdict(list)
    by_att = defaultdict(list)
    for r in J['pairs']:
        if r['b'] in sqname:
            by_def[r['b']].append(r)
        if r['a'] in sqname:
            by_att[r['a']].append(r)
    first_last = defaultdict(lambda: [10 ** 9, -1])
    for r in J['pairsW']:
        if r['tiles'] > 0 or r['sent'] > 0:
            fl = first_last[(r['a'], r['b'])]
            fl[0] = min(fl[0], r['w'] * 100)
            fl[1] = max(fl[1], r['w'] * 100 + 99)
    for p in squad:
        rows = sorted([r for r in by_def[p] if r['a'] < 512], key=lambda r: -r['tiles'])[:5]
        print(f"{sqname[p]}#{p} 被打（按被拿走的地排序）：" + ('（无）' if not rows else ''))
        for r in rows:
            fl = first_last[(r['a'], r['b'])]
            print(f"   {nm(r['a'])} 投兵 {k(r['sent'])}({r['n']}笔) 拿地 {r['tiles']} 打掉存兵 {k(r['balDmg'])} 时段 {fl[0]}-{fl[1]}")
        rows = sorted([r for r in by_att[p]], key=lambda r: -r['sent'])[:6]
        print(f"{sqname[p]}#{p} 打别人（按投兵排序）：")
        for r in rows:
            fl = first_last[(r['a'], r['b'])]
            print(f"   → {nm(r['b'])} 投兵 {k(r['sent'])}({r['n']}笔) 拿地 {r['tiles']} 打掉存兵 {k(r['balDmg'])} 退回 {k(r['ret'])} 时段 {fl[0]}-{fl[1]}")

EV = J['events']


def fmt_ev(e):
    t = e['type']
    if t == 'attack':
        return f"t={e['t']} {nm(e['p'])} 陆攻→{nm(e['q'])} pct={e['pct']} {'成' if e['ok'] else '落空'} 存兵 {k(e['B0'])} 地 {e['L0']} 投 {k(e['troops'])}（对方 兵 {k(e.get('tB', 0))} 地 {e.get('tL', 0)}）"
    if t == 'boat':
        return f"t={e['t']} {nm(e['p'])} 出船→{nm(e['q'])} pct={e['pct']} {'成' if e['ok'] else '落空'} 存兵 {k(e['B0'])} 载 {k(e['troops'])} 航程 {e.get('routeLen', 0)}"
    if t == 'donate':
        return f"t={e['t']} {nm(e['p'])} 捐→{nm(e['q'])} pct={e['pct']} {'成' if e['ok'] else '拒'} 捐出方存兵 {k(e['B0'])} 到账 {k(e['got'])} 税 {k(e['fee'])}（收款方 兵 {k(e['qB0'])} 地 {e['qL0']}；配额 {e.get('quotaAfter')}/{e.get('cap')}）"
    if t == 'boat-land':
        return f"t={e['t']} {nm(e['p'])} 的船登陆→{nm(e['q'])} 兵 {k(e['troops'])}"
    if t == 'leave':
        return f"t={e['t']} {nm(e['p'])} 离场（地 {e.get('L0')} 兵 {k(e.get('B0', 0))}）"
    if t == 'died':
        return f"t={e['t']} {nm(e['p'])} 阵亡"
    if t == 'retreat':
        return f"t={e['t']} {nm(e['p'])} 撤回对 {nm(e['q'])} 的进攻 兵 {k(e.get('troops', 0))}"
    return f"t={e['t']} {nm(e['p'])} {t}"


def flows_between(p, t0, t1):
    f = F30[str(p)]
    i0, i1 = idx_at(f['t'], t0), idx_at(f['t'], t1)
    if i0 < 0 or i1 < 0:
        return None
    return [f['flows'][i1][c] - f['flows'][i0][c] for c in range(len(CATS))]


def contact_str(p, t):
    c = C30[str(p)]
    i = idx_at(c['t'], t)
    if i < 0:
        return '-'
    top = ' '.join(f"{nm(a)}:{n}" for a, n in c['top'][i])
    return f"中立 {c['neut'][i]} 敌真人 {c['eh'][i]} 敌离场 {c['el'][i]} 机器人 {c['bot'][i]} 我方号 {c['mateS'][i]} 路人队友 {c['mateO'][i]}｜{top}"


if 6 in secs:
    print("\n== 6 阵亡/离场号的最后 600 拍（每 60 拍一行：地｜兵｜密度｜在外进攻兵｜被真人打的兵｜被机器人打的兵｜边界接触）==")
    for p in squad:
        if only and sqname[p] not in only:
            continue
        pl = P[p]
        marks = []
        if pl['leftT'] >= 0:
            marks.append(('离场', pl['leftT']))
        if pl['deathT'] >= 0:
            marks.append(('阵亡', pl['deathT']))
        if not marks:
            print(f"-- {sqname[p]}#{p}：活到录像结束（终地 {pl['endTerr']} 终兵 {k(pl['endBal'])}）")
            continue
        print(f"-- {sqname[p]}#{p}：" + '，'.join(f"{a} t={b}" for a, b in marks) + f"；峰值地 {pl['peakTerr']}@{pl['peakT']}")
        for label, tt in marks:
            t0 = max(0, tt - 600)
            s = S10[str(p)]
            print(f"   [{label}前] ")
            for t in list(range(t0 - t0 % 60, tt, 60)) + [tt - 1]:
                i = idx_at(s['t'], t)
                if i < 0:
                    continue
                terr, bal = s['terr'][i], s['bal'][i]
                print(f"   t={s['t'][i]} 地 {terr}｜兵 {k(bal)}｜密度 {bal / max(terr, 1):.0f}｜外 {k(s['out'][i])}｜真人打 {k(s['inH'][i])}｜机打 {k(s['inB'][i])}｜{contact_str(p, s['t'][i])}")
            evs = [e for e in EV if t0 <= e['t'] <= tt and (e['p'] == p or e.get('q') == p) and e['type'] in ('attack', 'donate', 'boat', 'leave', 'died', 'boat-land', 'retreat')]
            inc = [e for e in evs if e.get('q') == p and e['p'] != p]
            own = [e for e in evs if e['p'] == p]
            print(f"   这 600 拍：自己发指令 {len(own)} 条（陆攻 {sum(1 for e in own if e['type'] == 'attack')}，船 {sum(1 for e in own if e['type'] == 'boat')}，捐 {sum(1 for e in own if e['type'] == 'donate')}）；别人对它 {len(inc)} 条")
            for e in inc[-12:]:
                print('     ' + fmt_ev(e))
            for e in own[-8:]:
                print('     自己：' + fmt_ev(e))
            fl = flows_between(p, t0, tt - 1)
            if fl:
                print('   收支：' + ' '.join(f"{CATS[c]} {k(v)}" for c, v in enumerate(fl) if abs(v) >= 1))
            # 窗口战账
            w0, w1 = t0 // 100, tt // 100
            agg = defaultdict(lambda: [0, 0, 0])
            for r in J['pairsW']:
                if r['b'] == p and w0 <= r['w'] <= w1:
                    a = agg[r['a']]
                    a[0] += r['sent']
                    a[1] += r['tiles']
                    a[2] += r['balDmg']
            rows = sorted(agg.items(), key=lambda kv: -kv[1][1])[:5]
            print('   这段时间打它的：' + '；'.join(f"{nm(a)} 投 {k(v[0])} 拿地 {v[1]} 打掉兵 {k(v[2])}" for a, v in rows))

if 7 in secs:
    print("\n== 7 捐兵真账（录像里真正执行的）与调度日志对账 ==")
    dons = [e for e in EV if e['type'] == 'donate']
    out = [e for e in dons if e['p'] in sqname]
    inn = [e for e in dons if e['q'] in sqname and e['p'] not in sqname]
    print(f"我方号捐出 {len(out)} 笔：到账合计 {k(sum(e['got'] for e in out))}，税合计 {k(sum(e['fee'] for e in out))}；路人队友捐给我方号 {len(inn)} 笔，到账 {k(sum(e['got'] for e in inn))}")
    for e in out + inn:
        q = e['q']
        extra = ''
        if q in sqname:
            inH = s_at(q, e['t'], 'inH')
            fl = flows_between(q, e['t'] - e['t'] % 30, e['t'] - e['t'] % 30 + 150)
            if fl:
                extra = f"｜收款号当时被真人打 {k(inH or 0)}；之后150拍 打真人 {k(-fl[3])} 打机器人 {k(-fl[2])} 打中立 {k(-fl[1])} 出船 {k(-fl[4])} 被打掉 {k(-fl[8])} 再捐出 {k(-fl[5])}"
        print('  ' + fmt_ev(e) + f" 捐出方密度 {e['B0'] / max(e['L0'], 1):.0f} 收款方密度 {e['qB0'] / max(e['qL0'], 1):.0f}" + extra)
    D = J['dispatch']
    inrep = [d for d in D if d['p'] >= 0]
    ex = [d for d in inrep if d['exec']]
    print(f"调度日志 {len(D)} 条（发出方在本盘录像里的 {len(inrep)} 条）：录像里有对应已执行捐兵 {len(ex)} 条，没有 {len(inrep) - len(ex)} 条")
    reasons = defaultdict(int)
    for d in inrep:
        if d['exec']:
            continue
        rs = [s['reason'] for s in d['sim']]
        key = rs[2] if len(rs) > 2 else (rs[-1] if rs else '?')
        if all(r != 'ok' for r in rs):
            reasons[f'四个试算拍都会被拒（+14拍处原因：{key}）'] += 1
        elif all(r == 'ok' for r in rs):
            reasons['四个试算拍都能通过（指令没到引擎或另有原因）'] += 1
        else:
            reasons['试算拍里有的通过有的被拒：' + '/'.join(rs)] += 1
    for kx, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"   未执行原因 {v} 条：{kx}")
    lags = sorted(d['exec']['t'] - d['t'] for d in ex)
    if lags:
        print(f"   已执行的那些：日志拍→执行拍 延迟 中位 {lags[len(lags) // 2]} 最大 {lags[-1]} 拍；捐出方日志 myBal 与执行时存兵之差中位 {sorted(abs(d['exec']['B0'] - d['myBal']) for d in ex)[len(ex) // 2]}")
    shown = 0
    for d in inrep:
        if d['exec']:
            continue
        s = d['sim'][2] if len(d['sim']) > 2 else (d['sim'][-1] if d['sim'] else None)
        if s is None:
            continue
        ex_s = f" 已用配额 {s['extra']['used']} + 本笔 {s['extra']['cost']} > 上限 {s['extra']['cap']}（想捐 {k(s['extra']['want'])}）" if s.get('extra') else ''
        print(f"   未执行例：t={d['t']} {d['bot']} {d['kind']} pct={d['pct']} → {nm(d['q'])} 日志 myBal {k(d['myBal'])} dMe {d['dMe']} dAlly {d['dAlly']}｜+14拍试算：{s['reason']}{ex_s}；收款方 兵 {k(s['qB'])} 地 {s['qL']}（上限 {k(150 * s['qL'])}）")
        shown += 1
        if shown >= 14:
            break
    # 每号：日志条数/执行条数
    per = defaultdict(lambda: [0, 0])
    for d in inrep:
        per[d['bot']][0] += 1
        per[d['bot']][1] += 1 if d['exec'] else 0
    print('   每号 日志/执行：' + ' '.join(f"{b}:{v[0]}/{v[1]}" for b, v in per.items()))
    # 没有对应调度日志的我方已执行捐兵
    used = {(d['p'], d['exec']['t']) for d in ex}
    orphan = [e for e in out if e['ok'] and (e['p'], e['t']) not in used]
    if orphan:
        print(f"   录像里我方号已执行、但 80 拍内找不到同 pct 调度日志的捐兵 {len(orphan)} 笔：" + '；'.join(f"t={e['t']} {nm(e['p'])}→{nm(e['q'])} pct={e['pct']} 到账 {k(e['got'])}" for e in orphan[:8]))

if 8 in secs:
    print("\n== 8 兵力骤降窗口（90 拍内存兵跌 ≥30%，窗口对齐 90 拍）收支分解 ==")
    for p in squad:
        if only and sqname[p] not in only:
            continue
        s = S10[str(p)]
        pl = P[p]
        stop = pl['leftT'] if pl['leftT'] >= 0 else (pl['deathT'] if pl['deathT'] >= 0 else end)
        t = 90
        while t + 90 <= stop:
            i0, i1 = idx_at(s['t'], t), idx_at(s['t'], t + 90)
            if i0 >= 0 and i1 >= 0 and s['t'][i0] == t and s['t'][i1] == t + 90:
                b0, b1 = s['bal'][i0], s['bal'][i1]
                if b0 >= 2000 and b1 <= 0.7 * b0:
                    fl = flows_between(p, t, t + 90)
                    resid = (b1 - b0) - sum(fl) if fl else 0
                    parts = ' '.join(f"{CATS[c]} {k(v)}" for c, v in enumerate(fl) if abs(v) >= max(1, 0.02 * b0)) if fl else ''
                    print(f"{sqname[p]} t={t}-{t + 90}: 兵 {k(b0)}→{k(b1)}（{100 * (b1 - b0) / b0:.0f}%） 地 {s['terr'][i0]}→{s['terr'][i1]}｜{parts}｜残差 {k(resid)}")
            t += 90

if 9 in secs:
    print("\n== 9 每号每 300 拍经济体检（地｜兵｜密度｜兵/软上限%｜窗口内：利息地租 / 罚息损失 / 打中立 / 打机器人 / 打真人 / 出船 / 捐出 / 收捐 / 被打掉｜接触）==")
    for p in squad:
        if only and sqname[p] not in only:
            continue
        s = S10[str(p)]
        pl = P[p]
        stop = pl['deathT'] if pl['deathT'] >= 0 else end
        print(f"-- {sqname[p]}#{p}" + (f"（t={pl['leftT']} 离场后由引擎托管）" if pl['leftT'] >= 0 else ''))
        t = 300
        f = F30[str(p)]
        print(f"   全程罚息损失合计 {k(f['capLoss'][-1] if f['capLoss'] else 0)}")
        while t <= stop:
            i = idx_at(s['t'], t)
            if i >= 0 and s['t'][i] == t and T0 <= t <= T1:
                terr, bal = s['terr'][i], s['bal'][i]
                fl = flows_between(p, t - 300, t) or [0] * len(CATS)
                j0, j1 = idx_at(f['t'], t - 300), idx_at(f['t'], t)
                cl = (f['capLoss'][j1] - f['capLoss'][j0]) if (j0 >= 0 and j1 >= 0) else 0
                print(f"   t={t} 地 {terr}｜兵 {k(bal)}｜密度 {bal / max(terr, 1):.0f}｜{100 * bal / max(100 * terr, 1):.0f}%｜利 {k(fl[0])} 罚息 {k(cl)} 中立 {k(-fl[1])} 机 {k(-fl[2])} 真人 {k(-fl[3])} 船 {k(-fl[4])} 捐出 {k(-fl[5])} 收捐 {k(fl[6])} 被打掉 {k(-fl[8])}｜{contact_str(p, t)}")
            t += 300

if 10 in secs:
    import re
    print("\n== 10 客户端落后（按日志行序估计：某号打 [HL-TICK] t=X 时，全队已见到的最大拍号 − X）与离场 ==")
    rows = []
    tmax = 0
    rx = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-(TICK|DISPATCH|OPENING)\] t=(\d+)')
    per = defaultdict(list)
    last = {}
    for line in open(f'{DATA}/bundles/{mid}/in_game.log', encoding='utf-8'):
        m = rx.match(line)
        if not m:
            continue
        bot, kind, t = m.group(2), m.group(3), int(m.group(4))
        tmax = max(tmax, t)
        last[bot] = t
        if kind == 'TICK':
            per[bot].append((t, tmax - t))
    for bot, arr in per.items():
        big = [(t, lag) for t, lag in arr if lag >= 90]
        mx = max(arr, key=lambda x: x[1]) if arr else (0, 0)
        pid = next((p for p in squad if sqname[p] == bot), None)
        lv = P[pid]['leftT'] if pid is not None else -1
        print(f"{bot}: 最后一条日志 t={last.get(bot)}；录像离场拍 {lv if lv >= 0 else '-'}；落后 ≥90 拍的快照 {len(big)}/{len(arr)}；最大落后 {mx[1]} 拍@t={mx[0]}；" + ' '.join(f"{t}:{lag}" for t, lag in big[:14]))
    D = J['dispatch']
    lag = defaultdict(list)
    for d in D:
        if d.get('exec'):
            lag[d['bot']].append(d['exec']['t'] - d['t'])
    for b, arr in lag.items():
        arr.sort()
        print(f"   调度指令延迟 {b}: n={len(arr)} 中位 {arr[len(arr) // 2]} p90 {arr[int(0.9 * (len(arr) - 1))]} 最大 {arr[-1]}；≥25 拍 {sum(1 for x in arr if x >= 25)} 笔")

if '--win' in args:
    # --win bot,t0,t1[,step]：某号在 [t0,t1] 的逐 step 拍状态 + 全部相关指令 + 窗口战账
    w = args[args.index('--win') + 1].split(',')
    bot, t0, t1 = w[0], int(w[1]), int(w[2])
    step = int(w[3]) if len(w) > 3 else 30
    p = next(pp for pp in squad if sqname[pp] == bot)
    s = S10[str(p)]
    print(f"\n== 窗口 {bot}#{p} t={t0}..{t1} ==")
    for t in range(t0 - t0 % 10, t1 + 1, step):
        i = idx_at(s['t'], t)
        if i < 0 or s['t'][i] != t:
            continue
        terr, bal = s['terr'][i], s['bal'][i]
        print(f"   t={t} 地 {terr}｜兵 {k(bal)}｜密度 {bal / max(terr, 1):.0f}｜外 {k(s['out'][i])}｜真人打 {k(s['inH'][i])}｜机打 {k(s['inB'][i])}｜配额已用 {s['quota'][i]}｜{contact_str(p, t)}")
    evs = [e for e in EV if t0 <= e['t'] <= t1 and (e['p'] == p or e.get('q') == p)]
    print(f"   指令 {len(evs)} 条：")
    for e in evs[:int(w[4]) if len(w) > 4 else 60]:
        print('     ' + fmt_ev(e))
    fl = flows_between(p, t0, t1)
    if fl:
        print('   收支：' + ' '.join(f"{CATS[c]} {k(v)}" for c, v in enumerate(fl) if abs(v) >= 1))
    agg_in = defaultdict(lambda: [0, 0, 0])
    agg_out = defaultdict(lambda: [0, 0, 0])
    for r in J['pairsW']:
        if t0 // 100 <= r['w'] <= t1 // 100:
            if r['b'] == p:
                a = agg_in[r['a']]
            elif r['a'] == p:
                a = agg_out[r['b']]
            else:
                continue
            a[0] += r['sent']
            a[1] += r['tiles']
            a[2] += r['balDmg']
    print('   窗口内（按 100 拍对齐）它打别人：' + '；'.join(f"{nm(a)} 投 {k(v[0])} 拿地 {v[1]} 打掉兵 {k(v[2])}" for a, v in sorted(agg_out.items(), key=lambda kv: -kv[1][0])[:6]))
    print('   窗口内别人打它：' + '；'.join(f"{nm(a)} 投 {k(v[0])} 拿地 {v[1]} 打掉兵 {k(v[2])}" for a, v in sorted(agg_in.items(), key=lambda kv: -kv[1][1])[:6]))

if 10 in secs:
    # 同一拍多条进攻（策略每 5 拍最多下 1 条陆攻；服务器每 7 拍结算一帧，正常一帧至多 2 条）
    print("   同拍连发（同一个号在同一拍执行 ≥3 条陆攻/出船指令）：")
    for p in squad:
        by = defaultdict(list)
        for e in EV:
            if e['p'] == p and e['type'] in ('attack', 'boat'):
                by[e['t']].append(e)
        bursts = [(t, es) for t, es in by.items() if len(es) >= 3]
        if not bursts:
            continue
        tot = sum(len(es) for es in by.values())
        desc = []
        for t, es in sorted(bursts, key=lambda x: -len(x[1]))[:6]:
            b0 = es[0]['B0']
            spent = sum((e.get('troops') or 0) + (e.get('fee') or 0) for e in es if e['ok'])
            tg = defaultdict(int)
            for e in es:
                tg[nm(e['q'])] += 1
            desc.append(f"t={t}×{len(es)}（{'/'.join(f'{a}×{n}' for a, n in tg.items())}；花掉当拍存兵 {100 * spent / max(b0, 1):.0f}%，首条只要 {100 * ((es[0].get('troops') or 0)) / max(b0, 1):.0f}%）")
        print(f"   {sqname[p]}: 指令 {tot} 条，连发 {len(bursts)} 次，共 {sum(len(es) for _, es in bursts)} 条；" + '；'.join(desc))
