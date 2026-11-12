#!/usr/bin/env python3
# A041_facts.py — A041 复盘里引用、而通用脚本（truth_digest.py / match_facts.py / match_extra.py / game_facts.py / 三本账）不直接给的数字。
#   只读 /tmp/c136-r05/truth/A041.json（match_truth.mjs 的逐拍重放产物）、/tmp/c136-r05/work/A041-cmds.tsv（replay_cmds.mjs 导出的指令表）、
#   发现集 bundles/A041/in_game.log。先跑：bash scripts/accounts_batch.sh A041。
#   §1 选点期：后端协调器每一轮求解的点集（[BACKEND-SPAWN-COORD]）——轮数、不同的点集、每个点集的角尖、外圈点里贴着地图边线的个数、
#        扇形朝向（角尖 → 外圈点质心 的方位角；屏幕坐标，0°＝正右、90°＝正下）、最小间距。
#   §2 选点期：录像里我方出生指令逐拍；同一个号同一拍 ≥2 条的组——块内先后 与 日志里指派先后 的对照；逐号「最后指派 vs 实际落点」。
#   §3 选点期：其他真人的每条出生指令到我方最终落点的最近距离（≤120 格的列出）；最终落在「编队质心 + 最远号半径」里的其他真人。
#   §4 我方十个最终落点：到最近队友、到地图右下角、是否在边线上；外圈/内圈/角尖。
#   §5 每 300 拍：我方号地中位、其余真人地中位、我方号名次；编队/路人队友/敌队的地与兵（HS）。
#   §6 1500–3213：编队兵 ÷ 敌队兵、被围号握兵、落地的陆攻条数、已执行捐兵、少拿的利息（按 300 拍；T30/C30/F30/events）。
#   §7 kaito9 与 dsc.gg/cold1 的对峙（1500–2400，每 100 拍取 S10/HS 最近的采样点）。
#   §8 其他真人逐个：出生点、到最近真人出生点的距离、每 600 拍的地/兵、地的来源（中立/机器人/真人）、对真人出兵、收/捐；
#        各组（我方号/路人队友/敌方）「到最近真人出生点的距离」中位。
#   §9 非我方真人之间的捐兵（allDon）：逐笔 ≥200k 的、按队汇总；敌方银行号（从不打真人、只攒兵、后期整笔捐出）的账。
#   §10 我方号的地的来源（中立/机器人/真人）与 600 拍窗口里编队对真人的易手（pairAll 口径同 game_facts.py）。
#   §11 捐兵配额表（引擎 game.js donationCost L348-357、donationCapTick L379-383、donCap 初值 L124）：各拍的上限点数、每点折多少兵、
#        一个受赠方从开局到该拍「最多一共能收」多少兵；与同拍没有敌邻的号握着的兵、有敌邻的号数对照。
#   §12 3900–4274 拍三个最有兵的不被围的号（kaito9、ryan_m、noah88）对正被真人打的队友：探针里逐（捐出方×候选×采样拍）的拦截行
#        （读 /tmp/c136-r05/work/A041-donprobe.txt = shadow.mjs A041 --cold --quiet --t0 3595 --t1 4830 --don-probe 3600,3625,…,4825 的输出）。
#   §13 路人队友的易手（pairAll）：每个路人队友从谁手里拿地、丢给谁，按 600 拍窗口；以及它们每 300 拍的地/兵/密度与同拍被围的我方号握着的兵。
# 用法：python3 scripts/review_build/A041_facts.py [--sec 1,2,3,4,5,6,7,8,9,10,11,12,13]
import bisect
import csv
import json
import math
import re
import statistics as st
import sys
from collections import defaultdict

M = 'A041'
sec = set((sys.argv[sys.argv.index('--sec') + 1] if '--sec' in sys.argv else '1,2,3,4,5,6,7,8,9,10,11,12,13').split(','))
J = json.load(open(f'/tmp/c136-r05/truth/{M}.json'))
P = {p['id']: p for p in J['players']}
sq = {s['p']: s['bot'] for s in J['squad']}
pid = {b: p for p, b in sq.items()}
H = J['humans']
OUR = J['ourTeam']
HS = J['HS']
CATS = J['cats']
MW, MH = J['map'].get('W', 884), J['map'].get('H', 960)
LOG = f'/agent/repos/c136-data/bundles/{M}/in_game.log'
TSV = f'/tmp/c136-r05/work/{M}-cmds.tsv'


def k(x):
    return f'{x/1e6:.2f}M' if abs(x) >= 1e6 else f'{x/1000:.0f}k' if abs(x) >= 1000 else str(int(x))


def nm(p):
    if p in sq:
        return sq[p]
    if p in P:
        return P[p]['name'][:16] + f"(#{p},T{P[p]['team']})"
    return f'#{p}'


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---------- 日志里的求解轮与逐号指派 ----------
solves = []     # (seq, minSep, {bot: (x,y)})
assigns = []    # (seq, bot, role, (x,y))
for ln in open(LOG, encoding='utf8', errors='replace'):
    m = re.match(r'(\d+)\t\[BACKEND-SPAWN-COORD\] Solved (\d+) bots in ([\d.]+)ms \(map=(\d+)x(\d+), minSep=(\d+)px, boss=(\w+)\): (.*)', ln)
    if m:
        pts = {}
        for seg in m.group(8).split(' | '):
            mm = re.match(r'(?:\[\w+\] )?(\w+)\(\w+\)->\((\d+),(\d+)\)', seg.strip())
            if mm:
                pts[mm.group(1)] = (int(mm.group(2)), int(mm.group(3)))
        solves.append((int(m.group(1)), int(m.group(6)), pts, float(m.group(3))))
        continue
    m = re.match(r'(\d+)\t\[(\w+)\] \[HL-SPAWN-BACKEND\] me=\d+ slot=\d+ role=(\w+) -> \((\d+),(\d+)\)', ln)
    if m:
        assigns.append((int(m.group(1)), m.group(2), m.group(3), (int(m.group(4)), int(m.group(5)))))

rows = list(csv.DictReader(open(TSV, encoding='utf8'), delimiter='\t'))
spawn = []      # (块内全局行号, tick, player, (x,y))
for i, r in enumerate(rows):
    if r['kind'] == 'spawn':
        a = int(r['a'])
        spawn.append((i, int(r['tick']), int(r['player']), (a % MW, a // MW)))
final = {}
for i, t, p, xy in spawn:
    final[p] = (t, xy)          # 块内顺序最后一条 = 引擎最后执行的那条
ourFinal = {sq[p]: final[p][1] for p in sq if p in final}


def role_of(bot, xy):
    for s, b, r, q in assigns:
        if b == bot and q == xy:
            return r
    return '?'


if '1' in sec:
    print('§1 后端协调器的求解轮（[BACKEND-SPAWN-COORD]）')
    sets = []
    for s, ms, pts, dur in solves:
        key = tuple(sorted(pts.items()))
        for e in sets:
            if e['key'] == key:
                e['n'] += 1
                e['seqs'].append(s)
                break
        else:
            sets.append({'key': key, 'n': 1, 'seqs': [s], 'pts': pts, 'minSep': ms, 'dur': dur})
    print(f'   求解 {len(solves)} 轮，不同的点集 {len(sets)} 个；每轮耗时 中位 {st.median([x[3] for x in solves]):.1f} 毫秒、最大 {max(x[3] for x in solves):.1f}')
    prev = None
    for n, e in enumerate(sets, 1):
        pts = e['pts']
        roles = {b: role_of(b, xy) for b, xy in pts.items()}
        apex = [b for b, r in roles.items() if r == 'CORNER_APEX_BANK']
        outer = [b for b, r in roles.items() if r == 'OUTER_SHIELD_WALL']
        other = [b for b, r in roles.items() if r not in ('CORNER_APEX_BANK', 'OUTER_SHIELD_WALL', 'INNER_ARC_BANK')]
        onEdge = [b for b in outer if pts[b][0] in (18, MW - 19) or pts[b][1] in (18, MH - 19)]
        xs = [v[0] for v in pts.values()]
        ys = [v[1] for v in pts.values()]
        c = (st.mean(xs), st.mean(ys))
        mind = min(dist(pts[a], pts[b]) for a in pts for b in pts if a < b)
        axis = '-'
        if apex and outer:
            ox = st.mean(pts[b][0] for b in outer)
            oy = st.mean(pts[b][1] for b in outer)
            ax, ay = pts[apex[0]]
            axis = f'{math.degrees(math.atan2(oy - ay, ox - ax)):.0f}°'
        moved = ''
        if prev:
            mv = [dist(prev[b], pts[b]) for b in pts if b in prev]
            moved = f'｜比上一个点集：逐号位移 中位 {st.median(mv):.0f}、最大 {max(mv):.0f}、换了位置（>30 格）的号 {sum(1 for x in mv if x > 30)} 个'
        prev = pts
        print(f'   点集 {n}（日志序号 {e["seqs"][0]}，重复 {e["n"]} 轮，minSep={e["minSep"]}）：角尖 {apex[0] if apex else "-"}{pts[apex[0]] if apex else ""}｜外圈 {len(outer)} 个，其中贴着地图边线（x={MW-19} 或 y={MH-19}）的 {len(onEdge)} 个'
              f'｜角尖→外圈质心 朝向 {axis}｜质心 ({c[0]:.0f},{c[1]:.0f})｜最小间距 {mind:.0f}{moved}'
              + (f'｜不在扇形里的点：{", ".join(b + str(pts[b]) + "〔" + roles[b] + "〕" for b in other)}' if other else ''))
        print('      ' + '；'.join(f'{b}{pts[b]}〔{roles[b][:5]}〕' for b in sorted(pts, key=lambda b: pts[b])))

if '2' in sec:
    print('§2 录像里我方的出生指令（拍；块内顺序）与日志指派的对照')
    byT = defaultdict(list)
    for i, t, p, xy in spawn:
        if p in sq:
            byT[t].append((i, sq[p], xy))
    for t in sorted(byT):
        print(f'   t={t}: ' + '；'.join(f'#{i} {b}{xy}' for i, b, xy in byT[t]))
    others = [(t, p) for i, t, p, xy in spawn if p not in sq]
    print(f'   我方出生指令 {sum(len(v) for v in byT.values())} 条（拍 {min(byT)}…{max(byT)}）；其他真人 {len(others)} 条，来自 {len(set(p for t, p in others))} 人')
    print('   同一个号同一拍 ≥2 条的组：')
    grp = defaultdict(list)
    for i, t, p, xy in spawn:
        if p in sq:
            grp[(t, sq[p])].append((i, xy))
    nrev = ntot = nstale = 0
    for (t, b), lst in sorted(grp.items()):
        if len(lst) < 2:
            continue
        ntot += 1
        seqs = []
        for i, xy in lst:
            ss = [s for s, bb, r, q in assigns if bb == b and q == xy]
            seqs.append(ss[-1] if ss else -1)
        rev = all(seqs[j] > seqs[j + 1] for j in range(len(seqs) - 1))
        nrev += rev
        lastAssigned = [q for s, bb, r, q in assigns if bb == b][-1]
        stale = final[pid[b]][1] == lst[-1][1] and lst[-1][1] != lastAssigned
        nstale += stale
        print(f'      t={t} {b}: 块内顺序 ' + ' → '.join(f'{xy}〔日志序号 {s}〕' for (i, xy), s in zip(lst, seqs))
              + f'｜块内先后与日志先后{"相反" if rev else "相同"}｜生效的是 {lst[-1][1]}（块内最后一条＝日志里较早的那次指派）'
              + ('；此后没有再收到指令，最终落点就是它' if stale else f'；之后又有指令，最终落点 {final[pid[b]][1]}'))
    print(f'   合计 {ntot} 组，块内先后与日志先后相反的 {nrev} 组；因此停在旧点上的号 {nstale} 个')
    print('   逐号：日志指派次数 / 录像指令条数 / 最后一次指派 / 实际落点 / 相差')
    for b in sorted(pid, key=lambda b: pid[b]):
        la = [(s, r, q) for s, bb, r, q in assigns if bb == b]
        nc = sum(1 for i, t, p, xy in spawn if p == pid[b])
        f = final[pid[b]]
        d = dist(la[-1][2], f[1])
        print(f'      {b}: 指派 {len(la)} 次 / 指令 {nc} 条 / 最后指派 {la[-1][2]}〔{la[-1][1]}〕 / 落点 {f[1]}（t={f[0]}）/ 差 {d:.0f} 格{"  ← 不一致" if d > 5 else ""}')

if '3' in sec:
    print('§3 其他真人的出生指令到我方最终落点的最近距离')
    cx = st.mean(v[0] for v in ourFinal.values())
    cy = st.mean(v[1] for v in ourFinal.values())
    rmax = max(dist((cx, cy), v) for v in ourFinal.values())
    print(f'   编队质心 ({cx:.0f},{cy:.0f})，最远号离质心 {rmax:.0f} 格')
    firstOur = min(t for i, t, p, xy in spawn if p in sq)
    print(f'   我方第一条出生指令在 t={firstOur}；在它之前已经落点的其他真人：')
    for i, t, p, xy in spawn:
        if p in sq or t >= firstOur:
            continue
        b, d = min(((bb, dist(xy, q)) for bb, q in ourFinal.items()), key=lambda z: z[1])
        dc = dist(xy, (cx, cy))
        print(f'      t={t} {nm(p)} {xy}：离编队质心 {dc:.0f}{"（在最远号半径内）" if dc <= rmax else ""}，离最近的我方最终落点 {b} {d:.0f}')
    print('   选点期全程，落在我方任一最终落点 120 格以内的其他真人指令：')
    for i, t, p, xy in spawn:
        if p in sq:
            continue
        b, d = min(((bb, dist(xy, q)) for bb, q in ourFinal.items()), key=lambda z: z[1])
        if d <= 120:
            print(f'      t={t} {nm(p)} {xy}：离 {b} {d:.0f} 格{"  ← 这是它的最终落点" if final[p][1] == xy and final[p][0] == t else ""}')
    print('   最终落在「质心 + 最远号半径」里的其他真人（含没有出生指令、由引擎安排的；出生点取 truth.players[].spawn）：')
    for p in sorted(P):
        if p in sq or p >= H:
            continue
        s = P[p].get('spawn')
        if not s or s[0] < 0:
            continue
        dc = dist(s, (cx, cy))
        if dc <= rmax:
            b, d = min(((bb, dist(s, q)) for bb, q in ourFinal.items()), key=lambda z: z[1])
            hasCmd = p in final
            print(f'      {nm(p)} 出生 {tuple(s)}：离质心 {dc:.0f}，离最近的我方号 {b} {d:.0f} 格；{"最后一条出生指令 t=" + str(final[p][0]) if hasCmd else "没有出生指令"}')

if '4' in sec:
    print('§4 我方十个最终落点')
    corner = (MW - 1, MH - 1)
    for b in sorted(ourFinal, key=lambda b: ourFinal[b]):
        xy = ourFinal[b]
        mate, d = min(((bb, dist(xy, q)) for bb, q in ourFinal.items() if bb != b), key=lambda z: z[1])
        la = [(s, r, q) for s, bb, r, q in assigns if bb == b]
        edge = '下边线' if xy[1] == MH - 19 else '右边线' if xy[0] == MW - 19 else ''
        print(f'   {b} {xy}〔最后指派的角色 {la[-1][1]}〕：最近队友 {mate} {d:.0f} 格；到右下角 {dist(xy, corner):.0f} 格；到下边 {MH - 1 - xy[1]}、到右边 {MW - 1 - xy[0]}{"；在" + edge + "上" if edge else ""}')
    ds = sorted(min(dist(xy, q) for bb, q in ourFinal.items() if bb != b) for b, xy in ourFinal.items())
    xs = [v[0] for v in ourFinal.values()]
    ys = [v[1] for v in ourFinal.values()]
    print(f'   最近队友距离：最小 {ds[0]:.0f}、中位 {st.median(ds):.0f}、最大 {ds[-1]:.0f}｜外接框 x {min(xs)}–{max(xs)}（宽 {max(xs)-min(xs)}）、y {min(ys)}–{max(ys)}（高 {max(ys)-min(ys)}）；地图 {MW}×{MH}')
    onEdge = [b for b, xy in ourFinal.items() if xy[1] == MH - 19 or xy[0] == MW - 19]
    print(f'   在地图边线（x={MW-19} 或 y={MH-19}，协调器的钳位线）上的号 {len(onEdge)} 个：{", ".join(sorted(onEdge))}')

if '5' in sec:
    print('§5 每 300 拍：我方号地中位 / 其余在场真人地中位 / 我方号名次（HS）')
    for t in (300, 600, 900, 1200, 1500, 1800, 2100):
        if t not in HS['t']:
            continue
        i = HS['t'].index(t)
        terr, bal = HS['terr'][i], HS['bal'][i]
        alive = [p for p in range(H) if terr[p] > 0]
        ours = [terr[p] for p in alive if p in sq]
        oth = [terr[p] for p in alive if p not in sq]
        en = [terr[p] for p in alive if p not in sq and P[p]['team'] != OUR]
        rk = sorted(alive, key=lambda p: -terr[p])
        ranks = sorted(rk.index(p) + 1 for p in alive if p in sq)
        print(f'   t={t} 在场 {len(alive)} 人：我方号 中位 {st.median(ours):.0f}（{min(ours)}–{max(ours)}）兵合计 {k(sum(bal[p] for p in alive if p in sq))}｜其余真人 中位 {st.median(oth):.0f}｜敌方真人 中位 {st.median(en):.0f}、兵合计 {k(sum(bal[p] for p in alive if p not in sq and P[p]["team"] != OUR))}'
              f'｜我方号名次 {ranks[0]}–{ranks[-1]}（中位 {st.median(ranks):.1f}）；进前一半的 {sum(1 for r in ranks if r <= len(alive) / 2)} 个')

if '6' in sec:
    print('§6 1500–3300 每 300 拍：编队兵 ÷ 敌队兵、没有敌邻的号握兵、落地的陆攻、已执行的捐兵、少拿的利息')
    T30 = J['T30']
    ev = J['events']

    def s10(p, t):
        s = J['S10'][str(p)]
        i = bisect.bisect_right(s['t'], t) - 1
        return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)

    def c30(p, t):
        c = J['C30'][str(p)]
        i = bisect.bisect_right(c['t'], t) - 1
        return {kk: c[kk][i] for kk in c if kk != 't'} if i >= 0 else {}

    def caploss(p, t0, t1):
        f = J['F30'][str(p)]
        i0 = bisect.bisect_right(f['t'], t0) - 1
        i1 = bisect.bisect_right(f['t'], t1) - 1
        return f['capLoss'][i1] - (f['capLoss'][i0] if i0 >= 0 else 0)

    evk = sorted(set(e.get('kind', e.get('type', '?')) for e in ev))
    print(f'   （events 的种类：{", ".join(evk)}）')
    for t0 in range(1500, 3300, 300):
        t1 = t0 + 300
        sqB = sum(s10(p, t0)[1] for p in sq)
        i = HS['t'].index(t0)
        enB = sum(HS['bal'][i][p] for p in range(H) if p not in sq and P[p]['team'] != OUR and HS['terr'][i][p] > 0)
        noE = [p for p in sq if c30(p, t0).get('eh', 0) == 0]
        noEB = sum(s10(p, t0)[1] for p in noE)
        atk = [e for e in ev if e.get('kind', e.get('type')) in ('attack', 'atk') and e.get('p') in sq and t0 <= e.get('t', -1) < t1]
        don = [e for e in ev if e.get('kind', e.get('type')) in ('donate', 'don') and e.get('p') in sq and t0 <= e.get('t', -1) < t1]
        cl = sum(caploss(p, t0, t1) for p in sq)
        print(f'   {t0}–{t1}: 窗首 编队兵 {k(sqB)} ÷ 敌队兵 {k(enB)} = {sqB / max(1, enB):.2f}｜没有敌邻的号 {len(noE)} 个握 {k(noEB)}（{100 * noEB / max(1, sqB):.0f}%）'
              f'｜窗内落地 陆攻 {len(atk)} 条、捐兵 {len(don)} 笔｜少拿的利息 {k(cl)}')

if '7' in sec:
    print('§7 kaito9 与 dsc.gg/cold1（#23）：每 300 拍（HS）两边的地/兵，kaito9 的敌邻格数（C30 eh）')
    q = 23
    for t in (1200, 1500, 1800, 2100, 2400, 2700, 3000):
        i = HS['t'].index(t)
        kp = pid['kaito9']
        npid = pid['noah88']
        c = J['C30'][str(kp)]
        ci = bisect.bisect_right(c['t'], t) - 1
        cn = J['C30'][str(npid)]
        cni = bisect.bisect_right(cn['t'], t) - 1
        print(f'   t={t}: kaito9 {HS["terr"][i][kp]} 格/{k(HS["bal"][i][kp])}（敌邻 {c["eh"][ci]}）｜noah88 {HS["terr"][i][npid]} 格/{k(HS["bal"][i][npid])}（敌邻 {cn["eh"][cni]}）'
              f'｜cold1 {HS["terr"][i][q]} 格/{k(HS["bal"][i][q])}｜kaito9 兵 ÷ cold1 兵 {HS["bal"][i][kp] / max(1, HS["bal"][i][q]):.2f}；两号合计 ÷ cold1 {(HS["bal"][i][kp] + HS["bal"][i][npid]) / max(1, HS["bal"][i][q]):.2f}')

if '8' in sec:
    print('§8 其他真人逐个（出生点取 truth.players[].spawn；地/兵取 HS；地的来源与对真人出兵取 players[] 的全程累计）')
    sp = {p: tuple(P[p]['spawn']) for p in range(H) if P[p].get('spawn') and P[p]['spawn'][0] >= 0}
    near = {p: min(dist(sp[p], sp[q]) for q in sp if q != p) for p in sp}

    def grp(p):
        return '我方号' if p in sq else '路人队友' if P[p]['team'] == OUR else '敌方'

    for g in ('我方号', '路人队友', '敌方'):
        ds = sorted(near[p] for p in sp if grp(p) == g)
        print(f'   到最近真人出生点的距离｜{g} {len(ds)} 人：中位 {st.median(ds):.0f}（{ds[0]:.0f}–{ds[-1]:.0f}）')
    ds = sorted(near[p] for p in sp if p not in sq)
    print(f'   到最近真人出生点的距离｜我方号以外 {len(ds)} 人：中位 {st.median(ds):.0f}')
    ticks = [t for t in (600, 1200, 1500, 1800, 2400, 3000, 3600, 4200, 4800) if t in HS['t']]
    for p in sorted(sp, key=lambda p: -P[p]['peakTerr']):
        if p in sq:
            continue
        x = P[p]
        series = ' | '.join(f'{t}: {HS["terr"][HS["t"].index(t)][p]}/{k(HS["bal"][HS["t"].index(t)][p])}' for t in ticks)
        print(f'   {nm(p)}〔{grp(p)}〕出生 {sp[p]}，最近真人 {near[p]:.0f} 格｜峰值 {x["peakTerr"]}@{x["peakT"]}｜离场 {x["leftT"]} 阵亡 {x["deathT"]}'
              f'｜陆攻 {x["nAtk"]} 条、船 {x["nBoat"]} 条｜地的来源 中立 {x["tilesN"]} / 机器人 {x["tilesB"]} / 真人 {x["tilesH"]}，丢 {x["tilesLost"]}'
              f'｜对真人出兵 {k(x["sentH"])}｜捐出 {x["donOutN"]} 笔 {k(x["donOutV"])}（税 {k(x["donOutFee"])}）收到 {x["donInN"]} 笔 {k(x["donInV"])}')
        print(f'        {series}')
    print('   我方号：地的来源 中立 / 机器人 / 真人，丢给别人的地，对真人出兵')
    for p in sorted(sq, key=lambda p: -P[p]['peakTerr']):
        x = P[p]
        print(f'      {sq[p]}：出生 {sp[p]}，最近真人 {near[p]:.0f} 格｜中立 {x["tilesN"]} / 机器人 {x["tilesB"]} / 真人 {x["tilesH"]}，丢 {x["tilesLost"]}｜对真人出兵 {k(x["sentH"])}｜峰值 {x["peakTerr"]}@{x["peakT"]}')
    for g in ('我方号', '路人队友', '敌方'):
        ps = [p for p in sp if grp(p) == g]
        print(f'   合计｜{g} {len(ps)} 人：中立 {sum(P[p]["tilesN"] for p in ps)} / 机器人 {sum(P[p]["tilesB"] for p in ps)} / 真人 {sum(P[p]["tilesH"] for p in ps)}；对真人出兵 {k(sum(P[p]["sentH"] for p in ps))}')

if '9' in sec:
    print('§9 非我方真人之间的捐兵（allDon = [拍, 捐出方, 受赠方, 到账, 税]）')
    rows9 = [r for r in J['allDon'] if r[1] not in sq and r[2] not in sq]
    rowsIn = [r for r in J['allDon'] if r[1] not in sq and r[2] in sq]
    rowsSq = [r for r in J['allDon'] if r[1] in sq]
    print(f'   全场捐兵 {len(J["allDon"])} 笔：我方号捐出 {len(rowsSq)} 笔 {k(sum(r[3] for r in rowsSq))}（税 {k(sum(r[4] for r in rowsSq))}）；'
          f'路人队友捐给我方号 {len(rowsIn)} 笔 {k(sum(r[3] for r in rowsIn))}（税 {k(sum(r[4] for r in rowsIn))}）；非我方真人之间 {len(rows9)} 笔 {k(sum(r[3] for r in rows9))}（税 {k(sum(r[4] for r in rows9))}）')
    for tm in sorted(set(P[r[1]]['team'] for r in rows9)):
        rs = [r for r in rows9 if P[r[1]]['team'] == tm]
        v = sum(r[3] for r in rs)
        f = sum(r[4] for r in rs)
        print(f'   T{tm} 内部：{len(rs)} 笔 到账 {k(v)}、税 {k(f)}（税 ÷ 到账 {100 * f / max(1, v):.0f}%）；单笔到账 中位 {k(st.median([r[3] for r in rs]))}、最大 {k(max(r[3] for r in rs))}')
    print('   到账 ≥200k 的逐笔：')
    for t, a, b, v, f in rows9:
        if v >= 200e3:
            i = bisect.bisect_right(HS['t'], t) - 1
            print(f'      t={t} {nm(a)} → {nm(b)}：到账 {k(v)}、税 {k(f)}（{100 * f / max(1, v):.0f}%）｜捐出方当时（HS t={HS["t"][i]}）{HS["terr"][i][a]} 格/{k(HS["bal"][i][a])}；受赠方 {HS["terr"][i][b]} 格/{k(HS["bal"][i][b])}')
    print('   按（捐出方 → 受赠方）汇总：')
    agg = defaultdict(lambda: [0, 0, 0, 10 ** 9, 0])
    for t, a, b, v, f in rows9:
        e = agg[(a, b)]
        e[0] += 1
        e[1] += v
        e[2] += f
        e[3] = min(e[3], t)
        e[4] = max(e[4], t)
    for (a, b), e in sorted(agg.items(), key=lambda z: -z[1][1]):
        print(f'      {nm(a)} → {nm(b)}：{e[0]} 笔 到账 {k(e[1])}、税 {k(e[2])}（{100 * e[2] / max(1, e[1]):.0f}%）｜{e[3]}–{e[4]} 拍')
    print('   路人队友捐给我方号（逐笔）：')
    for t, a, b, v, f in rowsIn:
        print(f'      t={t} {nm(a)} → {nm(b)}：到账 {k(v)}、税 {k(f)}（{100 * f / max(1, v):.0f}%）')
    print('   敌方大额捐兵之后受赠方对我方号的出兵（events 里 attack、p=受赠方、q∈我方号，捐兵拍起 60 拍内）：')
    for t, a, b, v, f in rows9:
        if v < 200e3:
            continue
        hits = [e for e in J['events'] if e['type'] == 'attack' and e['p'] == b and e.get('q') in sq and t <= e['t'] <= t + 60]
        if hits:
            print(f'      t={t} {nm(a)} → {nm(b)} {k(v)}：其后 60 拍 ' + '；'.join(f'{e["t"]} 拍 {k(e["troops"])} → {sq[e["q"]]}（对方当时 {e["tL"]} 格/{k(e["tB"])}）' for e in hits))

if '10' in sec:
    print('§10 600 拍窗口：编队从真人手里拿到的地 / 丢给真人的地（pairAll = [窗口序号, 得地方, 失地方, 格数]；失地方 600＝AI 机器人合计、512＝中立）')
    wins = sorted(set(r[0] for r in J['pairAll']))
    for w in wins:
        got = sum(r[3] for r in J['pairAll'] if r[0] == w and r[1] in sq and r[2] < H and r[2] not in sq)
        lost = sum(r[3] for r in J['pairAll'] if r[0] == w and r[2] in sq and r[1] < H and r[1] not in sq)
        fromBots = sum(r[3] for r in J['pairAll'] if r[0] == w and r[1] in sq and r[2] == 600)
        fromN = sum(r[3] for r in J['pairAll'] if r[0] == w and r[1] in sq and r[2] == 512)
        allBots = sum(r[3] for r in J['pairAll'] if r[0] == w and r[1] < H and r[2] == 600)
        allN = sum(r[3] for r in J['pairAll'] if r[0] == w and r[1] < H and r[2] == 512)
        print(f'   窗口 {w}（{w * 600}–{w * 600 + 599} 拍）：编队 从真人 +{got} / 丢给真人 −{lost}｜从机器人 {fromBots}（全场真人 {allBots}，占 {100 * fromBots / max(1, allBots):.1f}%）｜从中立 {fromN}（全场真人 {allN}，占 {100 * fromN / max(1, allN):.1f}%）')
    print('   各窗口里从我方号手里拿地最多的 3 个真人：')
    for w in wins:
        agg = defaultdict(int)
        for r in J['pairAll']:
            if r[0] == w and r[2] in sq and r[1] < H and r[1] not in sq:
                agg[r[1]] += r[3]
        if agg:
            print(f'      窗口 {w}：' + '；'.join(f'{nm(p)} {v}' for p, v in sorted(agg.items(), key=lambda z: -z[1])[:3]))

if '11' in sec:
    print('§11 捐兵配额表（game.js：donCap 初值 15，每逢 t%100==99 加 4（t<1071）/6（<2142）/8（<3213）/10；一笔捐兵 v 花的点数：'
          't<2142 是 2+⌊100v÷(30·uw)⌋，2142–3212 是 2+⌊100v÷(100·uw)⌋，≥3213 是 4+⌊v÷受赠方的地⌋；uw = 1+⌊陆地÷300⌋；≥4284 不限）')
    land = J['map']['land']
    uw = 1 + land // 300

    def cap_at(t):
        c = 15
        for x in range(99, t + 1, 100):
            c += 4 if x < 1071 else 6 if x < 2142 else 8 if x < 3213 else 10
        return c

    def s10b(p, t):
        s = J['S10'][str(p)]
        i = bisect.bisect_right(s['t'], t) - 1
        return (s['terr'][i], s['bal'][i]) if i >= 0 else (0, 0)

    def c30b(p, t):
        c = J['C30'][str(p)]
        i = bisect.bisect_right(c['t'], t) - 1
        return {kk: c[kk][i] for kk in c if kk != 't'} if i >= 0 else {}

    print(f'   全图陆地 {land} → uw = {uw}；t<2142 每点 {30 * uw / 100:.0f} 兵，2142–3212 每点 {uw} 兵')
    for t in (1510, 1800, 2100, 2141, 2142, 2400, 2700, 3000, 3212):
        cap = cap_at(t)
        per = 30 * uw / 100 if t < 2142 else uw
        mx = (cap - 2) * per
        noE = [p for p in sq if c30b(p, t).get('eh', 0) == 0]
        withE = [p for p in sq if c30b(p, t).get('eh', 0) > 0]
        idle = sum(s10b(p, t)[1] for p in noE)
        print(f'   t={t}: 上限 {cap} 点，每点 {per:.0f} 兵 → 一个受赠方累计最多收 {k(mx)}｜有敌邻的号 {len(withE)} 个（{", ".join(sq[p] for p in withE)}）→ 全部收满 {k(mx * len(withE))}'
              f'｜没有敌邻的号 {len(noE)} 个握 {k(idle)} → 收满也只送得出 {100 * mx * len(withE) / max(1, idle):.0f}%')
    for t in (3213, 3600, 3900, 4200):
        cap = cap_at(t)
        rows = []
        for p in sorted(sq, key=lambda p: -s10b(p, t)[0]):
            L, B = s10b(p, t)
            if c30b(p, t).get('eh', 0) > 0 and L > 0:
                rows.append(f'{sq[p]} {L} 格 → 累计最多 {k((cap - 4) * L)}')
        print(f'   t={t}: 上限 {cap} 点，每点 = 受赠方的地｜有敌邻的号：' + '；'.join(rows))
    print('   调度日志的想捐量（pct×捐出方存兵，dispatch[].sim[0].extra.want）与所需点数、对方上限：按 300 拍')
    for t0 in range(1500, 3300, 300):
        rs = [d for d in J['dispatch'] if t0 <= d['t'] < t0 + 300 and d.get('sim')]
        if not rs:
            continue
        wants = [d['sim'][0]['extra'].get('want', 0) for d in rs if d['sim'][0].get('extra')]
        costs = [d['sim'][0]['extra'].get('cost', 0) for d in rs if d['sim'][0].get('extra')]
        caps = [d['sim'][0]['extra'].get('cap', 0) for d in rs if d['sim'][0].get('extra')]
        used = [d['sim'][0]['extra'].get('used', 0) for d in rs if d['sim'][0].get('extra')]
        if not wants:
            continue
        over = sum(1 for c, cp in zip(costs, caps) if c > cp)
        print(f'      {t0}–{t0 + 300}: 日志 {len(rs)} 条｜想捐量 中位 {k(st.median(wants))}、合计 {k(sum(wants))}｜所需点数 中位 {st.median(costs):.0f}｜对方上限 中位 {st.median(caps):.0f}、已用 中位 {st.median(used):.0f}｜单笔就超过整个上限的 {over} 条')

if '12' in sec:
    import os
    PROBE = f'/tmp/c136-r05/work/{M}-donprobe.txt'
    print('§12 3900–4274 拍：kaito9、ryan_m、noah88 对正被真人打的队友（探针；每 25 拍一个采样拍）')
    if not os.path.exists(PROBE):
        print(f'   （缺 {PROBE}：先跑 shadow.mjs {M} --cold --quiet --t0 3595 --t1 4830 --don-probe 3600,3625,…,4825）')
    else:
        rich = ('kaito9', 'ryan_m', 'noah88')
        don = None
        hd = None
        rows12 = []      # (t, donor, dMe, bal, selfUnderAtk, selfAtk, cand, candUnderAtk, reason)
        heads = []       # (t, donor, dMe, bal, returned4343)
        for ln in open(PROBE, encoding='utf8'):
            m = re.match(r'-- 调度候选 (\S+) t=(\d+) 地 (\d+) 兵 (\d+) 密度 (\d+)｜boxedIn=(\w+).*?自己被真人打 (\d+) 自己在打真人 (\d+)(.*)', ln)
            if m:
                don = m.group(1)
                hd = (int(m.group(2)), don, int(m.group(5)), int(m.group(4)), int(m.group(7)), int(m.group(8)), 'L4343' in m.group(9))
                heads.append(hd)
                continue
            m = re.match(r'\s+→ \[APEX\] (\w+)#\d+ 地 (\d+) 兵 (\d+) 密度 (\d+)｜被真人打 (\d+)（([\d.]+)×兵）.*?｜敌邻 (\d+)｜(.*)', ln)
            if m and hd:
                why = m.group(8).strip()
                key = '★' if why.startswith('★') else re.match(r'(L\d+)', why).group(1) if re.match(r'L\d+', why) else why[:12]
                rows12.append((hd[0], hd[1], hd[2], hd[3], hd[4], hd[5], m.group(1), int(m.group(5)), key))
        for a, b in ((3900, 4274), (4275, 4829)):
            sel = [r for r in rows12 if a <= r[0] <= b and r[1] in rich and r[7] > 0]
            hs = [h for h in heads if a <= h[0] <= b and h[1] in rich]
            cnt = defaultdict(int)
            for r in sel:
                cnt[r[8]] += 1
            ret = sum(1 for h in hs if h[6])
            print(f'   {a}–{b}: 三个号的（捐出方×采样拍）{len(hs)} 个，其中 L4343 直接返回（自己在交战）{ret} 个；过了前两道门、候选正被真人打的（捐出方×候选×采样拍）{len(sel)} 个：'
                  + '、'.join(f'{kk} {v}' for kk, v in sorted(cnt.items(), key=lambda z: -z[1])))
            for d in rich:
                hh = [h for h in hs if h[1] == d]
                if not hh:
                    continue
                ds = sorted(h[2] for h in hh)
                bs = sorted(h[3] for h in hh)
                rr = [r for r in sel if r[1] == d]
                c2 = defaultdict(int)
                for r in rr:
                    c2[r[8]] += 1
                print(f'      {d}: 采样拍 {len(hh)}｜密度 {ds[0]}–{ds[-1]}（中位 {st.median(ds):.0f}；≥102 的 {sum(1 for x in ds if x >= 102)} 个）｜存兵 {k(bs[0])}–{k(bs[-1])}｜L4343 直接返回 {sum(1 for h in hh if h[6])}｜对正被打的候选：'
                      + ('、'.join(f'{kk} {v}' for kk, v in sorted(c2.items(), key=lambda z: -z[1])) or '无'))
        print('   同期被打的候选（3900–4274，任何捐出方）：（候选×采样拍）被打的个数 / 其中至少一个队友给了 ★ 的个数')
        cand = defaultdict(lambda: [set(), set()])
        for r in rows12:
            if 3900 <= r[0] <= 4274 and r[7] > 0:
                cand[r[6]][0].add(r[0])
                if r[8] == '★':
                    cand[r[6]][1].add(r[0])
        for c, (a1, a2) in sorted(cand.items(), key=lambda z: -len(z[1][0])):
            print(f'      {c}: {len(a1)} / {len(a2)}')

if '13' in sec:
    print('§13 路人队友的易手（pairAll = [600 拍窗口序号, 得地方, 失地方, 格数]；只计真人之间）')
    mates = [q for q in range(H) if q not in sq and P[q]['team'] == OUR and max(HS['terr'][i][q] for i in range(len(HS['t']))) > 0]
    tot_gain = tot_loss = 0
    for m in mates:
        gain = defaultdict(int)
        loss = defaultdict(int)
        gw = defaultdict(lambda: defaultdict(int))
        lw = defaultdict(lambda: defaultdict(int))
        for w, tk, ls, n in J['pairAll']:
            if tk == m and ls < H:
                gain[ls] += n
                gw[w][ls] += n
            if ls == m and tk < H:
                loss[tk] += n
                lw[w][tk] += n
        tot_gain += sum(v for q, v in gain.items() if P[q]['team'] != OUR)
        tot_loss += sum(v for q, v in loss.items() if P[q]['team'] != OUR)
        print(f'   {nm(m)}：从真人手里拿 {sum(gain.values())} 格（' + ('、'.join(f'{nm(q)} {v}' for q, v in sorted(gain.items(), key=lambda z: -z[1])[:5]) or '无')
              + f'）｜丢给真人 {sum(loss.values())} 格（' + ('、'.join(f'{nm(q)} {v}' for q, v in sorted(loss.items(), key=lambda z: -z[1])[:6]) or '无') + '）')
        for w in sorted(set(gw) | set(lw)):
            print(f'      窗口 {w}（{w * 600}–{w * 600 + 599} 拍）：拿 ' + ('、'.join(f'{nm(q)} {v}' for q, v in sorted(gw[w].items(), key=lambda z: -z[1])[:4]) or '0')
                  + '｜丢 ' + ('、'.join(f'{nm(q)} {v}' for q, v in sorted(lw[w].items(), key=lambda z: -z[1])[:4]) or '0'))
    print(f'   路人队友合计：从敌方真人手里拿 {tot_gain} 格，丢给敌方真人 {tot_loss} 格')
    print('   每 300 拍：路人队友的 地/兵/密度（HS）｜同拍没有敌邻的我方号握着的兵（C30 eh=0，S10 存兵）')

    def s10c(p, t):
        s_ = J['S10'][str(p)]
        i = bisect.bisect_right(s_['t'], t) - 1
        return (s_['terr'][i], s_['bal'][i]) if i >= 0 else (0, 0)

    def c30c(p, t):
        c = J['C30'][str(p)]
        i = bisect.bisect_right(c['t'], t) - 1
        return {kk: c[kk][i] for kk in c if kk != 't'} if i >= 0 else {}

    for t in range(1500, 3601, 300):
        if t not in HS['t']:
            continue
        i = HS['t'].index(t)
        parts = [f"{P[m]['name'][:14]} {HS['terr'][i][m]}/{k(HS['bal'][i][m])}/密 {HS['bal'][i][m] / max(1, HS['terr'][i][m]):.0f}" for m in mates if HS['terr'][i][m] > 0]
        idle = sum(s10c(p, t)[1] for p in sq if c30c(p, t).get('eh', 0) == 0)
        tot = sum(HS['terr'][i][m] for m in mates)
        print(f'      t={t}: ' + ('；'.join(parts) or '（都不在了）') + f'｜路人合计 {tot} 格｜没有敌邻的我方号握 {k(idle)}')
