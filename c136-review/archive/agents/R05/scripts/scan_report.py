#!/usr/bin/env python3
"""scan_report.py — 把全量机械检测的输出装订成 reports/PATTERN-SCAN.md（只装订，不做新的计量）。

依次运行并收录：
  pattern_scan.py --tsv out/pattern-scan.tsv --json /tmp/c136-r05/work/pattern-scan.json --agg --sum --classes
  spawn_exec_sum.py --list                       （读 out/spawn-exec-all.tsv）
  perf_vs_lag.py
另做一张对照表：pattern_scan 的 L/N/B（只读对局包）对 已复盘各局 reviews/<局>.json 里的决策级延迟账（delay_account.py，要跑影子策略），
用来说明「不跑影子也能数」的口径和「跑了影子」的口径差多少。

前置：bash ../../tools/run-heavy.sh node scripts/replay_dump_all.mjs；
      python3 scripts/spawn_exec.py --tsv <全部有录像的局> > out/spawn-exec-all.tsv
用法：python3 scripts/scan_report.py [--out reports/PATTERN-SCAN.md]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
a = sys.argv[1:]
outp = a[a.index('--out') + 1] if '--out' in a else 'reports/PATTERN-SCAN.md'
SCANJ = '/tmp/c136-r05/work/pattern-scan.json'


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=110)
    if r.returncode != 0:
        raise SystemExit(f'失败：{" ".join(cmd)}\n{r.stderr[-800:]}')
    return r.stdout


def tsv_to_md(lines):
    rows = [ln.split('\t') for ln in lines if ln.strip()]
    if not rows:
        return []
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '|'.join(' --: ' for _ in rows[0]) + '|']
    out += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return out


scan = run(['python3', 'scripts/pattern_scan.py', '--tsv', 'out/pattern-scan.tsv', '--json', SCANJ, '--agg', '--sum', '--classes'])
spawn = run(['python3', 'scripts/spawn_exec_sum.py', '--list'])
perf = run(['python3', 'scripts/perf_vs_lag.py'])
doc = open(os.path.join(HERE, 'pattern_scan.py'), encoding='utf-8').read().split('"""')[1]

P = []
P.append('# 全量机械检测：高频失分模式在全部对局包里出现多少次')
P.append('')
P.append('> 本文件由 `python3 scripts/scan_report.py` 生成，不手改。所有数字来自下面三个脚本对全部有录像的对局包的输出；逐局明细在 `out/pattern-scan.tsv`、`out/spawn-exec-all.tsv`。')
P.append('> 这些检测只读对局包文件和录像命令流（`replay_dump_all.mjs` 解码），不跑引擎、不跑影子策略，全量跑一遍约 2 秒。')
P.append('')
P.append('## 0. 口径（pattern_scan.py 头注原文）')
P.append('')
P.append('```text')
P.append(doc.strip())
P.append('```')
P.append('')

# ---- 把 pattern_scan 的输出切成段 ----
secs = {}
cur = None
for ln in scan.split('\n'):
    if ln.startswith('====='):
        cur = ln.strip('= ').strip()
        secs[cur] = []
    elif cur is not None:
        secs[cur].append(ln)
P.append('## 1. 各检测项的全量合计')
P.append('')
for name, body in secs.items():
    if '全量合计' in name:
        P.append(f'### {name}')
        P.append('')
        P += [f'- {ln}' for ln in body if ln.strip()]
        P.append('')
P.append('## 2. 按 组别·版本 × 结局')
P.append('')
for name, body in secs.items():
    if name.startswith('按 组别'):
        P.append(body[0])
        P.append('')
        P += tsv_to_md(body[1:])
        P.append('')
P.append('## 3. 每个检测项把对局分成「有 / 没有」两类：赢的局数对期望赢局数')
P.append('')
for name, body in secs.items():
    if name.startswith('各检测项把对局'):
        P.append(body[0])
        P.append('')
        P += tsv_to_md(body[1:])
        P.append('')
P.append('读法：「期望赢」= 这些局各自 1÷队数 之和，即编队所在的队与别的队一样强时该赢多少局。样本小（A 组一共赢 8 局），这里只看方向，不做显著性判断。')
P.append('')
P.append('## 4. 出生执行（spawn_exec.py 全量 → spawn_exec_sum.py）')
P.append('')
sl = spawn.strip().split('\n')
P += tsv_to_md([ln for ln in sl if '\t' in ln])
P.append('')
P += [f'- {ln}' for ln in sl if '\t' not in ln and ln.strip()]
P.append('')
P.append('## 5. 策略每拍耗时对指令迟到（perf_vs_lag.py）')
P.append('')
P.append('```text')
P.append(perf.strip())
P.append('```')
P.append('')

# ---- 对照表 ----
P.append('## 6. 只读对局包的口径（pattern_scan）对 决策级口径（delay_account，要跑影子策略）')
P.append('')
P.append('每格「账本 ‖ 扫描」。账本 = 该时段落地指令里延迟 ≥90 拍的占比（只算落地的）；扫描 = 该时段有新指令的采样里「迟到 ≥90 拍或永远没到」的占比（含没到的）。')
P.append('')
S = {o['matchId']: o for o in json.load(open(SCANJ)) if 'error' not in o}
ids = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'reviews')) if f.endswith('.json'))
rows = [['局', '0–600 拍', '600–1500 拍', '1500–3000 拍', '3000+ 拍', '没落地：账本（想发−执行）÷想发', '没落地：扫描', '600–1500 拍同拍批：账本', '扫描', '延迟波局：账本（P50≥60）', '扫描（600–1500 迟到采样 ≥25%）']]
agree = 0
for m in ids:
    J = json.load(open(os.path.join(ROOT, 'reviews', f'{m}.json')))
    D = J.get('delayAccount') or {}
    o = S.get(m)
    if not D or not o:
        continue
    bp = {r['period']: r for r in D.get('delayByPeriod') or []}
    r = [m]
    for i, pn in enumerate(['0–600', '600–1500', '1500–3000', '3000+']):
        x = bp.get(pn) or {}
        L = o['L'][i]
        r.append((f"{100 * x.get('ge90', 0) / x['matched']:.0f}%" if x.get('matched') else '–') + ' ‖ ' + (f"{100 * L['late90'] / L['samples']:.0f}%" if L['samples'] else '–'))
    ft = D.get('funnelTotals') or {}
    r.append(f"{100 * ft['neverLandedByCount'] / ft['intended']:.0f}%" if ft.get('intended') else '–')
    r.append(f"{100 * o['N']['never'] / o['N']['issued']:.0f}%" if o['N']['issued'] else '–')
    bt = {x['period']: x for x in D.get('batches') or []}.get('600–1500') or {}
    r.append(f"{bt.get('batches', 0)} 批 {bt.get('cmds', 0)} 条")
    r.append(f"{o['B'][1]['batches']} 批 {o['B'][1]['cmds']} 条")
    lag_a = ((bp.get('600–1500') or {}).get('p50') or 0) >= 60
    lag_s = bool(o['L'][1]['samples']) and o['L'][1]['late90'] / o['L'][1]['samples'] >= 0.25
    agree += 1 if lag_a == lag_s else 0
    r += ['是' if lag_a else '否', '是' if lag_s else '否']
    rows.append(r)
P += tsv_to_md(['\t'.join(r) for r in rows])
P.append('')
P.append(f'「延迟波局」的判定两种口径一致的局：{agree}/{len(rows) - 1}。')
P.append('')
txt = '\n'.join(P) + '\n'
open(os.path.join(ROOT, outp), 'w', encoding='utf-8').write(txt)
print('→', outp, txt.count('\n'), '行')
