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


def quart(a):
    a = sorted(x for x in a if x is not None)
    if not a:
        return None, None, None
    q = lambda p: a[min(len(a) - 1, max(0, int(round(p * (len(a) - 1)))))]
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

    # ---- 分解
    D = []
    for k in keys:
        e = R[k]
        h = e['history']
        c0 = seeds(e, 'C0')
        c1 = seeds(e, 'C1')
        c2 = seeds(e, 'C2')
        c2w = seeds(e, 'C2w') or c2
        if not (c0 and c1 and c2):
            continue
        row = {'mid': k[0], 'group': GROUP.get(k[0], ''), 't0': k[1], 't1': e['meta']['t1'], 'seats': len(e['meta']['squad']), 'alive0': h['alive0'], 'c2wSeparate': bool(seeds(e, 'C2w')),
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

    # 逐局把 5 个窗口串起来：对数分解（各窗口起点都是历史局面，所以 ln(历史终点/历史起点) 逐窗口相加就是整段的 ln 变化）
    P('### 表 C　逐局把首尾相接的窗口串起来：ln(人均相对领土) 的整段变化分到五段（只算两端都 > 0 的窗口）')
    P('')
    P('| 局 | 组 | 串起来的窗口 | 起点 → 终点（历史） | ln 变化合计 | 规则（C0） | 基础延迟 | 落后波 | 页面/掉线 | 残差 | C0 一路走下来的终点（等效） |')
    P('| :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: |')
    chain = {}
    for mid in MID_ORDER:
        rows = [r for r in D if r['mid'] == mid]
        rows.sort(key=lambda r: r['t0'])
        use = []
        for r in rows:
            vals = [r['relTerr1_start'], r['relTerr1_hist'], r['relTerr1_C0'], r['relTerr1_C1'], r['relTerr1_C2w'], r['relTerr1_C2']]
            if min(vals) <= 0:
                break
            if use and use[-1]['t1'] != r['t0']:
                break
            use.append(r)
        if not use:
            continue
        ln = math.log
        tot = sum(ln(r['relTerr1_hist'] / r['relTerr1_start']) for r in use)
        rules = sum(ln(r['relTerr1_C0'] / r['relTerr1_start']) for r in use)
        base = sum(ln(r['relTerr1_C1'] / r['relTerr1_C0']) for r in use)
        wave = sum(ln(r['relTerr1_C2w'] / r['relTerr1_C1']) for r in use)
        page = sum(ln(r['relTerr1_C2'] / r['relTerr1_C2w']) for r in use)
        resid = sum(ln(r['relTerr1_hist'] / r['relTerr1_C2']) for r in use)
        chain[mid] = dict(n=len(use), tot=tot, rules=rules, base=base, wave=wave, page=page, resid=resid, start=use[0]['relTerr1_start'], end=use[-1]['relTerr1_hist'], t0=use[0]['t0'], t1=use[-1]['t1'])
        P(f"| {mid} | {GROUP[mid]} | {use[0]['t0']}→{use[-1]['t1']}（{len(use)} 个） | {fmt(use[0]['relTerr1_start'])} → {fmt(use[-1]['relTerr1_hist'])} | {fmt(tot, 3, True)} | {fmt(rules, 3, True)} | {fmt(base, 3, True)} | {fmt(wave, 3, True)} | {fmt(page, 3, True)} | {fmt(resid, 3, True)} | {fmt(use[0]['relTerr1_start'] * math.exp(rules))} |")
    P('')
    P('| 组 | 局数 | ln 变化合计（均值） | 规则（C0） | 基础延迟 | 落后波 | 页面/掉线 | 残差 | 占合计的比例：规则 / 基础延迟 / 落后波 / 页面 / 残差 |')
    P('| :-- | --: | --: | --: | --: | --: | --: | --: | :-- |')
    for g in GROUP_ORDER + ['全部']:
        ms = [m for m in chain if g == '全部' or GROUP[m] == g]
        if not ms:
            continue
        n = len(ms)
        S = {k: sum(chain[m][k] for m in ms) for k in ('tot', 'rules', 'base', 'wave', 'page', 'resid')}
        sh = ' / '.join(f"{100 * S[k] / S['tot']:.0f}%" if abs(S['tot']) > 1e-9 else '-' for k in ('rules', 'base', 'wave', 'page', 'resid'))
        P(f"| {g} | {n} | {fmt(S['tot'] / n, 3, True)} | {fmt(S['rules'] / n, 3, True)} | {fmt(S['base'] / n, 3, True)} | {fmt(S['wave'] / n, 3, True)} | {fmt(S['page'] / n, 3, True)} | {fmt(S['resid'] / n, 3, True)} | {sh} |")
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
