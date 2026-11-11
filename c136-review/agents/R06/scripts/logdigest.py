#!/usr/bin/env python3
"""logdigest.py — 只靠日志（in_game.log 的 HL-TICK / HL-OPENING / HL-DONATE，加 results.csv）就能数出来的局内事实。
录像没覆盖到的时段（或整局没有可用录像）用它；有录像真值的段落再用 oplag / issued 两段和真值对表。

用法：python3 logdigest.py <matchId> <段>
  stale     「发令不见效 → 集中清仓」：cmds 计数在涨、领土不动、余额只按利息涨（指令没有在本机局面里生效），
            随后相邻快照之间余额一次跌掉 >=50% 而领土没有丢。给出这段里发了几条指令 N，以及
            「N 条 12% 的 pulse 逐条按当时余额执行」会剩下的比例 0.868^N，与实际剩余比例对照
  silent    零指令时段：cmds 计数连续 >=450 拍不变（号还活着、日志照常打印）
  seqlag    日志行的全局序号对齐：同一时刻各号的本机拍相差多少（落后 = 本机模拟落后于最快的那个号）
  overcap   超软上限（兵 > 100×领土）的快照数，以及按引擎利率公式估算的少拿利息（按快照线性插值，估算值）
  drop30    全量 DROP30（相邻快照余额跌 >=30%）与日志侧归因：丢地 / 清仓 / 发船 / 捐款日志
  wall      墙上时钟对表：results.csv 的 (tick, seconds) 拟合出「服务器拍 = (seconds − a)/0.056」，再看每条结算行落盘时
            各号日志正打印到哪个本机拍 → 本机模拟落后服务器多少拍；日志停掉的号最后一条快照对应的墙上时刻
  oplag     开局指令「下令拍 → 进录像的执行拍」的延迟（HL-OPENING 的 t 与录像里同一条无主地指令的拍；需要录像）
  issued    日志 cmds 计数（策略自己数的已发指令）与录像里该号的指令条数（需要录像）
  json      以上汇总写 out/<id>/logdigest.json
所有阈值都写在函数开头的常量里。
"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match, interest_rate, isqrt  # noqa: E402

PULSE_LEFT = 1 - 123 / 1024 - 12 / 1024   # 一条 pct=122 的陆攻执行后余额剩下的比例（出兵 123/1024 + 手续费 12/1024）= 0.868


def fmt(n):
    n = int(n)
    a = abs(n)
    if a >= 10 ** 6:
        return f"{n / 1e6:.2f}M"
    if a >= 10 ** 4:
        return f"{n / 1e3:.0f}k"
    return str(n)


def death_tick(b):
    r = b.result
    if r and r.get('event') == 'died':
        return r['tick']
    return None


def name_of(b):
    return b.names[0] if b.names else f"me{b.me}"


# ------------------------------------------------------------------ stale
def pure_interest(a, c, land):
    """a→c 之间一条指令都没生效时，余额应该是多少（领土按 a 的算，逐 10 拍复利）。"""
    b = a['bal']
    t = a['t']
    while t < c['t']:
        t += 10
        b += b * interest_rate(t, a['terr'], land, b) // 10000
    return b


def stale_rows(M, min_cmds=4, drop=0.5, keep_land=0.9, lo=0.97, hi=1.08):
    """每个号的「发令不见效 → 集中清仓」段。
    不见效间隔：相邻快照之间 cmds 涨了，而余额 / 纯利息预测 在 [lo, hi] 内且领土变化 <= 2%（= 这段发的指令一条都没在本机局面里生效）。
    清仓：之后某个间隔余额 <= drop×纯利息预测，且领土 >= keep_land×之前（不是被人打穿丢的）。向前把相连的不见效间隔并成一段。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        n = len(tr)
        for j in range(1, n):
            a, c = tr[j - 1], tr[j]
            if not (a['bal'] >= 20000 and c['bal'] <= drop * pure_interest(a, c, M.land) and c['terr'] >= keep_land * a['terr']):
                continue
            i = j - 1
            while i > 0:
                p, q = tr[i - 1], tr[i]
                ratio = q['bal'] / max(1, pure_interest(p, q, M.land))
                if q['cmds'] > p['cmds'] and lo <= ratio <= hi and abs(q['terr'] - p['terr']) <= 0.02 * max(1, p['terr']):
                    i -= 1
                else:
                    break
            n_run = a['cmds'] - tr[i]['cmds']
            n_dump = c['cmds'] - a['cmds']
            if n_run + n_dump < min_cmds:
                continue
            after = tr[j + 1]['terr'] if j + 1 < n else c['terr']
            bal_next = tr[j + 1]['bal'] if j + 1 < n else c['bal']
            left = c['bal'] / max(1, pure_interest(a, c, M.land))
            implied = math.log(max(left, 1e-9)) / math.log(PULSE_LEFT)
            out.append(dict(me=me, name=name_of(b), t0=tr[i]['t'], tDump0=a['t'], tDump1=c['t'], cmdsRun=n_run, cmdsDump=n_dump,
                            balBefore=a['bal'], balAfter=c['bal'], left=left, implied=implied,
                            terrBefore=a['terr'], terrAfter=c['terr'], terrNext=after, densBefore=a['dens'], densAfter=c['dens'],
                            nb=a['nb'], gap=c['t'] - a['t'], deathT=death_tick(b), balNext=bal_next, rebound=bal_next >= 0.5 * a['bal'],
                            boats=c['boats'] - tr[i]['boats']))
    return out


def sec_stale(M):
    rows = stale_rows(M)
    print('「发令不见效 → 集中清仓」（只看日志）。不见效 = cmds 计数在涨，而余额正好等于纯利息预测、领土不动（发出的指令一条都没在本机局面里生效）；')
    print('   清仓 = 相邻快照之间余额不到纯利息预测的一半、而领土没丢。k = ln(清仓后余额/纯利息预测)/ln(0.868)：相当于 k 条 12% 的 pulse（出兵 123/1024 + 手续费 12/1024）逐条按当时余额执行；')
    print('   回弹 = 下一个快照余额回到清仓前的一半以上（出去的兵没花完又退回，例如目标被吃光）')
    if not rows:
        print('   （没有）')
        return
    for r in rows:
        dt = f"，{r['deathT'] - r['tDump1']} 拍后阵亡" if r['deathT'] else ''
        rb = f"；回弹：下一快照余额 {fmt(r['balNext'])}" if r['rebound'] else ''
        bt = f"（其中发船 {r['boats']} 条）" if r['boats'] else ''
        print(f"   {r['name']:14s} 不见效 t={r['t0']}~{r['tDump0']} 发令 {r['cmdsRun']} 条{bt}，清仓间隔里又发 {r['cmdsDump']} 条；nb={r['nb']} → t={r['tDump0']}~{r['tDump1']} 余额 {fmt(r['balBefore'])}→{fmt(r['balAfter'])}"
              f"（剩纯利息预测的 {100 * r['left']:.2f}%，k={r['implied']:.1f}），领土 {r['terrBefore']}→{r['terrAfter']}→{r['terrNext']}，密度 {r['densBefore']:.0f}→{r['densAfter']:.1f}{rb}{dt}")
    real = [r for r in rows if not r['rebound']]
    print(f"合计 {len(rows)} 段，涉及 {len({r['me'] for r in rows})} 个号；其中没有回弹的 {len(real)} 段，清掉的兵 {fmt(sum(r['balBefore'] - r['balAfter'] for r in real))}，"
          f"清仓后 2 个快照内领土合计 +{sum(max(r['terrAfter'], r['terrNext']) - r['terrBefore'] for r in real)} 格；这些号里之后阵亡的 {sum(1 for r in real if r['deathT'])} 个")
    # 对照：清仓窗口里每个有快照的号——清仓前发了几条指令、清仓窗口里余额最低掉到纯利息预测的多少
    if real:
        tA = min(r['t0'] for r in real)
        tB = max(r['tDump0'] for r in real)
        tC = max(r['tDump1'] for r in real)
        tD = min(r['tDump0'] for r in real)
        print(f"对照：t={tA}~{tB} 发令条数 vs t={tD}~{tC} 各间隔里「余额/纯利息预测」的最小值（全部有快照的号）")
        for me, b in sorted(M.bots.items()):
            pre = [x for x in b.traj if tA <= x['t'] <= tB]
            win = [x for x in b.traj if tD <= x['t'] <= tC]
            if len(pre) < 2 or len(win) < 2:
                continue
            ratios = [(y['bal'] / max(1, pure_interest(x, y, M.land)), x['t'], y['t'], x['terr'], y['terr']) for x, y in zip(win, win[1:])]
            mn = min(ratios)
            last = [x for x in pre if x['t'] >= tB - 270]
            nxt = next((x for x in b.traj if x['t'] > tB), None)
            if len(last) >= 2:
                tail = f"其中最后 270 拍（t={tB - 270}~{tB}）{last[-1]['cmds'] - last[0]['cmds']:2d} 条、nb={'/'.join(str(x['nb']) for x in last)}"
            else:
                tail = f"最后 270 拍没有快照（下一条快照 t={nxt['t'] if nxt else '-'} 时 cmds={nxt['cmds'] if nxt else '-'}）"
            print(f"   {name_of(b):14s} 发令 {pre[-1]['cmds'] - pre[0]['cmds']:3d} 条（cmds {pre[0]['cmds']}→{pre[-1]['cmds']}），{tail}"
                  f"｜最小比值 {mn[0]:.2f}（t={mn[1]}~{mn[2]}，领土 {mn[3]}→{mn[4]}）")


# ------------------------------------------------------------------ silent
def silent_rows(M, min_len=450):
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        i = 0
        while i < len(tr):
            j = i
            while j + 1 < len(tr) and tr[j + 1]['cmds'] == tr[i]['cmds'] and tr[j + 1]['boats'] == tr[i]['boats']:
                j += 1
            if tr[j]['t'] - tr[i]['t'] >= min_len:
                seg = tr[i:j + 1]
                d = death_tick(b)
                out.append(dict(me=me, name=name_of(b), t0=tr[i]['t'], t1=tr[j]['t'], len=tr[j]['t'] - tr[i]['t'],
                                nbMin=min(s['nb'] for s in seg), nbMax=max(s['nb'] for s in seg), neutMax=max(s['neut'] for s in seg),
                                dens0=tr[i]['dens'], dens1=tr[j]['dens'], densMax=max(s['dens'] for s in seg),
                                terr0=tr[i]['terr'], terr1=tr[j]['terr'], terrMax=max(s['terr'] for s in seg), bal0=tr[i]['bal'], bal1=tr[j]['bal'],
                                over100=sum(1 for s in seg if s['dens'] > 100), over125=sum(1 for s in seg if s['dens'] > 125),
                                toDeath=(d is not None and j == len(tr) - 1), deathT=d, isLast=(j == len(tr) - 1)))
            i = j + 1
    return out


def sec_silent(M):
    rows = silent_rows(M)
    print('零指令时段（日志 cmds 与 boats 计数连续 >=450 拍不变；日志照常每 90 拍打印 = 策略在跑、没有发出任何指令）')
    if not rows:
        print('   （没有）')
        return
    for r in rows:
        tail = f"，直到阵亡 t={r['deathT']}" if r['toDeath'] else ('，日志到此为止' if r['isLast'] else '')
        print(f"   {r['name']:14s} t={r['t0']}~{r['t1']}（{r['len']} 拍）nb {r['nbMin']}~{r['nbMax']} neut<={r['neutMax']}；密度 {r['dens0']:.0f}→{r['dens1']:.0f}（最高 {r['densMax']:.0f}；>100 的快照 {r['over100']} 个、>125 的 {r['over125']} 个）；"
              f"领土 {r['terr0']}→{r['terr1']}（最高 {r['terrMax']}）；兵 {fmt(r['bal0'])}→{fmt(r['bal1'])}{tail}")
    print(f"合计 {len(rows)} 段 {sum(r['len'] for r in rows)} 拍，涉及 {len({r['me'] for r in rows})} 个号")


# ------------------------------------------------------------------ seqlag
def seqlag_rows(M):
    """日志行号（全局递增的收集序号）对齐。lead[t] = 第一个打印本机拍 t 的行号。
    某号在行号 s 打印本机拍 t 时，「此刻最快的号已经到了哪一拍」= max{t' : lead[t'] <= s}；差 = 落后拍数。"""
    lead = {}
    for me, b in M.bots.items():
        for s in b.traj:
            if s['t'] not in lead or s['line'] < lead[s['t']]:
                lead[s['t']] = s['line']
    ticks = sorted(lead)
    # 让 lead 随 t 单调（后面的拍不可能比前面的拍更早被最快的号打印）
    out = defaultdict(list)
    for me, b in M.bots.items():
        for s in b.traj:
            best = s['t']
            for t in ticks:
                if t > s['t'] and lead[t] <= s['line']:
                    best = max(best, t)
            out[me].append((s['t'], best - s['t']))
    return out


def sec_seqlag(M):
    L = seqlag_rows(M)
    print('日志序号对齐：某号打印本机拍 t 的那一刻，最快的号已经打印到哪一拍；差 = 落后拍数（快照每 90 拍一个，所以分辨率是 90 拍）')
    for me in sorted(L):
        b = M.bots[me]
        rows = [(t, d) for t, d in L[me] if d >= 90]
        mx = max((d for _, d in L[me]), default=0)
        if not rows:
            continue
        print(f"   {name_of(b):14s} 最大落后 {mx:4d} 拍；落后 >=90 拍的快照：" + ' '.join(f"{t}:-{d}" for t, d in rows[:24]) + (' …' if len(rows) > 24 else ''))
    tot = sum(1 for me in L for _, d in L[me] if d >= 90)
    print(f"合计：落后 >=90 拍的快照 {tot} 个 / 全部快照 {sum(len(v) for v in L.values())} 个；涉及 {sum(1 for me in L if any(d >= 90 for _, d in L[me]))} 个号")


# ------------------------------------------------------------------ overcap
def rate_nocap(t, terr, land):
    i = (511 * terr) // max(1, land)
    r = 100 + isqrt(25600 * i // 508)
    if t < 1920:
        r = max((100 * (13440 - 6 * t)) // 1920, r)
    return r


def overcap_rows(M):
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        if not tr:
            continue
        lost = got = 0
        n100 = sum(1 for s in tr if s['dens'] > 100)
        n125 = sum(1 for s in tr if s['dens'] > 125)
        n149 = sum(1 for s in tr if s['dens'] >= 149)
        spans = []
        for a, c in zip(tr, tr[1:]):
            if c['t'] - a['t'] > 180:
                continue
            steps = max(1, (c['t'] - a['t']) // 10)
            for k in range(steps):
                f = (k + 0.5) / steps
                bal = a['bal'] + (c['bal'] - a['bal']) * f
                terr = a['terr'] + (c['terr'] - a['terr']) * f
                t = a['t'] + (c['t'] - a['t']) * f
                r0 = rate_nocap(int(t), int(terr), M.land)
                r1 = interest_rate(int(t), int(terr), M.land, int(bal))
                got += bal * r1 / 10000
                lost += bal * (r0 - r1) / 10000
        i = 0
        while i < len(tr):
            if tr[i]['dens'] > 100:
                j = i
                while j + 1 < len(tr) and tr[j + 1]['dens'] > 100:
                    j += 1
                spans.append((tr[i]['t'], tr[j]['t'], max(s['dens'] for s in tr[i:j + 1])))
                i = j + 1
            else:
                i += 1
        if n100:
            out.append(dict(me=me, name=name_of(b), n=len(tr), n100=n100, n125=n125, n149=n149, lost=int(lost), got=int(got), spans=spans))
    return out


def sec_overcap(M):
    rows = overcap_rows(M)
    print('超软上限（日志快照密度 > 100）。少拿利息 = 按引擎利率公式（超过 100×领土后利率按超出比例的 2 倍递减）在相邻快照间线性插值估算')
    if not rows:
        print('   （没有）')
    for r in rows:
        sp = ' '.join(f"{a}~{b}(最高{d:.0f})" for a, b, d in r['spans'][:12])
        print(f"   {r['name']:14s} 快照 {r['n']} 个：密度>100 的 {r['n100']} 个、>125 的 {r['n125']} 个、>=149 的 {r['n149']} 个；估算实得利息 {fmt(r['got'])}、少拿 {fmt(r['lost'])}｜{sp}")


# ------------------------------------------------------------------ drop30
def drop30_rows(M):
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        for a, c in zip(tr, tr[1:]):
            if a['bal'] < 1000 or c['bal'] > 0.7 * a['bal']:
                continue
            lab = []
            if c['terr'] < 0.9 * a['terr']:
                lab.append('丢地')
            if c['terr'] > 1.01 * a['terr']:
                lab.append('得地')
            if c['boats'] > a['boats']:
                lab.append(f"发船{c['boats'] - a['boats']}")
            dn = [e for e in b.donations if a['t'] < e['t'] <= c['t']]
            if dn:
                lab.append(f"捐款日志{len(dn)}")
            if c['cmds'] > a['cmds']:
                lab.append(f"指令{c['cmds'] - a['cmds']}")
            if not lab:
                lab.append('无指令无丢地')
            out.append(dict(me=me, name=name_of(b), t0=a['t'], t1=c['t'], bal0=a['bal'], bal1=c['bal'], drop=1 - c['bal'] / a['bal'],
                            terr0=a['terr'], terr1=c['terr'], dens0=a['dens'], dens1=c['dens'], nb=a['nb'], labels=lab,
                            cls=('丢地' if '丢地' in lab else '发船' if any(x.startswith('发船') for x in lab) else '捐款' if dn else '出兵' if c['cmds'] > a['cmds'] or '得地' in lab else '其他')))
    return out


def sec_drop30(M):
    rows = drop30_rows(M)
    print(f"全量 DROP30（相邻快照余额跌 >=30%，起点余额 >=1000）：{len(rows)} 次")
    by = defaultdict(int)
    for r in rows:
        by[r['cls']] += 1
    print('   日志侧归类（优先级：丢地 > 发船 > 捐款日志 > 出兵/得地 > 其他）：' + '，'.join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))
    for r in rows:
        print(f"   {r['name']:14s} t={r['t0']}~{r['t1']} 兵 {fmt(r['bal0'])}→{fmt(r['bal1'])}（-{100 * r['drop']:.0f}%）领土 {r['terr0']}→{r['terr1']} 密度 {r['dens0']:.0f}→{r['dens1']:.0f} nb={r['nb']}｜{'、'.join(r['labels'])}")


# ------------------------------------------------------------------ wall
TICK_S = 0.056


def wall_rows(M):
    """results.csv 每行有 tick 和 seconds（进房后秒数）。阵亡/终局行的 tick 是本机拍（那一拍本机才知道自己死了），
    用它们拟合 seconds = a + 0.056×tick；残差小 = 这些时刻本机没有落后。
    然后对每条结算行：按落盘行号找出其它号在它前后最近打印的快照 → 那一刻各号本机拍；服务器拍 = (seconds − a)/0.056。"""
    rs = [r for r in M.results if r.get('seconds') is not None]
    fit = [r for r in rs if r['event'] in ('died', 'end') and r['tick']]
    if len(fit) < 2:
        return None
    # 取 a 的最小值：落后只会让 seconds 偏大，最小的 a 最接近「不落后」
    offs = sorted(r['seconds'] - TICK_S * r['tick'] for r in fit)
    a = offs[0]
    rl = {x['name']: x['line'] for x in M.results_log}
    snaps = []
    for me, b in M.bots.items():
        for s in b.traj:
            snaps.append((s['line'], s['t'], me))
    snaps.sort()
    out = []
    for r in rs:
        line = rl.get(r['bot'])
        srv = (r['seconds'] - a) / TICK_S
        near = []
        if line is not None:
            last_before = {}
            first_after = {}
            for ln, t, me in snaps:
                if ln < line:
                    last_before[me] = (ln, t)
                elif me not in first_after:
                    first_after[me] = (ln, t)
            for me in sorted(set(last_before) | set(first_after)):
                lb = last_before.get(me)
                fa = first_after.get(me)
                if lb and fa and fa[0] - line <= 40 and line - lb[0] <= 40:
                    near.append((me, lb[1], fa[1]))
        out.append(dict(bot=r['bot'], me=r['meId'], event=r['event'], tick=r['tick'], seconds=r['seconds'], line=line, serverTick=srv,
                        resid=r['seconds'] - a - TICK_S * r['tick'], near=near))
    # 日志停掉的号：最后一条快照的行号落在哪两条结算行之间
    marks = sorted((x['line'], x['bot'], x['serverTick']) for x in out if x['line'] is not None)
    silent = []
    for me, b in sorted(M.bots.items()):
        if b.result or not b.traj:
            continue
        s = b.traj[-1]
        prev = [m for m in marks if m[0] < s['line']]
        nxt = [m for m in marks if m[0] > s['line']]
        silent.append(dict(me=me, name=name_of(b), lastT=s['t'], line=s['line'], before=nxt[0] if nxt else None, after=prev[-1] if prev else None))
    return dict(a=a, offs=offs, rows=out, silent=silent)


def sec_wall(M):
    W = wall_rows(M)
    if not W:
        print('结算行不足，拟合不了')
        return
    print(f"墙上时钟对表：阵亡/终局行拟合 seconds = a + 0.056×tick，a = {W['a']:.1f} 秒（各行的 seconds − 0.056×tick：" + ' '.join(f"{x:.1f}" for x in W['offs']) + '）')
    print('   服务器拍 = (seconds − a)/0.056（seconds 是整秒，误差 ±18 拍）。「当时各号本机拍」= 这条结算行落盘前/后各号最近一条快照的拍号')
    for r in W['rows']:
        near = '；'.join(f"{name_of(M.bots[me])} {t0}~{t1}" for me, t0, t1 in r['near'])
        lo = [t0 for _, t0, _ in r['near']]
        hi = [t1 for _, _, t1 in r['near']]
        lag = f"；本机落后服务器约 {r['serverTick'] - max(hi):.0f}~{r['serverTick'] - min(lo):.0f} 拍" if r['near'] and r['event'] == 'left' else ''
        print(f"   {r['bot']:12s} {r['event']:5s} 结算 tick={r['tick']} seconds={r['seconds']} → 服务器拍≈{r['serverTick']:.0f}（残差 {r['resid']:+.1f} 秒）{lag}")
        if r['event'] == 'left' and near:
            print(f"        当时各号本机拍：{near}")
    if W['silent']:
        print('日志停掉、也没有结算行的号（最后一条快照落在哪两条结算行之间）：')
        for s in W['silent']:
            af = f"{s['after'][1]} 之后" if s['after'] else '第一条结算行之前'
            bf = f"{s['before'][1]}（服务器拍≈{s['before'][2]:.0f}）之前" if s['before'] else '最后一条结算行之后'
            print(f"   {s['name']:14s} 最后快照 本机拍 {s['lastT']}（行号 {s['line']}）：{af}、{bf}")

# ------------------------------------------------------------------ oplag / issued（需要录像真值）
def oplag_rows(M):
    S = M.sim
    if not S:
        return None
    cm = defaultdict(list)
    for c in S['squadCmds']:
        if c['k'] == 'atk' and c['raw'] == 512:
            cm[c['p']].append(c)
    out = {}
    for me, b in sorted(M.bots.items()):
        used = set()
        rows = []
        for o in b.opening:
            pct = max(0, min(1023, math.ceil(o['spend'] * 1024 / max(1, o['bal'])) - 1))
            hit = None
            for i, c in enumerate(cm[me]):
                if i in used or c['t'] < o['t']:
                    continue
                if c['pct'] == pct:
                    hit = (i, c)
                    break
            if hit:
                used.add(hit[0])
                rows.append((o['t'], hit[1]['t'] - o['t']))
            else:
                rows.append((o['t'], None))
        out[me] = rows
    return out


def sec_oplag(M):
    R = oplag_rows(M)
    if R is None:
        print('没有录像真值（先跑 run_truth.sh）')
        return
    print('开局无主地指令：下令拍（HL-OPENING 的 t）→ 进录像的执行拍，相差多少拍（x = 录像范围内没找到同百分比的指令）')
    buckets = defaultdict(list)
    for me, rows in R.items():
        b = M.bots[me]
        print(f"   {name_of(b):14s} " + ' '.join(f"{t}:{'x' if d is None else d}" for t, d in rows))
        for t, d in rows:
            if d is not None:
                buckets[min(7, t // 100)].append(d)
    print('   按下令拍分段的延迟中位数 / 最大值：' + '；'.join(f"{'t>=700' if k == 7 else f't={k * 100}~{k * 100 + 99}'} 中位 {sorted(v)[len(v) // 2]} 最大 {max(v)}（{len(v)} 条）" for k, v in sorted(buckets.items())))


def issued_rows(M):
    S = M.sim
    if not S:
        return None
    last = S['endT']
    cm = defaultdict(list)
    for c in S['squadCmds']:
        if c['k'] in ('atk', 'boat', 'boatAdd', 'retreat'):
            cm[c['p']].append(c['t'])
    for x in S.get('donations', []):
        if x.get('ok'):
            cm[x['from']].append(x['t'])
    out = []
    for me, b in sorted(M.bots.items()):
        snaps = [s for s in b.traj if s['t'] <= last]
        if not snaps:
            continue
        rows = []
        for s in snaps:
            rows.append((s['t'], s['cmds'], sum(1 for t in cm[me] if t <= s['t'])))
        s = snaps[-1]
        rep = sum(1 for t in cm[me] if t <= s['t'])
        out.append(dict(me=me, name=name_of(b), t=s['t'], issued=s['cmds'], inReplay=rep, lastCmdT=max(cm[me]) if cm[me] else None, series=rows))
    return out


def sec_issued(M):
    R = issued_rows(M)
    if R is None:
        print('没有录像真值（先跑 run_truth.sh）')
        return
    print(f"日志 cmds 计数（策略自己数的已发指令）vs 录像里该号到同一拍为止的指令条数（录像到 t={M.sim['endT']}）")
    for r in R:
        ser = ' '.join(f"{t}:{a}/{b}" for t, a, b in r['series'] if t >= 600)
        print(f"   {r['name']:14s} 末快照 t={r['t']}：已发 {r['issued']} 条，录像里 {r['inReplay']} 条（差 {r['issued'] - r['inReplay']}）；录像里最后一条 t={r['lastCmdT']} ｜{ser}")
    ti = sum(r['issued'] for r in R)
    tr = sum(r['inReplay'] for r in R)
    print(f"合计：已发 {ti} 条，录像里 {tr} 条（{100 * tr / max(1, ti):.1f}%）")


def build_json(M):
    doc = dict(matchId=M.id, stale=stale_rows(M), silent=silent_rows(M), drop30=drop30_rows(M), wall=wall_rows(M), overcap=overcap_rows(M))
    L = seqlag_rows(M)
    doc['seqlag'] = {str(me): dict(maxLag=max((d for _, d in v), default=0), lagSnaps=sum(1 for _, d in v if d >= 90), snaps=len(v)) for me, v in L.items()}
    o = oplag_rows(M)
    if o is not None:
        doc['oplag'] = {str(me): rows for me, rows in o.items()}
        doc['issued'] = [{k: v for k, v in r.items() if k != 'series'} for r in issued_rows(M)]
    return doc


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mid, sec = sys.argv[1], sys.argv[2]
    M = load_match(mid)
    if sec == 'stale':
        sec_stale(M)
    elif sec == 'silent':
        sec_silent(M)
    elif sec == 'seqlag':
        sec_seqlag(M)
    elif sec == 'drop30':
        sec_drop30(M)
    elif sec == 'wall':
        sec_wall(M)
    elif sec == 'overcap':
        sec_overcap(M)
    elif sec == 'oplag':
        sec_oplag(M)
    elif sec == 'issued':
        sec_issued(M)
    elif sec == 'json':
        doc = build_json(M)
        doc['matchId'] = mid
        os.makedirs(os.path.join(OUT, mid), exist_ok=True)
        p = os.path.join(OUT, mid, 'logdigest.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
