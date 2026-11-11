#!/usr/bin/env python3
"""simdigest.py — 读真引擎重放的真值（eng_replay.cjs 写的 out/<id>/sim_state.json），打印逐局复盘要用的事实表。

用法：python3 simdigest.py <matchId> <段> [参数]
  check              重演与日志的逐点核对（可信到哪一拍、之后偏多少）
  boats [me]         我方每条船：瞄准谁、靠上谁的岸、海上自然损耗、被敌船打掉多少、沉没
  fees               手续费账：陆攻/发船/捐款各付了多少、占收入多少、出兵不到余额 5% 的指令
  nfs                isNoFullSend 置真条件的重演（逐拍余额 + 开局日志的发令拍）
  gaps               指令断档：策略在发令（日志 cmds 计数在涨）但 ≥300 拍没有一条指令进录像；离开的号日志停在哪一拍
  husks              我方空壳（离开后内置 AI 托管）与我方在场号之间的交换
  poolai             名字撞进编队名字池的内置 AI（策略按名字把它们当编队号保护）：占地、与我方号接壤的时段
  protbox            策略眼里没有可打邻居的时段（nb=0 且 neut=0），以及当时实际挨着哪些被保护名单挡住的地
  medians [前缀]     单号领土中位数：我方在场号 / 名字带前缀的一组 / 其余真人
  pair <me> [t0 t1]  某个号在窗口内与每个对手的交换（耗兵/得地/失地/被打掉兵）
  cmdlist <me> [t0 t1]  某个号在窗口内进了录像的每条指令，以及别人对它下的陆攻、给它的捐款
  teams              各队真实领土/兵力/在场真人/空壳占地（协议拍 + 我方阵亡拍）
  roster             我方每个号：队、出生、离开拍、阵亡拍、被谁拿走的地、峰值
  dens [t]           各队在场真人：我方号 vs 外人的地、兵、密度、单号领土中位（缺省取重放末拍）
  ledger [me]        兵力去向账：整局合计；给 me 则按 500 拍窗口展开
  deaths [me]        死因链：死前 900 拍的领土/兵力、邻居、谁拿走了地、谁打掉了兵、自己做了什么、收到什么援助
  don                我方参与的每笔捐款：到账、手续费、收款人当时的状态与之后 300 拍的去向；对倒
  cmds               我方指令是否生效：空指令、同拍连发、手续费/出兵比
  probe              我方每条 [HL-DONATE] 日志的结局：已执行 / 配额不够 / 收款人顶格 / 收款人已阵亡 / 校验能过却没执行
  gifts              船靠友军岸移交兵力（到账多少、蒸发多少）
  neigh <me> [t0 t1] 某个号的真实邻居时间线
  front [win]        每个号每个窗口主要和谁交换了什么（花兵、得地、失地、被打掉的兵）
  boxed              没有敌方邻居（只挨着队友/水/内置 AI）的时段
  landings [min]     船靠上我方号的岸：外人的船（海上登陆）、我方号的船靠到异队我方号（=打自己人）
  shadow [win]       影子策略（strat_probe.mjs --json）与录像的对照；断档段里影子想打谁
  gates              影子策略每个决策拍卡在哪道闸（strat_probe.mjs --json --tally）：t<1500 打内置 AI 的底线
                     （winR 项 / dpKeep / safeFinite，safeFinite 取到的是谁的兵）；t>=1500 对真人邻居的出口行号
  dups [gap]         重复下单：同一个号对同一目标的陆攻在 gap 拍（缺省 21）内又下一条；影子在同一段里想发几条
  crowd              同拍两条指令：影子在一拍里既发无主地小单又发对玩家陆攻，录像里随后执行的是哪条
  bursts [min] [frac] 同拍连发清仓：同一个号同一拍进录像 >=min 条（缺省 3）且一拍内出兵+费 >= frac×拍前兵（缺省 0.4，拍前兵 >=2 万）
  collapse           清地规则核对（领土 <= 衰减峰值/4 → 剩下的地全变无主地、余额清零；有船在海上的不出局）：
                     每个号清地拍、清地前一拍领土、当时的衰减峰值、冲高前的领土、正式阵亡拍、清地后又上岸的最大领土
  lumps              空壳整笔转交（引擎规则：离开的真人由内置 AI 托管，没有可打的目标时把全部余额捐给一个队友，手续费 6.25%，
                     不是指令、不进录像）：我方号收到的、我方空壳转出的
  json               写 out/<id>/simdigest.json（复盘 JSON 引用的事实）
所有数字都来自重演；重演可信范围见 check 段。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match, pname  # noqa: E402

PROTO = [90, 180, 270, 630, 1170, 1530, 2070, 3060, 4050, 4500, 5040, 6030, 7020, 8010, 9000, 9990, 10980, 11970, 12960]


class Sim:
    def __init__(self, mid, M=None):
        self.M = M or load_match(mid)
        self.S = self.M.sim
        if not self.S:
            raise SystemExit(f'{mid}: 没有 out/{mid}/sim_state.json（先跑 run_truth.sh {mid}）')
        S = self.S
        self.H = S['humans']
        self.hum = S['hum']
        self.ticks = S['ticks']
        self.tix = {t: i for i, t in enumerate(self.ticks)}
        self.team = S['teams']
        self.squad = sorted(int(k) for k in S['finalBots'])
        self.leave = {int(k): v for k, v in S['leaveT'].items()}
        self.deathT = S['deathT']
        self.endT = S['endT']
        self.land = S['land']
        led = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        for w, me, kind, other, v in S['ledger']:
            led[me][kind][w][other] += v
        self.led = led
        self.neigh = defaultdict(list)
        for n in S['neigh']:
            self.neigh[n['p']].append(n)
        self.validTo = S['check']['firstBad'] if S['check']['firstBad'] >= 0 else self.endT

    # ---- 基础取数
    def ix(self, t):
        """<= t 的最近采样下标。"""
        e = self.S['every']
        i = min(len(self.ticks) - 1, max(0, t // e))
        while i > 0 and self.ticks[i] > t:
            i -= 1
        while i + 1 < len(self.ticks) and self.ticks[i + 1] <= t:
            i += 1
        return i

    def terr(self, p, t):
        return self.hum[p]['terr'][self.ix(t)] if p < self.H else None

    def bal(self, p, t):
        return self.hum[p]['bal'][self.ix(t)] if p < self.H else None

    def name(self, p):
        return pname(self.M, p)

    def cls(self, me, other, t):
        """对方相对 me 的类别。"""
        if other == 512:
            return '无主地'
        if other < 0:
            return '-'
        if other == me:
            return '自己的地'
        if other >= self.H:
            return '内置AI' if self.team[other] == 0 or self.team[other] != self.team[me] else '同队AI'
        husk = other in self.leave and t >= self.leave[other]['t']
        same = self.team[other] == self.team[me]
        if other in self.squad:
            return ('我方号·同队' if same else '我方号·异队') + ('(空壳)' if husk else '')
        return ('队友' if same else '敌方真人') + ('(空壳)' if husk else '')

    def led_sum(self, me, kind, t0=0, t1=10 ** 9, by=None):
        """账目合计；by='other' 返回 {对方: 值}，by='cls' 返回 {类别: 值}。"""
        tot = 0
        out = defaultdict(int)
        for w, d in self.led[me][kind].items():
            if w + self.S['ledgerWindow'] <= t0 or w >= t1:
                continue
            for other, v in d.items():
                tot += v
                if by == 'other':
                    out[other] += v
                elif by == 'cls':
                    out[self.cls(me, other, w)] += v
        return out if by else tot

    def alive_active(self, p, t):
        """t 拍时在场且未离开。"""
        if self.deathT[p] >= 0 and t >= self.deathT[p]:
            return False
        if p in self.leave and t >= self.leave[p]['t']:
            return False
        return True

    def end_of(self, p):
        return self.deathT[p] if self.deathT[p] >= 0 else self.endT


def fmt(n):
    n = int(n)
    if abs(n) >= 10 ** 6:
        return f'{n / 10 ** 6:.2f}M'
    if abs(n) >= 10 ** 4:
        return f'{n / 1000:.0f}k'
    return str(n)


def pc(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


# ------------------------------------------------------------------ check
def sec_check(X):
    c = X.S['check']
    print(f"重放 {X.S['matchId']}（{X.S.get('producer', 'sim')}）：录像 {X.S['replayPath'].split('/')[-2]} 到 t={X.endT}；地图 {X.S['map']} 陆地 {X.land}；真人 {X.H}，{X.S['nTeams']} 队")
    print(f"日志快照 {c['points']} 条，指纹完全对上 {c['exact']} 条（{pc(c['exact'], c['points'])}），第一条对不上 t={c['firstBad']}")
    if c['bad']:
        bk = defaultdict(list)
        for r in c['bad']:
            bk[r['t'] // 1000].append(r)
        print('对不上的行按千拍分桶（与最接近的我方号比）：')
        for k in sorted(bk):
            rs = bk[k]
            te = sorted(abs(r['nearTerr'] - r['terr']) / max(1, r['terr']) for r in rs)
            be = sorted(abs(r['nearBal'] - r['bal']) / max(1, r['bal']) for r in rs)
            print(f"  t {k * 1000}~{k * 1000 + 999}: {len(rs)} 行；领土误差 中位 {te[len(rs) // 2]:.4f} 最大 {te[-1]:.3f}；兵力误差 中位 {be[len(rs) // 2]:.4f} 最大 {be[-1]:.3f}")
    if X.M.nameReuse:
        print('同一个日志名字先后属于不同玩家（按指纹拆开）：', {k: v for k, v in X.M.nameReuse.items()})
    print(f"录像里陆攻/发船/捐款指令在重演中没生效 {X.S['rejectedCmds']} 条")


# ------------------------------------------------------------------ teams
def team_rows(X, ticks=None):
    S = X.S
    nT = S['nTeams']
    if ticks is None:
        ticks = [t for t in PROTO if t <= X.endT]
        ticks += [X.deathT[p] for p in X.squad if X.deathT[p] > 0]
        ticks.append(X.endT)
    rows = []
    for t in sorted(set(ticks)):
        i = X.ix(t)
        tl, tb, th, tk = S['teamLand'][i], S['teamBal'][i], S['teamHumans'][i], S['teamHusk'][i]
        occupied = sum(tl)
        sq_land = defaultdict(int)
        sq_alive = defaultdict(int)
        sq_husk = defaultdict(int)
        for p in X.squad:
            if X.deathT[p] >= 0 and S['ticks'][i] >= X.deathT[p]:
                continue
            tm = X.team[p]
            if X.alive_active(p, S['ticks'][i]):
                sq_alive[tm] += 1
                sq_land[tm] += S['hum'][p]['terr'][i]
            else:
                sq_husk[tm] += S['hum'][p]['terr'][i]
        rows.append(dict(t=S['ticks'][i], teamLand=tl, teamBal=tb, teamHumans=th, teamHusk=tk, occupied=occupied,
                         sqLand=dict(sq_land), sqAlive=dict(sq_alive), sqHusk=dict(sq_husk)))
    return rows


def sec_teams(X):
    S = X.S
    nT = S['nTeams']
    bots_teamed = any(X.team[p] for p in range(X.H, 512))
    print(f"各队真实数据（份额 = 占全图陆地 {X.land} 的比例；空壳 = 已离开、由内置 AI 托管的真人的地；AI {'分进各队' if bots_teamed else '不属于任何队（0 队）'}）")
    sq_team = defaultdict(list)
    for p in X.squad:
        sq_team[X.team[p]].append(p)
    print('我方分队：', {tm: len(v) for tm, v in sorted(sq_team.items())})
    head = '   t  | ' + ' | '.join(f'队{k} 地% 兵 人 壳%' for k in range(1, nT + 1)) + (' | AI地%' if not bots_teamed else '') + ' | 我方在场(号数/地%) 按队'
    print(head)
    for r in team_rows(X):
        cells = []
        for k in range(1, nT + 1):
            cells.append(f"{100 * r['teamLand'][k] / X.land:5.1f} {fmt(r['teamBal'][k]):>6} {r['teamHumans'][k]:2d} {100 * r['teamHusk'][k] / X.land:4.1f}")
        ai = f" | {100 * r['teamLand'][0] / X.land:5.1f}" if not bots_teamed else ''
        sq = ' '.join(f"队{tm}:{r['sqAlive'].get(tm, 0)}/{100 * r['sqLand'].get(tm, 0) / X.land:.1f}" for tm in sorted(sq_team))
        print(f"{r['t']:5d} | " + ' | '.join(cells) + ai + ' | ' + sq)


# ------------------------------------------------------------------ dens（各队：我方号 vs 外人，在场号的地/兵/密度/单号领土中位）
def dens_rows(X, t=None):
    S = X.S
    i = X.ix(t if t is not None else X.endT)
    tt = S['ticks'][i]
    out = []
    for k in range(1, S['nTeams'] + 1):
        row = dict(team=k, t=tt)
        for tag, sel in (('ours', lambda p: p in X.squad), ('rest', lambda p: p not in X.squad)):
            ps = [p for p in range(X.H) if X.team[p] == k and sel(p) and X.alive_active(p, tt)]
            land = sum(S['hum'][p]['terr'][i] for p in ps)
            bal = sum(S['hum'][p]['bal'][i] for p in ps)
            row[tag] = dict(n=len(ps), land=land, bal=bal, dens=round(bal / land, 1) if land else 0,
                            med=median([S['hum'][p]['terr'][i] for p in ps]) if ps else 0,
                            names=[X.name(p) for p in sorted(ps, key=lambda q: -S['hum'][q]['terr'][i])[:4]])
        out.append(row)
    return tt, out


def burst_rows(X, min_n=3, frac=0.4):
    """同拍连发清仓：按 (号, 拍) 聚合进了录像的我方指令。"""
    S = X.S
    pt = S['perTick']
    t0 = pt['t0']
    by = defaultdict(list)
    for c in S['squadCmds']:
        by[(c['p'], c['t'])].append(c)
    dt = {d['p']: d['t'] for d in S['deaths']}
    rows = []
    for (p, t), cs in sorted(by.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if len(cs) < min_n:
            continue
        eff = [c for c in cs if c['ok']]
        B0 = cs[0]['B0']
        out = sum(c.get('sent', 0) + c.get('fee', 0) + c.get('delivered', 0) for c in eff)
        if B0 < 20000 or out < frac * B0:
            continue
        te = pt['terr'][str(p)]
        i = t - t0
        peak = max(te[i:i + 301]) if 0 <= i < len(te) else 0
        tg = defaultdict(int)
        for c in cs:
            if c['k'] == 'boat':
                tg['发船'] += 1
            elif c['k'] == 'don':
                tg['捐→' + X.name(c['to'])] += 1
            elif c['to'] >= 512:
                tg['无主地' + ('' if c['ok'] else '(没生效)')] += 1
            else:
                tg['攻→' + X.name(c['to'])] += 1
        pcts = [c['pct'] for c in eff if c['k'] == 'atk' and c['to'] < 512]
        rows.append(dict(t=t, p=p, name=X.name(p), n=len(cs), eff=len(eff), B0=B0, out=out, share=out / B0, terr0=te[i] if 0 <= i < len(te) else 0, peak300=peak,
                         deathT=dt.get(p, -1), targets=dict(tg), pcts=pcts))
    return rows


def sec_bursts(X, min_n=3, frac=0.4):
    rows = burst_rows(X, min_n, frac)
    print(f"同拍连发清仓（同一个号同一拍进录像 >={min_n} 条，且这一拍出兵+手续费 >= {frac:.0%} 拍前兵，拍前兵 >=2 万）。引擎按指令顺序逐条按「当时余额」结算，所以 k 条同样百分比的指令一拍内拿走 1-(1-pct-费率)^k")
    print('    t  号              条/生效   拍前兵   一拍出兵+费 占比 | 领土 → 300 拍内峰值 | 阵亡拍(距) | 目标（条数）；对玩家陆攻的 pct‰')
    for r in rows:
        d = r['deathT']
        print(f"{r['t']:5d}  {r['name'][:14]:14s} {r['n']:2d}/{r['eff']:<2d} {fmt(r['B0']):>8s} {fmt(r['out']):>8s} {100 * r['share']:5.1f}% | {r['terr0']:5d} → {r['peak300']:5d} | "
              f"{(str(d) + '(' + str(d - r['t']) + ')') if d > 0 else '-':>11s} | " + '，'.join(f"{k}×{v}" for k, v in r['targets'].items()) + (('；' + '/'.join(str(x) for x in r['pcts'])) if r['pcts'] else ''))
    big = [r for r in rows if r['share'] >= 0.7]
    dead = [r for r in big if r['deathT'] > 0 and r['deathT'] - r['t'] <= 900]
    print(f"合计 {len(rows)} 组，出兵+费 {fmt(sum(r['out'] for r in rows))}；其中一拍拿走 >=70% 的 {len(big)} 组（{fmt(sum(r['out'] for r in big))}），涉及 {len(set(r['p'] for r in big))} 个号；这些组里 900 拍内阵亡的 {len(dead)} 组（{len(set(r['p'] for r in dead))} 个号）")
    return rows


def collapse_rows(X):
    """引擎清地规则（干净模拟器 game.js aliveTick/collapse，与真引擎逐拍对上）：每拍 peak = 领土>=peak ? 领土 : peak - max(1, (peak-领土)//1000)；
    领土 <= peak//4 → 清地（剩下的格子全部变无主地、余额清零）；有船在海上则只清地不出局，船靠岸后可以再上岸。"""
    S = X.S
    pt = S['perTick']
    t0 = pt['t0']
    dt = {d['p']: d['t'] for d in S['deaths']}
    rows = []
    for p in X.squad:
        te = pt['terr'].get(str(p))
        if not te:
            continue
        peak = 0
        mx, mxT = 0, -1
        for i, x in enumerate(te):
            if x < 0:
                continue
            if i > 0 and x == 0 and te[i - 1] > 0 and peak > 0:
                pre = te[max(0, (mxT - t0) - 300)] if mxT >= 0 else 0
                after = max([v for v in te[i:] if v >= 0] or [0])
                rows.append(dict(p=p, name=X.name(p), t=t0 + i, terrBefore=te[i - 1], peak=peak, line=peak // 4, maxTerr=mx, maxT=mxT, pre300=pre,
                                 deathT=dt.get(p, -1), afterMax=after, ok=te[i - 1] > peak // 4))
                break
            if x >= peak:
                peak = x
            else:
                peak = peak - max(1, (peak - x) // 1000)
            if x > mx:
                mx, mxT = x, t0 + i
    return rows


def sec_collapse(X):
    rows = collapse_rows(X)
    print('清地规则核对：每拍 peak = 领土>=peak ? 领土 : peak - max(1,(peak-领土)//1000)；领土 <= peak//4 → 剩下的地全变无主地、余额清零（有船在海上的不出局）')
    print('号              清地拍  前一拍领土  衰减峰值  峰值/4 | 历史最大领土@拍  最大前300拍的领土  按「最大前300拍领土」算的清地线 | 正式阵亡拍  清地后再上岸的最大领土')
    for r in sorted(rows, key=lambda r: r['t']):
        print(f"{r['name']:14s} {r['t']:6d} {r['terrBefore']:8d} {r['peak']:9d} {r['line']:7d} | {r['maxTerr']:6d}@{r['maxT']:<5d} {r['pre300']:8d} {r['pre300'] // 4:12d} | {r['deathT']:8d} {r['afterMax']:8d}"
              + ('' if r['ok'] else '  ← 前一拍已经在线下'))
    print(f"清地 {len(rows)} 个号，清地那一拍变成无主地的格子合计 {sum(r['terrBefore'] for r in rows)}；前一拍领土都在线上、下一拍清地的 {sum(1 for r in rows if r['ok'])} 个")
    up = [r for r in rows if r['pre300'] > 0 and r['maxTerr'] >= 1.3 * r['pre300']]
    print(f"其中清地前冲高过（历史最大 >= 1.3×最大前 300 拍的领土）的 {len(up)} 个号：清地时还剩 {sum(r['terrBefore'] for r in up)} 格，按冲高前领土算的清地线合计 {sum(r['pre300'] // 4 for r in up)} 格")
    return rows


def lump_rows(X):
    """空壳整笔转交。收款侧：我方号一拍内余额跳涨（不是利息拍的正常利息、不是捐款指令、不是船移交），
    且同队某个已离开的真人在前后两个采样拍之间余额掉到接近 0、掉的量 ×(1-64/1024) 与跳涨相差 <3% → 确认。
    转出侧：我方空壳一拍内余额掉 >=80% 且领土不变。"""
    S = X.S
    pt = S['perTick']
    t0 = pt['t0']
    tk = S['ticks']
    don = defaultdict(int)
    for d in S['donations']:
        don[(d['to'], d['t'])] += d['delivered']
    gift = defaultdict(int)
    for g in S.get('boatGifts', []):
        gift[(g['to'], g['t'])] += g['delivered']
    ins, outs = [], []
    for p in X.squad:
        b = pt['bal'].get(str(p))
        te = pt['terr'].get(str(p))
        if not b:
            continue
        for i in range(1, len(b)):
            t = t0 + i
            if b[i] < 0 or b[i - 1] < 0:
                continue
            d = b[i] - b[i - 1]
            if d >= 20000 and d > 0.04 * max(1, b[i - 1]):
                if sum(don.get((p, x), 0) for x in (t - 1, t, t + 1)) >= 0.8 * d or sum(gift.get((p, x), 0) for x in (t - 1, t, t + 1)) >= 0.8 * d:
                    continue
                a = max(x for x in tk if x <= t - 1)
                bb = min(x for x in tk if x >= t)
                ia, ib = tk.index(a), tk.index(bb)
                src = None
                for q in range(X.H):
                    if q == p or X.team[q] != X.team[p] or q not in X.leave or X.leave[q]['t'] > t:
                        continue
                    drop = S['hum'][q]['bal'][ia] - S['hum'][q]['bal'][ib]
                    if not (drop > 0 and S['hum'][q]['bal'][ib] <= 0.05 * S['hum'][q]['bal'][ia]):
                        continue
                    # 空壳的余额在前一个采样拍之后还会变（离开前的利息）：离开拍落在两个采样拍之间时，用离开那一拍的余额再对一次
                    bases = [S['hum'][q]['bal'][ia]] + ([X.leave[q]['bal']] if a < X.leave[q]['t'] <= t else [])
                    hit = [x for x in bases if abs(x * 960 / 1024 - d) <= 0.03 * d]
                    if hit:
                        src = dict(q=q, name=X.name(q), leftT=X.leave[q]['t'], bal0=hit[0], bal1=S['hum'][q]['bal'][ib])
                        break
                if src:
                    ins.append(dict(t=t, p=p, name=X.name(p), bal0=b[i - 1], bal1=b[i], amount=d, terr=te[i], src=src))
            lv = X.leave.get(p)
            if lv and t > lv['t'] and b[i - 1] >= 20000 and b[i] <= 0.2 * b[i - 1] and te[i] == te[i - 1]:
                a = max(x for x in tk if x <= t - 1)
                bb = min(x for x in tk if x >= t)
                ia, ib = tk.index(a), tk.index(bb)
                want = (b[i - 1] - b[i]) * 960 / 1024
                cand = sorted(((S['hum'][q]['bal'][ib] - S['hum'][q]['bal'][ia], q) for q in range(X.H) if q != p and X.team[q] == X.team[p]), reverse=True)
                to = [dict(q=q, name=X.name(q), gain=g) for g, q in cand[:1] if g >= 0.7 * want]
                outs.append(dict(t=t, p=p, name=X.name(p), bal0=b[i - 1], bal1=b[i], terr=te[i], to=to))
    return ins, outs


def sec_lumps(X):
    ins, outs = lump_rows(X)
    print('空壳整笔转交（引擎规则 = 干净模拟器 bots.js botAttackTeam/botDonate：离开的真人由内置 AI 托管，没有可打的地、发不了船时，把全部余额交给一个「最近在打仗」的队友，手续费 64/1024，不占配额、不是指令）')
    print(f"我方号收到 {len(ins)} 笔，共 {fmt(sum(r['amount'] for r in ins))}：")
    for r in ins:
        s = r['src']
        print(f"   t={r['t']:5d} {r['name']:14s} 地 {r['terr']:5d} 兵 {fmt(r['bal0'])}→{fmt(r['bal1'])}（+{r['amount']}）← {s['name']}（t={s['leftT']} 离开；余额 {s['bal0']}→{s['bal1']}，×960/1024={s['bal0'] * 960 // 1024}）")
    print(f"我方空壳转出 {len(outs)} 笔，共 {fmt(sum(r['bal0'] - r['bal1'] for r in outs))}：")
    for r in outs:
        print(f"   t={r['t']:5d} 空壳 {r['name']:14s} 地 {r['terr']:5d} 兵 {fmt(r['bal0'])}→{fmt(r['bal1'])} → " + '去向没有逐笔核对' + (''.join(f"（同队里同一采样段余额涨得最多的：{x['name']} +{fmt(x['gain'])}）" for x in r['to'])))
    return ins, outs


def sec_dens(X, t=None):
    tt, rows = dens_rows(X, t)
    print(f"t={tt} 各队在场真人：我方号 vs 外人（地、兵、密度=兵/地、单号领土中位）")
    tot = dict(ours=[0, 0, 0], rest=[0, 0, 0])
    for r in rows:
        o, e = r['ours'], r['rest']
        for tag, v in (('ours', o), ('rest', e)):
            tot[tag][0] += v['n']
            tot[tag][1] += v['land']
            tot[tag][2] += v['bal']
        print(f"   队{r['team']}：我方 {o['n']} 个 地 {o['land']}（{100 * o['land'] / X.land:.1f}%）兵 {fmt(o['bal'])} 密度 {o['dens']} 中位 {o['med']}"
              f" ｜ 外人 {e['n']} 个 地 {e['land']}（{100 * e['land'] / X.land:.1f}%）兵 {fmt(e['bal'])} 密度 {e['dens']} 中位 {e['med']}；最大的：{'、'.join(e['names'])}")
    for tag, nm in (('ours', '我方合计'), ('rest', '外人合计')):
        n, land, bal = tot[tag]
        print(f"   {nm}：{n} 个 地 {land}（{100 * land / X.land:.1f}%）兵 {fmt(bal)} 密度 {bal / max(1, land):.1f}")


# ------------------------------------------------------------------ roster
def takers(X, me, t0, t1, kind='lost', top=4):
    d = X.led_sum(me, kind, t0, t1, by='other')
    tot = sum(d.values())
    items = sorted(d.items(), key=lambda kv: -kv[1])[:top]
    return tot, [(o, v) for o, v in items]


def sec_roster(X):
    S = X.S
    print('我方每个号（重演真值）。「被拿走的地」= 死前 900 拍内各进攻者从它手里拿走的格数')
    print(' me 名字             队 出生框(x0,y0)  离开拍 阵亡拍  峰值地  结局              死前900拍谁拿走了地')
    for p in X.squad:
        hb = S['hum'][p]
        peak = max(hb['terr'])
        peak_t = S['ticks'][hb['terr'].index(peak)]
        lv = X.leave.get(p)
        dt = X.deathT[p]
        fb = S['finalBots'][str(p)]
        if dt >= 0:
            tot, tk = takers(X, p, dt - 900, dt + 1)
            who = '；'.join(f"{X.name(o)}[{X.cls(p, o, dt)}] {v}" for o, v in tk)
            end = f"阵亡 t={dt}"
        else:
            who = ''
            end = f"存活 地{fb['terr']} 兵{fmt(fb['bal'])}" + ('(空壳)' if fb['st'] == 2 else '')
        sb = S['spawnBox'].get(str(p), [0, 0, 0, 0, 0])
        print(f"{p:3d} {X.M.bots[p].name if p in X.M.bots else '?':16s} {X.team[p]:2d} ({sb[0]:4d},{sb[1]:4d})  {lv['t'] if lv else '-':>6} {dt if dt >= 0 else '-':>6} {peak:6d}@{peak_t:<5d} {end:18s} {who}")


# ------------------------------------------------------------------ ledger
KINDS = ['inc', 'capLoss', 'huskLoss', 'atkOut', 'boatOut', 'fee', 'donOut', 'donFee', 'donIn', 'spent', 'gain', 'lost', 'dmg', 'capRet',
         'boatGiftOut', 'boatGiftLost', 'boatGiftIn', 'waste', 'seaLoss', 'retreatBack']
KIND_CN = dict(inc='利息+地租', capLoss='顶格少拿', huskLoss='空壳少拿', atkOut='陆攻出兵', boatOut='发船出兵', fee='出兵手续费', donOut='捐出到账', donFee='捐款手续费',
               donIn='收到捐款', spent='战斗耗兵', gain='得地', lost='失地', dmg='被打掉兵', capRet='回兵溢出',
               boatGiftOut='船兵交友军', boatGiftLost='船兵交接蒸发', boatGiftIn='收到船兵', waste='其它白损', seaLoss='海上损失', retreatBack='撤回兵')


def ledger_totals(X, me, t0=0, t1=10 ** 9):
    return {k: X.led_sum(me, k, t0, t1) for k in KINDS}


def sec_ledger(X, me=None, win=500):
    if me is None:
        print('整局兵力去向账（单位：兵；得地/失地单位：格）。顶格少拿 = 兵力超过 100×领土后利率被降档、以及撞 150×领土硬顶而少拿的利息；空壳少拿 = 离开后不再有利息')
        for part in (KINDS[:14], KINDS[14:]):
            print(' me 名字            队 ' + ' '.join(f'{KIND_CN[k]:>8s}' for k in part))
            for p in X.squad:
                T = ledger_totals(X, p)
                if part is not KINDS[:14] and not any(T[k] for k in part):
                    continue
                print(f"{p:3d} {X.M.bots[p].name if p in X.M.bots else '?':14s} {X.team[p]:2d} " + ' '.join(f'{fmt(T[k]):>10s}' for k in part))
        print('\n战斗耗兵 / 得地 按对方类别：')
        for p in X.squad:
            sp = X.led_sum(p, 'spent', by='cls')
            ga = X.led_sum(p, 'gain', by='cls')
            if not sp:
                continue
            parts = []
            for c in sorted(sp, key=lambda c: -sp[c]):
                eff = f"{sp[c] / ga[c]:.1f}兵/格" if ga.get(c) else '没拿到地'
                parts.append(f"{c} 耗{fmt(sp[c])} 得{ga.get(c, 0)}格({eff})")
            print(f"  {p:3d} {X.M.bots[p].name:14s} " + '；'.join(parts))
        print('\n失地 / 被打掉兵 按对方类别：')
        for p in X.squad:
            lo = X.led_sum(p, 'lost', by='cls')
            dm = X.led_sum(p, 'dmg', by='cls')
            if not lo and not dm:
                continue
            parts = [f"{c} 失{lo.get(c, 0)}格 掉{fmt(dm.get(c, 0))}兵" for c in sorted(set(lo) | set(dm), key=lambda c: -(lo.get(c, 0)))]
            print(f"  {p:3d} {X.M.bots[p].name:14s} " + '；'.join(parts))
        return
    print(f"me={me} {X.name(me)} 队{X.team[me]}：每 {win} 拍的兵力去向")
    end = X.end_of(me)
    tot = ledger_totals(X, me)
    ks = [k for k in KINDS if tot[k]]
    print('   窗口      地    兵   ' + ' '.join(f'{KIND_CN[k]:>8s}' for k in ks))
    for w in range(0, end + 1, win):
        T = ledger_totals(X, me, w, w + win)
        print(f"{w:5d}~{w + win - 1:<5d} {X.terr(me, w):6d} {fmt(X.bal(me, w)):>6s} " + ' '.join(f'{fmt(T[k]):>10s}' for k in ks))


# ------------------------------------------------------------------ neigh
def neigh_line(X, n):
    me = n['p']
    nb = []
    for q, cnt, terr, bal, tm, kind in n['nb']:
        dens = bal / terr if terr else 0
        nb.append(f"{X.name(q)}[{X.cls(me, q, n['t'])}] 接{cnt} 地{terr} 密{dens:.0f}")
    on = ' '.join(f"{X.name(a)}:{fmt(v)}" for a, v, tm in n['on'])
    mine = ' '.join(f"{X.name(a)}:{fmt(v)}" for a, v in n['mine'])
    dens = n['bal'] / n['terr'] if n['terr'] else 0
    return (f"t={n['t']:5d} 地{n['terr']:6d} 兵{fmt(n['bal']):>6s} 密{dens:5.1f}{' 空壳' if n['st'] == 2 else ''} 边{n['border']} 岸{n['coast']} 无主邻格{n['neut']} 船{n['boats']}"
            f" | 邻居{n['nbAll']}: " + '；'.join(nb[:5]) + (f" | 被攻: {on}" if on else '') + (f" | 在攻: {mine}" if mine else ''))


def sec_neigh(X, me, t0=0, t1=10 ** 9):
    for n in X.neigh[me]:
        if t0 <= n['t'] <= t1:
            print(neigh_line(X, n))


def enemy_contact(X, n):
    """这一拍的邻居里：敌方真人（含空壳）、内置 AI、队友 各接壤多少格。"""
    me = n['p']
    out = defaultdict(int)
    for q, cnt, terr, bal, tm, kind in n['nb']:
        c = X.cls(me, q, n['t'])
        if c.startswith('敌方') or '异队' in c:
            out['enemy'] += cnt
        elif c == '内置AI':
            out['ai'] += cnt
        else:
            out['mate'] += cnt
    return out


def sec_boxed(X):
    print('没有敌方真人邻居的时段（只挨队友 / 内置 AI / 水 / 无主地）。密 = 兵/地；顶格少拿 = 该时段内因超软上限少拿的利息')
    for p in X.squad:
        runs = []
        cur = None
        for n in X.neigh[p]:
            if n['st'] == 2:
                break
            ec = enemy_contact(X, n)
            boxed = ec['enemy'] == 0 and n['neut'] == 0 and n['t'] >= 900
            if boxed:
                if cur is None:
                    cur = [n['t'], n['t'], [], ec['ai']]
                cur[1] = n['t']
                cur[2].append(n['bal'] / max(1, n['terr']))
                cur[3] = max(cur[3], ec['ai'])
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
        runs = [r for r in runs if r[1] - r[0] >= 180]
        if not runs:
            continue
        parts = []
        for a, b, ds, ai in runs:
            cl = X.led_sum(p, 'capLoss', a, b + 90)
            inc = X.led_sum(p, 'inc', a, b + 90)
            parts.append(f"t={a}~{b}（密 {min(ds):.0f}→{max(ds):.0f}，AI 邻格最多 {ai}，实得利息 {fmt(inc)}，顶格少拿 {fmt(cl)}）")
        print(f"  {p:3d} {X.M.bots[p].name:14s} 队{X.team[p]}: " + '；'.join(parts))


# ------------------------------------------------------------------ protbox（被「保护名单」围住）
_POOL = None


def pool_set():
    """策略源码第一行的 SQUAD_POOL_SET（isOurSquadBot 按它认号）。"""
    global _POOL
    if _POOL is None:
        import re
        src = open('/agent/repos/c136-data/src/strategy/v27-team-c110.js').readline()
        m = re.search(r'new Set\(\[(.*)\]\)', src)
        _POOL = set(s.lower() for s in json.loads('[' + m.group(1) + ']')) if m else set()
    return _POOL


def eng_name(X, p):
    an = X.S.get('allNames')
    if an and p < len(an):
        return an[p]
    return X.name(p)


def prot_kind(X, me, o):
    """策略眼里 o 相对 me 是什么：'mate' 同队；'xsquad' 异队但名字在池里的真人（含我方号、空壳、撞名外人）；'poolai' 名字在池里的内置 AI；
    'open' 可以打的（敌方真人 / 普通内置 AI）。前三种都不进邻居表。"""
    if X.team[o] > 0 and X.team[o] == X.team[me]:
        return 'mate'
    nm = (eng_name(X, o) or '').strip()
    if nm.lower() in pool_set() or '[NPL]' in nm.upper() or '[NOPE]' in nm.upper():
        return 'xsquad' if o < X.H else 'poolai'
    return 'open'


def protbox_rows(X, min_len=180, t_from=600):
    """我方在场号「策略眼里没有可打的邻居、也没有无主邻格」的时段（nb=0 且 neut=0），以及这时它实际挨着谁。"""
    out = []
    for p in X.squad:
        cur = None
        runs = []
        for n in X.neigh[p]:
            if n['st'] == 2 or n['t'] < t_from:
                continue
            c = defaultdict(int)
            for o, cnt, terr, bal, _tm, _h in n['nb']:
                c[prot_kind(X, p, o)] += cnt
            boxed = c['open'] == 0 and n['neut'] == 0
            if boxed:
                if cur is None:
                    cur = dict(p=p, t0=n['t'], t1=n['t'], dens=[], xsquad=0, poolai=0, mate=0, n=0, who=defaultdict(int))
                cur['t1'] = n['t']
                cur['n'] += 1
                cur['dens'].append(n['bal'] / max(1, n['terr']))
                for k in ('xsquad', 'poolai', 'mate'):
                    cur[k] = max(cur[k], c[k])
                for o, cnt, terr, bal, _tm, _h in n['nb']:
                    k = prot_kind(X, p, o)
                    if k in ('xsquad', 'poolai'):
                        cur['who'][o] = max(cur['who'][o], cnt)
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
        for r in runs:
            if r['t1'] - r['t0'] >= min_len:
                r['capLoss'] = X.led_sum(p, 'capLoss', r['t0'], r['t1'] + 90)
                r['inc'] = X.led_sum(p, 'inc', r['t0'], r['t1'] + 90)
                out.append(r)
    return out


def sec_protbox(X):
    rows = protbox_rows(X)
    print('策略眼里「没有可打的邻居、也没有无主邻格」的时段（同队、名字在池里的异队号/空壳、名字撞池的内置 AI 都不进邻居表）。')
    print('异队池内号 / 撞名 AI = 这段时间里实际挨着、但被保护名单挡住不能打的接壤格数（最大值）')
    if not rows:
        print('   （没有）')
        return
    for r in sorted(rows, key=lambda r: (r['p'], r['t0'])):
        who = '；'.join(f"{eng_name(X, o) if o >= X.H else X.name(o)}{'(AI)' if o >= X.H else ''} {c}格" for o, c in sorted(r['who'].items(), key=lambda kv: -kv[1])[:4])
        print(f"   {X.name(r['p'])[:14]:14s} 队{X.team[r['p']]} t={r['t0']:5d}~{r['t1']:5d}（{r['t1'] - r['t0'] + 90} 拍）密 {min(r['dens']):.0f}~{max(r['dens']):.0f}"
              f" ｜ 挨着队友 {r['mate']} 格、异队池内号 {r['xsquad']} 格、撞名 AI {r['poolai']} 格 ｜ 实得利息 {fmt(r['inc'])}、顶格少拿 {fmt(r['capLoss'])}" + (f" ｜ {who}" if who else ''))
    tot = sum(r['t1'] - r['t0'] + 90 for r in rows)
    pr = [r for r in rows if r['xsquad'] or r['poolai']]
    print(f"合计 {len(rows)} 段 {tot} 拍；其中 {len(pr)} 段（{sum(r['t1'] - r['t0'] + 90 for r in pr)} 拍）挨着被保护名单挡住的地")


# ------------------------------------------------------------------ deaths
def sec_deaths(X, only=None):
    S = X.S
    order = sorted([p for p in X.squad if X.deathT[p] >= 0], key=lambda p: X.deathT[p])
    for p in order:
        if only is not None and p != only:
            continue
        dt = X.deathT[p]
        lv = X.leave.get(p)
        b = X.M.bots.get(p)
        print(f"\n=== me={p} {b.name if b else '?'} 队{X.team[p]} 阵亡 t={dt}" + (f"（t={lv['t']} 已离开成空壳，当时地 {lv['terr']} 兵 {fmt(lv['bal'])}）" if lv else '') + ' ===')
        hb = S['hum'][p]
        peak = max(hb['terr'])
        print(f"峰值领土 {peak} @t={S['ticks'][hb['terr'].index(peak)]}；阵亡线 = 峰值/4 ≈ {peak // 4}")
        # 轨迹
        pts = [t for t in range(max(0, dt - 900), dt, 90)] + [dt - 30, dt - 1]
        print('轨迹: ' + '  '.join(f"t{t}:{X.terr(p, t)}/{fmt(X.bal(p, t))}" for t in sorted(set(pts)) if t >= 0))
        for span in (300, 900):
            tot, tk = takers(X, p, dt - span, dt + 1)
            dtot, dk = takers(X, p, dt - span, dt + 1, kind='dmg')
            print(f"死前 {span} 拍：失地 {tot} 格 ← " + '；'.join(f"{X.name(o)}[{X.cls(p, o, dt)}] {v}" for o, v in tk)
                  + f" ｜ 被打掉兵 {fmt(dtot)} ← " + '；'.join(f"{X.name(o)} {fmt(v)}" for o, v in dk))
        T = ledger_totals(X, p, dt - 900, dt + 1)
        print('死前 900 拍自己的账: ' + ' '.join(f"{KIND_CN[k]}={fmt(T[k])}" for k in KINDS if T[k]))
        sp = X.led_sum(p, 'spent', dt - 900, dt + 1, by='other')
        ga = X.led_sum(p, 'gain', dt - 900, dt + 1, by='other')
        if sp:
            print('  耗兵对象: ' + '；'.join(f"{X.name(o)}[{X.cls(p, o, dt)}] 耗{fmt(v)} 得{ga.get(o, 0)}格" for o, v in sorted(sp.items(), key=lambda kv: -kv[1])[:5]))
        # 邻居
        ns = [n for n in X.neigh[p] if dt - 400 <= n['t'] < dt]
        for n in ns[-3:]:
            print('  ' + neigh_line(X, n))
        # 指令
        cm = [c for c in S['squadCmds'] if c['p'] == p and dt - 600 <= c['t'] <= dt]
        if cm:
            print(f"死前 600 拍自己的指令 {len(cm)} 条（生效 {sum(c['ok'] for c in cm)}）: " + ' '.join(
                f"t{c['t']}:{'船' if c['k'] == 'boat' else '撤' if c['k'] == 'retreat' else '攻' + X.name(c.get('to', 512))}{c.get('pct', '')}‰{'' if c['ok'] else '×'}→{fmt(c['sent'])}" for c in cm[-14:]))
        else:
            print('死前 600 拍自己没有任何陆攻/发船指令')
        on = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('to') == p and dt - 600 <= c['t'] <= dt]
        if on:
            agg = defaultdict(lambda: [0, 0, 10 ** 9, 0])
            for c in on:
                a = agg[c['p']]
                a[0] += 1
                a[1] += c['sent']
                a[2] = min(a[2], c['t'])
                a[3] = max(a[3], c['t'])
            print('死前 600 拍对它的陆攻指令: ' + '；'.join(f"{X.name(a)}[{X.cls(p, a, dt)}] {v[0]}条 共{fmt(v[1])}兵 t={v[2]}~{v[3]}" for a, v in sorted(agg.items(), key=lambda kv: -kv[1][1])))
        dn_in = [x for x in S['donations'] if x['to'] == p and x['ok'] and dt - 900 <= x['t'] <= dt]
        dn_out = [x for x in S['donations'] if x['from'] == p and x['ok'] and dt - 900 <= x['t'] <= dt]
        if dn_in:
            print('死前 900 拍收到捐款: ' + '；'.join(f"t{x['t']} {X.name(x['from'])} {fmt(x['delivered'])}" for x in dn_in))
        if dn_out:
            print('死前 900 拍自己捐出: ' + '；'.join(f"t{x['t']} →{X.name(x['to'])} {fmt(x['delivered'])}(费{fmt(x['fee'])})" for x in dn_out))
        if b:
            rs = [e for q in X.squad if q in X.M.bots for e in X.M.bots[q].assists if e['ally'] == p and dt - 900 <= e['t'] <= dt]
            if rs:
                print(f"死前 900 拍别的号为它发的协防戳 {len(rs)} 条: " + ' '.join(f"t{e['t']}:{X.M.bots[e['me']].name}→{e['enemyName']}" for e in rs[:10]))


# ------------------------------------------------------------------ donations
def don_rows(X):
    S = X.S
    rows = []
    for x in S['donations']:
        if not (x['from'] in X.squad or x['to'] in X.squad):
            continue
        t, q = x['t'], x['to']
        r = dict(x)
        r['eff'] = x['delivered'] / (x['delivered'] + x['fee']) if x['delivered'] + x['fee'] else 0
        r['toDens'] = x['toBal'] / x['toTerr'] if x['toTerr'] else 0
        r['toRoom'] = 150 * x['toTerr'] - x['toBal']
        t2 = min(X.endT, t + 300)
        r['toAlive300'] = not (X.deathT[q] >= 0 and X.deathT[q] <= t2) if q < X.H else None
        r['toTerr300'] = X.terr(q, t2) if q < X.H else None
        r['toBal300'] = X.bal(q, t2) if q < X.H else None
        if q in X.squad:
            r['toSpent300'] = X.led_sum(q, 'spent', t, t + 300)
            r['toGain300'] = X.led_sum(q, 'gain', t, t + 300)
            r['toDmg300'] = X.led_sum(q, 'dmg', t, t + 300)
            r['toDonOut300'] = sum(y['delivered'] for y in S['donations'] if y['from'] == q and y['ok'] and t < y['t'] <= t + 300)
        cm = [c for c in X.M.cmds if c['player'] == q and t < c['t'] <= t + 300 and c['id'] in (1, 3)]
        r['toCmds300'] = len(cm)
        rows.append(r)
    return rows


def sec_don(X):
    rows = don_rows(X)
    ok = [r for r in rows if r['ok']]
    out = [r for r in ok if r['from'] in X.squad]
    print(f"我方参与的已执行捐款 {len(ok)} 笔（我方捐出 {len(out)} 笔：到账 {fmt(sum(r['delivered'] for r in out))}，手续费 {fmt(sum(r['fee'] for r in out))}，"
          f"损耗率 {pc(sum(r['fee'] for r in out), sum(r['fee'] + r['delivered'] for r in out))}）")
    print('    t  捐款人→收款人                         pct  捐前兵  到账   手续费 到账率 | 收款人: 地  密  余量 被攻 | 300拍后: 存活 地 兵 期间耗兵/得地/被打掉/又捐出 指令数')
    for r in ok:
        q = r['to']
        on = '+'.join(f"{X.name(a)}:{fmt(v)}" for a, v in r['onRecv'][:2]) or '-'
        extra = ''
        if 'toSpent300' in r:
            extra = f"{fmt(r['toSpent300'])}/{r['toGain300']}格/{fmt(r['toDmg300'])}/{fmt(r['toDonOut300'])}"
        qq = f" 配额{r['qUsed0']}→{r['qUsed1']}/{r['qLim']}" if 'qUsed0' in r else ''
        print(f"{r['t']:5d}  {X.name(r['from'])[:16]:16s}→{X.name(q)[:16]:16s}[{X.cls(r['from'], q, r['t'])[:8]:8s}] {r['pct']:4d} {fmt(r['B0']):>7s} {fmt(r['delivered']):>6s} {fmt(r['fee']):>6s} {100 * r['eff']:4.0f}% |"
              f" {r['toTerr']:6d} {r['toDens']:4.0f} {fmt(r['toRoom']):>6s} {on[:28]:28s} | {'活' if r['toAlive300'] else '亡'} {r['toTerr300']} {fmt(r['toBal300'] or 0)} {extra} {r['toCmds300']}{qq}")
    # 小额
    small = [r for r in out if r['pct'] < 150]
    if small:
        print(f"其中 pct<150 的 {len(small)} 笔：到账 {fmt(sum(r['delivered'] for r in small))}，手续费 {fmt(sum(r['fee'] for r in small))}，损耗率 {pc(sum(r['fee'] for r in small), sum(r['fee'] + r['delivered'] for r in small))}")
    husk = [r for r in out if r['toLeft']]
    if husk:
        print(f"捐给空壳（已离开的号）{len(husk)} 笔：到账 {fmt(sum(r['delivered'] for r in husk))}，手续费 {fmt(sum(r['fee'] for r in husk))}")
    dead = [r for r in out if r['toAlive300'] is False]
    if dead:
        print(f"收款人 300 拍内阵亡的 {len(dead)} 笔：到账 {fmt(sum(r['delivered'] for r in dead))}，手续费 {fmt(sum(r['fee'] for r in dead))}")
    # 对倒
    pp = []
    for i, a in enumerate(ok):
        for b in ok[i + 1:]:
            if b['t'] - a['t'] > 150:
                break
            if b['from'] == a['to'] and b['to'] == a['from']:
                pp.append((a, b))
                break
    if pp:
        print(f"对倒（A→B 后 150 拍内 B→A）{len(pp)} 组：回流 {fmt(sum(b['delivered'] for a, b in pp))}，两头手续费 {fmt(sum(a['fee'] + b['fee'] for a, b in pp))}")
        for a, b in pp:
            print(f"   t{a['t']} {X.name(a['from'])}→{X.name(a['to'])} {fmt(a['delivered'])}(费{fmt(a['fee'])})；t{b['t']} 回 {fmt(b['delivered'])}(费{fmt(b['fee'])})")
    return rows


# ------------------------------------------------------------------ probe / gifts
def probe_verdict(rs):
    """rs：一条捐款日志在日志拍、+7、+14、+21、+28 拍用引擎校验函数逐项判的结果。返回 (结论, 说明)。"""
    if not rs:
        return ('无探针', '')
    later = [r for r in rs[1:4]] or rs
    if all(not r['recvAlive'] for r in later):
        return ('收款人已阵亡', '')
    if all(r.get('donorOk', 1) == 0 for r in later):
        return ('捐款人已阵亡或离开', '')
    if all(r.get('sameTeam', 1) == 0 for r in later):
        return ('不同队', '')
    if all(r['amount'] < 1 for r in later):
        r = later[0]
        return ('收款人顶格', f"余量 {r['room']}（地 {r['toTerr']} 兵 {r['toBal']}）")
    qs = [r for r in later if r['amount'] >= 1]
    if all(not r['quotaOk'] for r in qs):
        r = qs[0]
        return ('配额不够', f"这笔要 {r['cost']} 点，已用 {r['used']}/{r['lim']}（想捐 {r['amount']}）")
    if any(not r['quotaOk'] for r in qs):
        r = [x for x in qs if not x['quotaOk']][0]
        return ('配额临界', f"要 {r['cost']} 点，已用 {r['used']}/{r['lim']}")
    return ('校验能过却没执行', f"想捐 {qs[0]['amount']}，要 {qs[0]['cost']} 点，已用 {qs[0]['used']}/{qs[0]['lim']}")


def probe_rows(X):
    from r06lib import donation_truth
    out = []
    P = X.S.get('probes') or {}
    for rec in donation_truth(X.M):
        r = dict(rec)
        r['probe'] = P.get(str(rec['line']))
        if rec['accepted'] is False:
            r['verdict'], r['why'] = probe_verdict(r['probe'])
        elif rec['accepted']:
            r['verdict'], r['why'] = '已执行', ''
        else:
            r['verdict'], r['why'] = '录像没覆盖', ''
        out.append(r)
    return out


def sec_probe(X, verbose=True):
    rows = probe_rows(X)
    by = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by[r['kind']][r['verdict']] += 1
    print('我方 [HL-DONATE] 日志逐条结论（已执行 = 录像里有对应捐款；其余用引擎校验函数在日志拍后 7/14/21 拍各判一次）')
    for k in sorted(by):
        print(f"  {k}: " + '；'.join(f'{v} {n}' for v, n in sorted(by[k].items(), key=lambda kv: -kv[1])))
    tot = defaultdict(int)
    for r in rows:
        tot[r['verdict']] += 1
    print('  合计: ' + '；'.join(f'{v} {n}' for v, n in sorted(tot.items(), key=lambda kv: -kv[1])))
    if verbose:
        print('没执行的逐条：')
        for r in rows:
            if r['accepted'] is False:
                print(f"   t={r['t']:5d} {X.name(r['me'])[:16]:16s}→{X.name(r['to'])[:16]:16s} {r['kind']:7s} pct={r['pct']:4d} 捐前兵 {fmt(r['myBal']):>6s} | {r['verdict']} {r['why']}")
    return rows


def sec_gifts(X):
    G = X.S.get('boatGifts') or []
    if not G:
        print('没有船靠友军岸移交兵力的事件')
        return
    out = [g for g in G if g['from'] in X.squad]
    print(f"船靠友军岸移交兵力 {len(G)} 次（我方发出 {len(out)} 次：船上兵 {fmt(sum(g['troops'] for g in out))}，到账 {fmt(sum(g['delivered'] for g in out))}，蒸发 {fmt(sum(g['troops'] - g['delivered'] for g in out))}）")
    for g in G:
        print(f"   t={g['t']:5d} {X.name(g['from'])[:16]:16s}→{X.name(g['to'])[:16]:16s}[{X.cls(g['from'], g['to'], g['t'])}] 船上 {fmt(g['troops']):>6s} 到账 {fmt(g['delivered']):>6s} 蒸发 {fmt(g['troops'] - g['delivered']):>6s}"
              f" ｜ 收方 地 {g['toTerr']} 兵 {fmt(g['toBal'])}{' 空壳' if g['toLeft'] else ''}")


# ------------------------------------------------------------------ boats
def boat_rows(X):
    """我方每条船：发船（瞄准谁）→ 靠岸（登上谁的地、船上还剩多少）或在海上消失。按引擎里的船编号（bid）配对。
    how: landed = 靠岸；sunk = 没靠岸就从海上消失且消失时船上 0 兵（被敌船打光）；gone = 没靠岸消失但还有兵（主人阵亡等）；atsea = 重放结束时还在海上。"""
    S = X.S
    rows = [dict(c=c, land=None, end=None, how='atsea') for c in S['squadCmds'] if c['k'] == 'boat' and c['ok'] and c['p'] in X.squad]
    by = defaultdict(list)
    for r in rows:
        by[(r['c']['p'], r['c'].get('bid', -1))].append(r)
    for l in S.get('boatLands') or []:
        for r in by.get((l['p'], l.get('bid', -2)), []):
            if r['land'] is None and r['c']['t'] <= l['t']:
                r['land'] = l
                r['how'] = 'landed'
                break
    for e in S.get('boatEnds') or []:
        for r in by.get((e['p'], e['bid']), []):
            if r['end'] is None and r['c']['t'] <= e['t']:
                r['end'] = e
                if r['land'] is None:
                    r['how'] = 'sunk' if e['troops'] == 0 else 'gone'
                break
    for r in rows:
        c = r['c']
        t1 = r['land']['t'] if r['land'] else (r['end']['t'] if r['end'] else X.endT)
        left = r['land']['troops'] if r['land'] else (r['end']['troops'] if r['end'] else None)
        # 海上自然损耗：每逢 t%5==3 掉 max(1, 兵>>7)
        v = c['sent']
        for t in range(c['t'] + 1, t1 + 1):
            if t % 5 == 3:
                v = max(v - max(1, v >> 7), 0)
        r['t1'] = t1
        r['decayOnly'] = v
        r['left'] = left
        r['seaLoss'] = c['sent'] - left if left is not None else None
        r['hitLoss'] = max(0, v - left) if left is not None else None   # 自然损耗之外的部分 = 被敌船打掉的
    return rows


def sec_boats(X, only=None):
    rows = boat_rows(X)
    if not rows:
        print('我方没有发过船')
        return
    print('我方发船。瞄准 = 发船那一拍按引擎靠岸规则会登上谁的地；靠岸 = 船到岸时登陆格的主人（决定这船兵打谁 / 交给谁）。')
    print('引擎：发船手续费 = 余额的 32/1024；船速 0.24~0.57 格/拍（兵越多越快，挨打后 3 拍内只有 0.04 格/拍）；每 5 拍掉 1/128 的兵；每 2 拍，7.5 格内每条敌船打掉我船「敌船兵力的 10%」')
    print(f"{'me':>3s} {'名字':14s} {'船':>3s} {'船上兵':>8s} {'手续费':>8s} | {'靠岸兵':>8s} {'自然损耗':>8s} {'被敌船打掉':>9s} {'沉没条数':>4s} | 瞄准（条数/兵） | 靠岸（条数/兵）")
    for p in X.squad:
        rs = [r for r in rows if r['c']['p'] == p]
        if not rs:
            continue
        aim = defaultdict(lambda: [0, 0])
        hit = defaultdict(lambda: [0, 0])
        for r in rs:
            c, l = r['c'], r['land']
            a = aim[X.cls(p, c['tgt'], c['t']) if c.get('tgt', -1) >= 0 else '水/未知']
            a[0] += 1
            a[1] += c['sent']
            if l is None:
                h = hit[{'sunk': '沉没', 'gone': '消失(主人阵亡等)', 'atsea': '终局还在海上'}[r['how']]]
                h[0] += 1
                h[1] += c['sent']
            else:
                key = '自己的岸' if l['self'] else (X.cls(p, l['to'], l['t']) + ('·无空槽白损' if l['noSlot'] else ''))
                h = hit[key]
                h[0] += 1
                h[1] += l['troops']
        sent = sum(r['c']['sent'] for r in rs)
        fee = sum(r['c']['fee'] for r in rs)
        landed = sum(r['land']['troops'] for r in rs if r['land'])
        dec = sum(r['c']['sent'] - r['decayOnly'] for r in rs if r['left'] is not None)
        hl = sum(r['hitLoss'] for r in rs if r['left'] is not None)
        print(f"{p:3d} {X.M.bots[p].name[:14]:14s} {len(rs):3d} {fmt(sent):>8s} {fmt(fee):>8s} | {fmt(landed):>8s} {fmt(dec):>8s} {fmt(hl):>9s} {sum(1 for r in rs if r['how'] == 'sunk'):4d} | "
              + '；'.join(f"{k} {v[0]}/{fmt(v[1])}" for k, v in sorted(aim.items(), key=lambda kv: -kv[1][1])) + ' | '
              + '；'.join(f"{k} {v[0]}/{fmt(v[1])}" for k, v in sorted(hit.items(), key=lambda kv: -kv[1][1])))
    if only is not None:
        print(f"\n逐条（me={only} {X.name(only)}）：")
        for r in rows:
            c, l = r['c'], r['land']
            if c['p'] != only:
                continue
            aim = f"{X.name(c['tgt'])}[{X.cls(only, c['tgt'], c['t'])}] 地{c.get('tgtTerr', 0)} 兵{fmt(c.get('tgtBal', 0))}" if c.get('tgt', -1) >= 0 else '水/未知'
            if l:
                hit = f"t={l['t']}（{l['t'] - c['t']} 拍）靠岸→{'自己的岸' if l['self'] else X.name(l['to']) + '[' + X.cls(only, l['to'], l['t']) + ']'} 剩 {fmt(l['troops'])}（自然损耗 {fmt(c['sent'] - r['decayOnly'])}，被敌船打掉 {fmt(r['hitLoss'])}）"
                if not l['self'] and l['to'] < 512:
                    hit += f" 对方 地{l['toTerr']} 兵{fmt(l['toBal'])}"
            elif r['how'] == 'sunk':
                hit = f"t={r['t1']}（{r['t1'] - c['t']} 拍）在海上被打光：自然损耗 {fmt(c['sent'] - r['decayOnly'])}，被敌船打掉 {fmt(r['hitLoss'])}"
            elif r['how'] == 'gone':
                hit = f"t={r['t1']} 没靠岸就消失，当时船上还有 {fmt(r['left'])}"
            else:
                hit = '重放结束时还在海上'
            print(f"   t={c['t']:5d} {c['pct']:4d}‰ 余额 {fmt(c['B0']):>6s} 船上 {fmt(c['sent']):>6s} 费 {fmt(c['fee']):>6s} 我地 {c['myTerr']:6d} | 瞄准 {aim} | {hit}")


# ------------------------------------------------------------------ fees
def sec_fees(X):
    """每条指令都按「发令时余额」收一次固定比例的手续费（陆攻 12/1024、发船 32/1024、捐款 64/1024），与这条指令实际出多少兵无关。"""
    S = X.S
    print('手续费按发令时的余额收（陆攻 1.17%、发船 3.125%、捐款 6.25%），与出兵多少无关。下面按「出兵占余额的比例」分档，看每档的出兵与手续费')
    print(f"{'me':>3s} {'名字':14s} {'总收入':>8s} | {'陆攻费':>7s} {'发船费':>7s} {'捐款费':>7s} {'费合计':>7s} {'费/收入':>7s} | 出兵<5%余额的指令：条数 出兵 手续费 费/兵 | 其中余额≥100万时")
    for p in X.squad:
        cm = [c for c in S['squadCmds'] if c['p'] == p and c['ok'] and c['k'] in ('atk', 'boat', 'boatAdd')]
        dn = [x for x in S['donations'] if x['from'] == p and x['ok']]
        if not cm and not dn:
            continue
        fa = sum(c['fee'] for c in cm if c['k'] == 'atk')
        fb = sum(c['fee'] for c in cm if c['k'] != 'atk')
        fd = sum(x['fee'] for x in dn)
        inc = X.led_sum(p, 'inc')
        small = [c for c in cm if c['B0'] > 0 and c['sent'] < 0.05 * c['B0']]
        big = [c for c in small if c['B0'] >= 10 ** 6]
        print(f"{p:3d} {X.M.bots[p].name[:14]:14s} {fmt(inc):>8s} | {fmt(fa):>7s} {fmt(fb):>7s} {fmt(fd):>7s} {fmt(fa + fb + fd):>7s} {pc(fa + fb + fd, inc):>7s} | "
              f"{len(small):3d} {fmt(sum(c['sent'] for c in small)):>7s} {fmt(sum(c['fee'] for c in small)):>7s} {pc(sum(c['fee'] for c in small), sum(c['sent'] for c in small)):>6s} | "
              f"{len(big):3d} 条 出兵 {fmt(sum(c['sent'] for c in big))} 费 {fmt(sum(c['fee'] for c in big))}")


# ------------------------------------------------------------------ nfs（isNoFullSend 误锁的重演）
def nfs_rows(X):
    """按 c110 Policy.send / updateShadowQuota（L3810-3893）的条件重演「isNoFullSend 被置真」：
    陆攻发令后第 1~7 拍内，只要余额 < 发令时余额 − 手续费，就把这段跌幅当成「这条指令实际发出去的兵」；
    想发的兵 >= 1.12 × 跌幅（且跌幅没到全部余额）→ isNoFullSend = true（此后不再复位）。
    发令拍 = 录像执行拍往前 8~14 拍里 5 的倍数（策略只在 t%5==0 决策；线上延迟 8~13 拍），想发的兵用实际发出的兵代替（偏保守）。
    开局有 [HL-OPENING] 的指令用日志里的发令拍与 spend。certain = 所有候选发令拍都满足；possible = 至少一个满足。"""
    S = X.S
    PT = S.get('perTick')
    if not PT:
        return None
    t0 = PT['t0']
    out = {}
    for p in X.squad:
        bal = PT['bal'][str(p)]

        def B(t):
            i = t - t0
            return bal[i] if 0 <= i < len(bal) and bal[i] is not None else -1

        def judge(td, want):
            b0 = B(td)
            if b0 <= 0:
                return None
            fee = 12 * b0 // 1024
            for u in range(td + 1, td + 8):
                bu = B(u)
                if bu < 0:
                    return None
                if bu < b0 - fee:
                    actual = max(0, b0 - bu - fee)
                    return dict(lock=(want >= 1.12 * actual and actual < b0 - fee - 50), u=u, actual=actual, want=want, b0=b0)
            return dict(lock=False, u=None, actual=None, want=want, b0=b0)
        sends = [c for c in S['squadCmds'] if c['p'] == p and c['k'] == 'atk' and c['ok']]
        certain = possible = None
        n = 0
        for c in sends:
            cands = [td for td in range(c['t'] - 14, c['t'] - 7) if td % 5 == 0]
            rs = [judge(td, c['sent']) for td in cands]
            rs = [r for r in rs if r]
            if not rs:
                continue
            n += 1
            if possible is None and any(r['lock'] for r in rs):
                possible = dict(t=c['t'], to=c['to'], **[r for r in rs if r['lock']][0])
            if certain is None and all(r['lock'] for r in rs):
                certain = dict(t=c['t'], to=c['to'], **rs[0])
        # 开局日志（发令拍与 spend 都是日志原文）
        op = None
        b = X.M.bots.get(p)
        for e in (b.opening if b else []):
            r = judge(e['t'], e.get('spend', 0))
            if r and r['lock']:
                op = dict(t=e['t'], **r)
                break
        out[p] = dict(sends=n, certain=certain, possible=possible, opening=op)
    return out


def sec_nfs(X):
    rows = nfs_rows(X)
    if rows is None:
        print('重放里没有逐拍余额（重跑 run_truth.sh）')
        return
    print('isNoFullSend 误锁重演（推断：发令拍日志里没有，按执行拍往前 8~14 拍的 5 的倍数取候选）。锁定后 t>=4800 的几个保守闸门全部失效（safeAt 联防留兵、offers 里的 shadowedByTop / isLeaderFortress / isGiantTopRival / isStaleHardAgg、buyLand 的 isSiegeShrink）')
    print(f"{'me':>3s} {'名字':14s} {'陆攻':>4s} | 肯定被锁（所有候选发令拍都满足） | 可能被锁（至少一个候选满足） | 开局日志直接判")
    for p, r in rows.items():
        if not r['sends']:
            continue

        def f(x):
            if not x:
                return '没有'
            return f"t={x['t']} 想发 {fmt(x['want'])}，窗口内余额只跌了 {fmt(x['actual'])}（第 {x['u']} 拍）"
        end = X.end_of(p)
        lv = X.leave.get(p, {}).get('t')
        print(f"{p:3d} {X.M.bots[p].name[:14]:14s} {r['sends']:4d} | {f(r['certain'])} | {f(r['possible'])} | {f(r['opening'])} | {'离开 t=' + str(lv) if lv else ('阵亡 t=' + str(end) if X.deathT[p] >= 0 else '活到终局')}")


# ------------------------------------------------------------------ cmds
def sec_cmds(X):
    S = X.S
    by = defaultdict(list)
    for c in S['squadCmds']:
        if c['p'] in X.squad and c['k'] in ('atk', 'boat'):
            by[c['p']].append(c)
    print('我方指令是否生效（重演）。空指令 = 进了录像但引擎没执行（没扣兵没扣费）；连发 = 同一拍 ≥4 条')
    print(' me 名字            陆攻 生效 空   发船 生效 | 出兵合计  手续费 费/兵 | 连发组 连发里生效条数 连发出兵 连发手续费 | 最大单拍')
    for p in X.squad:
        cs = by.get(p, [])
        if not cs:
            continue
        atk = [c for c in cs if c['k'] == 'atk']
        boat = [c for c in cs if c['k'] == 'boat']
        sent = sum(c['sent'] for c in cs)
        fee = sum(c['fee'] for c in cs)
        tick = defaultdict(list)
        for c in cs:
            tick[c['t']].append(c)
        bursts = {t: v for t, v in tick.items() if len(v) >= 4}
        b_ok = sum(c['ok'] for v in bursts.values() for c in v)
        b_sent = sum(c['sent'] for v in bursts.values() for c in v)
        b_fee = sum(c['fee'] for v in bursts.values() for c in v)
        mx = max(tick.items(), key=lambda kv: len(kv[1]))
        print(f"{p:3d} {X.M.bots[p].name:14s} {len(atk):4d} {sum(c['ok'] for c in atk):4d} {sum(1 - c['ok'] for c in atk):3d}  {len(boat):4d} {sum(c['ok'] for c in boat):4d} | {fmt(sent):>8s} {fmt(fee):>7s} {pc(fee, sent):>6s} |"
              f" {len(bursts):4d} {b_ok:6d} {fmt(b_sent):>10s} {fmt(b_fee):>8s} | t={mx[0]} {len(mx[1])}条")
    # 最贵的连发
    allb = []
    for p, cs in by.items():
        tick = defaultdict(list)
        for c in cs:
            tick[c['t']].append(c)
        for t, v in tick.items():
            okv = [c for c in v if c['ok']]
            if len(okv) >= 3:
                allb.append((sum(c['sent'] + c['fee'] for c in okv), p, t, okv))
    allb.sort(reverse=True)
    if allb:
        print('同拍生效 ≥3 条里出兵最多的：')
        for tot, p, t, v in allb[:10]:
            b0 = v[0]['B0']
            kinds = ''.join('船' if c['k'] == 'boat' else '攻' for c in v)
            print(f"   t={t} {X.M.bots[p].name:14s} {kinds} 拍前兵 {fmt(b0)} → 一拍内出兵+费 {fmt(tot)}（{pc(tot, b0)}），领土 {v[0].get('myTerr', '?')}")


# ------------------------------------------------------------------ front
def sec_front(X, win=900):
    print(f"每个号每 {win} 拍的主要交换（耗兵→得地；失地←；被打掉兵←）。只列有战斗的窗口")
    for p in X.squad:
        end = X.end_of(p)
        lines = []
        for w in range(0, end + 1, win):
            sp = X.led_sum(p, 'spent', w, w + win, by='other')
            ga = X.led_sum(p, 'gain', w, w + win, by='other')
            lo = X.led_sum(p, 'lost', w, w + win, by='other')
            dm = X.led_sum(p, 'dmg', w, w + win, by='other')
            if not sp and not lo:
                continue
            a = '；'.join(f"{X.name(o)}[{X.cls(p, o, w)[:4]}] 耗{fmt(v)}得{ga.get(o, 0)}" for o, v in sorted(sp.items(), key=lambda kv: -kv[1])[:3])
            b = '；'.join(f"{X.name(o)}[{X.cls(p, o, w)[:4]}] {v}格/{fmt(dm.get(o, 0))}兵" for o, v in sorted(lo.items(), key=lambda kv: -kv[1])[:3])
            husk = ' 空壳' if p in X.leave and w >= X.leave[p]['t'] else ''
            lines.append(f"   {w:5d}~ 地{X.terr(p, w)} 兵{fmt(X.bal(p, w))}{husk} | 打: {a or '-'} | 被打: {b or '-'}")
        if lines:
            print(f" me={p} {X.M.bots[p].name} 队{X.team[p]}")
            print('\n'.join(lines))


# ------------------------------------------------------------------ pair / cmdlist
def sec_pair(X, me, t0=0, t1=10 ** 9):
    """某个号在 [t0,t1) 内与每个对手的交换：我花的兵→得地；失地←对方；被对方打掉的兵。"""
    sp = X.led_sum(me, 'spent', t0, t1, by='other')
    ga = X.led_sum(me, 'gain', t0, t1, by='other')
    lo = X.led_sum(me, 'lost', t0, t1, by='other')
    dm = X.led_sum(me, 'dmg', t0, t1, by='other')
    w = X.S['ledgerWindow']
    print(f"me={me} {X.name(me)} 队{X.team[me]}：t={t0}~{min(t1, X.end_of(me))} 与各对手的交换（账按 {w} 拍一格记，窗口边界向外取整）")
    for o in sorted(set(sp) | set(ga) | set(lo) | set(dm), key=lambda o: -(sp.get(o, 0) + dm.get(o, 0))):
        per = f"{sp.get(o, 0) / ga[o]:.1f} 兵/格" if ga.get(o) else '-'
        print(f"   {X.name(o)[:22]:22s}[{X.cls(me, o, max(t0, 0))}] 我耗 {fmt(sp.get(o, 0)):>7s} 得 {ga.get(o, 0):6d} 格（{per}）｜失 {lo.get(o, 0):6d} 格 被打掉 {fmt(dm.get(o, 0)):>7s}")


def sec_cmdlist(X, me, t0=0, t1=10 ** 9):
    """某个号在 [t0,t1] 内进了录像的每条指令（陆攻/发船/撤回/捐款）与别人对它下的陆攻。"""
    S = X.S
    rows = []
    for c in S['squadCmds']:
        if not (t0 <= c['t'] <= t1):
            continue
        if c['p'] == me:
            if c['k'] == 'atk':
                what = f"攻 {X.name(c.get('to', 512))}[{X.cls(me, c.get('to', 512), c['t'])}]"
            elif c['k'] == 'boat':
                tg = c.get('tgt', -1)
                what = '船→' + (f"{X.name(tg)}[{X.cls(me, tg, c['t'])}]" if tg >= 0 else '?')
            else:
                what = c['k']
            rows.append((c['t'], 0, f"{what} {c.get('pct', '')}‰ 余额 {fmt(c.get('B0', 0))} 出兵 {fmt(c.get('sent', 0))} 费 {fmt(c.get('fee', 0))}{'' if c['ok'] else ' ×没生效'} 我地 {c.get('myTerr', '?')}"))
        elif c['k'] == 'atk' and c.get('to') == me:
            rows.append((c['t'], 1, f"    ← {X.name(c['p'])}[{X.cls(me, c['p'], c['t'])}] 攻我 {c.get('pct', '')}‰ 出兵 {fmt(c.get('sent', 0))}{'' if c['ok'] else ' ×没生效'}"))
    for x in S['donations']:
        if not (t0 <= x['t'] <= t1) or not x['ok']:
            continue
        if x['from'] == me:
            rows.append((x['t'], 0, f"捐→{X.name(x['to'])} {x.get('pct', '')}‰ 到账 {fmt(x['delivered'])} 费 {fmt(x['fee'])}"))
        elif x['to'] == me:
            rows.append((x['t'], 1, f"    ← 收到 {X.name(x['from'])} 捐款 {fmt(x['delivered'])}"))
    print(f"me={me} {X.name(me)} 队{X.team[me]}：t={t0}~{min(t1, X.endT)} 进了录像的指令（缩进行 = 别人对它）")
    for t, _, s in sorted(rows, key=lambda r: (r[0], r[1])):
        print(f"   t={t:5d} 地{X.terr(me, t):6d} 兵{fmt(X.bal(me, t)):>6s} | {s}")
    if not rows:
        print('   （没有）')


# ------------------------------------------------------------------ gaps（指令断档）
def gap_rows(X, min_gap=300, min_issued=5):
    """指令断档：某个号相邻两次「有指令进录像」的拍相隔 >= min_gap，而这段时间里它的日志 cmds 计数（策略自己数的已发指令数）
    涨了 >= min_issued。即策略在发令、服务器没收到（或收到时已过期成批执行）。离开的号把「最后一条指令→离开拍」也算一段。"""
    S = X.S
    out = []
    for p in X.squad:
        b = X.M.bots.get(p)
        if not b:
            continue
        lv = X.leave.get(p, {}).get('t')
        end = lv if lv is not None else X.end_of(p)
        ticks = sorted({c['t'] for c in S['squadCmds'] if c['p'] == p and c['k'] in ('atk', 'boat', 'boatAdd', 'retreat')} |
                       {x['t'] for x in S['donations'] if x['from'] == p and x['ok']})
        ticks = [t for t in ticks if t <= end]
        per_tick = defaultdict(int)
        for c in S['squadCmds']:
            if c['p'] == p and c['k'] in ('atk', 'boat', 'boatAdd', 'retreat'):
                per_tick[c['t']] += 1
        traj = [(s['t'], s['cmds']) for s in b.traj]

        def cnt_at(t):
            v = None
            for tt, n in traj:
                if tt <= t:
                    v = n
            return v
        seq = ticks + ([end] if lv is not None else [])
        for a, c in zip(seq, seq[1:]):
            if c - a < min_gap or a < 400:
                continue
            n0, n1 = cnt_at(a), cnt_at(c)
            issued = (n1 - n0) if n0 is not None and n1 is not None else None
            if issued is None or issued < min_issued:
                continue
            out.append(dict(p=p, t0=a, t1=c, gap=c - a, issued=issued, batch=per_tick.get(c, 0), leftAtEnd=(lv is not None and c == end)))
    return out


def sec_gaps(X):
    rows = gap_rows(X)
    print('指令断档（相邻两次有指令进录像的拍相隔 ≥300，且这段时间日志 cmds 计数涨了 ≥5）。「断档后一拍执行」= 断档结束那一拍同时生效的指令条数')
    if not rows:
        print('   （没有）')
    for r in sorted(rows, key=lambda r: (r['p'], r['t0'])):
        tail = '→ 离开' if r['leftAtEnd'] else f"→ t={r['t1']} 一拍执行 {r['batch']} 条"
        print(f"   {X.M.bots[r['p']].name:14s} t={r['t0']:5d}~{r['t1']:5d} 断 {r['gap']:4d} 拍，期间策略发令 {r['issued']:3d} 条 {tail}")
    if rows:
        bots = sorted({r['p'] for r in rows})
        print(f"合计 {len(rows)} 段，涉及 {len(bots)} 个号；最长 {max(r['gap'] for r in rows)} 拍；断档期间策略共发令 {sum(r['issued'] for r in rows)} 条")
    sec_freeze(X)


def freeze_rows(X):
    """离开的号：日志最后一条快照的本地拍、最后一条进录像的指令、服务器登记离开的拍。"""
    S = X.S
    out = []
    for p in X.squad:
        lv = X.leave.get(p)
        b = X.M.bots.get(p)
        if not lv or not b:
            continue
        last_log = b.traj[-1]['t'] if b.traj else None
        cm = [c['t'] for c in S['squadCmds'] if c['p'] == p and c['k'] in ('atk', 'boat') and c['t'] <= lv['t']]
        out.append(dict(p=p, leaveT=lv['t'], lastLog=last_log, lastCmd=max(cm) if cm else None, terr=lv['terr'], bal=lv['bal']))
    return out


def sec_freeze(X):
    rows = freeze_rows(X)
    if not rows:
        return
    print('离开的号：日志停在哪一拍（本地）→ 服务器登记离开的拍')
    for r in sorted(rows, key=lambda r: r['leaveT']):
        ll = r['lastLog']
        print(f"   {X.M.bots[r['p']].name:14s} 日志末拍 {ll if ll is not None else '-':>5} 最后一条指令 {r['lastCmd'] if r['lastCmd'] is not None else '-':>5} 离开 {r['leaveT']:5d}"
              + (f"（日志停后 {r['leaveT'] - ll} 拍）" if ll is not None else '') + f" 离开时 地 {r['terr']} 兵 {fmt(r['bal'])}")


# ------------------------------------------------------------------ husks（我方空壳与在场号的交换）
def husk_rows(X):
    """我方离开的号（空壳，内置 AI 托管）在离开之后与我方在场号之间的交换。
    返回 [(空壳, 在场号, 空壳耗兵, 空壳从它手里得地, 在场号耗兵, 在场号从空壳手里得地, 在场号被空壳打掉的兵)]。"""
    out = []
    for h in X.squad:
        if h not in X.leave:
            continue
        t0 = X.leave[h]['t']
        t1 = X.end_of(h) + 1
        sp = X.led_sum(h, 'spent', t0, t1, by='other')
        ga = X.led_sum(h, 'gain', t0, t1, by='other')
        for a in X.squad:
            if a == h:
                continue
            a_sp = X.led_sum(a, 'spent', t0, t1, by='other').get(h, 0)
            a_ga = X.led_sum(a, 'gain', t0, t1, by='other').get(h, 0)
            a_dm = X.led_sum(a, 'dmg', t0, t1, by='other').get(h, 0)
            if sp.get(a, 0) or ga.get(a, 0) or a_sp or a_ga:
                out.append(dict(h=h, a=a, hSpent=sp.get(a, 0), hGain=ga.get(a, 0), aSpent=a_sp, aGain=a_ga, aDmg=a_dm,
                                aHusk=(a in X.leave and X.leave[a]['t'] <= t0), same=X.team[h] == X.team[a]))
    return out


def sec_husks(X):
    rows = husk_rows(X)
    print('我方空壳（离开后由内置 AI 托管）与我方其它号之间的交换，从空壳离开那一拍算到它阵亡（账按 100 拍一格）')
    if not rows:
        print('   （没有）')
        return
    for r in sorted(rows, key=lambda r: -(r['hSpent'] + r['aSpent'])):
        print(f"   空壳 {X.name(r['h'])[:12]:12s}(队{X.team[r['h']]}) ↔ {X.name(r['a'])[:14]:14s}(队{X.team[r['a']]}{'·也是空壳' if r['aHusk'] else ''}{'·同队' if r['same'] else '·异队'})"
              f"：空壳耗 {fmt(r['hSpent']):>6s} 兵从它手里拿 {r['hGain']:5d} 格、打掉它 {fmt(r['aDmg']):>6s} 兵 ｜ 它耗 {fmt(r['aSpent']):>6s} 兵从空壳手里拿 {r['aGain']:5d} 格")
    act = [r for r in rows if not r['aHusk']]
    print(f"合计（只算在场号）：空壳对在场号耗兵 {fmt(sum(r['hSpent'] for r in act))}、拿走 {sum(r['hGain'] for r in act)} 格、打掉 {fmt(sum(r['aDmg'] for r in act))} 兵；"
          f"在场号对空壳耗兵 {fmt(sum(r['aSpent'] for r in act))}、拿回 {sum(r['aGain'] for r in act)} 格")
    S = X.S
    n_land = sum(1 for c in S['squadCmds'] if c['k'] == 'atk' and c.get('to') in X.squad and c['p'] in X.squad)
    print(f"录像里我方号对我方号（含空壳）的陆攻指令 {n_land} 条")


# ------------------------------------------------------------------ poolai（名字撞进编队名字池的内置 AI）
def poolai_rows(X):
    """名字在 SQUAD_POOL_SET 里的内置 AI：策略的 isOurSquadBot 只看名字，会把它们当成编队号（不进邻居表、不打）。
    返回 (AI 列表, 我方号与它们接壤的时段列表)。"""
    S = X.S
    pa = S.get('poolAi') or {}
    ais = []
    for k, v in pa.items():
        p = int(k)
        pk = max(v['terr']) if v['terr'] else 0
        last = max([S['ticks'][i] for i, x in enumerate(v['terr']) if x > 0], default=None)
        ais.append(dict(p=p, name=v['name'], peak=pk, peakT=S['ticks'][v['terr'].index(pk)] if pk else None, lastAlive=last))
    ids = {a['p'] for a in ais}
    touch = defaultdict(list)
    for me in X.squad:
        for n in X.neigh[me]:
            if me in X.leave and n['t'] >= X.leave[me]['t']:
                continue
            for o, cnt, terr, bal, _tm, _h in n['nb']:
                if o in ids:
                    touch[(me, o)].append(dict(t=n['t'], cnt=cnt, terr=terr, bal=bal, myTerr=n['terr'], myBal=n['bal']))
    return ais, touch


def sec_poolai(X):
    ais, touch = poolai_rows(X)
    S = X.S
    if not S.get('poolAi') and 'poolAi' not in S:
        print('这份 sim_state.json 没有 poolAi 字段（用新版 eng_replay.cjs 重跑 run_truth.sh）')
        return
    print(f"名字在编队名字池里的内置 AI {len(ais)} 个（策略 isOurSquadBot 只按名字认号 → 它们不进邻居表、不会被陆攻）")
    for a in sorted(ais, key=lambda a: -a['peak']):
        print(f"   bot{a['p']:<4d} {a['name'][:18]:18s} 峰值 {a['peak']:5d} 格 @t={a['peakT']}，最后在场 t={a['lastAlive']}")
    tot = []
    for t in [t for t in PROTO if t <= X.endT]:
        i = X.ix(t)
        tot.append((S['ticks'][i], sum(v['terr'][i] for v in S['poolAi'].values()), S['teamLand'][i][0]))
    print('   各拍合计占地（格）/ 全部内置 AI 占地：' + ' '.join(f"t{t}:{a}/{b}" for t, a, b in tot))
    if not touch:
        print('   我方在场号没有和它们接壤过')
        return
    print('我方在场号与它们接壤的时段（邻居每 90 拍采样一次）：')
    for (me, o), rows in sorted(touch.items(), key=lambda kv: -len(kv[1])):
        a = next(x for x in ais if x['p'] == o)
        sp = X.led_sum(me, 'spent', by='other').get(o, 0)
        ga = X.led_sum(me, 'gain', by='other').get(o, 0)
        r0, r1 = rows[0], rows[-1]
        dens = [r['bal'] / max(1, r['terr']) for r in rows]
        print(f"   {X.name(me)[:14]:14s} ↔ bot{o} {a['name'][:14]:14s} t={r0['t']}~{r1['t']}（{len(rows)} 次采样），接壤 {min(r['cnt'] for r in rows)}~{max(r['cnt'] for r in rows)} 格，"
              f"对方 {min(r['terr'] for r in rows)}~{max(r['terr'] for r in rows)} 格、密度 {min(dens):.1f}~{max(dens):.1f}；我方当时 {min(r['myTerr'] for r in rows)}~{max(r['myTerr'] for r in rows)} 格；整局对它耗兵 {fmt(sp)} 得 {ga} 格")


# ------------------------------------------------------------------ medians（单号领土中位数对比）
def median(v):
    v = sorted(v)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def median_rows(X, ticks=None, prefix=None):
    """各拍：我方在场号 / 其余在场真人（可选：名字带 prefix 的一组单列）的单号领土中位数。在场 = 存活且未离开。"""
    S = X.S
    out = []
    base = ticks or sorted(set([t for t in PROTO if t <= X.endT] + [t for t in (900, X.endT) if t <= X.endT]))
    seen = set()
    for t in base:
        i = X.ix(t)
        tt = S['ticks'][i]
        if tt in seen:
            continue
        seen.add(tt)
        ours, grp, rest = [], [], []
        for p in range(X.H):
            if X.deathT[p] >= 0 and tt >= X.deathT[p]:
                continue
            if p in X.leave and tt >= X.leave[p]['t']:
                continue
            v = S['hum'][p]['terr'][i]
            if p in X.squad:
                ours.append(v)
            elif prefix and prefix.lower() in X.name(p).lower():
                grp.append(v)
            else:
                rest.append(v)
        out.append(dict(t=tt, ours=ours, grp=grp, rest=rest, oursBal=[S['hum'][p]['bal'][i] for p in X.squad if not (X.deathT[p] >= 0 and tt >= X.deathT[p]) and not (p in X.leave and tt >= X.leave[p]['t'])]))
    return out


def sec_medians(X, prefix=None):
    print('单号领土中位数（只算在场 = 存活且未离开的真人号）' + (f"；「{prefix}」= 名字里带 {prefix} 的号" if prefix else ''))
    for r in median_rows(X, prefix=prefix):
        g = f" ｜ {prefix} {len(r['grp'])} 个 中位 {median(r['grp'])}" if prefix else ''
        print(f"   t={r['t']:5d} 我方 {len(r['ours']):2d} 个 中位 {median(r['ours'])} 最小 {min(r['ours']) if r['ours'] else '-'} 最大 {max(r['ours']) if r['ours'] else '-'}{g}"
              f" ｜ 其余真人 {len(r['rest'])} 个 中位 {median(r['rest'])}")
    S = X.S
    ai = [(S['ticks'][i], round(100 * S['teamLand'][i][0] / X.land, 1)) for i in range(len(S['ticks'])) if S['ticks'][i] % 90 == 0 and S['ticks'][i] <= 2700]
    print('   内置 AI 占地%：' + ' '.join(f"t{t}:{v}" for t, v in ai if t % 180 == 0 or t in (630, 1170, 1530)))


# ------------------------------------------------------------------ landings（登陆：谁的船靠上了我方号的岸）
def landing_rows(X):
    """boatLands 里登陆格主人是我方号的全部靠岸事件（发船人可以是任何人）。
    kind：enemy = 异队真人/内置 AI 登陆我方在场号；squadX = 我方在场号登陆异队我方在场号（引擎按进攻结算）；
    huskHit = 我方空壳（AI 托管）登陆我方在场号；onHusk = 登陆我方空壳；gift = 同队移交；self = 靠回自己的岸。"""
    S = X.S
    out = []
    for r in S['boatLands']:
        p, to = r['p'], r['to']
        if to not in X.squad:
            continue
        if to == p or r.get('self'):
            kind = 'self'
        elif r.get('toLeft'):
            kind = 'onHusk'
        elif r.get('friend'):
            kind = 'gift'
        elif p in X.squad:
            lv = X.leave.get(p, {}).get('t')
            kind = 'huskHit' if lv is not None and r['t'] >= lv else 'squadX'
        else:
            kind = 'enemy'
        out.append(dict(t=r['t'], p=p, to=to, troops=r['troops'], toBal=r['toBal'], toTerr=r['toTerr'], kind=kind,
                        ratio=(r['troops'] / r['toBal']) if r['toBal'] else None))
    return out


def sec_landings(X, min_troops=0):
    rows = landing_rows(X)
    en = [r for r in rows if r['kind'] == 'enemy']
    print('外人的船在我方在场号的岸上登陆（引擎：登陆 = 用船上的兵对登陆格主人发起一次进攻）。占比 = 船上兵 / 我方号当时的兵')
    for r in en:
        if r['troops'] < min_troops:
            continue
        print(f"   t={r['t']:5d} {X.name(r['p'])[:22]:22s}(队{X.team[r['p']] if r['p'] < len(X.team) else 0}) → {X.name(r['to'])[:16]:16s}(队{X.team[r['to']]}) 船上 {fmt(r['troops']):>7s}｜对方 地 {r['toTerr']:6d} 兵 {fmt(r['toBal']):>7s}｜占比 {pc(r['troops'], r['toBal'])}")
    big = [r for r in en if r['ratio'] is not None and r['ratio'] >= 0.5 and r['troops'] >= 20000]
    print(f"合计 {len(en)} 次、船上 {fmt(sum(r['troops'] for r in en))} 兵；其中船上兵 >= 我方号当时兵力一半（且 >=2 万）的 {len(big)} 次：" +
          '，'.join(f"{X.name(r['p'])}→{X.name(r['to'])}@{r['t']}" for r in big))
    sx = [r for r in rows if r['kind'] == 'squadX']
    print('我方在场号的船靠上「异队的我方在场号」的岸（保护名单只管陆攻和选目标，船到岸时登陆格换了主人照样结算成进攻）')
    agg = defaultdict(lambda: [0, 0])
    for r in sx:
        a = agg[(r['p'], r['to'])]
        a[0] += 1
        a[1] += r['troops']
    for (p, to), (n, tr) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        ts = ','.join(str(r['t']) for r in sx if r['p'] == p and r['to'] == to)
        print(f"   {X.name(p)[:16]:16s}(队{X.team[p]}) → {X.name(to)[:16]:16s}(队{X.team[to]}) {n} 条、船上共 {fmt(tr)} 兵（t={ts}）")
    print(f"合计 {len(sx)} 条、{fmt(sum(r['troops'] for r in sx))} 兵")
    hh = [r for r in rows if r['kind'] == 'huskHit']
    if hh:
        print('我方空壳（AI 托管）的船登陆我方在场号：' + '，'.join(f"{X.name(r['p'])}→{X.name(r['to'])}@{r['t']} {fmt(r['troops'])}" for r in hh))


# ------------------------------------------------------------------ shadow（影子策略探针的汇总）
def shadow_load(X):
    p = os.path.join(OUT, X.S['matchId'], 'probe.json')
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def shadow_rows(X, win=300):
    """影子策略（strat_probe.mjs --json）与录像的对照。影子的指令不执行，同一个想法每 15 拍（无主地每 5 拍）重复，
    所以只比「这个窗口里有没有这一类指令」：窗口 = win 拍；类 = 对玩家陆攻 / 发船 / 捐款。"""
    D = shadow_load(X)
    if not D:
        return None
    act = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for c in D['actual']:
        if not c['ok']:
            continue
        k = 'atk' if c['k'] == 'atk' and c['to'] != 512 else c['k'] if c['k'] != 'atk' else 'neu'
        act[c['p']][c['t'] // win][k] += 1
    out = {}
    for ps, o in D['shadows'].items():
        p = int(ps)
        sh = defaultdict(lambda: defaultdict(int))
        tgt = defaultdict(lambda: defaultdict(int))
        for c in o['cmds']:
            k = 'atk' if c['k'] == 'atk' and c['to'] != 512 else c['k'] if c['k'] != 'atk' else 'neu'
            sh[c['t'] // win][k] += 1
            if k == 'atk':
                tgt[c['t'] // win][c['to']] += 1
        ws = sorted(set(sh) | set(act[p]))
        out[p] = dict(nfsT=o.get('nfsT', -1), err=o.get('err', 0), wins=[dict(w=w * win, sh=dict(sh[w]), ac=dict(act[p][w]), tgt=dict(tgt[w])) for w in ws])
    return out


def sec_shadow(X, win=300):
    R = shadow_rows(X, win)
    if R is None:
        print('没有 probe.json：先跑 strat_probe.mjs <局> --me squad --json')
        return
    gaps = defaultdict(list)
    for r in gap_rows(X):
        gaps[r['p']].append(r)
    print(f'影子策略 vs 录像（每 {win} 拍一个窗口，只比「有没有这一类指令」：攻=对玩家陆攻，船，捐）')
    tot_ok = tot_n = 0
    lag_ok = lag_n = 0
    for p in sorted(R):
        if p not in X.M.bots:
            continue
        r = R[p]
        ok = n = 0
        in_gap_want = in_gap_got = 0
        for w in r['wins']:
            a, b = w['w'], w['w'] + win
            lag = any(g['t0'] < b and g['t1'] > a for g in gaps[p])
            for k in ('atk', 'boat', 'don'):
                s, c = w['sh'].get(k, 0) > 0, w['ac'].get(k, 0) > 0
                if not s and not c:
                    continue
                n += 1
                ok += 1 if s == c else 0
                if lag:
                    lag_n += 1
                    lag_ok += 1 if s == c else 0
                    if s and not c:
                        in_gap_want += 1
        tot_ok += ok
        tot_n += n
        gs = '；'.join(f"断档 t={g['t0']}~{g['t1']}" for g in gaps[p]) or '无断档'
        print(f"   {X.M.bots[p].name:14s} 窗口×类 一致 {ok}/{n}｜{gs}｜断档窗口里「影子想发、录像没有」{in_gap_want} 个｜isNoFullSend 置真拍 {r['nfsT'] if r['nfsT'] >= 0 else '-'}")
    print(f"合计一致 {tot_ok}/{tot_n}；其中落在断档窗口的 {lag_ok}/{lag_n}，断档之外 {tot_ok - lag_ok}/{tot_n - lag_n}")
    lock = [(X.M.bots[p].name, R[p]['nfsT']) for p in sorted(R) if p in X.M.bots and R[p]['nfsT'] >= 0]
    print(f"影子里 isNoFullSend 被置真的号 {len(lock)} 个：" + '，'.join(f"{n}@{t}" for n, t in lock))


def sec_shadow_gap(X):
    """断档期间影子想打谁：每段断档里，影子想对玩家陆攻/发船的 15 拍格数，和录像里同期实际执行的条数。"""
    D = shadow_load(X)
    if not D:
        print('没有 probe.json')
        return
    print('断档期间：影子（看得到真实局面的同一份策略）想发的指令 vs 录像里实际执行的')
    for g in sorted(gap_rows(X), key=lambda r: (r['p'], r['t0'])):
        p = g['p']
        cm = [c for c in D['shadows'][str(p)]['cmds'] if g['t0'] < c['t'] < g['t1']]
        slots = {(c['t'] // 15, c['k'] if not (c['k'] == 'atk' and c['to'] == 512) else 'neu') for c in cm}
        na = len([1 for s in slots if s[1] == 'atk'])
        nb = len([1 for s in slots if s[1] == 'boat'])
        nd = len([1 for s in slots if s[1] == 'don'])
        nn = len([1 for s in slots if s[1] == 'neu'])
        tg = defaultdict(int)
        for c in cm:
            if c['k'] == 'atk' and c['to'] != 512:
                tg[c['to']] += 1
        top = ' '.join(f"{X.S['allNames'][q] if q < len(X.S.get('allNames', [])) else q}×{n}" for q, n in sorted(tg.items(), key=lambda kv: -kv[1])[:3])
        ac = [c for c in D['actual'] if c['p'] == p and c['ok'] and g['t0'] < c['t'] < g['t1']]
        print(f"   {X.M.bots[p].name:14s} t={g['t0']}~{g['t1']}（{g['gap']} 拍）影子想发的 15 拍格：攻 {na} 无主地 {nn} 船 {nb} 捐 {nd}（{top or '-'}）｜录像里这段执行 {len(ac)} 条")


# ------------------------------------------------------------------ json
# ------------------------------------------------------------------ gates / dups / crowd（HUB 广播 0004 的三处对账）
def in_gap(gaps, p, t):
    return any(r['p'] == p and r['t0'] < t < r['t1'] for r in gaps)


def gate_rows(X):
    """影子探针的逐决策拍流水（probe.json 的 tally）。返回 (early, core)：
    early[p] = Counter(闸)（600<=t<1500，且策略眼里至少有一个内置 AI 邻居的决策拍）；
    core[p]  = Counter(闸)（t>=1500，且 offers 里至少有一个真人邻居的决策拍；闸 = 排第一的真人报价的出口）。"""
    D = shadow_load(X)
    if not D or not D.get('tally'):
        return None
    gaps = gap_rows(X)
    early = defaultdict(lambda: defaultdict(int))
    core = defaultdict(lambda: defaultdict(int))
    coreai = defaultdict(lambda: defaultdict(int))
    extra = defaultdict(lambda: defaultdict(int))
    for r in D['tally']:
        p, t = r['p'], r['t']
        if not X.alive_active(p, t):
            continue
        if 600 <= t < 1500:
            if r.get('ai', 0) > 0:
                g = r.get('gate', '?')
                if g == 'floor:sb':
                    g = 'sb:' + r.get('sbKind', '?') + ('' if r.get('passNoSb') else '(去掉也不够)')
                early[p][g] += 1
                extra[p]['aiTicks'] += 1
                if in_gap(gaps, p, t):
                    extra[p]['aiTicksInGap'] += 1
                if 'A' in r['out']:
                    extra[p]['aiCmd'] += 1
            elif r['neut'] == 0:
                extra[p]['noTarget'] += 1
        elif t >= 1500:
            if r.get('hum', 0) > 0:
                hg = r.get('hg', '?').split(',')
                first = 'send' if 'send' in hg else hg[0]
                if first == 'L5361':
                    first = 'L5361:sb:' + r.get('sbKind', '?') if r.get('h5361') == 'sb' else 'L5361:dpKeep'
                core[p][first] += 1
                extra[p]['humTicks'] += 1
                if r.get('over'):
                    extra[p]['humOver'] += 1
                if r.get('onMe', 0) > 0:
                    extra[p]['humOnMe'] += 1
                    if 'send' not in hg:
                        extra[p]['humOnMeNoSend'] += 1
            if r.get('ai', 0) > 0:
                ag = r.get('ag', '?').split(',')
                first = 'send' if 'send' in ag else ag[0]
                if first == 'L5361':
                    if r.get('sbA', 0) > 0:
                        first = 'L5361:sb:' + r.get('sbKind', '?') + ('' if r.get('sbPassA', 0) > 0 else '(去掉也不够)')
                    else:
                        first = 'L5361:dpKeep'
                coreai[p][first] += 1
    return early, core, extra, coreai


def gate_txt(g):
    if g.startswith('L5361:sb:'):
        return f"保底线=safeFinite〔{g[9:]}的兵〕>=余额(L5361)"
    if g == 'L5361:dpKeep':
        return '保底线=dpKeep>=余额(L5361)'
    return GATE_TXT.get(g, g)


GATE_TXT = {
    'L5267': 'c>=worth 且没超软上限(L5267)', 'L5271': '唯一真人缓冲(L5271)', 'L5275': '目标太小(L5275)', 'L5280': 'crowdedHard(L5280)',
    'L5284': 'absorb(L5284)', 'L5288': 'doorSea(L5288)', 'L5345': 'siegeShrink(L5345)', 'L5361': 'avail<=0：保底线>=余额(L5361)',
    'L5490': '在途兵已够(L5490)', 'L5497': 'pulse 太小(L5497)', 'L5504': '在途兵已够(L5504)', 'L5506': 'pulse 太小(L5506)',
    'L5511': '在途兵>=4%(L5511)', 'L5520': 'pulse 太小(L5520)', 'L5528': '买不起整笔且不足 chunk(L5528)', 'send': '出兵', 'later': '排在前面的报价已 break',
    'L5364': '已在打它(L5364)', 'L5367a': '单太小：want < minCmd=4.7% 余额(L5367)', 'L5367b': '买不起整笔且不足 chunk(L5367)',
}


def sec_gates(X):
    R = gate_rows(X)
    if R is None:
        print('没有 probe.json 的 tally（先跑 strat_probe.mjs <id> --me squad --json --tally）')
        return
    early, core, extra, coreai = R
    print('影子策略逐决策拍（每 5 拍）卡在哪道闸。影子 = 策略源码跑在录像重演的真实局面上，指令只记不执行。')
    print('一、t=600~1499，策略眼里至少有一个内置 AI 邻居的决策拍（General.act → Style.pickTarget；打内置 AI 的底线 = max(winR 项, dpKeep, safeFinite)）')
    print('   闸：ok=有内置 AI 可出兵；botOk=AI 的地价 > winR×t×自己密度；winR/dpKeep=底线取到该项；sb:X=底线取到 safeFinite，'
          '而它取的是「某个内置 AI 邻居的另一个邻居 X 的兵」')
    tot = defaultdict(int)
    for p in X.squad:
        if p not in early:
            continue
        c = early[p]
        n = sum(c.values())
        sb_sq = sum(v for g, v in c.items() if g.startswith('sb:我方') and '不够' not in g)
        e = extra[p]
        parts = '，'.join(f"{g.replace('floor:', '')} {v}" for g, v in sorted(c.items(), key=lambda kv: -kv[1]))
        print(f"   {X.M.bots[p].name:14s} 决策拍 {n:3d}（其中断档段内 {e.get('aiTicksInGap', 0):3d}）；影子对内置 AI 发令 {e.get('aiCmd', 0):3d} 拍；"
              f"被「我方号的兵」当底线卡住且去掉就能出兵 {sb_sq:3d} 拍（{pc(sb_sq, n)}）｜{parts}")
        for g, v in c.items():
            tot[g] += v
    n = sum(tot.values())
    if n:
        sq = sum(v for g, v in tot.items() if g.startswith('sb:我方号') and '不够' not in g)
        sq_same = sum(v for g, v in tot.items() if g.startswith('sb:我方号·同队') and '不够' not in g)
        husk = sum(v for g, v in tot.items() if g.startswith('sb:我方空壳') and '不够' not in g)
        oth = sum(v for g, v in tot.items() if g.startswith('sb:') and not g.startswith('sb:我方'))
        print(f"   合计 {n} 个决策拍：可出兵 {tot.get('ok', 0)}（{pc(tot.get('ok', 0), n)}）；地价闸 botOk {tot.get('botOk', 0)}；"
              f"底线=winR 项 {tot.get('floor:winR', 0)}，=dpKeep {tot.get('floor:dpKeep', 0)}；"
              f"底线=safeFinite 且取的是我方在场号的兵、去掉就能出兵 {sq}（{pc(sq, n)}；其中同队 {sq_same}），取的是我方空壳 {husk}，取的是别人（敌方真人/外人队友/内置 AI）{oth}")
    print('二、t>=1500，offers 里至少有一个真人邻居的决策拍（Policy.buyLand；闸 = 这一拍有没有对真人出兵，没有则取排第一的真人报价的出口）')
    tot = defaultdict(int)
    te = defaultdict(int)
    for p in X.squad:
        if p not in core:
            continue
        c = core[p]
        n = sum(c.values())
        e = extra[p]
        parts = '，'.join(f"{gate_txt(g)} {v}" for g, v in sorted(c.items(), key=lambda kv: -kv[1]))
        print(f"   {X.M.bots[p].name:14s} 决策拍 {n:4d}（超软上限 {e.get('humOver', 0):4d}；正被真人打 {e.get('humOnMe', 0):4d}，其中没有对真人出兵 {e.get('humOnMeNoSend', 0):4d}）｜{parts}")
        for g, v in c.items():
            tot[g] += v
        for kk, v in e.items():
            te[kk] += v
    n = sum(tot.values())
    if n:
        parts = '，'.join(f"{gate_txt(g)} {v}（{pc(v, n)}）" for g, v in sorted(tot.items(), key=lambda kv: -kv[1]))
        print(f"   合计 {n} 个决策拍：{parts}")
        print(f"   正被真人打的决策拍 {te.get('humOnMe', 0)}，其中这一拍没有对任何真人出兵 {te.get('humOnMeNoSend', 0)}（{pc(te.get('humOnMeNoSend', 0), te.get('humOnMe', 0))}）")
    print('三、t>=1500，offers 里至少有一个非真人报价（内置 AI / 空壳）的决策拍（闸 = 这一拍有没有对非真人出兵，没有则取排第一的非真人报价的出口）')
    tot = defaultdict(int)
    for p in X.squad:
        if p not in coreai:
            continue
        c = coreai[p]
        n = sum(c.values())
        parts = '，'.join(f"{gate_txt(g)} {v}" for g, v in sorted(c.items(), key=lambda kv: -kv[1]))
        print(f"   {X.M.bots[p].name:14s} 决策拍 {n:4d}｜{parts}")
        for g, v in c.items():
            tot[g] += v
    n = sum(tot.values())
    if n:
        parts = '，'.join(f"{gate_txt(g)} {v}（{pc(v, n)}）" for g, v in sorted(tot.items(), key=lambda kv: -kv[1]))
        print(f"   合计 {n} 个决策拍：{parts}")
        sq = sum(v for g, v in tot.items() if g.startswith('L5361:sb:我方号') and '不够' not in g)
        print(f"   其中保底线取的是我方在场号的兵、去掉就能出兵：{sq}（{pc(sq, n)}）")


def dup_rows(X, gap=21):
    """重复下单：同一个号、同一目标（对玩家的陆攻，目标非无主地）相邻两条生效指令相隔 <= gap 拍。
    gap=21 = 3 个服务器回合；第一条下去后要等它进录像、局面刷新，策略才看得到自己的在途兵。"""
    S = X.S
    out = []
    last = {}
    for c in S['squadCmds']:
        if c['k'] != 'atk' or not c['ok'] or c['p'] not in X.squad:
            continue
        key = (c['p'], c['raw'])
        if c['raw'] != 512 and key in last and 0 < c['t'] - last[key]['t'] <= gap:
            a = last[key]
            out.append(dict(p=c['p'], to=c['to'], raw=c['raw'], t0=a['t'], t1=c['t'], pct0=a['pct'], pct1=c['pct'], sent0=a['sent'], sent1=c['sent'],
                            fee1=c['fee'], B0=a['B0'], toTerr=a['toTerr'], toBal=a['toBal']))
        last[key] = c
    return out


def sec_dups(X, gap=21):
    rows = dup_rows(X, gap)
    D = shadow_load(X)
    S = X.S
    n_atk = sum(1 for c in S['squadCmds'] if c['k'] == 'atk' and c['ok'] and c['p'] in X.squad and c['raw'] != 512)
    print(f"重复下单：同一个号对同一玩家目标的陆攻，相隔 <= {gap} 拍又下一条（两条都生效）。我方对玩家的陆攻共 {n_atk} 条")
    if not rows:
        print('   （没有）')
        return
    sent2 = sum(r['sent1'] for r in rows)
    fee2 = sum(r['fee1'] for r in rows)
    print(f"   合计 {len(rows)} 组（占对玩家陆攻 {pc(len(rows), n_atk)}）；第二条共出兵 {fmt(sent2)}、手续费 {fmt(fee2)}")
    by_p = defaultdict(int)
    for r in rows:
        by_p[r['p']] += 1
    print('   按号：' + '，'.join(f"{X.M.bots[p].name} {v}" for p, v in sorted(by_p.items(), key=lambda kv: -kv[1])))
    big = sorted(rows, key=lambda r: -(r['sent0'] + r['sent1']))[:10]
    print('   出兵最多的 10 组（影子 = 同一时段影子策略对同一目标想发的条数；影子每 15 拍可重发，>1 不代表重复）：')
    for r in big:
        sh = '-'
        if D:
            cm = D['shadows'].get(str(r['p']), {}).get('cmds', [])
            sh = sum(1 for c in cm if c['k'] == 'atk' and c['to'] == r['raw'] and r['t0'] - 25 <= c['t'] <= r['t1'])
        need = 2 * r['toTerr'] + 2 * r['toBal']
        print(f"   t={r['t0']}/{r['t1']}（隔 {r['t1'] - r['t0']} 拍）{X.M.bots[r['p']].name:14s} → {eng_name(X, r['to']) if r['to'] != 512 else '（目标已阵亡，记成无主地）'}"
              f" {r['pct0']}‰ {fmt(r['sent0'])} + {r['pct1']}‰ {fmt(r['sent1'])}；拍前兵 {fmt(r['B0'])}；目标当时 地 {r['toTerr']} 兵 {fmt(r['toBal'])}"
              f"（吃光约需 {fmt(need)}）；影子同段 {sh} 条")


def crowd_rows(X):
    """同拍两条指令：影子在一个决策拍里既发无主地单又发对玩家的陆攻/船。录像里该号在随后 25 拍内实际执行了哪几类。"""
    D = shadow_load(X)
    if not D:
        return None
    S = X.S
    acts = defaultdict(list)
    for c in S['squadCmds']:
        if c['ok'] and c['k'] in ('atk', 'boat') and c['p'] in X.squad:
            acts[c['p']].append(c)
    out = []
    for me, o in D['shadows'].items():
        p = int(me)
        by = defaultdict(list)
        for c in o['cmds']:
            by[c['t']].append(c)
        for t, v in sorted(by.items()):
            if len(v) < 2:
                continue
            neu = [c for c in v if c['k'] == 'atk' and c['to'] == 512]
            oth = [c for c in v if not (c['k'] == 'atk' and c['to'] == 512)]
            if not neu or not oth:
                continue
            got = [c for c in acts.get(p, []) if t <= c['t'] <= t + 25]
            got_neu = any(c['k'] == 'atk' and c['raw'] == 512 for c in got)
            got_oth = any(not (c['k'] == 'atk' and c['raw'] == 512) for c in got)
            out.append(dict(p=p, t=t, neuPct=neu[0]['pct'], neuAmt=neu[0]['amt'], othK=oth[0]['k'], othTo=oth[0]['to'], othPct=oth[0]['pct'], othAmt=oth[0]['amt'],
                            gotNeu=got_neu, gotOth=got_oth))
    return out


def sec_crowd(X):
    rows = crowd_rows(X)
    if rows is None:
        print('没有 probe.json（先跑 strat_probe.mjs <id> --me squad --json）')
        return
    D = shadow_load(X)
    n_dec = sum(len({c['t'] for c in o['cmds']}) for o in D['shadows'].values())
    print(f"同拍两条指令（影子在一个决策拍里既发无主地单又发对玩家的指令）：{len(rows)} 拍 / 影子有指令的决策拍 {n_dec}")
    if not rows:
        return
    both = sum(1 for r in rows if r['gotNeu'] and r['gotOth'])
    only_neu = sum(1 for r in rows if r['gotNeu'] and not r['gotOth'])
    only_oth = sum(1 for r in rows if r['gotOth'] and not r['gotNeu'])
    none = sum(1 for r in rows if not r['gotOth'] and not r['gotNeu'])
    early = sum(1 for r in rows if r['t'] < 1500)
    print(f"   其中 t<1500 {early} 拍；录像随后 25 拍内：两类都执行 {both}，只执行无主地单 {only_neu}，只执行对玩家的 {only_oth}，都没执行 {none}")
    for r in rows[:12]:
        tgt = eng_name(X, r['othTo']) if r['othTo'] not in (512, -1) else '?'
        print(f"   t={r['t']} {X.M.bots[r['p']].name:14s} 无主地 {r['neuPct']}‰ {fmt(r['neuAmt'])} + {'船' if r['othK'] == 'boat' else '攻'}→{tgt} {r['othPct']}‰ {fmt(r['othAmt'])}"
              f" ｜录像：无主地单{'执行' if r['gotNeu'] else '没有'}，对玩家的{'执行' if r['gotOth'] else '没有'}")



def build_json(X):
    S = X.S
    doc = dict(matchId=S['matchId'], replaySource=S['replayPath'].split('/')[-2], replayEnd=X.endT,
               check=dict(points=S['check']['points'], exact=S['check']['exact'], firstBad=S['check']['firstBad']),
               noEffectCmds=S['rejectedCmds'], teams=team_rows(X), bots={})
    for p in X.squad:
        dt = X.deathT[p]
        hb = S['hum'][p]
        peak = max(hb['terr'])
        rec = dict(me=p, name=X.M.bots[p].name if p in X.M.bots else None, team=X.team[p], leaveT=X.leave[p]['t'] if p in X.leave else None,
                   deathT=dt if dt >= 0 else None, peakTerr=peak, peakT=S['ticks'][hb['terr'].index(peak)], ledger=ledger_totals(X, p))
        if dt >= 0:
            tot, tk = takers(X, p, dt - 900, dt + 1)
            rec['landTakenLast900'] = [dict(by=o, name=X.name(o), cls=X.cls(p, o, dt), cells=v) for o, v in tk]
        doc['bots'][p] = rec
    return doc


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mid, sec = sys.argv[1], sys.argv[2]
    a = sys.argv[3:]
    X = Sim(mid)
    if sec == 'check':
        sec_check(X)
    elif sec == 'teams':
        sec_teams(X)
    elif sec == 'bursts':
        sec_bursts(X, int(sys.argv[3]) if len(sys.argv) > 3 else 3, float(sys.argv[4]) if len(sys.argv) > 4 else 0.4)
    elif sec == 'collapse':
        sec_collapse(X)
    elif sec == 'lumps':
        sec_lumps(X)
    elif sec == 'dens':
        sec_dens(X, int(sys.argv[3]) if len(sys.argv) > 3 else None)
    elif sec == 'roster':
        sec_roster(X)
    elif sec == 'ledger':
        sec_ledger(X, int(a[0]) if a else None, int(a[1]) if len(a) > 1 else 500)
    elif sec == 'deaths':
        sec_deaths(X, int(a[0]) if a else None)
    elif sec == 'don':
        sec_don(X)
    elif sec == 'cmds':
        sec_cmds(X)
    elif sec == 'probe':
        sec_probe(X)
    elif sec == 'gifts':
        sec_gifts(X)
    elif sec == 'boats':
        sec_boats(X, int(a[0]) if a else None)
    elif sec == 'fees':
        sec_fees(X)
    elif sec == 'nfs':
        sec_nfs(X)
    elif sec == 'neigh':
        sec_neigh(X, int(a[0]), int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 10 ** 9)
    elif sec == 'front':
        sec_front(X, int(a[0]) if a else 900)
    elif sec == 'boxed':
        sec_boxed(X)
    elif sec == 'gaps':
        sec_gaps(X)
    elif sec == 'husks':
        sec_husks(X)
    elif sec == 'poolai':
        sec_poolai(X)
    elif sec == 'protbox':
        sec_protbox(X)
    elif sec == 'medians':
        sec_medians(X, a[0] if a else None)
    elif sec == 'pair':
        sec_pair(X, int(a[0]), int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 10 ** 9)
    elif sec == 'cmdlist':
        sec_cmdlist(X, int(a[0]), int(a[1]) if len(a) > 1 else 0, int(a[2]) if len(a) > 2 else 10 ** 9)
    elif sec == 'shadow':
        sec_shadow(X, int(a[0]) if a else 300)
        sec_shadow_gap(X)
    elif sec == 'landings':
        sec_landings(X, int(a[0]) if a else 0)
    elif sec == 'gates':
        sec_gates(X)
    elif sec == 'dups':
        sec_dups(X, int(a[0]) if a else 21)
    elif sec == 'crowd':
        sec_crowd(X)
    elif sec == 'json':
        doc = build_json(X)
        p = os.path.join(OUT, mid, 'simdigest.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
