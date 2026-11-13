#!/usr/bin/env python3
# boatwhy.py — 汇总 boatwhy.mjs 的逐局输出（out/_run/boatwhy/<局>.json）→ out/_cross/boatwhy.txt / .json
#
# 走偏第一处根因（船靠在「不是地」的格上）的上游：这种船为什么会停在地图下标 0。
# boatwhy.mjs 在每艘船发出时读航线的点数；点数不到 2 的，把寻路的每一步读出来。只用模拟器（这一步模拟器和线上引擎一致：
# 两边都发出了这艘船，boatprobe 在线上引擎里读到的船的位置也是下标 0）。
#
# 对账两处：
#   [BW-A] 参照重演对本包日志的核对行数，和 fixprobe 的「不换」臂（out/_cross/fixprobe.json）；
#   [BW-C] 航线只有一个点的船 ←→ 靠在「不是地」的格上的船（fixprobe [FX-D] 的 13 艘），应该是同一批。
#
#   python3 c136-review/agents/R08/scripts/boatwhy.py
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'out', '_run')
OUT = os.path.join(HERE, '..', 'out', '_cross')
SRC = os.path.join(RUN, 'boatwhy')
DIRN = ['上', '右', '下', '左']
BR = {'table': '航线表里现成的', 'reversed': '表里有反向的', 'same': '起点就是 water（建两个点）', 'straight': '直线或斜一段再直一段', 'search': '搜出来的（searchRoute）',
      'full': '航线表满了', 'nocoast': '没有海岸格', 'searchfail': '搜不到', 'unknown': '没记到'}
BRS = ['table', 'reversed', 'same', 'straight', 'search']

lines = []


def P(s=''):
    lines.append(s)


def load(fn):
    try:
        return json.load(open(fn, encoding='utf-8'))
    except Exception:
        return None


order = []
cohort = {}
for mid, H, c in load(os.path.join(RUN, 'fidabl_list.json')) or []:
    order.append(mid)
    cohort[mid] = c
D = {}
killed, running = [], []
for fn in sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []:
    fp = os.path.join(SRC, fn)
    if fn.endswith('.started'):
        try:
            age = time.time() - int(open(fp).read().strip()) / 1000
        except Exception:
            age = 1e9
        (killed if age > 960 else running).append(fn[:-len('.started')])
    elif fn.endswith('.json'):
        d = load(fp)
        if d:
            D[d['matchId']] = d
mids = [m for m in order if m in D]
R = {}
J = {'report': R}

P('boatwhy：一发出就走到头、停在地图下标 0 的船是怎么发出来的（走偏第一处根因的上游；只用模拟器。脚本 boatwhy.mjs → boatwhy.py）')
P()
if killed or running:
    P(f'  跑到一半被时间上限杀掉的：{" ".join(killed) or "无"}；正在跑的：{" ".join(running) or "无"}')
    P()

# ---------- [BW-A]
P('[BW-A] 覆盖和对账')
rows = sum(D[m]['val']['rows'] for m in mids)
both = sum(D[m]['val']['both'] for m in mids)
P(f'  局单 {len(order)} 份录像，有输出的 {len(mids)} 份；参照重演对本包日志快照 {both} / {rows} 行逐位相同')
FX = load(os.path.join(OUT, 'fixprobe.json'))
if FX:
    fx = {r['matchId']: r['arms'].get('none') for r in FX['rows']}
    same = sum(1 for m in mids if fx.get(m) and fx[m]['val']['rows'] == D[m]['val']['rows'] and fx[m]['val']['both'] == D[m]['val']['both'] and fx[m]['endTick'] == D[m]['endTick'])
    P(f'  和 fixprobe 的「不换」臂比（核对行数、结束拍）：{same} / {len(mids)} 份相同')
    R['BW_FX_SAME'] = str(same)
tot = {}
for m in mids:
    for k, v in D[m]['cnt'].items():
        if k in ('lenHist', 'br'):
            continue
        tot[k] = tot.get(k, 0) + v
hist = {}
for m in mids:
    for k, v in D[m]['cnt']['lenHist'].items():
        hist[int(k)] = hist.get(int(k), 0) + v
P(f'  真人发船指令 {tot.get("boatCmd", 0)} 条，成了的 {tot.get("boatCmdOk", 0)} 条；发出的船 {tot.get("launch", 0)} 艘（真人席位 {tot.get("launchHuman", 0)}、内置 AI {tot.get("launchBot", 0)}）')
P('  航线的点数：' + '，'.join(f'{k} 个点 {hist[k]} 艘' for k in sorted(hist) if k <= 4) + f'，5 个点以上 {sum(v for k, v in hist.items() if k >= 5)} 艘')
R['BW_N'] = str(len(mids))
R['BW_VAL_BOTH'] = str(both)
R['BW_VAL_ROWS'] = str(rows)
R['BW_CMDS'] = str(tot.get('boatCmd', 0))
R['BW_CMDS_OK'] = str(tot.get('boatCmdOk', 0))
R['BW_LAUNCH'] = str(tot.get('launch', 0))
R['BW_LAUNCH_HUMAN'] = str(tot.get('launchHuman', 0))
R['BW_LAUNCH_BOT'] = str(tot.get('launchBot', 0))
R['BW_LEN1'] = str(hist.get(1, 0))
R['BW_LEN_LT1'] = str(sum(v for k, v in hist.items() if k < 1))
P()

# ---------- [BW-B]
P('[BW-B] 航线不到两个点的船，逐艘（寻路每一步读到的）')
P('  局 | 发出的拍 | 船主 | 发出时船上的兵 | 方向 | 航线 | water 四邻里本方的地：格数 / 在海岸表里的 / 在边界表里的 / 自己四邻里有无主地或别人的地的 | 海岸表里离 water 最近的格：距离 | 它旁边的水格（寻路的起点）是不是 water：距离 | 航线出自寻路的哪一步 | 本来要靠的那一格是谁的 | 下一拍靠岸读的格 | 同一局里更早从同一个 water 发出过这种船')
notes = []
for m in mids:
    lands = {(x['t'], x['p']): x for x in D[m]['lands']}
    for x in D[m]['notes']:
        x = dict(x)
        x['matchId'] = m
        x['land'] = lands.get((x['t'] + 1, x['p']))
        prev = [y for y in notes if y['matchId'] == m and y.get('water') == x.get('water') and y['t'] < x['t']]
        x['prev'] = f'{prev[0]["t"]} 拍 #{prev[0]["p"]}' if prev else None
        notes.append(x)
J['notes'] = notes


def vt(l):
    if not l:
        return '（下一拍没有靠岸）'
    v = l['v']
    kind = '图外' if v is None else {2: '水', 3: '图边', 5: '山'}.get(v, f'地形号 {v}')
    return f'下标 {l["c"]}（{kind}），船在下标 {l["at"]}'


for x in notes:
    if not x.get('fromCmd'):
        P(f'  {x["matchId"]} | {x["t"]} | #{x["p"]} | {x["troops"]} | 类型 {x["type"]} | {x["len"]} 个点 | （不是真人发船指令发出来的）')
        continue
    who = x['wantOwner']
    who = '无主地' if who == 'neutral' else '不是地' if who is None else ('自己' if who == x['p'] else f'#{who}')
    P(f'  {x["matchId"]} | {x["t"]} | #{x["p"]} | {max(x["troops"], 60)} | {DIRN[x["dir"] & 3]} | {x["len"]} 个点{"，就是 water" if x.get("routeIsWater") else ""} | '
      f'{x["ownAdj"]} / {x["ownAdjCoast"]} / {x.get("ownAdjBorder", "?")} / {x.get("ownAdjHostile", "?")} | {math.sqrt(x["coastDist2"]):.1f} 格 | {"是" if x["startIsWater"] else "不是"}：{math.sqrt(x["startDist2"]):.1f} 格 | '
      f'{BR.get(x.get("br"), x.get("br"))} | {who} | {vt(x["land"])} | {x["prev"] or "没有"}')
n = len(notes)
cmd = [x for x in notes if x.get('fromCmd')]
P(f'  合计 {n} 艘，{len({x["matchId"] for x in notes})} 局；其中真人发船指令发出来的 {len(cmd)} 艘，内置 AI 的 {sum(1 for x in notes if not x["human"])} 艘')
P(f'  这 {len(cmd)} 艘里：航线只有一个点、这个点就是 water 的 {sum(1 for x in cmd if x.get("routeIsWater"))} 艘；water 四邻里有本方的地的 {sum(1 for x in cmd if x["ownAdj"] > 0)} 艘，'
  f'那些地没有一格在海岸表里的 {sum(1 for x in cmd if x["ownAdj"] > 0 and x["ownAdjCoast"] == 0)} 艘')
nb = [x for x in cmd if x['ownAdj'] > 0 and x['ownAdjCoast'] == 0]
P(f'  这 {len(nb)} 艘（water 挨着的本方地没有一格在海岸表里）挨着 water 的本方地一共 {sum(x["ownAdj"] for x in nb)} 格：在边界表里的 {sum(x.get("ownAdjBorder", 0) for x in nb)} 格，'
  f'自己四邻里有无主地或别人的地的 {sum(x.get("ownAdjHostile", 0) for x in nb)} 格')
R['BW_NB_CELLS'] = str(sum(x['ownAdj'] for x in nb))
R['BW_NB_BORDER'] = str(sum(x.get('ownAdjBorder', 0) for x in nb))
R['BW_NB_HOSTILE'] = str(sum(x.get('ownAdjHostile', 0) for x in nb))
pathA = [x for x in cmd if not x['startIsWater']]
pathB = [x for x in cmd if x['startIsWater']]
P(f'  两条来路：寻路的起点不是 water 的 {len(pathA)} 艘（其中 water 四邻的本方地没有一格在海岸表里的 {sum(1 for x in pathA if x["ownAdj"] > 0 and x["ownAdjCoast"] == 0)} 艘，'
  f'航线是搜出来的 {sum(1 for x in pathA if x.get("br") == "search")} 艘）；'
  f'起点就是 water 的 {len(pathB)} 艘（其中航线是表里现成的 {sum(1 for x in pathB if x.get("br") == "table")} 艘；同一局里更早已经有船从同一个 water 发出、留下了一个点的航线的 {sum(1 for x in pathB if x["prev"])} 艘'
  + ('：' + '、'.join(f'{x["matchId"]} {x["t"]} 拍 #{x["p"]}（前一艘是 {x["prev"]}）' for x in pathB if x['prev']) if pathB else '') + '）')
decay = []
for x in cmd:
    if not x['land']:
        continue
    a, b = max(x['troops'], 60), x['land']['troops']
    if a != b:
        ok = x['t'] % 5 == 3 and b == max(a - max(1, a >> 7), 0)
        decay.append(f'{x["matchId"]} {x["t"]} 拍 #{x["p"]}：发出时 {a}、靠岸时 {b}（差 {a - b}；{"发出的那一拍 t % 5 = 3，正好是船上损耗拍，减 1/128，对得上" if ok else "对不上损耗规则"}）')
P(f'  发出时的兵和下一拍靠岸时的兵：相同的 {sum(1 for x in cmd if x["land"] and max(x["troops"], 60) == x["land"]["troops"])} 艘；不同的 {len(decay)} 艘' + ('——' + '；'.join(decay) if decay else ''))
R['BW_TROOPS_SAME'] = str(sum(1 for x in cmd if x['land'] and max(x['troops'], 60) == x['land']['troops']))
R['BW_TROOPS_DIFF'] = str(len(decay))
P(f'  同一个 water 上不止一艘的：{sum(1 for x in cmd if x["prev"])} 艘是重复（{"、".join(sorted({x["matchId"] for x in cmd if x["prev"]})) or "无"}）；不同的 water 一共 {len({(x["matchId"], x["water"]) for x in cmd})} 个')
dirs = {}
for x in cmd:
    dirs[x['dir'] & 3] = dirs.get(x['dir'] & 3, 0) + 1
P('  按发船方向：' + '，'.join(f'{DIRN[k]} {dirs[k]} 艘' for k in sorted(dirs))
  + f'；下一拍靠岸读的格在图外的 {sum(1 for x in cmd if x["land"] and x["land"]["v"] is None)} 艘、是图边格的 {sum(1 for x in cmd if x["land"] and x["land"]["v"] == 3)} 艘、'
  f'船的位置是下标 0 的 {sum(1 for x in cmd if x["land"] and x["land"]["at"] == 0)} 艘')
want = {}
for x in cmd:
    w = x['wantOwner']
    k = '无主地' if w == 'neutral' else '不是地' if w is None else ('自己的地' if w == x['p'] else '别的玩家的地')
    want[k] = want.get(k, 0) + 1
P('  本来要靠的那一格：' + '，'.join(f'{k} {v} 艘' for k, v in sorted(want.items())))
R['BW_NOTES'] = str(n)
R['BW_NOTES_MATCHES'] = str(len({x['matchId'] for x in notes}))
R['BW_NOTES_CMD'] = str(len(cmd))
R['BW_NOTES_BOT'] = str(sum(1 for x in notes if not x['human']))
R['BW_ROUTE_IS_WATER'] = str(sum(1 for x in cmd if x.get('routeIsWater')))
R['BW_OWNADJ'] = str(sum(1 for x in cmd if x['ownAdj'] > 0))
R['BW_OWNADJ_NOCOAST'] = str(sum(1 for x in cmd if x['ownAdj'] > 0 and x['ownAdjCoast'] == 0))
R['BW_START_NOT_WATER'] = str(len(pathA))
R['BW_PATH_A_NOCOAST'] = str(sum(1 for x in pathA if x['ownAdj'] > 0 and x['ownAdjCoast'] == 0))
R['BW_PATH_A_SEARCH'] = str(sum(1 for x in pathA if x.get('br') == 'search'))
R['BW_PATH_B_TABLE'] = str(sum(1 for x in pathB if x.get('br') == 'table'))
R['BW_PATH_B'] = str(len(pathB))
R['BW_PATH_B_PREV'] = str(sum(1 for x in pathB if x['prev']))
R['BW_REPEAT'] = str(sum(1 for x in cmd if x['prev']))
R['BW_WATERS'] = str(len({(x['matchId'], x['water']) for x in cmd}))
R['BW_OFFMAP'] = str(sum(1 for x in cmd if x['land'] and x['land']['v'] is None))
R['BW_EDGE'] = str(sum(1 for x in cmd if x['land'] and x['land']['v'] == 3))
R['BW_AT0'] = str(sum(1 for x in cmd if x['land'] and x['land']['at'] == 0))
R['BW_WANT_OTHER'] = str(want.get('别的玩家的地', 0))
R['BW_WANT_SELF'] = str(want.get('自己的地', 0))
R['BW_WANT_NEUTRAL'] = str(want.get('无主地', 0))
P()

# ---------- [BW-C]
P('[BW-C] 对账：航线只有一个点的船 ←→ 靠在「不是地」的格上的船')
lands = [(m, x['t'], x['p'], x['troops']) for m in mids for x in D[m]['lands']]
from_notes = {(x['matchId'], x['t'] + 1, x['p']) for x in notes}
hit = sum(1 for m, t, p, tr in lands if (m, t, p) in from_notes)
back = sum(1 for x in notes if x['land'])
P(f'  靠在「不是地」的格上的船 {len(lands)} 艘：其中前一拍发出、航线不到两个点的 {hit} 艘；航线不到两个点的 {n} 艘里，下一拍靠在「不是地」的格上的 {back} 艘')
R['BW_LANDS'] = str(len(lands))
R['BW_LANDS_HIT'] = str(hit)
R['BW_NOTES_BACK'] = str(back)
if FX:
    fxb = {(b['matchId'], b['t'], b['p'], b['troops']) for b in FX.get('boats', [])}
    mine = set(lands)
    P(f'  和 fixprobe [FX-D] 的船（局、靠岸的拍、船主、兵）比：fixprobe {len(fxb)} 艘，这里 {len(mine)} 艘，两边都有的 {len(fxb & mine)} 艘')
    R['BW_FX_BOATS'] = str(len(fxb))
    R['BW_FX_BOATS_BOTH'] = str(len(fxb & mine))
P()

# ---------- [BW-D]
P('[BW-D] 前提有多常见：成了的真人发船指令，按 water 四邻里有没有本方的地分')
P('  类 | 指令 | 其中航线只有一个点的')
for key, name in (('adj0', 'water 四邻里没有本方的地'), ('adjCoast', '有本方的地，至少一格在海岸表里'), ('adjNoCoast', '有本方的地，没有一格在海岸表里')):
    a, b = tot.get(key, 0), tot.get(key + 'Len1', 0)
    P(f'  {name} | {a} | {b}' + (f'（{100 * b / a:.1f}%）' if a else ''))
    R[f'BW_{key.upper()}'] = str(a)
    R[f'BW_{key.upper()}_LEN1'] = str(b)
    R[f'BW_{key.upper()}_PCT'] = f'{100 * b / a:.1f}%' if a else '—'
P()
P('  同一批指令再按「航线出自寻路的哪一步」分（每格：指令数 / 其中航线只有一个点的）')
brt = {}
for m in mids:
    for key, B in (D[m]['cnt'].get('br') or {}).items():
        for b, (n1, n2) in B.items():
            e = brt.setdefault(key, {}).setdefault(b, [0, 0])
            e[0] += n1
            e[1] += n2
cols = BRS + sorted({b for B in brt.values() for b in B} - set(BRS))
P('  类 | ' + ' | '.join(BR.get(b, b) for b in cols) + ' | 合计')
for key, name in (('adj0', 'water 四邻里没有本方的地'), ('adjCoast', '有本方的地，至少一格在海岸表里'), ('adjNoCoast', '有本方的地，没有一格在海岸表里')):
    B = brt.get(key, {})
    P(f'  {name} | ' + ' | '.join(f'{B.get(b, [0, 0])[0]} / {B.get(b, [0, 0])[1]}' for b in cols) + f' | {sum(v[0] for v in B.values())} / {sum(v[1] for v in B.values())}')
    for b in cols:
        R[f'BW_BR_{key.upper()}_{b.upper()}'] = str(B.get(b, [0, 0])[0])
        R[f'BW_BR_{key.upper()}_{b.upper()}_LEN1'] = str(B.get(b, [0, 0])[1])
sea = sum(B.get('search', [0, 0])[0] for B in brt.values())
sea_own = sum(brt.get(k, {}).get('search', [0, 0])[0] for k in ('adjCoast', 'adjNoCoast'))
sea_own1 = sum(brt.get(k, {}).get('search', [0, 0])[1] for k in ('adjCoast', 'adjNoCoast'))
sea0 = brt.get('adj0', {}).get('search', [0, 0])
P(f'  走到 searchRoute 的 {sea} 条：water 挨着本方的地的 {sea_own} 条，航线只有一个点的 {sea_own1} 条；water 不挨着本方的地的 {sea0[0]} 条，航线只有一个点的 {sea0[1]} 条')
R['BW_SEARCH'] = str(sea)
R['BW_SEARCH_OWN'] = str(sea_own)
R['BW_SEARCH_OWN_LEN1'] = str(sea_own1)
R['BW_SEARCH_ADJ0'] = str(sea0[0])
R['BW_SEARCH_ADJ0_LEN1'] = str(sea0[1])
a = tot.get('boatCmdOk', 0)
P(f'  合计 {a} 条；航线只有一个点的 {sum(tot.get(k + "Len1", 0) for k in ("adj0", "adjCoast", "adjNoCoast"))} 条'
  + (f'（每 {a / max(1, len(cmd)):.0f} 条成了的发船指令里 1 条）' if cmd else ''))
R['BW_ONE_IN'] = f'{a / max(1, len(cmd)):.0f}' if cmd else '—'
per = sorted(((m, len(D[m]['notes'])) for m in mids if D[m]['notes']), key=lambda z: -z[1])
P('  有这种船的局：' + ('；'.join(f'{m} {k} 艘' for m, k in per) or '无') + f'；一艘都没有的 {len(mids) - len(per)} 局')
R['BW_MATCHES_NONE'] = str(len(mids) - len(per))
P()
P('怎么读（代码事实在 src/sim/sim/boats.js，行号是镜像里那一份的）：')
P('  1. 真人发船 boat(pct, water, dir)（L777-792）只检查 water 是挨着岸的水格、water 按方向挪一格是地；不检查 water 是不是挨着自己的地。')
P('  2. 寻路 boatRouteIndex（L659-671）：先在海岸表 coast[p] 里找离 water 最近的格，取它旁边的水格当起点。海岸表只收「四邻里有水、但没有无主地也没有别人的地」的本方格')
P('     （game.js hostileTo L172-175、promoteToBorder L1119-1130、refreshBorder L1170-1189：四邻里有无主地或别人的地——队友的也算——的格归边界表 border[p]）。')
P('     所以顶在前线上、同时挨着水的本方格不在海岸表里。')
P('  3. 来路一：起点不是 water、航线表里没有现成的、两点之间又没有直线或「斜一段再直一段」的水路（straightRoute L698-710）时，走 searchRoute(water, p)（L714-759）：')
P('     从 water 向外搜，搜到上下左右挨着本方的地的水格就停。water 自己挨着本方的地（不管那一格在不在海岸表里），第一圈就停，回溯出来的航线只有 [water] 一个点，')
P('     并且按「起点 water、终点 water」记进航线表（addRoute L545-551）。')
P('     来路二：之后任何一个号从同一个 water 发船、而它的海岸表里正好有挨着 water 的格（起点就是 water）时，boatRouteIndex 第一步查表 findRoute(water, water)')
P('     查到的就是这条一个点的航线（排在「起点等于终点就建 [water, water] 两个点的航线」那一行前面），于是它的船也只有一个点。')
P('  4. 一个点的航线：moveBoats（L289-326）取下一个点是 undefined，位置算出来是 NaN，写进 Uint32Array 是 0；进度当拍到头。')
P('     下一拍靠岸（arrive L230-260）读的是「下标 0 按发船方向挪一格」：上、左在图外，右、下是图边的格——之后兵的去向见 boatprobe / fixprobe。')
P()
P('读数时的限制：')
P('  1. 这是模拟器里读到的。发船这一步模拟器和线上引擎一致的证据是间接的：boatprobe 在引擎里读过 5 艘，位置都是下标 0、都是发出的当拍到头；')
P('     有这种船的局里，除了已知走偏的 A053、A057，其余的整局全场地和兵和引擎一致 [FA-E]。引擎那一侧的航线点数没有直接读。')
P('  2. 「航线出自哪一步」是照 boatRouteIndex 的顺序在调用它以前只读地走了一遍得到的（查表、看表满没满、查反向、比起点），直线和搜索两步是看原函数有没有走到 searchRoute。')
P('  3. 只看了真人发船指令。内置 AI 发的船不走 searchRoute（boatRouteIndex 的 bfs 参数是 0），这 89 份录像里它们的航线没有一个点的。')

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'boatwhy.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
J['rows'] = [dict(matchId=m, cohort=cohort.get(m), cnt=D[m]['cnt'], notes=len(D[m]['notes']), lands=len(D[m]['lands'])) for m in mids]
with open(os.path.join(OUT, 'boatwhy.json'), 'w', encoding='utf-8') as f:
    json.dump(J, f, ensure_ascii=False)
if '-q' in sys.argv:
    print(f'boatwhy.py：{len(mids)} 份录像 → out/_cross/boatwhy.txt')
else:
    print('\n'.join(lines))
