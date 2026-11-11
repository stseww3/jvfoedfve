#!/usr/bin/env python3
"""shadow_report.py — 读 shadow.mjs 的产物（out/<mid>/shadow_*.csv），按节打印影子策略的机械统计。

用法：python3 shadow_report.py <matchId> [--section check,flow,chunks,bursts,paths,list] [--bot name]
                                [--t0 N --t1 N] [--win 300] [--tag x] [--strategy vb|va|c110]
节：
  check   影子与日志的三重校验汇总（HL-TICK 点数、OPENING/DISPATCH 行数在 shadow.mjs 的标准输出里，这里只汇总 HL-TICK）
  flow    每个号按决策拍分窗：策略发出几条、录像里落地几条、丢了几条、落地的延迟（中位/最大）
  chunks  成块补帧：每次落地（号, 落地拍）→ 留下的是哪几拍的决策、延迟；并按“下一块的跨度 = 上一块处理用掉的真实时间”
          反推每块每个游戏拍用掉的真实毫秒数（56 = 刚好跟得上）
  bursts  同一拍落地 >=3 条的组：决策拍区间、决策时想出的兵、执行时实际扣的兵、占执行前余额的比例、代码行
  paths   指令按代码位置（类.方法:行）分类：发出 / 落地
  lagcurve 全队合计的延迟曲线（按决策拍分窗）
  repeat  正常延迟下同一决策被重复下令几次（在途无记账的常态代价）
  donate  每条捐款决策的去向：落地 / 到了引擎没生效（配额等）/ 堵在通道里；需要先跑 dispatch_audit.mjs 才有配额列
  overprice 对真人的陆攻令按 发令时余额是否过 100 倍领土（over，buyLand 因此不做 c>=worth 的熔断）× 报价单价 c 是否 >= 愿付价 worth
          分四类：受理条数、想出的兵、落地条数、落地时实扣；over 且 c>=worth 的一类再按号、按目标列出（需要新版 shadow.mjs 的 c/worth/over 列）
  list    --bot 必填：该号在 [t0,t1] 的逐条决策（t, 类型, pct, 目标, 余额, 想出的兵, 落地拍, 代码行）
"""
import argparse
import csv
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
STRAT_DIR = '/agent/repos/c136-data/src/strategy'
STRAT_FILES = {'va': 'v27-team-c116-va.js', 'vb': 'v27-team-c116-vb.js', 'c116': 'v27-team-c116.js', 'c110': 'v27-team-c110.js', 'g09': 'v27-team-g09.js'}
VA = {'A003', 'A005', 'A009'}


def strategy_key(mid):
    if mid.startswith('B'):
        return 'c110'
    return 'va' if mid in VA else 'vb'


def outline(key):
    """行号 -> '类.方法'（按缩进两格的方法声明和顶层 function/class 粗分）。"""
    path = os.path.join(STRAT_DIR, STRAT_FILES[key])
    spans = []  # (startLine, name)
    cls = None
    for i, line in enumerate(open(path, encoding='utf8'), 1):
        m = re.match(r'^(?:export )?class (\w+)', line)
        if m:
            cls = m.group(1)
            continue
        m = re.match(r'^(?:export )?(?:async )?function (\w+)', line)
        if m:
            cls = None
            spans.append((i, m.group(1)))
            continue
        if line.startswith('}'):
            cls = None if not line.startswith('})') else cls
        m = re.match(r'^  (?:async )?(\w+)\((.*)\) \{\s*$', line)
        if m and cls and m.group(1) not in ('if', 'for', 'while', 'switch'):
            spans.append((i, f'{cls}.{m.group(1)}'))
    spans.sort()
    starts = [s[0] for s in spans]

    def name_of(ln):
        import bisect
        k = bisect.bisect_right(starts, ln) - 1
        return spans[k][1] if k >= 0 else '?'
    return name_of


def nice_path(path, name_of, depth=3):
    """'Policy.send:484<Policy.send:1827<...<Policy.buyLand:5616<Policy.act:4942' -> 'Policy.buyLand L5616 ← Policy.act L4942'"""
    fr = []
    for f in path.split('<'):
        m = re.match(r'.*:(\d+)$', f)
        if not m:
            continue
        ln = int(m.group(1))
        nm = name_of(ln)
        if nm.endswith('.send'):
            continue
        fr.append(f'{nm} L{ln}')
    return ' ← '.join(fr[:depth])


def load(mid, name, tag=''):
    p = os.path.join(OUT, mid, f'{name}{"_" + tag if tag else ""}.csv')
    if not os.path.exists(p):
        sys.exit(f'缺 {p}，先跑 node scripts/shadow.mjs {mid}')
    return list(csv.DictReader(open(p, encoding='utf8')))


def med(a):
    return int(statistics.median(a)) if a else '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mid')
    ap.add_argument('--section', default='check,flow,chunks,bursts,paths')
    ap.add_argument('--bot')
    ap.add_argument('--t0', type=int, default=0)
    ap.add_argument('--t1', type=int, default=10**9)
    ap.add_argument('--win', type=int, default=300)
    ap.add_argument('--tag', default='')
    ap.add_argument('--strategy')
    ap.add_argument('--min-n', type=int, default=3)
    ap.add_argument('--min-lag', type=int, default=60)
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--floor-from', type=int, default=700, help='idle 节：只列 t0 不早于这一拍的 floor 窗口（开局期的留兵是 DP 计划内的）')
    a = ap.parse_args()
    mid = a.mid
    secs = a.section.split(',')
    name_of = outline(a.strategy or strategy_key(mid))
    cmds = load(mid, 'shadow_cmds', a.tag)
    match = load(mid, 'shadow_match', a.tag)
    bots = []
    for r in cmds:
        if r['bot'] not in bots:
            bots.append(r['bot'])
    if a.bot:
        bots = [b for b in bots if b == a.bot or b.endswith(':' + a.bot)]

    if 'check' in secs:
        ck = load(mid, 'shadow_check', a.tag)
        print(f'== {mid} 校验：影子吐出的 [HL-TICK] 对日志 [HL-TICK]（nb / neut / cmds / boats 四项全同才算同）')
        by = defaultdict(list)
        for r in ck:
            by[r['bot']].append(r)
        tot = ok = 0
        for b, rows in by.items():
            n_ok = sum(1 for r in rows if r['ok'] == '1')
            tot += len(rows)
            ok += n_ok
            bad = next((r for r in rows if r['ok'] != '1'), None)
            print(f'  {b:14s} {n_ok}/{len(rows)}' + (f'  首个不同 t={bad["t"]} 日志 nb/neut/cmds/boats={bad["logNb"]}/{bad["logNeut"]}/{bad["logCmds"]}/{bad["logBoats"]} 影子 {bad["shNb"]}/{bad["shNeut"]}/{bad["shCmds"]}/{bad["shBoats"]}' if bad else ''))
        print(f'  合计 {ok}/{tot}')
        bad_all = [r for r in ck if r['ok'] != '1']
        if bad_all:
            only_boat = sum(1 for r in bad_all
                            if r['logNb'] == r['shNb'] and r['logNeut'] == r['shNeut']
                            and int(r['shCmds']) - int(r['logCmds']) == int(r['shBoats']) - int(r['logBoats']))
            print(f'  不同的 {len(bad_all)} 个快照里，nb / neut 相同且 cmds 的差正好等于 boats 的差（即只差在船指令的受理上）：{only_boat} 个')
            for b, rows in by.items():
                r = rows[-1]
                if r['logBoats'] != r['shBoats']:
                    print(f'    {b:14s} 最后一个快照 t={r["t"]}：日志 cmds/boats={r["logCmds"]}/{r["logBoats"]}，影子 {r["shCmds"]}/{r["shBoats"]}；'
                          f'除船以外的指令 日志 {int(r["logCmds"]) - int(r["logBoats"])} 影子 {int(r["shCmds"]) - int(r["shBoats"])}')

    if 'idle' in secs:
        idle = load(mid, 'shadow_idle', a.tag)
        print(f'\n== {mid} 闲置审计（每个决策拍归一类；按号汇总 [{a.t0},{min(a.t1, 99999)}]）')
        print('   cmd=发了指令 boxed=没有可打的邻居也没有中立地 dp=1500 拍前还有中立地、按租期等待 floor/floorN=身边有机器人地但保底线 winFloor>=余额（1500 拍前；floorN 是身边还剩中立地时） other=其余 cap=余额顶在 150 倍领土')
        byb = defaultdict(list)
        for r in idle:
            if a.t0 <= int(r['t0']) <= a.t1:
                byb[r['bot']].append(r)

        def runs(rows, pred):
            out = []
            cur = None
            for r in rows:
                t0 = int(r['t0'])
                if pred(r):
                    if cur and t0 == cur[1] + 100:
                        cur[1] = t0
                    else:
                        cur = [t0, t0]
                        out.append(cur)
            return ' '.join(f'{x}-{y + 99}' for x, y in out) or '无'

        tot = defaultdict(int)
        for b in [x for x in bots if x in byb] + [x for x in byb if x not in bots]:
            rows = byb[b]
            n = sum(int(r['acts']) for r in rows)
            c = {k: sum(int(r[k]) for r in rows) for k in ('cmd', 'boxed', 'dp', 'floor', 'floorN', 'other', 'cap')}
            for k, v in c.items():
                tot[k] += v
            tot['acts'] += n
            print(f"  {b:12s} 决策拍 {n:5d} | cmd {c['cmd']:4d} boxed {c['boxed']:5d} dp {c['dp']:4d} floor {c['floor']:4d} floorN {c['floorN']:4d} other {c['other']:5d} | cap {c['cap']:5d}")
            print(f"       boxed>=80% 的窗口：{runs(rows, lambda r: int(r['boxed']) >= 0.8 * int(r['acts']))}")
            print(f"       cap>=80% 的窗口：{runs(rows, lambda r: int(r['cap']) >= 0.8 * int(r['acts']))}")
            fl = lambda r: int(r['floor']) + int(r['floorN'])
            fr = [r for r in rows if fl(r) >= 0.5 * int(r['acts']) and int(r['t0']) >= a.floor_from]
            if fr:
                print(f"       floor+floorN>=50% 的窗口（t0>={a.floor_from}）：{runs(rows, lambda r: fl(r) >= 0.5 * int(r['acts']) and int(r['t0']) >= a.floor_from)}；这些窗口里 floor+floorN 共 {sum(fl(r) for r in fr)} 个决策拍、cmd {sum(int(r['cmd']) for r in fr)} 个；保底线取自 safeFinite {sum(int(r['bySafe']) for r in fr)} / dpKeep {sum(int(r['byKeep']) for r in fr)} / 回本线 {sum(int(r['byPx']) for r in fr)}")
                if a.verbose:
                    for r in fr:
                        print(f"         t0={r['t0']:>5s} 余额均值 {r['bal']:>7s} 领土 {r['terr']:>5s} 保底线均值 {r['floorAvg']:>7s} 身边机器人 {r['aiNb']} 个 共 {r['aiLand']} 格 密度 {r['aiDens']}")
                else:
                    f0, f1 = fr[0], fr[-1]
                    print(f"         首窗 t0={f0['t0']} 余额 {f0['bal']} 保底线 {f0['floorAvg']} 机器人地 {f0['aiLand']} 格(密度 {f0['aiDens']})；末窗 t0={f1['t0']} 余额 {f1['bal']} 保底线 {f1['floorAvg']} 机器人地 {f1['aiLand']} 格(密度 {f1['aiDens']})；领土 {f0['terr']}→{f1['terr']}")
            # other 的去向（见 shadow.mjs 的说明）：oPrice = buyLand 在价格线上 break（L5358）
            if rows and 'oPrice' in rows[0]:
                oc = {k: sum(int(r[k] or 0) for r in rows) for k in ('oPrice', 'oGate', 'oEmpty', 'oNoCall', 'priceOnMe')}
                for k, v in oc.items():
                    tot[k] += v
                if c['other']:
                    print(f"       other 细分：价格线 {oc['oPrice']} / 其他闸门 {oc['oGate']} / 没有可打目标或没空槽 {oc['oEmpty']} / 没走到 offers {oc['oNoCall']}；价格线里正被人打的 {oc['priceOnMe']} 个决策拍")
                pr = [r for r in rows if int(r['oPrice'] or 0) >= 0.5 * int(r['acts'])]
                if pr:
                    print(f"       价格线>=50% 的窗口：{runs(rows, lambda r: int(r['oPrice'] or 0) >= 0.5 * int(r['acts']))}；这些窗口共 {sum(int(r['oPrice']) for r in pr)} 个价格线决策拍、cmd {sum(int(r['cmd']) for r in pr)} 个")
                    show = pr if a.verbose else [pr[0], pr[len(pr) // 2], pr[-1]] if len(pr) >= 3 else pr
                    for r in show:
                        print(f"         t0={r['t0']:>5s} 余额均值 {r['bal']:>8s} 领土 {r['terr']:>6s} 密度 {r['dens']:>5s} | 最便宜目标 单价 c={r['priceC']} 愿付价 worth={r['priceWorth']} 对方密度 {r['priceDq']} | 人类邻居 {r['foeNb']} 个 | 正被打 {r['priceOnMe']} 拍" + (f"（来袭兵力均值 {r['priceInAtk']}）" if r['priceInAtk'] else ''))
        if tot['acts'] and tot.get('oPrice') is not None and tot['other']:
            print(f"  合计 other {tot['other']} = 价格线 {tot['oPrice']} + 其他闸门 {tot['oGate']} + 无目标 {tot['oEmpty']} + 没走到 {tot['oNoCall']}；价格线占全部决策拍 {100*tot['oPrice']/tot['acts']:.1f}%")
        if tot['acts']:
            print(f"  合计 决策拍 {tot['acts']} | cmd {tot['cmd']} ({100*tot['cmd']/tot['acts']:.1f}%) boxed {tot['boxed']} ({100*tot['boxed']/tot['acts']:.1f}%) dp {tot['dp']} ({100*tot['dp']/tot['acts']:.1f}%) floor {tot['floor']} ({100*tot['floor']/tot['acts']:.1f}%) floorN {tot['floorN']} ({100*tot['floorN']/tot['acts']:.1f}%) other {tot['other']} ({100*tot['other']/tot['acts']:.1f}%) | cap {tot['cap']} ({100*tot['cap']/tot['acts']:.1f}%)")

    if 'flow' in secs:
        print(f'\n== {mid} 指令流（按决策拍每 {a.win} 拍一窗）：发出 / 落地 / 丢失；落地延迟 中位~最大（拍）')
        for b in bots:
            rows = [r for r in cmds if r['bot'] == b and r['ok'] == '1' and r['kind'] in ('attack', 'donate')]
            if not rows:
                continue
            lag_of = {}
            for x in match:
                if x['bot'] == b and x['uniq'] != '0':
                    lag_of[(int(x['tDecide']), x['kind'], x['pct'])] = int(x['lag'])
            wins = defaultdict(lambda: [0, 0, []])
            for r in rows:
                t = int(r['t'])
                if t < a.t0 or t > a.t1:
                    continue
                w = t // a.win * a.win
                wins[w][0] += 1
                if r['landedAt']:
                    wins[w][1] += 1
                    wins[w][2].append(int(r['landedAt']) - t)
            tot_i = sum(v[0] for v in wins.values())
            tot_l = sum(v[1] for v in wins.values())
            print(f'  {b}: 发出 {tot_i}，落地（已定位）{tot_l}，丢失或未定位 {tot_i - tot_l}')
            for w in sorted(wins):
                i, l, lags = wins[w]
                print(f'     {w:5d}-{w + a.win - 1:<5d} 发 {i:3d} 落 {l:3d} 丢 {i - l:3d}  延迟 {med(lags)}~{max(lags) if lags else "-"}')

    if 'chunks' in secs:
        ch = load(mid, 'shadow_chunks', a.tag)
        print(f'\n== {mid} 成块补帧（号, 落地拍 T）：留下 n 条 = 决策拍 t0–t1；延迟 = T - 决策拍；')
        print('   块跨度 = 下一次落地的第一条决策拍 - 本次第一条决策拍；真实用时 = T - 上一次落地拍；毫秒/拍 = 真实用时 x 56 / 块跨度')
        for b in bots:
            rows = [r for r in ch if r['bot'] == b and a.t0 <= int(r['tick']) <= a.t1]
            if not rows:
                continue
            print(f'  {b}')
            prevT = None
            shown = 0
            for i, r in enumerate(rows):
                T, n, t0, t1 = int(r['tick']), int(r['n']), int(r['t0']), int(r['t1'])
                lag1 = int(r['lagMax'])
                nxt = rows[i + 1] if i + 1 < len(rows) else None
                dur = T - prevT if prevT is not None else None
                prevT = T
                if lag1 < a.min_lag and n < a.min_n:
                    continue
                # 毫秒/拍 只在“积压状态”下有意义：本次与下一次落地的延迟都 >= min_lag
                span = int(nxt['t0']) - t0 if nxt is not None and int(nxt['lagMax']) >= a.min_lag and lag1 >= a.min_lag else None
                ms = f'{dur * 56 / span:6.1f}' if span and dur and span > 0 else '     -'
                print(f'     T={T:5d} n={n} 决策 {t0:5d}-{t1:<5d} 延迟 {int(r["lagMin"]):4d}~{lag1:<4d} 块跨度 {span if span is not None else "-":>4} 真实用时 {dur if dur is not None else "-":>4} 毫秒/拍 {ms}')
                shown += 1
            if not shown:
                print('     （没有延迟 >= %d 拍或同拍 >= %d 条的落地）' % (a.min_lag, a.min_n))

    if 'bursts' in secs:
        print(f'\n== {mid} 同拍落地 >= {a.min_n} 条的组（陆攻）：决策时想出的兵合计 vs 执行时实际扣掉的（兵+手续费）')
        grp = defaultdict(list)
        for x in match:
            if x['kind'] == 'attack' and (not a.bot or x['bot'] in bots):
                grp[(x['bot'], int(x['tick']))].append(x)
        print('   号         落地拍  条数 目标                     决策拍        延迟      决策时余额  想出的兵合计  执行前余额  实际扣掉   占比   代码位置')
        for (b, T), xs in sorted(grp.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if len(xs) < a.min_n or T < a.t0 or T > a.t1:
                continue
            loc = [x for x in xs if x['uniq'] != '0']
            td = [int(x['tDecide']) for x in loc]
            want = sum(int(x['troopsDecide']) for x in loc)
            spent = sum(int(x['spent']) for x in xs if x['spent'] != '')
            bal0 = max(int(x['balExec']) for x in xs if x['balExec'] != '')
            bald = [int(x['balDecide']) for x in loc]
            tgt = Counter(x['targetName'] for x in xs).most_common(1)[0][0].strip('"')
            sites = Counter(nice_path(x['path'], name_of, 1) for x in loc).most_common(1)
            appl = sum(1 for x in xs if x['applied'] == '1')
            print(f'   {b:10s} {T:6d} {len(xs):3d}({appl}) {tgt[:22]:22s} {min(td) if td else "-":>5}-{max(td) if td else "-":<5} {T - max(td) if td else "-":>4}~{T - min(td) if td else "-":<4} {min(bald) if bald else "-":>7}-{max(bald) if bald else "-":<7} {want:>9} {bal0:>10} {spent:>9} {100 * spent / max(1, bal0):5.1f}%  {sites[0][0] if sites else "未定位"}')

    if 'paths' in secs:
        print(f'\n== {mid} 指令按代码位置：发出 / 落地（已定位）')
        c = Counter()
        l = Counter()
        for r in cmds:
            if r['ok'] != '1' or (a.bot and r['bot'] not in bots):
                continue
            t = int(r['t'])
            if t < a.t0 or t > a.t1:
                continue
            k = (r['kind'], nice_path(r['path'], name_of, 2))
            c[k] += 1
            if r['landedAt']:
                l[k] += 1
        for k, n in c.most_common():
            print(f'   {n:5d} / {l[k]:<5d} {k[0]:7s} {k[1]}')

    if 'lagcurve' in secs:
        print(f'\n== {mid} 全队延迟曲线：按决策拍每 {a.win} 拍一窗，全部号合计 发出 / 落地（已定位）；落地延迟 最小/中位/最大')
        wins = defaultdict(lambda: [0, 0, []])
        for r in cmds:
            if r['ok'] != '1' or r['kind'] not in ('attack', 'donate') or (a.bot and r['bot'] not in bots):
                continue
            t = int(r['t'])
            if t < a.t0 or t > a.t1:
                continue
            w = t // a.win * a.win
            wins[w][0] += 1
            if r['landedAt']:
                wins[w][1] += 1
                wins[w][2].append(int(r['landedAt']) - t)
        ti = tl = 0
        for w in sorted(wins):
            i, l, lags = wins[w]
            ti += i
            tl += l
            print(f'   {w:5d}-{w + a.win - 1:<5d} 发 {i:4d} 落 {l:4d} ({100 * l / max(1, i):5.1f}%)  延迟 {min(lags) if lags else "-"}/{med(lags)}/{max(lags) if lags else "-"}')
        print(f'   合计 [{a.t0},{min(a.t1, 99999)}] 发 {ti} 落 {tl} ({100 * tl / max(1, ti):.1f}%)')

    if 'repeat' in secs:
        print(f'\n== {mid} 正常延迟下的重复下令：同一号对同一目标在连续决策周期（间隔 5 拍）里发出的一串陆攻令算一组；只统计整组都落地且延迟 < {a.min_lag} 拍的组')
        print('   组长分布；以及每组 第一条决策时想出的兵占当时余额的比例（意图） 对 整组实际扣掉的兵占第一条执行前余额的比例（实际）')
        byb = defaultdict(list)
        mrow = {}
        for x in match:
            if x['uniq'] != '0' and x['kind'] == 'attack':
                mrow[(x['bot'], int(x['tDecide']))] = x
        for r in cmds:
            if r['ok'] == '1' and r['kind'] == 'attack' and (not a.bot or r['bot'] in bots):
                byb[r['bot']].append(r)
        hist = Counter()
        rows_out = []
        for b, rs in byb.items():
            run = []
            def flush():
                if not run:
                    return
                ms = [mrow.get((b, int(r['t']))) for r in run]
                if all(m is not None and int(m['lag']) < a.min_lag for m in ms) and a.t0 <= int(run[0]['t']) <= a.t1:
                    hist[len(run)] += 1
                    want = int(ms[0]['troopsDecide']) / max(1, int(ms[0]['balDecide']))
                    spent = sum(int(m['spent']) for m in ms if m['spent'] != '')
                    b0 = max(int(m['balExec']) for m in ms if m['balExec'] != '')
                    rows_out.append((int(run[0]['t']), b, len(run), run[0]['targetName'].strip('"'), want, spent / max(1, b0), nice_path(run[0]['path'], name_of, 1)))
            for r in rs:
                if run and int(r['t']) - int(run[-1]['t']) == 5 and r['target'] == run[-1]['target']:
                    run.append(r)
                else:
                    flush()
                    run = [r]
            flush()
        print('   组长: ' + '  '.join(f'{k} 条 x{n}' for k, n in sorted(hist.items())))
        big = [x for x in rows_out if x[2] >= 2 and x[4] >= 0.05]
        if big:
            ratio = sorted(x[5] / x[4] for x in big)
            print(f'   组长 >=2 且意图 >=5% 的 {len(big)} 组：实际/意图 中位 {ratio[len(ratio) // 2]:.2f}，最大 {ratio[-1]:.2f}')
        for x in sorted(rows_out, key=lambda x: -x[5])[:a.top]:
            print(f'     t={x[0]:5d} {x[1]:10s} {x[2]} 条 → {x[3][:20]:20s} 意图 {100 * x[4]:5.1f}%  实际 {100 * x[5]:5.1f}%  {x[6]}')

    if 'donate' in secs:
        # 每条捐款决策的去向：landed 录像里有；engine 到了引擎但没生效（正常延迟，或落在某一批留下的前 9 条名额里）；channel 堵在通道里没到引擎
        ch = load(mid, 'shadow_chunks', a.tag)
        batches = defaultdict(list)
        for r in ch:
            batches[r['bot']].append((int(r['tick']), int(r['t0']), int(r['t1']), int(r['n']), int(r['lagMin']), int(r['lagMax'])))
        acc = defaultdict(list)
        for r in cmds:
            if r['ok'] == '1':
                acc[r['bot']].append(r)
        da = {}
        dap = os.path.join(OUT, mid, 'dispatch_audit.csv')
        if os.path.exists(dap):
            for r in csv.DictReader(open(dap, encoding='utf8')):
                da[(r['bot'].split(':')[-1], int(r['t']), int(r['to']))] = r
        # 全队共用一条延迟曲线（日志里各号的本地拍齐步走）：用任意号最近一条已定位落地指令的延迟判断当时是否在积压
        landed_all = sorted((int(r['t']), int(r['landedAt']) - int(r['t'])) for r in cmds if r['ok'] == '1' and r['landedAt'])
        import bisect
        lt = [x[0] for x in landed_all]
        def squad_lag(t):
            i = bisect.bisect_right(lt, t)
            lp = landed_all[i - 1][1] if i > 0 else None
            ln = landed_all[i][1] if i < len(landed_all) else None
            return lp, ln
        print(f'\n== {mid} 捐款决策的去向（landed 落地 / engine 到了引擎没生效 / lagged 积压期间发出、录像里没有：被通道丢弃还是到了引擎被拒，分不出来）')
        tot = Counter()
        rows_out = []
        for b in bots:
            rs = acc[b]
            bs = sorted(batches.get(b, []))
            for i, r in enumerate(rs):
                if r['kind'] != 'donate':
                    continue
                t = int(r['t'])
                if t < a.t0 or t > a.t1:
                    continue
                cls, execT = None, None
                if r['landedAt']:
                    cls, execT = 'landed', int(r['landedAt'])
                else:
                    lp, ln = squad_lag(t)
                    inb = next((x for x in bs if x[1] <= t <= x[2]), None)
                    if inb:
                        cls, execT = 'engine', inb[0]
                    elif (lp is None or lp < a.min_lag) and (ln is None or ln < a.min_lag) and not (lp is None and ln is None):
                        cls, execT = 'engine', t + (ln if ln is not None else lp)
                    else:
                        # 紧跟在上一批留下的前缀后面、名额还没满 9 条：算到了引擎
                        pb = next((x for x in reversed(bs) if x[2] < t), None)
                        if pb and pb[5] >= a.min_lag:
                            k = sum(1 for x in rs if pb[2] < int(x['t']) <= t)
                            if pb[3] + k <= 9 and t < pb[0]:
                                cls, execT = 'engine', pb[0]
                        if cls is None:
                            cls = 'lagged'
                d = da.get((b.split(':')[-1], t, int(r['target'])))
                tot[(cls, d['would'] if d else '?')] += 1
                rows_out.append((t, b, r['targetName'].strip('"'), int(r['pct']), int(r['troops']), cls, execT, d))
        for (cls, would), n in sorted(tot.items()):
            print(f'   {cls:8s} 按决策拍状态引擎会 {would:7s}: {n}')
        if a.verbose:
            print('       t 号        → 受赠者            pct   名义额  去向     执行拍  成本/已用/上限(决策拍)')
            for t, b, tn, pct, troops, cls, execT, d in rows_out:
                q = f"{d['cost']}/{d['used']}/{d['cap']}" if d else '-'
                print(f'   {t:5d} {b:10s} {tn[:16]:16s} {pct:4d} {troops:8d}  {cls:8s} {execT if execT else "-":>6}  {q}')

    if 'overprice' in secs:
        print(f'\n== {mid} 高于愿付价的进攻：对真人的陆攻令，按 发令时余额是否过 100 倍领土（over）× 单价 c 是否 >= 愿付价 worth 分类 [{a.t0},{a.t1}]')
        mrow = {(x['bot'], int(x['tDecide'])): x for x in match if x['uniq'] != '0' and x['kind'] == 'attack'}
        agg = defaultdict(lambda: [0, 0, 0, 0, [], []])
        perbot = defaultdict(lambda: [0, 0, 0, 0])
        pertgt = defaultdict(lambda: [0, 0, 0, 0, [], []])
        nocol = 0
        for r in cmds:
            if r['kind'] != 'attack' or r['ok'] != '1' or (a.bot and r['bot'] not in bots):
                continue
            t = int(r['t'])
            if t < a.t0 or t > a.t1:
                continue
            if r.get('c', '') == '':
                if r['targetName'].strip('"') not in ('NEUTRAL', '') and not r['targetName'].strip('"').startswith('AI#'):
                    nocol += 1
                continue
            if r.get('person') != '1':
                continue
            c, w, ov = float(r['c']), float(r['worth']), r['over'] == '1'
            k = ('over' if ov else 'notover') + ('_hi' if c >= w else '_lo')
            m = mrow.get((r['bot'], t))
            spent = int(float(m['spent'] or 0)) if m else 0
            x = agg[k]; x[0] += 1; x[1] += int(r['troops']); x[2] += 1 if m else 0; x[3] += spent; x[4].append(c); x[5].append(w)
            if k == 'over_hi':
                pb = perbot[r['bot']]; pb[0] += 1; pb[1] += int(r['troops']); pb[2] += 1 if m else 0; pb[3] += spent
                pt = pertgt[r['targetName'].strip('"')]; pt[0] += 1; pt[1] += int(r['troops']); pt[2] += 1 if m else 0; pt[3] += spent; pt[4].append(c); pt[5].append(float(r['tBal']) / max(1, float(r['tTerr'])))
        lab = {'over_hi': 'over 且 c>=worth（熔断被跳过）', 'over_lo': 'over 且 c<worth', 'notover_lo': '未 over 且 c<worth（正常）', 'notover_hi': '未 over 且 c>=worth（c<cheap 等）'}
        print('   类别                              受理  想出的兵合计  落地  落地时实扣合计  c 中位  worth 中位')
        for k in ('over_hi', 'over_lo', 'notover_lo', 'notover_hi'):
            x = agg.get(k)
            if not x:
                print(f'   {lab[k]:30s} {0:5d}')
                continue
            print(f'   {lab[k]:30s} {x[0]:5d} {x[1]:12d} {x[2]:5d} {x[3]:14d} {med(x[4]):7.1f} {med(x[5]):9.1f}')
        if nocol:
            print(f'   （另有 {nocol} 条对玩家的进攻令没有报价列：不是从 buyLand 报价表出的，或这一版策略没有 offers()）')
        if perbot:
            print('   over 且 c>=worth 按号：' + '；'.join(f"{b} {v[0]} 条 想出 {v[1]}，落地 {v[2]} 条 实扣 {v[3]}" for b, v in sorted(perbot.items(), key=lambda kv: -kv[1][1])))
            print('   over 且 c>=worth 按目标：' + '；'.join(f"{tn[:18]} {v[0]} 条 想出 {v[1]}（c 中位 {med(v[4]):.0f}，对方密度中位 {med(v[5]):.0f}）" for tn, v in sorted(pertgt.items(), key=lambda kv: -kv[1][1])[:a.top]))

    if 'list' in secs:
        if not a.bot:
            sys.exit('--section list 需要 --bot')
        print(f'\n== {mid} {a.bot} 逐条决策 [{a.t0},{a.t1}]')
        print('      t 类型   pct 目标                   受理   余额    密度  想出的兵  目标余额 目标领土 落地拍  代码位置')
        for r in cmds:
            if r['bot'] not in bots:
                continue
            t = int(r['t'])
            if t < a.t0 or t > a.t1:
                continue
            print(f'  {t:5d} {r["kind"]:6s} {int(r["pct"]):4d} {r["targetName"].strip(chr(34))[:22]:22s} {r["ok"]:>3} {int(r["bal"]):8d} {float(r["dens"]):6.1f} {int(r["troops"]):8d} {int(r["tBal"]):9d} {int(r["tTerr"]):7d} {r["landedAt"] or "-":>6}  {nice_path(r["path"], name_of, 2)}')


if __name__ == '__main__':
    main()
