#!/usr/bin/env python3
# hidstate.py — 汇总 hidstate.mjs 的逐局输出（out/_run/hidstate/<局>.json）→ out/_cross/hidstate.txt / .json
#
# 线上引擎原文 对 模拟器，整局逐拍比九项「看不见的状态」（验收条款 R7 的现状）。样本是固定的几局，不是全量（见 fid_batch.sh 的 HID_SAMPLE）。
# 地和兵（看得见的状态）两边对不对得上，用的是 engdiff 的结果（全场每个玩家，每 10 拍）。
#
#   python3 c136-review/agents/R08/scripts/hidstate.py
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'out', '_run')
OUT = os.path.join(HERE, '..', 'out', '_cross')
SRC = os.path.join(RUN, 'hidstate')
FIELDS = ['随机数状态', '扫描表条数', '扫描表校验和', '航线表条数', '航线表校验和', '终局提速', '全场船数', '欠账', '还有地的队数']

lines = []


def P(s=''):
    lines.append(s)


cohort = {}
try:
    for mid, H, c in json.load(open(os.path.join(RUN, 'fidabl_list.json'), encoding='utf-8')):
        cohort[mid] = c
except Exception:
    pass

rows, killed, running = [], [], []
for fn in sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []:
    if fn.endswith('.started'):
        try:
            age = time.time() - int(open(os.path.join(SRC, fn)).read().strip()) / 1000
        except Exception:
            age = 1e9
        (killed if age > 660 else running).append(fn[:-8])
    elif fn.endswith('.json'):
        rows.append(json.load(open(os.path.join(SRC, fn), encoding='utf-8')))
if not rows:
    print('还没有逐局输出')
    sys.exit(0)

vis = {}
for r in rows:
    fp = os.path.join(RUN, 'engdiff', f"{r['matchId']}.json")
    if os.path.exists(fp):
        e = json.load(open(fp, encoding='utf-8'))
        vis[r['matchId']] = e.get('firstT') if e.get('nBad') else None


def hid_first(r):
    ts = [v['t'] for v in r['first'].values() if v]
    return min(ts) if ts else None


P('hidstate.py — 线上引擎原文 对 模拟器：整局逐拍比九项看不见的状态；逐局输出 out/_run/hidstate/')
P('')
P('[HS-A] 样本和覆盖')
P(f"  跑完的局 {len(rows)}（squad10 {sum(1 for r in rows if cohort.get(r['matchId']) == 'squad10')} / squad20 {sum(1 for r in rows if cohort.get(r['matchId']) == 'squad20')}；"
  f"组队局 {sum(1 for r in rows if r['teamGame'])} / 自由混战 {sum(1 for r in rows if not r['teamGame'])}）；并排的拍数合计 {sum(r['nCmp'] for r in rows)}")
if killed:
    P(f"  跑到一半被时间上限杀掉、没有输出的局 {len(killed)}：{' '.join(sorted(killed))}")
P('  局 | 编队档 | 真人 | 队数 | 并排的拍 | 地和兵（engdiff，每 10 拍全场）| 九项看不见的状态')
for r in rows:
    m = r['matchId']
    v = vis.get(m, 0)
    h = hid_first(r)
    bad = [f"{k} {x['t']} 拍" for k, x in r['first'].items() if x]
    P(f"  {m} | {cohort.get(m, '?')} | {r['H']} | {r['nTeams']} | {r['nCmp']}（{r['t0']}~{r['t1']}） | "
      + ('没有比过' if m not in vis else '整局一致' if v is None else f'{v} 拍走偏') + ' | '
      + ('整局逐拍相等' if h is None else '第一次不等：' + '；'.join(bad)))
P('')

P('[HS-B] 逐项：整局逐拍相等的局数 / 样本局数；不等的局第一次不等的拍')
for k in FIELDS:
    bad = [(r['matchId'], r['first'][k]) for r in rows if r['first'].get(k)]
    P(f"  {k} | {len(rows) - len(bad)} / {len(rows)}" + ('' if not bad else ' | ' + '；'.join(
        f"{m} {x['t']} 拍" + ('' if x['eng'] is None else f"（引擎 {x['eng']}，模拟器 {x['sim']}）") + f"，不等的拍数 {x['nBad']}" for m, x in bad)))
P(f"  这几项不是摆设：样本里扫描表有内容的拍数合计 {sum(r['scanTicks'] for r in rows)}；航线表最多 {max(r['routeMax'] for r in rows)} 条；同时在海上的船最多 {max(r['boatMax'] for r in rows)} 艘；"
  f"有人欠账的拍数合计 引擎 {sum(r['debtTicksE'] for r in rows)} / 模拟器 {sum(r['debtTicksS'] for r in rows)}")
P('')

P('[HS-C] 欠账第一次不等的那一拍：谁、两边各欠多少')
any_debt = False
for r in rows:
    if r.get('debtDiff'):
        any_debt = True
        x = r['first']['欠账']
        P(f"  {r['matchId']} {x['t']} 拍（之后不等的拍数 {x['nBad']}）：" + '；'.join(f"#{p}「{name}」引擎 {a} / 模拟器 {b}" for p, name, a, b in r['debtDiff']))
if not any_debt:
    P('  样本里没有欠账不等的局')
P('')

P('[HS-D] 看不见的状态先不等、地和兵后不等（或者一直没显出来）')
lead = []
silent = []
for r in rows:
    m = r['matchId']
    h = hid_first(r)
    if h is None:
        continue
    v = vis.get(m, 0)
    which = '、'.join(k for k, x in r['first'].items() if x and x['t'] == h)
    if m in vis and v is None:
        silent.append(m)
        P(f'  {m}：{h} 拍 {which} 不等；地和兵到录像结束（{r["t1"]} 拍）都没有显出来')
    elif m in vis:
        lead.append(v - h)
        P(f'  {m}：{h} 拍 {which} 不等；地和兵 {v} 拍走偏（晚 {v - h} 拍）')
    else:
        P(f'  {m}：{h} 拍 {which} 不等；地和兵没有比过')
n_clean = sum(1 for r in rows if hid_first(r) is None)
P(f'  合计：九项整局逐拍相等的 {n_clean} / {len(rows)} 局；看不见的状态不等、地和兵没显出来的 {len(silent)} 局；先于地和兵不等的 {len(lead)} 局')

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'hidstate.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
json.dump({'n': len(rows), 'clean': n_clean, 'silent': silent, 'killed': sorted(killed), 'running': sorted(running)},
          open(os.path.join(OUT, 'hidstate.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(lines))
