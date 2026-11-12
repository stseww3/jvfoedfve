#!/usr/bin/env python3
# A011_facts.py — A011 专用事实表（全部机械计数；只读 /tmp/c136-r05/truth/A011.json、work/A011-{cmds.tsv,delay.json,land.json,attrib.json}、
#   发现集 bundles/*/results.csv、bundles/{A010,A011,A013,B009}/in_game.log、统筹发布的 src/tools/rooms-discovery.json）。
#   先跑：bash scripts/accounts_batch.sh A011（产出 truth、cmds.tsv 和三本账的 json）。
#   A 段：A011 的 10 个结果行（拍、秒、记录时刻、地、兵、sent/accepted）；是否同一拍；记录时刻的先后。
#   B 段：钟面模型——发现集每间房用阵亡行拟合「记录时刻 − 开房时刻 = a + b×拍」（≥4 个阵亡行、拍跨度 ≥1500）；
#         b（每拍毫秒）与 a（开房到第 0 拍的秒数）按房间真人数分两档列出分布；据此推 A011 第 1071 拍的 UTC。
#   C 段：B009 另一间房（c110 机群的 9 个号）的结果行；用它唯一的阵亡行做锚，推它最后一拍 6643 的 UTC。
#   D 段：发现集里「同一拍 ≥5 个号 left」的房间逐个列出：停拍的 UTC（有阵亡行就用最后一个阵亡行做锚，否则用 B 段的 a、b）、
#         登记离场的时刻、两者相差的秒数；停拍时刻相差 ≤10 秒的房间归成一组。另列：A011 开房前后 25 分钟内发现集里的局（manifest.jsonl）、
#         停拍那一刻发现集里还在打的房间。
#   E 段：日志全局序号——A011 首末序号、RESULT 行之间缺的序号；A010 末行、A013 首行。
#   F 段：选点期——全场/我方出生指令落地拍的分布；逐号「日志指派次数 / 录像指令条数 / 最后指派 vs 最后落地」；
#         协调器 27 轮求解（点集相同只是换人的轮数）；ryan_m、leo_tx 末段的日志行与录像指令逐条对列；最终出生点两两距离。
#   G 段：名字撞名单——录像名单里去掉 [标签] 后落在策略硬编码名单里的非我方真人；[HL-SPAWN] 的 squad= 取值；
#         该真人选点期逐条出生指令的位置与当时最近的我方号的距离。另列选点期曾经落在我方任一号 50 格内的其他真人。
#   H 段：300/600/900/终局 各拍：我方号、路人队友、敌方真人的地中位、密度中位、兵合计；我方号逐个的名次；队伍合计。
#   I 段：叠点的两个号（ryan_m、leo_tx）与其余 8 个号：地、出生份额、留底决策拍占比。
#   J 段：600 拍贴着我方号的机器人地到 900 拍、终局归谁；600 拍起全场机器人地各组拿到多少。
#   K 段：停拍前的命令流——900 拍起每 7 拍一个回合的全场落地指令数；我方号最后 150 拍每条指令的决策拍/落地拍/延迟；
#         落地延迟按 60 拍一窗的中位（看停拍前有没有爬坡）；同拍批（同一玩家同一拍 ≥3 条）我方号对其他真人。
#   L 段：正文引用的零散数字（终局兵地、密度、各号 600→900 的地增量、中途离场的其他真人、各号 900/1050 拍的边界构成与队友占比）。
#   N 段：兵账对照（truth.players 的全程合计）：编队 / 路人队友 / 敌方真人 各自的利息地租、投向中立/机器人/真人的兵、每格机器人地花的兵、
#         被拿走的地、被打掉的兵、终局存兵 ÷ 全程利息地租（没花出去的比例）。
#   M 段：留底探针（work/A011-floor.txt = shadow.mjs A011 --cold --floor 605,655,…,1055 的逐样本行）：
#         「贴着几乎没兵的机器人、却没有一个机器人目标过得了留底」的样本数；充当锁的机器人（经它定留底）逐个列出；互锁的号对。
# 用法：python3 scripts/review_build/A011_facts.py [--sec A,B,C,D,E,F,G,H,I,J,K,L,M,N] [--dmin 5]
import csv, json, math, os, re, sys, collections, statistics as st, datetime as dt, glob
M = 'A011'
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
W = os.environ.get('C136_WORK', '/tmp/c136-r05/work')
T = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
sec = set((sys.argv[sys.argv.index('--sec') + 1] if '--sec' in sys.argv else 'A,B,C,D,E,F,G,H,I,J,K,L,M,N').split(','))
H = T['humans']
P = {p['id']: p for p in T['players']}
SQ = {s['p']: s['bot'] for s in T['squad']}
BOT2P = {b: p for p, b in SQ.items()}
card = json.load(open(f'{DATA}/bundles/{M}/card.json'))
MW = T['map']['W']
k = lambda v: (f'{v / 1e6:.2f}M' if abs(v) >= 1e6 else f'{v / 1e3:.0f}k' if abs(v) >= 1e4 else f'{v:.0f}')
nm = lambda p: (SQ[p] if p in SQ else P[p]['name'])
dist = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
cmds = list(csv.DictReader(open(f'{W}/{M}-cmds.tsv', encoding='utf-8'), delimiter='\t'))
xy = lambda a: (int(a) % MW, int(a) // MW)
ts = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
hms = lambda x: dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime('%H:%M:%S.%f')[:-5]
med = lambda xs: st.median(xs) if xs else float('nan')


def rows_of(m):
    return list(csv.DictReader(open(f'{DATA}/bundles/{m}/results.csv', encoding='utf-8')))


def rooms_of_all():
    """每间房的结果行：按统筹的 rooms-discovery.json（号名 + me 对到房）；一局只有一间房时全部行归它。"""
    J = json.load(open(f'{DATA}/src/tools/rooms-discovery.json'))
    out = []
    for m in J:
        mid = m['matchId']
        try:
            rs = rows_of(mid)
        except FileNotFoundError:
            continue
        for r in m['rooms']:
            keys = {(n, b.get('me')) for b in r.get('bots', []) for n in b.get('names', [])}
            rr = [x for x in rs if (x['bot'], int(x['meId']) if x['meId'] not in ('', None) else None) in keys] if len(m['rooms']) > 1 else rs
            if rr:
                out.append((mid, r['roomIdx'], r.get('seeded'), rr))
    return out


def start_of(rr):
    return med([ts(x['at']) - float(x['seconds']) for x in rr if x['at'] and x['seconds'] not in ('', None)])


def fit(rr):
    pts = [(int(x['tick']), ts(x['at'])) for x in rr if x['event'] == 'died' and x['at'] and int(x['tick']) > 0]
    if len(pts) < 4 or max(p[0] for p in pts) - min(p[0] for p in pts) < 1500:
        return None
    s0 = start_of(rr)
    n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y - s0 for _, y in pts) / n
    b = sum((x - mx) * (y - s0 - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    a = my - b * mx
    res = max(abs((y - s0) - (a + b * x)) for x, y in pts)
    return a, b, n, res


ROOMS = rooms_of_all() if sec & {'B', 'C', 'D'} else []
FITS_ALL = {(m, i): f for m, i, sd, rr in ROOMS for f in [fit(rr)] if f}
FITS = {key: f for key, f in FITS_ALL.items() if f[3] <= 1.0}   # 只用最大残差 ≤1 秒的房间（其余是客户端本地拍落后的房，另计）
big = [(m, i) for m, i, sd, rr in ROOMS if (m, i) in FITS and (sd or 0) > 50]
small = [(m, i) for m, i, sd, rr in ROOMS if (m, i) in FITS and (sd or 0) <= 50]
B_ALL = sorted(FITS[x][1] for x in FITS)
A_BIG = sorted(FITS[x][0] for x in big)
A_SMALL = sorted(FITS[x][0] for x in small)
q = lambda xs, f: xs[min(len(xs) - 1, max(0, round(f * (len(xs) - 1))))]

if 'A' in sec:
    print('== A A011 的结果行 ==')
    rr = rows_of(M)
    s0 = start_of(rr)
    print(f"   开房时刻（各行 记录时刻 − seconds 的中位）= {hms(s0)} UTC；card.timeUtc = {card['timeUtc']}")
    for x in sorted(rr, key=lambda x: x['at']):
        print(f"   {x['bot']}#{x['meId']}: event={x['event']} result={x['result']} tick={x['tick']} seconds={x['seconds']} at={x['at'][11:23]}（开房后 {ts(x['at']) - s0:.1f} 秒）place={x['place']} 地 {x['territory']} 兵 {x['balance']} sent/accepted {x['sent']}/{x['accepted']} alivePlayers={x['alivePlayers']} team='{x['teamMine']}'")
    tk = sorted({int(x['tick']) for x in rr}); at = sorted(ts(x['at']) for x in rr)
    print(f"   10 行的 tick 取值 {tk}（1071 = 7×{1071 // 7}，余 {1071 % 7}）；记录时刻 {hms(at[0])}–{hms(at[-1])}，前后 {at[-1] - at[0]:.1f} 秒；第 1 个到第 2 个隔 {at[1] - at[0]:.1f} 秒，第 2 个到最后一个 {at[-1] - at[1]:.1f} 秒")
    print(f"   录像：totalTicks {T['endTick']}，最后一条指令在 {max(int(r['tick']) for r in cmds)} 拍；录像里我方号的离场指令 {sum(1 for r in cmds if r['kind'].startswith('leave') and int(r['player']) in SQ)} 条")
    print(f"   地/兵合计（结果行）：地 {sum(int(x['territory']) for x in rr)}、兵 {sum(int(x['balance']) for x in rr)}；sent 合计 {sum(int(x['sent']) for x in rr)}、accepted 合计 {sum(int(x['accepted']) for x in rr)}；录像里我方号的指令合计 {sum(1 for r in cmds if int(r['player']) in SQ)} 条")

if 'B' in sec:
    print('== B 钟面模型（发现集各房的阵亡行拟合：记录时刻 − 开房时刻 = a + b×拍）==')
    print(f'   可拟合的房间 {len(FITS_ALL)} 间（≥4 个阵亡行、拍跨度 ≥1500）；其中最大残差 ≤1 秒的 {len(FITS)} 间（下面只用这些）：真人 >50 的 {len(big)} 间、≤50 的 {len(small)} 间；残差 >1 秒的 {len(FITS_ALL) - len(FITS)} 间：' + '、'.join(f'{m_}房{i_}（{FITS_ALL[(m_, i_)][3]:.1f} 秒）' for m_, i_ in sorted(FITS_ALL) if (m_, i_) not in FITS))
    print(f'   b（毫秒/拍）：中位 {med(B_ALL) * 1000:.2f}，四分位 {q(B_ALL, .25) * 1000:.2f}–{q(B_ALL, .75) * 1000:.2f}，最小 {B_ALL[0] * 1000:.2f}、最大 {B_ALL[-1] * 1000:.2f}')
    print(f'   a（秒，真人 >50 的房）：中位 {med(A_BIG):.1f}，四分位 {q(A_BIG, .25):.1f}–{q(A_BIG, .75):.1f}，最小 {A_BIG[0]:.1f}、最大 {A_BIG[-1]:.1f}')
    print(f'   a（秒，真人 ≤50 的房）：中位 {med(A_SMALL):.1f}，四分位 {q(A_SMALL, .25):.1f}–{q(A_SMALL, .75):.1f}，最小 {A_SMALL[0]:.1f}、最大 {A_SMALL[-1]:.1f}')
    resid = sorted(FITS[x][3] for x in FITS)
    print(f'   拟合残差（各房最大绝对残差，秒）：中位 {med(resid):.2f}，最大 {resid[-1]:.2f}')
    for key in (('A010', 0), ('A013', 0), ('A014', 0), ('B010', 0)):
        if key in FITS_ALL:
            a, b, n, r = FITS_ALL[key]; print(f'      {key[0]} 房{key[1]}: a={a:.1f} 秒、b={b * 1000:.2f} 毫秒/拍（{n} 个阵亡行，最大残差 {r:.2f} 秒）')
    s0 = start_of(rows_of(M))
    lo = s0 + q(A_BIG, .25) + q(B_ALL, .25) * 1071; hi = s0 + q(A_BIG, .75) + q(B_ALL, .75) * 1071; mid = s0 + med(A_BIG) + med(B_ALL) * 1071
    lo2 = s0 + A_BIG[0] + B_ALL[0] * 1071; hi2 = s0 + A_BIG[-1] + B_ALL[-1] * 1071
    print(f'   A011 第 1071 拍 ≈ 开房后 {med(A_BIG) + med(B_ALL) * 1071:.1f} 秒 = {hms(mid)} UTC（四分位 {hms(lo)}–{hms(hi)}；极值 {hms(lo2)}–{hms(hi2)}）')
    at = sorted(ts(x['at']) for x in rows_of(M))
    print(f'   10 个号登记 left 的时刻比这一拍晚：最早 {at[0] - mid:.1f} 秒、第 2 个 {at[1] - mid:.1f} 秒、最晚 {at[-1] - mid:.1f} 秒')
    print(f'   如果客户端一直在走拍，登记时刻对应的拍应是 {(at[0] - s0 - med(A_BIG)) / med(B_ALL):.0f}–{(at[-1] - s0 - med(A_BIG)) / med(B_ALL):.0f}；结果行里写的都是 1071')

if 'C' in sec:
    print('== C B009 另一间房（c110 机群）==')
    for m, i, sd, rr in ROOMS:
        if m != 'B009': continue
        s0 = start_of(rr)
        ev = collections.Counter(x['event'] for x in rr)
        print(f"   B009 房{i}: 真人 {sd}，结果行 {len(rr)} 个 {dict(ev)}，开房 {hms(s0)} UTC，meId {sorted(int(x['meId']) for x in rr)}")
        died = [x for x in rr if x['event'] == 'died']; left = [x for x in rr if x['event'] == 'left']
        for x in died: print(f"      阵亡行 {x['bot']}#{x['meId']} tick={x['tick']} seconds={x['seconds']} at={x['at'][11:23]}")
        if left:
            tkc = collections.Counter(int(x['tick']) for x in left); at = sorted(ts(x['at']) for x in left)
            print(f"      left 行 {len(left)} 个：tick 取值 " + '、'.join(f'{t_}（7×{t_ // 7} 余 {t_ % 7}）×{n_} 个号' for t_, n_ in sorted(tkc.items())) + f"；记录时刻 {hms(at[0])}–{hms(at[-1])}")
            for x in sorted(left, key=lambda x: x['at']): print(f"         {x['bot']}#{x['meId']} tick={x['tick']} seconds={x['seconds']} at={x['at'][11:23]} 地 {x['territory']} 兵 {x['balance']}")
            if died:
                d = max(died, key=lambda x: int(x['tick']))
                for t_ in sorted(tkc):
                    dtk = t_ - int(d['tick'])
                    e = [ts(d['at']) + dtk * b for b in (B_ALL[0], q(B_ALL, .25), med(B_ALL), q(B_ALL, .75), B_ALL[-1])]
                    print(f"      以阵亡行为锚（{d['tick']} 拍 = {d['at'][11:23]}），往后 {dtk} 拍 × b：第 {t_} 拍 ≈ {hms(e[2])} UTC（b 取四分位 {hms(e[1])}–{hms(e[3])}；极值 {hms(e[0])}–{hms(e[4])}）；到登记 left {at[0] - e[2]:.1f}–{at[-1] - e[2]:.1f} 秒")
                print(f"      这间房自己的 (秒, 拍)：{d['seconds']} 秒 / {d['tick']} 拍 → 扣掉 a（≤50 人房中位 {med(A_SMALL):.1f} 秒）后每拍 {(float(d['seconds']) - med(A_SMALL)) / int(d['tick']) * 1000:.1f} 毫秒")
    c9 = json.load(open(f'{DATA}/bundles/B009/card.json'))
    print(f"   B009 卡：cohort {c9['cohort']}，timeUtc {c9['timeUtc']}，resultLabel {c9.get('outcome', {}).get('resultLabel', c9.get('resultLabel'))}")

if 'D' in sec:
    DMIN = int(sys.argv[sys.argv.index('--dmin') + 1]) if '--dmin' in sys.argv else 5
    print(f'== D 发现集里「同一拍 ≥{DMIN} 个号 left」的房间（--dmin 可改门槛）==')
    found = []
    for m, i, sd, rr in ROOMS:
        byt = collections.defaultdict(list)
        for x in rr:
            if x['event'] == 'left' and x['at']: byt[int(x['tick'])].append(x)
        for tk, xs in byt.items():
            if len(xs) < DMIN: continue
            s0 = start_of(rr)
            died = [x for x in rr if x['event'] == 'died' and x['at'] and int(x['tick']) <= tk]
            if died:
                d = max(died, key=lambda x: int(x['tick'])); stop = ts(d['at']) + (tk - int(d['tick'])) * med(B_ALL); how = f"锚 {d['tick']} 拍"
            else:
                a = med(A_BIG) if (sd or 0) > 50 else med(A_SMALL); stop = s0 + a + med(B_ALL) * tk; how = f'a={a:.1f}'
            at = sorted(ts(x['at']) for x in xs)
            found.append((stop, m, i, sd, len(xs), len(rr), tk, how, at))
    found.sort()
    grp = []
    for f in found:
        if grp and f[0] - grp[-1][-1][0] <= 10: grp[-1].append(f)
        else: grp.append([f])
    for g in grp:
        print(f"   -- 一组（{len(g)} 间房）" if len(g) > 1 else '   -- 单独一间')
        for stop, m, i, sd, n, tot, tk, how, at in g:
            day = dt.datetime.fromtimestamp(stop, dt.timezone.utc).strftime('%m-%d')
            print(f"      {m} 房{i}（真人 {sd}，结果行 {tot} 个）：{n} 个号 left 在 {tk} 拍（余 {tk % 7}）；停拍 ≈ {day} {hms(stop)} UTC（{how}）；登记 left {hms(at[0])}–{hms(at[-1])}，晚 {at[0] - stop:.0f}–{at[-1] - stop:.0f} 秒")
    print(f"   合计 {len(found)} 间房、{sum(f[4] for f in found)} 个号；成组（停拍时刻相差 ≤10 秒）的 {sum(1 for g in grp if len(g) > 1)} 组 {sum(len(g) for g in grp if len(g) > 1)} 间房")
    tot_left = sum(1 for m, i, sd, rr in ROOMS for x in rr if x['event'] == 'left'); tot = sum(len(rr) for m, i, sd, rr in ROOMS)
    print(f"   发现集全部结果行 {tot} 个，其中 event=left 的 {tot_left} 个；落在上面这些房里的 {sum(f[4] for f in found)} 个")

if 'D' in sec:
    # 停拍前后两个机群在发现集里的开房时刻（manifest.jsonl；验证集的局这里看不到）
    man = [json.loads(l) for l in open(f'{DATA}/manifest.jsonl', encoding='utf-8')]
    t0 = ts('2026-11-09T15:21:20Z')
    near = sorted((ts(r['timeUtc']), r['matchId'], r['cohort']) for r in man if r.get('timeUtc') and abs(ts(r['timeUtc']) - t0) <= 1500)
    print('   A011 开房前后 25 分钟内发现集里的局（开房时刻，相对 15:22:44 停拍的分钟数）：' + '；'.join(
        f"{m} {c} {dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%H:%M:%S')}（{(t - (t0 + 83.9)) / 60:+.1f}）" for t, m, c in near))
if 'D' in sec:
    # 停拍那一刻（A011 开房 + 83.9 秒）发现集里哪些房还在打：开房时刻 ≤ 停拍时刻 ≤ 该房最后一个结果行的记录时刻
    tf = ts('2026-11-09T15:21:20Z') + 0.2 + 83.9
    live = []
    for m, i, sd, rr in ROOMS:
        ats = [ts(x['at']) for x in rr if x['at']]
        if not ats: continue
        s0 = start_of(rr)
        if s0 <= tf <= max(ats): live.append((m, i, sd, len(rr), s0, max(ats)))
    print(f"   停拍那一刻（{hms(tf)} UTC）发现集里还在打的房 {len(live)} 间：" + '；'.join(f"{m} 房{i}（真人 {sd}，结果行 {n} 个，开房 {hms(a)}，最后一个结果行 {hms(b)}）" for m, i, sd, n, a, b in live))
if 'E' in sec:
    print('== E 日志全局序号 ==')
    def seqs(m):
        out = []
        for ln in open(f'{DATA}/bundles/{m}/in_game.log', encoding='utf-8', errors='replace'):
            a = ln.split('\t', 1)
            if a[0].isdigit(): out.append((int(a[0]), a[1].strip() if len(a) > 1 else ''))
        return out
    s = seqs(M); ss = [x for x, _ in s]
    miss = sorted(set(range(min(ss), max(ss) + 1)) - set(ss))
    print(f'   A011 日志 {len(s)} 行，序号 {min(ss)}–{max(ss)}（跨 {max(ss) - min(ss) + 1} 个），缺 {len(miss)} 个')
    res = [x for x, l in s if l.startswith('[RESULT')]; lastTick = max(x for x, l in s if '[HL-TICK]' in l)
    print(f'   最后一条 [HL-TICK] 序号 {lastTick}；RESULT 行序号 {res}；{lastTick}–{res[-1]} 之间缺的序号 {[x for x in miss if lastTick < x < res[-1]]}')
    print(f'   其余缺号：{[x for x in miss if x < lastTick]}')
    tl = collections.Counter(int(re.search(r't=(\d+)', l).group(1)) for _, l in s if '[HL-TICK]' in l)
    print(f'   [HL-TICK] 行按 t：{dict(sorted(tl.items()))}（每 90 拍一条；下一条该在 1080 拍）')
    for m in ('A010', 'A013'):
        z = seqs(m); print(f'   {m} 日志序号 {min(x for x, _ in z)}–{max(x for x, _ in z)}（{len(z)} 行）')

if 'F' in sec:
    print('== F 选点期 ==')
    sp = [r for r in cmds if r['kind'] == 'spawn']
    ours = [r for r in sp if int(r['player']) in SQ]; oth = [r for r in sp if int(r['player']) not in SQ]
    t_all = [int(r['tick']) for r in sp]
    print(f"   全场出生指令 {len(sp)} 条，拍 {min(t_all)}…{max(t_all)}；我方 {len(ours)} 条，拍 {min(int(r['tick']) for r in ours)}…{max(int(r['tick']) for r in ours)}；其他真人 {len(oth)} 条（{len({r['player'] for r in oth})} 人），拍 {min(int(r['tick']) for r in oth)}…{max(int(r['tick']) for r in oth)}")
    last_ours = max(int(r['tick']) for r in ours)
    print(f"   我方最后一条落地之后（>{last_ours} 拍）其他真人还落地 {sum(1 for r in oth if int(r['tick']) > last_ours)} 条（{len({r['player'] for r in oth if int(r['tick']) > last_ours})} 人）")
    c = collections.Counter(int(r['tick']) for r in ours)
    print('   我方出生指令按拍：' + ' '.join(f'{t}:{v}' for t, v in sorted(c.items())))
    lv = [(int(r['tick']), nm(int(r['player'])), P[int(r['player'])]['team']) for r in cmds if r['kind'].startswith('leave') and int(r['tick']) <= 0]
    print('   选点期离场的真人：' + '；'.join(f'{n}（T{tm}）{t} 拍' for t, n, tm in lv))
    # 日志指派
    logA = collections.defaultdict(list); rounds = []
    for ln in open(f'{DATA}/bundles/{M}/in_game.log', encoding='utf-8', errors='replace'):
        a = ln.split('\t', 1)
        if len(a) < 2: continue
        m_ = re.match(r'\[(\w+)\] \[HL-SPAWN-BACKEND\] me=(\d+) slot=(\d+) role=(\w+) -> \((\d+),(\d+)\)', a[1])
        if m_: logA[m_.group(1)].append((int(a[0]), (int(m_.group(5)), int(m_.group(6))), m_.group(4)))
        if '[BACKEND-SPAWN-COORD]' in a[1]:
            ms = int(re.search(r'minSep=(\d+)px', a[1]).group(1)); el = float(re.search(r'in ([\d.]+)ms', a[1]).group(1))
            rounds.append((int(a[0]), ms, el, {b: (int(x), int(y)) for b, x, y in re.findall(r'\[APEX\] (\w+)\([A-Z_]+\)->\((\d+),(\d+)\)', a[1])}))
    asg = [tuple(sorted(r[3].items())) for r in rounds]; pts = [tuple(sorted(r[3].values())) for r in rounds]
    perm = sum(1 for i in range(1, len(rounds)) if pts[i] == pts[i - 1] and asg[i] != asg[i - 1])
    same = sum(1 for i in range(1, len(rounds)) if asg[i] == asg[i - 1])
    tail = 0
    for i in range(len(rounds) - 1, 0, -1):
        if asg[i] == asg[-1]: tail += 1
        else: break
    print(f'   协调器求解 {len(rounds)} 轮：不同的指派 {len(set(asg))} 个、不同的点集 {len(set(pts))} 个；与上一轮点集相同只是换了人的 {perm} 轮；与上一轮完全相同的 {same} 轮；末尾连续相同的 {tail} 轮（序号 {rounds[-tail][0]}–{rounds[-1][0]}）；耗时中位 {med([r[2] for r in rounds]):.0f} 毫秒')
    print('   minSep 逐轮：' + ' '.join(str(r[1]) for r in rounds))
    lastpts = sorted(rounds[-1][3].values())
    dd = sorted(dist(a, b) for i, a in enumerate(lastpts) for b in lastpts[i + 1:])
    print(f'   最后一轮 10 个点两两距离：最小 {dd[0]:.0f}、次小 {dd[1]:.0f}、中位 {med(dd):.0f}；每个点到最近点：' + ' '.join(f'{min(dist(a, b) for b in lastpts if b != a):.0f}' for a in lastpts))
    for i in range(1, len(rounds)):
        if pts[i] == pts[i - 1] and asg[i] != asg[i - 1]:
            sw = [b for b in rounds[i][3] if rounds[i][3][b] != rounds[i - 1][3][b]]
            print(f'      序号 {rounds[i][0]}：点集不变，换了人的号 {sw}')
    for b in sorted(logA, key=lambda b: BOT2P[b]):
        p = BOT2P[b]; rc = [(int(r['tick']), xy(r['a'])) for r in sp if int(r['player']) == p]
        la = logA[b]; fin = tuple(P[p]['spawn'])
        print(f"      {b}#{p}: 日志指派 {len(la)} 次、录像出生指令 {len(rc)} 条（末条 {rc[-1][0]} 拍 → {rc[-1][1]}）；日志最后指派 {la[-1][1]} {la[-1][2]}（序号 {la[-1][0]}）；引擎落点 {fin}；最后指派与末条指令{'一致' if dist(la[-1][1], rc[-1][1]) <= 6 else '不一致，差 %.0f 格' % dist(la[-1][1], rc[-1][1])}；末条指令到引擎落点 {dist(rc[-1][1], fin):.1f} 格")
    print('   ryan_m / leo_tx 末段（日志序号 ≥ 6985296 的指派，与 −36 拍起的录像指令，各按原顺序）：')
    for b in ('ryan_m', 'leo_tx'):
        print(f"      {b} 日志：" + ' → '.join(f'{s_}:{pt}' for s_, pt, _ in logA[b] if s_ >= 6985296))
        print(f"      {b} 录像：" + ' → '.join(f"{int(r['tick'])}拍[{i}]:{xy(r['a'])}" for i, r in enumerate(cmds) if r['kind'] == 'spawn' and int(r['player']) == BOT2P[b] and int(r['tick']) >= -36))
    # 同拍多条出生指令的先后：录像块内顺序 对 日志（＝客户端收到指派并下单）的顺序
    def wof(mid):
        for ln in open(f'{DATA}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
            m_ = re.search(r'map=(\d+)x(\d+)', ln)
            if m_ and 'BACKEND-SPAWN-COORD' in ln: return int(m_.group(1))
        return None
    print('   同拍 ≥2 条出生指令（同一个号）在录像块内的顺序，对日志里指派的先后（对齐：录像这一拍的点集 = 日志里接下来连续 n 条的点集）：')
    tot = collections.Counter()
    for mid in sorted({f.split('/')[-1][:4] for f in glob.glob(f'{W}/*-cmds.tsv')}):
        w_ = wof(mid)
        if not w_: continue
        cm = list(csv.DictReader(open(f'{W}/{mid}-cmds.tsv', encoding='utf-8'), delimiter='\t'))
        names = {int(r['player']): re.sub(r'\[[^\]]*\]', '', r['name']).strip() for r in cm if r['kind'] == 'spawn'}
        lg = collections.defaultdict(list)
        for ln in open(f'{DATA}/bundles/{mid}/in_game.log', encoding='utf-8', errors='replace'):
            a = ln.split('\t', 1)
            if len(a) < 2: continue
            m_ = re.match(r'\[([^\]]+)\] \[HL-SPAWN-BACKEND\] me=(\d+) .*?-> \((\d+),(\d+)\)', a[1])
            if m_: lg[(m_.group(1), int(m_.group(2)))].append((int(m_.group(3)), int(m_.group(4))))
        res = collections.Counter(); ex = []
        for (b, me), L in lg.items():
            if names.get(me) != b: continue
            R = collections.defaultdict(list)
            for r in cm:
                if r['kind'] == 'spawn' and int(r['player']) == me: R[int(r['tick'])].append((int(r['a']) % w_, int(r['a']) // w_))
            i = 0
            for t in sorted(R):
                g = R[t]; n = len(g)
                if n == 1:
                    for j in range(i, min(i + 6, len(L))):
                        if L[j] == g[0]: i = j + 1; break
                    continue
                hit = None
                for j in range(i, min(i + 6, len(L) - n + 1)):
                    if sorted(L[j:j + n]) == sorted(g): hit = j; break
                if hit is None: res['对不上'] += 1; continue
                sl = L[hit:hit + n]; i = hit + n
                if len(set(g)) == 1: res['同一个点'] += 1
                elif sl == g: res['与日志同序'] += 1
                elif sl == g[::-1]: res['与日志反序'] += 1; ex.append(f'{b}@{t}×{n}')
                else: res['其他排列'] += 1
        tot.update(res)
        # 末条落地指令 ≠ 日志最后指派 的号；其中「最后一拍落地 ≥2 条、块内第一条 = 日志最后指派」的（＝后发的那条被先发的覆盖）
        mism = []; lifo = []
        for (b, me), L in lg.items():
            if names.get(me) != b or not L: continue
            R = [(int(r['tick']), (int(r['a']) % w_, int(r['a']) // w_)) for r in cm if r['kind'] == 'spawn' and int(r['player']) == me]
            if not R: continue
            if math.hypot(R[-1][1][0] - L[-1][0], R[-1][1][1] - L[-1][1]) > 6:
                mism.append(b)
                lastT = [pt for t_, pt in R if t_ == R[-1][0]]
                if len(lastT) >= 2 and math.hypot(lastT[0][0] - L[-1][0], lastT[0][1] - L[-1][1]) <= 6: lifo.append(f'{b}@{R[-1][0]}')
        tot['末条≠最后指派的号'] += len(mism); tot['其中被同拍先发的那条覆盖'] += len(lifo)
        if sum(res.values()) or mism: print(f"      {mid}: 同拍组 {sum(res.values())} 个：{dict(res)}" + (f"｜反序的：{' '.join(ex[:14])}" if mid == M else '') + f"｜末条落地指令 ≠ 日志最后指派的号 {len(mism)} 个 {mism}，其中最后一拍 ≥2 条且块内第一条 = 最后指派的 {len(lifo)} 个 {lifo}")
    print(f'      合计：{dict(tot)}')
    sqs = {p: tuple(P[p]['spawn']) for p in SQ}
    nn = {p: min((dist(sqs[p], sqs[q_]), q_) for q_ in SQ if q_ != p) for p in SQ}
    print('   引擎落点到最近我方号：' + '；'.join(f'{SQ[p]}→{SQ[v[1]]} {v[0]:.1f}' for p, v in sorted(nn.items(), key=lambda kv: kv[1][0])))
    vals = sorted(v[0] for v in nn.values())
    land = card['mapLand']; rc_ = math.sqrt(land / H / math.pi)
    print(f'   最近我方号距离：中位 {med(vals):.0f}、最小 {vals[0]:.1f}、最大 {vals[-1]:.0f} 格；全图人均 {land / H:.0f} 格 → 人均间距 2×sqrt(人均/π) = {2 * rc_:.0f} 格')
    cx = sum(x for x, _ in sqs.values()) / 10; cy = sum(y for _, y in sqs.values()) / 10
    print(f'   阵心 ({cx:.0f},{cy:.0f})，最远的号离阵心 {max(dist((cx, cy), s_) for s_ in sqs.values()):.0f} 格；(1360,274) 这个点最终没有号：离它最近的我方落点 ' + '、'.join(f'{SQ[p]} {dist((1360, 274), s_):.0f}' for p, s_ in sorted(sqs.items(), key=lambda kv: dist((1360, 274), kv[1]))[:4]))

if 'G' in sec:
    print('== G 名字撞名单 ==')
    LIST = ['mishi', 'matzz', 'kiholma', 'leo_99', 'racoon', 'zexos', 'talon', 'vortex', 'kronos', 'nexus', '777', 'sayo', 'kaito', 'riku', '_alex', 'tomo', 'zero_2', 'sora',
            'lucas94', 'dave_w', 'mark07', 'kevin_k', 'ethan21', 'ryan_m', 'noah88', 'leo_tx', 'alex_k', 'zero_7', 'kaito9', 'riku_x', 'sora_w', 'zexos1', 'talon5']
    low = lambda n: re.sub(r'\[[^\]]*\]', '', n).strip().lower()
    hit = [p for p in range(H) if low(P[p]['name']) in LIST]
    print(f"   录像名单里去掉 [标签] 后落在名单（{len(LIST)} 个名字）里的真人 {len(hit)} 个：" + '、'.join(f"{P[p]['name']}#{p}（T{P[p]['team']}{'，我方号' if p in SQ else ''}）" for p in hit))
    sq_log = collections.Counter(re.search(r'squad=(\d+)', ln).group(1) for ln in open(f'{DATA}/bundles/{M}/in_game.log', encoding='utf-8', errors='replace') if '[HL-SPAWN]' in ln)
    print(f'   日志 [HL-SPAWN] 行的 squad= 取值：{dict(sq_log)}')
    pos = {}; hist = collections.defaultdict(list)
    for r in cmds:
        if r['kind'] != 'spawn': continue
        p = int(r['player']); t = int(r['tick']); pos[p] = xy(r['a'])
        if p not in SQ:
            near = min(((dist(pos[p], pos[s_]), s_) for s_ in SQ if s_ in pos), default=None)
            hist[p].append((t, pos[p], near))
    for p in hit:
        if p in SQ: continue
        print(f"   {P[p]['name']}#{p} 的出生指令：" + '；'.join(f'{t} 拍 {pt} 距最近我方号 {SQ[n[1]]} {n[0]:.0f} 格' if n else f'{t} 拍 {pt}' for t, pt, n in hist[p]) + f"；最终出生 {tuple(P[p]['spawn'])}，终局地 {P[p]['endTerr']} 兵 {P[p]['endBal']}")
    close = []
    for p, hs in hist.items():
        ts_ = [(t, n[0], n[1]) for t, pt, n in hs if n and n[0] <= 50]
        if ts_: close.append((min(x[1] for x in ts_), p, ts_, hs))
    print(f'   选点期某条出生指令落在我方任一号当时位置 50 格内的其他真人 {len(close)} 个：')
    for d0, p, ts_, hs in sorted(close):
        fin = tuple(P[p]['spawn']); fd = min(dist(fin, tuple(P[s_]['spawn'])) for s_ in SQ) if fin[0] >= 0 else None
        print(f"      {P[p]['name']}#{p}（T{P[p]['team']}）：最近 {d0:.0f} 格；这样的指令 " + '、'.join(f'{t} 拍离 {SQ[s_]} {d:.0f}' for t, d, s_ in ts_) + f"；它最后一条出生指令 {hs[-1][0]} 拍 {hs[-1][1]}；" + (f'最终出生点离最近我方号 {fd:.0f} 格' if fd is not None else '没有进场（选点期离场）') + (f"；离场拍 {P[p]['leftT']}" if P[p]['leftT'] != -1 else ''))

if 'H' in sec:
    print('== H 各拍站位（在场 = 地 > 0）==')
    HS = T['HS']
    def groups(terr, bal):
        g = collections.defaultdict(list)
        for p in range(H):
            if terr[p] <= 0: continue
            g['我方号' if p in SQ else ('路人队友' if P[p]['team'] == T['ourTeam'] else '敌方真人')].append((terr[p], bal[p], p))
        return g
    samples = [(t, HS['terr'][i], HS['bal'][i]) for i, t in enumerate(HS['t'])] + [(T['endTick'], [P[p]['endTerr'] for p in range(H)], [P[p]['endBal'] for p in range(H)])]
    for t, terr, bal in samples:
        g = groups(terr, bal)
        allp = sorted((terr[p] for p in range(H) if terr[p] > 0), reverse=True)
        oth = [x for kk in ('路人队友', '敌方真人') for x in g[kk]]
        print(f"   t={t}: 在场真人 {len(allp)}｜" + '｜'.join(f"{kk} {len(g[kk])} 人 地中位 {med([x[0] for x in g[kk]]):.0f} 密度中位 {med([x[1] / x[0] for x in g[kk]]):.1f} 地合计 {sum(x[0] for x in g[kk])} 兵合计 {k(sum(x[1] for x in g[kk]))}" for kk in ('我方号', '路人队友', '敌方真人')))
        print(f"        其他真人（路人队友+敌方）地中位 {med([x[0] for x in oth]):.0f}、上四分位 {q(sorted(x[0] for x in oth), .75)}、密度中位 {med([x[1] / x[0] for x in oth]):.1f}；我方号地中位 ÷ 其他真人地中位 = {med([x[0] for x in g['我方号']]) / med([x[0] for x in oth]):.2f}；我方号地合计占全图 {100 * sum(x[0] for x in g['我方号']) / card['mapLand']:.2f}%、占本队真人地 {100 * sum(x[0] for x in g['我方号']) / (sum(x[0] for x in g['我方号']) + sum(x[0] for x in g['路人队友'])):.1f}%、兵占本队真人 {100 * sum(x[1] for x in g['我方号']) / (sum(x[1] for x in g['我方号']) + sum(x[1] for x in g['路人队友'])):.1f}%")
        print('        我方号名次（地，在场真人里）：' + '、'.join(f"{SQ[p]} {allp.index(terr[p]) + 1}（{terr[p]} 格/{k(bal[p])} 兵/密度 {bal[p] / terr[p]:.1f}）" for p in SQ) + f"；名次中位 {med([allp.index(terr[p]) + 1 for p in SQ]):.1f}/{len(allp)}")
    T30 = T['T30']
    for t in (600, 750, 900, 990, 1050):
        i = T30['t'].index(t)
        print(f"   T30 t={t}: 队伍地 {T30['land'][i]}（占全图 " + '/'.join(f"{100 * v / card['mapLand']:.1f}%" for v in T30['land'][i]) + f"）兵 {[k(v) for v in T30['bal'][i]]}；编队地 {T30['squadLand'][i]}（{100 * T30['squadLand'][i] / card['mapLand']:.2f}%）兵 {k(T30['squadBal'][i])}，密度 {T30['squadBal'][i] / T30['squadLand'][i]:.1f}；" + '、'.join(f"队{j} 密度 {T30['bal'][i][j] / max(1, T30['land'][i][j]):.1f}" for j in range(1, len(T30['land'][i]))))

if 'I' in sec:
    print('== I 叠点的两个号与其余 8 个号 ==')
    HS = T['HS']; pair = [BOT2P['ryan_m'], BOT2P['leo_tx']]; rest = [p for p in SQ if p not in pair]
    for i, t in enumerate(HS['t']):
        print(f"   t={t}: ryan_m {HS['terr'][i][pair[0]]}、leo_tx {HS['terr'][i][pair[1]]}（合计 {HS['terr'][i][pair[0]] + HS['terr'][i][pair[1]]}）；其余 8 个号 中位 {med([HS['terr'][i][p] for p in rest]):.0f}、最小 {min(HS['terr'][i][p] for p in rest)}、最大 {max(HS['terr'][i][p] for p in rest)}；两号合计 ÷ (2×其余中位) = {(HS['terr'][i][pair[0]] + HS['terr'][i][pair[1]]) / (2 * med([HS['terr'][i][p] for p in rest])):.2f}")
    print(f"   终局: ryan_m {P[pair[0]]['endTerr']}、leo_tx {P[pair[1]]['endTerr']}；其余 8 个号 中位 {med([P[p]['endTerr'] for p in rest]):.0f}；两号合计 ÷ (2×其余中位) = {(P[pair[0]]['endTerr'] + P[pair[1]]['endTerr']) / (2 * med([P[p]['endTerr'] for p in rest])):.2f}")
    L = json.load(open(f'{W}/{M}-land.json')); vb = {x['bot']: x['cells'] for x in L['voronoi']['perBot']}
    print(f"   出生份额（Voronoi）：ryan_m {vb['ryan_m']}、leo_tx {vb['leo_tx']}（合计 {vb['ryan_m'] + vb['leo_tx']}）；其余 8 个号 中位 {med([vb[SQ[p]] for p in rest]):.0f}；全图人均 {card['mapLand'] / L['voronoi']['humans']:.0f}（{L['voronoi']['humans']} 个进场真人）；编队合计 {L['voronoi']['squadCells']} = 全图 {100 * L['voronoi']['landShare']:.1f}%，人数占 {100 * L['voronoi']['headShare']:.1f}% → {L['voronoi']['ratio']:.2f}")
    A = json.load(open(f'{W}/{M}-attrib.json'))
    for b in [SQ[p] for p in SQ]:
        r = A['byBot'][b]; n = sum(r.values()); fl = r['留底锁·无在途'] + r['留底·有在途']
        print(f"      {b}: 决策拍 {n}，留底 {fl}（{100 * fl / n:.1f}%，其中无在途 {r['留底锁·无在途']}），有效 {r['有效']}（{100 * r['有效'] / n:.1f}%），围在里面 {r['围在里面']}，只剩中立边 {r['只剩中立边']}")
    print(f"   全队 {A['rows']} 个决策拍（窗口 {A['window']}，录像到 1071 拍）：{A['cats']}；定留底的 {A['floorSetter']}；safeFinite ≥ 一半存兵 {A['safeFiniteHalf']}")

if 'J' in sec:
    print('== J 机器人地 ==')
    L = json.load(open(f'{W}/{M}-land.json')); BL = L['botLand']
    print(f"   600 拍：我方名下格子里的机器人地 {BL['A']['tiles']} 格；贴着我方号的 {BL['B']['bots']} 个机器人共 {BL['B']['tiles']} 格；全图机器人地 {BL['C']['tiles']} 格")
    for key in ('A', 'B', 'C'):
        for f in BL['fate'][key]:
            tot = sum(v for kk, v in f.items() if kk not in ('t', 'byHuman'))
            print(f"      {key} 到 t={f['t']}: " + '、'.join(f'{kk} {v}（{100 * v / tot:.1f}%）' for kk, v in f.items() if kk not in ('t', 'byHuman') and v))
    # pairAll: [600 拍窗号, 玩家, 来源（512=中立、600=机器人、其余=真人编号）, 格数]
    grab = collections.defaultdict(collections.Counter)
    for w_, a_, src_, n_ in T['pairAll']:
        src = '中立' if src_ == 512 else ('机器人' if src_ == 600 else '真人')
        grab[('0–599' if w_ == 0 else '600–1071', src)][a_] += n_
    act = [p for p in range(H) if P[p]['peakTerr'] > 0]
    for (win, src), c in sorted(grab.items()):
        sq = [c[p] for p in SQ]; ot = sorted(c[p] for p in act if p not in SQ)
        mates = [c[p] for p in act if p not in SQ and P[p]['team'] == T['ourTeam']]; foes = [c[p] for p in act if p not in SQ and P[p]['team'] != T['ourTeam']]
        tot = sum(c[p] for p in act)
        print(f"   {win} 从{src}拿到的地：进场真人 {len(act)} 人合计 {tot:.0f} 格；我方号 {sum(sq):.0f}（{100 * sum(sq) / max(1, tot):.1f}%，每号中位 {med(sq):.0f}）；路人队友 {len(mates)} 人 {sum(mates):.0f}（每人中位 {med(mates):.0f}）；敌方真人 {len(foes)} 人 {sum(foes):.0f}（每人中位 {med(foes):.0f}）；其余进场真人每人中位 {med(ot):.0f}、上四分位 {q(ot, .75):.0f}；我方号人数占 {100 * 10 / len(act):.1f}%")
        if src == '机器人': print('        各号：' + ' '.join(f'{SQ[p]}:{c[p]:.0f}' for p in SQ) + f"；我方号每号中位 ÷ 其余每人中位 = {med(sq) / max(1, med(ot)):.2f}")

if 'K' in sec:
    print('== K 停拍前的命令流 ==')
    rd = collections.Counter(); rs = collections.Counter()
    for r in cmds:
        t = int(r['tick'])
        if t >= 896 and r['kind'] in ('attack', 'boat', 'donate'):
            rd[t] += 1
            if int(r['player']) in SQ: rs[t] += 1
    allr = [rd[t] for t in range(896, 1065, 7)]
    print(f'   896–1064 拍每个回合（7 拍）全场落地的 陆攻/出船/捐兵 指令数：' + ' '.join(f'{t}:{rd[t]}' for t in range(896, 1072, 7)))
    print(f'   回合指令数：中位 {med(allr):.0f}、最小 {min(allr)}、最大 {max(allr)}；最后 5 个回合 {[rd[t] for t in range(1036, 1065, 7)]}；1071 拍 {rd[1071]} 条')
    off = collections.Counter(int(r['tick']) % 7 for r in cmds if int(r['tick']) > 0)
    print(f'   全场指令落地拍 mod 7 的分布：{dict(sorted(off.items()))}')
    early = collections.Counter(); late = collections.Counter()
    for r in cmds:
        t = int(r['tick'])
        if r['kind'] not in ('attack', 'boat'): continue
        if 600 <= t < 900: early['我方' if int(r['player']) in SQ else '其他'] += 1
        if 900 <= t <= 1071: late['我方' if int(r['player']) in SQ else '其他'] += 1
    print(f"   600–899 拍 陆攻/出船：我方 {early['我方']} 条、其他真人 {early['其他']} 条（每拍 {early['其他'] / 300:.2f}）；900–1071：我方 {late['我方']}、其他 {late['其他']}（每拍 {late['其他'] / 172:.2f}）")
    D = json.load(open(f'{W}/{M}-delay.json'))
    tail = [d for d in D['decisions'] if d[1] >= 920]
    print(f'   影子在 920 拍之后的决策 {len(tail)} 条：落地 {sum(1 for d in tail if d[5] is not None)}、没落地 {sum(1 for d in tail if d[5] is None)}')
    for d in tail:
        print(f'      {d[0]} 决策 {d[1]} 拍 {d[2]}/{d[3]} → ' + (f'落地 {d[5]} 拍（延迟 {d[6]}）' if d[5] is not None else '没落地') + f'，名义兵 {d[7]}')
    nl = [d for d in tail if d[5] is None]
    print(f"   没落地的 {len(nl)} 条：决策拍 ≥1057 的 {sum(1 for d in nl if d[1] >= 1057)} 条（基线延迟 {D['baseline']} 拍，来不及在 1071 拍前落地），<1057 的 {sum(1 for d in nl if d[1] < 1057)} 条（" + '、'.join(f'{d[0]} {d[1]}' for d in nl if d[1] < 1057) + '）')
    for b300 in D['delayBy300']: print(f"   落地延迟 t={b300['t']}–{b300['t'] + 299}: {b300['n']} 条，中位 {b300['p50']}、最大 {b300['max']}")
    print(f"   同拍批：" + '；'.join(f"{b['bot']} {b['T']} 拍 ×{b['n']}（决策比落地早 {b['staleMin']}–{b['staleMax']} 拍，打掉批前存兵 {100 * b['drain']:.0f}%）" for b in D['batchList']))
    tl = T['tickLines']
    print(f'   录像重放与日志 [HL-TICK] 行对上的数：tickLines = {tl}')

if 'K' in sec:
    # 延迟有没有在停拍前爬坡：按落地拍每 60 拍一窗（延迟 = 落地拍 − 影子决策拍；基线 12 拍）
    DD = json.load(open(f'{W}/{M}-delay.json'))['decisions']
    win = collections.defaultdict(list)
    for r in DD:
        if r[5] is not None and r[6] is not None and r[5] >= 600: win[(r[5] - 600) // 60].append((r[6], r[0], r[1], r[5]))
    print('   落地延迟按落地拍每 60 拍一窗（条数 / 中位 / 最大 / 延迟 ≥24 拍的条数）：' + '；'.join(
        f"{600 + 60 * k}–{600 + 60 * k + 59}: {len(v)} / {med([x[0] for x in v]):.0f} / {max(x[0] for x in v)} / {sum(1 for x in v if x[0] >= 24)}" for k, v in sorted(win.items())))
    late = sorted((x for v in win.values() for x in v if x[0] >= 30), key=lambda x: x[3])
    print('   延迟 ≥30 拍的落地指令：' + '；'.join(f'{b} 决策 {d} → 落地 {l}（{dl}）' for dl, b, d, l in late))
    byb = collections.defaultdict(list)
    for r in DD:
        if r[5] is not None and r[6] is not None and r[5] >= 880: byb[r[0]].append(r[6])
    print('   880 拍以后各号落地延迟（条数 / 中位 / 最大）：' + '；'.join(f'{b} {len(v)} / {med(v):.0f} / {max(v)}' for b, v in sorted(byb.items())))
if 'K' in sec:
    # 同拍批（同一玩家同一拍 ≥3 条陆攻/出船）：我方号 对 其他真人（IO-HOST-WAVE 的口径）
    cnt = collections.Counter()
    for ln in open(f'{W}/{M}-cmds.tsv', encoding='utf-8'):
        c = ln.rstrip('\n').split('\t')
        if c[0] == 'tick' or c[2] not in ('attack', 'boat'): continue
        cnt[(int(c[0]), int(c[3]))] += 1
    sqp_ = {x['p'] for x in T['squad']}
    b_sq = sorted((t, p, n) for (t, p), n in cnt.items() if n >= 3 and p in sqp_)
    b_ot = sorted((t, p, n) for (t, p), n in cnt.items() if n >= 3 and p not in sqp_)
    two_sq = sum(1 for (t, p), n in cnt.items() if n == 2 and p in sqp_); two_ot = sum(1 for (t, p), n in cnt.items() if n == 2 and p not in sqp_)
    nm_ = {q['id']: q['name'] for q in T['players']}
    print(f"   同拍批（同一玩家同一拍 ≥3 条陆攻/出船）：我方号 {len(b_sq)} 批 {sum(n for _, _, n in b_sq)} 条（" + '、'.join(f'{nm_[p].replace("[APEX] ", "")}@{t}×{n}' for t, p, n in b_sq) + f"）；其他真人 {len(b_ot)} 批 {sum(n for _, _, n in b_ot)} 条（" + '、'.join(f'{nm_[p]}#{p}@{t}×{n}' for t, p, n in b_ot[:12]) + f"）；同拍 2 条的：我方号 {two_sq} 次、其他真人 {two_ot} 次")
    tot_sq = sum(n for (t, p), n in cnt.items() if p in sqp_); tot_ot = sum(n for (t, p), n in cnt.items() if p not in sqp_)
    print(f"   全程陆攻/出船指令：我方号 {tot_sq} 条、其他真人 {tot_ot} 条；≥3 条同拍批里的指令占比 我方 {100 * sum(n for _, _, n in b_sq) / max(1, tot_sq):.1f}%、其他 {100 * sum(n for _, _, n in b_ot) / max(1, tot_ot):.1f}%")
if 'L' in sec:
    print('== L 零散数字 ==')
    HS = T['HS']; i6 = HS['t'].index(600); i9 = HS['t'].index(900)
    print('   各号 600→900→终局 的地：' + '；'.join(f"{SQ[p]} {HS['terr'][i6][p]}→{HS['terr'][i9][p]}→{P[p]['endTerr']}（600→900 {HS['terr'][i9][p] - HS['terr'][i6][p]:+d}）" for p in SQ))
    print(f"   编队 600→900 地 {sum(HS['terr'][i6][p] for p in SQ)}→{sum(HS['terr'][i9][p] for p in SQ)}（{sum(HS['terr'][i9][p] - HS['terr'][i6][p] for p in SQ):+d}），兵 {k(sum(HS['bal'][i6][p] for p in SQ))}→{k(sum(HS['bal'][i9][p] for p in SQ))}；终局地 {sum(P[p]['endTerr'] for p in SQ)}、兵 {k(sum(P[p]['endBal'] for p in SQ))}，密度 {sum(P[p]['endBal'] for p in SQ) / sum(P[p]['endTerr'] for p in SQ):.1f}")
    for t_i, t in ((i6, 600), (i9, 900)):
        oth = [(HS['terr'][t_i][p], HS['bal'][t_i][p]) for p in range(H) if p not in SQ and HS['terr'][t_i][p] > 0]
        print(f"   t={t} 其他真人 {len(oth)} 人：地合计 {sum(x[0] for x in oth)}、兵合计 {k(sum(x[1] for x in oth))}、整体密度 {sum(x[1] for x in oth) / sum(x[0] for x in oth):.1f}；我方号整体密度 {sum(HS['bal'][t_i][p] for p in SQ) / sum(HS['terr'][t_i][p] for p in SQ):.1f}")
    oth = [(P[p]['endTerr'], P[p]['endBal']) for p in range(H) if p not in SQ and P[p]['endTerr'] > 0 and P[p]['state'] == 0]
    print(f"   终局在线的其他真人 {len(oth)} 人：地中位 {med([x[0] for x in oth]):.0f}、密度中位 {med([x[1] / x[0] for x in oth]):.1f}、整体密度 {sum(x[1] for x in oth) / sum(x[0] for x in oth):.1f}")
    gone = [(p, P[p]) for p in range(H) if p not in SQ and (P[p]['leftT'] != -1 or P[p]['deathT'] != -1)]
    print('   中途离场/阵亡的其他真人：' + '；'.join(f"{x['name']}#{p}（T{x['team']}）离场 {x['leftT']} 阵亡 {x['deathT']} 终地 {x['endTerr']}" for p, x in gone))
    hum = [(r['a'], r['b'], r['tiles'], r['sent']) for r in T['pairs'] if r['a'] < H and r['b'] < H and (r['a'] in SQ) != (r['b'] in SQ) and (r['a'] in SQ or r['b'] in SQ)]
    print('   我方号与其他真人之间的陆攻（pairs）：' + ('；'.join(f'{nm(a)}→{nm(b)} 投 {s_:.0f} 拿 {tl_:.0f} 格' for a, b, tl_, s_ in hum) or '无'))
    ev = collections.Counter((e['type'], '中立' if e['q'] == 512 else ('机器人' if e['q'] >= H else '真人')) for e in T['events'])
    print(f'   我方号已执行指令（events）：{dict(ev)}')
    c30 = T['C30']
    MATE_SHARE = []
    for p in SQ:
        c = c30[str(p)]; i = c['t'].index(900); j = c['t'].index(1050)
        print(f"      {SQ[p]} 边界 t=900：中立 {c['neut'][i]} 机器人 {c['bot'][i]} 敌真人 {c['eh'][i]} 我方号 {c['mateS'][i]} 路人队友 {c['mateO'][i]}｜t=1050：中立 {c['neut'][j]} 机器人 {c['bot'][j]} 敌真人 {c['eh'][j]} 我方号 {c['mateS'][j]} 路人队友 {c['mateO'][j]}")
        tot_ = c['neut'][j] + c['bot'][j] + c['eh'][j] + c.get('el', [0] * (j + 1))[j] + c['mateS'][j] + c['mateO'][j]
        MATE_SHARE.append((SQ[p], 100 * (c['mateS'][j] + c['mateO'][j]) / max(1, tot_), 100 * c['mateS'][j] / max(1, tot_)))
    MATE_SHARE.sort(key=lambda x: -x[1])
    print('   t=1050 边界外侧属于队友（我方号 + 路人队友）的格子占比（括号内只算我方号）：' + '、'.join(f'{b} {a:.0f}%（{m_:.0f}%）' for b, a, m_ in MATE_SHARE) + f"；≥70% 的号 {sum(1 for x in MATE_SHARE if x[1] >= 70)} 个")

if 'M' in sec:
    print('== M 留底探针（shadow.mjs --cold --floor 的逐样本行）==')
    rx = re.compile(r'^\[留底\] t=(\d+) (\S+) 兵 (\d+) 地 (\d+)｜相邻机器人 (\d+) 个（共 (\d+) 格，其中几乎没兵的 (\d+) 个）｜safeFinite=(\d+)（([^）]*)）(.*?)｜此刻过得了留底的机器人目标 (\d+) 个')
    rw = re.compile(r'由 机器人#(\d+)（地 (\d+) 兵 (\d+)）决定：它的其它邻居里最弱的是 (.+?) 兵 (\d+)$')
    rows = []
    for ln in open(f'{W}/{M}-floor.txt', encoding='utf-8', errors='replace'):
        m_ = rx.match(ln.strip())
        if not m_: continue
        t, b, B, L_, nb, cells, empty, sf, _, rest, ok = m_.groups()
        w_ = rw.search(rest)
        who = w_.group(4) if w_ else None
        kind = None
        if who:
            kind = '我方号' if '(我方号)' in who else ('机器人' if who.startswith('机器人#') else '其他真人')
            who = who.replace('(我方号)', '').replace('[APEX] ', '')
        rows.append(dict(t=int(t), bot=b, B=int(B), L=int(L_), nb=int(nb), cells=int(cells), empty=int(empty), sf=int(sf), ok=int(ok), via=int(w_.group(1)) if w_ else None,
                         viaL=int(w_.group(2)) if w_ else None, viaB=int(w_.group(3)) if w_ else None, who=who, kind=kind))
    ts_ = sorted({r['t'] for r in rows})
    print(f'   样本 {len(rows)} 个（{len(ts_)} 个采样拍 {ts_[0]}–{ts_[-1]} × 10 个号）')
    for lo, hi in ((600, 900), (900, 1100)):
        rr = [r for r in rows if lo <= r['t'] < hi]; nbr = [r for r in rr if r['nb'] > 0]
        lock = [r for r in nbr if r['ok'] == 0]; emp = [r for r in nbr if r['empty'] > 0]; emplock = [r for r in emp if r['ok'] == 0]
        kinds = collections.Counter(r['kind'] for r in lock)
        print(f"   {lo}–{hi}: 样本 {len(rr)}，贴着机器人的 {len(nbr)}（贴着的机器人地 中位 {med([r['cells'] for r in nbr]):.0f} 格）；没有一个机器人目标过得了留底的 {len(lock)}（{100 * len(lock) / max(1, len(nbr)):.0f}%）；safeFinite ≥ 一半存兵 {sum(1 for r in nbr if r['sf'] * 2 >= r['B'])}、≥ 全部存兵 {sum(1 for r in nbr if r['sf'] >= r['B'])}；锁死样本里定留底的：{dict(kinds)}")
        print(f"        贴着至少 1 个几乎没兵的机器人的样本 {len(emp)}，其中没有目标过得了留底的 {len(emplock)}（{100 * len(emplock) / max(1, len(emp)):.0f}%）；这些样本的存兵中位 {med([r['B'] for r in emplock]):.0f}、safeFinite ÷ 存兵 中位 {med([r['sf'] / r['B'] for r in emplock]):.2f}")
    via = collections.defaultdict(list)
    for r in rows:
        if r['via'] is not None and r['ok'] == 0: via[r['via']].append(r)
    print('   充当锁的机器人（锁死样本里经它定留底，≥3 个样本的）：')
    for v, rr in sorted(via.items(), key=lambda kv: -len(kv[1])):
        if len(rr) < 3: continue
        print(f"      机器人#{v}: {len(rr)} 个样本，拍 {min(r['t'] for r in rr)}–{max(r['t'] for r in rr)}，它的地 {min(r['viaL'] for r in rr)}–{max(r['viaL'] for r in rr)}、兵 {min(r['viaB'] for r in rr)}–{max(r['viaB'] for r in rr)}；被锁的号 {dict(collections.Counter(r['bot'] for r in rr))}；拿来比的邻居 {dict(collections.Counter(r['who'] for r in rr))}")
    pairs = collections.Counter()
    for r in rows:
        if r['ok'] == 0 and r['kind'] == '我方号': pairs[tuple(sorted((r['bot'], r['who'].split('#')[0])))] += 1
    print('   互锁的号对（锁死样本里 号 ↔ 定它留底的我方号，不分方向）：' + '；'.join(f'{a}↔{b} {n}' for (a, b), n in pairs.most_common()))
    for r in rows:
        if (r['bot'], r['t']) in (('zero_7', 905), ('noah88', 1005), ('leo_tx', 1005), ('leo_tx', 1055), ('alex_k', 905), ('sora_w', 1005), ('riku_x', 905), ('ryan_m', 905)):
            print(f"      例 t={r['t']} {r['bot']}: 兵 {r['B']} 地 {r['L']}，贴着 {r['nb']} 个机器人共 {r['cells']} 格（几乎没兵的 {r['empty']} 个），safeFinite {r['sf']}（{100 * r['sf'] / r['B']:.0f}% 存兵）" + (f"，经机器人#{r['via']}（地 {r['viaL']} 兵 {r['viaB']}）取 {r['who']} 的存兵" if r['via'] is not None else '') + f"，过得了留底的机器人目标 {r['ok']} 个")

if 'N' in sec:
    print('== N 兵账对照（truth.players 全程合计；flows 按 cats 顺序）==')
    cats = T['cats']
    print('   cats = ' + ' '.join(cats))
    grp = collections.defaultdict(list)
    for q in T['players']:
        if q['id'] >= T['humans'] or not q.get('spawn') or q['spawn'][0] < 0: continue
        if q['peakTerr'] <= 0: continue
        g = '我方号' if q.get('squad') else ('路人队友' if q['team'] == T['ourTeam'] else '敌方真人')
        grp[g].append(q)
    def line(g, L_):
        f = [dict(zip(cats, q['flows'])) for q in L_]
        eco = sum(x['eco'] for x in f); n = len(L_)
        sN, sB, sH = (sum(q[k] for q in L_) for k in ('sentN', 'sentB', 'sentH'))
        tN, tB, tH = (sum(q[k] for q in L_) for k in ('tilesN', 'tilesB', 'tilesH'))
        out = -sum(v for x in f for k, v in x.items() if k not in ('eco', 'ret', 'dmg', 'donIn') and v < 0)
        ret = sum(x.get('ret', 0) for x in f); dmg = -sum(x.get('dmg', 0) for x in f)
        endB = sum(q['endBal'] for q in L_ if q['alive']); endT = sum(q['endTerr'] for q in L_ if q['alive'])
        lost = [q['tilesLost'] for q in L_]
        per = sorted((q['sentB'] / q['tilesB']) for q in L_ if q['tilesB'] >= 200)
        print(f"   {g}（{n} 人）：利息地租 {eco}（每人中位 {med([x['eco'] for x in f]):.0f}）｜从存兵里扣走（打中立/机器人/真人/船/捐，含手续费）{out} = 利息地租的 {100 * out / eco:.0f}%，退回 {ret}（{100 * ret / max(1, out):.0f}%）｜被打掉 {dmg}（每人中位 {med([-x.get('dmg', 0) for x in f]):.0f}）")
        print(f"        投兵 中立 {sN} / 机器人 {sB} / 真人 {sH}；拿地 中立 {tN} / 机器人 {tB} / 真人 {tH}；每格 中立 {sN / max(1, tN):.1f} / 机器人 {sB / max(1, tB):.1f} 兵（拿到 ≥200 格机器人地的 {len(per)} 人逐个：中位 {med(per) if per else 0:.1f}，四分位 {per[len(per) // 4] if per else 0:.1f}–{per[(3 * len(per)) // 4] if per else 0:.1f}）")
        print(f"        被拿走的地 合计 {sum(lost)}（每人中位 {med(lost):.0f}，>0 的 {sum(1 for v in lost if v > 0)} 人）｜终局在场 {sum(1 for q in L_ if q['alive'])} 人，存兵 {endB} = 全组利息地租的 {100 * endB / eco:.0f}%，地 {endT}，密度 {endB / max(1, endT):.1f}")
    for g in ('我方号', '路人队友', '敌方真人'): line(g, grp[g])
    line('其他真人合计', grp['路人队友'] + grp['敌方真人'])
    print('   我方号逐个（投向机器人的兵 / 拿到的机器人地 / 每格兵｜利息地租｜终兵 ÷ 利息地租）：')
    for q in grp['我方号']:
        f = dict(zip(cats, q['flows']))
        print(f"      {q['name'].replace('[APEX] ', '')}: {q['sentB']} / {q['tilesB']} / {q['sentB'] / max(1, q['tilesB']):.1f}｜{f['eco']}｜{100 * q['endBal'] / f['eco']:.0f}%")
    sqp = {q['id'] for q in grp['我方号']}
    byH_sq = sum(r[3] for r in T['pairAll'] if r[2] in sqp)
    byH_ot = sum(r[3] for r in T['pairAll'] if r[2] < T['humans'] and r[2] not in sqp)
    lost_sq = sum(q['tilesLost'] for q in grp['我方号']); oth = grp['路人队友'] + grp['敌方真人']; lost_ot = sum(q['tilesLost'] for q in oth)
    print(f"   被机器人拿走的地（= 被拿走的地 − 被真人拿走的地，pairAll）：我方号 {lost_sq} − {byH_sq} = {lost_sq - byH_sq}（每号平均 {(lost_sq - byH_sq) / len(sqp):.0f}）；其他真人 {lost_ot} − {byH_ot} = {lost_ot - byH_ot}（每人平均 {(lost_ot - byH_ot) / len(oth):.0f}）；比值 {((lost_sq - byH_sq) / len(sqp)) / max(1e-9, (lost_ot - byH_ot) / len(oth)):.2f}")
    nb = [r for r in T['pairs'] if r['a'] >= T['humans'] and r['b'] in sqp]
    print(f"   机器人打我方号（pairs）：{len(nb)} 对，{sum(r['n'] for r in nb)} 笔，投兵 {sum(r['sent'] for r in nb)}，拿地 {sum(r['tiles'] for r in nb)}，打掉存兵 {sum(r['balDmg'] for r in nb)}；逐号被拿走：" + '、'.join(f"{q['name'].replace('[APEX] ', '')} {q['tilesLost']}" for q in grp['我方号']))
