#!/usr/bin/env python3
# result_clock.py — 用 results.csv 的墙上时间（at）给「客户端落后服务器多少拍」做一个不依赖影子策略的旁证。
#   results.csv 每个有结果的号一行：tick = 上报那一刻客户端的本地拍，at = 上报的墙上时间（毫秒）。
#   服务器每拍 56 毫秒（TAU，可用 --tau 改）。每行算 c = 本地拍 − 墙上时间 ÷ TAU；c 最大的那一行是「跑得最靠前」的客户端，
#   取它做基准（--ref <号> 可指定别的），其余每行：相对落后 = 基准的 c − 本行的 c（≥0）。
#   基准行自己落后多少看不到，所以这是「至少落后这么多」；基准行那时的指令延迟在基线时，相对落后 ≈ 绝对落后。
#   推算的服务器拍 = 本行本地拍 + 相对落后。
#   另列：相邻两行之间「本地拍差 ÷ 墙上时间差」换算出的每拍毫秒（两行都不落后时应 ≈ TAU），
#         以及每行的 上报本地拍 − 录像里的阵亡拍（truth 里有这个号时；>10 说明客户端在追帧：本地拍在很短的墙上时间里跑了很多拍）。
#   B 组对局先跑 scripts/alias_overlay.py <局> 并加 C136_DATA=/tmp/c136-r05/overlay。
# 用法：python3 scripts/result_clock.py <局…> [--tau 56] [--ref 号] [--tsv]
import csv, datetime as dt, json, os, sys
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
args = sys.argv[1:]
TAU = float(args[args.index('--tau') + 1]) if '--tau' in args else 56.0
REF = args[args.index('--ref') + 1] if '--ref' in args else None
TSV = '--tsv' in args
ids = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--tau', '--ref'))]
if TSV: print('\t'.join(['match', 'bot', 'event', 'localTick', 'deathTick', 'reportMinusDeath', 'wallSec', 'relLagTicks', 'relLagSec']))
for mid in ids:
    d = DATA if os.path.exists(f'{DATA}/bundles/{mid}/results.csv') else '/agent/repos/c136-data'
    rows = []
    for r in csv.DictReader(open(f'{d}/bundles/{mid}/results.csv', encoding='utf-8')):
        try:
            at = dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp()
            rows.append({'bot': r['bot'], 'event': r['event'], 'tick': int(float(r['tick'])), 'at': at})
        except Exception:
            pass
    if not rows:
        if not TSV: print(f'== {mid}: results.csv 没有可用的行'); continue
        continue
    rows.sort(key=lambda r: r['at'])
    death = {}
    tp = f'/tmp/c136-r05/truth/{mid}.json'
    if os.path.exists(tp):
        T = json.load(open(tp)); P = {p['id']: p for p in T['players']}
        for s in T['squad']: death[s['bot']] = P[s['p']]['deathT']
    for r in rows: r['c'] = r['tick'] - r['at'] * 1000.0 / TAU
    ref = next((r for r in rows if r['bot'] == REF), max(rows, key=lambda r: r['c']))
    w0 = rows[0]['at']
    if not TSV: print(f"== {mid}: {len(rows)} 行；基准 {ref['bot']}（本地拍 {ref['tick']}）；TAU={TAU:g} 毫秒 ==")
    prev = None
    for r in rows:
        rel = ref['c'] - r['c']
        dth = death.get(r['bot'], -1)
        gap = r['tick'] - dth if dth is not None and dth >= 0 and r['event'] == 'died' else None
        if TSV:
            print('\t'.join(map(str, [mid, r['bot'], r['event'], r['tick'], dth if dth is not None else '', gap if gap is not None else '', round(r['at'] - w0, 3), round(rel), round(rel * TAU / 1000.0, 1)])))
        else:
            ms = ''
            if prev and r['at'] > prev['at'] and r['tick'] != prev['tick']:
                ms = f"｜与上一行之间 {r['tick'] - prev['tick']} 拍 / {r['at'] - prev['at']:.1f} 秒 = {1000.0 * (r['at'] - prev['at']) / (r['tick'] - prev['tick']):.1f} 毫秒/拍"
            print(f"   {r['bot']}: {r['event']} 上报本地拍 {r['tick']}" + (f"（录像阵亡拍 {dth}，上报 − 阵亡 = {gap}）" if gap is not None else '') + f"｜墙上 +{r['at'] - w0:.1f} 秒｜相对落后 {rel:.0f} 拍（{rel * TAU / 1000.0:.1f} 秒），推算服务器拍 {r['tick'] + rel:.0f}{ms}")
        prev = r
