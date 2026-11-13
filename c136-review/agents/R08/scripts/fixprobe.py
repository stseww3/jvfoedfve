#!/usr/bin/env python3
# fixprobe.py — 汇总 fixprobe.mjs 的逐局输出（out/_run/fixprobe/<局>.<臂>.json）→ out/_cross/fixprobe.txt / .json
#
# 两处走偏根因的充分性检验：把线上引擎原文里那两步的写法补到重放器的对局对象上（实例上包一层，src/sim 不动），
# 看参照重演对本包日志快照（本编队各号的地和兵，每个快照一行）逐位核对，不一致的行还剩多少。
#   none  不换      copy  自检（扫描表那一支照抄、规则不换，应该和 none 逐位相同）
#   scan  只换无主地扫描表「要不要重扫」那一步      boat  只换船靠在「不是地」的格上那一步      both  两处都换
# 真值只有本包日志（线上引擎的文件不在镜像里）：所以这里量到的是「日志看得见的地方对不对得上」，不是全场 512 个玩家逐位。
# 和线上引擎直接比的只有两小段：
#   [FX-F] boatprobe 在清场以前逐拍读过 5 艘船之后船主的余额和欠账（out/_cross/boatprobe.txt），这里拿同样几拍的重放器读数去比；
#   [FX-G] huskprobe 在清场以前逐拍读过 A001 扫描表岔开前后的九项「看不见的状态」（out/_cross/huskprobe.txt），同样去比。
#
# 图外的格不在「换」的范围里：模拟器读图外的格得到 undefined，不走提前返回那一行，结果和线上引擎相同（见 fixprobe.mjs 的说明）；
# 这种船在 [FX-D](b) 里单列。
#
#   python3 c136-review/agents/R08/scripts/fixprobe.py
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'out', '_run')
OUT = os.path.join(HERE, '..', 'out', '_cross')
SRC = os.path.join(RUN, 'fixprobe')
ARMS = ['none', 'copy', 'scan', 'boat', 'both']
AN = {'none': '不换', 'copy': '自检（照抄不换规则）', 'scan': '只换扫描表那一步', 'boat': '只换船靠岸那一步', 'both': '两处都换'}
FOCUS = ['A053', 'A057', 'A001']

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
killed = []
running = []
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
            D.setdefault(d['matchId'], {})[d['arm']] = d
mids = [m for m in order if m in D] + sorted(m for m in D if m not in order)
R = {}
J = {'report': R}


def bad(d):
    return d['val']['rows'] - d['val']['both']


def vt(v):
    return '图外' if v is None else {1: '无主地', 2: '水', 3: '图边', 5: '山'}.get(v, f'地形号 {v}')


P('fixprobe：两处走偏根因的充分性检验——把线上引擎原文里那两步的写法补到重放器的对局对象上（src/sim 不动），看走偏还剩多少')
P('（真值是本包日志里本编队各号的地和兵；脚本 fixprobe.mjs → fixprobe.py）')
P()
if killed or running:
    P(f'  跑到一半被时间上限杀掉的：{" ".join(killed) or "无"}；正在跑的：{" ".join(running) or "无"}')
    P()

# ---------- [FX-A]
P('[FX-A] 走偏的 3 局，逐臂')
P('  局 | 臂 | 对本包日志快照：都一致 / 行数 | 不一致的行 | 第一处不一致的拍 | 每 10 拍全场地和兵的校验和 和「不换」相同 | 结束拍 | 猎杀 / 提速事件 | 扫描表那一步两种规则不同的次数（走到那一步的次数）| 靠在不是地的格上的船')
for mid in FOCUS:
    if mid not in D:
        continue
    base = D[mid].get('none')
    for arm in ARMS:
        d = D[mid].get(arm)
        if not d:
            continue
        same = '—' if not base else ('是' if d['refHash'] == base['refHash'] and d['refHashN'] == base['refHashN'] else '否')
        P(f'  {mid} | {AN[arm]} | {d["val"]["both"]} / {d["val"]["rows"]} | {bad(d)} | {d["firstMism"][0] if d["firstMism"] else "—"} | {same} | {d["endTick"]} | '
          f'{len(d["events"])} | {len(d["scanNotes"])}（{d["scanReached"]}） | {len(d["boatNotes"])}')
        R[f'FX_{mid}_{arm.upper()}_BAD'] = str(bad(d))
        R[f'FX_{mid}_{arm.upper()}_ROWS'] = str(d['val']['rows'])
        R[f'FX_{mid}_{arm.upper()}_FIRST'] = str(d['firstMism'][0]) if d['firstMism'] else '—'
P()

# ---------- [FX-B]
cp = [(m, D[m]['none'], D[m]['copy']) for m in mids if 'none' in D[m] and 'copy' in D[m]]
ok = [m for m, a, b in cp if a['refHash'] == b['refHash'] and a['refHashN'] == b['refHashN'] and a['val'] == b['val'] and a['endTick'] == b['endTick'] and a['events'] == b['events']]
reached = sum(b['scanReached'] for m, a, b in cp)
P('[FX-B] 自检：扫描表那一支照抄、规则不换（copy），和不换（none）比')
P(f'  两条臂都有的 {len(cp)} 局（{" ".join(m for m, a, b in cp)}）：校验和、核对行数、结束拍、事件表全部相同的 {len(ok)} 局；照抄的那一支在这几局里一共走到「要不要重扫」那一步 {reached} 次')
R['FX_COPY_N'] = str(len(cp))
R['FX_COPY_OK'] = str(len(ok))
P()

# ---------- [FX-C]
nb = [(m, D[m]['none'], D[m]['both']) for m in mids if 'none' in D[m] and 'both' in D[m]]
P('[FX-C] 全部录像：不换（none）对 两处都换（both）')
rows0 = sum(a['val']['rows'] for m, a, b in nb)
ok0 = sum(a['val']['both'] for m, a, b in nb)
rows1 = sum(b['val']['rows'] for m, a, b in nb)
ok1 = sum(b['val']['both'] for m, a, b in nb)
P(f'  两条臂都有的 {len(nb)} 份录像；对本包日志快照逐位核对：不换 {ok0} / {rows0} 行（不一致 {rows0 - ok0} 行），两处都换 {ok1} / {rows1} 行（不一致 {rows1 - ok1} 行）')
R['FX_N'] = str(len(nb))
R['FX_NONE_OK'] = str(ok0)
R['FX_NONE_ROWS'] = str(rows0)
R['FX_NONE_BAD'] = str(rows0 - ok0)
R['FX_BOTH_OK'] = str(ok1)
R['FX_BOTH_ROWS'] = str(rows1)
R['FX_BOTH_BAD'] = str(rows1 - ok1)
better = [(m, bad(a), bad(b)) for m, a, b in nb if bad(b) < bad(a)]
worse = [(m, bad(a), bad(b)) for m, a, b in nb if bad(b) > bad(a)]
same = [m for m, a, b in nb if bad(b) == bad(a)]
P(f'  不一致的行变少的 {len(better)} 局' + (('：' + '；'.join(f'{m} {x}→{y}' for m, x, y in better)) if better else '')
  + f'；不变的 {len(same)} 局（其中本来就是 0 的 {sum(1 for m, a, b in nb if bad(a) == 0 and bad(b) == 0)} 局）'
  + f'；变多的 {len(worse)} 局' + (('：' + '；'.join(f'{m} {x}→{y}' for m, x, y in worse)) if worse else ''))
R['FX_BETTER'] = str(len(better))
R['FX_WORSE'] = str(len(worse))
R['FX_SAME'] = str(len(same))
left = [(m, bad(b), b['firstMism'][0] if b['firstMism'] else None) for m, a, b in nb if bad(b)]
P('  两处都换以后还有不一致的行的局：' + ('；'.join(f'{m} {x} 行（第一处 {t} 拍）' for m, x, t in left) if left else '无'))
R['FX_LEFT'] = str(len(left))
fired_scan = [m for m, a, b in nb if a['scanNotes']]
fired_boat = [m for m, a, b in nb if any(x['v'] is not None for x in a['boatNotes'])]
fired = set(fired_scan) | set(fired_boat)
hash_diff = [m for m, a, b in nb if not (a['refHash'] == b['refHash'] and a['refHashN'] == b['refHashN'])]
quiet = [m for m, a, b in nb if m not in fired]
quiet_same = [m for m, a, b in nb if m not in fired and a['refHash'] == b['refHash'] and a['refHashN'] == b['refHashN'] and a['endTick'] == b['endTick'] and a['events'] == b['events']]
P(f'  不换的那一遍里，扫描表那一步两种规则不同过的 {len(fired_scan)} 局（{" ".join(fired_scan) or "无"}）；有船靠在图内不是地的格上的 {len(fired_boat)} 局（{" ".join(fired_boat) or "无"}）')
P(f'  两处都没有碰到的 {len(quiet)} 局：换不换，每 10 拍全场 512 个玩家地和兵的校验和、结束拍、事件表全部相同的 {len(quiet_same)} 局')
P(f'  校验和不同的局（换了以后全场某个玩家的地或兵在某个取样拍上不一样了）：{" ".join(hash_diff) or "无"}')
same_out = []
debt_only = []
for m, a, b in nb:
    if m not in fired or m in hash_diff:
        continue
    bn = {(x['t'], x['p'], x['c']): x for x in b['boatNotes']}
    hows_m = [bn[(x['t'], x['p'], x['c'])]['how'] for x in a['boatNotes'] if x['v'] is not None and (x['t'], x['p'], x['c']) in bn]
    (same_out if all(h.startswith('不敌对') for h in hows_m) else debt_only).append(m)
P(f'  碰到了但校验和没有变的局：{" ".join(m for m in sorted(fired) if m not in hash_diff) or "无"}——其中船都是「不敌对、作废」、两种写法结果本来就一样的 {len(same_out)} 局（{" ".join(same_out) or "无"}）；'
  f'有船被挂成进攻、但全场地和兵到终局没有变的 {len(debt_only)} 局（{" ".join(debt_only) or "无"}；差别在哪见 [FX-D]）')
R['FX_TOUCHED_SAMEHASH'] = str(len([m for m in fired if m not in hash_diff]))
R['FX_SAME_OUT'] = str(len(same_out))
R['FX_DEBT_ONLY'] = str(len(debt_only))
R['FX_SCAN_MATCHES'] = str(len(fired_scan))
R['FX_BOAT_MATCHES'] = str(len(fired_boat))
R['FX_QUIET'] = str(len(quiet))
R['FX_QUIET_SAME'] = str(len(quiet_same))
R['FX_HASH_DIFF'] = str(len(hash_diff))
ev_diff = [m for m, a, b in nb if a['endTick'] != b['endTick'] or a['events'] != b['events']]
P(f'  结束拍或者猎杀 / 提速事件表变了的局：' + ('；'.join(
    f'{m}（结束拍 {D[m]["none"]["endTick"]}→{D[m]["both"]["endTick"]}，事件 {len(D[m]["none"]["events"])}→{len(D[m]["both"]["events"])}'
    + (f'，换了以后第一次在 {D[m]["both"]["events"][0][0]} 拍' if D[m]['both']['events'] else '') + '）' for m in ev_diff) if ev_diff else '无'))
ev0 = sum(1 for m, a, b in nb if a['events'])
ev1 = sum(1 for m, a, b in nb if b['events'])
hunt0 = sum(1 for m, a, b in nb if any(e[1] == 'hunt' for e in a['events']))
hunt1 = sum(1 for m, a, b in nb if any(e[1] == 'hunt' for e in b['events']))
P(f'  触发过猎杀 / 终局提速的局：不换 {ev0} 局（其中有过猎杀的 {hunt0} 局），两处都换 {ev1} 局（{hunt1} 局）')
R['FX_EV_NONE'] = str(ev0)
R['FX_EV_BOTH'] = str(ev1)
R['FX_HUNT_NONE'] = str(hunt0)
R['FX_HUNT_BOTH'] = str(hunt1)
R['FX_EV_DIFF'] = str(len(ev_diff))
P()

# ---------- [FX-D]
P('[FX-D] 靠在「不是地」的格上的船（不换的那一遍读到的全部）')
P('  (a) 图内的格（图边 / 山 / 水）——模拟器直接返回、引擎按读出来的主人号处理，就是换的那一步')
P('  局 | 拍 | 船主 | 船上的兵 | 要读的那一格 | 按引擎的公式读出来的主人号（在场 / 地）| 和船主 | 两处都换以后的去向 | 之后 8 拍船主余额、欠账的变化（拍:变化）：不换 → 两处都换')


def after(y):
    if not y or not y.get('after'):
        return '—'
    prev = y['bal0']
    pd = y.get('debt0') or 0
    ch = []
    for row in y['after']:
        t, bal = row[0], row[1]
        debt = row[3] if len(row) > 3 else pd
        if bal != prev:
            ch.append(f'{t}:{bal - prev:+d}')
        if debt != pd:
            ch.append(f'{t}:欠账{debt - pd:+d}')
        prev, pd = bal, debt
    return ' '.join(ch) or '没有变化'


nin = noff = 0
hows = {}
vs = {}
off_matches = set()
in_matches = set()
off_enemy0 = off_had = off_noslot = 0
J['boats'] = []
for m, a, b in nb:
    bn = {(x['t'], x['p'], x['c']): x for x in b['boatNotes']}
    for x in a['boatNotes']:
        J['boats'].append(dict(matchId=m, t=x['t'], p=x['p'], troops=x['troops'], v=x['v'], target=x['target'], enemy=x['enemy']))
        if x['v'] is None:
            noff += 1
            off_matches.add(m)
            off_enemy0 += 0 if x['enemy'] else 1
            off_had += 1 if x.get('hadAtk0') else 0
            off_noslot += 0 if x.get('freeSlot', 1) else 1
            continue
        nin += 1
        in_matches.add(m)
        y = bn.get((x['t'], x['p'], x['c']))
        how = y['how'] if y else '（两处都换的那一遍里没有这艘船）'
        hk = how.split(' ')[0]
        hows[hk] = hows.get(hk, 0) + 1
        vs[vt(x['v'])] = vs.get(vt(x['v']), 0) + 1
        P(f'  {m} | {x["t"]} | #{x["p"]} | {x["troops"]} | {vt(x["v"])}（下标 {x["c"]}） | {x["target"]}（{"在场" if x["tAlive"] else "不在场"} / {x["tTerr"]}） | {"敌对" if x["enemy"] else "不敌对"} | {how} | {after(x)} → {after(y)}')
P(f'  合计 {nin} 艘，{len(in_matches)} 局（{" ".join(sorted(in_matches)) or "无"}）；要读的那一格：' + ('，'.join(f'{k} {v} 艘' for k, v in sorted(vs.items())) or '无')
  + '；两处都换以后的去向：' + ('，'.join(f'{k} {v} 艘' for k, v in sorted(hows.items())) or '无'))
R['FX_BOATS_IN'] = str(nin)
R['FX_BOATS_IN_MATCHES'] = str(len(in_matches))
R['FX_BOATS_IN_ATTACK'] = str(sum(v for k, v in hows.items() if k.startswith('敌对：挂成进攻')))
R['FX_BOATS_IN_VOID'] = str(sum(v for k, v in hows.items() if k.startswith('不敌对')))
# 敌对的那几艘：换了以后退回的兵进了余额还是抵了欠账（只看两条臂在这艘船之前状态相同的：船主当拍的余额、欠账两边一样）
to_bal, to_debt, skipped = [], [], []
for m, a, b in nb:
    bn = {(x['t'], x['p'], x['c']): x for x in b['boatNotes']}
    for x in a['boatNotes']:
        y = bn.get((x['t'], x['p'], x['c']))
        if x['v'] is None or not y or not y['how'].startswith('敌对：挂成进攻'):
            continue
        if (x['bal0'], x['debt0']) != (y['bal0'], y['debt0']) or not x.get('after') or not y.get('after'):
            skipped.append(m)
            continue
        ex, ey = x['after'][-1], y['after'][-1]
        dbal, ddebt = ey[1] - ex[1], (ey[3] if len(ey) > 3 else 0) - (ex[3] if len(ex) > 3 else 0)
        tag = f'{m} #{x["p"]}（{x["troops"]} 兵；8 拍后和不换的那一遍比，余额 {dbal:+d}、欠账 {ddebt:+d}）'
        (to_debt if ddebt and not dbal else to_bal).append(tag)
P(f'  敌对的那几艘，换了以后退回的兵：进了余额的 {len(to_bal)} 艘——' + ('；'.join(to_bal) or '无'))
P(f'    抵了欠账的 {len(to_debt)} 艘——' + ('；'.join(to_debt) or '无') + '。抵欠账的船，全场地和兵看不出差别（[FX-C]），只比地和兵的核对（engdiff）不会报')
R['FX_REFUND_BAL'] = str(len(to_bal))
R['FX_REFUND_DEBT'] = str(len(to_debt))
P('  (b) 图外的格——模拟器读到 undefined，不提前返回，挂成对 0 号的进攻；引擎读图外格得到的也是 0 号（boatprobe 的 B010 #42）。这一步没有换')
P(f'  合计 {noff} 艘，{len(off_matches)} 局（{" ".join(sorted(off_matches)) or "无"}）')
P(f'  这条路上引擎照 0 号查、模拟器照 undefined 查的三样：船主和 0 号其实不敌对（引擎会转交，模拟器挂成进攻）{off_enemy0} 艘；'
  f'船主已经有一条对 0 号的进攻（引擎并进去，模拟器另开一栏）{off_had} 艘；船主没有空的进攻栏 {off_noslot} 艘')
R['FX_BOATS_OFF'] = str(noff)
R['FX_BOATS_OFF_MATCHES'] = str(len(off_matches))
R['FX_BOATS_OFF_EDGE'] = str(off_enemy0 + off_had)
R['FX_BOATS'] = str(nin + noff)
fired_boat_in = sorted(in_matches)
BP = [('A053', 1765, 32, 49071), ('A057', 2486, 93, 34985), ('B010', 3515, 42, 60), ('B010', 3823, 45, 172242), ('B010', 3900, 45, 190165)]
got = {(b_['matchId'], b_['t'], b_['p'], b_['troops']) for b_ in J['boats']}
hit = sum(1 for x in BP if x in got)
P(f'  boatprobe [BP-A]（线上引擎那一侧读到的 5 艘：局、走到头的拍、船主、兵）在 (a)(b) 两张表里的 {hit} 艘')
R['FX_BP_HIT'] = str(hit)
P()

# ---------- [FX-E]
P('[FX-E] 扫描表「要不要重扫」那一步两种规则不同的拍（不换的那一遍读到的）')
P('  局 | 次数 | 第一次的拍 | 那一拍扫描表条数 | 存活 | 第二名个人的地 | 32 拍缓存里还有地的队 | 方向')
nscan = 0
for m, a, b in nb:
    if not a['scanNotes']:
        continue
    x = a['scanNotes'][0]
    nscan += len(a['scanNotes'])
    dr = '模拟器不重扫、引擎重扫' if x['simSecond'] else '模拟器重扫、引擎不重扫'
    P(f'  {m} | {len(a["scanNotes"])} | {x["t"]} | {x["n"]} | {x["alive"]} | {x["simSecond"]} | {x["teamsLeft"]} | {dr}')
P(f'  合计 {nscan} 次，{len(fired_scan)} 局；全部录像里组队局走到那一步一共 {sum(a["scanReached"] for m, a, b in nb)} 次')
R['FX_SCAN_NOTES'] = str(nscan)
R['FX_SCAN_REACHED'] = str(sum(a['scanReached'] for m, a, b in nb))
P()
# ---------- [FX-F]
P('[FX-F] 那 5 艘船之后几拍船主的余额和欠账：重放器 对 boatprobe 在线上引擎里逐拍读到的（out/_cross/boatprobe.txt，清场以前入库的）')
bp_rows = {}
bp_path = os.path.join(OUT, 'boatprobe.txt')
if os.path.exists(bp_path):
    cur = None
    for ln in open(bp_path, encoding='utf-8'):
        mm = re.match(r'^== (\S+) 玩家 #(\d+)', ln)
        if mm:
            cur = (mm.group(1), int(mm.group(2)))
            continue
        mm = re.match(r'^\s+(\d+) \| (\d+) \| (\d+) \|', ln)
        if mm and cur:
            bp_rows[(cur[0], cur[1], int(mm.group(1)))] = (int(mm.group(2)), int(mm.group(3)))
    P('  局 | 船主 | 走到头的拍 | 比了几拍 | 不换：余额和欠账都相同的拍 | 两处都换：都相同的拍')
    tot = eq0 = eq1 = 0
    for m, t0, p, troops in BP:
        if m not in D or 'none' not in D[m] or 'both' not in D[m]:
            continue
        cells = []
        n = 0
        for arm in ('none', 'both'):
            x = next((z for z in D[m][arm]['boatNotes'] if z['t'] == t0 and z['p'] == p and z['troops'] == troops), None)
            k = e = 0
            for row in (x or {}).get('after') or []:
                eng = bp_rows.get((m, p, row[0]))
                if eng is None or len(row) < 4:
                    continue
                k += 1
                e += 1 if (row[1], row[3]) == eng else 0
            cells.append(e)
            n = k
        tot += n
        eq0 += cells[0]
        eq1 += cells[1]
        P(f'  {m} | #{p} | {t0} | {n} | {cells[0]} | {cells[1]}')
    P(f'  合计比了 {tot} 拍：不换 {eq0} 拍相同，两处都换 {eq1} 拍相同')
    R['FX_BP_TICKS'] = str(tot)
    R['FX_BP_NONE_EQ'] = str(eq0)
    R['FX_BP_BOTH_EQ'] = str(eq1)
else:
    P('  out/_cross/boatprobe.txt 不在，这一项跳过')
P()

# ---------- [FX-G]
P('[FX-G] A001 扫描表岔开的那一段：重放器 对 huskprobe 在线上引擎里逐拍读到的（out/_cross/huskprobe.txt [HP-A]、[HP-B]，清场以前入库的）')
P('  九项：随机数状态 / 扫描表条数 / 扫描表校验和 / 航线表条数 / 航线表校验和 / 终局提速 / 全场船数 / #11 的余额 / #11 的船数')
hp_path = os.path.join(OUT, 'huskprobe.txt')
if os.path.exists(hp_path) and 'A001' in D:
    eng_rows = {}
    eng_4780, sim_4780 = {}, {}
    HPA = {'随机数状态': 0, '扫描表条数': 1, '扫描表校验和': 2, '航线表条数': 3, '航线表校验和': 4, '终局提速': 5, '全场船数': 6, '被观察玩家的余额': 7, '被观察玩家的船数': 8}
    for ln in open(hp_path, encoding='utf-8'):
        mm = re.match(r'^\s+(\d+) \| ([\d /-]+) \| ([\d /-]+?)( \*)?$', ln)
        if mm:
            eng_rows[int(mm.group(1))] = [int(v) for v in mm.group(2).split(' / ')][:9]
            continue
        mm = re.match(r'^\s+(\S+) \| (\d+) 拍：引擎 (-?\d+)，模拟器 (-?\d+)', ln)
        if mm and mm.group(1) in HPA and int(mm.group(2)) == 4780:
            eng_4780[HPA[mm.group(1)]] = int(mm.group(3))
            sim_4780[HPA[mm.group(1)]] = int(mm.group(4))
    span = sorted(eng_rows)
    P(f'  [HP-B] 的 {len(span)} 拍（{span[0]}~{span[-1]}）× 九项；[HP-A] 里 4780 拍引擎和模拟器各 {len(eng_4780)} 项（第一次对不上落在这一拍的那几项）')
    P('  臂 | [HP-B]：九项都等于引擎读数的拍 / 比的拍 | 4780 拍：等于引擎读数的项 / 比的项 | 4780 拍：等于 huskprobe 里模拟器读数的项')
    for arm in ARMS:
        d = D['A001'].get(arm)
        if not d or not d.get('husk'):
            continue
        rows = {r[0]: r[1:] for r in d['husk']['rows']}
        n = sum(1 for t in span if t in rows)
        eq = sum(1 for t in span if t in rows and rows[t] == eng_rows[t])
        r4 = rows.get(4780)
        e4 = sum(1 for i, v in eng_4780.items() if r4 and r4[i] == v)
        s4 = sum(1 for i, v in sim_4780.items() if r4 and r4[i] == v)
        P(f'  {AN[arm]} | {eq} / {n} | {e4} / {len(eng_4780)} | {s4} / {len(sim_4780)}')
        R[f'FX_HP_{arm.upper()}_EQ'] = str(eq)
        R[f'FX_HP_{arm.upper()}_4780'] = str(e4)
        R[f'FX_HP_{arm.upper()}_4780SIM'] = str(s4)
        R['FX_HP_TICKS'] = str(n)
        R['FX_HP_4780_ITEMS'] = str(len(eng_4780))
    d = D['A001'].get('both')
    if d and d.get('husk'):
        rows = {r[0]: r[1:] for r in d['husk']['rows']}
        first = next((t for t in span if t in rows and rows[t][1] > 0), None)
        if first:
            P(f'  两处都换的那一遍，扫描表第一次有格子是 {first} 拍：{rows[first][1]} 条、校验和 {rows[first][2]}（引擎 {eng_rows[first][1]} 条、{eng_rows[first][2]}）；'
              f'4780 拍 #11 的余额 {rows[4780][7]}、船 {rows[4780][8]} 艘（引擎 {eng_4780.get(7)}、{eng_4780.get(8)}）')
else:
    P('  out/_cross/huskprobe.txt 不在，这一项跳过')
P()
P('读数时的限制：')
P('  1. 真值只有本包日志里本编队各号的地和兵。「不一致的行变成 0」说的是日志看得见的地方全对上了，不是全场 512 个玩家逐位对上了；后者要线上引擎的文件（engdiff），镜像里现在没有。和线上引擎直接比过的只有两小段：[FX-F] 那 5 艘船之后的几拍、[FX-G] A001 扫描表岔开前后的 20 拍。')
P('  2. 船那一步「读出来的主人号」用的是引擎公式里看得见的那一半（地形号 & 3）<< 3；公式里另外两个字节在没有主人的格上是不是总是 0，只有图边格的 4 次观察（boatprobe）。山、水两种格在这批录像里没有出现过。')
P('  3. 抵了欠账的那一艘（A021 #40）在线上引擎里怎么结算没有直接读过：是照同一类的两艘船（A053、A057：图边格、读出来 24、敌对）在引擎里的结算推的。')
P('  4. 这是检验根因找全了没有，不是给 src/sim 的补丁：包壳只在本脚本的对局对象实例上，src/sim 的文件和别的脚本的重演都没有动。')

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'fixprobe.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
J['rows'] = [dict(matchId=m, cohort=cohort.get(m), arms={arm: dict(val=d['val'], firstMism=d['firstMism'][0] if d['firstMism'] else None, endTick=d['endTick'],
                                                                  refHash=d['refHash'], events=len(d['events']), scanNotes=len(d['scanNotes']), scanReached=d['scanReached'],
                                                                  boatNotes=len(d['boatNotes'])) for arm, d in D[m].items()}) for m in mids]
with open(os.path.join(OUT, 'fixprobe.json'), 'w', encoding='utf-8') as f:
    json.dump(J, f, ensure_ascii=False)
if '-q' in sys.argv:
    print(f'fixprobe.py：{len(mids)} 局 → out/_cross/fixprobe.txt')
else:
    print('\n'.join(lines))
