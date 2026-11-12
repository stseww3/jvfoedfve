#!/usr/bin/env python3
"""fid_tables.py — 把保真度核对的结果（out/ 下的缓存与 reports/ckpt-data 下的中间表）汇成入库的表。

  ① 物理底座：out/<局>/ckpt_base.json           （base_xcheck.mjs 写的）
  ② 通道开环：reports/ckpt-data/chan_openloop.json （chan_openloop.mjs 写的）
  ③ 决策层：  out/<局>/ckpt_shadow_fid.json       （shadow_fid.mjs 写的）
  ④ 阶梯完整性：reports/ckpt-data/chan_unpaired.csv、trace_summary.csv、floor_check.csv、stair_logorder.csv

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

    # ④ 实录阶梯的完整性：只收唯一定位配对的阶梯在哪里是空的
    def read(name):
        path = os.path.join(DATA, name)
        return list(csv.DictReader(open(path))) if os.path.exists(path) else []
    ghosts, lo_rows, fl_rows, tsum = read('chan_unpaired.csv'), read('stair_logorder.csv'), read('floor_check.csv'), read('trace_summary.csv')
    if ghosts or lo_rows or fl_rows:
        md += ['## ④ 实录阶梯的完整性：只收唯一定位配对的阶梯，在落后最深的几段是空的', '',
               '阶梯只在「有指令落地、而且这条落地指令在影子序列里只有一个位置放得下」的地方有点。两种情况会让它在该有落后的地方显得健康：',
               '落地指令定位不唯一（同一条指令每个决策拍都在重发，成批落地只活下来几条）；这一段根本没有指令落地（全被 9 条顶丢，或页面在憋着）。', '']
    if ghosts:
        md += ['**(a) 模型多执行的指令落在哪**（`chan_unpaired.mjs`）：没配上录像、通道模型却判为执行的进攻。「长空档」= 它前后两条真落地的指令相隔 > 210 拍。', '']
        md.append(md_table([g for g in ghosts if g['mid'] in MIDS], [
            ('局', lambda r: r['mid']), ('没配上的进攻', lambda r: r['atkUnpaired']), ('其中模型判执行', lambda r: r['ghosts']),
            ('落在长空档里', lambda r: r['inLongGap']), ('最后一条落地指令之后', lambda r: r['afterLastLanded']), ('零散', lambda r: r['isolated']),
            ('所在空档 P50 / P90（拍）', lambda r: f"{r['gapP50']} / {r['gapP90']}" if r['gapP50'] else ''),
            ('这些指令上模型给的落后 P50 / P90', lambda r: f"{r['modelLagP50']} / {r['modelLagP90']}" if r['modelLagP50'] else ''),
            ('集中在哪几席', lambda r: r['top3']),
        ]))
        md += ['']
    if tsum:
        md += ['**(b) 定位不唯一的落地指令**（`make_trace.py`）：按「最早放得下的决策」配是落后的上界，按「最晚放得下的」配是下界。', '']
        md.append(md_table([t for t in tsum if t['mid'] in MIDS], [
            ('局', lambda r: r['mid']), ('唯一定位', lambda r: r['pairs']), ('落后 P50 / P75 / P90', lambda r: f"{r['lagP50']} / {r['lagP75']} / {r['lagP90']}"),
            ('定位不唯一', lambda r: r['unlocated']),
            ('上界口径：补上的条数，落后 P50 / P90', lambda r: f"{r['hiAdded']}，{r['hiAddedLagP50']} / {r['hiAddedLagP90']}" if r.get('hiAdded') not in ('', '0', None) else r.get('hiAdded', '')),
            ('下界口径：补上的条数，落后 P50 / P90', lambda r: f"{r['loAdded']}，{r['loAddedLagP50']} / {r['loAddedLagP90']}" if r.get('loAdded') not in ('', '0', None) else r.get('loAdded', '')),
            ('全体落后 P75 / P90：上界', lambda r: f"{r['hiLagP75']} / {r['hiLagP90']}"), ('下界', lambda r: f"{r['loLagP75']} / {r['loLagP90']}"),
        ]))
        md += ['']
    if fl_rows:
        md += ['**(c) 日志次序给的地板**（`logorder_floor.py`）：`in_game.log` 每行开头的流水号是收集次序。页面记下本机拍 t 的那一刻，流水号更小的行里出现过的最大本机拍',
               '就是服务器拍的下界（本机拍不会超过服务器拍）。粒度 90 拍。拿唯一定位的配对核对：τ 发出的指令不该早于「τ 之前最近一个日志点的下界 + 5 拍」落地。', '']
        md.append(md_table([f for f in fl_rows if f['mid'] in MIDS], [
            ('局', lambda r: r['mid']), ('日志点', lambda r: r['logPoints']), ('有落后下界（≥45 拍）的点', lambda r: r['floorPoints']), ('涉及席位', lambda r: r['floorSeats']),
            ('下界 P50 / P90 / 最大（拍）', lambda r: f"{r['floorLagP50']} / {r['floorLagP90']} / {r['floorLagMax']}" if r['floorLagP50'] else ''),
            ('核对的配对', lambda r: r['pairsChecked']), ('违反', lambda r: r['violations']),
        ]))
        md += ['', f"合计：{sum(int(f['pairsChecked']) for f in fl_rows if f['mid'] in MIDS)} 条配对，违反 {sum(int(f['violations']) for f in fl_rows if f['mid'] in MIDS)} 条。", '']
    if lo_rows:
        md += ['**(d) 三种只靠配对的阶梯够不够得着这个下界**（`stair_logorder.mjs`；「够得着」= 阶梯在这个日志点给的落后 ≥ 下界 − 45 拍）。只列有落后下界 ≥ 90 拍的局。', '']
        by = {}
        for r in lo_rows:
            by.setdefault(r['mid'], {})[r['variant']] = r
        rows = [(m, by[m]) for m in MIDS if m in by and int(by[m]['located']['behind'] or 0) > 0]
        md.append(md_table(rows, [
            ('局', lambda r: r[0]), ('下界 ≥ 90 拍的日志点', lambda r: r[1]['located']['behind']), ('下界 P50 / P90', lambda r: f"{r[1]['located']['lbP50']} / {r[1]['located']['lbP90']}"),
            ('够得着：唯一定位', lambda r: f"{r[1]['located']['reach']}（{100 * float(r[1]['located']['reachShare']):.0f}%）"),
            ('上界口径', lambda r: f"{r[1]['hi']['reach']}（{100 * float(r[1]['hi']['reachShare']):.0f}%）"),
            ('下界口径', lambda r: f"{r[1]['lo']['reach']}（{100 * float(r[1]['lo']['reachShare']):.0f}%）"),
            ('这些点上平均还差多少拍（max(0, 下界 − 阶梯落后) 的均值）：唯一定位 / 上界 / 下界', lambda r: f"{r[1]['located']['shortfallMean']} / {r[1]['hi']['shortfallMean']} / {r[1]['lo']['shortfallMean']}"),
        ]))
        tot = {v: (sum(int(by[m][v]['reach']) for m, _ in rows), sum(int(by[m][v]['behind']) for m, _ in rows)) for v in ('located', 'hi', 'lo')}
        md += ['', '合计够得着：' + '、'.join(f"{n} {a}/{b}" for n, (a, b) in (('唯一定位', tot['located']), ('上界口径', tot['hi']), ('下界口径', tot['lo']))) + '。', '']
    open(os.path.join(DATA, 'fid_tables.md'), 'w').write('\n'.join(md) + '\n')
    print(f'底座 {len(base)} 局、通道 {len(chan)} 局、决策层 {len(dec)} 局 → reports/ckpt-data/fid_base.csv、fid_channel.csv、fid_decision.csv、fid_tables.md')


if __name__ == '__main__':
    main()
