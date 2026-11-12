#!/usr/bin/env python3
"""aggregate.py — 汇总断面归因的各条臂（out/_ckpt/runs/*.json）→ reports/ckpt-data/ 下的入库数据表与报告用的表格。

读：out/_ckpt/runs/<局>-<t0>-<块>.json（scripts/ckpt/ckpt_run.mjs 的输出；同一个（局, 断面）可以分几块跑，这里合并）
写：reports/ckpt-data/ckpt_arms.csv    每条臂一行（含历史臂）
    reports/ckpt-data/ckpt_decomp.csv  每个（局, 断面）一行：历史 / C0 / C1 均值 / C2w 均值 / C2 均值，四段贡献与噪声底
    reports/ckpt-data/ckpt_tables.md   报告用的表（按通道状况分组的贡献、保真度残差、指令流签名）

口径：
  结果量 Y = 窗口结束时我方「人均相对领土」relTerr1 =（我方领土 ÷ 席位数）÷（全体真人领土 ÷ 真人数）。
  同一窗口各臂的起点相同（都是历史在断面拍的局面），所以
      历史 − 起点 = (C0 − 起点) + (C1 − C0) + (C2w − C1) + (C2 − C2w) + (历史 − C2)
                    版本规则      基础延迟     实录落后波     页面停摆/掉线   模拟器残差
  C1 / C2w / C2 各有 3 个种子，用均值；同一档 3 个种子的标准差就是这一档的噪声底。
  没有单独跑 C2w 的窗口（窗口结束前没有页面停摆 / 掉线离场）：C2w 与 C2 逐拍相同，直接取 C2。
"""
import csv
import glob
import json
import math
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(R01, 'out', '_ckpt', 'runs')
DST = os.path.join(R01, 'reports', 'ckpt-data')
GROUP = {
    'A075': '通道干净', 'A055': '通道干净', 'A023': '通道干净',
    'A019': '浅落后', 'A054': '浅落后', 'A003': '浅落后',
    'A031': '深落后', 'A050': '深落后', 'A009': '深落后', 'A057': '深落后', 'A059': '深落后', 'A094': '深落后',
    'B039': 'c110 深落后', 'B043': 'c110 深落后',
}
GROUP_ORDER = ['通道干净', '浅落后', '深落后', 'c110 深落后']
MID_ORDER = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094 B039 B043'.split()
ARM_COLS = ['relTerr0', 'relTerr1', 'capture0', 'capture1', 'terr0', 'terr1', 'alive0', 'alive1', 'husk1', 'dead1', 'wealth0', 'wealth1', 'income', 'netProd', 'feeAtk', 'feeLoss',
            'issued', 'preIssued', 'recorded', 'effective', 'dropped', 'lostChan', 'pending', 'batches', 'fullBatches', 'batchShare', 'dumpBatches', 'dupShare', 'atkVoidRate', 'rerouteRate', 'landedShare']


def load(tag_re=r'[a-z]', historical=True, keyfn=None):
    """→ {(mid, t0): {'meta': {...}, 'history': {...}, 'arms': {name: {...}}}}

    文件名 <局>-<t0>-<标签>.json。主批次的标签是单个小写字母（a、b、c…：同一个（局, 断面）分几块跑）；
    附加批次的标签带前缀：g0*（0→1500 一口气放开跑）、r06trace*（换 R06 的阶梯）、fillnearest* / filllinear*（换补法）、
    va* / vb* / vc*（换成另一个历史版本）。tag_re 选批次；keyfn 给出合并用的键（缺省 (局, t0)）。
    """
    out = {}
    for f in sorted(glob.glob(os.path.join(RUNS, '*.json'))):
        m = re.match(r'^([A-Z]\d+)-(\d+)-(\w+)\.json$', os.path.basename(f))
        if not m or not re.fullmatch(tag_re, m.group(3)):
            continue
        d = json.load(open(f))
        if d.get('mode') != 'r01-ckpt' or bool(d.get('historical')) != historical:
            continue
        key = keyfn(d, m.group(3)) if keyfn else (d['match'], d['t0'])
        e = out.setdefault(key, {'meta': {k: d.get(k) for k in ('match', 't0', 't1', 'humans', 'nTeams', 'strategy', 'stratKey', 'squad', 'truncated', 'ended', 'doomed', 'fill')}, 'history': d['history'], 'arms': {}, 'files': []})
        if d.get('truncated'):
            e['meta']['truncated'] = True
        e['files'].append(os.path.basename(f))
        if e['meta']['t1'] != d['t1']:
            # 分块跑的几个进程停在不同的拍（有一块被时间预算截断）：只留走得最远的那一块的历史臂，标记出来
            e['meta']['t1mismatch'] = True
            if d['t1'] > e['meta']['t1']:
                e['meta']['t1'] = d['t1']; e['history'] = d['history']
        for name, m in d['arms'].items():
            m['_t1'] = d['t1']
            e['arms'][name] = m
    return out


LIVE_BANDS = os.path.join(R01, '..', '..', 'archive', 'agents', 'R06', 'sim-v2', 'calib', 'live-bands.json')
CHAIN_FLOOR = 0.05
# 报告主口径用哪一种实录阶梯（located = 只收唯一定位的；hi / lo = 再加上定位不唯一的，取最早 / 最晚放得下的决策）
PRIMARY = os.environ.get('CKPT_PRIMARY', 'located')
SIG_COLS = ('recorded', 'issued', 'batches', 'fullBatches', 'batchShare', 'dumpBatches', 'dupShare', 'atkVoidRate', 'quotaRejectRate', 'dropped', 'lostChan', 'feeAtk', 'netProd', 'income')


def seeds(e, kind):
    return [m for n, m in sorted(e['arms'].items()) if n.split('@')[0] == kind and m['_t1'] == e['meta']['t1']]


def path_err(h, m):
    """沿途我方总领土的平均相对误差：mean_t |臂(t) − 历史(t)| ÷ 历史(t)（历史领土为 0 的采样点不算）。"""
    hs = {s['t']: s['terr'] for s in h.get('series') or []}
    e = [abs(s['terr'] - hs[s['t']]) / hs[s['t']] for s in m.get('series') or [] if hs.get(s['t'])]
    return sum(e) / len(e) if e else None


_SHADOW_DON = {}


def shadow_don_issued(mid, t0, t1):
    """历史这一窗口里我方页面发出过多少次捐款：取 R01 影子（out/<局>/shadow_cmds.csv，引擎接受的 donate 行）。
    录像只收真正执行了的捐款，被配额静默拒掉的不进录像，所以「发出」只能从影子拿（影子的累计指令数逐点对过真实日志）。"""
    if mid not in _SHADOW_DON:
        p = os.path.join(R01, 'out', mid, 'shadow_cmds.csv')
        ts = []
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                if r['kind'] == 'donate' and r['ok'] == '1':
                    ts.append(int(r['t']))
        _SHADOW_DON[mid] = ts
    return sum(1 for t in _SHADOW_DON[mid] if t0 < t <= t1)


_TRACE = {}
TRACE_DIR = {'located': 'traces', 'hi': 'traces-hi', 'lo': 'traces-lo'}


def window_lag(mid, t0, t1, variant='located'):
    """这一窗口里我方配上对的指令（下令拍在窗口内）的落后 = 落地拍 − 下令拍：→ (条数, P50, P75, P90, 均值)。"""
    if (mid, variant) not in _TRACE:
        p = os.path.join(DST, TRACE_DIR[variant], f'{mid}.json')
        rows = []
        if os.path.exists(p):
            for seat in json.load(open(p))['seats'].values():
                rows += [(r[0], r[1] - r[0]) for r in seat]
        _TRACE[(mid, variant)] = rows
    lags = sorted(l for t, l in _TRACE[(mid, variant)] if t0 < t <= t1)
    if not lags:
        return 0, None, None, None, None
    q = lambda p: lags[min(len(lags) - 1, int(p * len(lags)))]
    return len(lags), q(0.5), q(0.75), q(0.9), sum(lags) / len(lags)


def quart(a):
    """→ (P25, 中位, P75)，线性插值（与 R06 的 live_table.mjs 相同）。"""
    a = sorted(x for x in a if x is not None)
    if not a:
        return None, None, None

    def q(p):
        i = (len(a) - 1) * p
        lo, hi = math.floor(i), math.ceil(i)
        return a[lo] + (a[hi] - a[lo]) * (i - lo)
    return q(0.25), q(0.5), q(0.75)


def spearman(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 4:
        return None

    def rank(v):
        o = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx); syy = sum((b - my) ** 2 for b in ry)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def mean(a):
    return sum(a) / len(a) if a else None


def sd(a):
    return st.pstdev(a) if len(a) > 1 else 0.0


def fmt(v, nd=3, sign=False):
    if v is None:
        return '-'
    s = f'{v:+.{nd}f}' if sign else f'{v:.{nd}f}'
    return s


def decompose(R, keys, BAND, variant):
    """每个（局, 断面）一行：历史 / C0 / C1 / C2w / C2 的均值与四段贡献。variant 决定 C2 / C2w 取哪一批（哪种阶梯口径）。"""
    D = []
    for k in keys:
        e = R[k]
        h = e['history']
        c0 = seeds(e, 'C0')
        c1 = seeds(e, 'C1')
        c2 = seeds(e, 'C2')
        c2w_sep = seeds(e, 'C2w')
        rerun = False
        b = BAND.get(variant, {}).get(k)
        if b and b['meta']['t1'] == e['meta']['t1'] and seeds(b, 'C2'):
            c2 = seeds(b, 'C2')
            c2w_sep = seeds(b, 'C2w')
            rerun = True
        c2w = c2w_sep or c2
        if not (c0 and c1 and c2):
            continue
        row = {'mid': k[0], 'group': GROUP.get(k[0], ''), 't0': k[1], 't1': e['meta']['t1'], 'seats': len(e['meta']['squad']), 'alive0': h['alive0'], 'c2wSeparate': bool(c2w_sep),
               'variant': variant, 'variantRerun': rerun,
               'nC1': len(c1), 'nC2': len(c2), 'nC2w': len(c2w), 'truncated': bool(e['meta'].get('truncated')) or bool(e['meta'].get('t1mismatch'))}
        for y in ('relTerr1', 'capture1', 'alive1', 'wealth1', 'terr1'):
            H = h[y]
            v0 = c0[0][y]
            v1 = mean([m[y] for m in c1]); s1 = sd([m[y] for m in c1])
            vw = mean([m[y] for m in c2w]); sw = sd([m[y] for m in c2w])
            v2 = mean([m[y] for m in c2]); s2 = sd([m[y] for m in c2])
            start = h['relTerr0'] if y == 'relTerr1' else h['capture0'] if y == 'capture1' else h['alive0'] if y == 'alive1' else h['wealth0'] if y == 'wealth1' else h['terr0']
            row.update({f'{y}_start': start, f'{y}_hist': H, f'{y}_C0': v0, f'{y}_C1': v1, f'{y}_C1sd': s1, f'{y}_C2w': vw, f'{y}_C2wsd': sw, f'{y}_C2': v2, f'{y}_C2sd': s2,
                        f'{y}_rules': v0 - start, f'{y}_base': v1 - v0, f'{y}_wave': vw - v1, f'{y}_page': v2 - vw, f'{y}_resid': H - v2})
        # 指令流签名（历史 ↔ C2 均值）
        for y in SIG_COLS:
            row[f'{y}_hist'] = h.get(y)
            row[f'{y}_C2'] = mean([m[y] for m in c2 if m.get(y) is not None]) if any(m.get(y) is not None for m in c2) else None
            row[f'{y}_C1'] = mean([m[y] for m in c1 if m.get(y) is not None]) if any(m.get(y) is not None for m in c1) else None
            row[f'{y}_C0'] = c0[0].get(y)
        row['lagN'], row['lagP50'], row['lagP75'], row['lagP90'], row['lagMean'] = window_lag(k[0], k[1], e['meta']['t1'], variant)
        # 阶梯本身的落后：C2 臂的通道档每 150 拍采一次全体席位的平均落后拍数（含已阵亡的席位），取窗口内的均值
        lc = (c2w[0].get('lagCourse') or c2[0].get('lagCourse') or [])
        row['lagStairMean'] = mean([x[1] for x in lc]) if lc else None
        # 捐款：发出 → 进录像（没进的 = 被配额静默拒掉的 + 路上丢的）。历史的「发出」取影子；各臂取沙箱自己的账
        di = shadow_don_issued(k[0], k[1], e['meta']['t1'])
        row['donIssued_hist'] = di
        row['donOk_hist'] = h['don']['ok']
        row['donNotLanded_hist'] = max(0.0, 1 - h['don']['ok'] / di) if di > 0 else None
        for nm, arms in (('C2', c2), ('C1', c1), ('C0', c0)):
            iss = mean([m.get('donIssued') or 0 for m in arms]); okn = mean([m['don']['ok'] for m in arms])
            row[f'donIssued_{nm}'] = iss
            row[f'donOk_{nm}'] = okn
            row[f'donNotLanded_{nm}'] = max(0.0, 1 - okn / iss) if iss > 0 else None
        # 沿途（每 30 拍一个采样点）：我方总领土 C2 对历史的相对误差
        row['pathErr_C2'] = mean([path_err(h, m) for m in c2])
        row['pathErr_C1'] = mean([path_err(h, m) for m in c1])
        row['pathErr_C0'] = path_err(h, c0[0])
        # 席位级：C2 臂每个席位的终点领土对历史的 L1 ÷ 历史合计；其余真人被改打 / 作废的比例
        row['seatL1_C2'] = mean([m['div']['squadL1'] / max(1, m['div']['squadHist']) for m in c2])
        row['othersL1_C2'] = mean([m['div']['othersL1'] / max(1, m['div']['othersHist']) for m in c2])
        row['othersReroute_C2'] = mean([(m['others']['rerouted'] + m['others']['dropped']) / max(1, m['others']['atk']) for m in c2])
        row['othersReroute_C0'] = (c0[0]['others']['rerouted'] + c0[0]['others']['dropped']) / max(1, c0[0]['others']['atk'])
        row['pageDead_C2'] = c2[0].get('pageDead')
        row['husk1_hist'] = h['husk1']; row['husk1_C2'] = mean([m['husk1'] for m in c2]); row['husk1_C1'] = mean([m['husk1'] for m in c1])
        row['dead1_hist'] = h['dead1']; row['dead1_C2'] = mean([m['dead1'] for m in c2]); row['dead1_C1'] = mean([m['dead1'] for m in c1]); row['dead1_C0'] = c0[0]['dead1']
        D.append(row)
    return D


def chain_of(D, force_cut=None, y='relTerr1', floor=None):
    """逐局把首尾相接的窗口串成对数链。→ (chain, cut, use)。y = 结果量（relTerr1 人均相对领土 / wealth1 兵力）。
    我方被打到几乎归零的窗口不进链（ln 会被一个接近 0 的数撑爆；这种「生死窗口」另看活席数）。
    force_cut = {局: 断面}：强制在这个窗口前截断（比较不同阶梯口径 / 不同结果量时，让它们用同一组窗口）。"""
    chain, cut, uses = {}, {}, {}
    ln = math.log
    floor = CHAIN_FLOOR if floor is None else floor
    for mid in MID_ORDER:
        rows = [r for r in D if r['mid'] == mid]
        rows.sort(key=lambda r: r['t0'])
        use = []
        for r in rows:
            vals = [r[f'{y}_start'], r[f'{y}_hist'], r[f'{y}_C0'], r[f'{y}_C1'], r[f'{y}_C2w'], r[f'{y}_C2']]
            if min(vals) < floor or (force_cut and force_cut.get(mid) == r['t0']):
                cut[mid] = r['t0']
                break
            if use and use[-1]['t1'] != r['t0']:
                break
            use.append(r)
        if not use:
            continue
        tot = sum(ln(r[f'{y}_hist'] / r[f'{y}_start']) for r in use)
        rules = sum(ln(r[f'{y}_C0'] / r[f'{y}_start']) for r in use)
        base = sum(ln(r[f'{y}_C1'] / r[f'{y}_C0']) for r in use)
        wave = sum(ln(r[f'{y}_C2w'] / r[f'{y}_C1']) for r in use)
        page = sum(ln(r[f'{y}_C2'] / r[f'{y}_C2w']) for r in use)
        resid = sum(ln(r[f'{y}_hist'] / r[f'{y}_C2']) for r in use)
        chain[mid] = dict(n=len(use), tot=tot, rules=rules, base=base, wave=wave, page=page, resid=resid, start=use[0][f'{y}_start'], end=use[-1][f'{y}_hist'], t0=use[0]['t0'], t1=use[-1]['t1'])
        uses[mid] = use
    return chain, cut, uses


def boot_ci(vals, n_boot=4000, seed=20261112):
    """按局重抽样的均值 90% 区间（局数少，只当量级看）。"""
    import random
    if len(vals) < 4:
        return None
    rnd = random.Random(seed)
    ms = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(n_boot))
    return ms[int(0.05 * n_boot)], ms[int(0.95 * n_boot) - 1]


def main():
    R = load()
    os.makedirs(DST, exist_ok=True)
    keys = sorted(R.keys(), key=lambda k: (MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99, k[1]))

    # ---- ckpt_arms.csv
    with open(os.path.join(DST, 'ckpt_arms.csv'), 'w', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['mid', 'group', 't0', 't1', 'strategy', 'seats', 'arm', 'seed'] + ARM_COLS + ['donOk', 'donQuota', 'othersAtk', 'othersAsRecorded', 'othersRerouted', 'othersDropped', 'divSquadL1', 'divSquadHist', 'divOthersL1', 'divOthersHist', 'pageDead', 'stratErrors', 'guarded'])
        for k in keys:
            e = R[k]
            m0 = e['meta']
            rows = [('history', '', e['history'])] + [(n.split('@')[0], n.split('@')[1] if '@' in n else '1', m) for n, m in sorted(e['arms'].items())]
            for arm, seed, m in rows:
                o = m.get('others') or {}
                dv = m.get('div') or {}
                w.writerow([k[0], GROUP.get(k[0], ''), k[1], m.get('_t1', m0['t1']), m0['strategy'], len(m0['squad']), arm, seed] + [m.get(c) for c in ARM_COLS] +
                           [m['don']['ok'], m['don']['quota'], o.get('atk'), o.get('asRecorded'), o.get('rerouted'), o.get('dropped'), dv.get('squadL1'), dv.get('squadHist'), dv.get('othersL1'), dv.get('othersHist'), m.get('pageDead'), len(m.get('stratErrors') or []), m.get('guarded')])

    # ---- 分解。C2 / C2w 用哪一种实录阶梯口径：located / hi / lo；后两种只重跑了受影响的窗口，没重跑的沿用 located
    BAND = {v: load(rf'{v}[a-z]') for v in ('hi', 'lo')}
    DV = {v: decompose(R, keys, BAND, v) for v in ('located', 'hi', 'lo')}
    D = DV[PRIMARY]
    cols = list(D[0].keys()) if D else []
    with open(os.path.join(DST, 'ckpt_decomp.csv'), 'w', newline='') as fo:
        w = csv.DictWriter(fo, fieldnames=cols)
        w.writeheader()
        for r in D:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})

    # ---- 报告用的表
    L = []
    P = L.append
    WN = {0: '0→630', 630: '630→1500', 1500: '1500→3213', 3213: '3213→4284', 4284: '4284→5184'}
    P('<!-- 由 scripts/ckpt/aggregate.py 生成，勿手改 -->')
    P('')
    P('### 表 A　逐局逐窗口：窗口结束时我方人均相对领土（历史 / 各臂）与四段贡献')
    P('')
    P('| 局 | 窗口 | 断面时活席 | 起点 | 历史 | C0 | C1（±sd） | C2w（±sd） | C2（±sd） | 规则 C0−起点 | 基础延迟 C1−C0 | 落后波 C2w−C1 | 页面/掉线 C2−C2w | 残差 历史−C2 |')
    P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    for r in D:
        y = 'relTerr1'
        P(f"| {r['mid']} | {WN.get(r['t0'], r['t0'])}{'（到 ' + str(r['t1']) + '）' if r['t1'] - r['t0'] not in (630, 870, 1713, 1071, 900) else ''} | {r['alive0']}/{r['seats']} | {fmt(r[y + '_start'])} | {fmt(r[y + '_hist'])} | {fmt(r[y + '_C0'])} | {fmt(r[y + '_C1'])} ±{fmt(r[y + '_C1sd'])} | "
          f"{(fmt(r[y + '_C2w']) + ' ±' + fmt(r[y + '_C2wsd'])) if r['c2wSeparate'] else '= C2'} | {fmt(r[y + '_C2'])} ±{fmt(r[y + '_C2sd'])} | {fmt(r[y + '_rules'], 3, True)} | {fmt(r[y + '_base'], 3, True)} | {fmt(r[y + '_wave'], 3, True)} | {fmt(r[y + '_page'], 3, True) if r['c2wSeparate'] else '0'} | {fmt(r[y + '_resid'], 3, True)} |")
    P('')

    def agg(rows, y='relTerr1'):
        n = len(rows)
        if not n:
            return None
        s = lambda k: sum(r[f'{y}_{k}'] for r in rows)
        tot = sum(r[f'{y}_hist'] - r[f'{y}_C0'] for r in rows)
        return dict(n=n, start=s('start') / n, hist=s('hist') / n, C0=s('C0') / n, C1=s('C1') / n, C2w=s('C2w') / n, C2=s('C2') / n,
                    rules=s('rules') / n, base=s('base') / n, wave=s('wave') / n, page=s('page') / n, resid=s('resid') / n,
                    absResid=sum(abs(r[f'{y}_resid']) for r in rows) / n, noise1=sum(r[f'{y}_C1sd'] for r in rows) / n, noise2=sum(r[f'{y}_C2sd'] for r in rows) / n, gap=tot / n,
                    shBase=s('base') / tot if abs(tot) > 1e-9 else None, shWave=s('wave') / tot if abs(tot) > 1e-9 else None, shPage=s('page') / tot if abs(tot) > 1e-9 else None, shResid=s('resid') / tot if abs(tot) > 1e-9 else None)

    P('### 表 B　按通道状况分组、按窗口：各段贡献的均值（人均相对领土的点数）')
    P('')
    P('| 组 | 窗口 | 局数 | 起点 | C0 | 历史 | 规则 C0−起点 | 基础延迟 | 落后波 | 页面/掉线 | 残差 | \\|残差\\| 均值 | C1 噪声底 sd | C2 噪声底 sd | 历史−C0 | 其中：基础延迟 / 落后波 / 页面 / 残差 |')
    P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | :-- |')
    for g in GROUP_ORDER + ['全部']:
        for t0 in sorted(WN):
            rows = [r for r in D if (g == '全部' or r['group'] == g) and r['t0'] == t0]
            a = agg(rows)
            if not a:
                continue
            sh = ' / '.join('-' if a[k] is None else f'{100 * a[k]:.0f}%' for k in ('shBase', 'shWave', 'shPage', 'shResid'))
            P(f"| {g} | {WN[t0]} | {a['n']} | {fmt(a['start'])} | {fmt(a['C0'])} | {fmt(a['hist'])} | {fmt(a['rules'], 3, True)} | {fmt(a['base'], 3, True)} | {fmt(a['wave'], 3, True)} | {fmt(a['page'], 3, True)} | {fmt(a['resid'], 3, True)} | {fmt(a['absResid'])} | {fmt(a['noise1'])} | {fmt(a['noise2'])} | {fmt(a['gap'], 3, True)} | {sh} |")
    P('')

    P('### 表 B2　兵力（余额 + 在攻兵）与活席：各臂对历史（按组、按窗口；兵力取各局比值的几何均值，活席取均值）')
    P('')
    P('| 组 | 窗口 | 局数 | 兵力 C0÷历史 | 兵力 C1÷历史 | 兵力 C2w÷历史 | 兵力 C2÷历史 | 活席（非空壳）历史 | C0 | C1 | C2w | C2 | 实抢率 历史 | C0 | C1 | C2 |')
    P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    gm = lambda a: math.exp(sum(math.log(x) for x in a) / len(a)) if a and all(x > 0 for x in a) else None
    for g in GROUP_ORDER + ['全部']:
        for t0 in sorted(WN):
            rows = [r for r in D if (g == '全部' or r['group'] == g) and r['t0'] == t0]
            if not rows:
                continue
            wr = lambda k: gm([r[f'wealth1_{k}'] / r['wealth1_hist'] for r in rows if r['wealth1_hist'] > 0 and r[f'wealth1_{k}'] > 0])
            am = lambda k: mean([r[f'alive1_{k}'] for r in rows])
            cm = lambda k: mean([r[f'capture1_{k}'] for r in rows if r[f'capture1_{k}'] is not None])
            P(f"| {g} | {WN[t0]} | {len(rows)} | {fmt(wr('C0'), 2)} | {fmt(wr('C1'), 2)} | {fmt(wr('C2w'), 2)} | {fmt(wr('C2'), 2)} | {fmt(am('hist'), 1)} | {fmt(am('C0'), 1)} | {fmt(am('C1'), 1)} | {fmt(am('C2w'), 1)} | {fmt(am('C2'), 1)} | {fmt(cm('hist'), 2)} | {fmt(cm('C0'), 2)} | {fmt(cm('C1'), 2)} | {fmt(cm('C2'), 2)} |")
    P('')

    # 逐局把 5 个窗口串起来：对数分解（各窗口起点都是历史局面，所以 ln(历史终点/历史起点) 逐窗口相加就是整段的 ln 变化）
    P('### 表 C　逐局把首尾相接的窗口串起来：ln(人均相对领土) 的整段变化分到五段（只算两端都 > 0 的窗口）')
    P('')
    P('| 局 | 组 | 串起来的窗口 | 起点 → 终点（历史） | ln 变化合计 | 规则（C0） | 基础延迟 | 落后波 | 页面/掉线 | 残差 | C0 一路走下来的终点（等效） | C1 一路走下来的终点（等效） | C2 一路走下来的终点（等效） |')
    P('| :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    chain, cut, chain_use = chain_of(D)
    for mid in MID_ORDER:
        if mid not in chain:
            continue
        c = chain[mid]; use = chain_use[mid]
        tot, rules, base, wave, page, resid = (c[k] for k in ('tot', 'rules', 'base', 'wave', 'page', 'resid'))
        P(f"| {mid} | {GROUP[mid]} | {use[0]['t0']}→{use[-1]['t1']}（{len(use)} 个） | {fmt(use[0]['relTerr1_start'])} → {fmt(use[-1]['relTerr1_hist'])} | {fmt(tot, 3, True)} | {fmt(rules, 3, True)} | {fmt(base, 3, True)} | {fmt(wave, 3, True)} | {fmt(page, 3, True)} | {fmt(resid, 3, True)} | {fmt(use[0]['relTerr1_start'] * math.exp(rules))} | {fmt(use[0]['relTerr1_start'] * math.exp(rules + base))} | {fmt(use[0]['relTerr1_start'] * math.exp(rules + base + wave + page))} |")
    P('')
    if cut:
        P('没进链的生死窗口（历史或某条臂的人均相对领土 < %.2f）：' % CHAIN_FLOOR + '、'.join(f'{m} 的 {WN.get(t, t)}' for m, t in cut.items()) + '。')
        P('')
    P('| 组 | 局数 | ln 变化合计（均值） | 规则（C0） | 基础延迟 | 落后波 | 页面/掉线 | 残差 | 占合计的比例：规则 / 基础延迟 / 落后波 / 页面 / 残差 | 以 C1 为基线：规则+基础延迟 / 落后波 / 页面 / 残差 |')
    P('| :-- | --: | --: | --: | --: | --: | --: | --: | :-- | :-- |')
    chain_rows = []
    for g in GROUP_ORDER + ['A 局（c116 家族）', '全部']:
        ms = [m for m in chain if g == '全部' or GROUP[m] == g or (g.startswith('A 局') and m.startswith('A'))]
        if not ms:
            continue
        n = len(ms)
        S = {k: sum(chain[m][k] for m in ms) for k in ('tot', 'rules', 'base', 'wave', 'page', 'resid')}
        pc = lambda v: f"{100 * v / S['tot']:.0f}%" if abs(S['tot']) > 1e-9 else '-'
        sh = ' / '.join(pc(S[k]) for k in ('rules', 'base', 'wave', 'page', 'resid'))
        sh1 = ' / '.join([pc(S['rules'] + S['base']), pc(S['wave']), pc(S['page']), pc(S['resid'])])
        chain_rows.append({'group': g, 'n': n, **{k: S[k] / n for k in S}})
        P(f"| {g} | {n} | {fmt(S['tot'] / n, 3, True)} | {fmt(S['rules'] / n, 3, True)} | {fmt(S['base'] / n, 3, True)} | {fmt(S['wave'] / n, 3, True)} | {fmt(S['page'] / n, 3, True)} | {fmt(S['resid'] / n, 3, True)} | {sh} | {sh1} |")
    P('')
    with open(os.path.join(DST, 'ckpt_chain.csv'), 'w', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['mid', 'group', 't0', 't1', 'windows', 'relTerrStart', 'relTerrEndHist', 'lnTotal', 'lnRulesC0', 'lnBase', 'lnWave', 'lnPage', 'lnResid'])
        for m in MID_ORDER:
            if m in chain:
                c = chain[m]
                w.writerow([m, GROUP[m], c['t0'], c['t1'], c['n'], round(c['start'], 5), round(c['end'], 5)] + [round(c[k], 5) for k in ('tot', 'rules', 'base', 'wave', 'page', 'resid')])
        for r in chain_rows:
            w.writerow([f"均值：{r['group']}", '', '', '', r['n'], '', ''] + [round(r[k], 5) for k in ('tot', 'rules', 'base', 'wave', 'page', 'resid')])

    # 以健康通道（C1）为基线的一句话口径：历史终点 ÷ C1 一路走下来的终点 = exp(落后波 + 页面 + 残差)；领土与兵力各算一遍（同一组窗口）
    wchain = chain_of(D, cut, y='wealth1', floor=1)[0]
    P('### 表 H　以健康通道（C1）为基线：历史终点 ÷ C1 一路走下来的终点，分到落后波 / 页面掉线 / 残差（几何均值；领土与兵力）')
    P('')
    P('| 组 | 局数 | 结果量 | 历史 ÷ C1 路径 | 其中：落后波 | 页面/掉线 | 残差 | ln 差里各段占比：落后波 / 页面 / 残差 | 落后波+页面 的 ln 均值（按局重抽样 90% 区间） | 另：C1 路径 ÷ C0 路径（基础延迟） |')
    P('| :-- | --: | :-- | --: | --: | --: | --: | :-- | :-- | --: |')
    head_rows = []
    for g in GROUP_ORDER + ['A 局（c116 家族）', '全部']:
        for y, ch, label in (('relTerr1', chain, '人均相对领土'), ('wealth1', wchain, '兵力（余额 + 在攻）')):
            ms = [m for m in ch if m in chain and ch[m]['n'] == chain[m]['n'] and (g == '全部' or GROUP[m] == g or (g.startswith('A 局') and m.startswith('A')))]
            if not ms:
                continue
            mw, mp, mr, mb = (mean([ch[m][k] for m in ms]) for k in ('wave', 'page', 'resid', 'base'))
            gap = mw + mp + mr
            pc = lambda v: f'{100 * v / gap:.0f}%' if abs(gap) > 0.05 else '-'
            ci = boot_ci([ch[m]['wave'] + ch[m]['page'] for m in ms])
            head_rows.append({'group': g, 'n': len(ms), 'y': y, 'histOverC1': math.exp(gap), 'wave': math.exp(mw), 'page': math.exp(mp), 'resid': math.exp(mr), 'lnWavePage': mw + mp,
                              'ciLo': ci[0] if ci else None, 'ciHi': ci[1] if ci else None, 'c1OverC0': math.exp(mb)})
            P(f"| {g} | {len(ms)} | {label} | ×{math.exp(gap):.2f} | ×{math.exp(mw):.2f} | ×{math.exp(mp):.2f} | ×{math.exp(mr):.2f} | {pc(mw)} / {pc(mp)} / {pc(mr)} | {mw + mp:+.3f}" + (f"（{ci[0]:+.3f} ~ {ci[1]:+.3f}）" if ci else '（局数太少，不给区间）') + f" | ×{math.exp(mb):.2f} |")
    P('')
    with open(os.path.join(DST, 'ckpt_headline.csv'), 'w', newline='') as fo:
        w = csv.DictWriter(fo, fieldnames=list(head_rows[0].keys()))
        w.writeheader()
        for r in head_rows:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    P('逐局（人均相对领土 / 兵力）：历史 ÷ C1 路径，及其中落后波+页面：')
    P('')
    P('| 局 | 组 | 窗口 | 领土：历史 ÷ C1 路径 | 领土：落后波 × 页面 | 领土：残差 | 兵力：历史 ÷ C1 路径 | 兵力：落后波 × 页面 | 兵力：残差 |')
    P('| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: |')
    for m in MID_ORDER:
        if m not in chain:
            continue
        c = chain[m]; wc = wchain.get(m)
        ok = wc and wc['n'] == c['n']
        P(f"| {m} | {GROUP[m]} | {c['t0']}→{c['t1']} | ×{math.exp(c['wave'] + c['page'] + c['resid']):.2f} | ×{math.exp(c['wave'] + c['page']):.2f} | ×{math.exp(c['resid']):.2f} | "
          + (f"×{math.exp(wc['wave'] + wc['page'] + wc['resid']):.2f} | ×{math.exp(wc['wave'] + wc['page']):.2f} | ×{math.exp(wc['resid']):.2f} |" if ok else '- | - | - |'))
    P('')

    P('### 表 D　闭环保真度：C2 臂（实录通道 + 实录页面）对历史臂，逐局逐窗口')
    P('')
    P('| 局 | 窗口 | 人均相对领土 历史 / C2 | 差（C2−历史） | C2 噪声底 sd | 沿途领土相对误差 | 活席(非壳) 历史 / C2 | 空壳 历史 / C2 | 进录像条数 历史 / C2 | 同拍批≥3 历史 / C2 | 满 9 批 历史 / C2 | 清仓批 历史 / C2 | 同拍批占比 历史 / C2 | 陆攻落空率 历史 / C2 | 重复单占比 历史 / C2 | 捐款 发出→进录像 历史 / C2 | 席位级领土 L1÷历史 | 其余真人领土 L1÷历史 | 其余真人陆攻被改打或作废 |')
    P('| :-- | :-- | :-- | --: | --: | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | --: | --: | --: |')
    f2 = lambda v, nd=2: '-' if v is None else (f'{v:.{nd}f}' if isinstance(v, float) else str(v))
    for r in D:
        P(f"| {r['mid']} | {WN.get(r['t0'], r['t0'])} | {fmt(r['relTerr1_hist'])} / {fmt(r['relTerr1_C2'])} | {fmt(-r['relTerr1_resid'], 3, True)} | {fmt(r['relTerr1_C2sd'])} | {f2(r['pathErr_C2'], 3)} | {r['alive1_hist']} / {f2(r['alive1_C2'], 1)} | {r['husk1_hist']} / {f2(r['husk1_C2'], 1)} | "
          f"{r['recorded_hist']} / {f2(r['recorded_C2'], 0)} | {r['batches_hist']} / {f2(r['batches_C2'], 1)} | {r['fullBatches_hist']} / {f2(r['fullBatches_C2'], 1)} | {r['dumpBatches_hist']} / {f2(r['dumpBatches_C2'], 1)} | {f2(r['batchShare_hist'])} / {f2(r['batchShare_C2'])} | {f2(r['atkVoidRate_hist'])} / {f2(r['atkVoidRate_C2'])} | {f2(r['dupShare_hist'])} / {f2(r['dupShare_C2'])} | {r['donIssued_hist']}→{r['donOk_hist']} / {f2(r['donIssued_C2'], 0)}→{f2(r['donOk_C2'], 0)} | "
          f"{f2(r['seatL1_C2'])} | {f2(r['othersL1_C2'])} | {f2(r['othersReroute_C2'])} |")
    P('')

    # 保真度汇总
    P('### 表 E　闭环保真度汇总（按窗口）')
    P('')
    P('| 窗口 | 局数 | 残差均值（历史−C2） | \\|残差\\| 均值 | \\|残差\\| 中位 | \\|残差\\| ≤ 2×C2 噪声底 的局数 | \\|残差\\| ÷ 历史值 中位 | 活席数相同的局数 | 进录像条数 C2÷历史 中位 | 同拍批占比 \\|差\\| 均值 | 席位级领土 L1÷历史 中位 |')
    P('| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    for t0 in sorted(WN):
        rows = [r for r in D if r['t0'] == t0]
        if not rows:
            continue
        res = [r['relTerr1_resid'] for r in rows]
        within = sum(1 for r in rows if abs(r['relTerr1_resid']) <= 2 * max(r['relTerr1_C2sd'], 0.005))
        rel = sorted(abs(r['relTerr1_resid']) / r['relTerr1_hist'] for r in rows if r['relTerr1_hist'] > 0)
        same_alive = sum(1 for r in rows if abs(r['alive1_hist'] - r['alive1_C2']) < 0.34)
        rr = sorted(r['recorded_C2'] / r['recorded_hist'] for r in rows if r['recorded_hist'])
        bs = [abs((r['batchShare_hist'] or 0) - (r['batchShare_C2'] or 0)) for r in rows]
        sl = sorted(r['seatL1_C2'] for r in rows)
        med = lambda a: a[len(a) // 2] if a else None
        P(f"| {WN[t0]} | {len(rows)} | {fmt(mean(res), 3, True)} | {fmt(mean([abs(x) for x in res]))} | {fmt(med(sorted(abs(x) for x in res)))} | {within}/{len(rows)} | {fmt(med(rel), 2)} | {same_alive}/{len(rows)} | {fmt(med(rr), 2)} | {fmt(mean(bs), 3)} | {fmt(med(sl), 2)} |")
    P('')

    P('### 表 F　指令流签名：C0 / C1 / C2 / 历史（各窗口所有局合计或均值）')
    P('')
    P('| 窗口 | 局数 | 进录像条数 C0 / C1 / C2 / 历史 | 同拍批占比 C0 / C1 / C2 / 历史 | 重复单占比 C0 / C1 / C2 / 历史 | 陆攻落空率 C0 / C1 / C2 / 历史 | 陆攻手续费 C0 / C1 / C2 / 历史（千兵） | 被 9 条顶丢 C2 | 通道已断丢 C2 |')
    P('| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: |')
    for t0 in sorted(WN):
        rows = [r for r in D if r['t0'] == t0]
        if not rows:
            continue
        sm = lambda k: sum((r[k] or 0) for r in rows)
        av = lambda k: mean([r[k] for r in rows if r[k] is not None])
        P(f"| {WN[t0]} | {len(rows)} | {sm('recorded_C0'):.0f} / {sm('recorded_C1'):.0f} / {sm('recorded_C2'):.0f} / {sm('recorded_hist'):.0f} | {fmt(av('batchShare_C0'), 2)} / {fmt(av('batchShare_C1'), 2)} / {fmt(av('batchShare_C2'), 2)} / {fmt(av('batchShare_hist'), 2)} | "
          f"{fmt(av('dupShare_C0'), 2)} / {fmt(av('dupShare_C1'), 2)} / {fmt(av('dupShare_C2'), 2)} / {fmt(av('dupShare_hist'), 2)} | {fmt(av('atkVoidRate_C0'), 2)} / {fmt(av('atkVoidRate_C1'), 2)} / {fmt(av('atkVoidRate_C2'), 2)} / {fmt(av('atkVoidRate_hist'), 2)} | "
          f"{sm('feeAtk_C0') / 1000:.0f} / {sm('feeAtk_C1') / 1000:.0f} / {sm('feeAtk_C2') / 1000:.0f} / {sm('feeAtk_hist') / 1000:.0f} | {sm('dropped_C2'):.0f} | {sm('lostChan_C2'):.0f} |")
    P('')
    # ---- 剂量—反应：窗口里的落后有多深 ↔ 落后波这一段有多大
    P('### 表 W　剂量—反应：窗口内我方指令落后的 P75 分档 ↔ 落后波（C2w−C1）与页面/掉线（C2−C2w）两段')
    P('')
    P('| 窗口内落后 P75（拍） | （局, 窗口）数 | 落后 P75 中位 | 落后波：均值 | 落后波：中位 | 落后波 < 0 的个数 | 落后波 ÷ C1（相对量）均值 | 页面/掉线：均值 | C1 噪声底 sd 均值 |')
    P('| :-- | --: | --: | --: | --: | --: | --: | --: | --: |')
    BINS = [(0, 21, '≤ 21（三轮以内）'), (21, 70, '22–70'), (70, 210, '71–210'), (210, 10 ** 9, '> 210（30 轮以上）')]
    dose = [r for r in D if r.get('lagP75') is not None]
    for lo, hi, label in BINS:
        rows = [r for r in dose if lo < r['lagP75'] <= hi] if lo else [r for r in dose if r['lagP75'] <= hi]
        if not rows:
            continue
        wv = [r['relTerr1_wave'] for r in rows]
        rel = [r['relTerr1_wave'] / r['relTerr1_C1'] for r in rows if r['relTerr1_C1'] > 0]
        P(f"| {label} | {len(rows)} | {quart([r['lagP75'] for r in rows])[1]} | {fmt(mean(wv), 3, True)} | {fmt(quart(wv)[1], 3, True)} | {sum(1 for x in wv if x < 0)}/{len(wv)} | {fmt(100 * mean(rel), 1, True)}% | {fmt(mean([r['relTerr1_page'] for r in rows]), 3, True)} | {fmt(mean([r['relTerr1_C1sd'] for r in rows]))} |")
    rho = spearman([r['lagP75'] for r in dose], [r['relTerr1_wave'] for r in dose])
    rho2 = spearman([r['lagP75'] for r in dose], [r['relTerr1_wave'] / r['relTerr1_C1'] if r['relTerr1_C1'] > 0 else None for r in dose])
    P('')
    P(f"{len(dose)} 个（局, 窗口）：落后 P75 与落后波的秩相关 {'-' if rho is None else f'{rho:.2f}'}；与落后波相对量（÷C1）的秩相关 {'-' if rho2 is None else f'{rho2:.2f}'}。")
    P('')
    P('| 窗口内阶梯的平均落后（拍；全体席位、每 150 拍采样的均值） | （局, 窗口）数 | 平均落后 中位 | 落后波：均值 | 落后波：中位 | 落后波 < 0 的个数 | 落后波 ÷ C1（相对量）均值 | 页面/掉线：均值 | C1 噪声底 sd 均值 |')
    P('| :-- | --: | --: | --: | --: | --: | --: | --: | --: |')
    BINS2 = [(-1, 3, '≤ 3'), (3, 15, '3–15'), (15, 60, '15–60'), (60, 10 ** 9, '> 60')]
    dose2 = [r for r in D if r.get('lagStairMean') is not None]
    for lo, hi, label in BINS2:
        rows = [r for r in dose2 if lo < r['lagStairMean'] <= hi]
        if not rows:
            continue
        wv = [r['relTerr1_wave'] for r in rows]
        rel = [r['relTerr1_wave'] / r['relTerr1_C1'] for r in rows if r['relTerr1_C1'] > 0]
        P(f"| {label} | {len(rows)} | {fmt(quart([r['lagStairMean'] for r in rows])[1], 1)} | {fmt(mean(wv), 3, True)} | {fmt(quart(wv)[1], 3, True)} | {sum(1 for x in wv if x < 0)}/{len(wv)} | {fmt(100 * mean(rel), 1, True)}% | {fmt(mean([r['relTerr1_page'] for r in rows]), 3, True)} | {fmt(mean([r['relTerr1_C1sd'] for r in rows]))} |")
    rho = spearman([r['lagStairMean'] for r in dose2], [r['relTerr1_wave'] for r in dose2])
    rho2 = spearman([r['lagStairMean'] for r in dose2], [r['relTerr1_wave'] / r['relTerr1_C1'] if r['relTerr1_C1'] > 0 else None for r in dose2])
    P('')
    P(f"{len(dose2)} 个（局, 窗口）：阶梯平均落后与落后波的秩相关 {'-' if rho is None else f'{rho:.2f}'}；与落后波相对量（÷C1）的秩相关 {'-' if rho2 is None else f'{rho2:.2f}'}。")
    P('')

    # ---- G0 统计签名的四分位核对
    P('### 表 E2　统计签名的四分位核对（按窗口；每个（局, 窗口）一个点；C2 取 3 个种子的均值）')
    P('')
    P('| 窗口 | 签名 | 点数 | 历史 Q1 / 中位 / Q3 | C2 Q1 / 中位 / Q3 | C2 中位落在历史四分位区间内 | 逐点 \\|C2−历史\\| 中位 | 逐点秩相关 |')
    P('| :-- | :-- | --: | :-- | :-- | :-- | --: | --: |')
    SIGS = [('relTerr1', '窗口末人均相对领土', 3), ('recorded', '进录像条数', 0), ('batchShare', '同拍批占比', 2), ('dumpBatches', '同拍清仓批（个）', 1), ('dupShare', '重复单占比', 2), ('atkVoidRate', '陆攻落空率', 3),
            ('donIssued', '发出的捐款（次）', 0), ('donOk', '进录像的捐款（次）', 0), ('donNotLanded', '捐款拒单率（发出的里没进录像的）', 2)]
    sig_rows = []
    for t0 in list(sorted(WN)) + ['全部']:
        rows = [r for r in D if t0 == '全部' or r['t0'] == t0]
        if not rows:
            continue
        for key, label, nd in SIGS:
            pts = [(r[f'{key}_hist'], r[f'{key}_C2']) for r in rows if r.get(f'{key}_hist') is not None and r.get(f'{key}_C2') is not None]
            if len(pts) < 3:
                continue
            hq = quart([p[0] for p in pts]); cq = quart([p[1] for p in pts])
            inside = hq[0] <= cq[1] <= hq[2]
            mad = quart([abs(p[1] - p[0]) for p in pts])[1]
            rho = spearman([p[0] for p in pts], [p[1] for p in pts])
            sig_rows.append({'window': WN.get(t0, t0), 'sig': key, 'n': len(pts), 'histQ1': hq[0], 'histMed': hq[1], 'histQ3': hq[2], 'c2Q1': cq[0], 'c2Med': cq[1], 'c2Q3': cq[2], 'c2MedInsideHistIQR': int(inside), 'medAbsDiff': mad, 'spearman': rho})
            P(f"| {WN.get(t0, t0)} | {label} | {len(pts)} | {f2(float(hq[0]), nd)} / {f2(float(hq[1]), nd)} / {f2(float(hq[2]), nd)} | {f2(float(cq[0]), nd)} / {f2(float(cq[1]), nd)} / {f2(float(cq[2]), nd)} | {'是' if inside else '否'} | {f2(float(mad), max(nd, 2) if nd else 0)} | {'-' if rho is None else f'{rho:.2f}'} |")
    P('')
    if sig_rows:
        with open(os.path.join(DST, 'ckpt_signatures.csv'), 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(sig_rows[0].keys()))
            w.writeheader()
            for r in sig_rows:
                w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})

    # ---- 对照 R06 入库的「实盘区间」（sim-v2/calib/live-bands.json：按版本 × 卡顿档，全部合格历史局各项签名的 P25 / 中位 / P75）
    if os.path.exists(LIVE_BANDS):
        LB = json.load(open(LIVE_BANDS))
        # 卡顿档沿用 R06 的分法：第一窗口（630 起）的同拍批占比 < 15% 算 clean，≥ 50% 算 lag，其间 mid；R06 分过的局用它的
        cls = {}
        for r in D:
            if r['t0'] == 630:
                b = r.get('batchShare_hist') or 0
                cls[r['mid']] = (LB['matches'].get(r['mid']) or {}).get('cls') or ('clean' if b < 0.15 else 'lag' if b >= 0.5 else 'mid')
        cohort = lambda mid: 'c110' if mid.startswith('B') else (R[(mid, 630)]['meta'].get('stratKey') or '') if (mid, 630) in R else ''
        WL = {630: ('630~1530', 900 / 870), 1500: ('1530~3210', 1680 / 1713)}
        SIG3 = [('recPerSeat', '进录像条数 ÷ 席位', lambda r, a: r[f'recorded_{a}'] / r['seats'], True, 1),
                ('batchShare', '同拍批占比', lambda r, a: r[f'batchShare_{a}'], False, 2),
                ('dumpPerSeat', '清仓批 ÷ 席位', lambda r, a: r[f'dumpBatches_{a}'] / r['seats'], True, 2),
                ('atkVoidRate', '陆攻落空率', lambda r, a: r[f'atkVoidRate_{a}'], False, 2),
                ('dupShare', '重复单占比', lambda r, a: r[f'dupShare_{a}'], False, 2),
                ('donNotLanded', '捐款发出后没成交的占比', lambda r, a: r[f'donNotLanded_{a}'], False, 2),
                ('relTerr1', '窗口末人均相对领土', lambda r, a: r[f'relTerr1_{a}'], False, 3),
                ('aliveShare', '窗口末存活席位占比', lambda r, a: r[f'alive1_{a}'] / r['seats'], False, 2)]
        P('### 表 E3　对照 R06 入库的实盘区间（全部合格历史局的 P25 / 中位 / P75）：本报告这几局的历史值与 C2 臂落在哪')
        P('')
        P('| 版本 × 卡顿档 | 窗口（R06 的口径） | 签名 | 实盘区间 P25 / 中位 / P75（局数） | 本报告的局数 | 这几局的历史值 中位 | 这几局的 C2 中位 | C2 中位在区间内 | 逐局在区间内：历史 / C2 | 逐局历史与 C2 同在内或同在外 |')
        P('| :-- | :-- | :-- | :-- | --: | --: | --: | :-- | :-- | :-- |')
        live_rows = []
        for co in ('vb', 'va', 'c110'):
            for cl in ('all', 'clean', 'mid', 'lag'):
                for t0 in (630, 1500):
                    band = (LB['cohorts'].get(f'{co}|{cl}|{WL[t0][0]}') or {}).get('band')
                    rows = [r for r in D if r['t0'] == t0 and cohort(r['mid']) == co and (cl == 'all' or cls.get(r['mid']) == cl) and not r['truncated']]
                    if not band or not rows or (cl != 'all' and len(rows) < 2):
                        continue
                    for key, label, fn, scaled, nd in SIG3:
                        if key not in band:
                            continue
                        sc = WL[t0][1] if scaled else 1
                        pts = []
                        for r in rows:
                            try:
                                hv, cv = fn(r, 'hist'), fn(r, 'C2')
                            except (TypeError, KeyError):
                                continue
                            if hv is None or cv is None:
                                continue
                            pts.append((hv * sc, cv * sc))
                        if not pts:
                            continue
                        lo, md, hi, nb = band[key]
                        inside = lambda v: lo - 1e-9 <= v <= hi + 1e-9
                        hm, cm = quart([p[0] for p in pts])[1], quart([p[1] for p in pts])[1]
                        nh, nc = sum(1 for p in pts if inside(p[0])), sum(1 for p in pts if inside(p[1]))
                        agree = sum(1 for p in pts if inside(p[0]) == inside(p[1]))
                        live_rows.append({'cohort': co, 'cls': cl, 'window': WL[t0][0], 'sig': key, 'liveP25': lo, 'liveMed': md, 'liveP75': hi, 'liveN': nb, 'n': len(pts), 'histMed': hm, 'c2Med': cm,
                                          'c2MedInside': int(inside(cm)), 'histMedInside': int(inside(hm)), 'histInside': nh, 'c2Inside': nc, 'agree': agree})
                        P(f"| {co} × {cl} | {WL[t0][0]} | {label} | {f2(float(lo), nd)} / {f2(float(md), nd)} / {f2(float(hi), nd)}（{nb}） | {len(pts)} | {f2(float(hm), nd)}{'' if inside(hm) else '（区间外）'} | {f2(float(cm), nd)} | {'是' if inside(cm) else '否'} | {nh} / {nc} | {agree}/{len(pts)} |")
        P('')
        if live_rows:
            with open(os.path.join(DST, 'ckpt_livebands.csv'), 'w', newline='') as fo:
                w = csv.DictWriter(fo, fieldnames=list(live_rows[0].keys()))
                w.writeheader()
                for r in live_rows:
                    w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
            allr = [r for r in live_rows if r['cls'] == 'all']
            P(f"版本 × 全部卡顿档的 {len(allr)} 个（窗口, 签名）格子里：C2 中位落在实盘区间内的 {sum(r['c2MedInside'] for r in allr)} 个，这几局自己的历史值中位落在区间内的 {sum(r['histMedInside'] for r in allr)} 个，"
              f"两者同在内或同在外的 {sum(1 for r in allr if r['c2MedInside'] == r['histMedInside'])} 个。")
            P('')

    extra = []

    # ---- 0→1500 一口气放开跑
    G = load(r'g0[a-z]')
    if G:
        P('### 表 G　从开局一口气放开跑到 t=1500（不在 630 重新对齐）：窗口末人均相对领土与签名')
        P('')
        P('| 局 | 组 | 历史 | C0 | C1（±sd） | C2w（±sd） | C2（±sd） | 残差 历史−C2 | 沿途领土相对误差 C2 | 活席 历史 / C2 | 进录像条数 历史 / C2 | 同拍批占比 历史 / C2 | 重复单占比 历史 / C2 | 陆攻落空率 历史 / C2 |')
        P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :-- | :-- | :-- | :-- | :-- |')
        gres = []
        for k in sorted(G, key=lambda k: MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99):
            e = G[k]; h = e['history']
            c0, c1, c2 = seeds(e, 'C0'), seeds(e, 'C1'), seeds(e, 'C2')
            c2w = seeds(e, 'C2w')
            if not (c0 and c1 and c2):
                continue
            y = 'relTerr1'
            v1, s1 = mean([m[y] for m in c1]), sd([m[y] for m in c1])
            v2, s2 = mean([m[y] for m in c2]), sd([m[y] for m in c2])
            vw, sw = (mean([m[y] for m in c2w]), sd([m[y] for m in c2w])) if c2w else (v2, s2)
            mm = lambda key, arms: mean([m[key] for m in arms if m.get(key) is not None]) if any(m.get(key) is not None for m in arms) else None
            pe = mean([path_err(h, m) for m in c2])
            gres.append(h[y] - v2)
            extra.append({'table': 'G', 'mid': k[0], 't0': k[1], 't1': e['meta']['t1'], 'variant': 'free-run', 'hist': h[y], 'C0': c0[0][y], 'C1': v1, 'C1sd': s1, 'C2w': vw, 'C2': v2, 'C2sd': s2, 'n': len(c2), 'truncated': int(bool(e['meta'].get('truncated')))})
            P(f"| {k[0]} | {GROUP.get(k[0], '')} | {fmt(h[y])} | {fmt(c0[0][y])} | {fmt(v1)} ±{fmt(s1)} | {(fmt(vw) + ' ±' + fmt(sw)) if c2w else '= C2'} | {fmt(v2)} ±{fmt(s2)} | {fmt(h[y] - v2, 3, True)} | {f2(pe, 3)} | {h['alive1']} / {f2(mm('alive1', c2), 1)} | {h['recorded']} / {f2(mm('recorded', c2), 0)} | {f2(h.get('batchShare'))} / {f2(mm('batchShare', c2))} | {f2(h.get('dupShare'))} / {f2(mm('dupShare', c2))} | {f2(h.get('atkVoidRate'))} / {f2(mm('atkVoidRate', c2))} |")
        if gres:
            P('')
            P(f"{len(gres)} 局：残差均值 {mean(gres):+.3f}，|残差| 均值 {mean([abs(x) for x in gres]):.3f}，|残差| 中位 {quart([abs(x) for x in gres])[1]:.3f}。")
        P('')

    # ---- 敏感度：换阶梯来源、换补法
    T = load(r'r06trace[a-z]')
    if T:
        P('### 表 S1　C2 档的实录阶梯换成 R06 入库的那一份（另一套影子、另一套配对）')
        P('')
        P('| 局 | 窗口 | 历史 | C2（R01 的阶梯，±sd） | C2（R06 的阶梯，±sd） | 两份阶梯之差 | 残差 历史−C2：R01 / R06 |')
        P('| :-- | :-- | --: | --: | --: | --: | :-- |')
        for k in sorted(T, key=lambda k: (MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99, k[1])):
            e = T[k]; h = e['history']
            c2b = seeds(e, 'C2')
            c2a = seeds(R[k], 'C2') if k in R else []
            if not (c2a and c2b):
                continue
            y = 'relTerr1'
            va, sa = mean([m[y] for m in c2a]), sd([m[y] for m in c2a])
            vb, sb = mean([m[y] for m in c2b]), sd([m[y] for m in c2b])
            extra.append({'table': 'S1', 'mid': k[0], 't0': k[1], 't1': e['meta']['t1'], 'variant': 'r06trace', 'hist': h[y], 'C0': None, 'C1': None, 'C1sd': None, 'C2w': None, 'C2': vb, 'C2sd': sb, 'n': len(c2b), 'truncated': int(bool(e['meta'].get('truncated')))})
            P(f"| {k[0]} | {WN.get(k[1], k[1])} | {fmt(h[y])} | {fmt(va)} ±{fmt(sa)} | {fmt(vb)} ±{fmt(sb)} | {fmt(vb - va, 3, True)} | {fmt(h[y] - va, 3, True)} / {fmt(h[y] - vb, 3, True)} |")
        P('')
    F = load(r'fill(nearest|linear)[a-z]', keyfn=lambda d, tag: (d['match'], d['t0'], d.get('fill')))
    if F:
        P('### 表 S2　C2 档已知点之间的补法：auto（主口径）/ nearest / linear')
        P('')
        P('| 局 | 窗口 | 历史 | C2 auto（±sd） | C2 nearest（±sd） | C2 linear（±sd） | 三种补法的极差 |')
        P('| :-- | :-- | --: | --: | --: | --: | --: |')
        for k2 in sorted({(k[0], k[1]) for k in F}, key=lambda k: (MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99, k[1])):
            if k2 not in R:
                continue
            y = 'relTerr1'
            cells = {}
            base = seeds(R[k2], 'C2')
            if base:
                cells['auto'] = (mean([m[y] for m in base]), sd([m[y] for m in base]))
            for fl in ('nearest', 'linear'):
                e = F.get((k2[0], k2[1], fl))
                a = seeds(e, 'C2') if e else []
                if a:
                    cells[fl] = (mean([m[y] for m in a]), sd([m[y] for m in a]))
                    extra.append({'table': 'S2', 'mid': k2[0], 't0': k2[1], 't1': e['meta']['t1'], 'variant': f'fill={fl}', 'hist': R[k2]['history'][y], 'C0': None, 'C1': None, 'C1sd': None, 'C2w': None, 'C2': cells[fl][0], 'C2sd': cells[fl][1], 'n': len(a), 'truncated': int(bool(e['meta'].get('truncated')))})
            vals = [v[0] for v in cells.values()]
            cell = lambda fl: f"{fmt(cells[fl][0])} ±{fmt(cells[fl][1])}" if fl in cells else '-'
            P(f"| {k2[0]} | {WN.get(k2[1], k2[1])} | {fmt(R[k2]['history'][y])} | {cell('auto')} | {cell('nearest')} | {cell('linear')} | {fmt(max(vals) - min(vals)) if len(vals) > 1 else '-'} |")
        P('')

    # ---- 敏感度：实录阶梯的上下界（定位不唯一的落地指令取最早 / 最晚放得下的决策）
    nband = {v: sum(1 for r in DV[v] if r['variantRerun']) for v in ('hi', 'lo')}
    if nband['hi'] or nband['lo']:
        P('### 表 T　实录阶梯的三种口径：只收唯一定位的（主口径）/ 加上定位不唯一的、取最早放得下的决策（上界）/ 取最晚放得下的（下界）')
        P('')
        P('| 局 | 窗口 | 历史 | 窗口内落后 P75：主 / 上界 / 下界 | C2w：主 / 上界 / 下界 | C2：主 / 上界 / 下界 | 落后波 C2w−C1：主 / 上界 / 下界 | 页面/掉线：主 / 上界 / 下界 | 残差 历史−C2：主 / 上界 / 下界 | C2 噪声底 sd：主 / 上界 / 下界 |')
        P('| :-- | :-- | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |')
        idx = {v: {(r['mid'], r['t0']): r for r in DV[v]} for v in DV}
        y = 'relTerr1'
        trip = lambda k, col, nd=3, sign=False: ' / '.join(fmt(idx[v][k][col], nd, sign) if k in idx[v] else '-' for v in ('located', 'hi', 'lo'))
        for r in DV['located']:
            k = (r['mid'], r['t0'])
            if not any(k in idx[v] and idx[v][k]['variantRerun'] for v in ('hi', 'lo')):
                continue
            lag3 = ' / '.join(str(idx[v][k]['lagP75']) if k in idx[v] else '-' for v in ('located', 'hi', 'lo'))
            P(f"| {r['mid']} | {WN.get(r['t0'], r['t0'])} | {fmt(r[y + '_hist'])} | {lag3} | {trip(k, y + '_C2w')} | {trip(k, y + '_C2')} | {trip(k, y + '_wave', 3, True)} | {trip(k, y + '_page', 3, True)} | {trip(k, y + '_resid', 3, True)} | {trip(k, y + '_C2sd')} |")
            for v in ('hi', 'lo'):
                rv = idx[v].get(k)
                if rv and rv['variantRerun']:
                    extra.append({'table': 'T', 'mid': r['mid'], 't0': r['t0'], 't1': r['t1'], 'variant': f'trace-{v}', 'hist': r[y + '_hist'], 'C0': None, 'C1': None, 'C1sd': None, 'C2w': rv[y + '_C2w'], 'C2': rv[y + '_C2'], 'C2sd': rv[y + '_C2sd'], 'n': rv['nC2'], 'truncated': int(bool(rv['truncated']))})
        P('')
        P(f"重跑的（局, 窗口）：上界 {nband['hi']} 个、下界 {nband['lo']} 个；没重跑的窗口（这一口径在窗口里没有多出条目）沿用主口径的数。")
        P('')
        P('| 窗口 | 局数 | 落后波 均值：主 / 上界 / 下界 | 页面/掉线 均值：主 / 上界 / 下界 | 残差 均值：主 / 上界 / 下界 | \\|残差\\| 均值：主 / 上界 / 下界 | \\|残差\\| 中位：主 / 上界 / 下界 |')
        P('| :-- | --: | :-- | :-- | :-- | :-- | :-- |')
        for t0 in sorted(WN):
            ks = [(r['mid'], r['t0']) for r in DV['located'] if r['t0'] == t0 and all((r['mid'], r['t0']) in idx[v] for v in DV)]
            if not ks:
                continue
            m3 = lambda col, f=lambda x: x: ' / '.join(fmt(mean([f(idx[v][k][col]) for k in ks]), 3, f is not abs) for v in ('located', 'hi', 'lo'))
            md3 = ' / '.join(fmt(quart([abs(idx[v][k][y + '_resid']) for k in ks])[1]) for v in ('located', 'hi', 'lo'))
            P(f"| {WN[t0]} | {len(ks)} | {m3(y + '_wave')} | {m3(y + '_page')} | {m3(y + '_resid')} | {m3(y + '_resid', abs)} | {md3} |")
        P('')
        # 三种口径各自的对数链（用同一组窗口：任一口径下掉出链的窗口，三种口径都不算）
        cuts = {}
        for v in DV:
            for m, t in chain_of(DV[v])[1].items():
                cuts[m] = min(cuts.get(m, 10 ** 9), t)
        CH = {v: chain_of(DV[v], cuts)[0] for v in DV}
        P('| 组 | 局数 | 落后波（ln）：主 / 上界 / 下界 | 页面/掉线（ln）：主 / 上界 / 下界 | 残差（ln）：主 / 上界 / 下界 | 落后波+页面（ln）：主 / 上界 / 下界 |')
        P('| :-- | --: | :-- | :-- | :-- | :-- |')
        for g in GROUP_ORDER + ['A 局（c116 家族）', '全部']:
            ms = [m for m in CH['located'] if all(m in CH[v] and CH[v][m]['n'] == CH['located'][m]['n'] for v in DV) and (g == '全部' or GROUP[m] == g or (g.startswith('A 局') and m.startswith('A')))]
            if not ms:
                continue
            c3 = lambda f: ' / '.join(fmt(mean([f(CH[v][m]) for m in ms]), 3, True) for v in ('located', 'hi', 'lo'))
            P(f"| {g} | {len(ms)} | {c3(lambda c: c['wave'])} | {c3(lambda c: c['page'])} | {c3(lambda c: c['resid'])} | {c3(lambda c: c['wave'] + c['page'])} |")
        P('')

    # ---- 敏感度：落后波与页面停摆两段的先后次序（C1p = 基础延迟 + 实录页面寿命，不带落后波）
    O = [(k, R[k]) for k in keys if seeds(R[k], 'C1p') and seeds(R[k], 'C2w') and seeds(R[k], 'C1') and seeds(R[k], 'C2')]
    if O:
        P('### 表 O　落后波与页面/掉线两段的先后次序：四个角（C1、C1 + 页面、C1 + 落后波、两样都有）')
        P('')
        P('| 局 | 窗口 | C1 | C1p（只加页面/掉线） | C2w（只加落后波） | C2（两样都加） | 落后波：先加 C2w−C1 | 落后波：后加 C2−C1p | 页面：先加 C1p−C1 | 页面：后加 C2−C2w | 交互项 | 两种次序平均：落后波 / 页面 |')
        P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | :-- |')
        acc = []
        for k, e in O:
            y = 'relTerr1'
            a = {nm: mean([m[y] for m in seeds(e, nm)]) for nm in ('C1', 'C1p', 'C2w', 'C2')}
            w1, w2 = a['C2w'] - a['C1'], a['C2'] - a['C1p']
            p1, p2 = a['C1p'] - a['C1'], a['C2'] - a['C2w']
            acc.append((w1, w2, p1, p2))
            extra.append({'table': 'O', 'mid': k[0], 't0': k[1], 't1': e['meta']['t1'], 'variant': 'C1p', 'hist': e['history'][y], 'C0': None, 'C1': a['C1'], 'C1sd': sd([m[y] for m in seeds(e, 'C1')]), 'C2w': a['C2w'], 'C2': a['C1p'], 'C2sd': sd([m[y] for m in seeds(e, 'C1p')]), 'n': len(seeds(e, 'C1p')), 'truncated': int(bool(e['meta'].get('truncated')))})
            P(f"| {k[0]} | {WN.get(k[1], k[1])} | {fmt(a['C1'])} | {fmt(a['C1p'])} | {fmt(a['C2w'])} | {fmt(a['C2'])} | {fmt(w1, 3, True)} | {fmt(w2, 3, True)} | {fmt(p1, 3, True)} | {fmt(p2, 3, True)} | {fmt(p2 - p1, 3, True)} | {fmt((w1 + w2) / 2, 3, True)} / {fmt((p1 + p2) / 2, 3, True)} |")
        P('')
        n = len(acc)
        P(f"{n} 个（局, 窗口）的均值：落后波 先加 {mean([x[0] for x in acc]):+.3f} / 后加 {mean([x[1] for x in acc]):+.3f}；页面/掉线 先加 {mean([x[2] for x in acc]):+.3f} / 后加 {mean([x[3] for x in acc]):+.3f}；"
          f"交互项均值 {mean([x[3] - x[2] for x in acc]):+.3f}，|交互项| 均值 {mean([abs(x[3] - x[2]) for x in acc]):.3f}。")
        P('')

    # ---- 历史版本互换（只在 c116 家族内：Va / Vb / Vc）
    V = load(r'(va|vb|vc)[a-z]', historical=False, keyfn=lambda d, tag: (d['match'], d['t0'], d.get('stratKey')))
    if V:
        P('### 表 V　同一断面、同一通道下，把我方换成另一个历史版本（Va / Vb / Vc 互换）：窗口末人均相对领土')
        P('')
        P('| 局 | 当年版本 | 窗口 | C1：Va | C1：Vb | C1：Vc | C2：Va | C2：Vb | C2：Vc | 版本间极差 C1 / C2 | 同窗口的通道效应 \\|C1−C0\\| / \\|C2−C1\\| |')
        P('| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | :-- | :-- |')
        vsum = {}
        for k2 in sorted({(k[0], k[1]) for k in V}, key=lambda k: (MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99, k[1])):
            if k2 not in R:
                continue
            y = 'relTerr1'
            hv = R[k2]['meta'].get('stratKey') or ''
            cells = {}
            for ver in ('va', 'vb', 'vc'):
                e = R[k2] if ver == hv else V.get((k2[0], k2[1], ver))
                if not e:
                    continue
                for ch in ('C1', 'C2'):
                    a = seeds(e, ch)
                    if a:
                        cells[(ch, ver)] = (mean([m[y] for m in a]), sd([m[y] for m in a]), len(a))
                        if ver != hv:
                            extra.append({'table': 'V', 'mid': k2[0], 't0': k2[1], 't1': e['meta']['t1'], 'variant': f'{ver}:{ch}', 'hist': R[k2]['history'][y], 'C0': None, 'C1': cells[(ch, ver)][0] if ch == 'C1' else None, 'C1sd': cells[(ch, ver)][1] if ch == 'C1' else None, 'C2w': None, 'C2': cells[(ch, ver)][0] if ch == 'C2' else None, 'C2sd': cells[(ch, ver)][1] if ch == 'C2' else None, 'n': len(a), 'truncated': int(bool(e['meta'].get('truncated')))})
            cell = lambda ch, ver: (f"{'**' if ver == hv else ''}{fmt(cells[(ch, ver)][0])}{'**' if ver == hv else ''} ±{fmt(cells[(ch, ver)][1])}") if (ch, ver) in cells else '-'
            rng = lambda ch: (lambda v: fmt(max(v) - min(v)) if len(v) > 1 else '-')([cells[(ch, ver)][0] for ver in ('va', 'vb', 'vc') if (ch, ver) in cells])
            dr = next((r for r in D if r['mid'] == k2[0] and r['t0'] == k2[1]), None)
            eff = f"{fmt(abs(dr['relTerr1_base']))} / {fmt(abs(dr['relTerr1_C2'] - dr['relTerr1_C1']))}" if dr else '-'
            P(f"| {k2[0]} | {hv.capitalize()} | {WN.get(k2[1], k2[1])} | {cell('C1', 'va')} | {cell('C1', 'vb')} | {cell('C1', 'vc')} | {cell('C2', 'va')} | {cell('C2', 'vb')} | {cell('C2', 'vc')} | {rng('C1')} / {rng('C2')} | {eff} |")
            for ch in ('C1', 'C2'):
                for a_, b_ in (('va', 'vb'), ('vc', 'vb'), ('vc', 'va')):
                    if (ch, a_) in cells and (ch, b_) in cells:
                        vsum.setdefault((k2[1], ch, a_, b_), []).append((cells[(ch, a_)][0] - cells[(ch, b_)][0], math.sqrt((cells[(ch, a_)][1] ** 2 + cells[(ch, b_)][1] ** 2) / 3), k2[0]))
        P('')
        P('| 窗口 | 通道 | 对比 | 局数 | 差的均值 | 差的中位 | 同号局数（+ / −） | \\|差\\| 均值 | 种子噪声（差的标准误，均值） | 同窗口通道效应均值：基础延迟 / 落后波+页面 |')
        P('| :-- | :-- | :-- | --: | --: | --: | :-- | --: | --: | :-- |')
        for (t0, ch, a_, b_), v in sorted(vsum.items()):
            ds = [x[0] for x in v]
            mids = {x[2] for x in v}
            rows = [r for r in D if r['t0'] == t0 and r['mid'] in mids]
            eff = f"{fmt(mean([r['relTerr1_base'] for r in rows]), 3, True)} / {fmt(mean([r['relTerr1_C2'] - r['relTerr1_C1'] for r in rows]), 3, True)}" if rows else '-'
            P(f"| {WN.get(t0, t0)} | {ch} | {a_.capitalize()} − {b_.capitalize()} | {len(ds)} | {fmt(mean(ds), 3, True)} | {fmt(quart(ds)[1], 3, True)} | {sum(1 for d in ds if d > 0)} / {sum(1 for d in ds if d < 0)} | {fmt(mean([abs(d) for d in ds]))} | {fmt(mean([x[1] for x in v]))} | {eff} |")
        P('')

    if extra:
        with open(os.path.join(DST, 'ckpt_extra.csv'), 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(extra[0].keys()))
            w.writeheader()
            for r in extra:
                w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})

    open(os.path.join(DST, 'ckpt_tables.md'), 'w').write('\n'.join(L) + '\n')
    print(f'{len(R)} 个（局, 断面），{sum(len(e["arms"]) for e in R.values())} 条臂；分解 {len(D)} 行 → reports/ckpt-data/ckpt_arms.csv、ckpt_decomp.csv、ckpt_tables.md'
          f'；附加：放开跑 {len(G)}、换阶梯 {len(T)}、换补法 {len(F)}、换版本 {len(V)}')
    for nm, X in (('放开跑', G), ('换阶梯', T), ('换补法', F), ('换版本', V)):
        tb = [k for k, e in X.items() if e['meta'].get('truncated') or e['meta'].get('t1mismatch')]
        if tb:
            print(f'{nm}里被截断的：', tb)
    bad = [k for k, e in R.items() if e['meta'].get('truncated') or e['meta'].get('t1mismatch')]
    if bad:
        print('被时间预算截断 / 各块停在不同拍的：', bad)
    missing = [k for k, e in R.items() if not (seeds(e, 'C0') and len(seeds(e, 'C1')) >= 3 and len(seeds(e, 'C2')) >= 3)]
    if missing:
        print('臂还没跑全的：', missing)


if __name__ == '__main__':
    main()
