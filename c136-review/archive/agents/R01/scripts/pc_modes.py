#!/usr/bin/env python3
"""pc_modes.py — 影子策略的“待检记录从哪一拍开始核对”几种口径，在各局上和日志 [HL-TICK] 对得上的点数。

用法：python3 scripts/pc_modes.py [matchId ...] [--tags land,turn,]   （空标签 = 该局当前的默认输出 shadow_check.csv）
读 out/<mid>/shadow_check[_<tag>].csv（shadow.mjs --pc-shift <口径> --tag <tag> 写的）。
“除船全同” = nb、neut 相同，且 cmds−boats（进攻+捐兵的受理条数）相同；船指令的受理口径另有已知差异（见 notes/PROGRESS.md）。
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
args = [a for a in sys.argv[1:] if not a.startswith('--')]
tags = ['land', 'turn', '']
if '--tags' in sys.argv:
    tags = sys.argv[sys.argv.index('--tags') + 1].split(',')
    args = [a for a in args if a != sys.argv[sys.argv.index('--tags') + 1]]
mids = args or sorted(d for d in os.listdir(OUT) if os.path.exists(os.path.join(OUT, d, 'shadow_check.csv')))
tot = {t: [0, 0, 0] for t in tags}
print('局   | ' + ' | '.join(f"{(t or '默认'):>6s} 点数/四项全同/除船全同" for t in tags))
for mid in mids:
    cells = []
    for t in tags:
        f = os.path.join(OUT, mid, f"shadow_check{'_' + t if t else ''}.csv")
        if not os.path.exists(f):
            cells.append(f"{'—':>28s}")
            continue
        rows = list(csv.DictReader(open(f)))
        ok = sum(int(r['ok']) for r in rows)
        nb = sum(1 for r in rows if r['logNb'] == r['shNb'] and r['logNeut'] == r['shNeut']
                 and int(r['logCmds']) - int(r['logBoats']) == int(r['shCmds']) - int(r['shBoats']))
        tot[t][0] += len(rows); tot[t][1] += ok; tot[t][2] += nb
        bad = sorted({r['bot'] for r in rows if not (r['logNb'] == r['shNb'] and r['logNeut'] == r['shNeut']
                      and int(r['logCmds']) - int(r['logBoats']) == int(r['shCmds']) - int(r['shBoats']))})
        cells.append(f"{len(rows):>10d}/{ok}/{nb}" + (f"（差：{' '.join(bad)}）" if bad else ''))
    print(f"{mid} | " + ' | '.join(cells))
print('合计 | ' + ' | '.join(f"{tot[t][0]:>10d}/{tot[t][1]}/{tot[t][2]}" for t in tags))
