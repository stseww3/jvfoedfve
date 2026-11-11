#!/usr/bin/env python3
# hollow_rear.py — 每个我方号「最后一轮挨打」的账：第一发之前它在干什么、挨第一发时有多少兵、之后多久没地。
# 用来机械地数两种事：后排号被调度抽空后被逐个打穿（NEW-DN-HOLLOWREAR）、敌方用船在没有陆上敌邻的号身上登陆（NEW-DF-SEAFLANK）。
# 用法：python3 scripts/hollow_rear.py <局号> [--ours id,id,…] [--gap 300]
# 口径（全部来自真引擎重放 tmp/truth/<局号>/；封死与否来自影子策略 tmp/shadow/<局号>/rows.tsv，没有就留空）：
#   敌方出手   = 敌方真人对这个号的陆攻指令（进攻槽登记的兵 > 0）或船登陆后的进攻（ev.tsv 的 land 事件）；
#   没地的拍   = 出局拍，或者领土第一次跌到自己历史峰值的 10% 以下的拍（靠小船、小岛留在场上的号按这个算），取早的；
#   最后一轮   = 从没地的拍往前数，相邻两发相隔 ≤ gap 拍（默认 300）的那一串出手；第一发 = 这一串的头一发；
#   第一发前 600 拍的捐款：笔数、到账合计、最后一笔捐完后的密度；
#   第一发时   = 这个号的 领土 / 余额 / 密度，这一发的兵 ÷ 这个号的余额；
#   第一发前 300 拍有没有敌方真人陆上邻居（影子策略 nHum>0 的决策拍占比）、是不是封死（nb=0 且 neut=0 的占比）；
#   这一轮：出手的敌方真人数、发数、兵合计、其中船登陆的发数与兵；期间收到的捐款到账；第一发到没地隔了多少拍。
#   末尾按两个模式的定义各数一遍；再给全场「敌方真人的船在我方号身上登陆后的进攻」按出手方、按挨打的号的合计，和我方的船登陆敌方真人的发数。
import sys, os, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    gap = int(a[a.index('--gap') + 1]) if '--gap' in a else 300
    M = Match(mid, ours)

    def troops(c):
        return sum(int(x[2]) for x in c['sub'] if x and x[0] == 'atk')

    hits = collections.defaultdict(list)     # 我方号 -> [(t, 出手方, 兵, 是否船)]
    for c in M.cmd:
        if c['id'] == 1 and c['b'] in M.ours and c['p'] < M.ku and M.team.get(c['p']) != M.our_team:
            s = troops(c)
            if s > 0:
                hits[c['b']].append((c['t'], c['p'], s, False))
    for (t, kind, p, x, y, det) in M.ev:
        if kind != 'land' or '|' not in det:
            continue
        for part in det.split('|', 1)[1].split(';'):
            f = part.split(':')
            if f[0] == 'atk' and len(f) >= 3 and int(f[2]) > 0 and int(f[1]) in M.ours and p < M.ku and M.team.get(p) != M.our_team:
                hits[int(f[1])].append((t, p, int(f[2]), True))

    rows = collections.defaultdict(dict)     # 号名 -> t -> (nb, nHum, neut)
    rp = os.path.join(HERE, '..', 'tmp', 'shadow', mid, 'rows.tsv')
    if os.path.exists(rp):
        for l in open(rp, encoding='utf8'):
            x = l.rstrip('\n').split('\t')
            if x[0] == 't':
                continue
            rows[x[1]][int(x[0])] = (int(float(x[4])), int(float(x[8])), int(float(x[9])))

    dons_out = collections.defaultdict(list)  # 捐款人 -> [(t, 到账, 捐后密度)]
    dons_in = collections.defaultdict(list)   # 收款人 -> [(t, 到账)]
    for c in M.cmd:
        if c['id'] != 2 or 'q' not in c:
            continue
        cred = c['balQ1'] - c['balQ0']
        if cred <= 0:
            continue
        if c['p'] in M.ours:
            dons_out[c['p']].append((c['t'], cred, c['bal1'] / max(1, c['terr0'])))
        if c['q'] in M.ours:
            dons_in[c['q']].append((c['t'], cred))

    print(f'# {mid} 我方各号最后一轮挨打（相邻两发相隔 ≤{gap} 拍算同一轮）')
    names_h, names_s, names_w = [], [], []
    for p in M.our_ids:
        nm = M.nm(p)
        # 没地的拍：出局拍，或领土第一次跌到历史峰值 10% 以下的拍
        peak = 0
        gone = None
        for s in M.samples:
            st = M.state[s].get(p)
            if not st:
                continue
            peak = max(peak, st[0])
            if peak >= 1000 and st[0] <= 0.1 * peak:
                gone = s
                break
        dead = M.dead.get(p, (None,))[0]
        end = min(x for x in (gone, dead, M.last) if x is not None)
        hs = sorted(h for h in hits.get(p, []) if h[0] <= end)
        if not hs:
            print(f'{nm:8s} 全场没有被敌方真人打过；结束拍 {end}（{"出局" if dead else "对局结束"}）')
            continue
        i = len(hs) - 1
        while i > 0 and hs[i][0] - hs[i - 1][0] <= gap:
            i -= 1
        run = hs[i:]
        if dead is None and gone is None and end - run[-1][0] > gap:
            print(f'{nm:8s} 活到对局结束（拍 {end}）；最后一次被敌方真人打在拍 {run[-1][0]}')
            continue
        t1 = run[0][0]
        s1 = M.state[M.at(t1)].get(p, (0, 0))
        terr1, bal1 = s1[0], s1[1]
        d1 = bal1 / max(1, terr1)
        pre = [d for d in dons_out.get(p, []) if t1 - 600 <= d[0] < t1]
        last_d = pre[-1][2] if pre else None
        rr = [v for t, v in rows.get(nm, {}).items() if t1 - 300 <= t < t1]
        hum = sum(1 for v in rr if v[1] > 0) / len(rr) if rr else None
        boxed = sum(1 for v in rr if v[0] == 0 and v[2] == 0) / len(rr) if rr else None
        atk = sorted(set(M.nm(h[1]) for h in run))
        per = collections.OrderedDict()
        for h in sorted(run, key=lambda h: h[0]):
            v = per.setdefault(M.nm(h[1]), [0, 0, 0, 0])
            v[0] += 1; v[1] += h[2]
            if h[3]:
                v[2] += 1; v[3] += h[2]
        atk_txt = '、'.join(f'{k} {v[0]} 发 {fmt(v[1])}' + (f'（船登陆 {v[2]} 发 {fmt(v[3])}）' if v[2] else '') for k, v in sorted(per.items(), key=lambda kv: -kv[1][1]))
        tot = sum(h[2] for h in run)
        boats = [h for h in run if h[3]]
        got = sum(c for t, c in dons_in.get(p, []) if t1 <= t <= end)
        print(f'{nm:8s} 第一发 拍 {t1}{"（船登陆）" if run[0][3] else ""} {M.nm(run[0][1])} {fmt(run[0][2])} 兵；它当时 地 {terr1} 兵 {fmt(bal1)} 密度 {d1:.0f}（这一发 = 它余额的 {run[0][2] / max(1, bal1):.2f} 倍）'
              f' | 此前 600 拍捐出 {len(pre)} 笔 {fmt(sum(d[1] for d in pre))}' + (f'，最后一笔在拍 {pre[-1][0]}、捐后密度 {last_d:.0f}' if pre else '')
              + (f' | 此前 300 拍：有敌方真人陆邻的决策拍 {100 * hum:.0f}%，封死 {100 * boxed:.0f}%' if hum is not None else '')
              + f' | 这一轮 {len(atk)} 个敌方真人 {len(run)} 发 {fmt(tot)} 兵' + (f'（船登陆 {len(boats)} 发 {fmt(sum(h[2] for h in boats))}）' if boats else '')
              + f'，期间收到捐款 {fmt(got)} | 到{"出局" if dead and dead <= end else "没地"}（拍 {end}）隔 {end - t1} 拍；出手方：{atk_txt}')
        lost = dead is not None or gone is not None
        is_h = last_d is not None and last_d <= 32 and d1 <= 45 and lost
        is_s = run[0][3] and hum is not None and hum == 0 and d1 <= 45 and run[0][2] >= bal1 and lost
        if is_h:
            names_h.append((nm, end - t1))
        if is_s:
            names_s.append((nm, end - t1, run[0][2]))
        if last_d is not None and last_d <= 32 and lost:
            names_w.append((nm, round(d1), end - t1))
    for lim in (400, 700):
        h = [n for n, dt in names_h if dt <= lim]
        ss = [(n, tr) for n, dt, tr in names_s if dt <= lim]
        print(f'按 NEW-DN-HOLLOWREAR 的口径（此前 600 拍有捐款且最后一笔捐后密度 ≤32、挨第一发时密度 ≤45、{lim} 拍内没地）：{len(h)} 个号 {h}')
        print(f'按 NEW-DF-SEAFLANK 的口径（第一发是船登陆、此前 300 拍没有敌方真人陆邻、密度 ≤45、登陆兵 ≥ 余额、{lim} 拍内没地）：{len(ss)} 个号 {[n for n, _ in ss]}，登陆兵 {fmt(sum(tr for _, tr in ss))}')
    # 全场：敌方真人的船在我方号身上登陆后的进攻；我方的船登陆后打敌方真人的进攻
    ba, bv = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(lambda: [0, 0])
    for b, l in hits.items():
        for (t, p, s, isb) in l:
            if isb:
                ba[M.nm(p)][0] += 1; ba[M.nm(p)][1] += s
                bv[M.nm(b)][0] += 1; bv[M.nm(b)][1] += s
    ours_n = ours_s = 0
    for (t, kind, p, x, y, det) in M.ev:
        if kind != 'land' or '|' not in det or p not in M.ours:
            continue
        for part in det.split('|', 1)[1].split(';'):
            f = part.split(':')
            if f[0] == 'atk' and len(f) >= 3 and int(f[2]) > 0 and int(f[1]) < M.ku and M.team.get(int(f[1])) != M.our_team:
                ours_n += 1; ours_s += int(f[2])
    print(f'全场敌方真人的船在我方号身上登陆后的进攻：{sum(v[0] for v in ba.values())} 发 {fmt(sum(v[1] for v in ba.values()))} 兵；按出手方：'
          + '、'.join(f'{k} {v[0]} 发 {fmt(v[1])}' for k, v in sorted(ba.items(), key=lambda kv: -kv[1][1]))
          + '；按挨打的号：' + '、'.join(f'{k} {v[0]} 发 {fmt(v[1])}' for k, v in sorted(bv.items(), key=lambda kv: -kv[1][1])))
    print(f'我方号的船登陆后打敌方真人的进攻：{ours_n} 发 {fmt(ours_s)} 兵')
    print(f'放宽看：此前 600 拍最后一笔捐后密度 ≤32 的号，不限挨第一发时的密度（号, 挨第一发时密度, 到没地的拍数）：{names_w}')

if __name__ == '__main__':
    main()
