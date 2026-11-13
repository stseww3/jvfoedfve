#!/usr/bin/env python3
# cloneprobe.py — 汇总 cloneprobe.mjs 的逐局输出（out/_run/cloneprobe/<局>.json）→ out/_cross/cloneprobe.txt / .json
#
# 量的是「在断面克隆、照录像续跑」和「不克隆一路重演」（下面叫参照重演）差多少；两条臂：
#   原样    clone() 返回的对象（原型是基类 Game）
#   恢复类  把拷贝的原型改回重放器的子类（TGame）
# 比的对象是参照重演，不是线上引擎；参照重演自己和线上引擎对不对得上，见 engdiff（[FA-E]：89 局里 86 局整局全场一致）。
# 这一项先读逐局原始输出 out/_run/engdiff/<局>.json；原始输出不在的时候（不入库），退回已入库的汇总：
# out/_cross/fidabl.json 的 engine.diverged（走偏的局）和 out/_cross/fidabl.txt [FA-E] 里这几局第一处不一致的拍。
# 同一个物理房间出了两份包的（两份录像是同一条指令流，短的那份是长的那份的前一段），按 roomKey 去重，只留录像长的那一份。
# t=0 断面是单独跑的一遍（clone0_batch.sh → <局>.t0.json，只重演到 630 拍），这里把它的两次克隆并到同一局的记录里。
#
#   python3 c136-review/agents/R08/scripts/cloneprobe.py
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'out', '_run')
OUT = os.path.join(HERE, '..', 'out', '_cross')
SRC = os.path.join(RUN, 'cloneprobe')
ARMS = (('class', '恢复类'), ('asis', '原样'))

lines = []


def P(s=''):
    lines.append(s)


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


cohort = {}
try:
    for mid, H, c in json.load(open(os.path.join(RUN, 'fidabl_list.json'), encoding='utf-8')):
        cohort[mid] = c
except Exception:
    pass

rows = []
killed = []
running = []
t0 = {}
for fn in sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []:
    if fn.endswith('.started'):
        # 开跑时留的记号（内容是开跑的时刻）：超过时间上限还在的 = 跑到一半被杀；没超过的 = 正在跑
        try:
            age = time.time() - int(open(os.path.join(SRC, fn)).read().strip()) / 1000
        except Exception:
            age = 1e9
        (killed if age > 960 else running).append(fn[:-8])
    elif fn.endswith('.t0.json'):
        t0[fn[:-8]] = json.load(open(os.path.join(SRC, fn), encoding='utf-8'))
    elif fn.endswith('.json'):
        rows.append(json.load(open(os.path.join(SRC, fn), encoding='utf-8')))
n_t0 = 0
for r in rows:
    z = t0.get(r['matchId'])
    if z:
        n_t0 += 1
        r['segs'] = [s for s in z['segs'] if s['T'] == 0] + r['segs']
if not rows:
    print('还没有逐局输出')
    sys.exit(0)

# 参照重演对本包日志快照的逐行核对（整局），去重以前先合计：和已入库的 engdiff 汇总（fidabl.json 的 engine.simLog）对一遍，
# 两边一样 = 这一轮读到的对局包和模拟器，重演出来的东西和入库那一轮逐行相同
FA = json.load(open(os.path.join(OUT, 'fidabl.json'), encoding='utf-8'))
val_n = sum(1 for r in rows if r.get('val'))
val_rows = sum(r['val']['rows'] for r in rows if r.get('val'))
val_both = sum(r['val']['both'] for r in rows if r.get('val'))
val_bad = sorted(r['matchId'] for r in rows if r.get('val') and r['val']['both'] != r['val']['rows'])
all_runs = len(rows)

# 按房间去重：同一个房间留录像最长的那一份
by_room = {}
for r in rows:
    by_room.setdefault(r.get('roomKey') or r['matchId'], []).append(r)
dups = []
rows = []
for key, grp in by_room.items():
    grp.sort(key=lambda r: (-r['endTick'], r['matchId']))
    rows.append(grp[0])
    for r in grp[1:]:
        dups.append((r['matchId'], r['endTick'], grp[0]['matchId'], grp[0]['endTick']))
rows.sort(key=lambda r: r['matchId'])

# 参照重演自己对线上引擎：engdiff 的整局结果（原始输出在就读原始输出，不在就读已入库的汇总）
eng = {}
eng_src = '逐局原始输出 out/_run/engdiff/'
if os.path.isdir(os.path.join(RUN, 'engdiff')):
    for r in rows:
        fp = os.path.join(RUN, 'engdiff', f"{r['matchId']}.json")
        if os.path.exists(fp):
            e = json.load(open(fp, encoding='utf-8'))
            eng[r['matchId']] = e.get('firstT') if e.get('nBad') else None
else:
    eng_src = '已入库的汇总 out/_cross/fidabl.json、fidabl.txt [FA-E]'
    first = dict((m, int(t)) for m, t in re.findall(r'^\s+(\w+)（真人 \d+，录像 \d+ 拍）：第一处 t=(\d+)', open(os.path.join(OUT, 'fidabl.txt'), encoding='utf-8').read(), re.M))
    div = FA['engine']['diverged']
    assert sorted(first) == sorted(div), (first, div)
    assert FA['engine']['matches'] == len(cohort), (FA['engine']['matches'], len(cohort))   # engdiff 比过的就是局单里的全部局
    for r in rows:
        if r['matchId'] in cohort:
            eng[r['matchId']] = first.get(r['matchId'])

AT = sorted({s['T'] for r in rows for s in r['segs']})
n_team = sum(1 for r in rows if r['teamGame'])
P('cloneprobe.py — 断面克隆续跑 对 不克隆一路重演（参照重演）；逐局输出 out/_run/cloneprobe/')
P('')
P('[CP-A] 覆盖')
P(f'  跑完的录像 {all_runs} 份（局单 {len(cohort)} 局，每局用自己的录像）；同一个房间出了两份的只留长的那一份，去掉 {len(dups)} 份'
  + ('（' + '；'.join(f'{a} 录像到 {ea} 拍，和 {b}（{eb} 拍）同房' for a, ea, b, eb in sorted(dups)) + '）' if dups else '') + f'；下面按 {len(rows)} 个房间算')
P(f'  参照重演对本包日志快照逐行核对（整局，去重以前 {val_n} 份合计）：地和兵都一致 {val_both} / {val_rows} 行'
  + (f"；有不一致的行的局 {len(val_bad)}：{' '.join(val_bad)}" if val_bad else '；没有不一致的行'))
P(f"  已入库的 engdiff 汇总 [FA-E]（{FA['engine']['matches']} 局）：{FA['engine']['simLog'][0]} / {FA['engine']['simLog'][1]} 行"
  + ('' if all_runs != FA['engine']['matches'] else '——两边' + ('相同' if [val_both, val_rows] == FA['engine']['simLog'] else '不相同')))
P(f'  参照重演对线上引擎的结果取自：{eng_src}')
P(f'  t=0 断面（出生期刚结束）是单独跑的一遍，只重演到 630 拍：跑完 {n_t0} 份，并在下面各表的第一行')
P(f"  房间 {len(rows)}（squad10 {sum(1 for r in rows if cohort.get(r['matchId']) == 'squad10')} / squad20 {sum(1 for r in rows if cohort.get(r['matchId']) == 'squad20')}；"
  f'组队 {n_team} / 自由混战 {len(rows) - n_team}）；参照重演整局和线上引擎全场一致的 {sum(1 for r in rows if eng.get(r["matchId"], 0) is None)} 个，'
  f'走偏过的 {sum(1 for r in rows if eng.get(r["matchId"]) is not None)} 个'
  + ('（' + '；'.join(f'{m} 从 {t} 拍' for m, t in sorted(eng.items()) if t is not None) + '）' if any(t is not None for t in eng.values()) else ''))
evt = [min(e[0] for e in r['events']) for r in rows if r['events']]
P(f"  参照重演里有过猎杀 / 终局提速事件的 {len(evt)} 个房间" + (f'（第一次事件最早 {min(evt)} 拍）' if evt else ''))
for T in AT:
    P(f"  在 {T} 拍克隆的房间 {sum(1 for r in rows if any(s['T'] == T for s in r['segs']))}（录像不到这一拍的不克隆）")
if killed:
    P(f"  跑到一半被时间上限杀掉、没有输出的局 {len(killed)}：{' '.join(sorted(killed))}")
P('')

summary = {}
for arm, cn in ARMS:
    tag = 'CP-B' if arm == 'class' else 'CP-C'
    P(f"[{tag}] {cn}臂（{'把拷贝的原型改回 TGame，只考状态拷全了没有' if arm == 'class' else 'clone() 返回什么就用什么，原型是基类 Game'}）")
    P('  断面 | 克隆的房间 | 克隆那一拍全部字段相等 | 克隆抛错 | 续跑中抛错 | 续跑到段末、全场 512 个玩家的地、兵、存活逐拍相等 | 其中段末全部字段也相等 | 地或兵走偏 | 续跑的拍数合计')
    for T in AT:
        S = [(r, s) for r in rows for s in r['segs'] if s['T'] == T and s['arm'] == arm]
        n = len(S)
        clone_eq = sum(1 for _, s in S if not s['cloneErr'] and not (s.get('diffAtClone') or []))
        cerr = sum(1 for _, s in S if s['cloneErr'])
        rerr = sum(1 for _, s in S if s['err'])
        ok = [(r, s) for r, s in S if not s['cloneErr'] and not s['err'] and s['firstVis'] is None]
        ok_all = sum(1 for _, s in ok if not s['diffAtEnd'])
        bad = [(r, s) for r, s in S if s['firstVis'] is not None]
        ticks = sum((s['endT'] or T) - T for _, s in S if not s['cloneErr'])
        P(f'  {T} | {n} | {clone_eq} | {cerr} | {rerr} | {len(ok)} | {ok_all} | {len(bad)} | {ticks}')
        summary[(arm, T)] = dict(n=n, ok=len(ok), okAll=ok_all, bad=len(bad), err=cerr + rerr, ticks=ticks, hidOnly=len(ok) - ok_all)
        if bad:
            lag_all = [s['firstVis'] - s['firstHid'] for _, s in bad if s['firstHid'] is not None]
            summary[(arm, T)].update(firstMin=min(s['firstVis'] for _, s in bad), firstMed=q([s['firstVis'] for _, s in bad], .5), firstMax=max(s['firstVis'] for _, s in bad),
                                     lagN=len(lag_all), lagMin=min(lag_all) if lag_all else '–', lagMax=max(lag_all) if lag_all else '–', lagMed=q(lag_all, .5) if lag_all else '–')
        for r, s in S:
            if s['cloneErr']:
                P(f"    克隆抛错 {r['matchId']}：{s['cloneErr']}")
            if s['err']:
                P(f"    续跑抛错 {r['matchId']} {s['errT']} 拍：{s['err']}")
        hid_only = [(r, s) for r, s in ok if s['firstHid'] is not None or s['diffAtEnd']]
        if hid_only:
            P(f"    地和兵到段末都相等、但别的状态不等的 {len(hid_only)} 个房间：" + '；'.join(
                f"{r['matchId']}（{'第一次不等 ' + str(s['firstHid']) + ' 拍：' + '、'.join(s['hid']) if s['firstHid'] is not None else '逐拍比的几项都相等'}；段末不等的字段 {len(s['diffAtEnd'])} 个：{' '.join(s['diffAtEnd'][:8])}{' …' if len(s['diffAtEnd']) > 8 else ''}）"
                for r, s in hid_only))
        if bad:
            lag = [s['firstVis'] - s['firstHid'] for _, s in bad if s['firstHid'] is not None]
            P(f"    走偏的 {len(bad)} 个房间：第一处地或兵不等的拍 最早 {min(s['firstVis'] for _, s in bad)}、中位 {q([s['firstVis'] for _, s in bad], .5)}、最晚 {max(s['firstVis'] for _, s in bad)}；"
              f"从克隆算起隔了 最短 {min(s['firstVis'] - T for _, s in bad)} 拍、中位 {q([s['firstVis'] - T for _, s in bad], .5)} 拍；"
              + (f"在那之前别的状态先不等的 {len(lag)} 个，早 {min(lag)}~{max(lag)} 拍（中位 {q(lag, .5)}）" if lag else '在那之前逐拍比的几项状态都相等'))
    if arm == 'asis':
        stale = sum(1 for r in rows for s in r['segs'] if s['arm'] == 'asis' and s.get('subOnlyStale'))
        tot = sum(1 for r in rows for s in r['segs'] if s['arm'] == 'asis' and not s['cloneErr'])
        P(f'  子类自己的两个字段（各队总地缓存 teamCache、它的相位 teamW0）在这条臂里停在克隆那一拍的值：{stale} / {tot} 次克隆（基类的方法不读也不写，上面的「字段相等」不算它们）')
    tot_n = sum(summary[(arm, T)]['n'] for T in AT)
    tot_ok = sum(summary[(arm, T)]['okAll'] for T in AT)
    tot_err = sum(summary[(arm, T)]['err'] for T in AT)
    tot_ticks = sum(summary[(arm, T)]['ticks'] for T in AT)
    summary[(arm, 'ALL')] = dict(n=tot_n, okAll=tot_ok, err=tot_err, ticks=tot_ticks)
    P(f'  合计：{tot_n} 次克隆，续跑 {tot_ticks} 拍；到段末全场逐拍相等、全部字段也相等的 {tot_ok} 次；抛错 {tot_err} 次')
    P('')

P('[CP-D] 原样臂，1500 拍以后（1500 和 4284 两次克隆合起来看：有一次不等就算）：参照重演里有没有猎杀 / 终局提速事件 × 拷贝走没走偏')
P('  （两次克隆各自从参照重演当拍的状态出发，不是一条从 1500 拍一路跑到局末的拷贝；630 拍那一次克隆续跑到 1500 拍，这一段参照重演里没有事件，见 [CP-C] 第一行）')
tab = {}
detail = []
for r in rows:
    S = [s for s in r['segs'] if s['arm'] == 'asis' and s['T'] >= 1500 and not s['cloneErr']]
    if not S:
        continue
    has_ev = bool(r['events'])
    vis = [s['firstVis'] for s in S if s['firstVis'] is not None]
    hid = [s['firstHid'] for s in S if s['firstHid'] is not None]
    err = [s['errT'] for s in S if s['err']]
    kind = '地或兵走偏' if vis else '抛错' if err else '只有别的状态不等' if hid or any(s['diffAtEnd'] for s in S) else '一致'
    tab[(has_ev, kind)] = tab.get((has_ev, kind), 0) + 1
    detail.append((r, kind, min(vis) if vis else None, min(hid) if hid else None))
kinds = ['一致', '只有别的状态不等', '地或兵走偏', '抛错']
P('  参照重演 | ' + ' | '.join(kinds) + ' | 合计')
for has_ev in (True, False):
    P(f"  {'有事件' if has_ev else '没有事件'} | " + ' | '.join(str(tab.get((has_ev, k), 0)) for k in kinds) + f' | {sum(tab.get((has_ev, k), 0) for k in kinds)}')
n_ev = sum(tab.get((True, k), 0) for k in kinds)
n_noev = sum(tab.get((False, k), 0) for k in kinds)
split_ev = tab.get((True, '只有别的状态不等'), 0) + tab.get((True, '地或兵走偏'), 0)
P(f"  有事件的 {n_ev} 个房间里，拷贝和参照重演分开过的（地、兵，或者看不见的状态）{split_ev} 个：只比地和兵看得出来的 {tab.get((True, '地或兵走偏'), 0)} 个，"
  f"要比看不见的状态才看得出来的 {tab.get((True, '只有别的状态不等'), 0)} 个；到录像结束都没有分开的 {tab.get((True, '一致'), 0)} 个"
  + ('（' + '、'.join(sorted(r['matchId'] for r, k, v, h in detail if k == '一致' and r['events'])) + '）' if tab.get((True, '一致'), 0) else ''))
first_hid_kind = {}
for r in rows:
    for s_ in r['segs']:
        if s_['arm'] == 'asis' and s_['T'] >= 1500 and s_.get('hid'):
            for name in s_['hid']:
                first_hid_kind[name] = first_hid_kind.get(name, 0) + 1
if first_hid_kind:
    P('  看不见的状态里先不等的是哪一项（按克隆次数，一次可以有几项）：' + '；'.join(f'{k} {v}' for k, v in sorted(first_hid_kind.items(), key=lambda kv: -kv[1])))
ev_bad = [(r, v, h) for r, k, v, h in detail if k == '地或兵走偏']
if ev_bad:
    d1 = [(h if h is not None else v) - min(e[0] for e in r['events']) for r, v, h in ev_bad if r['events']]
    if d1:
        P(f'  走偏的 {len(ev_bad)} 个房间里，拷贝第一次和参照重演不等（含看不见的状态）比参照重演的第一次事件 晚 {min(d1)}~{max(d1)} 拍（中位 {q(d1, .5)}；负数 = 早）')
    engok = sum(1 for r, v, h in ev_bad if eng.get(r['matchId'], 0) is None)
    P(f'  这 {len(ev_bad)} 个房间里参照重演整局和线上引擎全场一致的 {engok} 个——在这些房间上，拷贝和参照重演不等也就是和线上引擎不等')
P('')

P('[CP-E] 「只剩一个队有地以后重不重扫无主地」这一处的暴露面（照模拟器自己的状态推的，没有跑线上引擎）')
team = [r for r in rows if r['teamGame']]
gap = [r for r in team if r.get('gap')]
sg = [r for r in team if r.get('scanGap')]
P(f'  组队房间 {len(team)}；录像里出现过「还有地的队只剩一个、第二名个人还有地」的 {len(gap)} 个；其中模拟器走到过「要不要重扫」那一步、按线上引擎的规则该重扫而模拟器没有重扫的 {len(sg)} 个')
if gap:
    why = {'扫描表是满的（512 条，两边都不扫）': 0, '第一轮还没扫完': 0, '别的（没等到判断的那一拍，或者榜首不是内置 AI）': 0}
    for r in gap:
        if r.get('scanGap'):
            continue
        g_ = r['gap']
        if g_['scanLen'] >= 512:
            why['扫描表是满的（512 条，两边都不扫）'] += 1
        elif g_['scanPass'] < 300:
            why['第一轮还没扫完'] += 1
        else:
            why['别的（没等到判断的那一拍，或者榜首不是内置 AI）'] += 1
    P(f'  没有走到那一步的 {len(gap) - len(sg)} 个，「只剩一个队有地」第一次出现那一拍的状况：' + '；'.join(f'{k} {v}' for k, v in why.items()))
if gap:
    rest = [r['endTick'] - r['gap']['t'] for r in gap]
    P(f'  出现以后录像还剩的拍数：最短 {min(rest)}、中位 {q(rest, .5)}、最长 {max(rest)}')
if sg:
    P('  局 | 只剩一个队有地（第一次） | 该重扫而没重扫（第一次） | 那一拍模拟器扫描表的条数 | 录像末拍 | 之后还剩多少拍 | 参照重演对线上引擎')
    for r in sorted(sg, key=lambda r: r['matchId']):
        e = eng.get(r['matchId'], 0)
        P(f"  {r['matchId']} | {r['gap']['t']} | {r['scanGap']['t']} | {r['scanGap']['scanLen']} | {r['endTick']} | {r['endTick'] - r['scanGap']['t']} | "
          + ('没有比过' if r['matchId'] not in eng else '整局全场一致' if e is None else f'{e} 拍走偏'))
    P('  对照：A001 上 huskprobe 直接从线上引擎读到的是 4672 拍条件开始不同、4678 拍扫描表里有了格子、4780 拍兵不等 [HP-F]。')
    quiet = [r for r in sg if r['matchId'] in eng and eng[r['matchId']] is None]
    P(f'  这 {len(sg)} 个房间里，地和兵整局都和线上引擎一致的 {len(quiet)} 个' + ('：这些房间里扫描表按推算已经分开，但到录像结束都没有在地和兵上显出来。' if quiet else '。'))
P('')

P('[CP-F] 逐个房间：局 | 编队档 | 真人 | 队数 | 录像末拍 | 参照重演的事件（第一次猎杀 / 第一次提速） | 各断面两条臂（恢复类 / 原样）：一致到哪一拍，或第一处不等的拍（h = 看不见的状态先不等的拍）')
for r in sorted(rows, key=lambda r: r['matchId']):
    hunt = next((e[0] for e in r['events'] if e[1] == 'hunt'), None)
    fast = next((e[0] for e in r['events'] if e[1] == 'fast'), None)
    cells = []
    for T in AT:
        part = []
        for arm, cn in ARMS:
            s = next((s for s in r['segs'] if s['T'] == T and s['arm'] == arm), None)
            if s is None:
                continue
            if s['cloneErr']:
                part.append(f'{cn} 克隆抛错')
            elif s['err']:
                part.append(f"{cn} {s['errT']} 拍抛错")
            elif s['firstVis'] is not None:
                part.append(f"{cn} {s['firstVis']} 拍不等" + (f"（h {s['firstHid']}）" if s['firstHid'] is not None else ''))
            else:
                part.append(f"{cn} 一致到 {s['endT']}" + (f"（h {s['firstHid']}）" if s['firstHid'] is not None else '') + ('' if not s['diffAtEnd'] else f"（段末 {len(s['diffAtEnd'])} 个字段不等）"))
        if part:
            cells.append(f'{T}：' + '，'.join(part))
    P(f"  {r['matchId']} | {cohort.get(r['matchId'], '?')} | {r['H']} | {r['nTeams']} | {r['endTick']} | {hunt if hunt is not None else '–'} / {fast if fast is not None else '–'} | " + '；'.join(cells))

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'cloneprobe.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
rep = {}
for (arm, T), v in summary.items():
    for k, x in v.items():
        rep[f'CP_{arm.upper()}_{T}_{k.upper()}'] = str(x)
rep['CP_N'] = str(len(rows))
rep['CP_DUPS'] = str(len(dups))
rep['CP_EVENTS'] = str(len(evt))
rep['CP_D_EV_N'] = str(n_ev)
rep['CP_D_EV_OK'] = str(tab.get((True, '一致'), 0))
rep['CP_D_EV_HID'] = str(tab.get((True, '只有别的状态不等'), 0))
rep['CP_D_EV_BAD'] = str(tab.get((True, '地或兵走偏'), 0))
rep['CP_D_EV_SPLIT'] = str(split_ev)
rep['CP_D_NOEV_N'] = str(n_noev)
rep['CP_D_NOEV_OK'] = str(tab.get((False, '一致'), 0))
rep['CP_D_BAD_ENGOK'] = str(sum(1 for r, v, h in ev_bad if eng.get(r['matchId'], 0) is None))
rep['CP_STALE'] = str(stale)
rep['CP_STALE_TOT'] = str(tot)
rep['CP_TEAM'] = str(len(team))
rep['CP_GAP'] = str(len(gap))
rep['CP_SCANGAP'] = str(len(sg))
rep['CP_RUNS'] = str(all_runs)
rep['CP_VAL_ROWS'] = str(val_rows)
rep['CP_VAL_BOTH'] = str(val_both)
json.dump({'report': rep, 'n': len(rows), 'killed': sorted(killed), 'running': sorted(running)}, open(os.path.join(OUT, 'cloneprobe.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(lines[:60]))
