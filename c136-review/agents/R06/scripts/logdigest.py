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
  donlog [号|-1]  没有录像时的捐款账：每条 HL-DONATE 按捐款方自己后面的余额读数判「执行了 / 没执行 / 判不了」，
            估手续费与到账，按「谁→谁」汇总；没执行的给日志侧原因（对方顶在硬上限 / 配额不够 / 不同队 / 已阵亡）。带号 = 打印与该号有关的逐条，-1 = 全部
  donval    有整局录像的局：把 donlog 这本只靠日志的账和录像真值对表（执行与否的一致率、到账估算的误差）
  cmdmix    指令构成：按时段把每个号 cmds 计数的增量拆成 捐款日志 / 协防戳日志 / 其余（出兵、发船等）
  idleloss  丢地间隔账：相邻快照在丢地的间隔里，有多少是「一条出兵/发船指令都没发」、其中多少起点密度已过 100；连续段列表
  spend [t0 t1]  兵去哪了：相邻快照间的净支出按「这段里发了什么指令」分账（无指令 / 只捐款 / 只协防戳 / 只出兵或发船 / 混合）
  fireband [t0 [t1]] [名字...]  有可打的邻居时（日志 nb>=1：非同队、非编队的邻居，真人还是内置 AI 日志分不清）按密度档数「这 90 拍里发没发出兵/发船指令」「是不是在丢地」
  capidle   满仓不动 → 被吃：连续 >=600 拍零指令且密度到过 >=140，段内或之后 600 拍领土跌掉 25% 以上或阵亡
  freezebound [t0]  满仓（密度>100）、有可打的邻居（nb>=1）、这 90 拍没有出兵/发船：按 c110 buyLand 超软上限分支反推「邻居是真人时，最强敌邻至少多少兵」（代码反推，不是实测）
  quotacap [收款人领土]  引擎受捐额度公式在本图上的封顶：各拍的上限点数、单笔最多到账、每 100 拍新增额度够收多少
  foes      协防戳日志里点名的外人：被它打的号、戳它的号 → 它不可能在哪些队
  assists [t0 t1]  协防戳日志按「谁替谁戳谁」计数（可限定拍范围），并列出同一范围内每个号的 cmds 增量
  opening   HL-OPENING 行：每个号的条数、拍范围、相邻两条的间隔（中位 / p10 / p90）
  peace     HL-PEACE 行：谁在哪一拍发起 / 投票、当时日志里的 teamLand，以及同一拍别的队里还在场的我方号
  oplag     开局指令「下令拍 → 进录像的执行拍」的延迟（HL-OPENING 的 t 与录像里同一条无主地指令的拍；需要录像）
  issued    日志 cmds 计数（策略自己数的已发指令）与录像里该号的指令条数（需要录像）
  bursts [t0]  便宜的集中出手（NEW:AT-cheap-burst）的机械判定：一个间隔内 >=3 条出兵/发船、两个间隔领土 +25%、每格 <80 兵、600 拍后仍 >=1.2 倍；起点 t>=t0（默认 630；模式实例取 1440）
  boxboats  被围发船：nb=0 且 neut=0 时发的船，500 拍内领土涨没涨（>=1.5 倍 = NEW:BT-boxed-breakout；<1.05 倍 = 没换到地）
  harvest [t0]  邻居崩盘后收地（NEW:AT-collapse-harvest）：t>=t0（默认 630）相邻快照 neut 从 0 变成 >=8，270 拍内领土 >=1.2 倍
  crumb     开局期被零星无主地卡住（NEW:OP-neutral-crumb-lock）：t<1500 连续 >=270 拍 neut>0、零指令、领土不变
  thinbig   又大又薄（NEW:EC-thin-big-target）的机械判定：密度 <12 连续 >=450 拍、领土到过在场我方号中位 2 倍且 nb>=1、到顶后 300 拍内跌 >=40%
  wallms    同 wall，但用结算行的毫秒时间戳 at（误差 ±1 拍）：每条结算行落盘时，其余在场号的日志打到了哪一拍
  noeffect [t0]  发了令却没有任何支出的间隔（NEW:IO-cmd-blackout 的日志侧判据）
  noefftl [t0 t1]  「发令不见效 / 清仓 / 超发」按 90 拍一档的时间分布：是不是全编队同时发生
  gaps      缺掉的 HL-TICK 快照（首尾快照之间拍号是 90 的倍数却没有打印）
  sentchk   结算行的 sent / accepted（外层数的发出 / 被收下的指令条数，含选点）对 策略 cmds + 日志 HL-SPAWN 行数：cmds 计数有没有漏数
  zerodrop [t0 t1]  零新令的余额下跌：cmds、boats 都没动、领土没丢，而余额 < 纯利息预测 × 0.75 → 更早发的指令到这一段才生效，给出发令到见效的拍数上下界
  json      以上汇总写 out/<id>/logdigest.json
所有阈值都写在函数开头的常量里。
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match, interest_rate, isqrt, quota_limit, quota_points, donation_truth  # noqa: E402

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
    lagw = lag_window(M)
    if lagw:
        early = [r for r in real if r['tDump0'] <= lagw[1] + 360]
        if early:
            print(f"   其中清仓发生在本机落后窗口（t={lagw[0]}~{lagw[1]}）结束后 360 拍以内的 {len(early)} 段、{len({r['me'] for r in early})} 个号（{'、'.join(r['name'] for r in early)}）："
                  f"清掉的兵 {fmt(sum(r['balBefore'] - r['balAfter'] for r in early))}，清仓后 2 个快照内领土合计 {sum(max(r['terrAfter'], r['terrNext']) - r['terrBefore'] for r in early):+d} 格"
                  f"（只算下一个快照 {sum(r['terrAfter'] - r['terrBefore'] for r in early):+d}、再下一个 {sum(r['terrNext'] - r['terrBefore'] for r in early):+d}）；"
                  f"清仓后密度 <=12 的 {sum(1 for r in early if r['densAfter'] <= 12)} 个，其中 300 拍内阵亡 {sum(1 for r in early if r['deathT'] and r['deathT'] - r['tDump1'] <= 300)} 个")
            pre = [r for r in early if r['cmdsRun'] > 0]
            nop = [r for r in early if r['cmdsRun'] == 0]
            print(f"   这 {len(early)} 段里清仓前有「发令不见效」前段的 {len(pre)} 段（{'、'.join('%s %d 条' % (r['name'], r['cmdsRun']) for r in pre)}）：清掉 {fmt(sum(r['balBefore'] - r['balAfter'] for r in pre))}；"
                  f"没有前段的 {len(nop)} 段（{'、'.join('%s 间隔内 %d 条、k=%.1f' % (r['name'], r['cmdsDump'], r['implied']) for r in nop)}）：清掉 {fmt(sum(r['balBefore'] - r['balAfter'] for r in nop))}")
            t_ref = lagw[1] + 450
            alive = []
            for r in early:
                snap = [x for x in M.bots[r['me']].traj if x['t'] == t_ref]
                if snap:
                    alive.append((r, snap[0]['terr']))
            if alive:
                parts = '、'.join("%s %+d" % (r['name'], v - r['terrBefore']) for r, v in alive)
                print(f"   到 t={t_ref}：这些号里还有快照的 {len(alive)} 个，领土比清仓前合计 {sum(v - r['terrBefore'] for r, v in alive):+d} 格（{parts}）")
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


def lag_window(M):
    """落后 >=90 拍的快照所在的本机拍范围 (t_min, t_max)；没有则 None。"""
    L = seqlag_rows(M)
    ts = [t for me in L for t, d in L[me] if d >= 90]
    return (min(ts), max(ts)) if ts else None


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
    w = lag_window(M)
    if w:
        print(f"   落后的快照都在本机拍 t={w[0]}~{w[1]}")
    slow = [(t, ms) for b in M.bots.values() for t, ms in b.slow]
    snaps = [x for b in M.bots.values() for x in b.traj]
    if snaps:
        in_w = sum(1 for t, _ in slow if w and w[0] <= t <= w[1])
        print(f"   策略自己的耗时：HL-SLOW-TICK {len(slow)} 行" + (f"（{min(ms for _, ms in slow):.1f}~{max(ms for _, ms in slow):.1f} 毫秒，t={min(t for t, _ in slow)}~{max(t for t, _ in slow)}，其中落后窗口内 {in_w} 行）" if slow else '')
              + f"；HL-TICK 快照里 avgMs 最大 {max((x.get('avgMs') or 0) for x in snaps):.1f}、maxMs 最大 {max((x.get('maxMs') or 0) for x in snaps):.1f}、skip 最大 {max((x.get('skip') or 0) for x in snaps):.0f}")


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
    if rows:
        print(f"合计（只列出过软上限的 {len(rows)} 个号）：估算实得利息 {fmt(sum(r['got'] for r in rows))}、少拿 {fmt(sum(r['lost'] for r in rows))}；"
              f"密度>100 的快照 {sum(r['n100'] for r in rows)} 个 / {sum(r['n'] for r in rows)} 个")


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

# ------------------------------------------------------------------ wallms（结算行的毫秒时间戳 at → 服务器拍；对照那一刻各号日志打到哪一拍）
def _at_s(r):
    """results.csv 的 at（ISO，毫秒）→ 当天秒数。跨零点的局不处理（本批 15 局没有）。"""
    m = re.search(r'T(\d\d):(\d\d):(\d\d)(?:\.(\d+))?Z', r.get('at') or '')
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + (float('0.' + m.group(4)) if m.group(4) else 0.0)


def wallms_rows(M):
    """拟合 at = A + 0.056×tick（A 取阵亡行里的最小值：写结算行只会晚、不会早）。
    每条结算行：服务器拍 = (at − A)/0.056；按落盘行号取每个号在这条结算行之前最后一条、之后第一条 HL-TICK 快照的拍号。
    「日志位置落后」= 服务器拍 − 之后第一条快照拍（下界）~ 服务器拍 − 之前最后一条快照拍（上界）。
    快照 90 拍一条，所以不落后时下界应在 −90~0、上界在 0~90。日志是否实时落盘无法单独验证：恒定的偏移也可能是落盘延迟。"""
    rs = [r for r in M.results if _at_s(r) is not None]
    fit = [r for r in rs if r['event'] == 'died' and r['tick']]
    if len(fit) < 2:
        return None
    A = min(_at_s(r) - TICK_S * r['tick'] for r in fit)
    rl = {x['name']: x['line'] for x in M.results_log}
    out = []
    for r in rs:
        line = rl.get(r['bot'])
        srv = (_at_s(r) - A) / TICK_S
        before, after = {}, {}
        if line is not None:
            for me, b in M.bots.items():
                for s in b.traj:
                    if s['line'] < line:
                        before[me] = s['t']
                    elif me not in after:
                        after[me] = s['t']
        both = [me for me in before if me in after and after[me] - before[me] <= 180]
        out.append(dict(bot=r['bot'], me=r['meId'], event=r['event'], tick=r['tick'], serverTick=srv, resid=_at_s(r) - A - TICK_S * r['tick'], line=line,
                        before=sorted(before[me] for me in both), after=sorted(after[me] for me in both), n=len(both)))
    return dict(A=A, rows=out)


def sec_wallms(M):
    W = wallms_rows(M)
    if not W:
        print('结算行不足（或没有 at 时间戳），拟合不了')
        return
    a = W['A']
    print(f"毫秒对表：阵亡行拟合 at = A + 0.056×tick，A = {int(a // 3600):02d}:{int(a % 3600 // 60):02d}:{a % 60:06.3f}（取最小值）。服务器拍 = (at − A)/0.056")
    print('   每条结算行：结算 tick｜服务器拍（残差秒 = 写结算行比 tick 晚多少）｜这条结算行落盘时，其余在场号日志里「之前最后一条 / 之后第一条」快照的拍号范围｜日志位置落后（服务器拍 − 之后第一条 ~ 服务器拍 − 之前最后一条，取各号中位）')
    lows, highs = [], []
    for r in W['rows']:
        if not r['n']:
            print(f"   {r['bot']:12s} {r['event']:5s} tick={r['tick']:5d}｜服务器拍≈{r['serverTick']:.0f}（残差 {r['resid']:+.2f} 秒）｜没有同时在场、快照连续的号")
            continue
        mb, ma = r['before'][len(r['before']) // 2], r['after'][len(r['after']) // 2]
        # 阵亡/终局行的 tick 本身就是「本机拍」：本机知道自己死了的那一拍
        lo, hi = r['serverTick'] - ma, r['serverTick'] - mb
        if r['event'] == 'died':
            lows.append(lo)
            highs.append(hi)
        print(f"   {r['bot']:12s} {r['event']:5s} tick={r['tick']:5d}｜服务器拍≈{r['serverTick']:.0f}（残差 {r['resid']:+.2f} 秒）｜{r['n']} 个号 之前 {r['before'][0]}~{r['before'][-1]}（中位 {mb}） / 之后 {r['after'][0]}~{r['after'][-1]}（中位 {ma}）"
              f"｜落后 {lo:+.0f} ~ {hi:+.0f} 拍")
    if lows:
        lows.sort()
        highs.sort()
        print(f"   阵亡行合计 {len(lows)} 条：落后下界 中位 {lows[len(lows) // 2]:+.0f}（最小 {lows[0]:+.0f}、最大 {lows[-1]:+.0f}）；上界 中位 {highs[len(highs) // 2]:+.0f}（最小 {highs[0]:+.0f}、最大 {highs[-1]:+.0f}）")
        print('   读法：下界 > 0 = 这条结算行写下时，别的号连「下一条」快照都还没打到服务器拍，即日志位置至少落后这么多拍；它可能是本机真的落后，也可能是日志晚落盘，日志自己分不开')


# ------------------------------------------------------------------ donlog（没有录像时的捐款账：只靠捐款方自己的余额读数）
DON_NOEXEC = 0.99    # 下一条余额读数 >= 「只涨利息」预测 × 0.99 → 这一段里没有任何支出（这条捐款没被执行，手续费也没扣）
DON_SPEND = 0.955    # 下一条余额读数 <= 预测 × 0.955 → 这一段里有支出（一笔捐款光手续费就是余额的 6.25%）
DON_LATE = 45        # 支出出现在后一段时，离下令拍不超过这么多拍才记到这条捐款头上
CAP_DENS = 148.0     # 收款方相邻快照密度 >= 这个值 → 当时顶在 150 倍领土的硬上限附近，装不进


def terr_at(b, t):
    """HL-TICK 快照之间线性插值的领土。"""
    prev = None
    for s in b.traj:
        if s['t'] <= t:
            prev = s
        else:
            if prev is None:
                return s['terr']
            w = (t - prev['t']) / max(1, s['t'] - prev['t'])
            return int(round(prev['terr'] + w * (s['terr'] - prev['terr'])))
    return prev['terr'] if prev else 0


def grow(bal, t0, t1, b, land):
    """t0→t1 之间没有任何指令生效时余额怎么走：t%10==9 结利息（引擎 E1/E9），t%100==99 加领土收入（E2/E10），都不超过 150 倍领土。"""
    x = bal
    for k in range(t0, t1):
        if k % 10 == 9:
            terr = terr_at(b, k)
            cap = 150 * terr
            if x < cap:
                x = min(cap, x + max(1, min(700, interest_rate(k, terr, land, x)) * x // 10000))
            if k % 100 == 99 and x < cap:
                x = min(cap, x + terr)
    return x


def snap_around(b, t):
    """t 前后各一条快照（没有就 None）。"""
    before = after = None
    for s in b.traj:
        if s['t'] <= t:
            before = s
        elif after is None:
            after = s
            break
    return before, after


def donlog_rows(M):
    """每条 HL-DONATE 日志 → 执行了没有（估）。
    读数 = 捐款方自己的 HL-DONATE 的 myBal 和 HL-TICK 的 bal；相邻两条读数之间按引擎利息公式推「没有支出」的余额，
    实际读数明显更低 = 这一段有支出。支出记到这一段起点那条捐款头上（起点不是捐款日志时记到之前 DON_LATE 拍内最近一条还没记账的捐款）。
    一段的支出比「手续费 + 最多到账」还多 5% 以上时，再往前找一条没记账的捐款一起分。
    同一段里有协防戳日志、或 cmds 计数显示还有别的指令 → 标「混」（金额不干净，只算条数）。
    到账（估）= min(滑杆想给的, 支出 − 手续费)；支出比「手续费 + 想给的」还多出来的部分记 extra（同一段里挨打掉的兵等，不是捐款）。"""
    land = M.land
    rows = []
    for me, b in sorted(M.bots.items()):
        if not b.donations:
            continue
        dons = sorted(b.donations, key=lambda e: e['t'])
        reads = {}
        for s in b.traj:
            reads[s['t']] = dict(t=s['t'], bal=s['bal'], don=None)
        for i, e in enumerate(dons):
            reads[e['t']] = dict(t=e['t'], bal=e['myBal'], don=i)
        rd = [reads[t] for t in sorted(reads)]
        st = [dict(e=e, i=i, exec=None, spend=0, mixed=False, shared=1) for i, e in enumerate(dons)]
        for a, c in zip(rd, rd[1:]):
            pred = grow(a['bal'], a['t'], c['t'], b, land)
            ratio = c['bal'] / max(1, pred)
            spend = pred - c['bal']
            cand = [x for x in st if x['exec'] is None and x['e']['t'] <= a['t'] and a['t'] - x['e']['t'] <= DON_LATE]
            # 收款人在这一段开始之前已经阵亡（结算行的阵亡拍）：这一段的支出不可能是给它的那条捐款
            for x in cand:
                rb0 = M.bots.get(x['e']['to'])
                dt0 = death_tick(rb0) if rb0 else None
                if dt0 is not None and dt0 <= a['t']:
                    x['exec'] = False
            cand = [x for x in cand if x['exec'] is None]
            if ratio >= DON_NOEXEC:
                # 这一段没有支出：起点那条捐款若到这一段结束已经过了 DON_LATE 拍，就定为没执行
                for x in cand:
                    if c['t'] - x['e']['t'] > DON_LATE:
                        x['exec'] = False
                continue
            if ratio > DON_SPEND or not cand:
                for x in cand:
                    if c['t'] - x['e']['t'] > DON_LATE:
                        x['exec'] = False
                continue
            x = cand[-1]
            asst = [y for y in b.assists if a['t'] <= y['t'] < c['t']]
            s1, _ = snap_around(b, x['e']['t'])
            _, s2 = snap_around(b, c['t'] - 1)
            other = None
            if s1 and s2:
                logged = sum(1 for y in dons if s1['t'] <= y['t'] < s2['t']) + sum(1 for y in b.assists if s1['t'] <= y['t'] < s2['t'])
                other = (s2['cmds'] - s1['cmds']) - logged + (s2['boats'] - s1['boats'])
            B = x['e']['myBal']
            fee = (64 * B) // 1024
            vmax = min((B * (x['e']['pct'] + 1)) // 1024, B - fee)
            x['exec'] = True
            x['spend'] = spend
            x['mixed'] = bool(asst) or (other is not None and other > 0)
            x['other'] = other
            if spend > 1.05 * (fee + vmax) and len(cand) >= 2 and not x['mixed']:
                y = cand[-2]
                y['exec'] = True
                y['shared'] = x['shared'] = 2
                y['spend'] = x['spend'] = spend // 2
                y['mixed'] = False
                y['other'] = other
            for z in cand:
                if z['exec'] is None and c['t'] - z['e']['t'] > DON_LATE:
                    z['exec'] = False
        for x in st:
            e = x['e']
            B = e['myBal']
            fee = (64 * B) // 1024
            vmax = min((B * (e['pct'] + 1)) // 1024, B - fee)
            rb = M.bots.get(e['to'])
            before = after = None
            if rb:
                before, after = snap_around(rb, e['t'])
            room = None
            capped = False
            if before:
                room = 150 * before['terr'] - before['bal']
                capped = before['dens'] >= CAP_DENS and (after is None or after['dens'] >= CAP_DENS)
            dead = bool(rb and death_tick(rb) is not None and death_tick(rb) <= e['t'])
            husk = is_husk(rb, e['t'])
            rows.append(dict(me=me, name=name_of(b), t=e['t'], kind=e['kind'], pct=e['pct'], to=e['to'], toName=e['toName'], bal=B, dMe=e['dMe'],
                             fee=fee, vmax=vmax, exec=x['exec'], spend=x['spend'], mixed=x['mixed'], shared=x['shared'], other=x.get('other'),
                             delivered=(min(vmax, max(0, x['spend'] - fee)) if x['exec'] and not x['mixed'] else None),
                             extra=(max(0, x['spend'] - fee - vmax) if x['exec'] and not x['mixed'] else None),
                             recvDens=(before['dens'] if before else None), recvDensAfter=(after['dens'] if after else None),
                             recvTerr=(before['terr'] if before else None), recvRoom=room, recvCapped=capped, recvDead=dead, recvHusk=husk,
                             sameTeam=(rb.team == b.team if rb and rb.team and b.team else None)))
    # 配额账（t<4284 才检查；只数得到「号给号」的捐款，外人给的看不见 → 已用点数是下限）
    used = defaultdict(int)
    for r in sorted(rows, key=lambda r: r['t']):
        r['quotaLimit'] = quota_limit(r['t']) if r['t'] < 4284 else None
        r['quotaUsed'] = used[r['to']] if r['t'] < 4284 else None
        want = r['vmax'] if r['recvRoom'] is None else max(0, min(r['vmax'], r['recvRoom']))
        r['quotaNeed'] = quota_points(r['t'], want, M.land, r['recvTerr'] or 1) if r['t'] < 4284 else None
        if r['exec'] and r['t'] < 4284:
            v = r['delivered'] if r['delivered'] is not None else want
            used[r['to']] += quota_points(r['t'], v, M.land, r['recvTerr'] or 1)
        # 第二种估法（引擎规则）：到账 = min(滑杆想给的, 对方离 150×领土硬上限的空间)；空间取对方在这条日志之前最近一条快照
        r['byRule'] = want if r['exec'] else None
        why = None
        if r['exec'] is False:
            if r['recvDead']:
                why = '对方已阵亡'
            elif r['sameTeam'] is False:
                why = '不同队'
            elif r['recvCapped'] or (r['recvRoom'] is not None and r['recvRoom'] <= 0):
                why = '对方顶在硬上限'
            elif r['quotaLimit'] is not None and r['quotaUsed'] + r['quotaNeed'] > r['quotaLimit']:
                why = '配额不够'
            else:
                why = '看不出'
        r['why'] = why
    return rows


PINGPONG_WIN = 150
HUSK_GAP = 180            # 收款人最后一条快照比这条捐款早多少拍以上，才算「页面已经停住」


def is_husk(rb, t):
    """NEW:DN-husk-donate / NEW:AS-poke-for-husk 的判据：这个号没有结算行（失联）或结算行是 left，
    而且它最后一条日志快照比 t 早 HUSK_GAP 拍以上（没有任何快照也算）。阵亡的号不算。"""
    if rb is None:
        return False
    r = rb.result
    if r and r.get('event') != 'left':
        return False
    last = rb.traj[-1]['t'] if rb.traj else None
    return last is None or t - last >= HUSK_GAP


def pingpong_pairs(rows, win=PINGPONG_WIN):
    ex = [r for r in rows if r['exec']]
    return [(a, b) for a in ex for b in ex if a['me'] == b['to'] and a['to'] == b['me'] and 0 < b['t'] - a['t'] <= win]


def sec_donlog(M, detail=None):
    rows = donlog_rows(M)
    n = len(rows)
    ex = [r for r in rows if r['exec']]
    no = [r for r in rows if r['exec'] is False]
    un = [r for r in rows if r['exec'] is None]
    clean = [r for r in ex if not r['mixed']]
    print(f"捐款日志账（只靠捐款方自己的余额读数，估）：日志 {n} 条 → 执行 {len(ex)}（其中金额干净 {len(clean)}、与别的指令混在一段 {len(ex) - len(clean)}）、没执行 {len(no)}、判不了 {len(un)}")
    print(f"   判据：相邻读数间按引擎利息推「没支出」的余额；实际 >= {DON_NOEXEC}× 记没执行，<= {DON_SPEND}× 记有支出；支出 − 手续费(6.25%) = 到账（估）")
    by = defaultdict(int)
    for r in no:
        by[r['why']] += 1
    print('   没执行的原因（日志侧）：' + '，'.join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))
    fee = sum(r['fee'] for r in ex)
    dl = sum(r['delivered'] for r in clean)
    feec = sum(r['fee'] for r in clean)
    worse = [r for r in clean if r['delivered'] < r['fee']]
    print(f"   执行的 {len(ex)} 条手续费合计 {fmt(fee)}；金额干净的 {len(clean)} 条：手续费 {fmt(feec)}、到账（估）{fmt(dl)}、按滑杆本来想给 {fmt(sum(r['vmax'] for r in clean))}")
    print(f"   到账 < 手续费的 {len(worse)} 条：手续费 {fmt(sum(r['fee'] for r in worse))}、到账 {fmt(sum(r['delivered'] for r in worse))}；干净段里超出「手续费+想给」的支出（挨打等，不算捐款）合计 {fmt(sum(r['extra'] for r in clean))}")
    w2 = [r for r in ex if r['byRule'] < r['fee']]
    low = [r for r in w2 if r['pct'] < 64]
    print(f"   第二种估法（引擎规则：到账 = min(想给, 对方离硬上限的空间)）：执行的 {len(ex)} 条到账 {fmt(sum(r['byRule'] for r in ex))}（干净的 {len(clean)} 条 {fmt(sum(r['byRule'] for r in clean))}）；"
          f"到账 < 手续费的 {len(w2)} 条：手续费 {fmt(sum(r['fee'] for r in w2))}、到账 {fmt(sum(r['byRule'] for r in w2))}（其中 pct<64 的 {len(low)} 条本来就是手续费比到账多；其余 {len(w2) - len(low)} 条是被对方的空间截掉的）")
    for r in sorted(w2, key=lambda r: -r['fee']):
        print(f"      {r['name']} t={r['t']} {r['kind']} pct={r['pct']} →{r['toName'][:12]}：余额 {r['bal']}、手续费 {r['fee']}、想给 {r['vmax']}、对方 {r['recvTerr']} 格 密度 {('%.0f' % r['recvDens']) if r['recvDens'] is not None else '?'}、空间 {r['recvRoom']}{'（混）' if r['mixed'] else ''}")
    pp = pingpong_pairs(rows)
    inv = {id(x): x for a, b_ in pp for x in (a, b_)}
    print(f"   反向配对（A→B 执行后 {PINGPONG_WIN} 拍内 B→A 也执行）：{len(pp)} 对，涉及 {len(inv)} 笔捐款，这些捐款的手续费合计 {fmt(sum(x['fee'] for x in inv.values()))}")
    for a, b_ in pp:
        print(f"      {a['name']}→{a['toName'][:12]} t={a['t']} pct={a['pct']} 手续费 {a['fee']}｜{b_['name']}→{b_['toName'][:12]} t={b_['t']} pct={b_['pct']} 手续费 {b_['fee']}")
    byteam = defaultdict(lambda: dict(n=0, ex=0, fee=0, rule=0))
    for r in rows:
        x = byteam[M.bots[r['me']].team]
        x['n'] += 1
        if r['exec']:
            x['ex'] += 1
            x['fee'] += r['fee']
            x['rule'] += r['byRule']
    print('   按捐款人所在队：' + '；'.join(f"队{k} 日志 {v['n']} 执行 {v['ex']} 手续费 {fmt(v['fee'])} 到账(第二种估法) {fmt(v['rule'])}" for k, v in sorted(byteam.items(), key=lambda kv: str(kv[0]))))
    hi = [r for r in ex if r['recvDens'] is not None and r['recvDens'] >= 100]
    lowp = [r for r in ex if r['pct'] < 150]
    print(f"   收款人收款前密度 >=100 的 {len(hi)} 条：手续费 {fmt(sum(r['fee'] for r in hi))}、到账(第二种估法) {fmt(sum(r['byRule'] for r in hi))}、想给 {fmt(sum(r['vmax'] for r in hi))}；"
          f"pct<150 的 {len(lowp)} 条（日志 {sum(1 for r in rows if r['pct'] < 150)} 条）：手续费 {fmt(sum(r['fee'] for r in lowp))}、到账(第二种估法) {fmt(sum(r['byRule'] for r in lowp))}；"
          f"pct<=63（按规则到账不高于手续费）的 {sum(1 for r in ex if r['pct'] <= 63)} 条（日志 {sum(1 for r in rows if r['pct'] <= 63)} 条）：手续费 {fmt(sum(r['fee'] for r in ex if r['pct'] <= 63))}、想给 {fmt(sum(r['vmax'] for r in ex if r['pct'] <= 63))}")
    hk = [r for r in rows if r['recvHusk']]
    hke = [r for r in hk if r['exec']]
    hkc = [r for r in hke if not r['mixed']]
    print(f"   给页面已停住/离开的席位（NEW:DN-husk-donate：收款人没有结算行或结算行是 left，且它最后一条快照比这条捐款早 >={HUSK_GAP} 拍）：日志 {len(hk)} 条、执行 {len(hke)} 条，"
          f"手续费 {fmt(sum(r['fee'] for r in hke))}；其中金额干净的 {len(hkc)} 条：手续费 {fmt(sum(r['fee'] for r in hkc))}、到账（估）{fmt(sum(r['delivered'] for r in hkc))}、想给 {fmt(sum(r['vmax'] for r in hkc))}")
    if hk:
        byk = defaultdict(list)
        for r in hk:
            byk[r['kind']].append(r)
        print('      按种类：' + '；'.join(f"{k} 日志 {len(v)} 执行 {sum(1 for r in v if r['exec'])} 手续费 {fmt(sum(r['fee'] for r in v if r['exec']))}" for k, v in sorted(byk.items())))
        byr = defaultdict(list)
        for r in hk:
            byr[r['to']].append(r)
        for to, v in sorted(byr.items(), key=lambda kv: -sum(r['fee'] for r in kv[1] if r['exec'])):
            rb = M.bots.get(to)
            last = rb.traj[-1] if rb and rb.traj else None
            ev = (rb.result.get('event') + f"@本机拍{rb.result.get('tick')}" if rb and rb.result else '没有结算行')
            e = [r for r in v if r['exec']]
            print(f"      →{v[0]['toName'][:12]:12s}（{ev}；最后快照 t={last['t'] if last else '-'} {last['terr'] if last else '-'} 格）：日志 {len(v)} 条、执行 {len(e)} 条、手续费 {fmt(sum(r['fee'] for r in e))}、"
                  f"到账（估，干净的 {sum(1 for r in e if not r['mixed'])} 条）{fmt(sum(r['delivered'] for r in e if not r['mixed']))}；t={min(r['t'] for r in v)}~{max(r['t'] for r in v)}；捐款人 {'、'.join(sorted({r['name'] for r in v}))}")
            da = sorted((x['t'], x['dAlly']) for ob in M.bots.values() for x in ob.donations if x['to'] == to and x.get('dAlly') is not None and is_husk(rb, x['t']))
            if da:
                print(f"         rescue 日志里捐款人看到的它的密度（dAlly）：{' '.join(f'{t}:{d}' for t, d in da)}")
        byd = defaultdict(list)
        for r in hk:
            byd[r['name']].append(r)
        print('      按捐款人：' + '；'.join(
            f"{k} 日志 {len(v)} 执行 {sum(1 for r in v if r['exec'])} 手续费 {fmt(sum(r['fee'] for r in v if r['exec']))} 想给 {fmt(sum(r['vmax'] for r in v if r['exec']))}"
            f"（pct<64 的 {sum(1 for r in v if r['exec'] and r['pct'] < 64)} 条：手续费 {fmt(sum(r['fee'] for r in v if r['exec'] and r['pct'] < 64))}、想给 {fmt(sum(r['vmax'] for r in v if r['exec'] and r['pct'] < 64))}）"
            for k, v in sorted(byd.items(), key=lambda kv: -sum(r['fee'] for r in kv[1] if r['exec']))))
        live = [r for r in rows if not r['recvHusk']]
        livee = [r for r in live if r['exec']]
        livec = [r for r in livee if not r['mixed']]
        print(f"      对照——给还在场的号：日志 {len(live)} 条、执行 {len(livee)} 条、手续费 {fmt(sum(r['fee'] for r in livee))}；金额干净的 {len(livec)} 条到账（估）{fmt(sum(r['delivered'] for r in livec))}")
    pair = defaultdict(list)
    for r in rows:
        pair[(r['me'], r['to'])].append(r)
    print('   按「谁→谁」：日志条数｜执行/没执行/判不了｜手续费｜到账(估，只算干净的)｜想给｜没执行原因｜下令拍范围')
    for (me, to), v in sorted(pair.items(), key=lambda kv: -sum(r['fee'] for r in kv[1] if r['exec'])):
        e = [r for r in v if r['exec']]
        c = [r for r in e if not r['mixed']]
        nn = [r for r in v if r['exec'] is False]
        w = defaultdict(int)
        for r in nn:
            w[r['why']] += 1
        st = '同队' if v[0]['sameTeam'] else '不同队' if v[0]['sameTeam'] is False else '?'
        print(f"   {v[0]['name']:12s}→{v[0]['toName'][:12]:12s}({st}) {len(v):3d}｜{len(e)}/{len(nn)}/{len(v) - len(e) - len(nn)}｜{fmt(sum(r['fee'] for r in e)):>7s}｜{fmt(sum(r['delivered'] for r in c)):>7s}（{len(c)} 条）｜{fmt(sum(r['vmax'] for r in c)):>7s}｜"
              + ' '.join(f"{k}{n_}" for k, n_ in w.items()) + f"｜t={v[0]['t']}~{v[-1]['t']}")
    if detail is not None:
        print(f"-- 逐条（{'全部' if detail < 0 else name_of(M.bots[detail])}）：t 种类 pct →谁｜余额 手续费 想给｜执行? 支出 到账(估)｜对方密度(前/后) 空间｜配额 已用+需要/上限｜原因")
        for r in rows:
            if detail >= 0 and r['me'] != detail and r['to'] != detail:
                continue
            exs = '执行' if r['exec'] else '没执行' if r['exec'] is False else '判不了'
            if r['exec'] and r['mixed']:
                exs += '(混)'
            if r['shared'] > 1:
                exs += '(两条合一段)'
            q = f"{r['quotaUsed']}+{r['quotaNeed']}/{r['quotaLimit']}" if r['quotaLimit'] is not None else '-'
            print(f"   {r['name']:12s} t={r['t']:5d} {r['kind']:7s} {r['pct']:3d} →{r['toName'][:12]:12s}｜{r['bal']:9d} {r['fee']:7d} {r['vmax']:8d}｜{exs} {int(r['spend']):8d} {'' if r['delivered'] is None else int(r['delivered']):>8}｜"
                  f"{'' if r['recvDens'] is None else round(r['recvDens'])}/{'' if r['recvDensAfter'] is None else round(r['recvDensAfter'])} {'' if r['recvRoom'] is None else r['recvRoom']}｜{q}｜{r['why'] or ''}")


# ------------------------------------------------------------------ donval（有录像的局：把上面这本「只靠日志」的账和录像真值对表）
def donval_rows(M):
    """只在有整局录像的局上跑：donlog 的「执行/没执行」对录像里有没有这条捐款；金额干净的那些，到账估算对引擎重放的真到账。"""
    if not getattr(M, 'cmds', None) or not M.sim:
        return None
    truth = {}
    for rec in donation_truth(M):
        truth[(rec['me'], rec['t'], rec['to'], rec['pct'])] = rec
    simd = defaultdict(list)
    for x in M.sim.get('donations', []):
        if x.get('ok'):
            simd[(x['from'], x['to'], x['pct'])].append(x)
    out = []
    for r in donlog_rows(M):
        tr = truth.get((r['me'], r['t'], r['to'], r['pct']))
        if not tr or tr['accepted'] is None:
            continue
        real = None
        if tr['accepted']:
            for x in simd[(r['me'], r['to'], r['pct'])]:
                if x['t'] == tr.get('execT'):
                    real = x
                    break
        out.append(dict(r, truth=bool(tr['accepted']), execT=tr.get('execT'), realDelivered=(real['delivered'] if real else None), realFee=(real['fee'] if real else None)))
    return out


def sec_donval(M):
    rows = donval_rows(M)
    if rows is None:
        print('没有整局录像，对不了表')
        return
    n = len(rows)
    cm = defaultdict(int)
    for r in rows:
        cm[(r['exec'], r['truth'])] += 1
    agree = cm[(True, True)] + cm[(False, False)]
    print(f"捐款日志账对录像真值：可对表的日志 {n} 条；判执行且录像里有 {cm[(True, True)]}、判没执行且录像里没有 {cm[(False, False)]}、"
          f"判执行但录像里没有 {cm[(True, False)]}、判没执行但录像里有 {cm[(False, True)]}、判不了 {cm[(None, True)] + cm[(None, False)]}（其中录像里有 {cm[(None, True)]}）；一致率 {100 * agree / max(1, n):.1f}%")
    cl = [r for r in rows if r['exec'] and r['truth'] and not r['mixed'] and r['realDelivered'] is not None]
    if cl:
        est = sum(r['delivered'] for r in cl)
        real = sum(r['realDelivered'] for r in cl)
        errs = sorted(abs(r['delivered'] - r['realDelivered']) / max(1, r['realDelivered']) for r in cl)
        fe = sum(r['fee'] for r in cl)
        fr = sum(r['realFee'] for r in cl)
        print(f"   金额干净且录像里有的 {len(cl)} 条：到账估算合计 {fmt(est)}、真值 {fmt(real)}（估/真 = {est / max(1, real):.3f}）；单条相对误差中位 {100 * errs[len(errs) // 2]:.1f}%、九成分位 {100 * errs[int(0.9 * (len(errs) - 1))]:.1f}%；"
              f"手续费按日志余额算 {fmt(fe)}、真值 {fmt(fr)}（{fe / max(1, fr):.3f}）")
    al = [r for r in rows if r['exec'] and r['truth'] and r['realDelivered'] is not None]
    if al:
        est2 = sum(r['byRule'] for r in al)
        real2 = sum(r['realDelivered'] for r in al)
        e2 = sorted(abs(r['byRule'] - r['realDelivered']) / max(1, r['realDelivered']) for r in al)
        w_est = set(id(r) for r in al if r['byRule'] < r['fee'])
        w_real = set(id(r) for r in al if r['realDelivered'] < r['realFee'])
        print(f"   第二种估法（到账 = min(想给, 对方空间)）对判执行且录像里有的 {len(al)} 条：估 {fmt(est2)}、真值 {fmt(real2)}（估/真 = {est2 / max(1, real2):.3f}）；单条相对误差中位 {100 * e2[len(e2) // 2]:.1f}%、九成分位 {100 * e2[int(0.9 * (len(e2) - 1))]:.1f}%；"
              f"「到账 < 手续费」：估出 {len(w_est)} 条、真值 {len(w_real)} 条、两边都是 {len(w_est & w_real)} 条")
    mx = [r for r in rows if r['exec'] and r['mixed']]
    print(f"   判执行但与别的指令混在一段的 {len(mx)} 条，其中录像里有 {sum(1 for r in mx if r['truth'])} 条")
    wrong = [r for r in rows if (r['exec'] is True and not r['truth']) or (r['exec'] is False and r['truth'])]
    for r in wrong[:12]:
        print(f"   不一致：{r['name']} t={r['t']} {r['kind']} pct={r['pct']} →{r['toName'][:12]} 余额 {r['bal']}｜账上 {'执行' if r['exec'] else '没执行'}{'(混)' if r['mixed'] else ''} 支出 {int(r['spend'])}｜录像 {'有 @' + str(r['execT']) if r['truth'] else '没有'}")


# ------------------------------------------------------------------ cmdmix（指令构成：cmds 计数里多少是捐款、多少是协防戳、剩下的才是出兵/发船）
CMDMIX_EDGES = [630, 1530, 2070, 3510, 5040, 7020, 9000, 9990, 10980, 11970, 12960, 13860]


def cmdmix_rows(M, edges=None):
    """按时段数每个号：cmds 计数涨了几条、其中捐款日志几条、协防戳日志几条、剩下的（出兵、发船等）几条；时段首尾的领土与余额。
    时段边界取快照拍；某号在边界上没有快照就用它之前最近的一条（阵亡的号只算到最后一条快照）。"""
    edges = edges or CMDMIX_EDGES
    out = []
    for me, b in sorted(M.bots.items()):
        if not b.traj:
            continue
        for t0, t1 in zip(edges, edges[1:]):
            a = b.at(t0)
            c = b.at(t1)
            if a is None or c is None or c['t'] <= a['t'] or a['t'] < t0 - 90:
                continue
            dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
            ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            dc = c['cmds'] - a['cmds']
            out.append(dict(me=me, name=name_of(b), t0=a['t'], t1=c['t'], seg=(t0, t1), cmds=dc, don=dn, poke=ps, other=dc - dn - ps, boats=c['boats'] - a['boats'],
                            terr0=a['terr'], terr1=c['terr'], bal0=a['bal'], bal1=c['bal'], dens0=a['dens'], dens1=c['dens'], full=(c['t'] == t1)))
    return out


def sec_cmdmix(M):
    rows = cmdmix_rows(M)
    segs = sorted({r['seg'] for r in rows})
    print('指令构成（cmds 计数的增量 = 捐款日志 + 协防戳日志 + 其余〔出兵、发船等〕）。每格：其余/捐款/戳；* = 这个号在本时段内阵亡，只算到最后一条快照')
    print('   ' + ' ' * 14 + ' '.join(f"{a}~{b}".rjust(13) for a, b in segs))
    by = defaultdict(dict)
    for r in rows:
        by[r['me']][r['seg']] = r
    for me in sorted(by):
        cells = []
        for s in segs:
            r = by[me].get(s)
            cells.append((f"{r['other']}/{r['don']}/{r['poke']}" + ('' if r['full'] else '*')).rjust(13) if r else ' ' * 13)
        print(f"   {name_of(M.bots[me]):14s}" + ' '.join(cells))
    print('   合计：时段｜在场号·拍（按各号实际覆盖的拍数）｜其余指令｜捐款｜戳｜每 1000 号·拍的其余指令｜时段首尾全队领土｜全队余额')
    for s in segs:
        v = [r for r in rows if r['seg'] == s]
        bt = sum(r['t1'] - r['t0'] for r in v)
        o = sum(r['other'] for r in v)
        print(f"   {s[0]:5d}~{s[1]:5d}｜{bt:6d}｜{o:4d}｜{sum(r['don'] for r in v):3d}｜{sum(r['poke'] for r in v):3d}｜{1000 * o / max(1, bt):5.1f}｜"
              f"{sum(r['terr0'] for r in v)}→{sum(r['terr1'] for r in v)}｜{fmt(sum(r['bal0'] for r in v))}→{fmt(sum(r['bal1'] for r in v))}")


# ------------------------------------------------------------------ idleloss（丢地的同时一条出兵指令都没发）
IDLE_LOSS = 0.99     # 相邻快照领土 < 0.99× → 这 90 拍在丢地
IDLE_DENS = 100.0    # 起点密度 >= 100 → 余额已经过软上限（利息开始打折）


def idleloss_rows(M):
    """相邻快照之间在丢地（领土少了 1% 以上）的间隔，按「这段里发没发出兵/发船指令」「起点密度过没过 100」分类；
    连续的「丢地 + 零出兵」间隔并成一段。出兵/发船 = cmds 计数增量 − 捐款日志 − 协防戳日志。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        iv = []
        for a, c in zip(tr, tr[1:]):
            if a['t'] < 630 or a['terr'] < 200:
                continue
            dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
            ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            other = (c['cmds'] - a['cmds']) - dn - ps + (c['boats'] - a['boats'])
            iv.append(dict(t0=a['t'], t1=c['t'], terr0=a['terr'], terr1=c['terr'], dens0=a['dens'], dens1=c['dens'], bal0=a['bal'], bal1=c['bal'],
                           losing=c['terr'] < IDLE_LOSS * a['terr'], other=other, don=dn, poke=ps, nb=a['nb']))
        lose = [x for x in iv if x['losing']]
        idle = [x for x in lose if x['other'] <= 0]
        dense = [x for x in idle if x['dens0'] >= IDLE_DENS]
        runs = []
        cur = None
        for x in iv:
            if x['losing'] and x['other'] <= 0:
                if cur and cur['t1'] == x['t0']:
                    cur['t1'] = x['t1']
                    cur['terr1'] = x['terr1']
                    cur['bal1'] = x['bal1']
                    cur['densMin'] = min(cur['densMin'], x['dens0'])
                    cur['densMax'] = max(cur['densMax'], x['dens0'])
                    cur['don'] += x['don']
                    cur['poke'] += x['poke']
                else:
                    cur = dict(t0=x['t0'], t1=x['t1'], terr0=x['terr0'], terr1=x['terr1'], bal0=x['bal0'], bal1=x['bal1'], densMin=x['dens0'], densMax=x['dens0'],
                               don=x['don'], poke=x['poke'])
                    runs.append(cur)
            else:
                cur = None
        dt = death_tick(b)
        out.append(dict(me=me, name=name_of(b), team=b.team, death=dt, nLose=len(lose), lostAll=sum(x['terr0'] - x['terr1'] for x in lose),
                        nIdle=len(idle), lostIdle=sum(x['terr0'] - x['terr1'] for x in idle),
                        nDense=len(dense), lostDense=sum(x['terr0'] - x['terr1'] for x in dense), runs=runs,
                        balAtDeath=(b.result.get('balance') if b.result and b.result.get('event') == 'died' else None),
                        peakBal=max((s['bal'] for s in tr), default=0)))
    return out


def sec_idleloss(M):
    rows = idleloss_rows(M)
    print(f"丢地间隔账（相邻快照领土少 1% 以上算丢地；t>=630、领土>=200 的间隔）：号｜丢地间隔数 共丢｜其中零出兵 间隔数 丢｜其中零出兵且起点密度>={IDLE_DENS:.0f} 间隔数 丢｜阵亡时余额（结算行）")
    for r in rows:
        print(f"   {r['name']:14s} 队{r['team']}｜{r['nLose']:3d} {r['lostAll']:7d}｜{r['nIdle']:3d} {r['lostIdle']:7d}（{100 * r['lostIdle'] / max(1, r['lostAll']):3.0f}%）｜{r['nDense']:3d} {r['lostDense']:7d}（{100 * r['lostDense'] / max(1, r['lostAll']):3.0f}%）｜"
              + (f"{fmt(r['balAtDeath'])}（历史最高余额的 {100 * r['balAtDeath'] / max(1, r['peakBal']):.0f}%）" if r['balAtDeath'] is not None else '-'))
    ta = sum(r['lostAll'] for r in rows)
    ti = sum(r['lostIdle'] for r in rows)
    td = sum(r['lostDense'] for r in rows)
    print(f"   合计：丢地 {ta} 格；其中零出兵间隔里丢的 {ti} 格（{100 * ti / max(1, ta):.0f}%）；零出兵且密度>={IDLE_DENS:.0f} 的 {td} 格（{100 * td / max(1, ta):.0f}%）")
    print('   连续「丢地 + 零出兵」>=270 拍的段：号 起止拍｜领土｜余额｜期间起点密度范围｜期间捐款/戳日志条数')
    for r in rows:
        for u in r['runs']:
            if u['t1'] - u['t0'] >= 270:
                tail = f"，{r['death'] - u['t1']} 拍后阵亡" if r['death'] and r['death'] - u['t1'] <= 600 else ''
                print(f"   {r['name']:14s} t={u['t0']}~{u['t1']}（{u['t1'] - u['t0']} 拍）｜{u['terr0']}→{u['terr1']}｜{fmt(u['bal0'])}→{fmt(u['bal1'])}｜{u['densMin']:.0f}~{u['densMax']:.0f}｜{u['don']}/{u['poke']}{tail}")


# ------------------------------------------------------------------ spend（兵去哪了：按「这段里发了什么指令」分账）
SPEND_MIN = 0.01


def spend_rows(M, t_from=0, t_to=10 ** 9):
    """相邻快照之间：按引擎利息推「没有任何支出」的余额 pred；pred − 实际 = 这段的净支出（>0）或净流入（<0，收到捐款/出去的兵退回）。
    按这段里日志记到的指令分账：无指令 / 只有捐款 / 只有协防戳 / 只有出兵或发船 / 混合。
    指令生效比下令晚 7~30 拍，下在间隔末尾的指令会记到下一段——只用于合计，不用于单段结论。"""
    out = []
    for me, b in sorted(M.bots.items()):
        acc = defaultdict(lambda: dict(n=0, spend=0, dterr=0, gain=0, lose=0))
        interest = 0
        inflow = 0
        for a, c in zip(b.traj, b.traj[1:]):
            if a['t'] < t_from or c['t'] > t_to or a['bal'] <= 0:
                continue
            pred = grow(a['bal'], a['t'], c['t'], b, M.land)
            interest += pred - a['bal']
            dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
            ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            ot = (c['cmds'] - a['cmds']) - dn - ps
            kinds = [k for k, v in (('don', dn), ('poke', ps), ('atk', ot)) if v > 0]
            cls = 'none' if not kinds else (kinds[0] if len(kinds) == 1 else 'mixed')
            d = pred - c['bal']
            x = acc[cls]
            x['n'] += 1
            dt = c['terr'] - a['terr']
            x['dterr'] += dt
            x['gain'] += max(0, dt)
            x['lose'] += max(0, -dt)
            if d > SPEND_MIN * pred:
                x['spend'] += d
            elif d < -SPEND_MIN * pred:
                inflow += -d
        out.append(dict(me=me, name=name_of(b), team=b.team, interest=interest, inflow=inflow, classes={k: dict(v) for k, v in acc.items()},
                        pokes=sum(1 for e in b.assists if t_from <= e['t'] <= t_to), dons=sum(1 for e in b.donations if t_from <= e['t'] <= t_to)))
    return out


def sec_spend(M, t_from=0, t_to=10 ** 9):
    rows = spend_rows(M, t_from, t_to)
    lab = dict(none='无指令', don='只捐款', poke='只协防戳', atk='只出兵/发船', mixed='混合')
    rng = '' if t_from == 0 and t_to >= 10 ** 9 else f"（t={t_from}~{t_to}）"
    print(f"兵去哪了{rng}（估）：相邻快照间 净支出 = 按引擎利息推的余额 − 实际余额；按这段里日志记到的指令分账。每格：段数 / 净支出 / 领土净变化（得 / 丢）")
    tot = defaultdict(lambda: dict(n=0, spend=0, dterr=0, gain=0, lose=0))
    for r in rows:
        if not r['classes']:
            continue
        parts = []
        for k in ('none', 'don', 'poke', 'atk', 'mixed'):
            x = r['classes'].get(k)
            if not x:
                continue
            for f in ('n', 'spend', 'dterr', 'gain', 'lose'):
                tot[k][f] += x[f]
            parts.append(f"{lab[k]} {x['n']} / {fmt(x['spend'])} / {x['dterr']:+d}（+{x['gain']} / −{x['lose']}）")
        print(f"   {r['name']:13s}(队{r['team']}) 利息 {fmt(r['interest'])}｜净流入 {fmt(r['inflow'])}｜" + '；'.join(parts))
    print('   合计：' + '；'.join(f"{lab[k]} {x['n']} 段 / {fmt(x['spend'])} / {x['dterr']:+d}（+{x['gain']} / −{x['lose']}）" for k, x in ((k, tot[k]) for k in ('none', 'don', 'poke', 'atk', 'mixed')) if x['n']))


# ------------------------------------------------------------------ bursts / thinbig（两个只靠日志的机械判定）
BURST_MIN_CMDS = 3        # 一个快照间隔内的出兵/发船指令条数下限
BURST_GROW = 1.25         # 这个间隔加下一个间隔，领土至少涨到几倍
BURST_MAX_COST = 80       # 净支出 / 净得格 的上限（兵）
BURST_HOLD_T = 600        # 之后多少拍再看一次
BURST_HOLD = 1.2          # 那时领土至少还是扩张前的几倍
BURST_MIN_TERR = 300      # 起点领土下限（排除开局头几圈）


def _other_cmds(b, a, c):
    dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
    ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
    return (c['cmds'] - a['cmds']) - dn - ps


def burst_rows(M, t_from=630):
    """NEW:AT-cheap-burst：一个快照间隔内 >=3 条出兵/发船指令，这个间隔加下一个间隔领土 +25% 以上，
    净支出/净得格 <80 兵（净支出 = 两个间隔里「按引擎利息推的余额 − 实际余额」之和，带符号），
    且 600 拍后（之后第一条 t>=起点+600 的快照；终局前不足 600 拍就用最后一条）领土仍 >= 扩张前的 1.2 倍。
    返回 (命中的, 只差最后一条「600 拍后还在」的)。相邻命中的间隔只记第一条。"""
    hits, faded = [], []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        last_hit = -10 ** 9
        for i in range(len(tr) - 2):
            a, c, e = tr[i], tr[i + 1], tr[i + 2]
            if a['t'] < t_from or a['terr'] < BURST_MIN_TERR or a['bal'] <= 0 or c['t'] - a['t'] > 270 or e['t'] - c['t'] > 270:
                continue
            ot = _other_cmds(b, a, c)
            if ot < BURST_MIN_CMDS or e['terr'] < BURST_GROW * a['terr']:
                continue
            spend = (grow(a['bal'], a['t'], c['t'], b, M.land) - c['bal']) + (grow(c['bal'], c['t'], e['t'], b, M.land) - e['bal'])
            cells = e['terr'] - a['terr']
            cost = spend / max(1, cells)
            if cost >= BURST_MAX_COST:
                continue
            later = [x for x in tr if x['t'] >= a['t'] + BURST_HOLD_T]
            dt = death_tick(b)
            if later:
                hold = later[0]
            elif dt is None and b.result and b.result.get('event') == 'end':
                hold = tr[-1]
            else:
                hold = None
            row = dict(me=me, name=name_of(b), team=b.team, t=a['t'], t1=e['t'], terr0=a['terr'], terr1=e['terr'], cmds=ot, bal0=a['bal'], balMin=min(c['bal'], e['bal']),
                       bal1=e['bal'], spend=int(spend), cost=round(cost, 1), dens0=round(a['dens'], 1), nb=a['nb'],
                       holdT=hold['t'] if hold else None, holdTerr=hold['terr'] if hold else None, died=dt)
            if a['t'] - last_hit <= 180:
                continue
            last_hit = a['t']
            (hits if hold and hold['terr'] >= BURST_HOLD * a['terr'] else faded).append(row)
    return hits, faded


def sec_bursts(M, t_from=630):
    hits, faded = burst_rows(M, t_from)
    print(f"便宜的集中出手（NEW:AT-cheap-burst；只用日志）：一个快照间隔内 >={BURST_MIN_CMDS} 条出兵/发船指令，这个间隔加下一个间隔领土 >= {BURST_GROW} 倍，"
          f"净支出/净得格 < {BURST_MAX_COST} 兵，{BURST_HOLD_T} 拍后领土仍 >= 扩张前的 {BURST_HOLD} 倍；起点 t>={t_from}（不带参数 = 630，含开局扩张；NEW:AT-cheap-burst 的实例取 bursts 1440）")
    def line(r):
        return (f"   {r['name']:13s}(队{r['team']}) t={r['t']}~{r['t1']} 指令 {r['cmds']} 条；领土 {r['terr0']}→{r['terr1']}（+{r['terr1'] - r['terr0']}）；余额 {fmt(r['bal0'])}→最低 {fmt(r['balMin'])}→{fmt(r['bal1'])}；"
                f"净支出 {fmt(r['spend'])}，每格 {r['cost']} 兵；起点密度 {r['dens0']} nb={r['nb']}；"
                + (f"t={r['holdT']} 领土 {r['holdTerr']}（{r['holdTerr'] / max(1, r['terr0']):.2f} 倍）" if r['holdT'] is not None else '之后没有快照')
                + (f"；阵亡 t={r['died']}" if r['died'] else ''))
    print(f"  命中 {len(hits)} 次：")
    for r in hits:
        print(line(r))
    print(f"  前三条都满足、但 {BURST_HOLD_T} 拍后没守住（或没活到）的 {len(faded)} 次：")
    for r in faded:
        print(line(r))


BOXB_WIN = 500            # 发船后多少拍内看领土
BOXB_GROW = 1.5           # 涨到几倍算「靠船突围」
BOXB_FLAT = 1.05          # 不到几倍算「没换到地」


def boxboat_rows(M):
    """被围发船：起点快照 nb=0 且 neut=0、这个间隔里 boats 计数涨了。相邻（<=270 拍）的这种间隔并成一段。
    每段：发船条数、这些间隔的净支出（按引擎利息推的余额 − 实际余额，带符号求和；同一间隔里有捐款日志的不计，另列条数）、起点领土、段首起 500 拍内（到段尾 +500）最高领土。
    NEW:BT-boxed-breakout = 最高领土 >= 1.5×起点；「没换到地」= 最高领土 < 1.05×起点。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        segs = []
        for a, c in zip(tr, tr[1:]):
            if a['nb'] == 0 and a['neut'] == 0 and c['boats'] > a['boats'] and c['t'] - a['t'] <= 270:
                spend = grow(a['bal'], a['t'], c['t'], b, M.land) - c['bal']
                dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
                if segs and a['t'] - segs[-1]['t1'] <= 270:
                    g = segs[-1]
                    g['t1'] = c['t']
                    g['boats'] += c['boats'] - a['boats']
                    g['n'] += 1
                else:
                    g = dict(me=me, name=name_of(b), team=b.team, t0=a['t'], t1=c['t'], boats=c['boats'] - a['boats'], spend=0, n=1, mixed=0, boatsMixed=0,
                             terr0=a['terr'], bal0=a['bal'], dens0=round(a['dens'], 1))
                    segs.append(g)
                if dn:
                    g['mixed'] += 1          # 这个间隔里还有捐款日志：支出分不开，不计入净支出
                    g['boatsMixed'] += c['boats'] - a['boats']
                else:
                    g['spend'] += spend
        for g in segs:
            win = [x for x in tr if g['t0'] < x['t'] <= g['t1'] + BOXB_WIN]
            g['maxTerr'] = max((x['terr'] for x in win), default=g['terr0'])
            g['maxT'] = next((x['t'] for x in win if x['terr'] == g['maxTerr']), None)
            g['endTerr'] = win[-1]['terr'] if win else g['terr0']
            g['endT'] = win[-1]['t'] if win else None
            g['died'] = death_tick(b)
            e1 = next((x for x in tr if x['t'] == g['t1']), None)
            nx = next((x for x in tr if x['t'] > g['t1']), None)
            g['bal1'] = e1['bal'] if e1 else None
            g['balNext'] = nx['bal'] if nx else None
            g['ratio'] = g['maxTerr'] / max(1, g['terr0'])
            g['kind'] = 'breakout' if g['ratio'] >= BOXB_GROW else ('flat' if g['ratio'] < BOXB_FLAT else 'some')
            out.append(g)
    return out


def sec_boxboats(M):
    rows = boxboat_rows(M)
    lab = dict(breakout='突围（NEW:BT-boxed-breakout）', some='涨了一点', flat='没换到地')
    print(f"被围发船（只用日志）：起点 nb=0 且 neut=0 的快照间隔里 boats 计数上涨，相邻间隔并成一段；看段首到段尾 +{BOXB_WIN} 拍内的最高领土；净支出只算没有捐款日志的间隔。"
          f"共 {len(rows)} 段、{sum(r['boats'] for r in rows)} 条船：" + '，'.join(f"{lab[k]} {sum(1 for r in rows if r['kind'] == k)} 段 / {sum(r['boats'] for r in rows if r['kind'] == k)} 条船 / 净支出 {fmt(sum(r['spend'] for r in rows if r['kind'] == k))}" for k in ('breakout', 'some', 'flat')))
    for r in rows:
        print(f"   {r['name']:13s}(队{r['team']}) t={r['t0']}~{r['t1']} 船 {r['boats']} 条（{r['n']} 个间隔）；起点 {r['terr0']} 格、{fmt(r['bal0'])} 兵、密度 {r['dens0']}；"
              f"净支出 {fmt(r['spend'])}（{r['boats'] - r['boatsMixed']} 条船；另 {r['boatsMixed']} 条所在间隔有捐款，不计）；段尾余额 {fmt(r['bal1']) if r['bal1'] is not None else '-'}、下一个快照 {fmt(r['balNext']) if r['balNext'] is not None else '-'}；"
              f"最高领土 {r['maxTerr']}（t={r['maxT']}，{r['ratio']:.2f} 倍）；t={r['endT']} 时 {r['endTerr']} 格 → {lab[r['kind']]}" + (f"；阵亡 t={r['died']}" if r['died'] else ''))


HARV_T_FROM = 630         # 开局期到处是无主地，不算
HARV_NEUT = 8             # 无主邻格从 0 跳到至少这么多
HARV_WIN = 270            # 从跳变前一个快照起多少拍内看领土
HARV_GROW = 1.2


def harvest_rows(M, t_from=None):
    """NEW:AT-collapse-harvest：t>=630，相邻快照（<=270 拍）neut 从 0 变成 >=8（引擎里一个玩家领土 <= 峰值/4 就崩盘，剩下的地变成无主地，
    正在打它的兵改打无主地），从跳变前一个快照起 270 拍内领土到过 >= 1.2 倍。
    同一个号相邻命中（起点相隔 <=270 拍）只记第一条。列出：这段里的指令数/发船数、余额（起点→最低→终点）、nb 的变化、600 拍后的领土。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        last = -10 ** 9
        for i in range(len(tr) - 1):
            a, c = tr[i], tr[i + 1]
            if a['t'] < (HARV_T_FROM if t_from is None else t_from) or c['t'] - a['t'] > 270 or a['neut'] != 0 or c['neut'] < HARV_NEUT or a['terr'] < 300:
                continue
            win = [x for x in tr if a['t'] < x['t'] <= a['t'] + HARV_WIN]
            top = max(win, key=lambda x: x['terr'])
            if top['terr'] < HARV_GROW * a['terr'] or a['t'] - last <= 270:
                continue
            last = a['t']
            pre = tr[i - 1] if i > 0 and a['t'] - tr[i - 1]['t'] <= 270 else a
            seg = [x for x in tr if pre['t'] <= x['t'] <= top['t']]
            later = [x for x in tr if x['t'] >= a['t'] + 600]
            spend = sum(grow(x['bal'], x['t'], y['t'], b, M.land) - y['bal'] for x, y in zip(seg, seg[1:]))
            dons = sum(1 for e in b.donations if pre['t'] <= e['t'] < top['t'])
            out.append(dict(me=me, name=name_of(b), team=b.team, t=a['t'], tNeut=c['t'], neut=c['neut'], terr0=a['terr'], terrTop=top['terr'], tTop=top['t'],
                            preT=pre['t'], cmds=top['cmds'] - pre['cmds'], boats=top['boats'] - pre['boats'], dons=dons, bal0=pre['bal'], balMin=min(x['bal'] for x in seg), bal1=top['bal'],
                            spend=int(spend), nb0=a['nb'], nb1=top['nb'], dens0=round(a['dens'], 1),
                            holdT=later[0]['t'] if later else None, holdTerr=later[0]['terr'] if later else None, died=death_tick(b)))
    return out


def sec_harvest(M, t_from=None):
    rows = harvest_rows(M, t_from)
    late = [r for r in rows if r['t'] >= 1440]
    print(f"邻居崩盘后收地（NEW:AT-collapse-harvest；只用日志）：t>={HARV_T_FROM if t_from is None else t_from}，相邻快照 neut 从 0 变成 >={HARV_NEUT}，从跳变前一个快照起 {HARV_WIN} 拍内领土 >= {HARV_GROW} 倍：{len(rows)} 次，"
          f"合计 +{sum(r['terrTop'] - r['terr0'] for r in rows)} 格；其中起点 t>=1440 的 {len(late)} 次、+{sum(r['terrTop'] - r['terr0'] for r in late)} 格、净支出合计 {fmt(sum(r['spend'] for r in late))}")
    for r in rows:
        print(f"   {r['name']:13s}(队{r['team']}) t={r['t']}→{r['tTop']} 领土 {r['terr0']}→{r['terrTop']}（+{r['terrTop'] - r['terr0']}，{r['terrTop'] / r['terr0']:.2f} 倍）；t={r['tNeut']} neut={r['neut']}；nb {r['nb0']}→{r['nb1']}；"
              f"t={r['preT']}~{r['tTop']} 指令 {r['cmds']} 条（发船 {r['boats']}、捐款日志 {r['dons']}）；余额 {fmt(r['bal0'])}→最低 {fmt(r['balMin'])}→{fmt(r['bal1'])}，净支出 {fmt(r['spend'])}"
              f"（每格 {r['spend'] / max(1, r['terrTop'] - r['terr0']):.0f} 兵）；起点密度 {r['dens0']}；"
              + (f"t={r['holdT']} 领土 {r['holdTerr']}" if r['holdT'] is not None else '之后没有快照') + (f"；阵亡 t={r['died']}" if r['died'] else ''))


CRUMB_MIN_LEN = 270       # 连续多少拍
CRUMB_T_MAX = 1500        # 只看开局期（t < coreFrom / dpEnd）


def crumb_rows(M):
    """NEW:OP-neutral-crumb-lock：t<1500，连续 >=270 拍 neut>0、cmds 与 boats 计数不变、领土不变（日志快照）。
    代码：t<dpEnd(1500) 无主地只走 dpNeutral（L2418-2444），要买的那几圈不到 minCmd（4×手续费 = 余额的 4.7%）就不发（L2440）；
    General.act L835 在 neutral>0 时直接返回，后面的发船（L840-844）和闲兵出手（L845）都走不到。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = [x for x in b.traj if x['t'] <= CRUMB_T_MAX + 30]
        i = 0
        while i < len(tr):
            if tr[i]['neut'] <= 0:
                i += 1
                continue
            j = i
            while (j + 1 < len(tr) and tr[j + 1]['neut'] > 0 and tr[j + 1]['cmds'] == tr[i]['cmds'] and tr[j + 1]['boats'] == tr[i]['boats']
                   and tr[j + 1]['terr'] == tr[i]['terr'] and tr[j + 1]['t'] - tr[j]['t'] <= 270):
                j += 1
            a, c = tr[i], tr[j]
            if c['t'] - a['t'] >= CRUMB_MIN_LEN:
                nxt = next((x for x in b.traj if x['t'] > c['t']), None)
                out.append(dict(me=me, name=name_of(b), team=b.team, t0=a['t'], t1=c['t'], terr=a['terr'], bal0=a['bal'], bal1=c['bal'], dens0=round(a['dens'], 1), dens1=round(c['dens'], 1),
                                nb=sorted({x['nb'] for x in tr[i:j + 1]}), neut=sorted({x['neut'] for x in tr[i:j + 1]}), minCmd0=4 * (12 * a['bal'] // 1024), minCmd1=4 * (12 * c['bal'] // 1024),
                                nextT=nxt['t'] if nxt else None, nextCmds=(nxt['cmds'] - c['cmds']) if nxt else None, nextBoats=(nxt['boats'] - c['boats']) if nxt else None))
            i = j + 1
    return out


def sec_crumb(M):
    rows = crumb_rows(M)
    print(f"开局期被零星无主地卡住（NEW:OP-neutral-crumb-lock；只用日志）：t<{CRUMB_T_MAX}，连续 >={CRUMB_MIN_LEN} 拍 neut>0、cmds/boats 计数不变、领土不变：{len(rows)} 段，合计 {sum(r['t1'] - r['t0'] for r in rows)} 拍")
    for r in rows:
        print(f"   {r['name']:13s}(队{r['team']}) t={r['t0']}~{r['t1']}（{r['t1'] - r['t0']} 拍）领土 {r['terr']}；nb {r['nb']} neut {r['neut']}；余额 {fmt(r['bal0'])}→{fmt(r['bal1'])}，密度 {r['dens0']}→{r['dens1']}；"
              f"最小指令量（4×手续费）{fmt(r['minCmd0'])}→{fmt(r['minCmd1'])}"
              + (f"；下一个快照 t={r['nextT']} 指令 +{r['nextCmds']}（其中发船 +{r['nextBoats']}）" if r['nextT'] is not None else '；之后没有快照'))



NOEFF_T_FROM = 630        # 开局周期出兵之后才数
NOEFF_RATIO = 0.985       # 间隔末余额 >= 纯利息预测 × 这个数 → 这段没有任何支出
NOEFF_MIN_CMDS = 2        # 这段里至少发了几条「其余指令」（陆攻一条的手续费就是余额的 12/1024 = 1.17%，两条就该低 2.3% 以上）
NOEFF_SEG = 270           # 连续多少拍以上算一段「断档」
NOEFF_GROW = 1.01         # 间隔末领土 <= 起点 × 这个数（涨了地就说明有指令生效了）


def noeffect_rows(M, t_from=NOEFF_T_FROM, t_to=None):
    """发了令却没有任何支出（NEW:IO-cmd-blackout 的日志侧判据；只用日志）。
    间隔 [a, c] = 相邻两条快照（相隔 <=180 拍，a.t >= t_from）。其余指令 = cmds 增量 − 这段里的捐款日志条数 − 协防戳日志条数（发船算在其余里）。
    不见效间隔：其余指令 >= NOEFF_MIN_CMDS，c.bal >= NOEFF_RATIO × 纯利息预测，且 c.terr <= NOEFF_GROW × a.terr（领土没涨）。
    这段里有别的我方号给它的捐款日志（下令拍在 [a.t−20, c.t)）时可能有流入盖住支出：单列 inflow，不算不见效。
    返回每个号：全部间隔的其余指令条数、不见效间隔的条数、连续不见效 >= NOEFF_SEG 拍的段。"""
    recv = defaultdict(list)
    for o, ob in M.bots.items():
        for e in ob.donations:
            recv[e['to']].append(e['t'])
    out = []
    for me, b in sorted(M.bots.items()):
        tr = [x for x in b.traj if x['t'] >= t_from and (t_to is None or x['t'] <= t_to)]
        iv = []
        for a, c in zip(tr, tr[1:]):
            if c['t'] - a['t'] > 180:
                continue
            logged = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t']) + sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            other = (c['cmds'] - a['cmds']) - logged
            if other <= 0:
                continue
            ratio = c['bal'] / max(1, pure_interest(a, c, M.land))
            inflow = any(a['t'] - 20 <= t < c['t'] for t in recv.get(me, ()))
            iv.append(dict(t0=a['t'], t1=c['t'], other=other, boats=c['boats'] - a['boats'], ratio=ratio, inflow=inflow,
                           noeff=(other >= NOEFF_MIN_CMDS and ratio >= NOEFF_RATIO and c['terr'] <= NOEFF_GROW * a['terr'] and not inflow),
                           nb=a['nb'], neut=a['neut'], dens=a['dens'], terr0=a['terr'], terr1=c['terr'], bal0=a['bal'], bal1=c['bal']))
        if not iv:
            continue
        segs = []
        cur = None
        for x in iv:
            if x['noeff'] and cur is not None and x['t0'] == cur['t1']:
                cur['t1'] = x['t1']
                cur['cmds'] += x['other']
                cur['boats'] += x['boats']
                cur['terr1'] = x['terr1']
                cur['bal1'] = x['bal1']
                cur['nbs'].append(x['nb'])
            elif x['noeff']:
                cur = dict(t0=x['t0'], t1=x['t1'], cmds=x['other'], boats=x['boats'], terr0=x['terr0'], terr1=x['terr1'], bal0=x['bal0'], bal1=x['bal1'],
                           dens0=x['dens'], nbs=[x['nb']])
                segs.append(cur)
            else:
                cur = None
        for g in segs:
            _, nxt = snap_around(b, g['t1'])
            s1, _ = snap_around(b, g['t1'])
            g['next'] = None
            if s1 and nxt and nxt['t'] - s1['t'] <= 180:
                g['next'] = dict(t=nxt['t'], ratio=nxt['bal'] / max(1, pure_interest(s1, nxt, M.land)), terr=nxt['terr'], cmds=nxt['cmds'] - s1['cmds'])
            g['nbMin'], g['nbMax'] = min(g['nbs']), max(g['nbs'])
            del g['nbs']
        out.append(dict(me=me, name=name_of(b), team=b.team, total=sum(x['other'] for x in iv), noeff=sum(x['other'] for x in iv if x['noeff']),
                        nIv=len(iv), nNoeff=sum(1 for x in iv if x['noeff']), inflowCmds=sum(x['other'] for x in iv if x['inflow']),
                        boatsNoeff=sum(x['boats'] for x in iv if x['noeff']),
                        segs=[g for g in segs if g['t1'] - g['t0'] >= NOEFF_SEG], died=death_tick(b)))
    return out


def sec_noeffect(M, t_from=NOEFF_T_FROM):
    rows = noeffect_rows(M, t_from)
    print(f"发了令却没有任何支出（NEW:IO-cmd-blackout 的日志侧判据；只用日志）：相邻快照间「其余指令」（cmds 增量 − 捐款日志 − 协防戳日志，含发船）>= {NOEFF_MIN_CMDS} 条，"
          f"而间隔末余额 >= 纯利息预测 × {NOEFF_RATIO}（一条陆攻光手续费就是余额的 1.17%）、领土没涨（<= {NOEFF_GROW} 倍）；起点 t>={t_from}；这段里有别的我方号给它捐款的间隔不算")
    tot = sum(r['total'] for r in rows)
    ne = sum(r['noeff'] for r in rows)
    print(f"  合计：其余指令 {tot} 条，其中落在不见效间隔里的 {ne} 条（{100 * ne / max(1, tot):.1f}%；其中发船 {sum(r['boatsNoeff'] for r in rows)} 条）；涉及 {sum(1 for r in rows if r['noeff'])} 个号；"
          f"连续 >= {NOEFF_SEG} 拍的段 {sum(len(r['segs']) for r in rows)} 段、{sum(g['cmds'] for r in rows for g in r['segs'])} 条")
    for r in sorted(rows, key=lambda r: -r['noeff']):
        if not r['noeff']:
            continue
        print(f"   {r['name']:13s}(队{r['team']}) 其余指令 {r['total']} 条 / 不见效 {r['noeff']} 条（{100 * r['noeff'] / max(1, r['total']):.0f}%；{r['nNoeff']}/{r['nIv']} 个间隔）"
              + (f"；阵亡 t={r['died']}" if r['died'] else ''))
        for g in r['segs']:
            nx = g['next']
            tail = '之后没有快照' if nx is None else f"下一个间隔（到 t={nx['t']}）余额是纯利息预测的 {100 * nx['ratio']:.0f}%、领土 {nx['terr']}、又发 {nx['cmds']} 条"
            print(f"       t={g['t0']}~{g['t1']}（{g['t1'] - g['t0']} 拍）发了 {g['cmds']} 条（其中发船 {g['boats']} 条）；nb {g['nbMin']}~{g['nbMax']}；领土 {g['terr0']}→{g['terr1']}；余额 {fmt(g['bal0'])}→{fmt(g['bal1'])}；起点密度 {g['dens0']:.0f}；{tail}")


def noefftl_rows(M, t_from=NOEFF_T_FROM, t_to=3600):
    """按时间看「发令不见效」和「集中清仓」是不是全编队同时发生（同时 = 公共原因，例如整机卡顿；各自 = 各号自己的局面）。
    每个 90 拍间隔 [a, c]（a.t 落在哪一档就记哪一档）：
      有令 = 其余指令（cmds 增量 − 捐款日志 − 协防戳日志）>= 1；不见效 = noeffect 的判据；
      清仓 = 余额 < 纯利息预测 × 0.5 且领土没丢（c.terr >= 0.9 × a.terr）；k = ln(余额/预测)/ln(0.868)。
      超发 = k − 这段里的其余指令条数 >= 3（执行掉的 12% 出手比这段里新发的指令多 3 条以上 → 有更早发的令在这段才生效，或单条比例远大于 12%）。"""
    bins = defaultdict(lambda: dict(alive=0, withCmd=0, cmds=0, noeff=0, noeffCmds=0, dump=0, over=0, who=[]))
    for me, b in sorted(M.bots.items()):
        tr = [x for x in b.traj if t_from <= x['t'] <= t_to]
        for a, c in zip(tr, tr[1:]):
            if c['t'] - a['t'] > 90:
                continue
            g = bins[a['t']]
            g['alive'] += 1
            logged = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t']) + sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            other = (c['cmds'] - a['cmds']) - logged
            ratio = c['bal'] / max(1, pure_interest(a, c, M.land))
            if other >= 1:
                g['withCmd'] += 1
                g['cmds'] += other
            if other >= NOEFF_MIN_CMDS and ratio >= NOEFF_RATIO and c['terr'] <= NOEFF_GROW * a['terr']:
                g['noeff'] += 1
                g['noeffCmds'] += other
            if ratio < 0.5 and c['terr'] >= 0.9 * a['terr'] and not logged and a['bal'] >= 1000 and a['terr'] >= 50:
                k = math.log(max(ratio, 1e-9)) / math.log(0.868)
                g['dump'] += 1
                if k - max(0, other) >= 3:
                    g['over'] += 1
                    g['who'].append(f"{name_of(b)} k={k:.1f}/令{max(0, other)}")
    return [dict(t=t, **g) for t, g in sorted(bins.items())]


def sec_noefftl(M, t_from=NOEFF_T_FROM, t_to=3600):
    rows = noefftl_rows(M, t_from, t_to)
    print(f"「发令不见效 / 清仓」时间分布（只用日志；每档 = 起点在这一拍的 90 拍间隔；t={t_from}~{t_to}）")
    print('   起点拍｜有连续快照的号｜有令的号 / 指令条数｜不见效的号 / 条数｜清仓的号（余额 < 纯利息预测的一半、领土没丢、这段没有捐款/戳日志）｜其中超发（k − 新发指令 >= 3）')
    for r in rows:
        if not r['withCmd'] and not r['dump']:
            continue
        print(f"   t={r['t']:5d}｜{r['alive']:2d}｜{r['withCmd']:2d} / {r['cmds']:3d}｜{r['noeff']:2d} / {r['noeffCmds']:3d}｜{r['dump']:2d}｜{r['over']:2d} {'；'.join(r['who'])}")
    a = sum(r['cmds'] for r in rows)
    n = sum(r['noeffCmds'] for r in rows)
    print(f"   合计：指令 {a} 条，不见效 {n} 条（{100 * n / max(1, a):.1f}%）；清仓 {sum(r['dump'] for r in rows)} 段，其中超发 {sum(r['over'] for r in rows)} 段")
    for lo, hi in ((630, 1260), (1260, 1890), (1890, 2520), (2520, 3600)):
        sub = [r for r in rows if lo <= r['t'] < hi]
        a = sum(r['cmds'] for r in sub)
        n = sum(r['noeffCmds'] for r in sub)
        print(f"      t={lo}~{hi}：指令 {a} 条，不见效 {n} 条（{100 * n / max(1, a):.1f}%）；清仓 {sum(r['dump'] for r in sub)} 段、超发 {sum(r['over'] for r in sub)} 段")


def sentchk_rows(M):
    """结算行的 sent / accepted（外层数的「发给服务器 / 服务器收下」的指令条数，含选点）对
    策略自己数的 cmds（最后一条快照）+ 日志 HL-SPAWN 行数。
    两边对得上 = cmds 计数没有漏掉任何一条发出去的指令（策略里有几处不记 cmds 的出兵：
    handoffFootholds L3537/L3543、reigniteNewBorders L3597、retreat L2126/L4641）。"""
    out = []
    for me, b in sorted(M.bots.items()):
        r = b.result
        if not r or not str(r.get('sent', '')).strip().isdigit():
            continue
        last = b.traj[-1] if b.traj else None
        cm = last['cmds'] if last else 0
        sp = len(b.spawns)
        acc = int(r['accepted']) if str(r.get('accepted', '')).strip().isdigit() else None
        out.append(dict(me=me, name=name_of(b), team=b.team, sent=int(r['sent']), accepted=acc, cmds=cm, spawnLines=sp,
                        diff=int(r['sent']) - cm - sp, lastSnap=(last['t'] if last else None), outT=int(r['tick']), event=r['event']))
    return out


def sec_sentchk(M):
    rows = sentchk_rows(M)
    print('外层计数对表：结算行 sent / accepted（发给服务器 / 服务器收下的指令条数，含选点）对 策略 cmds（最后一条快照）+ 日志 HL-SPAWN 行数')
    print('   号(队)｜sent / accepted｜cmds（最后快照拍）+ HL-SPAWN 行｜差 = sent − (cmds + 选点行)｜最后快照到结算行隔了多少拍')
    for r in rows:
        gap = (r['outT'] - r['lastSnap']) if r['lastSnap'] is not None else None
        print(f"   {r['name']:13s}(队{r['team']})｜{r['sent']:4d} / {r['accepted'] if r['accepted'] is not None else '-':>4}｜{r['cmds']:4d}（t={r['lastSnap']}）+ {r['spawnLines']:2d}｜{r['diff']:+d}｜{gap if gap is not None else '-'}")
    played = [r for r in rows if r['lastSnap'] is not None]
    ds = sorted(r['diff'] for r in played)
    print(f"   有快照的 {len(played)} 个号：sent 合计 {sum(r['sent'] for r in played)}，cmds + 选点行合计 {sum(r['cmds'] + r['spawnLines'] for r in played)}；"
          f"差的分布 {dict(Counter(ds))}；sent − accepted 合计 {sum(r['sent'] - (r['accepted'] or 0) for r in played)}")
    nop = [r for r in rows if r['lastSnap'] is None]
    for r in nop:
        print(f"   没有任何快照的席位 {r['name']}：sent {r['sent']} / accepted {r['accepted']}，日志 HL-SPAWN {r['spawnLines']} 行（选点全部发出并被收下；录像里生效几条见 digest picks）")


ZDROP_RATIO = 0.75        # 余额 < 纯利息预测的几成算「掉了」
ZDROP_KEEP_LAND = 0.98    # 领土没丢（c.terr >= 这个比例 × a.terr）


def zerodrop_rows(M, t_from=NOEFF_T_FROM, t_to=10 ** 9):
    """零新令的余额下跌（只用日志）：相邻快照 [a, c]（相隔 90 拍）里 cmds 与 boats 计数都没动、没有捐款/戳日志，
    领土没丢，而余额 < 纯利息预测 × ZDROP_RATIO。配上 sentchk（cmds 没有漏数）⇒ 这笔支出只能来自这一段之前发的指令。
    发令到见效的间隔：下界 lastCmdGapMin = 这一段起点 − 上一批指令所在间隔的终点（最晚发、最早见效）；
    上界 lastCmdGap = 这一段终点 − 上一批指令所在间隔的起点（最早发、最晚见效）。"""
    out = []
    for me, b in sorted(M.bots.items()):
        tr = [x for x in b.traj if x['t'] >= 90]
        last_change = None          # 最近一个 cmds 有变动的间隔 (a.t, c.t, 条数, 其中发船)
        for a, c in zip(tr, tr[1:]):
            dc = c['cmds'] - a['cmds']
            if dc > 0:
                last_change = (a['t'], c['t'], dc, c['boats'] - a['boats'])
                continue
            if c['t'] - a['t'] != 90 or not (t_from <= a['t'] <= t_to):
                continue
            if c['boats'] != a['boats'] or a['bal'] < 1000 or a['terr'] < 50 or c['terr'] < ZDROP_KEEP_LAND * a['terr']:
                continue
            ratio = c['bal'] / max(1, pure_interest(a, c, M.land))
            if ratio >= ZDROP_RATIO:
                continue
            out.append(dict(me=me, name=name_of(b), team=b.team, t0=a['t'], t1=c['t'], bal0=a['bal'], bal1=c['bal'], ratio=ratio,
                            terr0=a['terr'], terr1=c['terr'], nb=a['nb'], neut=a['neut'],
                            lastCmdIv=last_change, lastCmdGap=(c['t'] - last_change[0]) if last_change else None,
                            lastCmdGapMin=(a['t'] - last_change[1]) if last_change else None))
    return out


def sec_zerodrop(M, t_from=NOEFF_T_FROM, t_to=10 ** 9):
    rows = zerodrop_rows(M, t_from, t_to)
    print(f"零新令的余额下跌（只用日志）：相邻快照间 cmds、boats 都没动、没有捐款/戳日志、领土 >= {ZDROP_KEEP_LAND:.2f}× 起点，而余额 < 纯利息预测 × {ZDROP_RATIO}")
    print('   号(队)｜间隔｜余额｜余额/纯利息预测｜领土｜nb neut｜上一批指令发在哪个间隔（条数，其中发船）→ 发令到见效隔了多少拍（下界~上界）')
    for r in rows:
        lc = r['lastCmdIv']
        print(f"   {r['name']:13s}(队{r['team']})｜t={r['t0']}~{r['t1']}｜{fmt(r['bal0'])}→{fmt(r['bal1'])}｜{r['ratio']:.2f}｜{r['terr0']}→{r['terr1']}｜{r['nb']} {r['neut']}｜"
              + (f"t={lc[0]}~{lc[1]}（{lc[2]} 条，船 {lc[3]}）→ {r['lastCmdGapMin']}~{r['lastCmdGap']} 拍" if lc else '此前没有指令'))
    by = defaultdict(list)
    for r in rows:
        by[r['t0']].append(r['name'])
    print(f"   合计 {len(rows)} 段、{len({r['me'] for r in rows})} 个号；按起点拍：" + '；'.join(f"t={t} {len(v)}（{'、'.join(v)}）" for t, v in sorted(by.items())))
    for lo, hi in ((630, 1260), (1260, 1890), (1890, 2520), (2520, 3600), (3600, 10 ** 9)):
        sub = [r for r in rows if lo <= r['t0'] < hi]
        if sub:
            print(f"      t={lo}~{hi if hi < 10 ** 9 else '终局'}：{len(sub)} 段、{len({r['me'] for r in sub})} 个号，掉的兵合计 {fmt(sum(r['bal0'] - r['bal1'] for r in sub))}；"
                  f"发令到见效的下界 中位 {_median([r['lastCmdGapMin'] for r in sub if r['lastCmdGapMin'] is not None])} 拍")


def gaps_rows(M):
    """缺掉的 HL-TICK 快照。策略只在「本机拍是 90 的倍数、且这一拍 act() 走到了打印处」时打一条快照（c110 L4797 / L4822）；
    act() 开头有 `if (!g.canAct(me)) return`（L4782）。所以首尾快照之间缺掉的 90 的倍数 = 那一拍策略没被调用或被 canAct 挡回。
    对局包里没有适配层（LiveGame.canAct）的代码，缺口的成因只能推断：本机快进追帧时一批拍只调一次策略、或那一拍不许下令。"""
    out = []
    for me, b in sorted(M.bots.items()):
        have = {s['t'] for s in b.traj}
        if not have:
            continue
        lo, hi = min(have), max(have)
        miss = [t for t in range(lo, hi + 1, 90) if t not in have]
        out.append(dict(me=me, name=name_of(b), team=b.team, first=lo, last=hi, n=len(have), miss=miss))
    return out


def sec_gaps(M):
    rows = gaps_rows(M)
    tot = sum(r['n'] + len(r['miss']) for r in rows)
    mis = sum(len(r['miss']) for r in rows)
    print(f"缺掉的 HL-TICK 快照（首尾快照之间、拍号是 90 的倍数却没有打印）：{mis} 个 / 应有 {tot} 个（{100 * mis / max(1, tot):.1f}%）；涉及 {sum(1 for r in rows if r['miss'])} 个号")
    for r in rows:
        if r['miss']:
            print(f"   {r['name']:13s}(队{r['team']}) 缺 {len(r['miss']):2d} / {r['n'] + len(r['miss']):3d}：" + ' '.join(str(t) for t in r['miss']))
    by = defaultdict(list)
    for r in rows:
        for t in r['miss']:
            by[t].append(r['name'])
    alive = lambda t: sum(1 for r in rows if r['first'] <= t <= r['last'])
    print('   按拍（缺的号数 / 那一拍应有快照的号数）：' + '；'.join(f"t={t} {len(v)}/{alive(t)}" for t, v in sorted(by.items())))
    for lo, hi in ((90, 630), (630, 1260), (1260, 1890), (1890, 3600), (3600, 10 ** 9)):
        n = sum(len(v) for t, v in by.items() if lo <= t < hi)
        d = sum(alive(t) for t in range(90, 20000, 90) if lo <= t < hi)
        if d:
            print(f"      t={lo}~{hi if hi < 10 ** 9 else '终局'}：缺 {n} / 应有 {d}（{100 * n / d:.1f}%）")


THIN_DENS = 12            # 「薄」的密度上限
THIN_MIN_LEN = 450        # 连续多少拍
THIN_BIG = 2.0            # 领土 >= 在场我方号中位的几倍
THIN_FALL_T = 300         # 到顶之后多少拍内
THIN_FALL = 0.6           # 领土跌到峰值的几成以下（即跌 >=40%）


def _median(v):
    v = sorted(v)
    n = len(v)
    return 0 if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def thinbig_rows(M):
    """NEW:EC-thin-big-target：密度 <12 连续 >=450 拍，其间领土到过在场我方号中位的 2 倍以上且 nb>=1；到顶之后 300 拍内领土跌 >=40%（或阵亡）。"""
    med = {}
    def med_at(t):
        if t not in med:
            med[t] = _median([x['terr'] for bb in M.bots.values() for x in bb.traj if x['t'] == t])
        return med[t]
    out = []
    for me, b in sorted(M.bots.items()):
        tr = b.traj
        i = 0
        while i < len(tr):
            if tr[i]['dens'] >= THIN_DENS:
                i += 1
                continue
            j = i
            while j + 1 < len(tr) and tr[j + 1]['dens'] < THIN_DENS and tr[j + 1]['t'] - tr[j]['t'] <= 270:
                j += 1
            run = tr[i:j + 1]
            if run[-1]['t'] - run[0]['t'] >= THIN_MIN_LEN:
                big = [x for x in run if x['nb'] >= 1 and x['terr'] >= THIN_BIG * med_at(x['t'])]
                if big:
                    pk = max(big, key=lambda x: x['terr'])
                    after = [x for x in tr if pk['t'] < x['t'] <= pk['t'] + THIN_FALL_T]
                    dt = death_tick(b)
                    low = min((x['terr'] for x in after), default=pk['terr'])
                    dead = dt is not None and dt <= pk['t'] + THIN_FALL_T
                    if dead or low <= THIN_FALL * pk['terr']:
                        out.append(dict(me=me, name=name_of(b), team=b.team, t0=run[0]['t'], t1=run[-1]['t'], peakT=pk['t'], peak=pk['terr'], median=med_at(pk['t']),
                                        dens=round(pk['dens'], 1), nb=pk['nb'], low=0 if dead else low, died=dt))
            i = j + 1
    return out


def sec_thinbig(M):
    rows = thinbig_rows(M)
    print(f"又大又薄（NEW:EC-thin-big-target；只用日志）：密度 <{THIN_DENS} 连续 >={THIN_MIN_LEN} 拍，其间领土到过在场我方号中位的 {THIN_BIG:g} 倍以上且 nb>=1；到顶之后 {THIN_FALL_T} 拍内领土跌 >=40% 或阵亡：{len(rows)} 次")
    for r in rows:
        print(f"   {r['name']:13s}(队{r['team']}) 薄的时段 t={r['t0']}~{r['t1']}；领土峰值 t={r['peakT']} {r['peak']} 格（当时在场我方号中位 {r['median']:.0f}，密度 {r['dens']}，nb={r['nb']}）"
              f" → {THIN_FALL_T} 拍内最低 {r['low']} 格" + (f"；阵亡 t={r['died']}" if r['died'] else ''))


# ------------------------------------------------------------------ fireband（有可打的邻居时，按密度档看「这 90 拍里发没发出兵/发船指令」）
FIRE_BANDS = [(0, 50), (50, 90), (90, 100), (100, 114), (114, 126), (126, 137), (137, 142), (142, 150.1)]


def fireband_rows(M, t_from=2070, t_to=10 ** 9, names=None):
    """相邻快照间隔（起点 nb>=1、领土>=200）：按起点密度分档，数 间隔数 / 有出兵或发船指令的 / 在丢地的（-1% 以上）/ 丢地且零出兵的。
    档位边界 114、137、142 是 buyLand 超软上限后 keep=0.9/1.08/1.12×100×领土 时「可用兵 >= 20% 余额」对应的密度。"""
    cnt = {b: dict(n=0, fire=0, lose=0, loseIdle=0) for b in FIRE_BANDS}
    for me, b in sorted(M.bots.items()):
        if names and name_of(b) not in names:
            continue
        for a, c in zip(b.traj, b.traj[1:]):
            if a['t'] < t_from or c['t'] > t_to or a['nb'] < 1 or a['terr'] < 200:
                continue
            dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
            ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            ot = (c['cmds'] - a['cmds']) - dn - ps
            for band in FIRE_BANDS:
                if band[0] <= a['dens'] < band[1]:
                    x = cnt[band]
                    x['n'] += 1
                    x['fire'] += ot > 0
                    lose = c['terr'] < 0.99 * a['terr']
                    x['lose'] += lose
                    x['loseIdle'] += lose and ot <= 0
    return [dict(lo=k[0], hi=min(150, k[1]), **v) for k, v in cnt.items()]


def sec_fireband(M, t_from=2070, t_to=10 ** 9, names=None):
    rows = fireband_rows(M, t_from, t_to, names)
    who = '、'.join(names) if names else '全部号'
    print(f"按密度档看出手（{who}，t>={t_from}{'' if t_to >= 10 ** 9 else '~' + str(t_to)}，起点 nb>=1 的快照间隔）：密度档｜间隔数｜有出兵/发船指令｜在丢地｜丢地且零出兵")
    for r in rows:
        if r['n']:
            print(f"   {r['lo']:>3.0f}~{r['hi']:<3.0f}｜{r['n']:4d}｜{r['fire']:4d}（{100 * r['fire'] / r['n']:.0f}%）｜{r['lose']:4d}｜{r['loseIdle']:4d}")
    lo = [r for r in rows if r['hi'] <= 100]
    hi = [r for r in rows if r['lo'] >= 100]
    for lab, rs in (('密度 <100', lo), ('密度 >=100', hi), ('密度 >=114', [r for r in rows if r['lo'] >= 114])):
        n = sum(r['n'] for r in rs)
        if n:
            print(f"   {lab}：间隔 {n}，有出兵/发船 {sum(r['fire'] for r in rs)}（{100 * sum(r['fire'] for r in rs) / n:.1f}%），在丢地 {sum(r['lose'] for r in rs)}，丢地且零出兵 {sum(r['loseIdle'] for r in rs)}")


# ------------------------------------------------------------------ capidle（满仓不动 → 被吃）
CAPIDLE_LEN = 600
CAPIDLE_DENS = 140.0
CAPIDLE_LOSS = 0.75


def capidle_rows(M):
    """连续 >=600 拍 cmds/boats 计数不变（捐款、协防戳也算指令）、期间密度到过 >=140，
    且「这一段里」或「之后 600 拍内」领土跌到段首的 75% 以下，或在之后 600 拍内阵亡。"""
    out = []
    for r in silent_rows(M, CAPIDLE_LEN):
        if r['densMax'] < CAPIDLE_DENS:
            continue
        b = M.bots[r['me']]
        after = [s for s in b.traj if r['t1'] < s['t'] <= r['t1'] + 600]
        low_after = min((s['terr'] for s in after), default=r['terr1'])
        died = r['deathT'] is not None and r['deathT'] <= r['t1'] + 600
        lost_in = r['terr1'] < CAPIDLE_LOSS * r['terr0']
        lost_after = low_after < CAPIDLE_LOSS * r['terr1']
        if died or lost_in or lost_after:
            out.append(dict(r, lowAfter=low_after, died=died, lostIn=lost_in, lostAfter=lost_after))
    return out


def sec_capidle(M):
    rows = capidle_rows(M)
    print(f"满仓不动 → 被吃：连续 >={CAPIDLE_LEN} 拍零指令且期间密度到过 >={CAPIDLE_DENS:.0f}，段内或之后 600 拍领土跌到 {CAPIDLE_LOSS:.0%} 以下 / 阵亡：{len(rows)} 段")
    for r in rows:
        tail = f"，{r['deathT'] - r['t1']} 拍后阵亡" if r['died'] else f"，之后 600 拍最低 {r['lowAfter']}"
        print(f"   {r['name']:14s} t={r['t0']}~{r['t1']}（{r['len']} 拍）nb {r['nbMin']}~{r['nbMax']}；密度 {r['dens0']:.0f}→{r['dens1']:.0f}（最高 {r['densMax']:.0f}）；领土 {r['terr0']}→{r['terr1']}；兵 {fmt(r['bal0'])}→{fmt(r['bal1'])}{tail}")


# ------------------------------------------------------------------ quotacap（按引擎受捐额度公式：一个收款人最多能收多少）
QC_TICKS = [1100, 1500, 1800, 2141, 2142, 2500, 3000, 3212, 3213, 3600, 4000, 4283]


def quotacap_rows(M, recv_terr=5000):
    """引擎受捐额度（r06lib.quota_limit / quota_points，逐项对过 live-donation-check.txt）：上限全场共用、只随拍号涨；用量按收款人累计、整局不清零。
    每个拍号给：上限点数；「额度一点没用过」时这一拍单笔最多能到账多少（二分 quota_points<=上限）；
    以及从这一拍起每 100 拍新涨的额度够收多少（=稳态流量，已扣掉每笔固定的 2 或 4 点，按每 100 拍只收一笔算）。"""
    out = []
    for t in QC_TICKS:
        lim = quota_limit(t)
        lo, hi = 0, 10 ** 9
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if quota_points(t, mid, M.land, recv_terr) <= lim:
                lo = mid
            else:
                hi = mid - 1
        step = 4 if t < 1071 else 6 if t < 2142 else 8 if t < 3213 else 10
        lo2, hi2 = 0, 10 ** 9
        while lo2 < hi2:
            mid = (lo2 + hi2 + 1) // 2
            if quota_points(t, mid, M.land, recv_terr) <= step:
                lo2 = mid
            else:
                hi2 = mid - 1
        out.append(dict(t=t, limit=lim, maxOnce=lo, per100=lo2, step=step))
    return out


def sec_quotacap(M, recv_terr=5000):
    uv = 1 + M.land // 300
    print(f"受捐额度封顶（引擎公式；本图陆地 {M.land} → uv={uv}；t>=3213 的一档按收款人 {recv_terr} 格算；t>=4284 不再检查）")
    print("   拍｜上限点数｜额度没用过时单笔最多到账｜此后每 100 拍新增额度（+点数）够收")
    for r in quotacap_rows(M, recv_terr):
        print(f"   t={r['t']:>4}｜{r['limit']:>4}｜{fmt(r['maxOnce']):>8}｜+{r['step']} 点 → {fmt(r['per100'])}")
    print("   用量按收款人累计、整局不清零：上一档里收过的点数照样占着后面的上限。")


# ------------------------------------------------------------------ freezebound（满仓不出手 ⇒ 按代码反推「最强敌邻至少多少兵」）
FB_CHUNK = 0.2          # P17.chunk：没到 want 时至少要出余额的 20%（c110 L5528）
FB_FEE = 12 / 1024      # 陆攻手续费
FB_KEEPS = ((0.9, 'hold'), (1.12, 'overHumanKeep'))   # 超软上限后 keep = min(keep, 倍数×100×领土)（c110 L5348-5357）


def freezebound_rows(M, t_from=1500):
    """相邻快照间隔（起点 nb>=1、领土>=200、密度>100、t>=t_from）且这段里没有出兵/发船指令。
    c110 超软上限后的出兵条件（没有录像时只能按代码反推，不是实测）：
      keep = max(倍数×100×L, safe)，avail = B − fee − keep，要出手需 avail >= chunk×B（或够一口吃光，这里不算）；
      safe = max(safeFinite, dpKeep)，dpKeep = (最强敌方真人邻居的兵 + 它打我的在途兵 − 1.5×L)/1.78（L2491-2496、L2744-2754）。
    所以「倍数×100×L 这一项不拦」（密度够高）而仍然不出手 ⇒ safe > (1−fee−chunk)×B ⇒ 若 safe 取自 dpKeep，最强敌邻的兵 > 1.78×(1−fee−chunk)×B + 1.5×L。
    每个号给：这样的间隔数，以及其中余额最高那个快照的反推下界（两档 keep 各算一次：密度 >=114.2 用 0.9，>=142.1 用 1.12）。"""
    out = []
    for me, b in sorted(M.bots.items()):
        rows = []
        for a, c in zip(b.traj, b.traj[1:]):
            if a['t'] < t_from or a['nb'] < 1 or a['terr'] < 200 or a['dens'] <= 100:
                continue
            dn = sum(1 for e in b.donations if a['t'] <= e['t'] < c['t'])
            ps = sum(1 for e in b.assists if a['t'] <= e['t'] < c['t'])
            if (c['cmds'] - a['cmds']) - dn - ps > 0:
                continue
            B, L = a['bal'], a['terr']
            free = (1 - FB_FEE - FB_CHUNK) * B
            ok = [(k, lab) for k, lab in FB_KEEPS if k * 100 * L <= free]
            rows.append(dict(t=a['t'], bal=B, terr=L, dens=a['dens'], nb=a['nb'], keeps=[lab for _, lab in ok],
                             bound=int(1.78 * free + 1.5 * L) if ok else None, lost=a['terr'] - c['terr']))
        if not rows:
            continue
        hit = [r for r in rows if r['bound'] is not None]
        top = max(hit, key=lambda r: r['bal']) if hit else None
        out.append(dict(me=me, name=name_of(b), team=b.team, n=len(rows), nHit=len(hit), nHit112=sum(1 for r in hit if 'overHumanKeep' in r['keeps']),
                        top=top, t0=rows[0]['t'], t1=rows[-1]['t'], lostIdle=sum(max(0, r['lost']) for r in rows)))
    return out


def sec_freezebound(M, t_from=1500):
    rows = freezebound_rows(M, t_from)
    print(f"满仓不出手的反推下界（t>={t_from}；起点 nb>=1、密度>100 且这 90 拍里没有出兵/发船指令的快照间隔）。按 c110 buyLand 超软上限分支反推，不是实测：")
    print("   keep=max(倍数×100×地, safe)；要出手需 兵−手续费−keep >= 20%×兵。倍数 0.9 时密度 >=114.2 这一项就不拦、1.12（唯一真人邻居）时 >=142.1；")
    print("   这一项不拦而仍不出手 ⇒ safe > 78.8%×兵；safe 取自 dpKeep 时 ⇒ 最强敌方真人邻居的兵（加它打我的在途兵）> 1.403×兵 + 1.5×地")
    print("   注意：日志的 nb>=1 只说明有非同队、非编队的邻居，是真人还是内置 AI 分不清；邻居只有内置 AI 时走的是另一条分支（L5363-5369），下界不适用")
    print("   号(队)｜这样的间隔数 拍范围｜其中密度>=114.2 的 / >=142.1 的｜余额最高那个快照：拍 兵 地 密度 nb → 敌邻下界（是我的几倍）｜这些间隔里丢的地")
    for r in rows:
        tp = r['top']
        if tp:
            s = f"t={tp['t']} 兵 {fmt(tp['bal'])} 地 {tp['terr']} 密度 {tp['dens']:.0f} nb={tp['nb']} → >{fmt(tp['bound'])}（{tp['bound'] / tp['bal']:.2f} 倍）"
        else:
            s = '（密度都不到 114.2：倍数这一项本身就拦住）'
        print(f"   {r['name']:13s}(队{r['team']})｜{r['n']:3d} t={r['t0']}~{r['t1']}｜{r['nHit']:3d} / {r['nHit112']:3d}｜{s}｜{r['lostIdle']}")
    n = sum(r['n'] for r in rows)
    print(f"   合计 {len(rows)} 个号、{n} 个间隔；其中密度 >=114.2 的 {sum(r['nHit'] for r in rows)} 个、>=142.1 的 {sum(r['nHit112'] for r in rows)} 个；这些间隔里共丢 {sum(r['lostIdle'] for r in rows)} 格")


# ------------------------------------------------------------------ foes（协防戳日志里点名的外人：在哪些队不可能）
def foes_rows(M):
    """HL-ASSIST 只在「对方是真人、不是我的队友、不是名字池里的号」时才打（c110 L4427-4428、L4448），被打的号也不可能和打它的人同队。
    → 每个被点名的外人，排除掉所有戳过它的号的队、所有被它打的号的队，剩下的就是它可能在的队。"""
    teams = sorted({b.team for b in M.bots.values() if b.team})
    foe = {}
    for me, b in M.bots.items():
        for e in b.assists:
            f = foe.setdefault(e['enemy'], dict(id=e['enemy'], name=e['enemyName'], n=0, t0=e['t'], t1=e['t'], pokers=defaultdict(int), victims=defaultdict(int), ex=set()))
            f['n'] += 1
            f['t0'] = min(f['t0'], e['t'])
            f['t1'] = max(f['t1'], e['t'])
            f['pokers'][me] += 1
            f['victims'][e['ally']] += 1
            if b.team:
                f['ex'].add(b.team)
            vb = M.bots.get(e['ally'])
            if vb and vb.team:
                f['ex'].add(vb.team)
    out = []
    for f in sorted(foe.values(), key=lambda f: -f['n']):
        out.append(dict(id=f['id'], name=f['name'], n=f['n'], t0=f['t0'], t1=f['t1'], pokers=dict(f['pokers']), victims=dict(f['victims']),
                        excluded=sorted(f['ex']), possible=[t for t in teams if t not in f['ex']]))
    return out


def sec_foes(M):
    rows = foes_rows(M)
    print('协防戳日志里点名的外人（日志只在对方是真人、非队友、非名字池的号时才打）：编号 名字｜条数 拍范围｜被它打的号｜戳它的号｜不可能在的队 → 可能在的队')
    for f in rows:
        vi = ' '.join(f"{name_of(M.bots[p]) if p in M.bots else p}(队{M.bots[p].team if p in M.bots else '?'})×{n}" for p, n in sorted(f['victims'].items(), key=lambda kv: -kv[1]))
        pk = ' '.join(f"{name_of(M.bots[p])}(队{M.bots[p].team})×{n}" for p, n in sorted(f['pokers'].items(), key=lambda kv: -kv[1]))
        print(f"   #{f['id']} {f['name']}｜{f['n']} 条 t={f['t0']}~{f['t1']}｜{vi}｜{pk}｜非 {f['excluded']} → 可能 {f['possible']}")


# ------------------------------------------------------------------ assists / opening / peace（纯日志计数）
def alive_at(b, t):
    r = b.result
    if r and r.get('event') in ('died', 'left') and r['tick'] <= t:
        return False
    return bool(b.traj) and b.traj[0]['t'] <= t


def cmds_delta(b, t0, t1):
    """[t0, t1] 内 cmds 计数的增量：取 <=t0 的最后一条快照与 <=t1 的最后一条快照之差。"""
    a = c = None
    for x in b.traj:
        if x['t'] <= t0:
            a = x
        if x['t'] <= t1:
            c = x
    if c is None:
        return None
    return c['cmds'] - (a['cmds'] if a else 0)


def assists_rows(M, t_from=0, t_to=10 ** 9):
    cnt = defaultdict(int)
    for me, b in M.bots.items():
        for e in b.assists:
            if t_from <= e['t'] <= t_to:
                cnt[(me, e['ally'], e['enemy'], e['enemyName'])] += 1
    return [dict(poker=k[0], ally=k[1], enemy=k[2], enemyName=k[3], n=n) for k, n in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0][:3]))]


def sec_assists(M, t_from=0, t_to=10 ** 9):
    rows = assists_rows(M, t_from, t_to)
    rng = '全局' if t_to >= 10 ** 9 and t_from == 0 else f"t={t_from}~{t_to}"
    print(f"协防戳日志（{rng}）：{sum(r['n'] for r in rows)} 条。戳的人(队) → 替谁(队) 戳 外人｜条数")
    for r in rows:
        pb, ab = M.bots[r['poker']], M.bots.get(r['ally'])
        print(f"   {name_of(pb)}(队{pb.team}) → 替 {name_of(ab) if ab else r['ally']}(队{ab.team if ab else '?'}) 戳 #{r['enemy']} {r['enemyName']}｜{r['n']}")
    if rows:
        who = sorted({r['poker'] for r in rows} | {r['ally'] for r in rows if r['ally'] in M.bots})
        hi = t_to if t_to < 10 ** 9 else max(b.traj[-1]['t'] for b in M.bots.values() if b.traj)
        print('   同一范围内各号 cmds 增量 / 其中协防戳日志 / 捐款日志：' + '；'.join(
            f"{name_of(M.bots[p])} {cmds_delta(M.bots[p], t_from, hi)} / {sum(1 for e in M.bots[p].assists if t_from <= e['t'] <= t_to)} / {sum(1 for e in M.bots[p].donations if t_from <= e['t'] <= t_to)}" for p in who))


def _pctl(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def opening_rows(M):
    out = []
    for me, b in sorted(M.bots.items()):
        ts = [o['t'] for o in b.opening]
        gaps = [y - x for x, y in zip(ts, ts[1:])]
        # 没生效的开局周期：下一条 HL-OPENING 时领土没变、余额也没少（这条周期指令没有在本机局面里执行）
        dead = [x['t'] for x, y in zip(b.opening, b.opening[1:]) if y['terr'] == x['terr'] and y['bal'] >= x['bal'] and x['t'] < 630]
        first_grow = next((y['t'] for x, y in zip(b.opening, b.opening[1:]) if y['terr'] > x['terr']), None)
        s630 = next((x for x in b.traj if x['t'] == 630), None)
        out.append(dict(me=me, name=name_of(b), n=len(ts), t0=(ts[0] if ts else None), t1=(ts[-1] if ts else None), gaps=gaps,
                        dead=dead, firstGrow=first_grow, terr630=(s630['terr'] if s630 else None)))
    return out


def sec_opening(M):
    rows = opening_rows(M)
    allg = [g for r in rows for g in r['gaps']]
    ts = [t for r in rows for t in (r['t0'], r['t1']) if t is not None]
    print(f"HL-OPENING：{sum(r['n'] for r in rows)} 行，{sum(1 for r in rows if r['n'])} 个号，t={min(ts) if ts else '-'}~{max(ts) if ts else '-'}；"
          f"同一个号相邻两条的间隔 {len(allg)} 个：中位 {_pctl(allg, 0.5)}、p10 {_pctl(allg, 0.1)}、p90 {_pctl(allg, 0.9)}")
    for r in rows:
        print(f"   {r['name']:14s} {r['n']:3d} 条 t={r['t0']}~{r['t1']} 间隔 {' '.join(str(g) for g in r['gaps'])}")
    late = [r for r in rows if r['dead']]
    ok = [r for r in rows if not r['dead'] and r['n']]
    med = lambda v: (sorted(v)[len(v) // 2] if v else None)
    print(f"   没生效的开局周期（t<630；下一条 HL-OPENING 时领土没变、余额没少）：{sum(len(r['dead']) for r in late)} 条、{len(late)} 个号；"
          f"这些号 t=630 领土中位 {med([r['terr630'] for r in late if r['terr630'] is not None])}，其余 {len(ok)} 个号中位 {med([r['terr630'] for r in ok if r['terr630'] is not None])}")
    for r in late:
        print(f"      {r['name']:14s} 没生效的周期 t={'、'.join(str(t) for t in r['dead'])}；下一条 HL-OPENING 看到领土变大是 t={r['firstGrow']}；t=630 领土 {r['terr630']}")


def peace_rows(M):
    import re
    out = []
    for line, name, rest in M.peace:
        m = re.search(r't=(\d+) (initiated peace vote|voted YES[^(]*)(?:.*?teamLand=([\d.]+)%)?', rest)
        if not m:
            out.append(dict(line=line, name=name, raw=rest))
            continue
        t = int(m.group(1))
        me = next((k for k, b in M.bots.items() if name in b.names), None)
        my_team = M.bots[me].team if me is not None else None
        others = defaultdict(list)
        for k, b in sorted(M.bots.items()):
            if k != me and b.team and b.team != my_team and alive_at(b, t):
                others[b.team].append(name_of(b))
        same = [name_of(b) for k, b in sorted(M.bots.items()) if k != me and b.team == my_team and alive_at(b, t)]
        out.append(dict(line=line, t=t, name=name, me=me, team=my_team, kind=('initiated' if m.group(2).startswith('initiated') else 'votedYes'),
                        teamLand=(float(m.group(3)) if m.group(3) else None), sameTeam=same, otherTeams={str(k): v for k, v in others.items()}))
    return out


def sec_peace(M):
    rows = peace_rows(M)
    ini = [r for r in rows if r.get('kind') == 'initiated']
    yes = [r for r in rows if r.get('kind') == 'votedYes']
    print(f"HL-PEACE：{len(rows)} 行（发起 {len(ini)}、投赞成 {len(yes)}）。拍｜谁(队)｜日志里的 teamLand｜同队在场的我方号｜别的队里在场的我方号")
    prev = None
    for r in rows:
        if 't' not in r:
            print('   解析不了：', r['raw'][:120])
            continue
        o = ' '.join(f"队{k}:{'、'.join(v)}" for k, v in sorted(r['otherTeams'].items())) or '无'
        gap = '' if prev is None else f"（距上一条 {r['t'] - prev} 拍）"
        prev = r['t']
        print(f"   t={r['t']}{gap}｜{r['name']}(队{r['team']}) {r['kind']}｜{r['teamLand']}%｜{'、'.join(r['sameTeam']) or '无'}｜{o}")
    n_other = sum(1 for r in ini if r['otherTeams'])
    print(f"   发起时别的队里还有我方号在场的：{n_other} / {len(ini)} 次")


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
        r = b.result or {}
        out.append(dict(me=me, name=name_of(b), t=s['t'], issued=s['cmds'], inReplay=rep, lastCmdT=max(cm[me]) if cm[me] else None, series=rows,
                        resSent=r.get('sent'), resAccepted=r.get('accepted')))
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
    ne = {x['me']: x for x in noeffect_rows(M, t_to=M.sim['endT'])}
    print("   对照（每个号）：号｜日志已发 − 录像里（没到的）｜noeffect 判成不见效的（只算 630<=t<=录像末拍 的其余指令）｜结算行 sent/accepted")
    xs, ys = [], []
    for r in R:
        n = ne.get(r['me'])
        miss = r['issued'] - r['inReplay']
        nn = n['noeff'] if n else 0
        xs.append(miss)
        ys.append(nn)
        print(f"      {r['name']:14s} 没到 {miss:4d}｜不见效 {nn:4d}｜sent/accepted {r['resSent']}/{r['resAccepted']}")
    full = all(not b.traj or b.traj[-1]['t'] <= M.sim['endT'] for b in M.bots.values())
    acc = [(r['resAccepted'], r['inReplay']) for r in R if r['resAccepted'] not in (None, '')]
    if acc and full:
        print(f"   结算行 accepted 合计 {sum(int(a) for a, _ in acc)} 条，对应这些号录像里只有 {sum(b for _, b in acc)} 条：accepted 是页面本地接口的返回值，不是服务器收到的条数")
    elif acc:
        print("   （录像没盖到终局，结算行 accepted 和录像条数不能直接比）")
    print(f"   没到合计 {sum(xs)}，noeffect 判成不见效合计 {sum(ys)}（noeffect 只数 t>=630、连着 >=2 条且余额一点没少的间隔，是下界式判据）")
    print(f"合计：已发 {ti} 条，录像里 {tr} 条（{100 * tr / max(1, ti):.1f}%）")


def build_json(M):
    doc = dict(matchId=M.id, stale=stale_rows(M), silent=silent_rows(M), drop30=drop30_rows(M), wall=wall_rows(M), overcap=overcap_rows(M))
    doc['donlog'] = donlog_rows(M)
    doc['cmdmix'] = [dict(r, seg=list(r['seg'])) for r in cmdmix_rows(M)]
    doc['idleloss'] = idleloss_rows(M)
    doc['capidle'] = capidle_rows(M)
    doc['spend'] = spend_rows(M)
    doc['fireband'] = fireband_rows(M)
    doc['foes'] = foes_rows(M)
    doc['assists'] = assists_rows(M)
    doc['opening'] = opening_rows(M)
    doc['peace'] = peace_rows(M)
    L = seqlag_rows(M)
    doc['seqlag'] = {str(me): dict(maxLag=max((d for _, d in v), default=0), lagSnaps=sum(1 for _, d in v if d >= 90), snaps=len(v)) for me, v in L.items()}
    o = oplag_rows(M)
    if o is not None:
        doc['oplag'] = {str(me): rows for me, rows in o.items()}
        doc['issued'] = [{k: v for k, v in r.items() if k != 'series'} for r in issued_rows(M)]
    hits, faded = burst_rows(M, 1440)
    doc['bursts1440'] = dict(hits=hits, faded=faded)
    doc['thinbig'] = thinbig_rows(M)
    doc['crumb'] = crumb_rows(M)
    doc['boxboats'] = boxboat_rows(M)
    doc['harvest'] = harvest_rows(M)
    doc['noeffect'] = noeffect_rows(M)
    doc['freezebound'] = [{k: v for k, v in r.items() if k != 'rows'} for r in freezebound_rows(M)]
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
    elif sec == 'wallms':
        sec_wallms(M)
    elif sec == 'overcap':
        sec_overcap(M)
    elif sec == 'oplag':
        sec_oplag(M)
    elif sec == 'donlog':
        sec_donlog(M, (int(sys.argv[3]) if len(sys.argv) > 3 else None))
    elif sec == 'donval':
        sec_donval(M)
    elif sec == 'cmdmix':
        sec_cmdmix(M)
    elif sec == 'foes':
        sec_foes(M)
    elif sec == 'assists':
        a = [int(x) for x in sys.argv[3:5]]
        sec_assists(M, *(a if len(a) == 2 else ()))
    elif sec == 'opening':
        sec_opening(M)
    elif sec == 'peace':
        sec_peace(M)
    elif sec == 'idleloss':
        sec_idleloss(M)
    elif sec == 'capidle':
        sec_capidle(M)
    elif sec == 'fireband':
        a = sys.argv[3:]
        nums = [int(x) for x in a if x.lstrip('-').isdigit()]
        nm = [x for x in a if not x.lstrip('-').isdigit()]
        sec_fireband(M, *(nums[:2] if nums else ()), names=(nm or None))
    elif sec == 'spend':
        a = [int(x) for x in sys.argv[3:5]]
        sec_spend(M, *(a if len(a) == 2 else ()))
    elif sec == 'issued':
        sec_issued(M)
    elif sec == 'bursts':
        sec_bursts(M, *([int(sys.argv[3])] if len(sys.argv) > 3 else []))
    elif sec == 'thinbig':
        sec_thinbig(M)
    elif sec == 'crumb':
        sec_crumb(M)
    elif sec == 'noeffect':
        sec_noeffect(M, *([int(sys.argv[3])] if len(sys.argv) > 3 else []))
    elif sec == 'noefftl':
        sec_noefftl(M, *[int(x) for x in sys.argv[3:5]])
    elif sec == 'gaps':
        sec_gaps(M)
    elif sec == 'sentchk':
        sec_sentchk(M)
    elif sec == 'zerodrop':
        sec_zerodrop(M, *[int(x) for x in sys.argv[3:5]])
    elif sec == 'harvest':
        sec_harvest(M, *([int(sys.argv[3])] if len(sys.argv) > 3 else []))
    elif sec == 'boxboats':
        sec_boxboats(M)
    elif sec == 'freezebound':
        sec_freezebound(M, *( [int(sys.argv[3])] if len(sys.argv) > 3 else [] ))
    elif sec == 'quotacap':
        sec_quotacap(M, *( [int(sys.argv[3])] if len(sys.argv) > 3 else [] ))
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
