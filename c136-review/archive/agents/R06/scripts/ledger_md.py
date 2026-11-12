#!/usr/bin/env python3
"""ledger_md.py — 把 out/<id>/latency.json 与 out/<id>/landcap.json 排成复盘 md 里的 §5a 延迟账 / §5b 好地账。
数字全部来自 latency.py / landcap.py 的 json 产出，这里只排版，不再计算。

用法：python3 ledger_md.py <matchId> [--short]
  --short  每节 2 条（给行数已经贴近上限的 md 用）；默认每节 3 条
没有对局阶段录像的局只排选点与天然份额两项，并写明其余各项算不了。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'out')


def jload(mid, name):
    p = os.path.join(OUT, mid, name)
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def wan(x):
    if x is None:
        return '—'
    x = int(round(x))
    if abs(x) < 10000:
        return f"{x:,}"
    if abs(x) < 1000000:
        return f"{x / 1e4:.1f} 万"
    if abs(x) < 100000000:
        return f"{x / 1e4:,.0f} 万"
    return f"{x / 1e8:.2f} 亿"


def pc(a, b, d=1):
    if not b:
        return '—'
    return f"{100 * a / b:.{d}f}%"


def q3(d):
    return f"{d['p50']}/{d['p90']}/{d['max']}"


def nobullet(s):
    return s[2:] if s.startswith('- ') else s


def spawn_line(L):
    s = L.get('spawn') or {}
    if 'per' not in s:
        return (f"- **选点执行延迟**：没有录像，选点落地看不到；日志 HL-SPAWN {s.get('logged', 0)} 行、后端协调行 {s.get('backendLines', 0)} 行。")
    n = len(s['per'])
    lb = f"{s['lbP50']}/{s['lbP90']}/{s['lbMax']}" if s.get('lbMax') is not None else '—'
    return (f"- **选点执行延迟**：选点阶段 {s['steps']} 步，后端协调行 {s['backendLines']} 行；HL-SPAWN 下发 {s['logged']} 行、进录像 {s['landed']} 条（{pc(s['landed'], s['logged'], 0)}）；"
            f"最后一版就是出生点的 {s['lastOk']}/{n} 个号，停在更早一版坐标的 {s['late']} 个（差 1 条 {s['late1']}、2 条 {s['late2']}、>=3 条 {s['late3']}），一条都没落地（引擎随机落位）{s['zero']} 个；"
            f"最终落点 <80 格 {s['near']} 对（同像素 {s['samePixel']} 对）；选点延迟下界 P50/P90/Max = {lb} 步。")


def delay_line(L):
    fb = {b['band']: b for b in L['funnel']['bands']}
    parts = []
    for d in L['delay']:
        f = fb.get(d['band'])
        fun = f"｜{f['shadow']}→{f['landed']}→{f['ok']}" if f else ''
        core = q3(d)
        if d['band'] == '600~1500':
            core = f"**{core}**"
        parts.append(f"{d['band']} {core}（{d['n']} 条{fun}）")
    cells = [c for c in L.get('cells', []) if 600 <= c[0] <= 2250]
    tc = ''
    if cells:
        tc = '每 150 拍一格的中位：' + '→'.join(f"{c[2]}（{c[0]}）" if c[0] in (600, 1500, 2100) or c is cells[-1] else f"{c[2]}" for c in cells) + '。'
    fi = L['fidelity']
    pb = sorted((v['bands']['600~1500'][1], v['name']) for v in L.get('bots', []) if v.get('bands', {}).get('600~1500'))
    if len(pb) >= 2:
        tc += f"各号 600~1500 的中位 {pb[0][0]}~{pb[-1][0]} 拍（最小 {pb[0][1]}、最大 {pb[-1][1]}；{sum(1 for x in pb if x[0] >= 90)}/{len(pb)} 个号 >=90 拍）。"
    return (f"- **指令延迟**（按下令拍分段；拍，P50/P90/Max｜影子下令→进录像→生效）：" + '；'.join(parts) + '。' + tc
            + f"日志 cmds {fi['logCmds']:,}、影子 {fi['shadowCmds']:,}、进录像 {fi['landed']:,}（配上 {fi['exact'] + fi['fuzzy']:,}）；影子下了令、录像里没有的 {fi['lost']} 条 = 丢了或影子多想 {fi['lostBefore']} + 重放末拍还没落地 {fi['lost'] - fi['lostBefore']}"
            + (f"（其中下令时本号日志还在打印的 {sum(b.get('pendingLive', 0) for b in L['funnel']['bands'])} 条，其余是客户端停摆之后影子替它下的）。" if 'pendingLive' in L['funnel']['bands'][0] else '。'))


def loss_line(L):
    ex = [v for v in L['void'] if 'cls' not in v]
    ln = [v for v in L['void'] if 'cls' in v]
    a = []
    for v in ex:
        if v['band'] == '0~600' or not v['atk'] or (v['band'] == '3000+' and not (v['void'] or v['b'])):
            continue
        s = f"{v['band']} 陆攻 {v['atk']} 条没生效 {v['void']}（{pc(v['void'], v['atk'], 0)}"
        if v['a1']:
            s += f"；落地时目标已出局 {v['a1']} 条（内置 AI {v['a1Ai']}）、想发 {wan(v['a1Amt'])}兵"
        if v['a2']:
            s += f"；身边已没有无主地 {v['a2']} 条"
        s += f"）、打错 {v['b']} 条" + (f"（{wan(v['bSent'])}兵进了无主地线）" if v['b'] else '')
        a.append(s)
    red = []
    for v in ln:
        if v['cls'] == 'ai' and v['band'] != '0~600' and v['moved']:
            red.append(f"{v['band']} 出兵 {wan(v['sent'])}、被改挂 {wan(v['moved'])}（{pc(v['moved'], v['sent'], 0)}）")
    d_atk = [f"{v['band']} {v['dups']}/{v['base']}（{pc(v['dups'], v['base'], 0)}；没生效 {v['void']}）" for v in L['dups'] if v['kind'] == 'atk' and v['band'] != '0~600' and v['dups']]
    d_boat = [f"{v['band']} {v['dups']}/{v['base']}" for v in L['dups'] if v['kind'] == 'boat' and v['band'] != '0~600' and v['dups']]
    d_don = [f"{v['band']} {v['dups']}/{v['base']}" for v in L['dups'] if v['kind'] == 'don' and v['band'] != '0~600' and v['dups']]
    bt = [f"{v['band']} {v['batches']} 批 {v['cmds']} 条（整批没生效 {v['allVoid']} 批；清仓批 {v['drain']} 批 {wan(v['drainCost'])}兵）" for v in L['batches']['bands'] if v['band'] != '0~600' and v['batches']]
    s1 = '- **迟到落空 / 打错**（按执行拍分段）：' + '；'.join(a) + '。'
    if red:
        s1 += '打内置 AI 的进攻线（按开线拍）：' + '；'.join(red) + '——目标出局时还挂在线上的兵转去打无主地。'
    s2 = '**重复下单**（前一条还没进录像就对同一目标再下一条；按下令拍）：陆攻 ' + ('；'.join(d_atk) if d_atk else '0')
    if d_boat:
        s2 += '；发船 ' + '、'.join(d_boat)
    if d_don:
        s2 += '；捐款 ' + '、'.join(d_don)
    s2 += '。**同拍批**（同一个号一拍落地 >=3 条）：' + ('；'.join(bt) if bt else '0 批') + '。'
    return s1, s2


def vor_line(C):
    v = C['voronoi']
    s = (f"- **天然份额**（陆路 Voronoi，按真实出生点）：我方 {v['squad']} 个号 {v['squadVor']:,} 格 = 可达陆地的 {100 * v['squadVor'] / v['reach']:.1f}%（人头 {100 * v['squad'] / v['humans']:.1f}%，÷人头 = {v['ratio']:.2f}）；"
         f"单号中位 {v['squadMed']:,} 格对其他真人 {v['otherMed']:,} 格；不到全场人均一半的 {v['small']} 个号，排在全场后四分之一的 {v['bottom16']} 个、前四分之一的 {v['top16']} 个。")
    return s


def cap_part(C):
    out = []
    for c in C.get('capture', []):
        out.append(f"t={c['t']} 我方 {c['squadTerr']:,} 格 = {100 * c['squadRate']:.1f}%（单号中位 {100 * c['squadMedRate']:.1f}%）对其他真人 {100 * c['otherRate']:.1f}%（{100 * c['otherMedRate']:.1f}%）")
    s = '**实抢 ÷ 天然份额**：' + '；'.join(out) + '。'
    f = C.get('flow')
    if f:
        vor = {b['me']: b['vor'] for b in C['voronoi']['bots']}
        idle = [r for r in f["rows"] if r["t0"] < 150]
        if idle:
            live = [r for r in f["rows"] if r["t0"] >= 150]
            v_idle = sum(vor.get(r['me'], 0) for r in idle)
            v_live = sum(vor.get(r['me'], 0) for r in live)
            s += (f"其中 {len(idle)} 个席位 t={f['t0']} 不到 150 格（出生后没有扩张：" + '、'.join(r['name'].lstrip('*') for r in idle) + f"），名下天然份额 {v_idle:,} 格；"
                  f"只算其余 {len(live)} 个号：t={f['t0']} {pc(sum(r['t0'] for r in live), v_live)}、t={f['t1']} {pc(sum(r['t1'] for r in live), v_live)}。")
    return s


def ai_line(C):
    a = C['ai']
    later = [x for x in a['later'] if x['t'] <= 1800]
    ts = ' / '.join(str(x['t']) for x in later)
    sq = ' / '.join(pc(x['near']['squad'], x['near']['n']) for x in later)
    ot = ' / '.join(pc(x['near']['other'], x['near']['n']) for x in later)
    ref = [x for x in a['later'] if x['t'] <= 1500][-1]
    f = C['flow']
    sq_n = len(f['rows'])
    s = (f"- **身边的 AI 地**（t={a['t0']} 与我方接壤或一半以上在我方天然份额里的 {a['n']} 个内置 AI、{a['cells']:,} 格；全场 AI 地 {a['allCells']:,} 格）→ t={ts}：我方 {sq}，其他真人 {ot}；"
         f"其余 AI 地 {ref['rest']['n']:,} 格到 t={ref['t']}：我方 {pc(ref['rest']['squad'], ref['rest']['n'])}、其他真人 {pc(ref['rest']['other'], ref['rest']['n'])}。"
         f"t={f['t0']}→{f['t1']} 人均从 AI 手里拿到 {f['squad']['g_ai'] // max(1, sq_n):,} 格对其他真人 {f['other']['fromAi'] // max(1, f['other']['n']):,} 格，"
         f"人均净增 {(f['squad']['t1'] - f['squad']['t0']) // max(1, sq_n):,} 对 {(f['other']['t1'] - f['other']['t0']) // max(1, f['other']['n']):,} 格。")
    return s


def layer_line(C):
    y = C['layers']
    sp, g, la = y['spawn'], y['gates'], y['late']
    diff = sp['squadVor'] - sp['par']
    s = (f"- **三层归因**（t=600~1500 没抢到内置 AI 的地；三层不互斥、不相加）：① 出生位置：天然份额比按人头{'少' if diff < 0 else '多'} {abs(round(diff)):,} 格（{'−' if diff < 0 else '+'}{abs(100 * diff / sp['par']):.1f}%）；"
         f"② 策略底线：{g['n']:,} 个有 AI 邻居的决策拍可出兵 {pc(g['ok'], g['n'])}，卡在地价闸 {pc(g['botOk'], g['n'])}、底线取 safeFinite 且去掉就能出兵 {pc(g['safeFinite'], g['n'])}"
         f"（其中参照的是我方号或我方空壳的兵 {pc(g['safeFiniteSquad'], g['n'])}）、取 winR {pc(g['winR'], g['n'])}、取 dpKeep {pc(g['dpKeep'], g['n'])}；"
         f"③ 迟到：执行拍在这一段的陆攻 {la['atk']} 条里落空 {la['a1']} 条（{pc(la['a1'], la['atk'])}；想发 {wan(la['a1Amt'])}兵）、打错 {la['b']} 条（{wan(la['bSent'])}兵），"
         f"打 AI 的线出兵 {wan(la['aiSent'])}、其中 {pc(la['aiMoved'], la['aiSent'])} 被改挂到无主地线。")
    return s


def logcap_part(C):
    lc = C.get('logCapture')
    if not lc:
        return ''
    out = []
    for t in lc['ticks']:
        out.append(f"t={t['t']} 有快照的 {t['haveSnap']} 个号 {100 * t['haveRate']:.1f}%（单号中位 {100 * t['medRate']:.1f}%、领土中位 {t['medTerr']:,} 格）")
    return '**实抢 ÷ 天然份额**（只有我方日志快照，其他真人没有读数）：' + '；'.join(out) + '。'


def build(mid, short=False):
    L = jload(mid, 'latency.json')
    C = jload(mid, 'landcap.json')
    lines = []
    if L is None:
        return [f"（{mid}：没有 latency.json，先跑 latency.py {mid} json）"]
    full = 'delay' in L
    title = f"## 5a. 延迟账（latency.py；延迟 = 影子策略下令拍 → 录像执行拍；重放到 t={L['replayLast']}）" if full else "## 5a. 延迟账（latency.py）"
    lines += [title, '']
    if full:
        s1, s2 = loss_line(L)
        if short:
            lines += [spawn_line(L), delay_line(L) + nobullet(s1) + s2]
        else:
            lines += [spawn_line(L), delay_line(L), s1 + s2]
    else:
        lines += [spawn_line(L),
                  '- 对局阶段没有录像：下令拍 → 执行拍的延迟分位数、漏斗、迟到落空 / 打错、重复下单与同拍批都**算不了**；能看的只有日志侧（logdigest.py wallms / seqlag / sentchk / zerodrop / noefftl，见 §7 与 §10）。']
    lines.append('')
    if C is None:
        lines += ['## 5b. 好地账（landcap.py）', '', '- 没有录像：出生点真值与归属网格都没有，天然份额、实抢率、身边 AI 地去向、三层归因都**算不了**。', '']
        return lines
    full_c = 'capture' in C
    lines += ['## 5b. 好地账（landcap.py；领土网格来自真引擎重放）' if full_c else '## 5b. 好地账（landcap.py；只有选点阶段的录像）', '']
    if full_c:
        if short:
            lines += [vor_line(C) + cap_part(C) + nobullet(ai_line(C)), layer_line(C)]
        else:
            lines += [vor_line(C) + cap_part(C), ai_line(C), layer_line(C)]
    else:
        lines += [vor_line(C) + logcap_part(C),
                  '- 对局阶段没有归属网格：身边 AI 地的去向、其他真人的实抢率、三层归因里的第 ②③ 层都**算不了**；第 ① 层（出生位置）就是上面的天然份额。']
    lines.append('')
    return lines


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    short = '--short' in sys.argv[2:]
    print('\n'.join(build(mid, short)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
