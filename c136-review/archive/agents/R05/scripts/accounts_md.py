#!/usr/bin/env python3
"""accounts_md.py — 把一局的三本账（广播 0007：延迟硬账 / 好地账 / 600–1500 拍决策拍三层归因）渲染成复盘 .md 里的一节。

数据来源：reviews/<局>.json 的 delayAccount / landAccount / tickAttribution 三个字段
（由 scripts/review_build/common.py 的 accounts() 从 delay_account.py、land_account.mjs、tick_attrib.py 的输出原样裁剪进去）。
加 --work 时直接读 /tmp/c136-r05/work/<局>-{delay,land,attrib}.json（复盘 JSON 还没重建时用）。

口径（与三个脚本的头注一致）：
  延迟 = 指令在录像里的执行拍 − 影子策略做出同一条决策的拍；基线 = 0–600 拍的中位；
  影子 = 线上同一份策略源码在逐拍重放的局面上重跑出来的决策；
  按原意落地 = 落地时目标还活着、接壤；
  名下份额 = 每格陆地归离它最近的真人出生点；
  同拍批 = 同一个号同一拍执行 ≥3 条；在途重复 = 决策下在上一条同目标指令的在途期间。

用法：python3 scripts/accounts_md.py <局> [--work] [--title '## 6b. …']
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'review_build'))


def load(mid, work):
    if work:
        from common import accounts
        return accounts(mid)
    return json.load(open(os.path.join(HERE, '..', 'reviews', f'{mid}.json')))


def k(v):
    v = v or 0
    if abs(v) >= 1e6:
        return f'{v / 1e6:.2f}M'
    if abs(v) >= 1e4:
        return f'{v / 1e3:.0f}k'
    if abs(v) >= 1e3:
        return f'{v / 1e3:.1f}k'
    return f'{v:.0f}'


def n(v):
    return f'{int(round(v or 0)):,}'


def pct(a, b, d=0):
    return f'{100 * a / b:.{d}f}%' if b else '–'


def num(v):
    if v is None:
        return '–'
    return f'{v:g}' if isinstance(v, float) and v != int(v) else f'{int(v)}'


def render(mid, J, title):
    out = [title, '']
    if J.get('accountsNote'):
        out.append('- ' + J['accountsNote'])
    D, L, A = J.get('delayAccount'), J.get('landAccount'), J.get('tickAttribution')
    if D:
        sp = D.get('spawnExecution') or {}
        bots = sp.get('bots') or []
        v = sp.get('verdicts') or {}
        landed = v.get('最终坐标落地', 0)
        old = v.get('停在旧坐标', 0)
        rnd = sum(c for kk, c in v.items() if kk.startswith('0 条落地'))
        dist = sorted(b['distActualToFinal'] for b in bots if b.get('verdict') == '停在旧坐标' and b.get('distActualToFinal') is not None)
        s = f"- **出生执行**（`delay_account.py {mid}`）：协调器求解 {sp.get('solveRounds')} 轮、{sp.get('distinctSolutions')} 种解；录像里的 {len(bots)} 个号最终坐标落地 {landed} 个、停在旧坐标 {old} 个"
        if len(dist) == 1:
            s += f"（离最终坐标 {num(round(dist[0]))} 格）"
        elif dist:
            s += f"（离最终坐标 {num(round(dist[0]))}–{num(round(dist[-1]))} 格，中位 {num(round(dist[len(dist) // 2]))}）"
        s += f"、0 条落地由引擎随机落子 {rnd} 个；同像素堆叠 {sp.get('stackPairs', 0)} 对"
        if len(bots) > 1:
            s += f"；到最近我方号的距离中位 {num(round(sp.get('nearestAllyMedian') or 0))} 格"
        out.append(s + '。')
        base = D.get('baselineTicks')
        rows = D.get('delayByPeriod') or []
        s = f"- **指令延迟**（执行拍 − 影子决策拍；基线 {num(base)} 拍；落地条数 P50/P90/最大）：" + '；'.join(
            f"{r['period']} 拍 {r['landed']} 条" + (f" {num(r['p50'])}/{num(r['p90'])}/{num(r['max'])}" if r.get('matched') else '（无配对）') for r in rows if r['landed'])
        lag = D.get('lagByBotP50') or {}
        parts = []
        for i, r in enumerate(rows[1:3], start=1):
            xs = sorted((x[i] - base, b) for b, x in lag.items() if x[i] is not None)
            if xs and xs[-1][0] >= 10:
                parts.append(f"{r['period']} 拍 {num(max(0, round(xs[0][0])))}–{num(round(xs[-1][0]))} 拍（最多的是 {xs[-1][1]}）")
        if parts:
            s += '。各号中位比基线多：' + '，'.join(parts)
        out.append(s + '。')
        F = {r['period']: r for r in D.get('funnel') or []}
        segs = []
        for p in ('600–1500', '1500–3000'):
            r = F.get(p)
            if not r or not r['intended']:
                continue
            seg = f"{p} 拍 {n(r['intended'])} → {n(r['landed'])} → {n(r['asIntended'])}（{pct(r['asIntended'], r['intended'])}）"
            extra = []
            if r['deadToNeutral'] or r['deadVoid']:
                extra.append(f"目标已死 {r['deadToNeutral'] + r['deadVoid']}（改打中立 {r['deadToNeutral']}、作废 {r['deadVoid']}）")
            if r['void']:
                extra.append(f"不接壤作废 {r['void']}")
            if r['neverLanded']:
                extra.append(f"没落地 {n(r['neverLanded'])}（{pct(r['neverLanded'], r['intended'])}）")
            segs.append(seg + ('，' + '、'.join(extra) if extra else ''))
        sr = D.get('selfReport') or {}
        s = '- **漏斗**（影子想发 → 落地 → 按原意）：' + '；'.join(segs)
        if sr:
            s += f"。影子与客户端对账（含捐兵，数到各号最后一条日志）：影子 {n(sr.get('shadow'))} 条、自报 {n(sr.get('cmds'))} 条"
        ft = D.get('funnelTotals') or {}
        if ft:
            s += f"；全程陆攻/出船想发 {n(ft['intended'])} 条、录像里执行 {n(ft['executed'])} 条"
            if ft.get('unmatchedExec'):
                s += f"（其中 {ft['unmatchedExec']} 条没配上决策，上面的「没落地」因此最多多算 {ft['unmatchedExec']} 条）"
        ph = D.get('phantomDecisions') or {}
        phn = sum(v2 if isinstance(v2, int) else (v2.get('n', 0) if isinstance(v2, dict) else 0) for v2 in ph.values()) if isinstance(ph, dict) else 0
        if phn:
            s += f"（客户端没跑到的拍上另有 {phn} 条影子决策，不计）"
        out.append(s + '。')
        LV = {r['period']: r for r in D.get('lateVoid') or []}
        B = (LV.get('600–1500') or {}).get('B') or {}
        IR = {r['period']: r for r in D.get('inflightRepeats') or []}
        BT = {r['period']: r for r in D.get('batches') or []}
        s = '- **直接损失（600–1500 拍）**：'
        if B.get('landed'):
            dead = B.get('rewrittenOk', 0) + B.get('rewrittenVoid', 0)
            s += f"(a) 落地的打机器人指令 {B['landed']} 条里到达时目标已死 {dead} 条"
            if dead:
                s += f"（延迟中位 {num(B.get('staleRewrittenP50'))} 拍；作废 {B.get('rewrittenVoid', 0)}，改打中立 {B.get('rewrittenOk', 0)} 条打出 {k(B.get('rewrittenOut'))} + 手续费 {k(B.get('rewrittenFee'))}）"
            s += f"，命中的 {B.get('hit', 0)} 条打出 {k(B.get('hitOut'))} 拿 {n(B.get('hitTiles'))} 格；"
        else:
            s += '(a) 没有落地的打机器人指令；'
        r = IR.get('600–1500') or {}
        if r.get('attackDecisions'):
            s += f"(b) 陆攻决策 {r['attackDecisions']} 条里 {r['repeatDecisions']} 条（{pct(r['repeatDecisions'], r['attackDecisions'])}）是在途重复，落地的重复打出 {k(r.get('repeatOut'))}（占打出兵数的 {pct(r.get('repeatOut', 0), r.get('allOut', 0))}）+ 手续费 {k(r.get('repeatFee'))}；"
        b = BT.get('600–1500') or {}
        s += f"同拍批（一个号一拍落地 ≥3 条）{b.get('batches', 0)} 个 {b.get('cmds', 0)} 条（落地指令的 {pct(b.get('cmds', 0), b.get('landedAll', 0))}），整批作废 {b.get('allVoidBatches', 0)} 批，一拍打掉一半以上存兵 {b.get('drain50', 0)} 批"
        b2 = BT.get('1500–3000') or {}
        if b2.get('batches'):
            s += f"；1500–3000 拍 {b2['batches']} 批 {b2['cmds']} 条（{pct(b2['cmds'], b2.get('landedAll', 0))}），整批作废 {b2.get('allVoidBatches', 0)}、打掉一半以上 {b2.get('drain50', 0)} 批"
        out.append(s + '。')
    if L:
        V = L.get('voronoi') or {}
        cap = {c['t']: c for c in L.get('capture') or []}
        s = f"- **好地账**（`land_account.mjs {mid}`）：按出生点分的名下份额，编队 {n(V.get('squadCells'))} 格 = 全图 {100 * V.get('landShare', 0):.1f}%，人数占 {100 * V.get('headShare', 0):.1f}% → {V.get('ratio', 0):.2f}（每号中位 {n(V.get('squadMedian'))} 格，其余真人 {n(V.get('othersMedian'))}）。实际地 ÷ 名下份额："
        segs = []
        for t in (630, 1500):
            c = cap.get(t)
            if not c:
                continue
            g = c['groups'].get('我方号') or {}
            segs.append(f"{t} 拍 编队 {g.get('ratio', 0):.2f}（每号中位 {g.get('medianRatio', 0):.2f}），其余真人中位 {c.get('othersMedianRatio', 0):.2f}")
        land_line = s + '；'.join(segs) + '。'
        bl = L.get('botLand') or {}
        fate = bl.get('fate') or {}

        def last(key):
            rows = fate.get(key) or []
            return rows[-1] if rows else None

        segs = []
        a, b3, c3 = last('A'), last('B'), last('C')
        if a and bl.get('A', {}).get('tiles'):
            tot = bl['A']['tiles']
            seg = f"名下的机器人地 {n(tot)} 格我方拿到 {pct(a.get('我方号', 0), tot, 1)}、敌方真人 {pct(a.get('敌方真人', 0), tot, 1)}、仍是机器人 {pct(a.get('机器人', 0) + a.get('同队机器人', 0), tot, 1)}"
            segs.append(seg)
        if b3 and bl.get('B', {}).get('tiles'):
            tot = bl['B']['tiles']
            segs.append(f"贴着我方号、可以打的 {bl['B'].get('bots')} 个机器人 {n(tot)} 格我方 {pct(b3.get('我方号', 0), tot, 1)}、敌方真人 {pct(b3.get('敌方真人', 0), tot, 1)}")
        if c3 and bl.get('C', {}).get('tiles'):
            tot = bl['C']['tiles']
            seg = f"全图机器人地 {n(tot)} 格我方 {pct(c3.get('我方号', 0), tot, 1)}"
            pg = bl.get('perGroupLast') or {}
            if isinstance(pg, dict) and pg.get('我方号'):
                me = pg['我方号']
                others = sorted(((g['tiles'] / g['n'], kk) for kk, g in pg.items() if kk != '我方号' and g.get('n')), reverse=True)
                seg += f"（每号 {n(me['tiles'] / me['n'])} 格"
                if others:
                    seg += '；' + '、'.join(f"{kk} 每人 {n(v2)}" for v2, kk in others[:3])
                seg += '）'
            segs.append(seg)
        if segs:
            t1 = (c3 or a or b3 or {}).get('t', 1800)
            land_line += f"600 拍的机器人地到 {t1} 拍的去向：" + '；'.join(segs) + '。'
        out.append(land_line)
    if A and A.get('rows'):
        R = A['rows']
        c = A.get('cats') or {}
        ly = A.get('layers') or {}
        s = (f"- **600–1500 拍 {n(R)} 个决策拍的三层归因**（`tick_attrib.py {mid}`）：① 结构 {pct(ly.get('①结构', 0), R, 1)}（只贴敌方真人 {pct(c.get('只贴敌方真人', 0), R, 1)}、被围住 {pct(c.get('围在里面', 0), R, 1)}）；"
             f"② 留底 {pct(ly.get('②留底', 0), R, 1)}（纯锁 {pct(c.get('留底锁·无在途', 0), R, 1)}、上一条还在路上 {pct(c.get('留底·有在途', 0), R, 1)}）；"
             f"③ 发了但没用 {pct(ly.get('③执行', 0), R, 1)}（目标已死 {pct(c.get('迟到·目标已死', 0), R, 1)}、不接壤 {pct(c.get('迟到·不接壤', 0), R, 1)}、没落地 {pct(c.get('没落地', 0), R, 1)}）；"
             f"有效 {pct(ly.get('有效', 0), R, 1)}；其余 {pct(ly.get('其余', 0), R, 1)}")
        ns = (A.get('notSentSplit') or {}).get('split') or {}
        rest = []
        for kk in ('冷却空过', '在途已够', '配额闸拒发', 'send 返回 false（其他）', '其他'):
            if ns.get(kk):
                rest.append(f"{kk} {pct(ns[kk], R, 1)}")
        if not ns and c.get('有目标没发'):
            rest.append(f"有目标没发 {pct(c['有目标没发'], R, 1)}")
        if c.get('只剩中立边'):
            rest.append(f"只剩中立边 {pct(c['只剩中立边'], R, 1)}")
        if rest:
            s += '（' + '、'.join(rest) + '）'
        fs = A.get('floorSetter') or {}
        if fs:
            s += '。留底 ≥ 一半存兵的决策拍里定值的是 ' + '、'.join(f"{kk} {vv}" for kk, vv in sorted(fs.items(), key=lambda kv: -kv[1]))
        out.append(s + '。')
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    work = '--work' in a
    title = a[a.index('--title') + 1] if '--title' in a else '## 6b. 延迟硬账、好地账、600–1500 拍三层归因（广播 0007；数字全部来自脚本）'
    ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--title')]
    for mid in ids:
        print('\n'.join(render(mid, load(mid, work), title)))
        print()
