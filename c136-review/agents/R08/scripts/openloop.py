#!/usr/bin/env python3
# openloop.py — 汇总 openloop.mjs 的逐局输出（out/_run/openloop/<局>.json、<局>.plain.json）→ out/_cross/openloop.txt / .json
#
# 量的是开环可信期（会审稿验收条款 S5）：在 t=0 / 630 / 1500 / 4284 四个断面上，本编队换一种走法、别人照录像走，
# 别的真人的录像陆攻有多少条「生效 / 没生效」和历史不一样（翻面），按断面后 0~270 / 270~630 / 630~870 拍分窗。
# 两条臂都不带任何规则：wj 把本编队的录像指令推迟 7~19 拍（地板）；idle 本编队一条指令都不下。
# 单位是「录像」：同一个房间出了两份包的，两份包里的本编队不是同一批号，是两个不同的试验，都算。
# 录像没走满的窗，有几条算几条（和 cfprobe [CF-F] 同一口径）；逐份的分位数只用那个窗里别人的陆攻 ≥20 条的录像。
#
# 量法自己的四道检查（[OL-B]）：
#   1. 对照臂（拷贝原样照录像走）必须和参照重演逐条相同、段末全部字段相等；
#   2. 参照重演的校验和，带拷贝跑和不放拷贝跑（<局>.plain.json）必须相同；
#   3. 参照重演对本包日志快照的核对行数、猎杀 / 终局提速事件表、结束拍，和 cloneprobe 那一遍（out/_run/cloneprobe/<局>.json）相同；
#   4. t=630 断面的两条臂，和清场以前已入库的 cfprobe 汇总（out/_cross/cfprobe.json 的逐局行；那边每条臂都是从头重演）逐局逐窗相同。
# 3、4 两项的对照文件不在的时候跳过并写明。
#
#   python3 c136-review/agents/R08/scripts/openloop.py
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, '..', 'out', '_run')
OUT = os.path.join(HERE, '..', 'out', '_cross')
SRC = os.path.join(RUN, 'openloop')
SECTIONS = [0, 630, 1500, 4284]
WN = ['0~270', '270~630', '630~870']
WEND = [270, 630, 870]
ARMS = (('wj', '录像指令再推迟 7~19 拍（地板）'), ('idle', '一条指令都不下'))
MINN = 20

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
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def pc(a, b, nd=1):
    return '—' if not b else f'{100 * a / b:.{nd}f}%'


def pf(x, nd=1):
    return '—' if x is None else f'{100 * x:.{nd}f}%'


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

rows = []
plain = {}
killed = []
running = []
for fn in sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []:
    fp = os.path.join(SRC, fn)
    if fn.endswith('.started'):
        try:
            age = time.time() - int(open(fp).read().strip()) / 1000
        except Exception:
            age = 1e9
        (killed if age > 360 else running).append(fn[:-len('.started')])
    elif fn.endswith('.plain.json'):
        d = load(fp)
        if d:
            plain[d['matchId']] = d
    elif fn.endswith('.json'):
        d = load(fp)
        if d:
            rows.append(d)
rows.sort(key=lambda d: order.index(d['matchId']) if d['matchId'] in order else 10 ** 6)
R = {}
J = {'report': R}


def seg(d, T, arm):
    for s in d['segs']:
        if s['T'] == T and s['arm'] == arm:
            return s
    return None


have = [d for d in rows if d.get('own')]
noown = [d['matchId'] for d in rows if not d.get('own')]
rooms = len({d['roomKey'] for d in have})
P('openloop：四个断面上的开环可信期——本编队换一种走法、别人照录像走，别的真人的录像陆攻有多少条「生效 / 没生效」和历史不一样')
P('（两条臂都不带规则；比的对象是不克隆、照录像一路走的参照重演；只用模拟器。脚本 openloop.mjs → openloop.py）')
P()

# ---------- [OL-A]
P('[OL-A] 覆盖')
P(f'  局单 {len(order)} 份录像；有输出的 {len(rows)} 份；认出本编队的 {len(have)} 份（{rooms} 个房间；'
  f'squad10 {sum(1 for d in have if cohort.get(d["matchId"]) == "squad10")} / squad20 {sum(1 for d in have if cohort.get(d["matchId"]) == "squad20")}）'
  + (f'；没有认出本编队的：{" ".join(noown)}' if noown else ''))
if killed or running:
    P(f'  跑到一半被时间上限杀掉的：{" ".join(killed) or "无"}；正在跑的：{" ".join(running) or "无"}')
R['OL_RUNS'] = str(len(have))
R['OL_ROOMS'] = str(rooms)
P('  断面 | 做了克隆的录像 | 870 拍走满的 | 断面那一拍别的真人还在场的人数（中位）| 本编队还在场的号数（中位）| 各窗里别人的陆攻 ≥20 条的录像：0~270 / 270~630 / 630~870')
errs = []
for T in SECTIONS:
    ss = [(d, seg(d, T, 'idle')) for d in have]
    ss = [(d, s) for d, s in ss if s]
    full = sum(1 for d, s in ss if s['why'] == '走满')
    nP = q([s['at']['nP'] for d, s in ss], 0.5)
    oo = q([s['at']['ownOn'] for d, s in ss], 0.5)
    m = [sum(1 for d, s in ss if s['n'][k] >= MINN) for k in range(3)]
    P(f'  t={T} | {len(ss)} | {full} | {nP:.0f} | {oo:.0f} | {m[0]} / {m[1]} / {m[2]}')
    R[f'OL_{T}_N'] = str(len(ss))
    R[f'OL_{T}_FULL'] = str(full)
    R[f'OL_{T}_OTHERS'] = f'{nP:.0f}'
    R[f'OL_{T}_OWNON'] = f'{oo:.0f}'
    for d in have:
        for s in d['segs']:
            if s['T'] == T and (s.get('cloneErr') or s.get('err')):
                errs.append(f'{d["matchId"]} t={T} {s["arm"]}：{s.get("cloneErr") or s.get("err")}')
nseg = sum(len(d['segs']) for d in have)
P(f'  拷贝一共 {nseg} 份（每个断面 3 份：对照 / 推迟 / 不下）；克隆或续跑抛错的 {len(errs)} 份' + (('：' + '；'.join(errs[:6])) if errs else ''))
R['OL_SEGS'] = str(nseg)
R['OL_ERRS'] = str(len(errs))
P()

# ---------- [OL-B]
P('[OL-B] 量法自己的检查')
ctl = [(d, s) for d in have for s in d['segs'] if s['arm'] == 'ctl']
ctl_n = sum(sum(s['n']) for d, s in ctl)
ctl_flip = sum(sum(s['flip']) for d, s in ctl)
# clone.js 里登记为「每次调用自己清零的临时缓冲区」的字段：平时原对象和拷贝共用同一块（比不出差别）；
# 克隆以后才第一次分配的（bfsCost：真人发船寻路用，每次调用开头整块清零）两边各有一块，内容是各自最后一次调用留下的，不是对局状态。
SCRATCH = {'cand', 'frontCopy', 'mark', 'scratchList', 'tgt', 'bfsCost', 'spawnTiles'}
ctl_bad = [f'{d["matchId"]}@{s["T"]}' for d, s in ctl if sum(s['flip']) or [k for k in (s.get('ctlDiff') or []) if k not in SCRATCH] or s.get('err') or s.get('cloneErr')]
ctl_scr = [f'{d["matchId"]}@{s["T"]}（{" ".join(s["ctlDiff"])}）' for d, s in ctl if (s.get('ctlDiff') or []) and all(k in SCRATCH for k in s['ctlDiff'])]
P(f'  1. 对照臂（拷贝原样照录像走）：{len(ctl)} 份拷贝，别人的陆攻 {ctl_n} 条逐条和参照重演比，翻面 {ctl_flip} 条；'
  f'段末全部字段逐个比，对局状态有不等的 {len(ctl_bad)} 份' + (('：' + ' '.join(ctl_bad[:10])) if ctl_bad else '')
  + f'；只有临时缓冲区不等的 {len(ctl_scr)} 份' + (('：' + ' '.join(ctl_scr[:10])) if ctl_scr else '')
  + '（真人发船寻路的那块缓冲区克隆以后才第一次分配，两边各有一块；每次调用开头整块清零，不带对局状态）')
R['OL_CTL_SCRATCH'] = str(len(ctl_scr))
R['OL_CTL_N'] = str(len(ctl))
R['OL_CTL_CMDS'] = str(ctl_n)
R['OL_CTL_FLIP'] = str(ctl_flip)
R['OL_CTL_BAD'] = str(len(ctl_bad))
both = [(d, plain[d['matchId']]) for d in rows if d['matchId'] in plain]
same = [1 for a, b in both if a['refHash'] == b['refHash'] and a['refHashN'] == b['refHashN'] and a['endTick'] == b['endTick']]
bad = [a['matchId'] for a, b in both if not (a['refHash'] == b['refHash'] and a['refHashN'] == b['refHashN'] and a['endTick'] == b['endTick'])]
P(f'  2. 参照重演的校验和（每 10 拍全场 512 个玩家的地和兵）：带拷贝跑和不放拷贝跑都有的 {len(both)} 份录像，相同的 {len(same)} 份'
  + (('；不同的：' + ' '.join(bad)) if bad else '') + f'（合计 {sum(a["refHashN"] for a, b in both)} 个取样拍）')
R['OL_HASH_N'] = str(len(both))
R['OL_HASH_OK'] = str(len(same))
cp_n = cp_ok = 0
cp_bad = []
vr = vb = 0
for d in rows:
    c = load(os.path.join(RUN, 'cloneprobe', d['matchId'] + '.json'))
    if d.get('val'):
        vr += d['val']['rows']
        vb += d['val']['both']
    if not c:
        continue
    cp_n += 1
    # cloneprobe 的事件表只存了 [拍, 哪一种]
    if c.get('val') == d.get('val') and c.get('events') == [e[:2] for e in d.get('events') or []] and c.get('endTick') == d.get('endTick'):
        cp_ok += 1
    else:
        cp_bad.append(d['matchId'])
if cp_n:
    P(f'  3. 参照重演对本包日志快照的核对行数、猎杀 / 终局提速事件表、结束拍，和 cloneprobe 那一遍比：{cp_n} 份录像，三样都相同的 {cp_ok} 份'
      + (('；不同的：' + ' '.join(cp_bad)) if cp_bad else '') + f'；核对行合计 {vb} / {vr} 行逐位相同')
else:
    P(f'  3. cloneprobe 的逐局输出不在（不入库），这一项跳过；参照重演对本包日志快照 {vb} / {vr} 行逐位相同')
R['OL_CP_N'] = str(cp_n)
R['OL_CP_OK'] = str(cp_ok)
R['OL_VAL_ROWS'] = str(vr)
R['OL_VAL_BOTH'] = str(vb)
CF = load(os.path.join(OUT, 'cfprobe.json'))
if CF and CF.get('rows'):
    cf = {r['matchId']: r for r in CF['rows']}
    n = 0
    okk = {'idle': 0, 'wj': 0}
    own_ok = 0
    diff = []
    for d in have:
        r = cf.get(d['matchId'])
        if not r:
            continue
        n += 1
        # cfprobe 逐局行里 ownProbe 是那一遍重演认出来的本编队号数（own 是和 xtruth 的名单取交集以后的）
        if r.get('ownProbe') == d['own']:
            own_ok += 1
        else:
            diff.append(f'{d["matchId"]} 本编队号数 {r.get("ownProbe")}→{d["own"]}')
        for arm in ('idle', 'wj'):
            s = seg(d, 630, arm)
            mine = [[s['n'][k], s['flip'][k], s['down'][k], s['up'][k]] for k in range(3)] if s else None
            if mine == r['div'][arm]['win']:
                okk[arm] += 1
            else:
                diff.append(f'{d["matchId"]} {arm} {r["div"][arm]["win"]}→{mine}')
    only_cf = sorted(set(cf) - {d['matchId'] for d in have})
    only_me = sorted({d['matchId'] for d in have if seg(d, 630, 'idle')} - set(cf))
    P(f'  4. t=630 断面和已入库的 cfprobe 逐局行比（那边每条臂从头重演一遍，这边是克隆）：两边都有的 {n} 份录像；本编队号数相同 {own_ok} 份；'
      f'三个窗的条数、翻面数、两个方向全部相同：不下指令臂 {okk["idle"]} 份、推迟臂 {okk["wj"]} 份')
    if diff:
        P('     不同的：' + '；'.join(diff[:12]))
    P(f'     只在 cfprobe 里的：{" ".join(only_cf) or "无"}；只在这边的（cfprobe 的汇总不收录像不到 900 拍、对不上日志或者没有野人的局）：{" ".join(only_me) or "无"}')
    R['OL_CF_N'] = str(n)
    R['OL_CF_IDLE_OK'] = str(okk['idle'])
    R['OL_CF_WJ_OK'] = str(okk['wj'])
    R['OL_CF_OWN_OK'] = str(own_ok)
else:
    P('  4. out/_cross/cfprobe.json 不在，这一项跳过')
P()

# ---------- [OL-C]
P('[OL-C] 别的真人的录像陆攻「生效 / 没生效」翻面的占比（合计翻面 ÷ 合计条数；括号里：逐份录像的中位 / P90｜合计条数｜够 20 条的录像数）')
J['main'] = {}
for T in SECTIONS:
    P(f'  断面 t={T}')
    P('    臂 | 断面后 ' + ' | '.join(WN))
    J['main'][T] = {}
    for arm, an in ARMS:
        cells = []
        J['main'][T][arm] = []
        for k in range(3):
            ss = [s for s in (seg(d, T, arm) for d in have) if s]
            nn = sum(s['n'][k] for s in ss)
            ff = sum(s['flip'][k] for s in ss)
            per = [s['flip'][k] / s['n'][k] for s in ss if s['n'][k] >= MINN]
            cells.append(f'{pc(ff, nn)}（{pf(q(per, 0.5))} / {pf(q(per, 0.9))}｜{nn} 条｜{len(per)} 份）')
            J['main'][T][arm].append(dict(n=nn, flipped=ff, share=ff / nn if nn else None, perP50=q(per, 0.5), perP90=q(per, 0.9), m=len(per)))
            R[f'OL_{arm.upper()}_{T}_{k}_PCT'] = pc(ff, nn)
            R[f'OL_{arm.upper()}_{T}_{k}_CMDS'] = str(nn)
            R[f'OL_{arm.upper()}_{T}_{k}_M'] = str(len(per))
            R[f'OL_{arm.upper()}_{T}_{k}_P50'] = pf(q(per, 0.5))
            R[f'OL_{arm.upper()}_{T}_{k}_P90'] = pf(q(per, 0.9))
        P(f'    {an} | ' + ' | '.join(cells))
    ratio = []
    for k in range(3):
        a = J['main'][T]['idle'][k]['share']
        b = J['main'][T]['wj'][k]['share']
        ratio.append('—' if not a or not b else f'{a / b:.1f}')
        R[f'OL_RATIO_{T}_{k}'] = ratio[-1]
    P(f'    不下指令 ÷ 地板：{" | ".join(ratio)}')
# 哪个断面翻面最多（逐窗、逐臂），以及两个派生的数
for k in range(3):
    tops = []
    for arm, an in ARMS:
        best = max(SECTIONS, key=lambda T: J['main'][T][arm][k]['share'] or 0)
        tops.append(f'{an} t={best}（{pc(J["main"][best][arm][k]["flipped"], J["main"][best][arm][k]["n"])}）')
        R[f'OL_TOP_{arm.upper()}_{k}'] = f't={best}'
    P(f'  断面后 {WN[k]} 拍翻面占比最高的断面：' + '；'.join(tops))
x = max((J['main'][T]['wj'][k]['share'] or 0) for T in SECTIONS for k in range(3) if not (T == 630 and k == 2))
R['OL_WJ_OTHER_MAX'] = f'{100 * x:.1f}%'
P(f'  地板臂：t=630 断面 630~870 窗 {pc(J["main"][630]["wj"][2]["flipped"], J["main"][630]["wj"][2]["n"])}；别的断面、别的窗最高 {100 * x:.1f}%')
x = max((J['main'][T][arm][k]['share'] or 0) for T in SECTIONS if T != 630 for arm, an in ARMS for k in range(2))
R['OL_OTHER_MAX_630'] = f'{100 * x:.1f}%'
P(f'  t=0 / 1500 / 4284 三个断面，两条臂到断面后 630 拍为止的两个窗，翻面占比最高 {100 * x:.1f}%')
P()

# ---------- [OL-D]
P('[OL-D] 翻面的方向：历史生效 → 现在没生效 / 历史没生效 → 现在生效')
for T in SECTIONS:
    for arm, an in ARMS:
        ss = [s for s in (seg(d, T, arm) for d in have) if s]
        cells = []
        for k in range(3):
            dn = sum(s['down'][k] for s in ss)
            up = sum(s['up'][k] for s in ss)
            cells.append(f'{dn} / {up}')
            R[f'OL_{arm.upper()}_{T}_{k}_DOWN'] = str(dn)
            R[f'OL_{arm.upper()}_{T}_{k}_UP'] = str(up)
        P(f'  t={T} {an}：' + ' | '.join(f'{WN[k]} {cells[k]}' for k in range(3)))
P()

# ---------- [OL-E]
P('[OL-E] 窗末别的真人的地，拷贝和参照重演差多少（只算参照重演里那一拍还在场、有地的；Σ|差| ÷ Σ地，括号里：逐份录像的中位｜有差的人数 ÷ 人数）；最后一列是本编队的地 拷贝 ÷ 参照')
for T in SECTIONS:
    for arm, an in ARMS:
        ss = [s for s in (seg(d, T, arm) for d in have) if s]
        cells = []
        for k in range(3):
            dr = [s['drift'][k] for s in ss if s['drift'][k]]
            land = sum(x['land'] for x in dr)
            dl = sum(x['dLand'] for x in dr)
            per = [x['dLand'] / x['land'] for x in dr if x['land'] > 0]
            npp = sum(x['nP'] for x in dr)
            nd = sum(x['nDiff'] for x in dr)
            cells.append(f'{pc(dl, land)}（{pf(q(per, 0.5))}｜{pc(nd, npp, 0)}，{len(dr)} 份）')
            R[f'OL_DRIFT_{arm.upper()}_{T}_{k}'] = pc(dl, land)
            R[f'OL_DRIFTP_{arm.upper()}_{T}_{k}'] = pc(nd, npp, 0)
        dr = [s['drift'][2] for s in ss if s['drift'][2]]
        oref = sum(x['ownRef'] for x in dr)
        oarm = sum(x['ownArm'] for x in dr)
        own = '—' if not oref else f'{oarm / oref:.2f}'
        R[f'OL_OWN_{arm.upper()}_{T}'] = own
        P(f'  t={T} {an}：' + ' | '.join(f'断面后 {WEND[k]} 拍 {cells[k]}' for k in range(3)) + f' | 870 拍时本编队的地 {own}')
P()

# ---------- [OL-F]
P('[OL-F] 按编队档分（不下指令臂；合计翻面 ÷ 合计条数｜条数）')
for T in SECTIONS:
    cells = []
    for c in ('squad10', 'squad20'):
        ss = [s for s in (seg(d, T, 'idle') for d in have if cohort.get(d['matchId']) == c) if s]
        cc = []
        for k in range(3):
            nn = sum(s['n'][k] for s in ss)
            ff = sum(s['flip'][k] for s in ss)
            cc.append(f'{pc(ff, nn)}｜{nn}')
            R[f'OL_IDLE_{T}_{k}_{c.upper()}'] = pc(ff, nn)
        cells.append(f'{c}（{len(ss)} 份）' + ' / '.join(cc))
    P(f'  t={T}：' + '；'.join(cells))
P()

# ---------- [OL-G]
P('[OL-G] 两种过线办法各放行哪些「断面 × 窗」（4 个断面 × 3 个窗 = 12 格；用 [OL-C] 的合计占比，格名后面是 不下指令臂 / 地板臂 的翻面占比）')


def cell(T, k):
    a, b = J['main'][T]['idle'][k], J['main'][T]['wj'][k]
    return f't={T} {WN[k]}（{pc(a["flipped"], a["n"])} / {pc(b["flipped"], b["n"])}）'


GRID = [(T, k) for T in SECTIONS for k in range(3)]
rel_pass = [(T, k) for T, k in GRID if J['main'][T]['wj'][k]['flipped'] and J['main'][T]['idle'][k]['share'] / J['main'][T]['wj'][k]['share'] <= 2]
rel_na = [(T, k) for T, k in GRID if not J['main'][T]['wj'][k]['flipped']]
rel_fail = [(T, k) for T, k in GRID if (T, k) not in rel_pass and (T, k) not in rel_na]
P('  办法一（相对）：不下指令臂的翻面占比 ÷ 地板臂的 ≤ 2')
P(f'    放行 {len(rel_pass)} 格：' + ('；'.join(cell(T, k) for T, k in rel_pass) or '无'))
P(f'    拦下 {len(rel_fail)} 格：' + ('；'.join(cell(T, k) for T, k in rel_fail) or '无'))
P(f'    算不了（地板臂一条都没翻）{len(rel_na)} 格：' + ('；'.join(cell(T, k) for T, k in rel_na) or '无'))
R['OL_REL_PASS_N'] = str(len(rel_pass))
R['OL_REL_FAIL_N'] = str(len(rel_fail))
R['OL_REL_NA_N'] = str(len(rel_na))
if rel_pass:
    x = max(J['main'][T]['idle'][k]['share'] for T, k in rel_pass)
    R['OL_REL_PASS_MAXIDLE'] = f'{100 * x:.1f}%'
    P(f'    放行的格里不下指令臂翻面占比最高 {100 * x:.1f}%')
if rel_fail:
    x = min(J['main'][T]['idle'][k]['share'] for T, k in rel_fail)
    R['OL_REL_FAIL_MINIDLE'] = f'{100 * x:.1f}%'
    P(f'    拦下的格里不下指令臂翻面占比最低 {100 * x:.1f}%')
P('  办法二（绝对）：翻面占比不超过一条上限')
for cap in (2, 5, 10):
    cc = []
    for arm, an in ARMS:
        over = [(T, k) for T, k in GRID if 100 * (J['main'][T][arm][k]['share'] or 0) > cap]
        R[f'OL_ABS{cap}_{arm.upper()}_OVER_N'] = str(len(over))
        R[f'OL_ABS{cap}_{arm.upper()}_OVER'] = '、'.join(f't={T} 的 {WN[k]}' for T, k in over) or '无'
        cc.append(f'{an}超过的 {len(over)} 格（' + ('、'.join(f't={T} {WN[k]}' for T, k in over) or '无') + '）')
    P(f'    上限 {cap}%：' + '；'.join(cc))
P()

# ---------- [OL-H]
P('[OL-H] 逐份录像（不下指令臂；每个断面三个窗的 翻面/条数）')
P('  录像 | 档 | 真人 | 本编队 | 结束拍 | t=0 | t=630 | t=1500 | t=4284')
for d in have:
    cells = []
    for T in SECTIONS:
        s = seg(d, T, 'idle')
        cells.append('—' if not s else ' '.join(f'{s["flip"][k]}/{s["n"][k]}' for k in range(3)))
    P(f'  {d["matchId"]} | {cohort.get(d["matchId"], "?")} | {d["H"]} | {d["own"]} | {d["endTick"]} | ' + ' | '.join(cells))
P()
P('读数时的限制：')
rr = []
if CF and CF.get('div'):
    for rule in ('p0', 'p14', 'pj', 'ph'):
        for base in ('wj', 'idle'):
            for k in range(3):
                x, y = CF['div'][rule][k], CF['div'][base][k]
                if x['n'] and y['n'] and y['flipped']:
                    rr.append((x['flipped'] / x['n']) / (y['flipped'] / y['n']))
if rr:
    R['OL_RULE_RATIO_MIN'] = f'{min(rr):.1f}'
    R['OL_RULE_RATIO_MAX'] = f'{max(rr):.1f}'
P('  1. 两条臂都是「把本编队的历史指令拿掉 / 挪一下」，不是任何打法；本编队换成带规则的走法，翻面更多'
  + (f'（cfprobe [CF-F] 在 t=630 断面上量过四条带规则的臂：同一个窗里是这两条的 {min(rr):.1f}~{max(rr):.1f} 倍）。' if rr else '。'))
P('  2. 翻面只数了别的真人的陆攻；船、捐款、别人的内置 AI 邻居的走法没有数。内置 AI 在模拟器里是闭环的（看到新局面会改走法），不算开环偏差。')
P('  3. t=4284 断面以后别的真人剩得少，够 20 条的录像数见表；那一行的比例是少数几份录像撑起来的。')
P('  4. 比的是参照重演（89 份录像里 86 份整局和真引擎全场一致 [FA-E]），不是真引擎。')

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'openloop.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
J['rows'] = [dict(matchId=d['matchId'], cohort=cohort.get(d['matchId']), H=d['H'], own=d['own'], endTick=d['endTick'], roomKey=d['roomKey'],
                  segs=[dict(T=s['T'], arm=s['arm'], n=s['n'], flip=s['flip'], down=s['down'], up=s['up'], why=s['why'], endT=s['endT'], at=s['at'],
                             ownCmd=s['ownCmd'], ownDrop=s['ownDrop'], ownLate=s['ownLate'], ownLateSkip=s['ownLateSkip'], drift=s['drift']) for s in d['segs']])
             for d in have]
with open(os.path.join(OUT, 'openloop.json'), 'w', encoding='utf-8') as f:
    json.dump(J, f, ensure_ascii=False)
if '-q' in sys.argv:
    print(f'openloop.py：{len(have)} 份录像 → out/_cross/openloop.txt')
else:
    print('\n'.join(lines))
