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
  gates [t0 t1]      影子策略每个决策拍卡在哪道闸（可只看 t0~t1）（strat_probe.mjs --json --tally）：t<1500 打内置 AI 的底线
                     （winR 项 / dpKeep / safeFinite，safeFinite 取到的是谁的兵）；t>=1500 对真人邻居的出口行号
  exchange [t…]      对我方在场号出兵最多的 3 个敌方真人：逐窗口「它→我方」的陆攻/登陆与「我方→它」的陆攻/发船（条数、出兵、千分比），它两端的地/兵
  gapgrow [a b] [t…] 指令断档的号 vs 没断档的号：t=a~b（缺省 1000~2000）有断档段的为一组，各拍的领土合计、单号中位、兵力；其余真人同期
  boxedout [t0 t1]   策略眼里 nb=0 且 neut=0 的决策拍里影子发出了什么（捐款/发船/不发），密度落在 55 与 133.3 两条线的哪边；同段录像里真实的捐款和发船
  dups [gap]         重复下单：同一个号对同一目标的陆攻在 gap 拍（缺省 21）内又下一条；影子在同一段里想发几条
  crowd              同拍两条指令：影子在一拍里既发无主地小单又发对玩家陆攻，录像里随后执行的是哪条
  bursts [min] [frac] 同拍连发清仓：同一个号同一拍进录像 >=min 条（缺省 3）且一拍内出兵+费 >= frac×拍前兵（缺省 0.4，拍前兵 >=2 万）
  collapse           清地规则核对（领土 <= 衰减峰值/4 → 剩下的地全变无主地、余额清零；有船在海上的不出局）：
                     每个号清地拍、清地前一拍领土、当时的衰减峰值、冲高前的领土、正式阵亡拍、清地后又上岸的最大领土
  lumps              空壳整笔转交（引擎规则：离开的真人由内置 AI 托管，没有可打的目标时把全部余额捐给一个队友，手续费 6.25%，
                     不是指令、不进录像）：我方号收到的、我方空壳转出的
  top [t] [n]        某一拍领土最大的 n 个真人号（队、地、兵、密度）和我方在场号的名次
  halves [t…]        我方号按所在的队分组的逐窗口账：收入、顶格少拿、出兵、捐款到账/手续费、打出去/挨打（按对方类别），两端的地/兵（含同队外人）
  contact [T<队>] [t…] 接敌表：某一拍每个在场的我方号挨着哪些敌方真人、两边兵力、是否落在 dpKeep 冻结线上、被保护名单挡住的接壤格数
  sieges [最小兵]    敌方真人对我方号的逐个围攻（陆攻 + 登陆），目标自己与别的我方号同期对它的还手、目标同期的捐款进出
  pokes              HL-ASSIST 的 10% 协防戳：替谁打的（同队/异队/空壳）、打了谁、录像里的执行、戳前戳后对方对出手号的陆攻
  boatwar            船打船（引擎 acV：每 2 拍，7.5 格内不同队的船互相打）：我方号的船被谁的船打掉多少兵、打掉了谁的；
                     其中两头都是我方号（异队的我方号在海上互打）单列
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
                bl = pt['bal'].get(str(p)) or []
                rows.append(dict(p=p, name=X.name(p), t=t0 + i, terrBefore=te[i - 1], peak=peak, line=peak // 4, maxTerr=mx, maxT=mxT, pre300=pre,
                                 deathT=dt.get(p, -1), afterMax=after, ok=te[i - 1] > peak // 4,
                                 balBefore=(bl[i - 1] if i - 1 < len(bl) else -1)))
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
    print('清地前一拍的余额（清地时作废）：' + '；'.join(f"{r['name']} {fmt(r['balBefore'])}" for r in sorted(rows, key=lambda r: r['t']) if r['balBefore'] >= 0)
          + f"；合计 {fmt(sum(r['balBefore'] for r in rows if r['balBefore'] >= 0))}")
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


# ------------------------------------------------------------------ halves（我方号按所在的队分组，逐窗口的兵力去向 + 同窗口其余真人的地/兵）
def halves_rows(X, edges=None):
    """edges = 窗口边界拍（默认 1500/3000/4000/5000/6000/7000/8000/终局）。每个窗口、每个队里的我方号合计：
    收入、顶格少拿、出兵、手续费、捐款（到账/费/收到）、战斗耗兵与得地（按对方类别）、失地与被打掉兵（按对方类别）；
    以及窗口两端：我方在场号的地/兵、该队其余真人（外人，含空壳）的地/兵。
    账按 ledgerWindow（100 拍）一格记：边界先向下取到 100 的整数倍，每格只算进一个窗口（不重复计）。"""
    S = X.S
    lw = S['ledgerWindow']
    if not edges:
        edges = [e for e in (1500, 3000, 4000, 5000, 6000, 7000, 8000) if e < X.endT] + [X.endT]
    edges = [e - e % lw for e in edges[:-1]] + [edges[-1] if edges[-1] >= X.endT else edges[-1] - edges[-1] % lw]

    def bsum(p, k, a, b, by=None, husk=None):
        # husk=None 全算；True 只算该号离开之后（空壳）的格；False 只算在场时的格
        tot = 0
        out = defaultdict(int)
        for w, d in X.led[p][k].items():
            if not (a <= w < b):
                continue
            if husk is not None and (p in X.leave and w >= X.leave[p]['t']) != husk:
                continue
            for other, v in d.items():
                tot += v
                if by:
                    out[X.cls(p, other, w)] += v
        return out if by else tot
    teams = sorted({X.team[p] for p in X.squad})
    rows = []

    def side(tm, t):
        i = X.ix(t)
        ours = [p for p in X.squad if X.team[p] == tm and X.alive_active(p, S['ticks'][i]) and S['hum'][p]['terr'][i] > 0]
        oth = [p for p in range(X.H) if X.team[p] == tm and p not in ours and S['hum'][p]['terr'][i] > 0]
        return dict(n=len(ours), land=sum(S['hum'][p]['terr'][i] for p in ours), bal=sum(S['hum'][p]['bal'][i] for p in ours),
                    othN=len(oth), othLand=sum(S['hum'][p]['terr'][i] for p in oth), othBal=sum(S['hum'][p]['bal'][i] for p in oth))

    for a, b in zip(edges[:-1], edges[1:]):
        for tm in teams:
            mem = [p for p in X.squad if X.team[p] == tm]
            T = {k: sum(bsum(p, k, a, b) for p in mem) for k in KINDS}
            by = {}
            for k in ('spent', 'gain', 'lost', 'dmg'):
                d = defaultdict(int)
                for p in mem:
                    for c, v in bsum(p, k, a, b, by='cls').items():
                        d[c] += v
                by[k] = dict(d)
            hT = {k: sum(bsum(p, k, a, b, husk=True) for p in mem) for k in KINDS}
            hby = {}
            for k in ('spent', 'gain', 'lost', 'dmg'):
                d = defaultdict(int)
                for p in mem:
                    for c, v in bsum(p, k, a, b, by='cls', husk=True).items():
                        d[c] += v
                hby[k] = dict(d)
            rows.append(dict(t0=a, t1=b, team=tm, start=side(tm, a), end=side(tm, b), tot=T, by=by, husk=dict(tot=hT, by=hby)))
    return rows


def sec_halves(X, edges=None):
    print('我方号按所在的队分组的逐窗口账（单位：兵；地 = 格）。外人 = 该队里不是我方在场号的真人（含空壳）。账按 100 拍一格记，窗口边界取 100 的整数倍、每格只算一次')
    for r in halves_rows(X, edges):
        s0, s1, T, by = r['start'], r['end'], r['tot'], r['by']
        print(f"t={r['t0']}~{r['t1']} 队{r['team']}：我方 {s0['n']}→{s1['n']} 个号，地 {s0['land']}→{s1['land']}（{pc(s0['land'], X.land)}→{pc(s1['land'], X.land)}），兵 {fmt(s0['bal'])}→{fmt(s1['bal'])}"
              f"｜同队外人 {s0['othN']}→{s1['othN']} 个，地 {s0['othLand']}→{s1['othLand']}（{pc(s0['othLand'], X.land)}→{pc(s1['othLand'], X.land)}），兵 {fmt(s0['othBal'])}→{fmt(s1['othBal'])}")
        print(f"     收入 {fmt(T['inc'])}，顶格少拿 {fmt(T['capLoss'])}，空壳少拿 {fmt(T['huskLoss'])}｜陆攻出兵 {fmt(T['atkOut'])}，发船 {fmt(T['boatOut'])}，出兵手续费 {fmt(T['fee'])}"
              f"｜捐出到账 {fmt(T['donOut'])}，捐款手续费 {fmt(T['donFee'])}（占收入 {pc(T['donFee'], T['inc'])}），收到 {fmt(T['donIn'])}")
        sp, ga, lo, dm = by['spent'], by['gain'], by['lost'], by['dmg']
        print('     打出去：' + ('；'.join(f"{c} 耗 {fmt(sp[c])} 得 {ga.get(c, 0)} 格" for c in sorted(sp, key=lambda c: -sp[c])) or '无'))
        print('     挨打：' + ('；'.join(f"{c} 失 {lo.get(c, 0)} 格、掉 {fmt(dm.get(c, 0))} 兵" for c in sorted(set(lo) | set(dm), key=lambda c: -lo.get(c, 0))) or '无'))
        hT, hb = r['husk']['tot'], r['husk']['by']
        if any(hT.values()):
            print(f"     以上含空壳（已离开的我方号）的账：收入 {fmt(hT['inc'])}，空壳少拿 {fmt(hT['huskLoss'])}，收到捐款 {fmt(hT['donIn'])}，陆攻出兵 {fmt(hT['atkOut'])}｜打出去："
                  + ('；'.join(f"{c} 耗 {fmt(v)} 得 {hb['gain'].get(c, 0)} 格" for c, v in sorted(hb['spent'].items(), key=lambda kv: -kv[1])) or '无')
                  + '｜挨打：' + ('；'.join(f"{c} 失 {hb['lost'].get(c, 0)} 格、掉 {fmt(hb['dmg'].get(c, 0))} 兵" for c in sorted(set(hb['lost']) | set(hb['dmg']), key=lambda c: -hb['lost'].get(c, 0))) or '无'))
    R = halves_rows(X, edges)
    for tm in sorted({r['team'] for r in R}):
        rr = [r for r in R if r['team'] == tm]
        T = {k: sum(r['tot'][k] for r in rr) for k in rr[0]['tot']}
        hum = sum(r['by']['spent'].get('敌方真人', 0) for r in rr)
        humg = sum(r['by']['gain'].get('敌方真人', 0) for r in rr)
        lost = sum(r['by']['lost'].get('敌方真人', 0) for r in rr)
        dmg = sum(r['by']['dmg'].get('敌方真人', 0) for r in rr)
        hh = {k: sum(r['husk']['by'][k].get('敌方真人', 0) for r in rr) for k in ('spent', 'gain', 'lost', 'dmg')}
        hinc = sum(r['husk']['tot']['inc'] for r in rr)
        hin = sum(r['husk']['tot']['donIn'] for r in rr)
        print(f"t={rr[0]['t0']}~{rr[-1]['t1']} 队{tm} 合计：收入 {fmt(T['inc'])}，顶格少拿 {fmt(T['capLoss'])}，空壳少拿 {fmt(T['huskLoss'])}｜陆攻出兵 {fmt(T['atkOut'])}，发船 {fmt(T['boatOut'])}，出兵手续费 {fmt(T['fee'])}"
              f"｜捐出到账 {fmt(T['donOut'])}，捐款手续费 {fmt(T['donFee'])}（占收入 {pc(T['donFee'], T['inc'])}）｜对敌方真人耗兵 {fmt(hum)} 得 {humg} 格；被敌方真人拿走 {lost} 格、打掉 {fmt(dmg)} 兵"
              + (f"｜其中空壳的账：收入 {fmt(hinc)}、收到捐款 {fmt(hin)}、对敌方真人耗兵 {fmt(hh['spent'])} 得 {hh['gain']} 格、被敌方真人拿走 {hh['lost']} 格、打掉 {fmt(hh['dmg'])} 兵"
                 f" → 只算在场号：收入 {fmt(T['inc'] - hinc)}（捐款手续费占 {pc(T['donFee'], T['inc'] - hinc)}），对敌方真人耗兵 {fmt(hum - hh['spent'])} 得 {humg - hh['gain']} 格，被敌方真人拿走 {lost - hh['lost']} 格、打掉 {fmt(dmg - hh['dmg'])} 兵"
                 if (hinc or hin or any(hh.values())) else ''))


# ------------------------------------------------------------------ contact（某一拍：每个在场的我方号挨着哪些敌方真人、两边兵力、是否落在 dpKeep 的冻结线上）
def contact_rows(X, t, team=None):
    """取 <= t 的最近一次邻居采样。每个在场的我方号：地、兵、密度、策略眼里可打的真人邻居（敌方真人，含空壳）及其兵、
    挨着的「打不了的」邻居（同队 / 异队我方号）的接壤格数；frozen = 最强的敌方真人邻居的兵 >= 1.78×自己的兵 + 1.5×自己的地
    （dpKeep = max(0,(m-1.5L)/1.78) >= 余额，c110 L2491-2496；这里 m 只取对方余额，不含它已经压在我身上的在途兵，所以是下限）。"""
    rows = []
    for me in X.squad:
        if team is not None and X.team[me] != team:
            continue
        if not X.alive_active(me, t):
            continue
        ns = [n for n in X.neigh[me] if n['t'] <= t]
        if not ns:
            continue
        n = ns[-1]
        if n['terr'] <= 0:
            continue
        foes, prot, mates = [], 0, 0
        for q, cnt, terr, bal, tm, kind in n['nb']:
            c = X.cls(me, q, n['t'])
            if c.startswith('敌方'):
                foes.append(dict(q=q, name=X.name(q), border=cnt, terr=terr, bal=bal, husk='空壳' in c))
            elif '异队' in c:
                prot += cnt
            elif c.startswith('我方号·同队') or c == '队友':
                mates += cnt
        strongest = max((f['bal'] for f in foes), default=0)
        rows.append(dict(me=me, name=X.M.bots[me].name, team=X.team[me], t=n['t'], terr=n['terr'], bal=n['bal'], dens=n['bal'] / n['terr'],
                         foes=foes, protBorder=prot, mateBorder=mates, neut=n['neut'], boats=n['boats'],
                         on=sum(v for a, v, tm in n['on']), frozen=bool(foes) and strongest >= 1.78 * n['bal'] + 1.5 * n['terr'],
                         strongest=strongest))
    return rows


def sec_contact(X, ticks, team=None):
    print('接敌表：每个在场的我方号挨着哪些敌方真人（策略眼里可打的）。冻结线 = 最强的敌方真人邻居的兵 >= 1.78×自己的兵 + 1.5×自己的地（dpKeep >= 余额）')
    for t in ticks:
        R = contact_rows(X, t, team)
        if not R:
            continue
        tot_bal = sum(r['bal'] for r in R)
        front = [r for r in R if r['foes']]
        foe_ids = {}
        for r in front:
            for f in r['foes']:
                foe_ids[f['q']] = f
        print(f"t={R[0]['t']}{'（队' + str(team) + '）' if team is not None else ''}：我方在场 {len(R)} 个号、兵 {fmt(tot_bal)}；挨着敌方真人的 {len(front)} 个号、兵 {fmt(sum(r['bal'] for r in front))}"
              f"（其中落在冻结线上的 {sum(1 for r in front if r['frozen'])} 个）；被挨着的敌方真人 {len(foe_ids)} 个、兵 {fmt(sum(f['bal'] for f in foe_ids.values()))}")
        for r in sorted(R, key=lambda r: -r['terr']):
            fs = '；'.join(f"{f['name']}{'(空壳)' if f['husk'] else ''} 接{f['border']} 地{f['terr']} 兵{fmt(f['bal'])}（{f['bal'] / max(1, r['bal']):.2f}×）" for f in sorted(r['foes'], key=lambda f: -f['bal']))
            print(f"   {r['name']:14s} 队{r['team']} 地{r['terr']:6d} 兵{fmt(r['bal']):>6s} 密{r['dens']:5.1f} 正被打 {fmt(r['on']):>6s}｜打不了的接壤：异队我方号 {r['protBorder']} 格、同队 {r['mateBorder']} 格、无主 {r['neut']}"
                  f"｜{'敌方真人邻居：' + fs if fs else '没有敌方真人邻居'}{'  ← 冻结线上' if r['frozen'] else ''}")


# ------------------------------------------------------------------ sieges（敌方真人对我方号的逐个围攻：陆攻 + 登陆的兵、时间、目标当时的兵；目标与别的我方号同期对它的还手）
def siege_rows(X, min_troops=200000, gap=900):
    """按（敌方真人, 我方目标）汇总录像里的陆攻指令（含翻山，mtn=1）与登陆：条数、兵、首末拍；目标在首条那一拍的地/兵；
    同一对之间相邻两条隔了 gap 拍以上就拆成两组。
    同一时段 [首条-300, 末条+100] 里目标自己对这个敌人的出兵、别的我方号对这个敌人的出兵（含 10% 协防戳）、
    目标同期收到的捐款（到账）与捐出的（到账+手续费）。只列敌人出兵合计 >= min_troops 的组。"""
    S = X.S
    ev = defaultdict(list)
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c.get('ok') and c.get('to') in X.squad and c['p'] not in X.squad and c['p'] < X.H:
            if X.team[c['p']] == X.team[c['to']]:
                continue
            ev[(c['p'], c['to'])].append(dict(t=c['t'], boat=0, troops=c.get('sent', 0), mtn=1 if c.get('mtn') else 0,
                                              first=dict(t=c['t'], toTerr=c.get('toTerr'), toBal=c.get('toBal'), B0=c.get('B0'))))
    for b in S['boatLands']:
        if b['to'] in X.squad and b['p'] not in X.squad and b['p'] < X.H and not b.get('friend') and X.team[b['p']] != X.team[b['to']]:
            ev[(b['p'], b['to'])].append(dict(t=b['t'], boat=1, troops=b['troops'], mtn=0,
                                              first=dict(t=b['t'], toTerr=b['toTerr'], toBal=b['toBal'], B0=b.get('myBal'))))
    rows = []
    for (foe, me), L in ev.items():
        L.sort(key=lambda e: e['t'])
        groups, cur = [], []
        for e in L:
            if cur and e['t'] - cur[-1]['t'] > gap:
                groups.append(cur)
                cur = []
            cur.append(e)
        if cur:
            groups.append(cur)
        for G in groups:
            tot = sum(e['troops'] for e in G)
            if tot < min_troops:
                continue
            ts = [e['t'] for e in G]
            t0, t1 = min(ts) - 300, max(ts) + 100
            mine = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c['p'] == me and c.get('to') == foe and t0 <= c['t'] <= t1]
            others = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c['p'] in X.squad and c['p'] != me and c.get('to') == foe and t0 <= c['t'] <= t1
                      and X.alive_active(c['p'], c['t'])]
            don_in = [x for x in S['donations'] if x['ok'] and x['to'] == me and t0 <= x['t'] <= t1]
            don_out = [x for x in S['donations'] if x['ok'] and x['from'] == me and t0 <= x['t'] <= t1]
            rows.append(dict(foe=foe, foeName=X.name(foe), me=me, name=X.M.bots[me].name, team=X.team[me],
                             n=sum(1 for e in G if not e['boat']), mtn=sum(e['mtn'] for e in G), troops=sum(e['troops'] for e in G if not e['boat']),
                             boats=sum(1 for e in G if e['boat']), boatTroops=sum(e['troops'] for e in G if e['boat']),
                             t0=min(ts), t1=max(ts), first=G[0]['first'], foeBal0=X.bal(foe, min(ts)), foeTerr0=X.terr(foe, min(ts)),
                             mineN=len(mine), mineTroops=sum(c.get('sent', 0) for c in mine),
                             othersN=len(others), othersTroops=sum(c.get('sent', 0) for c in others), othersWho=sorted({X.M.bots[c['p']].name for c in others}),
                             donIn=sum(x['delivered'] for x in don_in), donOut=sum(x['delivered'] for x in don_out), donFee=sum(x['fee'] for x in don_out),
                             terrAfter=X.terr(me, min(max(ts) + 100, X.endT)), death=X.deathT[me], husk=(me in X.leave and min(ts) >= X.leave[me]['t'])))
    rows.sort(key=lambda r: r['t0'])
    return rows


def sec_sieges(X, min_troops=200000):
    print(f'敌方真人对我方号的围攻（录像里的陆攻指令（含翻山）+ 登陆；同一对相邻两条隔 900 拍以上拆成两组；合计 >= {fmt(min_troops)} 兵的组，按首条时间排）。还手 = [首条-300, 末条+100] 内对同一个敌人的陆攻')
    R = siege_rows(X, min_troops)
    for r in R:
        f = r['first']
        ratio = f"{r['foeBal0'] / max(1, f['toBal']):.1f}×" if f.get('toBal') else '-'
        print(f"   t={r['t0']:5d}~{r['t1']:5d} {r['foeName']}（地 {r['foeTerr0']} 兵 {fmt(r['foeBal0'])}）→ {r['name']}{'(空壳)' if r['husk'] else ''}（队{r['team']}，地 {f.get('toTerr')} 兵 {fmt(f.get('toBal') or 0)}，对方兵是它的 {ratio}）："
              f"陆攻 {r['n']} 条 {fmt(r['troops'])}" + (f"（其中翻山 {r['mtn']} 条）" if r.get('mtn') else '') + (f" + 登陆 {r['boats']} 次 {fmt(r['boatTroops'])}" if r['boats'] else '') +
              f"｜它自己还手 {r['mineN']} 条 {fmt(r['mineTroops'])}；别的我方号打这个敌人 {r['othersN']} 条 {fmt(r['othersTroops'])}{'（' + '、'.join(r['othersWho']) + '）' if r['othersWho'] else ''}"
              f"｜它同期收到捐款 {fmt(r['donIn'])}、捐出 {fmt(r['donOut'])}（手续费 {fmt(r['donFee'])}）｜末条后 100 拍地 {r['terrAfter']}" + (f"，阵亡 t={r['death']}" if r['death'] >= 0 else ''))
    if R:
        print(f"合计 {len(R)} 组：敌方出兵 {fmt(sum(r['troops'] + r['boatTroops'] for r in R))}；目标自己还手 {fmt(sum(r['mineTroops'] for r in R))}；别的我方号同期打这些敌人 {fmt(sum(r['othersTroops'] for r in R))}")


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
    # 按 pct（指令里的千分比，分母 1024）
    bp = defaultdict(lambda: [0, 0, 0])
    for r in out:
        b = bp[r['pct']]
        b[0] += 1
        b[1] += r['delivered']
        b[2] += r['fee']
    if bp:
        print('我方捐出按 pct：' + '；'.join(f"{k}‰ {v[0]} 笔 到账 {fmt(v[1])} 费 {fmt(v[2])}" for k, v in sorted(bp.items(), key=lambda kv: -kv[1][0])[:8])
              + (f"；其余 {sum(v[0] for k, v in sorted(bp.items(), key=lambda kv: -kv[1][0])[8:])} 笔" if len(bp) > 8 else ''))
    # 小额
    small = [r for r in out if r['pct'] < 150]
    if small:
        print(f"其中 pct<150 的 {len(small)} 笔：到账 {fmt(sum(r['delivered'] for r in small))}，手续费 {fmt(sum(r['fee'] for r in small))}，损耗率 {pc(sum(r['fee'] for r in small), sum(r['fee'] + r['delivered'] for r in small))}")
    husk = [r for r in out if r['toLeft']]
    if husk:
        print(f"捐给空壳（已离开的号）{len(husk)} 笔：到账 {fmt(sum(r['delivered'] for r in husk))}，手续费 {fmt(sum(r['fee'] for r in husk))}")
    if husk:
        by = defaultdict(lambda: [0, 0, 0])
        for r in husk:
            v = by[X.name(r['from'])]
            v[0] += 1
            v[1] += r['delivered']
            v[2] += r['fee']
        print('   按捐出号：' + '；'.join(f"{k} {v[0]} 笔 到账 {fmt(v[1])} 费 {fmt(v[2])}" for k, v in sorted(by.items(), key=lambda kv: -kv[1][1])))
    bad = [r for r in out if r['fee'] > r['delivered']]
    if bad:
        by = defaultdict(lambda: [0, 0, 0])
        for r in bad:
            v = by[X.name(r['from'])]
            v[0] += 1
            v[1] += r['delivered']
            v[2] += r['fee']
        print(f"手续费 > 到账的 {len(bad)} 笔：到账 {fmt(sum(r['delivered'] for r in bad))}，手续费 {fmt(sum(r['fee'] for r in bad))}")
        print('   按捐出号：' + '；'.join(f"{k} {v[0]} 笔 到账 {fmt(v[1])} 费 {fmt(v[2])}" for k, v in sorted(by.items(), key=lambda kv: -kv[1][2])))
        print('   最贵的 8 笔：' + '；'.join(f"t{r['t']} {X.name(r['from'])}→{X.name(r['to'])} 到账 {fmt(r['delivered'])} 费 {fmt(r['fee'])}（收款人密度 {r['toDens']:.0f}）" for r in sorted(bad, key=lambda r: r['delivered'] - r['fee'])[:8]))
    byteam = defaultdict(lambda: [0, 0, 0])
    for r in out:
        v = byteam[X.team[r['from']]]
        v[0] += 1
        v[1] += r['delivered']
        v[2] += r['fee']
    print('按捐出号所在的队：' + '；'.join(f"队{k} {v[0]} 笔 到账 {fmt(v[1])} 费 {fmt(v[2])}（损耗率 {pc(v[2], v[1] + v[2])}）" for k, v in sorted(byteam.items())))
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
    # 同一个本机拍 >=2 个号捐给同一个收款人（探针逐条单独判，不排先后：先到的一笔把收款人的余量/配额用掉，后面的就不成立了）
    grp = defaultdict(list)
    for r in rows:
        grp[(r['t'], r['to'])].append(r)
    multi = {k: v for k, v in grp.items() if len(v) >= 2}
    if multi:
        ne = [r for v in multi.values() for r in v if r['accepted'] is False]
        pas = [r for r in ne if r['verdict'] == '校验能过却没执行']
        print(f"  同一拍 >=2 个号捐给同一个收款人：{len(multi)} 组 {sum(len(v) for v in multi.values())} 条日志，其中没执行 {len(ne)} 条（「校验能过却没执行」{len(pas)} 条）；"
              + '；'.join(f"t={k[0]}→{X.name(k[1])} {len(v)} 个号（执行 {sum(1 for r in v if r['accepted'])}）" for k, v in sorted(multi.items())[:14]))
        byto = defaultdict(lambda: [0, 0, 0])
        for k, v in multi.items():
            byto[k[1]][0] += 1
            byto[k[1]][1] += len(v)
            byto[k[1]][2] += sum(1 for r in v if r['accepted'] is False)
        print('    按收款人：' + '；'.join(f"{X.name(q)} {a[0]} 组 {a[1]} 条（没执行 {a[2]}）" for q, a in sorted(byto.items(), key=lambda kv: -kv[1][1])))
        big = [(k, v) for k, v in sorted(multi.items()) if len(v) >= 4]
        if big:
            print(f"    其中同拍 >=4 个号的 {len(big)} 组：" + '；'.join(
                f"t={k[0]}→{X.name(k[1])} {len(v)} 个号（{'、'.join(X.M.bots[r['me']].name for r in v)}；执行 {sum(1 for r in v if r['accepted'])}）" for k, v in big))
    q = [r for r in rows if r['verdict'] == '配额不够']
    if q:
        print(f"  配额不够 {len(q)} 条按时段：t<2200 {sum(1 for r in q if r['t'] < 2200)}；2200~4283 {sum(1 for r in q if 2200 <= r['t'] < 4284)}；t>=4284 {sum(1 for r in q if r['t'] >= 4284)}（引擎从 t=4284 起不再查配额）")
        pr = defaultdict(list)
        for r in q:
            pr[(r['me'], r['to'])].append(r['t'])
        print('  配额不够按（捐款人→收款人）：' + '；'.join(f"{X.name(k[0])}→{X.name(k[1])} {len(v)} 条（t={min(v)}~{max(v)}）" for k, v in sorted(pr.items(), key=lambda kv: -len(kv[1]))[:10]))
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
    # 逐条挨打账（eng_replay.cjs 在引擎的船打船函数里装的只读口子）：[船主, 船编号, 10 拍格起点, 打掉的兵]
    hits = defaultdict(list)
    for o, bid, tb, d in S.get('boatHits') or []:
        hits[(o, bid)].append((tb, d))
    exact = S.get('boatHits') is not None
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
        r['left'] = left
        r['seaLoss'] = c['sent'] - left if left is not None else None
        if exact and left is not None:
            # 真值：被敌船打掉 = 口子记下的；自然损耗 = 总损耗 − 被打掉
            h = sum(d for tb, d in hits.get((c['p'], c.get('bid', -1)), []) if c['t'] - 10 < tb <= t1)
            h = min(h, c['sent'] - left)
            r['hitLoss'] = h
            r['decayOnly'] = c['sent'] - (c['sent'] - left - h)
        else:
            # 旧版 sim_state 没有逐条挨打账：按「一路没挨打」估自然损耗，剩下的算被打掉（会低估被打掉的）
            r['decayOnly'] = v
            r['hitLoss'] = max(0, v - left) if left is not None else None
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
    # 合计：没生效的陆攻打的是谁、落在哪一段
    atk_all = [c for cs in by.values() for c in cs if c['k'] == 'atk']
    dead = [c for c in atk_all if not c['ok']]
    neut_id = S.get('neutralId', 512)
    is_neut = lambda c: c.get('to') == neut_id or c.get('raw') == neut_id  # noqa: E731
    seg = lambda lo, hi: sum(1 for c in dead if lo <= c['t'] < hi)  # noqa: E731
    p47 = [c for c in atk_all if is_neut(c) and c['pct'] == 47]
    p47ok = [c for c in p47 if c['ok']]
    print(f"合计：陆攻 {len(atk_all)} 条，没生效 {len(dead)} 条（{pc(len(dead), len(atk_all))}），其中打无主地的 {sum(1 for c in dead if is_neut(c))} 条；"
          f"按拍：t<1500 {seg(0, 1500)}，1500~2199 {seg(1500, 2200)}，>=2200 {seg(2200, 10 ** 9)}")
    print(f"      无主地 47‰ 小单 {len(p47)} 条：没生效 {len(p47) - len(p47ok)}，生效 {len(p47ok)} 条出兵 {fmt(sum(c['sent'] for c in p47ok))}、手续费 {fmt(sum(c['fee'] for c in p47ok))}"
          f"（余额 >=50 万时的 {sum(1 for c in p47ok if c['B0'] >= 500000)} 条：出兵 {fmt(sum(c['sent'] for c in p47ok if c['B0'] >= 500000))}、手续费 {fmt(sum(c['fee'] for c in p47ok if c['B0'] >= 500000))}）")
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
            rows.append((c['t'], 1, f"    ← {X.name(c['p'])}[{X.cls(me, c['p'], c['t'])}] {'翻山' if c.get('mtn') else ''}攻我 {c.get('pct', '')}‰ 出兵 {fmt(c.get('sent', 0))}{'' if c['ok'] else ' ×没生效'}"))
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
        early = [r for r in rows if r['t0'] < 2000]
        if early and len(early) < len(rows):
            print(f"   其中 t<2000 开始的 {len(early)} 段：涉及 {len({r['p'] for r in early})} 个号，断 {min(r['gap'] for r in early)}~{max(r['gap'] for r in early)} 拍，策略共发令 {sum(r['issued'] for r in early)} 条；"
                  f"之后开始的 {len(rows) - len(early)} 段共发令 {sum(r['issued'] for r in rows if r['t0'] >= 2000)} 条")
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
        tot.append((S['ticks'][i], sum(v['terr'][i] for v in S['poolAi'].values()), S['aiLand'][i] if S.get('aiLand') else S['teamLand'][i][0]))
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
    al = S.get('aiLand')
    ai = [(S['ticks'][i], round(100 * (al[i] if al else S['teamLand'][i][0]) / X.land, 1)) for i in range(len(S['ticks'])) if S['ticks'][i] % 90 == 0 and S['ticks'][i] <= 2700]
    print('   内置 AI 占地%' + ('' if al or not any(X.team[p] for p in range(X.H, 512)) else '（旧重放文件没有 AI 合计，8 队局这里恒为 0，重跑 run_truth.sh）') + '：' + ' '.join(f"t{t}:{v}" for t, v in ai if t % 180 == 0 or t in (630, 1170, 1530)))
    if al:
        ab, an = S['aiBal'], S['aiAlive']
        print('   内置 AI 存活数/兵：' + ' '.join(f"t{S['ticks'][i]}:{an[i]}/{fmt(ab[i])}" for i in range(len(S['ticks'])) if S['ticks'][i] in (270, 630, 900, 1170, 1530, 2070, 3060)))


# ------------------------------------------------------------------ top（某一拍全场最大的真人号）
def top_rows(X, t=None, n=12):
    S = X.S
    i = X.ix(t if t is not None else X.endT)
    tt = S['ticks'][i]
    rows = []
    for p in range(X.H):
        if X.deathT[p] >= 0 and tt >= X.deathT[p]:
            continue
        terr, bal = S['hum'][p]['terr'][i], S['hum'][p]['bal'][i]
        if terr <= 0:
            continue
        rows.append(dict(p=p, name=X.name(p), team=X.team[p], terr=terr, bal=bal, ours=p in X.squad,
                         husk=p in X.leave and tt >= X.leave[p]['t']))
    rows.sort(key=lambda r: -r['terr'])
    return tt, rows[:n], rows


def sec_top(X, t=None, n=12):
    tt, top, allr = top_rows(X, t, n)
    print(f"t={tt} 领土最大的 {len(top)} 个真人号（全场在场真人 {sum(1 for r in allr if not r['husk'])} 个、空壳 {sum(1 for r in allr if r['husk'])} 个）")
    for k, r in enumerate(top, 1):
        tag = ('*我方' if r['ours'] else '') + ('·空壳' if r['husk'] else '')
        print(f"   {k:2d}. {r['name'][:22]:22s} 队{r['team']} 地 {r['terr']:6d}（{100 * r['terr'] / X.land:4.1f}%）兵 {fmt(r['bal']):>6s} 密度 {r['bal'] / max(1, r['terr']):5.1f} {tag}")
    ours = [(k, r) for k, r in enumerate(allr, 1) if r['ours'] and not r['husk']]
    if ours:
        print('   我方在场号的名次：' + '；'.join(f"{r['name']} 第 {k}（{r['terr']} 格，队{r['team']}）" for k, r in ours))


# ------------------------------------------------------------------ pokes（HL-ASSIST 的 10% 协防戳：替谁打的、打了谁、之后对方对我做了什么）
def poke_rows(X, before=900, after=600):
    S = X.S
    out = []
    atk_on = defaultdict(list)   # (attacker, target) -> [(t, sent)]
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c['ok'] and c.get('to', 512) < 512:
            atk_on[(c['p'], c['to'])].append((c['t'], c.get('sent', 0)))
    for land in S.get('boatLands', []):
        if land.get('to', 512) < 512 and not land.get('friend') and not land.get('self'):
            atk_on[(land['p'], land['to'])].append((land['t'], land.get('troops', 0)))
    for me in X.squad:
        if me not in X.M.bots:
            continue
        used = set()   # 每条执行的指令只配给一条日志（两条日志相隔 25 拍时各有自己的指令）
        for e in sorted(X.M.bots[me].assists, key=lambda e: e['t']):
            enemy, ally = e['enemy'], e['ally']
            ex = [c for c in S['squadCmds'] if c['p'] == me and c['k'] == 'atk' and c.get('to') == enemy and c.get('pct') == 102 and 0 <= c['t'] - e['t'] <= 60
                  and (c['t'], c.get('B0')) not in used]
            c = ex[0] if ex else None
            if c:
                used.add((c['t'], c.get('B0')))
            t = c['t'] if c else e['t']
            pre = [(tt, s) for tt, s in atk_on[(enemy, me)] if t - before <= tt < t]
            post = [(tt, s) for tt, s in atk_on[(enemy, me)] if t <= tt <= t + after]
            w = S['ledgerWindow']
            gain = sum(v for ww, d in X.led[me]['gain'].items() if t - w < ww <= t + 300 for o, v in d.items() if o == enemy)
            lost = sum(v for ww, d in X.led[me]['lost'].items() if t - w < ww <= t + after for o, v in d.items() if o == enemy)
            out.append(dict(logT=e['t'], t=t, me=me, enemy=enemy, ally=ally, executed=bool(c and c['ok']), sent=c.get('sent', 0) if c else 0, fee=c.get('fee', 0) if c else 0,
                            B0=c.get('B0', 0) if c else 0, myTerr=c.get('myTerr', 0) if c else 0, enemyTerr=c.get('toTerr', 0) if c else 0, enemyBal=c.get('toBal', 0) if c else 0,
                            allyCls=X.cls(me, ally, t), allyTerr=X.terr(ally, t), enemyTeam=X.team[enemy],
                            preN=len(pre), preTroops=sum(s for _, s in pre), postN=len(post), postTroops=sum(s for _, s in post),
                            postFirst=post[0][0] if post else None, gain300=gain, lost600=lost))
    out.sort(key=lambda r: (r['t'], r['me']))
    return out


def sec_pokes(X):
    rows = poke_rows(X)
    print('HL-ASSIST 的「10% squad-rescue poke」（tryDonateToTeammate L4448-4457：对「正在打某个编队号的主攻手」发一条 102‰ 的陆攻）')
    print('   之前/之后 = 被戳的那个人在戳之前 900 拍 / 之后 600 拍内对出手号的陆攻指令与登陆（条数、兵）；得地 = 戳后 300 拍内从它手里拿到的格数；失地 = 戳后 600 拍内被它拿走的格数')
    for r in rows:
        ex = f"执行 t={r['t']} 出兵 {fmt(r['sent'])} 费 {fmt(r['fee'])}（余额 {fmt(r['B0'])}，我地 {r['myTerr']}）" if r['executed'] else '录像里没有对应指令'
        print(f"   日志 t={r['logT']:5d} {X.name(r['me'])}(队{X.team[r['me']]}) → {X.name(r['enemy'])}(队{r['enemyTeam']}，地 {r['enemyTerr']} 兵 {fmt(r['enemyBal'])})，替 {X.name(r['ally'])}[{r['allyCls']}，地 {r['allyTerr']}]：{ex}"
              f"｜之前 {r['preN']} 条 {fmt(r['preTroops'])}｜之后 {r['postN']} 条 {fmt(r['postTroops'])}" + (f"（首条 t={r['postFirst']}，隔 {r['postFirst'] - r['t']} 拍）" if r['postFirst'] is not None else '')
              + f"｜得地 {r['gain300']} 失地 {r['lost600']}")
    if rows:
        exed = [r for r in rows if r['executed']]
        cross = [r for r in rows if '异队' in r['allyCls']]
        husk = [r for r in rows if '空壳' in r['allyCls']]
        quiet = [r for r in exed if r['preN'] == 0]
        hit = [r for r in quiet if r['postN'] > 0]
        # 两条日志可能对上同一条执行的指令（冷却内重复下令只进了一条）：出兵和手续费按（号, 执行拍）去重
        uniq = {(r['me'], r['t']): r for r in exed}
        uq = {(r['me'], r['t']): r for r in quiet}
        uh = {(r['me'], r['t']): r for r in hit}
        print(f"合计 {len(rows)} 条日志（对上录像指令的 {len(exed)} 条，去重后是 {len(uniq)} 条执行的指令：出兵 {fmt(sum(r['sent'] for r in uniq.values()))}、手续费 {fmt(sum(r['fee'] for r in uniq.values()))}）；"
              f"替异队号打的 {len(cross)} 条，被救的号已是空壳的 {len(husk)} 条")
        print(f"   戳之前 900 拍对方没有对出手号下过陆攻/登陆的 {len(uq)} 条指令，其中戳后 600 拍内对方对出手号动手的 {len(uh)} 条")
        byfoe = defaultdict(lambda: [0, 0])
        for r in uniq.values():
            byfoe[r['enemy']][0] += 1
            byfoe[r['enemy']][1] += r['sent']
        print('   按被戳的人：' + '；'.join(f"{X.name(q)} {v[0]} 条 {fmt(v[1])}" for q, v in sorted(byfoe.items(), key=lambda kv: -kv[1][1])))
    else:
        print('   （本局没有 HL-ASSIST）')


# ------------------------------------------------------------------ boatwar（船打船）
def boatwar_rows(X):
    """eng_replay.cjs 在引擎的 acV（船打船）里装的只读口子：按（开火的船主, 挨打的船主）累计打掉的兵。"""
    bs = X.S.get('boatShots')
    if bs is None:
        return None
    rows = []
    for e in bs:
        f, t = e['from'], e['to']
        rows.append(dict(t0=e['t0'], t1=e['t1'], frm=f, to=t, dmg=e['dmg'], n=e['n'], fromSquad=f in X.squad, toSquad=t in X.squad,
                         fromTeam=X.team[f] if f < len(X.team) else 0, toTeam=X.team[t] if t < len(X.team) else 0))
    rows.sort(key=lambda r: -r['dmg'])
    return rows


def sec_boatwar(X):
    rows = boatwar_rows(X)
    if rows is None:
        print('sim_state.json 里没有 boatShots（用新版 eng_replay.cjs 重跑 run_truth.sh）')
        return
    print('船打船（引擎 acV：每 2 拍，7.5 格内不同队的船互相打；同队的船不打）。只列至少一方是我方号的')
    both = [r for r in rows if r['fromSquad'] and r['toSquad']]
    print(f"两头都是我方号（异队的我方号在海上互打）：{len(both)} 组，共打掉 {fmt(sum(r['dmg'] for r in both))} 兵")
    for r in both:
        print(f"   t={r['t0']}~{r['t1']} {X.name(r['frm'])}(队{r['fromTeam']}) 的船 → {X.name(r['to'])}(队{r['toTeam']}) 的船：打掉 {fmt(r['dmg'])} 兵（{r['n']} 次）")
    inn = [r for r in rows if r['toSquad'] and not r['fromSquad']]
    out = [r for r in rows if r['fromSquad'] and not r['toSquad']]
    print(f"外人的船打我方号的船：{len(inn)} 组，共 {fmt(sum(r['dmg'] for r in inn))} 兵；我方号的船打外人的船：{len(out)} 组，共 {fmt(sum(r['dmg'] for r in out))} 兵")
    for r in (inn + out)[:16]:
        print(f"   t={r['t0']}~{r['t1']} {X.name(r['frm'])}(队{r['fromTeam']}) → {X.name(r['to'])}(队{r['toTeam']})：{fmt(r['dmg'])} 兵（{r['n']} 次）")


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


def gate_rows(X, t0=0, t1=10 ** 9):
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
        if not X.alive_active(p, t) or not (t0 <= t < t1):
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
                if 'send' not in hg and 'D' in r['out']:
                    extra[p]['humNoSendDon'] += 1
                    extra[p]['humNoSendDon:' + first] += 1
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


def boxedout_rows(X, t0=0, t1=10 ** 9):
    """策略眼里没有可打的邻居也没有无主邻格（nb=0 且 neut=0）的决策拍，影子在这些拍发出了什么
    （probe.json 的 tally）；同一段里录像真实执行的捐款与发船。
    两条线：被围捐款门槛 55 兵/格（tryDonateToTeammate L4463）；往价格 >= cRef 的岸发船要兵 > 100×地、
    且 boatFrac×(兵−100×地) >= feeK×(32/1024)×兵，即密度 >= 133.3（boatOut L1044 + floors L865）。"""
    D = shadow_load(X)
    if not D or not D.get('tally'):
        return None
    S = X.S
    rows = {}
    for r in D['tally']:
        p, t = r['p'], r['t']
        if not (t0 <= t < t1) or not X.alive_active(p, t):
            continue
        if r['nb'] != 0 or r['neut'] != 0:
            continue
        o = rows.setdefault(p, dict(me=p, name=X.M.bots[p].name, team=X.team[p], ticks=0, don=0, boat=0, other=0, none=0, dens=[], ge55=0, ge133=0, tFirst=t, tLast=t))
        o['ticks'] += 1
        o['tLast'] = t
        out = r['out']
        if 'D' in out:
            o['don'] += 1
        elif 'B' in out:
            o['boat'] += 1
        elif out:
            o['other'] += 1
        else:
            o['none'] += 1
        d = r['B'] / max(1, r['L'])
        o['dens'].append(d)
        if d >= 55:
            o['ge55'] += 1
        if d >= 133.3:
            o['ge133'] += 1
    for p, o in rows.items():
        ds = sorted(o.pop('dens'))
        o['densMed'] = round(ds[len(ds) // 2], 1)
        o['densMax'] = round(ds[-1], 1)
        dn = [x for x in S['donations'] if x['ok'] and x['from'] == p and t0 <= x['t'] < t1]
        o['realDon'] = len(dn)
        o['realDonDelivered'] = sum(x['delivered'] for x in dn)
        o['realDonFee'] = sum(x['fee'] for x in dn)
        bt = [c for c in S['squadCmds'] if c['k'] == 'boat' and c.get('ok') and c['p'] == p and t0 <= c['t'] < t1]
        o['realBoats'] = len(bt)
        o['realBoatTroops'] = sum(c['sent'] for c in bt)
    return sorted(rows.values(), key=lambda o: (o['team'], -o['ticks']))


def sec_boxedout(X, t0=0, t1=10 ** 9):
    R = boxedout_rows(X, t0, t1)
    if R is None:
        print('没有影子流水（先跑 strat_probe.mjs <id> --me squad --json --tally）')
        return
    print(f'策略眼里 nb=0 且 neut=0（没有可打的邻居、没有无主邻格）的决策拍里，影子发出了什么（t={t0}~{min(t1, X.endT)}）；'
          '右边是同一段录像里这个号真实执行的捐款和发船')
    print('   两条线：被围捐款门槛 55 兵/格（L4463）；往敌方岸发船要密度 >= 133.3（L1044 + L865：floor = 100×地）')
    for o in R:
        print(f"   {o['name']:<14} 队{o['team']} 这类决策拍 {o['ticks']:>4}（t={o['tFirst']}~{o['tLast']}）：影子捐款 {o['don']:>3}、发船 {o['boat']:>3}、其它 {o['other']:>2}、什么都不发 {o['none']:>4}"
              f"｜密度 中位 {o['densMed']:>5} 最高 {o['densMax']:>5}，>=55 的 {o['ge55']:>4} 拍、>=133.3 的 {o['ge133']:>4} 拍"
              f"｜录像：捐款 {o['realDon']} 笔（到账 {fmt(o['realDonDelivered'])}，费 {fmt(o['realDonFee'])}），发船 {o['realBoats']} 条（{fmt(o['realBoatTroops'])}）")
    for tm in sorted({o['team'] for o in R}):
        rr = [o for o in R if o['team'] == tm]
        print(f"   队{tm} 合计：这类决策拍 {sum(o['ticks'] for o in rr)}，影子捐款 {sum(o['don'] for o in rr)}、发船 {sum(o['boat'] for o in rr)}、什么都不发 {sum(o['none'] for o in rr)}；"
              f"密度 >=133.3 的 {sum(o['ge133'] for o in rr)} 拍；录像捐款 {sum(o['realDon'] for o in rr)} 笔（到账 {fmt(sum(o['realDonDelivered'] for o in rr))}，费 {fmt(sum(o['realDonFee'] for o in rr))}），发船 {sum(o['realBoats'] for o in rr)} 条")


def gapgrow_rows(X, a=1000, b=2000, ticks=None):
    """把我方号按「t=a~b 之间有没有指令断档（gap_rows）」分两组，对照各组的领土合计和单号中位，
    再列出其余真人（不含空壳）与内置 AI 的同期领土。返回 (断档组, 没断档组, rows)。"""
    S = X.S
    gp = sorted({r['p'] for r in gap_rows(X) if r['t0'] < b and r['t1'] > a})
    rest = [p for p in X.squad if p not in gp]
    ticks = ticks or [t for t in (1080, 1530, 1980, 2070, 2520, 3060) if t < X.endT]
    rows = []
    for t in ticks:
        def grp(ps):
            v = sorted(X.terr(p, t) for p in ps if X.alive_active(p, t))
            return dict(n=len(v), land=sum(v), med=(v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2) if v else 0,
                        troops=sum(X.bal(p, t) for p in ps if X.alive_active(p, t)))
        oth = [p for p in range(X.H) if p not in X.squad and X.alive_active(p, t) and X.terr(p, t) > 0]
        i = X.ix(t)
        hum_land = sum(S['hum'][p]['terr'][i] for p in range(X.H))
        rows.append(dict(t=t, gap=grp(gp), nogap=grp(rest), others=grp(oth), aiLand=S['aiLand'][i] if 'aiLand' in S else None, humLand=hum_land))
    return gp, rest, rows


def sec_gapgrow(X, a=1000, b=2000, ticks=None):
    gp, rest, rows = gapgrow_rows(X, a, b, ticks)
    print(f'指令断档（t={a}~{b} 之间有一段 >=300 拍、策略在发令而录像里没有指令）的号 vs 没断档的号：各组在场号的领土合计 / 单号中位 / 兵力合计')
    print('   断档组：' + '、'.join(X.M.bots[p].name for p in gp))
    print('   没断档：' + '、'.join(X.M.bots[p].name for p in rest))
    base = rows[0]
    for r in rows:
        def f(k):
            g, g0 = r[k], base[k]
            return f"{g['n']:>2} 个 {g['land']:>7} 格（×{g['land'] / max(1, g0['land']):.2f}）中位 {g['med']:>7.0f} 兵 {fmt(g['troops']):>6}"
        print(f"   t={r['t']:>5} 断档组 {f('gap')} ｜没断档 {f('nogap')} ｜其余真人 {f('others')}")


def exchange_rows(X, edges=None, top=3):
    """对我方在场号出兵最多的几个敌方真人，逐窗口的指令对账：它 → 我方在场号的陆攻（条数、出兵）与登陆（条数、船上兵），
    我方在场号 → 它的陆攻与发船（条数、出兵），它在窗口两端的地/兵，它每条陆攻的千分比。只算进了录像且生效的指令。"""
    S = X.S
    if not edges:
        edges = [e for e in (1500, 4000, 5000, 6000, 7000, 8100) if e < X.endT] + [X.endT]
    tot = defaultdict(int)
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c.get('ok') and c['p'] not in X.squad and c['p'] < X.H and c.get('to') in X.squad and X.alive_active(c['to'], c['t']) \
                and X.team[c['p']] != X.team[c['to']]:
            tot[c['p']] += c['sent']
    for l in S.get('boatLands') or []:
        if l['p'] not in X.squad and l['p'] < X.H and l.get('to') in X.squad and not l.get('friend') and X.alive_active(l['to'], l['t']):
            tot[l['p']] += l['troops']
    foes = [p for p, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:top]]
    rows = []
    for foe in foes:
        for a, b in zip(edges, edges[1:]):
            theirs = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c['p'] == foe and c.get('to') in X.squad and a <= c['t'] < b and X.alive_active(c['to'], c['t'])]
            lands = [l for l in (S.get('boatLands') or []) if l['p'] == foe and l.get('to') in X.squad and not l.get('friend') and a <= l['t'] < b and X.alive_active(l['to'], l['t'])]
            ours = [c for c in S['squadCmds'] if c['k'] in ('atk', 'boat') and c.get('ok') and c['p'] in X.squad and c.get('to') == foe and a <= c['t'] < b and X.alive_active(c['p'], c['t'])]
            tb = min(b, X.endT)
            rows.append(dict(foe=foe, name=X.name(foe), team=X.team[foe], t0=a, t1=b,
                             theirN=len(theirs), theirTroops=sum(c['sent'] for c in theirs), theirPct=sorted(c['pct'] for c in theirs), theirMtn=sum(1 for c in theirs if c.get('mtn')),
                             theirTargets=sorted({X.M.bots[c['to']].name for c in theirs} | {X.M.bots[l['to']].name for l in lands}),
                             landN=len(lands), landTroops=sum(l['troops'] for l in lands),
                             ourN=len(ours), ourTroops=sum(c['sent'] for c in ours), ourPct=sorted(c['pct'] for c in ours),
                             terr0=X.terr(foe, a), bal0=X.bal(foe, a), terr1=X.terr(foe, tb), bal1=X.bal(foe, tb)))
    return rows


def mountain_rows(X):
    """录像里的翻山指令（指令号 10，只有山地图有）：谁、对谁、千分比；进了 squadCmds 的（发令人或目标是编队名字的号）带出兵和手续费。
    引擎：出兵 = (pct+1)/1024×余额，另扣 max(余额/10, 1000)（bB.qi.i2 → bD.gv.m6）。需要 out/<id>/replay_decoded.json（replay_decode.mjs）。"""
    import json
    path = os.path.join(OUT, X.M.mid if hasattr(X.M, 'mid') else X.S['matchId'], 'replay_decoded.json')
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    rec = {(c['t'], c['p']): c for c in X.S['squadCmds'] if c.get('mtn')}
    rows = []
    for c in d.get('cmds', []):
        if c.get('id') != 10:
            continue
        p, pct, tg = c['player'], c['dX'] >> 10, c['dX'] % 1024
        r = rec.get((c['t'], p)) or rec.get((c['t'] + 1, p)) or rec.get((c['t'] - 1, p))
        rows.append(dict(t=c['t'], p=p, name=X.name(p), team=X.team[p] if p < X.H else 0, pct=pct, to=tg,
                         toName=(X.name(tg) if tg < X.H else ('无主地' if tg >= 512 else f'内置AI#{tg}')),
                         cls=(X.cls(tg, p, c['t']) if tg in X.squad else ''), bySquad=p in X.squad, onSquad=tg in X.squad,
                         sent=r['sent'] if r else None, fee=r['fee'] if r else None, ok=r['ok'] if r else None, B0=r['B0'] if r else None))
    return rows


def sec_mountain(X):
    R = mountain_rows(X)
    if R is None:
        print('没有 replay_decoded.json（先跑 replay_decode.mjs）')
        return
    print(f"录像里的翻山指令（指令号 10）{len(R)} 条：我方号发出的 {sum(1 for r in R if r['bySquad'])} 条；外人对编队名字的号发出的 {sum(1 for r in R if r['onSquad'] and not r['bySquad'])} 条")
    by = defaultdict(int)
    for r in R:
        by[r['name']] += 1
    print('   按发令人：' + '；'.join(f"{n} {v} 条" for n, v in sorted(by.items(), key=lambda kv: -kv[1])))
    for r in R:
        if not (r['onSquad'] or r['bySquad']):
            continue
        ex = f"｜拍前余额 {fmt(r['B0'])}，出兵 {fmt(r['sent'])}，手续费 {fmt(r['fee'])}{'' if r['ok'] else ' ×没生效'}" if r['sent'] is not None else ''
        tg = r['to']
        husk = '(空壳)' if (tg in X.leave and r['t'] >= X.leave[tg]['t']) else ''
        nb0 = [x for x in X.neigh[tg] if x['t'] <= r['t']]
        was = '-'
        if nb0:
            was = '已接壤' if any(q[0] == r['p'] for q in nb0[-1]['nb']) else '不接壤'
        lost = sum(v for w, d in X.led[tg]['lost'].items() if r['t'] - r['t'] % 100 <= w < r['t'] + 300 for o, v in d.items() if o == r['p'])
        print(f"   t={r['t']:5d} {r['name']}（队{r['team']}）→ {r['toName']}{husk}（队{X.team[tg]}，地 {X.terr(tg, r['t'])} 兵 {fmt(X.bal(tg, r['t']))}）{r['pct']}‰{ex}"
              f"｜下令前一次邻居采样：两者{was}｜此后 300 拍内它从目标手里拿走 {lost} 格")


def sec_exchange(X, edges=None, top=3):
    R = exchange_rows(X, edges, top)
    print('对我方在场号出兵最多的敌方真人：逐窗口指令对账（只算进了录像且生效的陆攻/登陆/发船；兵 = 出兵数）')
    cur = None
    for r in R:
        if r['foe'] != cur:
            cur = r['foe']
            rr = [x for x in R if x['foe'] == cur]
            print(f"  {r['name']}（队{r['team']}）：整段它→我方 陆攻 {sum(x['theirN'] for x in rr)} 条 {fmt(sum(x['theirTroops'] for x in rr))} + 登陆 {sum(x['landN'] for x in rr)} 条 {fmt(sum(x['landTroops'] for x in rr))}；"
                  f"我方→它 {sum(x['ourN'] for x in rr)} 条 {fmt(sum(x['ourTroops'] for x in rr))}")
        print(f"     t={r['t0']:>5}~{r['t1']:<5} 它→我方 陆攻 {r['theirN']:>2} 条 {fmt(r['theirTroops']):>7}（千分比 {r['theirPct']}{'，其中翻山 ' + str(r['theirMtn']) + ' 条' if r.get('theirMtn') else ''}）+ 登陆 {r['landN']} 条 {fmt(r['landTroops']):>6}，目标 {'、'.join(r['theirTargets']) or '-'}"
              f"｜我方→它 {r['ourN']:>2} 条 {fmt(r['ourTroops']):>6}（千分比 {r['ourPct']}）｜它 地 {r['terr0']}→{r['terr1']} 兵 {fmt(r['bal0'])}→{fmt(r['bal1'])}")


def sec_gates(X, t0=0, t1=10 ** 9):
    R = gate_rows(X, t0, t1)
    if R is None:
        print('没有 probe.json 的 tally（先跑 strat_probe.mjs <id> --me squad --json --tally）')
        return
    early, core, extra, coreai = R
    print('影子策略逐决策拍（每 5 拍）卡在哪道闸。影子 = 策略源码跑在录像重演的真实局面上，指令只记不执行。' + (f'只看 t={t0}~{t1}。' if t0 > 0 or t1 < 10 ** 9 else ''))
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
        dn = {k[len('humNoSendDon:'):]: v for k, v in te.items() if k.startswith('humNoSendDon:')}
        if dn:
            per = sorted(((X.M.bots[p].name, e.get('humNoSendDon', 0)) for p, e in extra.items() if e.get('humNoSendDon')), key=lambda kv: -kv[1])
            print(f"   有真人报价、这一拍没有对真人出兵、而影子同拍发出捐款的决策拍 {te.get('humNoSendDon', 0)} 个（捐款的保底线 safeAt(-1) 封顶 oppFloorCap×领土，L4528）："
                  + '；'.join(f"{gate_txt(k)} {v}" for k, v in sorted(dn.items(), key=lambda kv: -kv[1])) + '｜按号：' + '、'.join(f"{n} {v}" for n, v in per))
        # 超软上限时 buyLand 不比价（L5267 的 !over）：这一拍对真人出了兵、排第一的报价 hc >= worth
        D = shadow_load(X)
        sends = [r for r in D['tally'] if r['t'] >= 1500 and t0 <= r['t'] < t1 and r.get('hum', 0) > 0 and X.alive_active(r['p'], r['t']) and 'send' in (r.get('hg') or '').split(',')]
        osk = [r for r in sends if r.get('over') and r.get('hc') is not None and r.get('worth') is not None and r['hc'] >= r['worth']]
        if sends:
            by = defaultdict(list)
            for r in osk:
                by[r['p']].append(r)
            det = '；'.join(f"{X.M.bots[p].name} {len(v)} 拍（报价中位 {sorted(x['hc'] for x in v)[len(v) // 2]:.1f}、worth 中位 {sorted(x['worth'] for x in v)[len(v) // 2]:.1f}）"
                            for p, v in sorted(by.items(), key=lambda kv: -len(kv[1])))
            print(f"   对真人出兵的决策拍 {len(sends)}，其中超软上限且报价 >= worth（靠 L5267 的「超软上限不比价」放行）{len(osk)} 拍{'：' + det if det else ''}")
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



def foedon_rows(X):
    """外人之间的捐款（捐款人、收款人都不是我方号；只算录像里执行了的）。按队汇总，并给出每队收得最多的那个人。"""
    S = X.S
    rows = [x for x in S['donations'] if x.get('ok') and x['from'] not in X.squad and x['to'] not in X.squad and x['from'] < X.H and x['to'] < X.H]
    by_team = defaultdict(lambda: dict(n=0, delivered=0, fee=0, recv=defaultdict(int), give=defaultdict(int), ts=[]))
    for x in rows:
        d = by_team[X.team[x['from']]]
        d['n'] += 1
        d['delivered'] += x['delivered']
        d['fee'] += x['fee']
        d['recv'][x['to']] += x['delivered']
        d['give'][x['from']] += x['delivered']
        d['ts'].append(x['t'])
    return rows, by_team


def sec_foedon(X):
    rows, by_team = foedon_rows(X)
    tot = sum(x['delivered'] for x in rows)
    fee = sum(x['fee'] for x in rows)
    print(f"外人之间执行了的捐款 {len(rows)} 笔：到账 {fmt(tot)}，手续费 {fmt(fee)}（损耗率 {pc(fee, tot + fee)}）")
    sq = [x for x in X.S['donations'] if x.get('ok') and x['from'] in X.squad]
    print(f"   对照：我方号捐出 {len(sq)} 笔，到账 {fmt(sum(x['delivered'] for x in sq))}，手续费 {fmt(sum(x['fee'] for x in sq))}")
    for tm in sorted(by_team):
        d = by_team[tm]
        recv = sorted(d['recv'].items(), key=lambda kv: -kv[1])
        give = sorted(d['give'].items(), key=lambda kv: -kv[1])
        ts = sorted(d['ts'])
        print(f"   队{tm}：{d['n']} 笔，到账 {fmt(d['delivered'])}，手续费 {fmt(d['fee'])}；t={ts[0]}~{ts[-1]}（中位 {ts[len(ts) // 2]}）")
        print('      收：' + '；'.join(f"{X.name(p)} {fmt(v)}（{pc(v, d['delivered'])}）" for p, v in recv[:5]))
        print('      捐：' + '；'.join(f"{X.name(p)} {fmt(v)}" for p, v in give[:5]))
    pairs = defaultdict(lambda: [0, 0, 0])
    back = 0
    for x in rows:
        k = (x['from'], x['to'])
        pairs[k][0] += 1
        pairs[k][1] += x['delivered']
        pairs[k][2] += x['fee']
    for x in rows:
        if any(y['from'] == x['to'] and y['to'] == x['from'] and 0 < y['t'] - x['t'] <= 150 for y in rows):
            back += 1
    print(f"   来回对捐（A→B 之后 150 拍内 B→A）的外人捐款 {back} 笔；我方同口径见 don 节")
    for (a, b), (n, v, f) in sorted(pairs.items(), key=lambda kv: -kv[1][1])[:8]:
        print(f"      {X.name(a)}（队{X.team[a]}）→ {X.name(b)}：{n} 笔 到账 {fmt(v)} 费 {fmt(f)}")
    big = sorted(rows, key=lambda x: -x['delivered'])[:6]
    print('   最大的几笔：' + '；'.join(f"t={x['t']} {X.name(x['from'])}→{X.name(x['to'])} {x['pct']}‰ 到账 {fmt(x['delivered'])}（捐前 {fmt(x['B0'])}，收款人当时 地 {x['toTerr']} 兵 {fmt(x['toBal'])}）" for x in big))


def sec_foeled(X, top=8, cuts=None):
    """我方全体与每个外人的战斗账（账目 spent/gain/lost/dmg 按对方汇总；100 拍一格）：我方耗兵、得地、失地、被打掉兵，按时间段。
    用法：simdigest.py <id> foeled [top] [t1 t2 ...]（切点；默认 3000 5000 7000 9000）"""
    cuts = cuts or [3000, 5000, 7000, 9000]
    edges = [0] + cuts + [X.endT + 1]
    tot = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    kinds = {'spent': 0, 'gain': 1, 'lost': 2, 'dmg': 3}
    for w, me, kind, other, v in X.S['ledger']:
        if kind not in kinds or me not in X.squad or other in X.squad or other >= X.H or other < 0:
            continue
        seg = max(i for i in range(len(edges) - 1) if w >= edges[i])
        tot[other][seg][kinds[kind]] += v
        tot[other]['all'][kinds[kind]] += v
    who = sorted(tot, key=lambda p: -(tot[p]['all'][2]))[:top]
    print('我方全体与外人的战斗账（按我方失地排序；耗兵 = 我方打它花掉的兵，得地 / 失地 = 格，被打掉 = 我方被它打掉的兵；账按 100 拍一格记）')
    for p in who:
        a = tot[p]['all']
        print(f"   {X.name(p)}（队{X.team[p]}）整局：我方耗兵 {fmt(a[0])} 得地 {a[1]}（{a[0] / max(1, a[1]):.0f} 兵/格）｜失地 {a[2]} 被打掉 {fmt(a[3])}（它每拿 1 格我方掉 {a[3] / max(1, a[2]):.0f} 兵）")
        for i in range(len(edges) - 1):
            s = tot[p][i]
            if not any(s):
                continue
            print(f"      t={edges[i]}~{edges[i + 1] - 1 if i == len(edges) - 2 else edges[i + 1]}：耗兵 {fmt(s[0])} 得地 {s[1]}｜失地 {s[2]} 被打掉 {fmt(s[3])}｜净 {s[1] - s[2]:+d} 格")


def sec_foewho(X, floor=3000):
    """每个外人与我方各号的得失（账目 spent/gain/lost 按「外人 × 我方号」汇总，整局）：我方哪几个号从它手里得地、它从我方哪几个号手里拿地。
    用法：simdigest.py <id> foewho [floor]（得地、失地都不到 floor 格的外人不列；默认 3000）"""
    g = defaultdict(lambda: defaultdict(int))
    s = defaultdict(lambda: defaultdict(int))
    lo = defaultdict(lambda: defaultdict(int))
    for w, me, kind, other, v in X.S['ledger']:
        if me not in X.squad or other in X.squad or other >= X.H or other < 0:
            continue
        if kind == 'gain':
            g[other][me] += v
        elif kind == 'spent':
            s[other][me] += v
        elif kind == 'lost':
            lo[other][me] += v
    who = [p for p in set(g) | set(lo) if sum(g[p].values()) >= floor or sum(lo[p].values()) >= floor]
    who.sort(key=lambda p: -(sum(lo[p].values()) + sum(g[p].values())))
    print(f'外人 × 我方号的得失（整局；得地、失地都不到 {floor} 格的外人不列；按得地 + 失地排序）')
    for p in who:
        tg, ts, tl = sum(g[p].values()), sum(s[p].values()), sum(lo[p].values())
        end = '活到终局' if X.deathT[p] < 0 else f'阵亡 t={X.deathT[p]}'
        gs = '、'.join(f"{X.name(m)} {c}（耗兵 {fmt(s[p][m])}）" for m, c in sorted(g[p].items(), key=lambda kv: -kv[1])[:5] if c > 0)
        ls = '、'.join(f"{X.name(m)} {c}" for m, c in sorted(lo[p].items(), key=lambda kv: -kv[1])[:5] if c > 0)
        print(f"   {X.name(p)}（队{X.team[p]}，{end}）：我方从它得地 {tg} 格（耗兵 {fmt(ts)}）← {gs or '-'}｜它从我方拿走 {tl} 格 ← {ls or '-'}")


def sec_foepct(X, top=8):
    """外人的出手习惯：录像里每个外人的陆攻 / 捐款 / 发船指令条数和千分比分布（录像指令 id 1 / 2 / 3；dX = 千分比），离开拍（id 9）。
    列出对我方出兵最多的 top 个外人，加上捐款条数 >= 5 的外人。"""
    S = X.S
    tot = defaultdict(int)
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c.get('ok') and c['p'] not in X.squad and c['p'] < X.H and c.get('to') in X.squad:
            tot[c['p']] += c['sent']
    who = [p for p, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:top]]
    by = defaultdict(list)
    for c in X.M.cmds:
        if c.get('phase') == 'game' and c['player'] < X.H and c['player'] not in X.squad:
            by[c['player']].append(c)
    for p, cs in by.items():
        if sum(1 for c in cs if c['id'] == 2) >= 5 and p not in who:
            who.append(p)
    print('外人的出手习惯（录像指令；千分比:条数，按条数排前 6）')
    for p in who:
        cs = by.get(p, [])
        def dist(i):
            cnt = defaultdict(int)
            for c in cs:
                if c['id'] == i:
                    cnt[c['dX']] += 1
            n = sum(cnt.values())
            return n, ' '.join(f"{k}:{v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:6])
        na, da = dist(1)
        nd, dd = dist(2)
        nb, db = dist(3)
        leave = [c['t'] for c in cs if c['id'] == 9]
        print(f"   {X.name(p)}（队{X.team[p]}）对我方出兵 {fmt(tot.get(p, 0))}｜陆攻 {na} 条 [{da}]｜捐款 {nd} 条 [{dd}]｜发船 {nb} 条 [{db}]｜"
              + (f"离开 t={leave[0]}" if leave else ('阵亡 t=%d' % X.deathT[p] if X.deathT[p] >= 0 else '活到终局')))


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
    doc['halves'] = halves_rows(X)
    doc['sieges'] = siege_rows(X)
    doc['contact'] = {str(t): contact_rows(X, t) for t in (3060, 4050, 5040, 6030, 7020, 8010) if t < X.endT}
    doc['exchange'] = exchange_rows(X)
    gp, rest, rows = gapgrow_rows(X)
    doc['gapgrow'] = dict(gapBots=[X.M.bots[p].name for p in gp], noGapBots=[X.M.bots[p].name for p in rest], rows=rows)
    bo = boxedout_rows(X, 5000, 10 ** 9)
    if bo is not None:
        doc['boxedOutFrom5000'] = bo
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
        sec_gates(X, int(a[0]) if a else 0, int(a[1]) if len(a) > 1 else 10 ** 9)
    elif sec == 'exchange':
        sec_exchange(X, [int(x) for x in a] or None)
    elif sec == 'mountain':
        sec_mountain(X)
    elif sec == 'gapgrow':
        sec_gapgrow(X, int(a[0]) if a else 1000, int(a[1]) if len(a) > 1 else 2000, [int(x) for x in a[2:]] or None)
    elif sec == 'boxedout':
        sec_boxedout(X, int(a[0]) if a else 0, int(a[1]) if len(a) > 1 else 10 ** 9)
    elif sec == 'dups':
        sec_dups(X, int(a[0]) if a else 21)
    elif sec == 'crowd':
        sec_crowd(X)
    elif sec == 'top':
        sec_top(X, int(a[0]) if a else None, int(a[1]) if len(a) > 1 else 12)
    elif sec == 'pokes':
        sec_pokes(X)
    elif sec == 'contact':
        tm = None
        aa = list(a)
        if aa and aa[0].startswith('T'):
            tm = int(aa.pop(0)[1:])
        sec_contact(X, [int(v) for v in aa] or [3060, 4050, 5040, 6030, 7020], tm)
    elif sec == 'sieges':
        sec_sieges(X, int(a[0]) if a else 200000)
    elif sec == 'halves':
        sec_halves(X, [int(v) for v in a] if a else None)
    elif sec == 'boatwar':
        sec_boatwar(X)
    elif sec == 'foedon':
        sec_foedon(X)
    elif sec == 'foepct':
        sec_foepct(X, int(a[0]) if a else 8)
    elif sec == 'foeled':
        sec_foeled(X, int(a[0]) if a else 8, [int(v) for v in a[1:]] or None)
    elif sec == 'foewho':
        sec_foewho(X, int(a[0]) if a else 3000)
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
