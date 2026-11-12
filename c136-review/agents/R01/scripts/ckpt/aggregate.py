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
WEND = {0: 630, 630: 1500, 1500: 3213, 3213: 4284, 4284: 5184}
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


def band_selected():
    f = os.path.join(DST, 'band_select.csv')
    if not os.path.exists(f):
        return set()
    return {(r['mid'], int(r['t0']), r['variant']) for r in csv.DictReader(open(f)) if r['rerun'] == '1'}


BAND_SEL = set()


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
        if b and b['meta']['t1'] == e['meta']['t1'] and len(seeds(b, 'C2')) >= len(c2) and len(seeds(b, 'C2w')) >= len(c2w_sep):
            c2 = seeds(b, 'C2')
            c2w_sep = seeds(b, 'C2w')
            rerun = True
        # 这一口径在这个窗口里的阶梯与主口径不同（band_select.csv 选中了）但还没跑出来：先沿用主口径的数，打上标记
        pending = (not rerun) and ((k[0], k[1], variant) in BAND_SEL)
        c2w = c2w_sep or c2
        if not (c0 and c1 and c2):
            continue
        row = {'mid': k[0], 'group': GROUP.get(k[0], ''), 't0': k[1], 't1': e['meta']['t1'], 'seats': len(e['meta']['squad']), 'alive0': h['alive0'], 'c2wSeparate': bool(c2w_sep),
               'variant': variant, 'variantRerun': rerun, 'variantPending': pending,
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
        row['othersReroute_C1'] = mean([(m['others']['rerouted'] + m['others']['dropped']) / max(1, m['others']['atk']) for m in c1])
        row['othersAtk'] = c0[0]['others']['atk']
        # 合计口径用的原始量（各臂取种子均值）：逐人领土对历史的 L1、历史合计
        for nm, arms in (('C0', c0), ('C1', c1), ('C2', c2)):
            row[f'othersL1raw_{nm}'] = mean([m['div']['othersL1'] for m in arms])
            row[f'squadL1raw_{nm}'] = mean([m['div']['squadL1'] for m in arms])
        row['othersHistRaw'] = c0[0]['div']['othersHist']
        row['squadHistRaw'] = c0[0]['div']['squadHist']
        # 残差里有多少来自「某个席位在历史里出局了、在 C2 里没出局（或反过来）」这种一次性的生死事件
        hs = {x['p']: x for x in h['perSeat']}
        td = fl = nf = 0
        for m in c2:
            for x in m['perSeat']:
                dlt = hs[x['p']]['terr1'] - x['terr1']
                td += dlt
                if (hs[x['p']]['terr1'] == 0) != (x['terr1'] == 0):
                    fl += dlt; nf += 1
        row['terrDiff_C2'] = td / len(c2); row['flipTerr_C2'] = fl / len(c2); row['flipSeats_C2'] = nf / len(c2)
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
    BAND_SEL.update(band_selected())
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
    # ---- 局的清单（报告正文用）
    fb = {r['mid']: r for r in csv.DictReader(open(os.path.join(DST, 'fid_base.csv')))} if os.path.exists(os.path.join(DST, 'fid_base.csv')) else {}
    fc = {r['mid']: r for r in csv.DictReader(open(os.path.join(DST, 'fid_channel.csv')))} if os.path.exists(os.path.join(DST, 'fid_channel.csv')) else {}
    P('### 表 M　用到的 14 局')
    P('')
    P('| 局 | 组 | 当年版本 | 我方席位 / 真人 | 指令落后 P50 / P75 / P90（拍） | 页面中途停摆的席位 | 历史的人均相对领土：开局 → 630 → 1500 → 3213 → 4284 → 5184 |')
    P('| :-- | :-- | :-- | :-- | :-- | --: | :-- |')
    for mid in MID_ORDER:
        rs = sorted([r for r in D if r['mid'] == mid], key=lambda r: r['t0'])
        if not rs:
            continue
        b, c = fb.get(mid, {}), fc.get(mid, {})
        ver = (R[(mid, rs[0]['t0'])]['meta'].get('stratKey') or '')
        ver = 'c110' if ver == 'c110' else ver.capitalize()
        tr = ' → '.join([fmt(rs[0]['relTerr1_start'])] + [fmt(r['relTerr1_hist']) + (f"（到 {r['t1']}）" if r['t1'] != WEND.get(r['t0'], r['t1']) else '') for r in rs])
        P(f"| {mid} | {GROUP.get(mid, '')} | {ver} | {rs[0]['seats']} / {b.get('humans', '-')} | {c.get('lagP50', '-')} / {c.get('lagP75', '-')} / {c.get('lagP90', '-')} | {b.get('doomedSeats', '-')} | {tr} |")
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

    # 同一条链按窗口看：进了链的窗口里，每个窗口的 ln 各段在各局上的均值（→ 各段落在哪个时段）
    P('### 表 C2　同一条链按窗口看：各窗口 ln(人均相对领土) 的变化与五段（进了链的窗口；各局均值；括号里是换回倍数）')
    P('')
    P('| 组 | 窗口 | 局数 | 历史 ln 变化 | 健康通道（C1）下的 ln 变化 = 规则 + 基础延迟 | 其中规则（C0） | 基础延迟 | 落后波 | 页面/掉线 | 残差 |')
    P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |')
    lnx = math.log
    for g in ['通道干净', '浅落后', '深落后', 'c110 深落后', '全部']:
        for t0 in sorted(WN):
            rs = [r for m, use in chain_use.items() for r in use if r['t0'] == t0 and (g == '全部' or GROUP[m] == g)]
            if not rs:
                continue
            y = 'relTerr1'
            mm = lambda f: mean([f(r) for r in rs])
            tot = mm(lambda r: lnx(r[f'{y}_hist'] / r[f'{y}_start']))
            rules = mm(lambda r: lnx(r[f'{y}_C0'] / r[f'{y}_start']))
            base = mm(lambda r: lnx(r[f'{y}_C1'] / r[f'{y}_C0']))
            wave = mm(lambda r: lnx(r[f'{y}_C2w'] / r[f'{y}_C1']))
            page = mm(lambda r: lnx(r[f'{y}_C2'] / r[f'{y}_C2w']))
            resid = mm(lambda r: lnx(r[f'{y}_hist'] / r[f'{y}_C2']))
            x = lambda v: f"{fmt(v, 3, True)}（×{math.exp(v):.2f}）"
            P(f"| {g} | {WN[t0]} | {len(rs)} | {x(tot)} | {x(rules + base)} | {fmt(rules, 3, True)} | {fmt(base, 3, True)} | {x(wave)} | {x(page)} | {x(resid)} |")
    P('')
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
    # 粗外推：按全量 squad10 各局的通道状况占比给三组加权（通道状况用 M6 的 600–1500 拍落地率：≥ 0.9 干净、0.7–0.9 浅落后、< 0.7 深落后）
    jf = os.path.join(R01, 'reports', 'm6-data', 'joined.csv')
    if os.path.exists(jf):
        cnt = {'通道干净': 0, '浅落后': 0, '深落后': 0}
        for r in csv.DictReader(open(jf)):
            try:
                x = float(r['nd600_1500'])
            except ValueError:
                continue
            if r['cohort'] != 'squad10' or r['multi'] != '0':
                continue
            cnt['通道干净' if x >= 0.9 else '深落后' if x < 0.7 else '浅落后'] += 1
        n = sum(cnt.values())
        segs = []
        for y, label in (('relTerr1', '人均相对领土'), ('wealth1', '兵力')):
            hr = {r['group']: r for r in head_rows if r['y'] == y}
            if not all(g in hr for g in cnt) or not n:
                continue
            wsum = lambda key: sum(cnt[g] * math.log(hr[g][key]) for g in cnt) / n
            lw, lp, lr = wsum('wave'), wsum('page'), wsum('resid')
            segs.append(f"{label} 历史 ÷ C1 路径 ×{math.exp(lw + lp + lr):.2f}（落后波 ×{math.exp(lw):.2f}、页面/掉线 ×{math.exp(lp):.2f}、残差 ×{math.exp(lr):.2f}）")
            head_rows.append({'group': f'按全量 squad10 加权（{cnt["通道干净"]}/{cnt["浅落后"]}/{cnt["深落后"]}）', 'n': n, 'y': y, 'histOverC1': math.exp(lw + lp + lr), 'wave': math.exp(lw), 'page': math.exp(lp), 'resid': math.exp(lr),
                              'lnWavePage': lw + lp, 'ciLo': None, 'ciHi': None, 'c1OverC0': None})
        if segs:
            P(f"粗外推：全量 10 人编队局里有可比数据的 {n} 局，按 600–1500 拍进攻指令的「落地 ÷ 放行」分档，≥ 0.9 的 {cnt['通道干净']} 局、0.7–0.9 的 {cnt['浅落后']} 局、< 0.7 的 {cnt['深落后']} 局"
              f"（`reports/m6-data/joined.csv`）。把上表 A 局三组的 ln 均值按这个占比加权：" + '；'.join(segs) + '。'
              '前提是本报告每组的 3–6 局能代表全量里同一档的局，这一点没有验证。')
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

    P('### 表 R　残差最大的窗口：差在哪（历史 − C2 的我方领土，其中来自「生死不同」席位的部分）')
    P('')
    P('「生死不同」的席位 = 这个席位窗口末在历史里没有领土、在 C2 臂里还有（或反过来）。这类差是一次性的生死事件带来的（一块空壳被吃掉没有、一个席位被打死没有），'
      '不是指令流逐条的差。')
    P('')
    P('| 局 | 窗口 | 残差（历史 − C2，人均相对领土） | C2 噪声底 sd | 领土差（历史 − C2，格） | 其中生死不同的席位贡献（格） | 生死不同的席位数（3 个种子的均值） | 窗口内阶梯平均落后（拍） |')
    P('| :-- | :-- | --: | --: | --: | --: | --: | --: |')
    big = sorted([r for r in D if abs(r['relTerr1_resid']) >= 0.04], key=lambda r: -abs(r['relTerr1_resid']))
    for r in big:
        P(f"| {r['mid']} | {WN[r['t0']]} | {fmt(r['relTerr1_resid'], 3, True)} | {fmt(r['relTerr1_C2sd'])} | {r['terrDiff_C2']:+.0f} | {r['flipTerr_C2']:+.0f} | {r['flipSeats_C2']:.1f} | {f2(r['lagStairMean'], 0)} |")
    tot = sum(abs(r['relTerr1_resid']) for r in D)
    nb = len(big); wf = [r for r in big if r['flipSeats_C2'] > 0]; nfw = [r for r in big if r['flipSeats_C2'] == 0]
    small = [r for r in D if abs(r['relTerr1_resid']) < 0.04]
    P('')
    if big:
        P(f"{len(D)} 个（局, 窗口）的 |残差| 合计 {tot:.3f}，其中这 {nb} 个占 {sum(abs(r['relTerr1_resid']) for r in big) / max(1e-9, tot) * 100:.0f}%。"
          f"{len(wf)} 个有生死不同的席位（它们的领土差里 {sum(r['flipTerr_C2'] for r in wf) / min(-1e-9, sum(r['terrDiff_C2'] for r in wf)) * 100 if sum(r['terrDiff_C2'] for r in wf) < 0 else float('nan'):.0f}% 来自这些席位）；"
          f"另外 {len(nfw)} 个没有，其中 {sum(1 for r in nfw if r['relTerr1_resid'] < 0)} 个是历史低于 C2。"
          f"其余 {len(small)} 个窗口里有生死不同席位的 {sum(1 for r in small if r['flipSeats_C2'] > 0)} 个，|残差| 中位 {quart([abs(r['relTerr1_resid']) for r in small])[1]:.3f}。")
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
    P('### 表 P　对手是开环的：各臂里其余真人的录像指令还照原样执行了多少、他们的领土偏离历史多少')
    P('')
    P('其余真人在每条臂里都只是照录像出手（目标已经不存在或不相邻时改打最便宜的邻居，再不行就作废）。我方变强以后他们不会改主意，'
      '所以「改打或作废」的比例越高、他们的领土偏离历史越多，这条臂离「对手会怎么应对」就越远。')
    P('')
    P('| 窗口 | 局数 | 其余真人的陆攻（条，各局合计） | 改打或作废（各局比例的均值）：C0 / C1 / C2 | 其余真人逐人领土 L1 ÷ 历史（各局合计）：C0 / C1 / C2 | 我方逐席领土 L1 ÷ 历史（各局合计）：C0 / C1 / C2 |')
    P('| :-- | --: | --: | :-- | :-- | :-- |')
    for t0 in sorted(WN):
        rows = [r for r in D if r['t0'] == t0]
        if not rows:
            continue
        av = lambda k: mean([r[k] for r in rows if r.get(k) is not None])
        pool = lambda k, d: sum(r[k] for r in rows) / max(1, sum(r[d] for r in rows))
        P(f"| {WN[t0]} | {len(rows)} | {sum(r['othersAtk'] for r in rows)} | {av('othersReroute_C0') * 100:.1f}% / {av('othersReroute_C1') * 100:.1f}% / {av('othersReroute_C2') * 100:.1f}% | "
          f"{pool('othersL1raw_C0', 'othersHistRaw'):.3f} / {pool('othersL1raw_C1', 'othersHistRaw'):.3f} / {pool('othersL1raw_C2', 'othersHistRaw'):.3f} | "
          f"{pool('squadL1raw_C0', 'squadHistRaw'):.2f} / {pool('squadL1raw_C1', 'squadHistRaw'):.2f} / {pool('squadL1raw_C2', 'squadHistRaw'):.2f} |")
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

    # ---- 连乘的前提：窗口内的涨幅与起点水平无关。跨局看这个前提成不成立，并按跨局斜率给 C1 路径一个粗修正
    def ols(x, y):
        n = len(x)
        mx, my = mean(x), mean(y)
        sxx = sum((a - mx) ** 2 for a in x)
        syy = sum((b - my) ** 2 for b in y)
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
        if n < 4 or sxx <= 0 or syy <= 0:
            return None
        b = sxy / sxx
        a = my - b * mx
        s2 = sum((yy - (a + b * xx)) ** 2 for xx, yy in zip(x, y)) / (n - 2)
        return b, math.sqrt(s2 / sxx), sxy / math.sqrt(sxx * syy), n
    P('### 表 K　连乘的前提：窗口内的涨幅和起点水平有没有关系（跨局回归 ln(窗口末 ÷ 起点) 对 ln(起点)；起点都是历史的断面值）')
    P('')
    P('| 窗口 | 局数 | 历史：斜率 ± 标准误（相关系数） | C2 | C1 | C0 |')
    P('| :-- | --: | :-- | :-- | :-- | :-- |')
    slope = {}
    adj_path = None
    for t0 in (630, 1500, 3213, 4284):
        rs = [r for m, use in chain_use.items() for r in use if r['t0'] == t0]
        cells = []
        for arm in ('hist', 'C2', 'C1', 'C0'):
            o = ols([math.log(r['relTerr1_start']) for r in rs], [math.log(r[f'relTerr1_{arm}'] / r['relTerr1_start']) for r in rs])
            if arm == 'C1' and o:
                slope[t0] = o
            cells.append(f"{o[0]:+.2f} ± {o[1]:.2f}（{o[2]:+.2f}）" if o else '-')
        P(f"| {WN[t0]} | {len(rs)} | " + ' | '.join(cells) + ' |')
    P('')
    P('斜率 0 = 涨幅与起点无关（连乘成立）；−1 = 窗口末的水平与起点无关（之前亏的在这个窗口里全补回来，连乘会把之前的亏重复算进去）。'
      '这是跨局的关系，起点低的局同时也是落后重的局，不能直接当成同一局里的因果；局数少，标准误大。')
    P('')
    if slope:
        def adj_path(mid, upto, k=0.0):
            # k = 斜率取 估计值 + k × 标准误
            use = [r for r in chain_use.get(mid, []) if r['t1'] <= upto]
            if not use or use[-1]['t1'] != upto:
                return None
            Pl = None
            for r in use:
                H = r['relTerr1_start']
                Pl = H if Pl is None else Pl
                b = (slope[r['t0']][0] + k * slope[r['t0']][1]) if r['t0'] in slope else 0.0
                Pl = Pl * (r['relTerr1_C1'] / H) * (Pl / H) ** b
            return Pl
        def chain_path(mid, upto, arm):
            use = [r for r in chain_use.get(mid, []) if r['t1'] <= upto]
            if not use or use[-1]['t1'] != upto:
                return None
            v = use[0]['relTerr1_start']
            for r in use:
                v *= r[f'relTerr1_{arm}'] / r['relTerr1_start']
            return v
        P('按这些斜率给 C1 路径做一个粗修正：每个窗口的 C1 涨幅乘上（修正后的起点 ÷ 历史起点）^斜率，再往下接。几何均值：')
        P('')
        P('| 组 | 断面 | 局数 | 历史 ÷ C1 路径（连乘） | 历史 ÷ C1 路径（按斜率修正；括号里斜率取 ±1 个标准误） | 修正后的 C1 路径 ÷ 连乘的 C1 路径 |')
        P('| :-- | :-- | --: | --: | :-- | --: |')
        adj_rows = []
        for g in GROUP_ORDER + ['全部']:
            for upto in (1500, 3213, 5184):
                pts = []
                for m in chain_use:
                    if not (g == '全部' or GROUP[m] == g):
                        continue
                    hv, cv, av, lo, hi = chain_path(m, upto, 'hist'), chain_path(m, upto, 'C1'), adj_path(m, upto), adj_path(m, upto, -1), adj_path(m, upto, 1)
                    if None in (hv, cv, av, lo, hi):
                        continue
                    pts.append((hv, cv, av, lo, hi))
                if len(pts) < 2:
                    continue
                gm = lambda f: math.exp(mean([math.log(f(x)) for x in pts]))
                a, b, c1, c2 = gm(lambda x: x[0] / x[1]), gm(lambda x: x[0] / x[2]), gm(lambda x: x[0] / x[3]), gm(lambda x: x[0] / x[4])
                adj_rows.append({'group': g, 'at': upto, 'n': len(pts), 'histOverC1chain': a, 'histOverC1adj': b, 'adjLo': min(c1, c2), 'adjHi': max(c1, c2), 'adjOverChain': gm(lambda x: x[2] / x[1])})
                P(f"| {g} | t={upto} | {len(pts)} | ×{a:.2f} | ×{b:.2f}（×{min(c1, c2):.2f} ~ ×{max(c1, c2):.2f}） | ×{gm(lambda x: x[2] / x[1]):.2f} |")
        P('')
        if adj_rows:
            with open(os.path.join(DST, 'ckpt_chainadj.csv'), 'w', newline='') as fo:
                w = csv.DictWriter(fo, fieldnames=list(adj_rows[0].keys()))
                w.writeheader()
                for r in adj_rows:
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

        # ---- 反事实的水平对不对得上真实的通道干净局：把各臂从开局一路串到 1500 / 3213 拍的人均相对领土，和 R06 实盘区间里「通道干净」那一档比
        byk = {(r['mid'], r['t0']): r for r in D}
        def path_level(mid, arm, upto):
            lv = None
            for t0 in (0, 630, 1500):
                if t0 >= upto:
                    break
                r = byk.get((mid, t0))
                if not r or r.get('truncated') or not r.get('relTerr1_start') or r.get(f'relTerr1_{arm}') is None:
                    return None
                lv = (r['relTerr1_start'] if lv is None else lv) * r[f'relTerr1_{arm}'] / r['relTerr1_start']
            return lv
        P('### 表 L　反事实的水平对照：各臂从开局串到 1500 / 3213 拍的人均相对领土，对照 R06 实盘区间（同版本的全部合格历史局）')
        P('')
        P('| 版本 × 卡顿档（本报告的局） | 断面 | 局数 | 历史 中位 | C2 路径 中位 | C1 路径 中位 | C0 路径 中位 | 实盘同档区间 P25 / 中位 / P75（局数） | 实盘「通道干净」档区间（局数） | C1 路径逐局：低于 / 落在 / 高于 干净档区间 | 历史逐局：低于 / 落在 / 高于 干净档区间 |')
        P('| :-- | :-- | --: | --: | --: | --: | --: | :-- | :-- | :-- | :-- |')
        lvl_rows = []
        mids_all = [m for m in MID_ORDER if (m, 0) in byk]
        for co in ('vb', 'va', 'c110'):
            for cl in ('clean', 'mid+lag'):
                ms = [m for m in mids_all if cohort(m) == co and ((cls.get(m) == 'clean') == (cl == 'clean'))]
                if not ms:
                    continue
                for upto, wkey in ((1500, '630~1530'), (3213, '1530~3210')):
                    pts = {a: [v for v in (path_level(m, a, upto) for m in ms) if v is not None] for a in ('hist', 'C2', 'C1', 'C0')}
                    if not pts['C1']:
                        continue
                    own = [(LB['cohorts'].get(f"{co}|{c}|{wkey}") or {}).get('band', {}).get('relTerr1') for c in (['clean'] if cl == 'clean' else ['mid', 'lag'])]
                    cb = (LB['cohorts'].get(f'{co}|clean|{wkey}') or {}).get('band', {}).get('relTerr1')
                    bandtxt = lambda b: f"{b[0]:.2f} / {b[1]:.2f} / {b[2]:.2f}（{b[3]}）" if b else '-'
                    pos = lambda vals: (f"{sum(1 for v in vals if v < cb[0])} / {sum(1 for v in vals if cb[0] <= v <= cb[2])} / {sum(1 for v in vals if v > cb[2])}" if cb else '-')
                    md = lambda a: quart(pts[a])[1] if pts[a] else None
                    lvl_rows.append({'cohort': co, 'cls': cl, 'at': upto, 'n': len(pts['C1']), 'histMed': md('hist'), 'c2Med': md('C2'), 'c1Med': md('C1'), 'c0Med': md('C0'),
                                     'cleanP25': cb[0] if cb else None, 'cleanMed': cb[1] if cb else None, 'cleanP75': cb[2] if cb else None, 'cleanN': cb[3] if cb else None,
                                     'c1Above': sum(1 for v in pts['C1'] if cb and v > cb[2]), 'c1Inside': sum(1 for v in pts['C1'] if cb and cb[0] <= v <= cb[2]), 'c1Below': sum(1 for v in pts['C1'] if cb and v < cb[0]),
                                     'histAbove': sum(1 for v in pts['hist'] if cb and v > cb[2]), 'histInside': sum(1 for v in pts['hist'] if cb and cb[0] <= v <= cb[2]), 'histBelow': sum(1 for v in pts['hist'] if cb and v < cb[0]),
                                     'mids': ' '.join(ms)})
                    P(f"| {co} × {'通道干净' if cl == 'clean' else '有落后（mid、lag 两档）'}（{'、'.join(ms)}） | t={upto} | {len(pts['C1'])} | {f2(md('hist'), 3)} | {f2(md('C2'), 3)} | {f2(md('C1'), 3)} | {f2(md('C0'), 3)} | "
                      f"{'；'.join(bandtxt(b) for b in own if b) or '-'} | {bandtxt(cb)} | {pos(pts['C1'])} | {pos(pts['hist'])} |")
        P('')
        if lvl_rows:
            with open(os.path.join(DST, 'ckpt_levels.csv'), 'w', newline='') as fo:
                w = csv.DictWriter(fo, fieldnames=list(lvl_rows[0].keys()))
                w.writeheader()
                for r in lvl_rows:
                    w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
            P('R06 的窗口末是 1530 / 3210 拍，这里是 1500 / 3213 拍，差 30 拍和 3 拍，没有换算。卡顿档沿用 R06 的分法：630 起第一个窗口里我方指令的同拍批占比 < 0.15 为通道干净、≥ 0.5 为 lag、之间为 mid（R06 没分过的局按同一条规则补）。这个分法只看通道成不成批，不看页面有没有停摆或离场；C1 臂是两样都没有。')
            P('')
            vb = {(r['cls'], r['at']): r for r in lvl_rows if r['cohort'] == 'vb'}
            segs = []
            for at in (1500, 3213):
                r = vb.get(('mid+lag', at))
                if r and r['cleanMed']:
                    segs.append(f"t={at}：有落后的 {r['n']} 局 Vb，C1 路径中位 {r['c1Med']:.2f}，真实通道干净局是 {r['cleanP25']:.2f}–{r['cleanP75']:.2f}（中位 {r['cleanMed']:.2f}），"
                                f"{r['c1Above']} 局高于 P75、{r['c1Inside']} 局在区间内、{r['c1Below']} 局低于 P25；C1 路径中位 ÷ 干净档中位 = ×{r['c1Med'] / r['cleanMed']:.2f}，历史中位 ÷ 干净档中位 = ×{r['histMed'] / r['cleanMed']:.2f}")
            if segs:
                P('读法：如果「通道健康时这些局会怎样」的反事实是准的，C1 路径的水平应当和真实通道干净局的水平差不多。' + '。'.join(segs) + '。')
                P('')
            lag = {at: (LB['cohorts'].get(f'vb|lag|{wk}') or {}).get('band', {}).get('relTerr1') for at, wk in ((1500, '630~1530'), (3213, '1530~3210'))}
            cln = {at: (LB['cohorts'].get(f'vb|clean|{wk}') or {}).get('band', {}).get('relTerr1') for at, wk in ((1500, '630~1530'), (3213, '1530~3210'))}
            # 同一批局：模拟器给的（历史 ÷ C1 路径，逐局比值的几何均值）对「历史 ÷ 真实干净局中位」
            ms7 = [m for m in mids_all if cohort(m) == 'vb' and cls.get(m) != 'clean']
            cmp_ = []
            for at in (1500, 3213):
                rr = [(path_level(m, 'hist', at), path_level(m, 'C1', at), path_level(m, 'C2', at)) for m in ms7]
                rr = [x for x in rr if all(v and v > 0 for v in x)]
                if rr and cln.get(at):
                    g = lambda f: math.exp(mean([math.log(f(x)) for x in rr]))
                    cmp_.append(f"t={at}：历史 ÷ C1 路径 ×{g(lambda x: x[0] / x[1]):.2f}（其中 C2 路径 ÷ C1 路径 ×{g(lambda x: x[2] / x[1]):.2f}），历史 ÷ 真实干净局中位 ×{g(lambda x: x[0] / cln[at][1]):.2f}，"
                                f"C1 路径 ÷ 真实干净局中位 ×{g(lambda x: x[1] / cln[at][1]):.2f}")
            if cmp_:
                P(f"同一批局（有落后的 {len(ms7)} 局 Vb）逐局比值的几何均值：" + '；'.join(cmp_) + '。')
                P('')
            if adj_path:
                seg = []
                for at in (1500, 3213):
                    rr = [(path_level(m, 'hist', at), adj_path(m, at), adj_path(m, at, -1), adj_path(m, at, 1)) for m in ms7]
                    rr = [x for x in rr if all(v and v > 0 for v in x)]
                    if rr and cln.get(at):
                        g = lambda f: math.exp(mean([math.log(f(x)) for x in rr]))
                        lo, hi = sorted((g(lambda x: x[2] / cln[at][1]), g(lambda x: x[3] / cln[at][1])))
                        seg.append(f"t={at}：修正后的 C1 路径 ÷ 真实干净局中位 ×{g(lambda x: x[1] / cln[at][1]):.2f}（斜率 ±1 个标准误：×{lo:.2f} ~ ×{hi:.2f}），历史 ÷ 修正后的 C1 路径 ×{g(lambda x: x[0] / x[1]):.2f}")
                if seg:
                    P('C1 路径按表 K 的跨局斜率修正以后（同样这几局，逐局比值的几何均值）：' + '；'.join(seg) + '。')
                    P('')
            # 不靠连乘：一口气放开跑的 C1 / C2 水平对真实干净局
            seg = []
            for at, tagre in ((1500, r'g0[a-z]'), (3213, r'fr[a-z]')):
                FRX = load(tagre)
                rr = []
                for m in ms7:
                    e = FRX.get((m, 0))
                    if not e or e['meta']['t1'] != at or e['meta'].get('truncated'):
                        continue
                    c1, c2 = seeds(e, 'C1'), seeds(e, 'C2')
                    if c1 and c2:
                        rr.append((e['history']['relTerr1'], mean([x['relTerr1'] for x in c1]), mean([x['relTerr1'] for x in c2])))
                rr = [x for x in rr if all(v and v > 0 for v in x)]
                if rr and cln.get(at):
                    g = lambda f: math.exp(mean([math.log(f(x)) for x in rr]))
                    above = sum(1 for x in rr if x[1] > cln[at][2])
                    seg.append(f"t={at}（{len(rr)} 局）：C1 放开跑的水平中位 {quart([x[1] for x in rr])[1]:.2f}，÷ 真实干净局中位 ×{g(lambda x: x[1] / cln[at][1]):.2f}（{above} 局高于 P75）；"
                               f"历史 ÷ C1 放开跑 ×{g(lambda x: x[0] / x[1]):.2f}；C2 放开跑 ÷ C1 放开跑 ×{g(lambda x: x[2] / x[1]):.2f}")
            if seg:
                P('不连乘、从开局一口气放开跑的水平（同样这几局，逐局比值的几何均值）：' + '。'.join(seg) + '。')
                P('')
            # 这几局自己在实盘同档里的位置：历史与 C2 放开跑各在哪
            seg = []
            midb = {at: (LB['cohorts'].get(f'vb|mid|{wk}') or {}).get('band', {}).get('relTerr1') for at, wk in ((1500, '630~1530'), (3213, '1530~3210'))}
            for at, tagre in ((1500, r'g0[a-z]'), (3213, r'fr[a-z]')):
                FRX = load(tagre)
                for lab, sel, bd in (('lag 档', [m for m in ms7 if cls.get(m) == 'lag'], lag.get(at)), ('mid 档', [m for m in ms7 if cls.get(m) == 'mid'], midb.get(at))):
                    rr = []
                    for m in sel:
                        e = FRX.get((m, 0))
                        if not e or e['meta']['t1'] != at or e['meta'].get('truncated'):
                            continue
                        c2 = seeds(e, 'C2')
                        if c2:
                            rr.append((e['history']['relTerr1'], mean([x['relTerr1'] for x in c2])))
                    if rr and bd:
                        seg.append(f"t={at} {lab}（本报告 {len(rr)} 局：{'、'.join(sel)}）：历史中位 {quart([x[0] for x in rr])[1]:.2f}，C2 放开跑中位 {quart([x[1] for x in rr])[1]:.2f}；"
                                   f"实盘同档 P25 / 中位 / P75 = {bd[0]:.2f} / {bd[1]:.2f} / {bd[2]:.2f}（{bd[3]} 局）；历史低于同档 P25 的 {sum(1 for x in rr if x[0] < bd[0])} 局，C2 放开跑低于同档 P25 的 {sum(1 for x in rr if x[1] < bd[0])} 局")
            if seg:
                P('这几局在实盘同档里的位置（Vb；看的是选局：这几局的历史是不是比同档的典型局更差）：' + '。'.join(seg) + '。')
                P('')
            if all(lag.values()) and all(cln.values()):
                P('实盘横向对比（R06 的区间，Vb）：lag 档中位 ÷ clean 档中位 = ' + '、'.join(f"×{lag[at][1] / cln[at][1]:.2f}（t≈{at}，{lag[at][3]} 局对 {cln[at][3]} 局）" for at in (1500, 3213)) + '。')
                P('')
            jf = os.path.join(R01, 'reports', 'm6-data', 'joined.csv')
            if os.path.exists(jf):
                pop = {'clean': [], 'mid': [], 'deep': []}
                for r in csv.DictReader(open(jf)):
                    try:
                        x = float(r['nd600_1500'])
                        num = int(r['mid'][1:])
                    except ValueError:
                        continue
                    if r['cohort'] != 'squad10' or r['multi'] != '0' or not r['mid'].startswith('A') or not 18 <= num <= 95:
                        continue
                    pop['clean' if x >= 0.9 else 'deep' if x < 0.7 else 'mid'].append(r)
                def pmed(c, k):
                    v = []
                    for r in pop[c]:
                        try:
                            v.append(float(r[k]))
                        except ValueError:
                            pass
                    return quart(v)[1] if v else None
                if pop['clean'] and pop['deep']:
                    seg = []
                    for c, lab in (('deep', '< 0.7 档'), ('mid', '0.7–0.9 档')):
                        if pop[c]:
                            seg.append(f"{lab}（{len(pop[c])} 局）中位 ÷ ≥ 0.9 档（{len(pop['clean'])} 局）中位 = " + '、'.join(f"×{pmed(c, k) / pmed('clean', k):.2f}（{t} 拍）" for k, t in (('rel630', 630), ('rel1530', 1530), ('rel3060', 3060))))
                    P('另一套口径的实盘横向对比（M6 的全量表 `reports/m6-data/joined.csv`，Vb 的 10 人编队局；结果量是编队领土占全图的份额 ÷ 编队的人头份额，和本表的人均相对领土不是同一个量，只比倍数；按 600–1500 拍「落地 ÷ 放行」分档）：' + '；'.join(seg) + '。')
            P('')

    extra = []

    CVF = {}
    def chain_vs_free(RUNS, cps, label, per_match=False):
        """同一条臂：把 cps 里首尾相接的窗口连乘（起点 × 各窗口的 臂 ÷ 窗口起点），对一口气从 cps[0] 跑到 cps[-1]。按「通道干净 / 有落后」分开汇总。"""
        byk2 = {(r['mid'], r['t0']): r for r in D}
        ta, tb = cps[0], cps[-1]     # tb = None：一直接到这条放开跑自己停下的那一拍（各局录像长短不一）
        rows, skipped = [], []
        for k in sorted(RUNS, key=lambda k: MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99):
            e = RUNS[k]
            c1, c2 = seeds(e, 'C1'), seeds(e, 'C2')
            if not (c1 and c2) or k[1] != ta or e['meta'].get('truncated') or (tb is not None and e['meta']['t1'] != tb):
                continue
            wins, t = [], ta
            while t != e['meta']['t1']:
                w = byk2.get((k[0], t))
                if not w or w.get('truncated') or w['t1'] <= t:
                    wins = None
                    break
                wins.append(w)
                t = w['t1']
            y = 'relTerr1'
            free = {'C1': mean([m[y] for m in c1]), 'C2': mean([m[y] for m in c2])}
            hist = e['history'][y]
            if not wins:
                skipped.append((k[0], e['meta']['t1'], hist, free, e['history'].get('alive1'), mean([m['alive1'] for m in c1]), mean([m['alive1'] for m in c2])))
                continue
            ch = {}
            for arm in free:
                v = wins[0][f'{y}_start']
                for w in wins:
                    v *= w[f'{y}_{arm}'] / w[f'{y}_start']
                ch[arm] = v
            if min(list(free.values()) + list(ch.values()) + [hist]) < CHAIN_FLOOR:
                skipped.append((k[0], e['meta']['t1'], hist, free, e['history'].get('alive1'), mean([m['alive1'] for m in c1]), mean([m['alive1'] for m in c2])))
                continue
            rows.append({'mid': k[0], 'lag': GROUP.get(k[0]) != '通道干净', 'hist': hist, 'free': free, 'ch': ch, 'sd1': sd([m[y] for m in c1]), 'sd2': sd([m[y] for m in c2]), 'n': min(len(c1), len(c2)), 't1': e['meta']['t1'],
                         'alive': (e['history'].get('alive1'), mean([m['alive1'] for m in c2]))})
            extra.append({'table': f'chain-vs-free {label}', 'mid': k[0], 't0': ta, 't1': tb, 'variant': 'free', 'hist': hist, 'C1': free['C1'], 'C2': free['C2'], 'n': min(len(c1), len(c2))})
            extra.append({'table': f'chain-vs-free {label}', 'mid': k[0], 't0': ta, 't1': tb, 'variant': 'chain', 'hist': hist, 'C1': ch['C1'], 'C2': ch['C2'], 'n': min(len(c1), len(c2))})
        if not rows:
            return []
        if per_match:
            P(f"| 局 | 组 | 历史（t={tb if tb is not None else '放开跑的终点'}） | C1：串接 / 放开跑（±sd） | C2：串接 / 放开跑（±sd） | 历史 ÷ C1：串接 / 放开跑 | ln(C2÷C1)：串接 / 放开跑 | 残差 历史−C2（放开跑） |")
            P('| :-- | :-- | --: | :-- | :-- | :-- | :-- | --: |')
            for r in rows:
                P(f"| {r['mid']} | {GROUP.get(r['mid'], '')} | {fmt(r['hist'])}{'' if tb is not None else '（t=' + str(r['t1']) + '）'} | {fmt(r['ch']['C1'])} / {fmt(r['free']['C1'])} ±{fmt(r['sd1'])} | {fmt(r['ch']['C2'])} / {fmt(r['free']['C2'])} ±{fmt(r['sd2'])} | "
                  f"×{r['hist'] / r['ch']['C1']:.2f} / ×{r['hist'] / r['free']['C1']:.2f} | {fmt(math.log(r['ch']['C2'] / r['ch']['C1']), 3, True)} / {fmt(math.log(r['free']['C2'] / r['free']['C1']), 3, True)} | {fmt(r['hist'] - r['free']['C2'], 3, True)} |")
            P('')
        P(f'按通道状况分开看（{label}；几何均值）：')
        P('')
        P('| 组 | 局数 | C1：串接 ÷ 放开跑 | C2：串接 ÷ 放开跑 | 历史 ÷ C1：串接 | 历史 ÷ C1：放开跑 | C2 ÷ C1：串接 | C2 ÷ C1：放开跑 | 历史 ÷ C2：串接 | 历史 ÷ C2：放开跑 |')
        P('| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
        for lab, sel in (('通道干净', [r for r in rows if not r['lag']]), ('有落后（浅落后、深落后、c110）', [r for r in rows if r['lag']]), ('全部', rows)):
            if not sel:
                continue
            g = lambda f: math.exp(mean([math.log(f(r)) for r in sel]))
            P(f"| {lab} | {len(sel)} | ×{g(lambda r: r['ch']['C1'] / r['free']['C1']):.3f} | ×{g(lambda r: r['ch']['C2'] / r['free']['C2']):.3f} | ×{g(lambda r: r['hist'] / r['ch']['C1']):.2f} | ×{g(lambda r: r['hist'] / r['free']['C1']):.2f} | "
              f"×{g(lambda r: r['ch']['C2'] / r['ch']['C1']):.2f} | ×{g(lambda r: r['free']['C2'] / r['free']['C1']):.2f} | ×{g(lambda r: r['hist'] / r['ch']['C2']):.2f} | ×{g(lambda r: r['hist'] / r['free']['C2']):.2f} |")
        P('')
        if skipped:
            P(f'没进上面两张表的局（{label}；历史或某条臂的人均相对领土低于 {CHAIN_FLOOR}，或历史上我方中途归零、后面的窗口没有跑，比值没有意义）：'
              + '；'.join(f"{m}（到 t={t1}：历史 {fmt(h)}、活席 {al}；C1 放开跑 {fmt(fr['C1'])}、活席 {f2(a1, 1)}；C2 放开跑 {fmt(fr['C2'])}、活席 {f2(a2, 1)}）" for m, t1, h, fr, al, a1, a2 in skipped) + '。')
            P('')
        return rows

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
        # 串接近似的核对：表 C / 表 H 把各窗口的比值连乘当作「这条臂一路走下来」的终点。0→1500 这一段有真正一口气跑下来的值可比。
        byk = {(r['mid'], r['t0']): r for r in D}
        P('串接近似的核对（表 C、表 H 用的就是这个近似）：0→630 与 630→1500 两个窗口的比值连乘 `臂(0→630) × 臂(630→1500) ÷ 历史(630)`，对一口气跑到 1500 的同一条臂。')
        P('')
        P('| 局 | 组 | C0：串接 / 放开跑 | C1：串接 / 放开跑 | C2w：串接 / 放开跑 | C2：串接 / 放开跑 | ln(C2w÷C1)：串接 / 放开跑 | ln(C2÷C2w)：串接 / 放开跑 | ln(C2÷C1)：串接 / 放开跑 |')
        P('| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |')
        cc = {a: [] for a in ('C0', 'C1', 'C2w', 'C2', 'wave', 'page', 'both')}
        for k in sorted(G, key=lambda k: MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99):
            e = G[k]
            a, b = byk.get((k[0], 0)), byk.get((k[0], 630))
            c0, c1, c2 = seeds(e, 'C0'), seeds(e, 'C1'), seeds(e, 'C2')
            c2w = seeds(e, 'C2w') or c2
            if not (a and b and c0 and c1 and c2) or e['meta']['t1'] != 1500 or b['t1'] != 1500:
                continue
            y = 'relTerr1'
            free = {'C0': c0[0][y], 'C1': mean([m[y] for m in c1]), 'C2w': mean([m[y] for m in c2w]), 'C2': mean([m[y] for m in c2])}
            ch = {arm: a[f'{y}_{arm}'] * b[f'{y}_{arm}'] / b[f'{y}_start'] for arm in free}
            if min(list(free.values()) + list(ch.values())) < CHAIN_FLOOR:
                continue
            lw = (math.log(ch['C2w'] / ch['C1']), math.log(free['C2w'] / free['C1']))
            lp = (math.log(ch['C2'] / ch['C2w']), math.log(free['C2'] / free['C2w']))
            lb = (math.log(ch['C2'] / ch['C1']), math.log(free['C2'] / free['C1']))
            for arm in free:
                cc[arm].append((ch[arm], free[arm]))
            cc['wave'].append(lw); cc['page'].append(lp); cc['both'].append(lb)
            extra.append({'table': 'G-chain', 'mid': k[0], 't0': 0, 't1': 1500, 'variant': 'chain-vs-free', 'C0': ch['C0'], 'C1': ch['C1'], 'C2w': ch['C2w'], 'C2': ch['C2'], 'hist': e['history'][y], 'n': len(c2)})
            P(f"| {k[0]} | {GROUP.get(k[0], '')} | " + ' | '.join(f"{fmt(ch[arm])} / {fmt(free[arm])}" for arm in ('C0', 'C1', 'C2w', 'C2'))
              + f" | {fmt(lw[0], 3, True)} / {fmt(lw[1], 3, True)} | {fmt(lp[0], 3, True)} / {fmt(lp[1], 3, True)} | {fmt(lb[0], 3, True)} / {fmt(lb[1], 3, True)} |")
        if cc['C1']:
            n = len(cc['C1'])
            gm = lambda arm: math.exp(mean([math.log(x[0] / x[1]) for x in cc[arm]]))
            mab = lambda arm: mean([abs(math.log(x[0] / x[1])) for x in cc[arm]])
            P('')
            P(f"{n} 局：串接 ÷ 放开跑 的几何均值 —— C0 ×{gm('C0'):.3f}、C1 ×{gm('C1'):.3f}、C2w ×{gm('C2w'):.3f}、C2 ×{gm('C2'):.3f}；|ln 比值| 的均值 —— "
              f"C0 {mab('C0'):.3f}、C1 {mab('C1'):.3f}、C2w {mab('C2w'):.3f}、C2 {mab('C2'):.3f}。")
            P(f"落后波 ln(C2w÷C1) 的均值：串接 {mean([x[0] for x in cc['wave']]):+.3f}，放开跑 {mean([x[1] for x in cc['wave']]):+.3f}；页面/掉线 ln(C2÷C2w)：串接 {mean([x[0] for x in cc['page']]):+.3f}，放开跑 {mean([x[1] for x in cc['page']]):+.3f}；"
              f"两段合计 ln(C2÷C1)：串接 {mean([x[0] for x in cc['both']]):+.3f}，放开跑 {mean([x[1] for x in cc['both']]):+.3f}。")
        P('')
        CVF['0→1500'] = chain_vs_free(G, [0, 630, 1500], '0→1500')

    # ---- 630→3213 一口气放开跑：连乘第二个接头的直接核对
    SP = load(r'sp[a-z]')
    if SP:
        P('### 表 G2　从 630 一口气放开跑到 t=3213（不在 1500 重新对齐）：连乘第二个接头的核对')
        P('')
        CVF['630→3213'] = chain_vs_free(SP, [630, 1500, 3213], '630→3213', per_match=True)

    # ---- 0→3213 一口气放开跑：累计效应不靠连乘的直接估计
    FR = load(r'fr[a-z]')
    if FR:
        P('### 表 G3　从开局一口气放开跑到 t=3213（630、1500 两个接头都不重新对齐）')
        P('')
        CVF['0→3213'] = chain_vs_free(FR, [0, 630, 1500, 3213], '0→3213', per_match=True)

    # ---- 0→5184（或录像结束）一口气放开跑
    FS = load(r'fs[a-z]')
    if FS:
        P('### 表 G4　从开局一口气放开跑到 t=5184 或录像结束（中间不重新对齐）')
        P('')
        CVF['0→5184（或录像结束）'] = chain_vs_free(FS, [0, None], '0→5184', per_match=True)
        # 同一批放开跑沿途的水平：每 30 拍有一个采样，取离断面最近的那个
        def rel_at(series, t):
            x = min(series, key=lambda q: abs(q['t'] - t))
            if abs(x['t'] - t) > 30 or not x['humTerr']:
                return None
            return x['terr'] / x['humTerr']
        CPS = [630, 1500, 2400, 3213, 4284, 5184]
        tr = {}
        for k, e in FS.items():
            c1, c2 = seeds(e, 'C1'), seeds(e, 'C2')
            if not (c1 and c2) or e['meta'].get('truncated') or 'series' not in e['history']:
                continue
            # 人均相对领土 = (我方领土 ÷ 席位) ÷ (全体真人领土 ÷ 人数)；同一局里席位数与人数相同，比值里约掉
            sq = e['meta'].get('squad')
            nseat = len(sq) if isinstance(sq, (list, tuple)) else sq
            scale = (e['meta']['humans'] / nseat) if (nseat and e['meta'].get('humans')) else None
            for t in CPS:
                if t == e['meta']['t1'] and scale:
                    # 终点不在 30 拍的采样格上，直接用终点值
                    h = e['history']['relTerr1'] / scale
                    a1 = [m['relTerr1'] / scale for m in c1]
                    a2 = [m['relTerr1'] / scale for m in c2]
                else:
                    h = rel_at(e['history']['series'], t)
                    a1 = [rel_at(m['series'], t) for m in c1 if m.get('series')]
                    a2 = [rel_at(m['series'], t) for m in c2 if m.get('series')]
                if h is None or not a1 or not a2 or None in a1 or None in a2:
                    continue
                tr.setdefault(t, []).append({'mid': k[0], 'lag': GROUP.get(k[0]) != '通道干净', 'h': h, 'c1': mean(a1), 'c2': mean(a2), 'hrel': h * scale if scale else None, 'scale': scale})
        if tr:
            P('同一批放开跑沿途各断面的水平（每 30 拍一个采样，取离断面最近的，终点用终点值；历史的人均相对领土低于 %.2f 的局在那个断面不算）：' % CHAIN_FLOOR)
            P('')
            P('| 断面 | 组 | 局数 | 水平（人均相对领土的几何均值）：历史 / C2 / C1 | 历史 ÷ C2 放开跑 | C2 ÷ C1（放开跑） | 历史 ÷ C1 放开跑 | 历史低于 C2 的局数 | 通道模型解释的占比 ln(C2÷C1) ÷ ln(历史÷C1) |')
            P('| :-- | :-- | --: | :-- | --: | --: | --: | :-- | --: |')
            g5 = []
            for t in CPS:
                rows = [r for r in tr.get(t, []) if r['hrel'] is not None and r['hrel'] >= CHAIN_FLOOR and r['c1'] > 0 and r['c2'] > 0]
                for lab, sel in (('通道干净', [r for r in rows if not r['lag']]), ('有落后', [r for r in rows if r['lag']]), ('全部', rows)):
                    if not sel:
                        continue
                    g = lambda f: math.exp(mean([math.log(f(r)) for r in sel]))
                    def gci(f):
                        ci = boot_ci([math.log(f(r)) for r in sel])
                        return f"（×{math.exp(ci[0]):.2f} ~ ×{math.exp(ci[1]):.2f}）" if ci else ''
                    hc2, c21, hc1 = g(lambda r: r['h'] / r['c2']), g(lambda r: r['c2'] / r['c1']), g(lambda r: r['h'] / r['c1'])
                    share = f"{math.log(c21) / math.log(hc1):.0%}" if abs(math.log(hc1)) > 0.15 else '-'
                    lv = (g(lambda r: r['hrel']), g(lambda r: r['c2'] * r['scale']), g(lambda r: r['c1'] * r['scale']))
                    P(f"| t={t} | {lab} | {len(sel)} | {lv[0]:.2f} / {lv[1]:.2f} / {lv[2]:.2f} | ×{hc2:.2f}{gci(lambda r: r['h'] / r['c2'])} | ×{c21:.2f}{gci(lambda r: r['c2'] / r['c1'])} | ×{hc1:.2f}{gci(lambda r: r['h'] / r['c1'])} | {sum(1 for r in sel if r['h'] < r['c2'])}/{len(sel)} | {share} |")
                    g5.append({'t': t, 'group': lab, 'n': len(sel), 'histLevel': lv[0], 'c2Level': lv[1], 'c1Level': lv[2], 'histOverC2': hc2, 'c2OverC1': c21, 'histOverC1': hc1})
            P('')
            oth = []
            for k, e in FS.items():
                for m in seeds(e, 'C2') or []:
                    if m.get('others') and m.get('div'):
                        oth.append(((m['others']['rerouted'] + m['others']['dropped']) / max(1, m['others']['atk']), m['div']['othersL1'] / max(1, m['div']['othersHist'])))
            if oth:
                P(f"放开跑到终点时，C2 臂里其余真人的陆攻有 {mean([x[0] for x in oth]) * 100:.0f}% 改打或作废（各局各种子的均值），他们逐人领土与历史的 L1 偏差是历史总量的 {mean([x[1] for x in oth]) * 100:.0f}%。"
                  '（每个窗口各自起跑时这两个数是 7% 上下与 1%–6%，见表 P。）')
                P('')
            with open(os.path.join(DST, 'ckpt_freerun_path.csv'), 'w', newline='') as fo:
                w = csv.DictWriter(fo, fieldnames=list(g5[0].keys()))
                w.writeheader()
                for r in g5:
                    w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})

    # ---- 累计通道效应的几种估计放在一张表里
    if any(CVF.values()):
        P('### 表 Z　累计的通道效应：窗口连乘 对 一口气放开跑（人均相对领土，几何均值；「历史 ÷ C1」越小 = 通道效应越大）')
        P('')
        P('| 区间 | 组 | 局数 | 历史 ÷ C1：连乘 | 历史 ÷ C1：放开跑 | C2 ÷ C1：连乘 | C2 ÷ C1：放开跑 | 历史 ÷ C2：连乘 | 历史 ÷ C2：放开跑 | C1 的水平：连乘 ÷ 放开跑 | 历史 ÷ C1（放开跑）< 1 的局数 | 通道模型解释的占比 ln(C2÷C1) ÷ ln(历史÷C1)：连乘 / 放开跑 |')
        P('| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | :-- | :-- |')
        z_rows = []
        for label, rows in CVF.items():
            for lab, sel in (('通道干净', [r for r in rows or [] if not r['lag']]), ('有落后', [r for r in rows or [] if r['lag']]), ('全部', rows or [])):
                if not sel:
                    continue
                g = lambda f: math.exp(mean([math.log(f(r)) for r in sel]))
                z = {'span': label, 'group': lab, 'n': len(sel), 'histOverC1chain': g(lambda r: r['hist'] / r['ch']['C1']), 'histOverC1free': g(lambda r: r['hist'] / r['free']['C1']),
                     'c2OverC1chain': g(lambda r: r['ch']['C2'] / r['ch']['C1']), 'c2OverC1free': g(lambda r: r['free']['C2'] / r['free']['C1']),
                     'histOverC2chain': g(lambda r: r['hist'] / r['ch']['C2']), 'histOverC2free': g(lambda r: r['hist'] / r['free']['C2']),
                     'c1ChainOverFree': g(lambda r: r['ch']['C1'] / r['free']['C1']), 'nBelow': sum(1 for r in sel if r['hist'] < r['free']['C1'])}
                def gci(f):
                    ci = boot_ci([math.log(f(r)) for r in sel])
                    return f"（×{math.exp(ci[0]):.2f} ~ ×{math.exp(ci[1]):.2f}）" if ci else ''
                ci1 = boot_ci([math.log(r['hist'] / r['free']['C1']) for r in sel])
                z['histOverC1free_lo'], z['histOverC1free_hi'] = (math.exp(ci1[0]), math.exp(ci1[1])) if ci1 else (None, None)
                z_rows.append(z)
                P(f"| {label} | {lab} | {z['n']} | ×{z['histOverC1chain']:.2f}{gci(lambda r: r['hist'] / r['ch']['C1'])} | ×{z['histOverC1free']:.2f}{gci(lambda r: r['hist'] / r['free']['C1'])} | "
                  f"×{z['c2OverC1chain']:.2f} | ×{z['c2OverC1free']:.2f}{gci(lambda r: r['free']['C2'] / r['free']['C1'])} | ×{z['histOverC2chain']:.2f} | ×{z['histOverC2free']:.2f}{gci(lambda r: r['hist'] / r['free']['C2'])} | "
                  f"×{z['c1ChainOverFree']:.2f}{gci(lambda r: r['ch']['C1'] / r['free']['C1'])} | {z['nBelow']}/{z['n']} | "
                  + (f"{math.log(z['c2OverC1chain']) / math.log(z['histOverC1chain']):.0%} / {math.log(z['c2OverC1free']) / math.log(z['histOverC1free']):.0%}"
                     if min(abs(math.log(z['histOverC1chain'])), abs(math.log(z['histOverC1free']))) > 0.15 else '-') + ' |')
                z['shareChain'] = math.log(z['c2OverC1chain']) / math.log(z['histOverC1chain']) if abs(math.log(z['histOverC1chain'])) > 0.15 else None
                z['shareFree'] = math.log(z['c2OverC1free']) / math.log(z['histOverC1free']) if abs(math.log(z['histOverC1free'])) > 0.15 else None
        P('')
        with open(os.path.join(DST, 'ckpt_cumulative.csv'), 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(z_rows[0].keys()))
            w.writeheader()
            for r in z_rows:
                w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
        P('连乘 = 把首尾相接的窗口（每个都从历史的断面起跑）的比值乘起来；放开跑 = 从区间起点一口气跑到终点，中间不回到历史。放开跑只有 C1、C2 各 2–3 个种子。括号里是按局重抽样的 90%% 区间（不到 4 局的不给）。'
          '两种算法进的是同一批局：有一条臂或历史的人均相对领土低于 %.2f 的局两边都不算。' % CHAIN_FLOOR)
        P('')
        # 结论用的紧凑版：只留从开局起算的三段
        P('从开局起算的三段，紧凑版（每格：连乘 / 放开跑）：')
        P('')
        P('| 从开局到 | 组 | 局数 | 历史 ÷ 健康通道（C1） | 其中通道模型复现的：C2 ÷ C1 | 没解释的残差：历史 ÷ C2 | 通道模型复现的占比（ln 口径） |')
        P('| :-- | :-- | --: | :-- | :-- | :-- | :-- |')
        for z in z_rows:
            if not z['span'].startswith('0→'):
                continue
            sh = (f"{z['shareChain']:.0%} / {z['shareFree']:.0%}" if z.get('shareChain') is not None and z.get('shareFree') is not None else '-')
            P(f"| {z['span'].replace('0→', '').replace('（或录像结束）', ' 拍或录像结束') + ('' if '录像' in z['span'] else ' 拍')} | {z['group']} | {z['n']} | ×{z['histOverC1chain']:.2f} / ×{z['histOverC1free']:.2f} | ×{z['c2OverC1chain']:.2f} / ×{z['c2OverC1free']:.2f} | "
              f"×{z['histOverC2chain']:.2f} / ×{z['histOverC2free']:.2f} | {sh} |")
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
        P('### 表 T　实录阶梯的三种口径：只收唯一定位的（主口径）/ 加上定位不唯一的、取最早放得下的决策（上界）/ 取最晚放得下的（下界）；后两种都再按日志次序的下界抬高')
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
            star = ''.join('（' + {'hi': '上界', 'lo': '下界'}[v] + '还没跑，先沿用主口径）' for v in ('hi', 'lo') if k in idx[v] and idx[v][k]['variantPending'])
            P(f"| {r['mid']} | {WN.get(r['t0'], r['t0'])}{star} | {fmt(r[y + '_hist'])} | {lag3} | {trip(k, y + '_C2w')} | {trip(k, y + '_C2')} | {trip(k, y + '_wave', 3, True)} | {trip(k, y + '_page', 3, True)} | {trip(k, y + '_resid', 3, True)} | {trip(k, y + '_C2sd')} |")
            for v in ('hi', 'lo'):
                rv = idx[v].get(k)
                if rv and rv['variantRerun']:
                    extra.append({'table': 'T', 'mid': r['mid'], 't0': r['t0'], 't1': r['t1'], 'variant': f'trace-{v}', 'hist': r[y + '_hist'], 'C0': None, 'C1': None, 'C1sd': None, 'C2w': rv[y + '_C2w'], 'C2': rv[y + '_C2'], 'C2sd': rv[y + '_C2sd'], 'n': rv['nC2'], 'truncated': int(bool(rv['truncated']))})
        P('')
        npend = {v: [f"{r['mid']} {WN.get(r['t0'], r['t0'])}" for r in DV[v] if r['variantPending']] for v in ('hi', 'lo')}
        P(f"重跑的（局, 窗口）：上界 {nband['hi']} 个、下界 {nband['lo']} 个。阶梯与主口径平均相差不到 2 拍的窗口没有重跑，沿用主口径的数。"
          + (f"选中要重跑、还没跑出来的：上界 {len(npend['hi'])} 个、下界 {len(npend['lo'])} 个（按阶梯差从大到小排的队，没跑的是差得小的；下面的汇总里它们先沿用主口径的数）"
             f"——上界：{'、'.join(npend['hi']) or '无'}；下界：{'、'.join(npend['lo']) or '无'}。" if (npend['hi'] or npend['lo']) else '选中的窗口都跑完了。'))
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
        tsum, tsum_n = None, 0
        for g in GROUP_ORDER + ['A 局（c116 家族）', '全部']:
            ms = [m for m in CH['located'] if all(m in CH[v] and CH[v][m]['n'] == CH['located'][m]['n'] for v in DV) and (g == '全部' or GROUP[m] == g or (g.startswith('A 局') and m.startswith('A')))]
            if not ms:
                continue
            c3 = lambda f: ' / '.join(fmt(mean([f(CH[v][m]) for m in ms]), 3, True) for v in ('located', 'hi', 'lo'))
            P(f"| {g} | {len(ms)} | {c3(lambda c: c['wave'])} | {c3(lambda c: c['page'])} | {c3(lambda c: c['resid'])} | {c3(lambda c: c['wave'] + c['page'])} |")
            if g == '全部':
                tsum = {v: {key: mean([f(CH[v][m]) for m in ms]) for key, f in (('wave', lambda c: c['wave']), ('page', lambda c: c['page']), ('resid', lambda c: c['resid']))} for v in ('located', 'hi', 'lo')}
                tsum_n = len(ms)
        P('')
        if tsum:
            ex = lambda x: f"×{math.exp(x):.2f}"
            P(f"{tsum_n} 局的对数链，主口径 / 上界 / 下界：落后波 + 页面 {' / '.join(fmt(tsum[v]['wave'] + tsum[v]['page'], 3, True) for v in ('located', 'hi', 'lo'))}"
              f"（{' / '.join(ex(tsum[v]['wave'] + tsum[v]['page']) for v in ('located', 'hi', 'lo'))}）；"
              f"其中落后波 {' / '.join(ex(tsum[v]['wave']) for v in ('located', 'hi', 'lo'))}、页面/掉线 {' / '.join(ex(tsum[v]['page']) for v in ('located', 'hi', 'lo'))}；"
              f"残差 {' / '.join(fmt(tsum[v]['resid'], 3, True) for v in ('located', 'hi', 'lo'))}（{' / '.join(ex(tsum[v]['resid']) for v in ('located', 'hi', 'lo'))}）。"
              f"已重跑 上界 {nband['hi']} 个、下界 {nband['lo']} 个窗口" + (f"，排着队还没跑的 上界 {len(npend['hi'])} 个、下界 {len(npend['lo'])} 个（阶梯差得小的）。" if (npend['hi'] or npend['lo']) else '，选中的都跑完了。'))
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
        # 整条对数链按倒过来的次序重算（没有 C1p 的窗口页面一段本来就是 0 上下，两种次序一样）
        Od = dict(O)
        rev, miss = {}, []
        for mid, use in chain_use.items():
            w = pg = 0.0
            for r in use:
                e = Od.get((mid, r['t0']))
                if e:
                    c1p = mean([m['relTerr1'] for m in seeds(e, 'C1p')])
                    if c1p > CHAIN_FLOOR:
                        pg += math.log(c1p / r['relTerr1_C1'])
                        w += math.log(r['relTerr1_C2'] / c1p)
                        continue
                if abs(math.log(r['relTerr1_C2'] / r['relTerr1_C2w'])) > 0.02:
                    miss.append(f"{mid} {WN.get(r['t0'], r['t0'])}")
                w += math.log(r['relTerr1_C2w'] / r['relTerr1_C1'])
                pg += math.log(r['relTerr1_C2'] / r['relTerr1_C2w'])
            rev[mid] = (w, pg)
        if rev:
            mids_ = list(rev)
            w0, p0 = mean([chain[m]['wave'] for m in mids_]), mean([chain[m]['page'] for m in mids_])
            w1_, p1_ = mean([rev[m][0] for m in mids_]), mean([rev[m][1] for m in mids_])
            r0 = mean([chain[m]['resid'] for m in mids_])
            tot0 = w0 + p0 + r0
            P(f"{len(mids_)} 局的对数链按两种次序算：先加落后波（正文的口径）落后波 ×{math.exp(w0):.2f}、页面/掉线 ×{math.exp(p0):.2f}；先加页面 落后波 ×{math.exp(w1_):.2f}、页面/掉线 ×{math.exp(p1_):.2f}。"
              f"两段合计都是 ×{math.exp(w0 + p0):.2f}。占「历史 ÷ C1 路径」ln 差的份额（落后波 / 页面 / 残差）：{w0 / tot0:.0%} / {p0 / tot0:.0%} / {r0 / tot0:.0%} → {w1_ / tot0:.0%} / {p1_ / tot0:.0%} / {r0 / tot0:.0%}。"
              + (f"页面一段不为零（|ln| > 0.02）但还没有 C1p 臂的窗口：{'、'.join(miss)}，这些窗口按原次序算。" if miss else '页面一段不为零的窗口都有 C1p 臂。'))
            P('')

    # ---- 历史版本互换（c116 家族内 Va / Vb / Vc；c110 与 c116 家族之间）
    V = load(r'(va|vb|vc|c110)[a-z]', historical=False, keyfn=lambda d, tag: (d['match'], d['t0'], d.get('stratKey')))
    VN = {'va': 'Va', 'vb': 'Vb', 'vc': 'Vc', 'c110': 'c110'}
    if V:
        named = lambda e, kind: {n: m for n, m in e['arms'].items() if n.split('@')[0] == kind and m['_t1'] == e['meta']['t1']}
        P('### 表 V　同一断面、同一通道下，把我方换成另一个历史版本（Va / Vb / Vc 之间互换；c110 与 c116 家族之间互换）')
        P('')
        P('每一格都是「换上去的版本 − 当年那一版」在**同名种子**上的差（主批里当年那一版只取换版本那一批也跑了的种子）。'
          '「逐位相同」= 两个版本在这个窗口里窗口末的领土、兵力、进录像条数完全一样。')
        P('')
        P('| 局 | 当年版本 | 换成 | 窗口 | C1：当年 → 换后（差） | C2：当年 → 换后（差） | 兵力比 换后÷当年 C1 / C2 | 活席差 C1 / C2 | 种子数 C1 / C2 | 逐位相同 | 同窗口通道效应：基础延迟 / 落后波+页面 |')
        P('| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |')
        vrows = []
        for k in sorted(V, key=lambda k: (MID_ORDER.index(k[0]) if k[0] in MID_ORDER else 99, k[1], k[2] or '')):
            k2 = (k[0], k[1])
            if k2 not in R:
                continue
            e, h = V[k], R[k2]
            hv = h['meta'].get('stratKey') or ''
            if k[2] == hv or e['meta']['t1'] != h['meta']['t1']:
                continue
            row = {'mid': k[0], 't0': k[1], 'hv': hv, 'ver': k[2]}
            same = True
            for ch in ('C1', 'C2'):
                A, B = named(e, ch), named(h, ch)
                common = sorted(set(A) & set(B))
                if not common:
                    continue
                d = [A[n]['relTerr1'] - B[n]['relTerr1'] for n in common]
                row[f'{ch}_n'] = len(common)
                row[f'{ch}_hist'] = mean([B[n]['relTerr1'] for n in common])
                row[f'{ch}_alt'] = mean([A[n]['relTerr1'] for n in common])
                row[f'{ch}_d'] = mean(d)
                row[f'{ch}_se'] = (sd(d) / math.sqrt(len(d))) if len(d) > 1 else None
                row[f'{ch}_ln'] = mean([math.log(A[n]['relTerr1'] / B[n]['relTerr1']) for n in common]) if all(A[n]['relTerr1'] > CHAIN_FLOOR and B[n]['relTerr1'] > CHAIN_FLOOR for n in common) else None
                row[f'{ch}_w'] = math.exp(mean([math.log(max(1, A[n]['wealth1']) / max(1, B[n]['wealth1'])) for n in common]))
                row[f'{ch}_alive'] = mean([A[n]['alive1'] - B[n]['alive1'] for n in common])
                same = same and all(A[n]['terr1'] == B[n]['terr1'] and A[n]['wealth1'] == B[n]['wealth1'] and A[n]['recorded'] == B[n]['recorded'] for n in common)
                extra.append({'table': 'V', 'mid': k[0], 't0': k[1], 't1': e['meta']['t1'], 'variant': f'{k[2]}-{hv}:{ch}', 'hist': h['history']['relTerr1'], 'C0': None,
                              'C1': row[f'{ch}_alt'] if ch == 'C1' else None, 'C1sd': None, 'C2w': None, 'C2': row[f'{ch}_alt'] if ch == 'C2' else None, 'C2sd': None, 'n': len(common), 'truncated': int(bool(e['meta'].get('truncated')))})
            if 'C1_n' not in row and 'C2_n' not in row:
                continue
            row['same'] = same
            dr = next((r for r in D if r['mid'] == k[0] and r['t0'] == k[1]), None)
            row['base'] = dr['relTerr1_base'] if dr else None
            row['chan'] = (dr['relTerr1_C2'] - dr['relTerr1_C1']) if dr else None
            vrows.append(row)
            c = lambda ch: (f"{fmt(row[f'{ch}_hist'])} → {fmt(row[f'{ch}_alt'])}（{fmt(row[f'{ch}_d'], 3, True)}）" if f'{ch}_n' in row else '-')
            g = lambda key, nd=2, sign=False: ' / '.join((fmt(row.get(f'{ch}_{key}'), nd, sign) if row.get(f'{ch}_{key}') is not None else '-') for ch in ('C1', 'C2'))
            P(f"| {k[0]} | {VN.get(hv, hv)} | {VN.get(k[2], k[2])} | {WN.get(k[1], k[1])} | {c('C1')} | {c('C2')} | {g('w')} | {g('alive', 1, True)} | {row.get('C1_n', 0)} / {row.get('C2_n', 0)} | {'是' if same else '否'} | "
              f"{fmt(row['base'], 3, True)} / {fmt(row['chan'], 3, True)} |")
        P('')
        # 汇总：统一成「Vb − Va」「Vc − Vb」「Vc − Va」的方向
        P('按窗口汇总（方向统一：正数 = 前一个版本的窗口末人均相对领土更高）：')
        P('')
        P('| 窗口 | 对比 | 通道 | 局数 | 差的均值（按局重抽样 90% 区间） | 差的中位 | 正 / 负 的局数 | \\|差\\| 均值 | ln 比值的均值（换回倍数） | 兵力比的几何均值 | 种子噪声（差的标准误，各局均值） | 同一批局、同窗口的通道效应均值：基础延迟 / 落后波+页面 | \\|版本差\\| ÷ \\|落后波+页面\\| |')
        P('| :-- | :-- | :-- | --: | :-- | --: | :-- | --: | --: | --: | --: | :-- | --: |')
        def norm(r):
            pair = {r['hv'], r['ver']}
            if 'c110' in pair:
                if r['mid'].startswith('B'):
                    return 'c110 − Vb（B 局：当年是 c110，换成 Vb）', (1 if r['ver'] == 'c110' else -1)
                return 'c110 − c116 家族（A 局：当年是 Va 或 Vb，换成 c110）', (1 if r['ver'] == 'c110' else -1)
            if pair == {'va', 'vb'}:
                return 'Vb − Va', (1 if r['ver'] == 'vb' else -1)
            if pair == {'vb', 'vc'}:
                return 'Vc − Vb', (1 if r['ver'] == 'vc' else -1)
            return 'Vc − Va', (1 if r['ver'] == 'vc' else -1)
        vs = {}
        for r in vrows:
            name, sgn = norm(r)
            for ch in ('C1', 'C2'):
                if f'{ch}_n' in r:
                    vs.setdefault((r['t0'], name, ch), []).append((sgn * r[f'{ch}_d'], (sgn * r[f'{ch}_ln']) if r[f'{ch}_ln'] is not None else None, r[f'{ch}_w'] ** sgn, r[f'{ch}_se'], r))
        for (t0, name, ch), v in sorted(vs.items()):
            ds = [x[0] for x in v]
            lns = [x[1] for x in v if x[1] is not None]
            ses = [x[3] for x in v if x[3] is not None]
            base = mean([x[4]['base'] for x in v if x[4]['base'] is not None]); chan = mean([x[4]['chan'] for x in v if x[4]['chan'] is not None])
            mabs = mean([abs(d) for d in ds]); cabs = mean([abs(x[4]['chan']) for x in v if x[4]['chan'] is not None])
            ci = boot_ci(ds)
            P(f"| {WN.get(t0, t0)} | {name} | {ch} | {len(ds)} | {fmt(mean(ds), 3, True)}{f'（{ci[0]:+.3f} ~ {ci[1]:+.3f}）' if ci else ''} | {fmt(quart(ds)[1], 3, True)} | {sum(1 for d in ds if d > 1e-9)} / {sum(1 for d in ds if d < -1e-9)} | {fmt(mabs)} | "
              f"{(fmt(mean(lns), 3, True) + '（×' + format(math.exp(mean(lns)), '.2f') + '）') if lns else '-'} | ×{math.exp(mean([math.log(x[2]) for x in v])):.2f} | {fmt(mean(ses)) if ses else '-'} | "
              f"{fmt(base, 3, True)} / {fmt(chan, 3, True)} | {(format(mabs / cabs, '.2f')) if cabs and cabs > 1e-9 else '-'} |")
        P('')
        # 版本差在两种通道下是不是一回事（交互）
        inter = [(r['mid'], r['t0'], norm(r)[0], norm(r)[1] * (r['C2_d'] - r['C1_d'])) for r in vrows if 'C1_n' in r and 'C2_n' in r]
        if inter:
            byc = {}
            for m_, t_, nm_, x in inter:
                byc.setdefault((t_, nm_), []).append(x)
            P('版本差在实录通道下与在健康通道下相差多少（C2 下的差 − C1 下的差）：' + '；'.join(f"{WN.get(t_, t_)} {nm_}：均值 {mean(v):+.3f}、|·| 均值 {mean([abs(x) for x in v]):.3f}（{len(v)} 局）" for (t_, nm_), v in sorted(byc.items())) + '。')
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
