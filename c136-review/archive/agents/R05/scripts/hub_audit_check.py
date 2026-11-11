#!/usr/bin/env python3
"""hub_audit_check.py — 把 hub 的《延迟与好地审计》（ledger/latency-and-land-160.json）和我的两份账对一遍。

只做对账，不改 hub 的文件。三件事：
  1) hub 的 land 字段 对 真实陆地格数：13 局用逐拍重演的 map.land（/tmp/c136-r05/truth/<局>.json），
     全部发现集用对局包 card.json 的 mapLand（只读 /agent/repos/c136-data/bundles，不碰验证集）。
  2) hub 的延迟分档（开局指令 lagP90）对 我的 L 检测（600–1500 拍迟到采样占比，out/pattern-scan.tsv）。
  3) 13 局：hub 的 t1530 vs_fair、按真实陆地换算后的值、我的 1500 拍人均地比值（out/cross-ledger.json）。
用法：python3 scripts/hub_audit_check.py [--out reports/HUB-AUDIT-RECONCILE.md]
"""
import csv
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R05 = os.path.dirname(HERE)
HUB = os.path.join(R05, '..', '..', 'ledger', 'latency-and-land-160.json')
TRUTH = os.environ.get('C136_TRUTH', '/tmp/c136-r05/truth')
BUNDLES = os.environ.get('C136_BUNDLES', '/agent/repos/c136-data/bundles')
MATCHES = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']
WAVE = {'A017', 'A021', 'A026', 'A034', 'A058', 'A065', 'A093', 'B010'}


def main():
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    hub = {x['matchId']: x for x in json.load(open(HUB, encoding='utf-8'))}
    scan = {r['matchId']: r for r in csv.DictReader(open(os.path.join(R05, 'out', 'pattern-scan.tsv'), encoding='utf-8'), delimiter='\t')}
    cl = {r['mid']: r for r in json.load(open(os.path.join(R05, 'out', 'cross-ledger.json'), encoding='utf-8'))}
    dl5 = {}
    for m in MATCHES:
        try:
            J = json.load(open(os.path.join(R05, 'reviews', m + '.json'), encoding='utf-8'))
        except OSError:
            continue
        vor = ((J.get('landAccount') or {}).get('voronoi') or {}).get('ratio')
        pc = ((cl.get(m) or {}).get('perCapita') or {}).get('1500') or {}
        dl5[m] = (vor, pc.get('ratio'))
    L = []
    w = L.append
    w('# HUB-AUDIT-RECONCILE — hub《延迟与好地审计》对 R05 两份账的对账')
    w('')
    w('> 本文件由 `python3 scripts/hub_audit_check.py --out reports/HUB-AUDIT-RECONCILE.md` 生成，不手改。')
    w('> hub 的数取自 `c136-review/ledger/latency-and-land-160.json`；我的数取自 `out/pattern-scan.tsv`（全量 L 检测）、`out/cross-ledger.json` 和 13 局逐拍重演真值。')
    w('')

    w('## 1. hub 的 `land` 字段 对 真实陆地格数')
    w('')
    lands = sorted({x['land'] for x in hub.values()})
    w(f'- hub 表 {len(hub)} 局的 `land` 取值：' + '、'.join(f'{v:,}' for v in lands) + f'（{len(lands)} 种）。')
    true_land = {}
    for m in MATCHES:
        p = os.path.join(TRUTH, m + '.json')
        if os.path.exists(p):
            t = json.load(open(p, encoding='utf-8'))
            true_land[m] = (t['map']['land'], t['humans'])
    tl = sorted(v[0] for v in true_land.values())
    w(f'- 13 局逐拍重演里的真实陆地格数：{tl[0]:,}–{tl[-1]:,}，中位 {int(st.median(tl)):,}；比 500,000 大的 {sum(1 for v in tl if v > 500000)} 局、小的 {sum(1 for v in tl if v < 500000)} 局。')
    w('- hub 的 `share_pct` = 我方地 ÷ `land`，`vs_fair` = `share_pct` ÷ 人头占比。`land` 不对时两者一起按 500,000 ÷ 真实陆地 的倍数偏。')
    w('')
    w('| 局 | hub `land` | 真实陆地 | hub t1530：在场号 / 份额 / vs_fair | 按真实陆地换算的 vs_fair | 我的出生份额（名下÷人数） | 我的 1500 拍人均地比（对其余真人） |')
    w('| --: | --: | --: | --: | --: | --: | --: |')
    hv, cv = [], []
    for m in MATCHES:
        if m not in hub or m not in true_land:
            continue
        x = hub[m]
        t = (x.get('landCapture') or {}).get('t1530') or {}
        vf = t.get('vs_fair')
        corr = vf * x['land'] / true_land[m][0] if vf is not None else None
        if vf is not None:
            hv.append(vf)
            cv.append(corr)
        d0, d1 = dl5.get(m, (None, None))
        w(f'| {m} | {x["land"]:,} | {true_land[m][0]:,} | {t.get("n", "–")} / {t.get("share_pct", "–")}% / {vf if vf is not None else "–"} | {corr:.2f} | {d0:.2f} | {d1:.2f} |')
    w('')
    w(f'- 13 局 hub 的 t1530 vs_fair 中位 {st.median(hv):.2f}；按真实陆地换算后中位 {st.median(cv):.2f}。')
    w('- 最后两列与 `reports/DELAY-AND-LAND-ACCOUNT.md` 第 5 节同源（各局复盘 JSON 的 `landAccount.voronoi.ratio`、`out/cross-ledger.json` 的 `perCapita`），口径不同：hub 的分母是全图陆地（含还在机器人和中立手里的），分子只数当时在场的号；我的人均地比的分母是其余真人的人均地，离场和阵亡的席位也算。')
    w('')

    # 全部发现集：card.json 的 mapLand
    w('### 全部发现集：按 card.json 的 `mapLand` 重算')
    w('')
    w('hub 的脚本 `c136-review/tools/latency-and-land-audit.py` 第 54 行取 `card["map"]["land"]`，没有再取 `card["land"]`，都没有就用 500000。'
      '发现集的 card.json 里这个数叫 `mapLand`。')
    w('')
    cards = {}
    for m, x in hub.items():
        if x.get('set') != 'discovery':
            continue
        p = os.path.join(BUNDLES, m, 'card.json')
        if os.path.exists(p):
            c = json.load(open(p, encoding='utf-8'))
            cards[m] = c
    has_field = sum(1 for c in cards.values() if (c.get('map') or {}).get('land') or c.get('land'))
    has_ml = sum(1 for c in cards.values() if c.get('mapLand'))
    w(f'- hub 表里的发现集 {len(cards)} 局：card.json 里有 `map.land` 或 `land` 的 {has_field} 局，有 `mapLand` 的 {has_ml} 局。')
    same = sum(1 for m in true_land if m in cards and cards[m].get('mapLand') == true_land[m][0])
    w(f'- 13 局里 card.json 的 `mapLand` 与逐拍重演的陆地格数相等的 {same} 局。')
    mls = sorted(c['mapLand'] for c in cards.values() if c.get('mapLand'))
    if mls:
        w(f'- `mapLand` 的范围 {mls[0]:,}–{mls[-1]:,}，中位 {int(st.median(mls)):,}；>500,000 的 {sum(1 for v in mls if v > 500000)} 局、<500,000 的 {sum(1 for v in mls if v < 500000)} 局；'
          f'500,000 ÷ `mapLand` 的范围 {500000 / mls[-1]:.2f}–{500000 / mls[0]:.2f}。')
    w('')
    w('| 编队 | 局数 | t630 vs_fair 中位：hub | 按 `mapLand` 重算 | t1530 vs_fair 中位：hub | 按 `mapLand` 重算 | t1530 重算后 <1 的局 |')
    w('| --: | --: | --: | --: | --: | --: | --: |')
    by_c = {}
    for m, c in cards.items():
        if not c.get('mapLand'):
            continue
        x = hub[m]
        k = 500000 / c['mapLand']
        lc = x.get('landCapture') or {}
        a = (lc.get('t630') or {}).get('vs_fair')
        b = (lc.get('t1530') or {}).get('vs_fair')
        by_c.setdefault(x.get('cohort'), []).append((a, b, k))
    for coh in sorted(by_c):
        R = by_c[coh]
        a0 = [r[0] for r in R if r[0] is not None]
        a1 = [r[0] * r[2] for r in R if r[0] is not None]
        b0 = [r[1] for r in R if r[1] is not None]
        b1 = [r[1] * r[2] for r in R if r[1] is not None]
        w(f'| {coh} | {len(R)} | {st.median(a0):.3f}（{len(a0)} 局） | {st.median(a1):.3f} | {st.median(b0):.3f}（{len(b0)} 局） | {st.median(b1):.3f} | {sum(1 for v in b1 if v < 1)}/{len(b1)} |')
    w('')
    w('- 重算 = hub 的 vs_fair × 500,000 ÷ `mapLand`（分子、人头占比都不动，只换陆地格数）。')
    w('')

    w('## 2. hub 的延迟分档 对 我的 L 检测')
    w('')
    w('hub 的 `lagP90Ticks` 量的是 `[HL-OPENING]` 日志行（1500 拍前每个地租周期一条打中立的指令）到录像执行的延迟。')
    w('我的 L 检测量的是 600–1500 拍每条 `[HL-TICK]` 采样时最新一条指令还要多少拍才执行；「迟到采样占比」= 迟到 ≥90 拍或永远没到的采样 ÷ 有新指令的采样。')
    w('')
    tiers = [('<35', lambda v: v < 35), ('35–120', lambda v: 35 <= v < 120), ('≥120', lambda v: v >= 120)]
    rows = []
    for m, x in hub.items():
        if x.get('set') != 'discovery' or x.get('cohort') != 'squad10' or m not in scan:
            continue
        le = x.get('latencyAndExec') or {}
        p90 = le.get('lagP90Ticks')
        r = scan[m]
        try:
            n = int(r['L1.samples'])
            late = int(r['L1.late90'])
            rt = int(r['replayTicks'])
        except (KeyError, ValueError):
            continue
        if p90 is None or n == 0 or rt < 1500:
            continue
        rows.append((m, p90, late / n))
    w(f'A 组发现集里两边都有数的 {len(rows)} 局：')
    w('')
    w('| hub 分档（开局指令 lagP90，拍） | 局数 | 其中我的 L 检测判为延迟波局（600–1500 拍迟到采样 ≥25%） | ≥50% |')
    w('| --: | --: | --: | --: |')
    for name, cond in tiers:
        sub = [r for r in rows if cond(r[1])]
        w(f'| {name} | {len(sub)} | {sum(1 for r in sub if r[2] >= 0.25)} | {sum(1 for r in sub if r[2] >= 0.5)} |')
    w(f'| 合计 | {len(rows)} | {sum(1 for r in rows if r[2] >= 0.25)} | {sum(1 for r in rows if r[2] >= 0.5)} |')
    w('')
    w('我复盘的 8 个延迟波局（决策级延迟账，600–1500 拍落地指令延迟中位 ≥60 拍）在 hub 表里的分档：')
    w('')
    w('| 局 | hub 开局指令 lagP50 / lagP90（拍） | hub 分档 | 我的 600–1500 拍迟到采样占比 |')
    w('| --: | --: | --: | --: |')
    low = 0
    for m in MATCHES:
        if m not in WAVE or m not in hub:
            continue
        le = hub[m].get('latencyAndExec') or {}
        p50, p90 = le.get('lagMedTicks'), le.get('lagP90Ticks')
        tier = next((name for name, cond in tiers if p90 is not None and cond(p90)), '–')
        low += tier == '<35'
        r = scan.get(m, {})
        sh = f"{100 * int(r['L1.late90']) / int(r['L1.samples']):.0f}%" if r.get('L1.samples') and int(r['L1.samples']) else '–'
        w(f'| {m} | {p50} / {p90} | {tier} | {sh} |')
    w('')
    w(f'- 8 个延迟波局里 {low} 个在 hub 表里落在「<35 拍」一档。')
    w('')
    text = '\n'.join(L) + '\n'
    if out:
        open(out, 'w', encoding='utf-8').write(text)
        print('→', out)
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
