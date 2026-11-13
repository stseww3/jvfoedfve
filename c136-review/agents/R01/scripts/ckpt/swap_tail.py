#!/usr/bin/env python3
"""swap_tail.py — 版本互换的尾巴（4284 断面的全部互换、Vc 在 3213 / 4284 断面）单独汇总。

为什么单独一个脚本：2026-11-12 20:53 工作区被清空，out/_ckpt/runs/ 下的原始结果丢了；aggregate.py 要全部 354 步的
原始结果才能重算。这里只重跑当时没有结果的 44 步（scripts/steps/ckpt-tail.txt），基线取自入库的表：
  当年那一版在同一断面、同名种子上的 C1 / C2   ← reports/ckpt-data/ckpt_arms.csv
  同一（局, 窗口）的基础延迟与落后波 + 页面       ← reports/ckpt-data/ckpt_decomp.csv
每局一行与按窗口汇总的算法照抄 aggregate.py 的「表 V」一段（同名种子上的差；方向统一；按局重抽样的 90% 区间）。

核对（写进表的说明里）：
  1. 入库的表 V 里已经有的行（ckpt_extra.csv 的 V 行）这次又跑了的，换后的值要逐位相同——恢复后的数据镜像与清空前是同一份；
  2. 清空那一刻捡回来的原始结果（out/_ckpt/rescued/*.pre-wipe.json）与这次重跑的逐臂相同。

补跑的原始结果这次入库：脚本先把 out/_ckpt/runs/ 里属于 ckpt-tail.txt 的结果（和捡回来的那一份）拷到 reports/ckpt-data/tail-runs/，
再只从那里读——缓存再丢一次，表 VT 也能照入库的文件重算。

写：reports/ckpt-data/ckpt_vtail.md（表 VT）、reports/ckpt-data/ckpt_vtail.csv、reports/ckpt-data/tail-runs/
用法（在 agents/R01 下）：python3 scripts/ckpt/swap_tail.py
"""
import csv
import glob
import json
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import aggregate as ag  # noqa: E402

DST = ag.DST
R01 = ag.R01
WN = {0: '0→630', 630: '630→1500', 1500: '1500→3213', 3213: '3213→4284', 4284: '4284→5184'}
VN = {'va': 'Va', 'vb': 'Vb', 'vc': 'Vc', 'c110': 'c110'}
SK = {'v27-team-c116-va': 'va', 'v27-team-c116-vb': 'vb', 'v27-team-c116': 'vc', 'v27-team-c110': 'c110'}
ARM_NUM = ('relTerr1', 'terr1', 'wealth1', 'alive1', 'recorded')
TAIL = os.path.join(DST, 'tail-runs')
fmt, mean, sd = ag.fmt, ag.mean, ag.sd


def baseline():
    """入库的 ckpt_arms.csv → {(局, t0): {'stratKey', 't1', 'hist', 'arms': {臂名: {…}}}}；臂名与原始结果里的相同（C1、C1@2…）。"""
    out = {}
    with open(os.path.join(DST, 'ckpt_arms.csv'), newline='') as f:
        for r in csv.DictReader(f):
            e = out.setdefault((r['mid'], int(r['t0'])), {'stratKey': SK[r['strategy']], 't1': None, 'hist': None, 'arms': {}})
            if r['arm'] == 'history':
                e['hist'], e['t1'] = float(r['relTerr1']), int(r['t1'])
                continue
            name = r['arm'] if r['seed'] in ('', '1') else f"{r['arm']}@{r['seed']}"
            m = {c: float(r[c]) for c in ARM_NUM}
            m['_t1'] = int(r['t1'])
            e['arms'][name] = m
    return out


def decomp():
    out = {}
    with open(os.path.join(DST, 'ckpt_decomp.csv'), newline='') as f:
        for r in csv.DictReader(f):
            num = lambda c: float(r[c]) if r.get(c) not in (None, '') else None
            c1, c2 = num('relTerr1_C1'), num('relTerr1_C2')
            out[(r['mid'], int(r['t0']))] = {'base': num('relTerr1_base'), 'chan': (c2 - c1) if c1 is not None and c2 is not None else None}
    return out


def committed_v():
    """入库的表 V（ckpt_extra.csv）→ {(局, t0, '换成-当年:通道'): (换后的值, 种子数)}"""
    out = {}
    with open(os.path.join(DST, 'ckpt_extra.csv'), newline='') as f:
        for r in csv.DictReader(f):
            if r['table'] != 'V':
                continue
            ch = r['variant'].rsplit(':', 1)[1]
            out[(r['mid'], int(r['t0']), r['variant'])] = (float(r[ch]), int(r['n']))
    return out


def expected_steps():
    """ckpt-tail.txt 里的（局, t0, 版本）与对应的结果文件名。"""
    out, files = [], []
    p = os.path.join(R01, 'scripts', 'steps', 'ckpt-tail.txt')
    for line in open(p, encoding='utf8'):
        m = re.search(r'--match (\w+) --t0 (\d+) .*--strat (\w+) .*--tag (\w+)', line)
        if m and not line.startswith('#'):
            out.append((m.group(1), int(m.group(2)), m.group(3)))
            files.append(f'{m.group(1)}-{m.group(2)}-{m.group(4)}.json')
    return out, files


def sync_tail_runs(files):
    """out/_ckpt/runs/ 与 out/_ckpt/rescued/ 里属于尾巴的原始结果 → reports/ckpt-data/tail-runs/（入库）。"""
    pairs = [(os.path.join(R01, 'out', '_ckpt', 'runs', f), os.path.join(TAIL, f)) for f in files]
    pairs += [(f, os.path.join(TAIL, 'rescued', os.path.basename(f))) for f in sorted(glob.glob(os.path.join(R01, 'out', '_ckpt', 'rescued', '*.pre-wipe.json')))]
    n = 0
    for src, dst in pairs:
        if os.path.exists(src) and (not os.path.exists(dst) or open(src, 'rb').read() != open(dst, 'rb').read()):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            n += 1
    return n


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


def main():
    R, D, CV = baseline(), decomp(), committed_v()
    want, files = expected_steps()
    copied = sync_tail_runs(files)
    ag.RUNS = TAIL
    V = ag.load(r'(va|vb|vc|c110)[a-z]', historical=False, keyfn=lambda d, tag: (d['match'], d['t0'], d.get('stratKey')))
    have = [k for k in want if k in V]
    L = []
    P = L.append
    P('### 表 VT　版本互换的尾巴：4284 断面的全部互换，Vc 在 3213 / 4284 断面（工作区被清空以后补跑的 44 步）')
    P('')
    P('算法与表 V 相同：每一格都是「换上去的版本 − 当年那一版」在**同名种子**上的差。换上去的版本是这次重跑的原始结果；'
      '当年那一版（基线）取自入库的 `ckpt_arms.csv`，同窗口的通道效应取自 `ckpt_decomp.csv`。这个断面每种通道 1 个种子。')
    P('')
    P('| 局 | 当年版本 | 换成 | 窗口 | C1：当年 → 换后（差） | C2：当年 → 换后（差） | 兵力比 换后÷当年 C1 / C2 | 活席差 C1 / C2 | 种子数 C1 / C2 | 逐位相同 | 同窗口通道效应：基础延迟 / 落后波+页面 |')
    P('| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |')
    vrows, skipped, csvrows = [], [], []
    xsame, xdiff = [], []
    named = lambda arms, kind, t1: {n: m for n, m in arms.items() if n.split('@')[0] == kind and m['_t1'] == t1}
    for k in sorted(have, key=lambda k: (k[1], ag.MID_ORDER.index(k[0]) if k[0] in ag.MID_ORDER else 99, k[2])):
        k2 = (k[0], k[1])
        e, h = V[k], R.get(k2)
        if h is None:
            skipped.append(f'{k[0]}-{k[1]}-{k[2]}（入库的表里没有这个（局, 断面））'); continue
        hv = h['stratKey']
        if k[2] == hv:
            skipped.append(f'{k[0]}-{k[1]}-{k[2]}（和当年是同一版）'); continue
        if e['meta']['t1'] != h['t1'] or e['meta'].get('truncated'):
            skipped.append(f"{k[0]}-{k[1]}-{k[2]}（停在 {e['meta']['t1']} 拍，基线到 {h['t1']} 拍）"); continue
        row = {'mid': k[0], 't0': k[1], 'hv': hv, 'ver': k[2]}
        same = True
        for ch in ('C1', 'C2'):
            A, B = named(e['arms'], ch, e['meta']['t1']), named(h['arms'], ch, h['t1'])
            common = sorted(set(A) & set(B))
            if not common:
                continue
            d = [A[n]['relTerr1'] - B[n]['relTerr1'] for n in common]
            row[f'{ch}_n'] = len(common)
            row[f'{ch}_hist'] = mean([B[n]['relTerr1'] for n in common])
            row[f'{ch}_alt'] = mean([A[n]['relTerr1'] for n in common])
            row[f'{ch}_d'] = mean(d)
            row[f'{ch}_se'] = (sd(d) / math.sqrt(len(d))) if len(d) > 1 else None
            alive = all(A[n]['relTerr1'] > ag.CHAIN_FLOOR and B[n]['relTerr1'] > ag.CHAIN_FLOOR for n in common)
            row[f'{ch}_ln'] = mean([math.log(A[n]['relTerr1'] / B[n]['relTerr1']) for n in common]) if alive else None
            # 生死窗口（有一边的人均相对领土接近 0）不算兵力比
            row[f'{ch}_w'] = math.exp(mean([math.log(max(1, A[n]['wealth1']) / max(1, B[n]['wealth1'])) for n in common])) if alive else None
            row[f'{ch}_alive'] = mean([A[n]['alive1'] - B[n]['alive1'] for n in common])
            same = same and all(A[n]['terr1'] == B[n]['terr1'] and A[n]['wealth1'] == B[n]['wealth1'] and A[n]['recorded'] == B[n]['recorded'] for n in common)
            # 核对 1：入库的表 V 里已有的行
            cv = CV.get((k[0], k[1], f'{k[2]}-{hv}:{ch}'))
            if cv is not None:
                (xsame if abs(cv[0] - round(row[f'{ch}_alt'], 5)) < 1e-9 and cv[1] == len(common) else xdiff).append(
                    f"{k[0]} {WN.get(k[1], k[1])} {VN[k[2]]} {ch}：入库 {cv[0]:.4f}、重跑 {row[f'{ch}_alt']:.4f}")
        if 'C1_n' not in row and 'C2_n' not in row:
            skipped.append(f'{k[0]}-{k[1]}-{k[2]}（没有同名种子）'); continue
        row['same'] = same
        dr = D.get(k2) or {}
        row['base'], row['chan'] = dr.get('base'), dr.get('chan')
        vrows.append(row)
        c = lambda ch: (f"{fmt(row[f'{ch}_hist'])} → {fmt(row[f'{ch}_alt'])}（{fmt(row[f'{ch}_d'], 3, True)}）" if f'{ch}_n' in row else '-')
        g = lambda key, nd=2, sign=False: ' / '.join((fmt(row.get(f'{ch}_{key}'), nd, sign) if row.get(f'{ch}_{key}') is not None else '-') for ch in ('C1', 'C2'))
        P(f"| {k[0]} | {VN.get(hv, hv)} | {VN.get(k[2], k[2])} | {WN.get(k[1], k[1])} | {c('C1')} | {c('C2')} | {g('w')} | {g('alive', 1, True)} | {row.get('C1_n', 0)} / {row.get('C2_n', 0)} | {'是' if same else '否'} | "
          f"{fmt(row['base'], 3, True)} / {fmt(row['chan'], 3, True)} |")
        name, sgn = norm(row)
        csvrows.append({'mid': k[0], 't0': k[1], 't1': h['t1'], 'historical': hv, 'swapped': k[2], 'contrast': name.split('（')[0], 'sign': sgn,
                        **{f'{ch}_{key}': (round(row[f'{ch}_{key}'], 5) if isinstance(row.get(f'{ch}_{key}'), float) else row.get(f'{ch}_{key}'))
                           for ch in ('C1', 'C2') for key in ('n', 'hist', 'alt', 'd', 'ln', 'w', 'alive')},
                        'identical': int(same), 'baseDelay': row['base'], 'wavePlusPage': row['chan']})
    P('')
    P('按窗口汇总（方向统一：正数 = 前一个版本的窗口末人均相对领土更高）：')
    P('')
    P('| 窗口 | 对比 | 通道 | 局数 | 差的均值（按局重抽样 90% 区间） | 差的中位 | 正 / 负 的局数 | 差的绝对值的均值 | ln 比值的均值（换回倍数） | 兵力比的几何均值 | 同一批局、同窗口的通道效应均值：基础延迟 / 落后波+页面 | 版本差的绝对值 ÷ 落后波+页面的绝对值 | 活席数变了的局数 | 活席数没变的局：差的均值 | 生死窗口（不进 ln 与兵力比） |')
    P('| :-- | :-- | :-- | --: | :-- | --: | :-- | --: | --: | --: | :-- | --: | --: | --: | :-- |')
    vs = {}
    for r in vrows:
        name, sgn = norm(r)
        for ch in ('C1', 'C2'):
            if f'{ch}_n' in r:
                vs.setdefault((r['t0'], name, ch), []).append((sgn * r[f'{ch}_d'], (sgn * r[f'{ch}_ln']) if r[f'{ch}_ln'] is not None else None, (r[f'{ch}_w'] ** sgn) if r[f'{ch}_w'] is not None else None, r))
    for (t0, name, ch), v in sorted(vs.items()):
        ds = [x[0] for x in v]
        lns = [x[1] for x in v if x[1] is not None]
        ws = [x[2] for x in v if x[2] is not None]
        bases = [x[3]['base'] for x in v if x[3]['base'] is not None]
        chans = [x[3]['chan'] for x in v if x[3]['chan'] is not None]
        mabs = mean([abs(d) for d in ds]); cabs = mean([abs(c) for c in chans]) if chans else None
        ci = ag.boot_ci(ds)
        dead = [x[3]['mid'] for x in v if x[1] is None]
        flip = [x for x in v if abs(x[3][f'{ch}_alive']) >= 1]
        stay = [x[0] for x in v if abs(x[3][f'{ch}_alive']) < 1]
        P(f"| {WN.get(t0, t0)} | {name} | {ch} | {len(ds)} | {fmt(mean(ds), 3, True)}{f'（{ci[0]:+.3f} ~ {ci[1]:+.3f}）' if ci else ''} | {fmt(ag.quart(ds)[1], 3, True)} | {sum(1 for d in ds if d > 1e-9)} / {sum(1 for d in ds if d < -1e-9)} | {fmt(mabs)} | "
          f"{(fmt(mean(lns), 3, True) + '（×' + format(math.exp(mean(lns)), '.2f') + '）') if lns else '-'} | {('×' + format(math.exp(mean([math.log(x) for x in ws])), '.2f')) if ws else '-'} | "
          f"{fmt(mean(bases), 3, True) if bases else '-'} / {fmt(mean(chans), 3, True) if chans else '-'} | {(format(mabs / cabs, '.2f')) if cabs and cabs > 1e-9 else '-'} | {len(flip)} | {fmt(mean(stay), 3, True) if stay else '-'} | {'、'.join(dead) if dead else '-'} |")
    P('')
    inter = [(r['t0'], norm(r)[0], norm(r)[1] * (r['C2_d'] - r['C1_d'])) for r in vrows if 'C1_n' in r and 'C2_n' in r]
    if inter:
        byc = {}
        for t_, nm_, x in inter:
            byc.setdefault((t_, nm_), []).append(x)
        P('版本差在实录通道下与在健康通道下相差多少（C2 下的差 − C1 下的差）：' + '；'.join(f"{WN.get(t_, t_)} {nm_}：均值 {mean(v):+.3f}、|·| 均值 {mean([abs(x) for x in v]):.3f}（{len(v)} 局）" for (t_, nm_), v in sorted(byc.items())) + '。')
        P('')
    # 核对 2：清空那一刻捡回来的原始结果
    resc = []
    for f in sorted(glob.glob(os.path.join(TAIL, 'rescued', '*.pre-wipe.json'))):
        new = os.path.join(ag.RUNS, os.path.basename(f).replace('.pre-wipe', ''))
        if not os.path.exists(new):
            continue
        a, b = json.load(open(f)), json.load(open(new))
        key = lambda d: {n: [m.get(c) for c in ARM_NUM] + [[(s['t'], s['terr'], s['bal']) for s in m.get('series', [])]] for n, m in d['arms'].items()}
        resc.append((os.path.basename(new), key(a) == key(b) and a['history']['relTerr1'] == b['history']['relTerr1'], len(a['arms'])))
    P(f"核对。（1）入库的表 V 里已经有、这次又重跑了的行：{len(xsame)} 行换后的值与入库的逐位相同" + (f"，{len(xdiff)} 行不同（{'；'.join(xdiff)}）" if xdiff else '，没有不同的') + '。'
      + ('（2）清空那一刻捡回来的原始结果与这次重跑的对比：' + '；'.join(f"{n} {'逐臂相同（窗口末的领土、兵力、活席、进录像条数，以及沿途每 30 拍的领土与余额）' if ok else '不同'}（{na} 条臂）" for n, ok, na in resc) + '。' if resc else ''))
    P('')
    miss = [k for k in want if k not in V]
    if miss or skipped:
        P(f"还没有结果的步骤 {len(miss)} 个" + (f"：{'、'.join(f'{m}-{t}-{s}' for m, t, s in miss)}" if miss else '') + '。' + (f"没有进表的：{'；'.join(skipped)}。" if skipped else ''))
        P('')
    open(os.path.join(DST, 'ckpt_vtail.md'), 'w', encoding='utf8').write('\n'.join(L) + '\n')
    if csvrows:
        with open(os.path.join(DST, 'ckpt_vtail.csv'), 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=list(csvrows[0].keys()))
            w.writeheader()
            w.writerows(csvrows)
    print(f'拷进 tail-runs/ {copied} 个；尾巴 {len(want)} 步：有结果 {len(have)}，进表 {len(vrows)}，没进表 {len(skipped)}；核对 1 相同 {len(xsame)} / 不同 {len(xdiff)}；核对 2 {resc}')
    for x in xdiff:
        print('  不同：', x)


if __name__ == '__main__':
    main()
