#!/usr/bin/env python3
"""latency.py — 延迟账（HUB 广播 0007 第 2 项）：选点落地、指令从「策略下令」到「进录像执行」的延迟、漏斗、迟到落空、确认窗内重复下单、同拍批。

口径（全部可重算）：
  · 下令拍 τ：影子策略（strat_probe.mjs --json，逐拍在真引擎重放出的真实局面上跑同一份策略源码，指令只记不执行）发出这条指令的拍。
    客户端的本机局面是服务器局面的逐拍复刻（日志快照与重放同拍逐兵一致，见 simdigest check），所以客户端在「本机拍 τ」下的令 = 影子在 τ 下的令。
    用日志里策略自己数的 cmds 计数核对影子的累计条数（两者应相等）。
  · 执行拍 s：这条指令进录像（服务器执行）的拍。延迟 = s − τ = 客户端本机落后服务器的拍数 + 上行/排队。
  · 配对：同一个号、同一种指令（陆攻/发船/捐款）、pct 相同、目标相同（或录像里目标记成 512：下令时的目标落地前已出局，引擎改记无主地），
    τ <= s，按「先下令的先执行」取最早的未配对影子指令；同一服务器回合内的多条不要求次序（实测同回合内是倒序落地）。
    pct 对不上时放宽到 |Δpct| <= max(3, 6%)（标「近似」）。配对当时只有一个候选的标「唯一」，分位数另给一份只算唯一的。
  · 时段按下令拍 τ 分：0~600 / 600~1500 / 1500~3000 / 3000+（漏斗里「进录像」按执行拍分）。

用法：python3 latency.py <matchId> [spawn|delay|funnel|void|dups|batches|bots|json|all]（缺省 all）
  需要 out/<id>/sim_state.json（eng_replay.cjs）和 out/<id>/probe.json（strat_probe.mjs --me squad --json）。没有录像的局只打印 spawn 段的日志侧数字。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match  # noqa: E402

NEUTRAL = 512
EDGES = [0, 600, 1500, 3000, 10 ** 9]
MAXD = 1500          # 配对时允许的最大延迟（拍）
FUZZ_ABS, FUZZ_REL = 3, 0.06
BATCH_MIN = 3        # 同一号同一服务器回合进录像 >= 这么多条算一批
BATCH_DRAIN = 0.5    # 一批里出兵+手续费 >= 这个比例 × 批前余额 算「清仓批」


def band(t):
    for i in range(len(EDGES) - 1):
        if EDGES[i] <= t < EDGES[i + 1]:
            return i
    return len(EDGES) - 2


def band_name(i):
    return f"{EDGES[i]}~{EDGES[i + 1]}" if EDGES[i + 1] < 10 ** 9 else f"{EDGES[i]}+"


def pctl(v, q):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, int(q * len(s)))]


def q3(v):
    return f"{pctl(v, 0.5)}/{pctl(v, 0.9)}/{max(v)}" if v else '-'


def fmt(n):
    n = int(n)
    a = abs(n)
    if a >= 10 ** 6:
        return f"{n / 1e6:.2f}M"
    if a >= 10 ** 4:
        return f"{n / 1e3:.0f}k"
    return str(n)


class Ctx:
    pass


def load(mid):
    X = Ctx()
    X.M = M = load_match(mid)
    X.sim = M.sim
    pp = os.path.join(OUT, mid, 'probe.json')
    X.probe = json.load(open(pp)) if os.path.exists(pp) else None
    X.last = (M.sim or {}).get('endT', 0)
    X.H = (M.sim or {}).get('humans', M.humans)
    return X


def name(X, p):
    b = X.M.bots.get(p)
    if b:
        return b.name
    if p == NEUTRAL:
        return '无主地'
    an = (X.sim or {}).get('allNames') or []
    nm = an[p].strip() if 0 <= p < len(an) and an[p] else ''
    return (nm or f"#{p}") + ('' if p < X.H else '(AI)')


# ------------------------------------------------------------------ 配对
def align(X):
    """返回 rows（每条进录像的指令一行，带配上的影子指令）和 lost（没配上的影子指令）。"""
    if getattr(X, '_al', None):
        return X._al
    sim, probe = X.sim, X.probe
    acts = defaultdict(list)
    for i, c in enumerate(sim['squadCmds']):
        if c['k'] in ('atk', 'boat') and c['p'] in X.M.bots:
            acts[c['p']].append(dict(c, i=i))
    for i, dn in enumerate(sim['donations']):
        if dn['from'] in X.M.bots:
            acts[dn['from']].append(dict(t=dn['t'], k='don', p=dn['from'], to=dn['to'], raw=dn['to'], pct=dn['pct'], ok=dn['ok'], B0=dn['B0'], sent=dn['delivered'], fee=dn['fee'], i=10 ** 6 + i))
    rows, lost = [], []
    for me in sorted(X.M.bots):
        sh = probe['shadows'].get(str(me))
        S = [dict(c, j=j, used=False) for j, c in enumerate(sh['cmds'])] if sh else []
        A = sorted(acts.get(me, []), key=lambda c: (c['t'], c['i']))
        lo = 0
        k = 0
        while k < len(A):
            k2 = k
            while k2 < len(A) and A[k2]['t'] == A[k]['t']:
                k2 += 1
            hi_used = lo - 1
            for a in A[k:k2]:
                def ok_t(s):
                    if s['k'] != a['k'] or s['used'] or s['j'] < lo or s['t'] > a['t'] or a['t'] - s['t'] > MAXD:
                        return False
                    if a['k'] == 'atk':
                        return s['to'] == a['raw'] or a['raw'] == NEUTRAL
                    if a['k'] == 'don':
                        return s['to'] == a['to']
                    return True
                cand = [s for s in S if ok_t(s)]
                ex = [s for s in cand if s['pct'] == a['pct']]
                how = 'exact'
                if not ex:
                    ex = [s for s in cand if abs(s['pct'] - a['pct']) <= max(FUZZ_ABS, FUZZ_REL * a['pct'])]
                    how = 'fuzzy'
                r = dict(a, me=me)
                if ex:
                    # 目标完全相同的优先于「目标落地前出局改记 512」的
                    same = [s for s in ex if a['k'] != 'atk' or s['to'] == a['raw']]
                    s = (same or ex)[0]
                    s['used'] = True
                    hi_used = max(hi_used, s['j'])
                    r.update(tau=s['t'], sTo=s['to'], sPct=s['pct'], sAmt=s.get('amt', 0), how=how, uniq=(len(ex) == 1), delay=a['t'] - s['t'])
                else:
                    r.update(tau=None, how='none')
                rows.append(r)
            lo = max(lo, hi_used + 1)
            k = k2
        for s in S:
            if not s['used']:
                lost.append(dict(me=me, t=s['t'], k=s['k'], to=s['to'], pct=s['pct'], amt=s.get('amt', 0), before=(s['j'] < lo)))
    X._al = (rows, lost)
    return X._al


def cmds_at(b, t):
    """日志 cmds 计数在本机拍 <= t 的最后一条快照上的值。"""
    v = 0
    for s in b.traj:
        if s['t'] <= t:
            v = s['cmds']
        else:
            break
    return v


# ------------------------------------------------------------------ 各段
def sec_fidelity(X):
    rows, lost = align(X)
    M, probe = X.M, X.probe
    dev, tot_log, tot_sh = [], 0, 0
    for me, b in sorted(M.bots.items()):
        sh = probe['shadows'].get(str(me))
        if not sh:
            continue
        snaps = [s for s in b.traj if s['t'] <= X.last]
        if not snaps:
            continue
        t = snaps[-1]['t']
        n_sh = sum(1 for c in sh['cmds'] if c['t'] <= t)
        dev.append((abs(n_sh - snaps[-1]['cmds']), b.name, t, snaps[-1]['cmds'], n_sh))
        tot_log += snaps[-1]['cmds']
        tot_sh += n_sh
    n_all = len(rows)
    ex = sum(1 for r in rows if r['how'] == 'exact')
    fz = sum(1 for r in rows if r['how'] == 'fuzzy')
    print(f"== {M.id} 延迟账：重放到 t={X.last}；影子与日志核对（各号最后一条 <= 重放末拍的快照）：日志 cmds 合计 {tot_log}、影子同拍累计 {tot_sh}（{len(dev)} 个号；"
          f"单号最大差 {max(d[0] for d in dev) if dev else 0} 条，差 >=3 条的 {sum(1 for d in dev if d[0] >= 3)} 个号）")
    worst = sorted(dev, reverse=True)[:4]
    print('   差得最多的：' + '；'.join(f"{d[1]} t={d[2]} 日志 {d[3]} / 影子 {d[4]}" for d in worst))
    print(f"   进录像的我方陆攻/发船/捐款 {n_all} 条：与影子指令配上 {ex + fz} 条（pct 相同 {ex}、近似 {fz}；配对时只有一个候选的 {sum(1 for r in rows if r.get('uniq'))} 条），"
          f"配不上 {n_all - ex - fz} 条；影子下了令而录像里没有的 {len(lost)} 条（其中下令拍在该号最后一条配上的指令之前 {sum(1 for x in lost if x['before'])} 条 = 丢了或影子多想的，"
          f"之后 {sum(1 for x in lost if not x['before'])} 条 = 重放结束时还没落地）")
    return dict(logCmds=tot_log, shadowCmds=tot_sh, landed=n_all, exact=ex, fuzzy=fz, unmatched=n_all - ex - fz, lost=len(lost), lostBefore=sum(1 for x in lost if x['before']),
                maxDev=max(d[0] for d in dev) if dev else 0)


def sec_delay(X):
    rows, lost = align(X)
    out = []
    print('-- 延迟分位数（拍；P50 / P90 / 最大），按下令拍分段：全部配上的｜只算「唯一候选」的｜陆攻｜发船｜捐款｜>=35 拍（约 2 秒）的条数｜>=90 拍（约 5 秒）的条数')
    for i in range(len(EDGES) - 1):
        m = [r for r in rows if r['tau'] is not None and band(r['tau']) == i]
        if not m:
            continue
        d = [r['delay'] for r in m]
        du = [r['delay'] for r in m if r['uniq']]
        by = {k: [r['delay'] for r in m if r['k'] == k] for k in ('atk', 'boat', 'don')}
        print(f"   τ={band_name(i):10s} n={len(d):4d} {q3(d):>13s}｜n={len(du):4d} {q3(du):>13s}｜陆攻 n={len(by['atk'])} {q3(by['atk'])}｜发船 n={len(by['boat'])} {q3(by['boat'])}｜捐款 n={len(by['don'])} {q3(by['don'])}"
              f"｜>=35：{sum(1 for x in d if x >= 35)}｜>=90：{sum(1 for x in d if x >= 90)}")
        out.append(dict(band=band_name(i), n=len(d), p50=pctl(d, 0.5), p90=pctl(d, 0.9), max=max(d), nUniq=len(du), p50Uniq=pctl(du, 0.5), p90Uniq=pctl(du, 0.9),
                        ge35=sum(1 for x in d if x >= 35), ge90=sum(1 for x in d if x >= 90),
                        atk=[len(by['atk']), pctl(by['atk'], 0.5), pctl(by['atk'], 0.9)], boat=[len(by['boat']), pctl(by['boat'], 0.5), pctl(by['boat'], 0.9)],
                        don=[len(by['don']), pctl(by['don'], 0.5), pctl(by['don'], 0.9)]))
    # 细分：每 150 拍一格的中位延迟（看延迟从哪一拍开始拉长）
    cells = defaultdict(list)
    for r in rows:
        if r['tau'] is not None:
            cells[r['tau'] // 150].append(r['delay'])
    print('   每 150 拍一格（下令拍：条数 中位/最大）：' + ' '.join(f"{k * 150}:{len(v)} {pctl(v, 0.5)}/{max(v)}" for k, v in sorted(cells.items())))
    X.cells = [[k * 150, len(v), pctl(v, 0.5), max(v)] for k, v in sorted(cells.items())]
    return out


def sec_bots(X):
    rows, lost = align(X)
    M = X.M
    print('-- 各号延迟（拍）：每个时段 配上条数 中位/最大；重放末拍时 日志 cmds / 进录像条数（差 = 还在路上或丢了的）')
    out = []
    for me, b in sorted(M.bots.items()):
        m = [r for r in rows if r['me'] == me]
        if not m:
            continue
        cells, per_band = [], {}
        for i in range(len(EDGES) - 1):
            d = [r['delay'] for r in m if r['tau'] is not None and band(r['tau']) == i]
            if d:
                cells.append(f"{band_name(i)}: {len(d)} 条 {pctl(d, 0.5)}/{max(d)}")
                per_band[band_name(i)] = [len(d), pctl(d, 0.5), max(d)]
        c_end = cmds_at(b, X.last)
        d_all = [r['delay'] for r in m if r['tau'] is not None]
        last_d = [r['delay'] for r in m if r['tau'] is not None][-5:]
        print(f"   {b.name:14s} 队{b.team} {'；'.join(cells):62s}｜cmds {c_end} / 进录像 {len(m)}（差 {c_end - len(m)}）｜最后 5 条的延迟 {last_d}")
        out.append(dict(me=me, name=b.name, team=b.team, n=len(m), p50=pctl(d_all, 0.5), max=max(d_all) if d_all else None, cmdsLog=c_end, landed=len(m), bands=per_band))
    return out


def sec_funnel(X):
    rows, lost = align(X)
    M, probe = X.M, X.probe
    print('-- 漏斗（条）。按下令拍分段：影子下令 → 到重放末拍为止进了录像的（配上的）→ 其中生效；没进录像的分两种：后面还有本号更晚下的令进了录像（= 丢了，或影子比客户端多想了一条）、'
          '后面再没有本号的令进录像（= 重放结束时还在路上）')
    out = []
    # 客户端「本机拍」走到哪：本号日志最后一条快照的拍 + 89（快照 90 拍一条）。影子在这之后下的令，客户端自己没有算过（日志已停：停摆 / 离开 / 阵亡前的落后）
    last_log = {me: (bb.traj[-1]['t'] + 89 if bb.traj else -1) for me, bb in M.bots.items()}
    for i in range(len(EDGES) - 1):
        a, b = EDGES[i], EDGES[i + 1]
        if a > X.last:
            break
        sh = [(me, c) for me, v in probe['shadows'].items() for c in v['cmds'] if a <= c['t'] < b]
        sh_live = [1 for me, c in sh if c['t'] <= last_log.get(int(me), -1)]
        m = [r for r in rows if r['tau'] is not None and a <= r['tau'] < b]
        ok = sum(1 for r in m if r['ok'])
        lb = [x for x in lost if a <= x['t'] < b and x['before']]
        la = [x for x in lost if a <= x['t'] < b and not x['before']]
        la_live = [x for x in la if x['t'] <= last_log.get(x['me'], -1)]
        print(f"   τ={band_name(i):10s} 影子下令 {len(sh)}｜进录像 {len(m)}（{100 * len(m) / max(1, len(sh)):.0f}%）｜生效 {ok}（{100 * ok / max(1, len(sh)):.0f}%）、进了录像但没生效 {len(m) - ok}"
              f"｜没进录像：丢了/多想 {len(lb)}、重放结束时还在路上 {len(la)}（想发 {fmt(sum(x['amt'] for x in la))} 兵）"
              f"｜只算本号日志还在打印的拍：影子下令 {len(sh_live)}、还在路上 {len(la_live)}（想发 {fmt(sum(x['amt'] for x in la_live))} 兵）")
        out.append(dict(band=band_name(i), shadow=len(sh), landed=len(m), ok=ok, void=len(m) - ok, lost=len(lb), pending=len(la), pendingAmt=sum(x['amt'] for x in la),
                        shadowLive=len(sh_live), pendingLive=len(la_live), pendingLiveAmt=sum(x['amt'] for x in la_live)))
    # 日志核对：各号在快照拍上的 cmds 计数（策略自己数的已发指令）对 影子同拍累计 对 录像里执行拍 <= 该拍的条数
    snaps = sorted(set(s['t'] for b in M.bots.values() for s in b.traj if s['t'] <= X.last))
    pick = [t for t in snaps if t % 270 == 0 or t == snaps[-1]] if snaps else []
    cells = []
    for t in pick:
        n_log = n_sh = n_land = 0
        for me, b in M.bots.items():
            if not any(s['t'] == t for s in b.traj):
                continue
            n_log += cmds_at(b, t)
            n_sh += sum(1 for c in probe['shadows'].get(str(me), {}).get('cmds', []) if c['t'] <= t)
            n_land += sum(1 for r in rows if r['me'] == me and r['t'] <= t)
        cells.append((t, n_log, n_sh, n_land))
    print('   日志核对（快照拍：日志 cmds 合计 / 影子同拍累计 / 录像里已执行；只算那一拍有快照的号）：' + ' '.join(f"{t}:{a}/{b}/{c}" for t, a, b, c in cells))
    return dict(bands=out, check=cells)


def sec_void(X):
    rows, lost = align(X)
    sim = X.sim
    print('-- 迟到落空 / 打错目标（陆攻；按执行拍分段）')
    print('   A = 没生效（一兵不扣、不收手续费）；A1 = 下令时打的是玩家，落地时它已出局（录像记成 512）且身边没有无主地；A2 = 下令时打的就是无主地，落地时身边已没有无主地；')
    print('   A3 = 目标还在但落地时已不接壤；B = 生效了但打错：下令时打的是玩家，落地时它已出局，兵进了无主地线。「想发」= 影子下令时算的出兵数')
    out = []
    for i in range(len(EDGES) - 1):
        a, b = EDGES[i], EDGES[i + 1]
        m = [r for r in rows if r['k'] == 'atk' and a <= r['t'] < b]
        if not m:
            continue
        void = [r for r in m if not r['ok']]
        a1 = [r for r in void if r['raw'] == NEUTRAL and r.get('sTo') not in (None, NEUTRAL)]
        a2 = [r for r in void if r['raw'] == NEUTRAL and r.get('sTo') == NEUTRAL]
        a3 = [r for r in void if r['raw'] != NEUTRAL]
        a0 = [r for r in void if r['raw'] == NEUTRAL and r.get('sTo') is None]
        bb = [r for r in m if r['ok'] and r['raw'] == NEUTRAL and r.get('sTo') not in (None, NEUTRAL)]
        ai1 = sum(1 for r in a1 if r['sTo'] >= X.H)
        print(f"   t={band_name(i):10s} 陆攻进录像 {len(m)} 条：A 没生效 {len(void)} 条（{100 * len(void) / len(m):.0f}%）= A1 {len(a1)}（目标是内置 AI {ai1}、真人 {len(a1) - ai1}；想发 {fmt(sum(r['sAmt'] for r in a1))} 兵；"
              f"延迟 {q3([r['delay'] for r in a1])}）+ A2 {len(a2)}（想发 {fmt(sum(r['sAmt'] for r in a2))}；延迟 {q3([r['delay'] for r in a2])}）+ A3 {len(a3)} + 配不上影子的 {len(a0)}"
              f"｜B 打错 {len(bb)} 条（实发 {fmt(sum(r['sent'] for r in bb))} 兵；延迟 {q3([r['delay'] for r in bb])}）"
              f"｜生效且目标没变的 {len(m) - len(void) - len(bb)} 条（延迟 {q3([r['delay'] for r in m if r['ok'] and r not in bb and r['tau'] is not None])}）")
        out.append(dict(band=band_name(i), atk=len(m), void=len(void), a1=len(a1), a1Ai=ai1, a1Amt=sum(r['sAmt'] for r in a1), a2=len(a2), a2Amt=sum(r['sAmt'] for r in a2), a3=len(a3),
                        a0=len(a0), b=len(bb), bSent=sum(r['sent'] for r in bb)))
    # 进攻线账：线从第一条生效的陆攻到结束
    eps = sim.get('episodes') or []
    if eps:
        print('   进攻线账（一条线 = 从第一条生效的陆攻到线结束；按开线拍分段；目标按开线时算）：')
        for i in range(len(EDGES) - 1):
            a, b = EDGES[i], EDGES[i + 1]
            for cls, lab in (('ai', '打内置 AI'), ('hum', '打真人'), ('neu', '打无主地')):
                m = [e for e in eps if a <= e['t0'] < b and not e['redir'] and ((cls == 'neu' and e['to'] == NEUTRAL) or (cls == 'ai' and X.H <= e['to'] < NEUTRAL) or (cls == 'hum' and e['to'] < X.H))]
                if not m:
                    continue
                sent = sum(e['sent'] for e in m)
                red = [e for e in m if e['end'] == 'redirect']
                empty = [e for e in m if e['gain'] == 0 and e['end'] != 'open']
                print(f"      t={band_name(i):10s} {lab}：{len(m)} 条线、{sum(e['n'] for e in m)} 条指令、出兵 {fmt(sent)}；打掉 {fmt(sum(e['spent'] for e in m))}、得地 {sum(e['gain'] for e in m)} 格；"
                      f"线结束时退回余额 {fmt(sum(e['ret'] for e in m))}（{100 * sum(e['ret'] for e in m) / max(1, sent):.0f}%）；目标中途出局、剩兵被改挂到无主地线的 {len(red)} 条线 {fmt(sum(e['moved'] for e in red))} 兵"
                      f"（{100 * sum(e['moved'] for e in red) / max(1, sent):.0f}%）；一格没拿到的 {len(empty)} 条线（出兵 {fmt(sum(e['sent'] for e in empty))}）")
                out.append(dict(band=band_name(i), cls=cls, lines=len(m), cmds=sum(e['n'] for e in m), sent=sent, spent=sum(e['spent'] for e in m), gain=sum(e['gain'] for e in m),
                                ret=sum(e['ret'] for e in m), redirLines=len(red), moved=sum(e['moved'] for e in red), emptyLines=len(empty), emptySent=sum(e['sent'] for e in empty)))
        rl = [e for e in eps if e['redir'] and e['to'] == NEUTRAL]
        if rl:
            print(f"      被改挂出来的无主地线 {len(rl)} 条：挂上去 {fmt(sum(e['sent'] for e in rl))} 兵，之后打掉 {fmt(sum(e['spent'] for e in rl))}、得地 {sum(e['gain'] for e in rl)} 格、退回 {fmt(sum(e['ret'] for e in rl))}；"
                  f"挂着的拍数 中位/最大 {pctl([e['t1'] - e['t0'] for e in rl], 0.5)}/{max(e['t1'] - e['t0'] for e in rl)}")
    return out


def sec_dups(X):
    rows, lost = align(X)
    print('-- 确认窗内重复下单：同一个号对同一目标（陆攻；发船不分目标）的后一条，下令拍落在前一条「已下令、还没进录像」的窗口里（τ_前 < τ_后 < s_前）')
    out = []
    by = defaultdict(list)
    for r in rows:
        if r['tau'] is None:
            continue
        key = (r['me'], r['k'], r['sTo'] if r['k'] != 'boat' else -1)
        by[key].append(r)
    dup_rows = []
    for key, v in by.items():
        v.sort(key=lambda r: r['tau'])
        for j, r in enumerate(v):
            prev = [p for p in v[:j] if p['tau'] < r['tau'] < p['t']]
            if prev:
                dup_rows.append((r, len(prev)))
    for i in range(len(EDGES) - 1):
        base = [r for r in rows if r['tau'] is not None and band(r['tau']) == i]
        if not base:
            continue
        for kind, lab in (('atk', '陆攻'), ('boat', '发船'), ('don', '捐款')):
            bk = [r for r in base if r['k'] == kind]
            m = [(r, n) for r, n in dup_rows if band(r['tau']) == i and r['k'] == kind]
            if not bk or not m:
                continue
            ok = [r for r, n in m if r['ok']]
            tgt = defaultdict(int)
            for r, n in m:
                tgt['发船' if r['k'] == 'boat' else ('无主地' if r['sTo'] == NEUTRAL else ('内置 AI' if r['sTo'] >= X.H else '真人'))] += 1
            runs = defaultdict(int)
            for r, n in m:
                runs[min(n, 4)] += 1
            print(f"   τ={band_name(i):10s} {lab}：配上的 {len(bk)} 条里重复 {len(m)} 条（{100 * len(m) / len(bk):.0f}%；{dict(tgt)}）：生效 {len(ok)} 条、实发 {fmt(sum(r['sent'] for r in ok))} 兵、手续费 {fmt(sum(r['fee'] for r in ok))}；"
                  f"没生效 {len(m) - len(ok)} 条；下令时已有 1 / 2 / 3 / >=4 条同目标在途的：{runs.get(1, 0)} / {runs.get(2, 0)} / {runs.get(3, 0)} / {runs.get(4, 0)} 条")
            out.append(dict(band=band_name(i), kind=kind, base=len(bk), dups=len(m), ok=len(ok), sent=sum(r['sent'] for r in ok), fee=sum(r['fee'] for r in ok), void=len(m) - len(ok),
                            stack=[runs.get(1, 0), runs.get(2, 0), runs.get(3, 0), runs.get(4, 0)], byTarget=dict(tgt)))
    return out


def batch_rows(X):
    rows, lost = align(X)
    g = defaultdict(list)
    for r in rows:
        g[(r['me'], r['t'])].append(r)
    out = []
    for (me, t), v in sorted(g.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if len(v) < BATCH_MIN:
            continue
        B0 = max(r['B0'] for r in v)
        cost = sum(r['sent'] + r['fee'] for r in v if r['ok'])
        taus = [r['tau'] for r in v if r['tau'] is not None]
        out.append(dict(me=me, name=X.M.bots[me].name, t=t, n=len(v), ok=sum(1 for r in v if r['ok']), B0=B0, cost=cost, frac=cost / max(1, B0),
                        tau0=min(taus) if taus else None, tau1=max(taus) if taus else None, kinds=''.join(sorted(set(r['k'][0] for r in v))),
                        extra=sum(r['sent'] + r['fee'] for r in sorted(v, key=lambda r: r['i'])[1:] if r['ok'])))
    return out


def sec_batches(X):
    B = batch_rows(X)
    print(f"-- 同拍批：同一个号同一个服务器回合进录像 >= {BATCH_MIN} 条（追帧后积压的指令一起落地）；清仓批 = 这一批出兵+手续费 >= 批前余额的 {int(BATCH_DRAIN * 100)}%")
    out = []
    for i in range(len(EDGES) - 1):
        m = [b for b in B if EDGES[i] <= b['t'] < EDGES[i + 1]]
        if not m:
            continue
        dr = [b for b in m if b['frac'] >= BATCH_DRAIN]
        allvoid = [b for b in m if b['ok'] == 0]
        print(f"   t={band_name(i):10s} {len(m)} 批、{sum(b['n'] for b in m)} 条（每批 {min(b['n'] for b in m)}~{max(b['n'] for b in m)} 条）；整批没生效的 {len(allvoid)} 批 {sum(b['n'] for b in allvoid)} 条；"
              f"清仓批 {len(dr)} 批（抽走批前余额的 {min((round(100 * b['frac']) for b in dr), default=0)}%~{max((round(100 * b['frac']) for b in dr), default=0)}%，共 {fmt(sum(b['cost'] for b in dr))} 兵）；"
              f"全部批里第 2 条起多发的 {fmt(sum(b['extra'] for b in m))} 兵")
        out.append(dict(band=band_name(i), batches=len(m), cmds=sum(b['n'] for b in m), allVoid=len(allvoid), drain=len(dr), drainCost=sum(b['cost'] for b in dr), extra=sum(b['extra'] for b in m)))
    for b in sorted(B, key=lambda b: -b['frac'])[:12]:
        print(f"      {b['name']:14s} 执行拍 {b['t']} 一批 {b['n']} 条（生效 {b['ok']}；{b['kinds']}），下令拍 {b['tau0']}~{b['tau1']}（延迟 {b['t'] - b['tau1'] if b['tau1'] is not None else '-'}~{b['t'] - b['tau0'] if b['tau0'] is not None else '-'}），"
              f"批前余额 {fmt(b['B0'])}、这一批花掉 {fmt(b['cost'])}（{100 * b['frac']:.0f}%）")
    return dict(bands=out, rows=B)


def spawn_rows(X):
    """日志 HL-SPAWN（策略下发的选点，按落盘顺序）↔ 录像里生效的选点。
    同一步里落地的多条，录像里的次序是下发次序的倒序（实测：OmniMan 第 47 步的 9 条、Messi 第 38 步的 4 条都与日志行序相反），
    引擎按录像次序执行，所以一步里落地一批时最后生效的是这批里最早下发的那条。"""
    import digest as D
    M = X.M
    R = D.picks_rows(M)
    if not R:
        return None
    per = {}
    pairs = []
    for me, b in sorted(M.bots.items()):
        land = R['per'].get(me, [])
        logs = b.spawns
        # 还原下发次序：步号升序，同一步内倒序
        by_step = defaultdict(list)
        for st, x, y in land:
            by_step[st].append((st, x, y))
        issue = [r for st in sorted(by_step) for r in reversed(by_step[st])]
        j = 0
        idx = {}
        for n, (st, x, y) in enumerate(issue):
            hit = None
            for k in range(j, len(logs)):
                if logs[k]['x'] == x and logs[k]['y'] == y:
                    hit = k
                    break
            idx[n] = hit
            if hit is not None:
                j = hit + 1
                pairs.append((logs[hit]['line'], st))
        steps = [st for st, _, _ in land]
        fin = land[-1] if land else None                      # 引擎最后执行的一条 = 出生点
        fin_n = issue.index(fin) if fin else None             # 它在下发次序里的位置（同坐标取第一处）
        if fin:
            cands = [n for n, r in enumerate(issue) if r == fin and r[0] == fin[0]]
            fin_n = cands[0]
        fin_idx = idx.get(fin_n) if fin_n is not None else None
        # 同一坐标在日志里出现多次时，出生点对应哪一条有歧义：给出最晚的一种可能
        alt = None
        if fin_idx is not None:
            prev = max([v for n, v in idx.items() if n < fin_n and v is not None], default=-1)
            nxt = min([v for n, v in idx.items() if n > fin_n and v is not None], default=len(logs))
            same = [k for k in range(prev + 1, nxt) if logs[k]['x'] == fin[1] and logs[k]['y'] == fin[2]]
            alt = same[-1] if same else fin_idx
        per[me] = dict(name=b.name, team=b.team, logged=len(logs), landed=len(land), matched=sum(1 for h in idx.values() if h is not None),
                       finalIdx=fin_idx, finalIdxAlt=alt, late=(len(logs) - 1 - fin_idx) if fin_idx is not None else None,
                       lateAlt=(len(logs) - 1 - alt) if alt is not None else None,
                       finalStep=(fin[0] if fin else None), batch=max((steps.count(s) for s in set(steps)), default=0),
                       finalBatch=(steps.count(fin[0]) if fin else 0), finalPosInBatch=(len(by_step[fin[0]]) - 1 - [r for r in reversed(by_step[fin[0]])].index(fin)) if fin else None,
                       lastLog=(logs[-1]['x'], logs[-1]['y']) if logs else None, final=(fin[1], fin[2]) if fin else None,
                       lastStep=max(steps) if steps else None)
    # 每条配上的选点的延迟下界（步）：比它晚写日志的选点里最早落地的那一步 = 它下发时服务器最多走到的步
    pairs.sort()
    suf = [10 ** 9] * (len(pairs) + 1)
    for i in range(len(pairs) - 1, -1, -1):
        suf[i] = min(suf[i + 1], pairs[i][1])
    lb = [pairs[i][1] - suf[i] for i in range(len(pairs))]
    return dict(R=R, per=per, lb=lb, pairs=pairs)


def sec_spawn(X):
    M = X.M
    S = spawn_rows(X)
    n_back = sum(1 for ln in M.other if 'BACKEND' in ln)
    tot_log = sum(len(b.spawns) for b in M.bots.values())
    if not S:
        print(f"-- 选点：没有录像，落地情况看不到。日志 HL-SPAWN {tot_log} 行；后端协调行（BACKEND）{n_back} 行")
        return dict(logged=tot_log, backendLines=n_back)
    per, R = S['per'], S['R']
    tot_land = sum(v['landed'] for v in per.values())
    last_ok = [v for v in per.values() if v['late'] == 0]
    late = [v for v in per.values() if v['late']]
    zero = [v for v in per.values() if v['landed'] == 0]
    stale_batch = [v for v in per.values() if v['finalBatch'] >= 2]
    print(f"-- 选点落地（录像真值；选点阶段 {R['steps']} 步）：日志 HL-SPAWN {tot_log} 行（策略算出并下发的选点；每号 {min(v['logged'] for v in per.values())}~{max(v['logged'] for v in per.values())} 行），"
          f"进录像 {tot_land} 条（{100 * tot_land / max(1, tot_log):.0f}%）；后端协调行（BACKEND）{n_back} 行")
    print(f"   最后一条下发的选点就是出生点的 {len(last_ok)}/{len(per)} 个号；出生点停在更早一版坐标的 {len(late)} 个号（差 1 条的 {sum(1 for v in late if v['late'] == 1)}、2 条的 {sum(1 for v in late if v['late'] == 2)}、"
          f">=3 条的 {sum(1 for v in late if v['late'] >= 3)}）；配不上日志的 {sum(1 for v in per.values() if v['late'] is None and v['landed'])} 个号；一条都没落地（引擎随机落位）的 {len(zero)} 个号")
    print(f"   同一步里一口气落地 >=3 条的 {sum(1 for v in per.values() if v['batch'] >= 3)} 个号；出生点所在那一步落地 >=2 条（倒序执行，最后生效的是这批里最早下发的）的 {len(stale_batch)} 个号")
    if S['lb']:
        print(f"   选点延迟下界（步；比它晚下发的选点里最早落地的那一步为准）：{len(S['lb'])} 条 中位/P90/最大 {q3(S['lb'])}；>=5 步的 {sum(1 for x in S['lb'] if x >= 5)} 条、>=10 步的 {sum(1 for x in S['lb'] if x >= 10)} 条")
    for me, v in sorted(per.items(), key=lambda kv: -(kv[1]['late'] or 0)):
        if v['late'] or v['landed'] == 0 or v['batch'] >= 3 or v['late'] is None:
            dd = None
            if v['lastLog'] and v['final']:
                dd = round(((v['lastLog'][0] - v['final'][0]) ** 2 + (v['lastLog'][1] - v['final'][1]) ** 2) ** 0.5)
            amb = '' if v['finalIdxAlt'] == v['finalIdx'] else f"（同一坐标下发过不止一次，也可能是第 {v['finalIdxAlt'] + 1} 条，那样就是 {v['lateAlt']} 条没赶上）"
            print(f"      {v['name']:14s} 队{v['team']} 下发 {v['logged']} 条 / 落地 {v['landed']} 条；出生点 {v['final']} = 第 {v['finalIdx'] + 1 if v['finalIdx'] is not None else '?'} 条下发的（落在第 {v['finalStep']} 步，"
                  f"那一步落地 {v['finalBatch']} 条），之后下发的 {v['late']} 条没有成为出生点{amb}；最后一条下发的是 {v['lastLog']}，离出生点 {dd} 格")
    near = R['near']
    same = [r for r in near if r['dist'] == 0]
    print(f"   最终落点相距 <80 格的 {len(near)} 对（同像素 {len(same)} 对；异队 {sum(1 for r in near if r['teamA'] != r['teamB'])} 对）："
          + '；'.join(f"{M.bots[r['a']].name}(队{r['teamA']})↔{M.bots[r['b']].name}(队{r['teamB']}) {r['dist']} 格" for r in near))
    return dict(logged=tot_log, landed=tot_land, lastOk=len(last_ok), late=len(late), late1=sum(1 for v in late if v['late'] == 1), late2=sum(1 for v in late if v['late'] == 2),
                late3=sum(1 for v in late if v['late'] >= 3), zero=len(zero), batch3=sum(1 for v in per.values() if v['batch'] >= 3), staleBatch=len(stale_batch), backendLines=n_back, steps=R['steps'],
                lbP50=pctl(S['lb'], 0.5), lbP90=pctl(S['lb'], 0.9), lbMax=max(S['lb']) if S['lb'] else None, near=len(near), samePixel=len(same),
                per={str(me): dict(name=v['name'], team=v['team'], logged=v['logged'], landed=v['landed'], late=v['late'], lateAlt=v['lateAlt'], batch=v['batch'], finalBatch=v['finalBatch'],
                                   finalStep=v['finalStep'], final=v['final'], lastLog=v['lastLog']) for me, v in per.items()})


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    sec = sys.argv[2] if len(sys.argv) > 2 else 'all'
    X = load(mid)
    full = X.sim is not None and X.probe is not None and X.last > 60
    doc = dict(matchId=mid, replayLast=X.last, edges=EDGES[:-1])
    if sec in ('spawn', 'all', 'json'):
        doc['spawn'] = sec_spawn(X)
    if not full:
        if sec != 'spawn':
            print(f"（{mid}：没有对局阶段的重放或影子探针，延迟只能看日志侧：logdigest.py {mid} seqlag / wall / noeffect / stale / opening）")
    else:
        if sec in ('delay', 'all', 'json'):
            doc['fidelity'] = sec_fidelity(X)
            doc['delay'] = sec_delay(X)
            doc['cells'] = getattr(X, 'cells', [])
        if sec in ('bots', 'all', 'json'):
            doc['bots'] = sec_bots(X)
        if sec in ('funnel', 'all', 'json'):
            doc['funnel'] = sec_funnel(X)
        if sec in ('void', 'all', 'json'):
            doc['void'] = sec_void(X)
        if sec in ('dups', 'all', 'json'):
            doc['dups'] = sec_dups(X)
        if sec in ('batches', 'all', 'json'):
            doc['batches'] = sec_batches(X)
    if sec == 'json':
        os.makedirs(os.path.join(OUT, mid), exist_ok=True)
        p = os.path.join(OUT, mid, 'latency.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
