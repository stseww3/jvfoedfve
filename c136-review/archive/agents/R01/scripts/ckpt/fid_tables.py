#!/usr/bin/env python3
"""fid_tables.py — 把三层保真度核对的结果（out/ 下的缓存）汇成入库的表。

  ① 物理底座：out/<局>/ckpt_base.json           （base_xcheck.mjs 写的）
  ② 通道开环：reports/ckpt-data/chan_openloop.json （chan_openloop.mjs 写的）
  ③ 决策层：  out/<局>/ckpt_shadow_fid.json       （shadow_fid.mjs 写的）

输出 reports/ckpt-data/fid_base.csv、fid_channel.csv、fid_decision.csv、fid_tables.md
用法：python3 scripts/ckpt/fid_tables.py
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R01 = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(R01, 'out')
DATA = os.path.join(R01, 'reports', 'ckpt-data')
MIDS = 'A075 A055 A023 A019 A054 A003 A031 A050 A009 A057 A059 A094 B039 B043'.split()
GROUP = {'A075': '通道干净', 'A055': '通道干净', 'A023': '通道干净', 'A019': '浅落后', 'A054': '浅落后', 'A003': '浅落后',
         'A031': '深落后', 'A050': '深落后', 'A009': '深落后', 'A057': '深落后', 'A059': '深落后', 'A094': '深落后',
         'B039': 'c110 深落后', 'B043': 'c110 深落后'}


def pct(a, b, nd=1):
    return '' if not b else f'{100 * a / b:.{nd}f}%'


def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(DATA, name), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols):
    out = ['| ' + ' | '.join(c for c, _ in cols) + ' |', '|' + '|'.join('---' for _ in cols) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(fn(r)) for _, fn in cols) + ' |')
    return '\n'.join(out)


def main():
    lag = {r['mid']: r for r in csv.DictReader(open(os.path.join(DATA, 'trace_summary.csv')))}
    base, chan, dec = [], [], []
    for mid in MIDS:
        p = os.path.join(OUT, mid, 'ckpt_base.json')
        if os.path.exists(p):
            b = json.load(open(p))
            vr, ve, vl = b['vsResim'], b.get('vsEngine') or {}, b['vsLog']
            base.append({
                'mid': mid, 'group': GROUP[mid], 'replay': b['replay'], 'map': b['map'], 'humans': b['humans'], 'squad': len(b['squad']),
                'endT': b['endT'],
                'engineSame': ve.get('same', ''), 'engineCells': ve.get('cells', ''), 'engineLastT': ve.get('lastT', ''),
                'logSame': vl['same'], 'logCells': vl['cells'], 'logLastT': vl['lastT'],
                'resimSame': vr['same'], 'resimCells': vr['cells'], 'resimFirstBadT': vr['firstBadT'],
                'deathDiffSeats': len(b['deathDiff']), 'doomedSeats': len(b['doomed']),
            })
        p = os.path.join(OUT, mid, 'ckpt_shadow_fid.json')
        if os.path.exists(p):
            s = json.load(open(p))
            row = {'mid': mid, 'group': GROUP[mid], 'strategy': s['strategy'], 'endT': s['endT'], 'points': s['points']}
            for arm in ('C1', 'C2'):
                a = s['arms'].get(arm)
                if not a:
                    continue
                row.update({
                    f'{arm}_n': a['n'], f'{arm}_eqCmds': a['eqCmds'], f'{arm}_eqBoats': a['eqBoats'], f'{arm}_eqNb': a['eqNb'], f'{arm}_eqNeut': a['eqNeut'],
                    f'{arm}_seats': a['seats'], f'{arm}_seatsNeverDiverge': a['seatsNeverDiverge'], f'{arm}_firstDivergeMin': a['firstDivergeMin'],
                    f'{arm}_absDiffP90': a['absDiffP90'], f'{arm}_endRel': a['endRel'], f'{arm}_stratErrors': a.get('stratErrors', 0),
                })
            r = s.get('r01Shadow') or {}
            row.update({'r01_n': r.get('n', ''), 'r01_eqCmds': r.get('eqCmds', ''), 'r01_endRel': r.get('endRel', '')})
            dec.append(row)
    co = json.load(open(os.path.join(DATA, 'chan_openloop.json')))
    for mid in MIDS:
        c = co.get(mid)
        if not c:
            continue
        ins, loo, un = c['inSample'], c['loo'], c['un']
        row = {
            'mid': mid, 'group': GROUP[mid], 'lagP50': lag.get(mid, {}).get('lagP50', ''), 'lagP75': lag.get(mid, {}).get('lagP75', ''), 'lagP90': lag.get(mid, {}).get('lagP90', ''),
            'decisions': c['dec'], 'paired': c['paired'], 'unpaired': c['unpaired'],
            'in_exec': ins['exec'], 'in_dropCap': ins['dropCap'], 'in_lost': ins['lost'], 'in_exact': ins['exact'], 'in_within1round': ins['within7'],
        }
        for k in ('auto', 'nearest', 'linear', 'none'):
            L = loo[k]
            row.update({f'loo_{k}_exact': L['exact'], f'loo_{k}_within1round': L['within7'], f'loo_{k}_within3rounds': L['within21'], f'loo_{k}_bias': L['bias']})
        row.update({'loo_nLag': loo['auto']['nLag'], 'loo_auto_lagWithin3rounds': loo['auto']['lagWithin21'], 'loo_none_lagWithin3rounds': loo['none']['lagWithin21']})
        row.update({
            'atkDecided': c['atkDec'], 'atkLanded': c['atkLanded'], 'atkModelExec': c['atkModelExec'],
            'modelCmds': c['model']['cmds'], 'actualCmds': c['actual']['cmds'], 'modelRounds': c['model']['rounds'], 'actualRounds': c['actual']['rounds'],
            'modelB3': c['model']['b3'], 'actualB3': c['actual']['b3'], 'modelB9': c['model']['b9'], 'actualB9': c['actual']['b9'],
            'modelShare3': c['model']['share3'], 'actualShare3': c['actual']['share3'],
            'un_exec': un['exec'], 'un_dropCap': un['dropCap'], 'un_lost': un['lost'],
        })
        chan.append(row)
    write_csv('fid_base.csv', base)
    write_csv('fid_channel.csv', chan)
    write_csv('fid_decision.csv', dec)

    md = ['# 三层保真度核对（自动生成，勿手改）', '']
    md += ['## ① 物理底座：R06 的引擎移植（TGame）整局重放，逐采样拍对三份独立参照', '',
           '格子 = 某采样拍上某个真人的（存活、领土、余额）。真引擎与 R01 重演每 90 拍取一次全部真人；日志快照是我方席位自己日志里的领土与余额。', '']
    md.append(md_table(base, [
        ('局', lambda r: r['mid']), ('录像', lambda r: r['replay']), ('真人', lambda r: r['humans']), ('我方席', lambda r: r['squad']), ('走到', lambda r: r['endT']),
        ('对真引擎', lambda r: f"{r['engineSame']}/{r['engineCells']}"), ('对日志快照', lambda r: f"{r['logSame']}/{r['logCells']}"),
        ('对 R01 重演', lambda r: f"{r['resimSame']}/{r['resimCells']}"), ('R01 重演第一处不同', lambda r: '' if r['resimFirstBadT'] < 0 else f"t={r['resimFirstBadT']}"),
        ('页面中途停摆席', lambda r: r['doomedSeats']),
    ]))
    tot = lambda k: sum(int(r[k] or 0) for r in base)
    md += ['', f"合计：对真引擎 {tot('engineSame')}/{tot('engineCells')}；对日志快照 {tot('logSame')}/{tot('logCells')}；对 R01 重演 {tot('resimSame')}/{tot('resimCells')}。", '']

    md += ['## ② 通道开环：把同一串决策喂给通道模型（不带引擎），看落地拍与批次结构', '',
           '「留一」= 把配对点分 10 折，每次拿掉一折再去预测这一折的落地拍；「不带阶梯」= 只用基础延迟（C1）去预测。「一轮」= 7 拍。', '']
    md.append(md_table(chan, [
        ('局', lambda r: r['mid']), ('组', lambda r: r['group']), ('落后 P50/P75/P90', lambda r: f"{r['lagP50']}/{r['lagP75']}/{r['lagP90']}"),
        ('配对', lambda r: r['paired']),
        ('样本内：同拍', lambda r: f"{r['in_exact']:.2f}"), ('样本内：差≤一轮', lambda r: f"{r['in_within1round']:.2f}"),
        ('样本内：被判限流丢', lambda r: r['in_dropCap']),
        ('留一 auto：差≤一轮 / ≤三轮', lambda r: f"{r['loo_auto_within1round']:.2f} / {r['loo_auto_within3rounds']:.2f}"),
        ('留一 nearest', lambda r: f"{r['loo_nearest_within1round']:.2f} / {r['loo_nearest_within3rounds']:.2f}"),
        ('留一 linear', lambda r: f"{r['loo_linear_within1round']:.2f} / {r['loo_linear_within3rounds']:.2f}"),
        ('不带阶梯（C1）', lambda r: f"{r['loo_none_within1round']:.2f} / {r['loo_none_within3rounds']:.2f}"),
    ]))
    md += ['', '批次结构（只算进攻与出船；模型 = 通道模型吐出来的，实录 = 录像里我方真正执行的）：', '']
    md.append(md_table(chan, [
        ('局', lambda r: r['mid']), ('影子认可的进攻', lambda r: r['atkDecided']),
        ('实录落地', lambda r: f"{r['atkLanded']}（{pct(r['atkLanded'], r['atkDecided'], 0)}）"),
        ('模型执行', lambda r: f"{r['atkModelExec']}（{pct(r['atkModelExec'], r['atkDecided'], 0)}）"),
        ('条数 模型/实录', lambda r: f"{r['modelCmds']}/{r['actualCmds']}"), ('有指令的轮 模型/实录', lambda r: f"{r['modelRounds']}/{r['actualRounds']}"),
        ('≥3 条的批 模型/实录', lambda r: f"{r['modelB3']}/{r['actualB3']}"), ('满 9 条的批 模型/实录', lambda r: f"{r['modelB9']}/{r['actualB9']}"),
        ('成批条数占比 模型/实录', lambda r: f"{r['modelShare3']:.2f}/{r['actualShare3']:.2f}"),
        ('没配上的：模型判 执行/限流丢/页面已死', lambda r: f"{r['un_exec']}/{r['un_dropCap']}/{r['un_lost']}"),
    ]))
    md += ['']

    md += ['## ③ 决策层：沙箱里的历史版本整局影子运行，逐点对真实日志里的累计指令数', '',
           '点 = 某席某次日志快照（每 90 拍一行 `[HL-TICK]`）上的累计指令数 `cmds`。「从未分叉的席」= 整局每个点都相等。「末点相对差」= 全队最后一个点上（沙箱 − 日志）÷ 日志。', '']
    md.append(md_table(dec, [
        ('局', lambda r: r['mid']), ('版本', lambda r: r['strategy'].replace('v27-team-', '')),
        ('C1 钟：相等点', lambda r: f"{r['C1_eqCmds']}/{r['C1_n']}（{pct(r['C1_eqCmds'], r['C1_n'], 0)}）"),
        ('C2 钟：相等点', lambda r: f"{r['C2_eqCmds']}/{r['C2_n']}（{pct(r['C2_eqCmds'], r['C2_n'], 0)}）" if 'C2_n' in r else ''),
        ('从未分叉的席（C1 钟）', lambda r: f"{r['C1_seatsNeverDiverge']}/{r['C1_seats']}"),
        ('最早分叉', lambda r: '' if r['C1_firstDivergeMin'] in (None, -1, '') else f"t={r['C1_firstDivergeMin']}"),
        ('差的 P90（条）', lambda r: r['C1_absDiffP90']), ('末点相对差', lambda r: f"{100 * r['C1_endRel']:+.1f}%"),
        ('邻居数/中立数相等点', lambda r: f"{r['C1_eqNb']}/{r['C1_n']}、{r['C1_eqNeut']}/{r['C1_n']}"),
        ('R01 自己的影子：相等点', lambda r: f"{r['r01_eqCmds']}/{r['r01_n']}"),
    ]))
    md += ['']
    open(os.path.join(DATA, 'fid_tables.md'), 'w').write('\n'.join(md) + '\n')
    print(f'底座 {len(base)} 局、通道 {len(chan)} 局、决策层 {len(dec)} 局 → reports/ckpt-data/fid_base.csv、fid_channel.csv、fid_decision.csv、fid_tables.md')


if __name__ == '__main__':
    main()
