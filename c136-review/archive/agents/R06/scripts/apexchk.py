#!/usr/bin/env python3
"""apexchk.py — 「外人」统计里有多少其实是另一支我方编队（squad10，名字带 [APEX]）

对手画像（foeprofile.py、crossmatch.py foes）把「不是 squad20 的真人」都算作外人。B010、B038、B039 这三局 squad10 也在场。
这个脚本数：外人之间的捐款、pct>=900 的捐款、外人对我方在场号的陆攻、我方对它们的陆攻，各有多少与 [APEX] 有关。

用法：python3 scripts/apexchk.py            产物：out/_cross/apexchk.txt（只读 sim_state.json，不重放）
"""
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
from r06lib import OUT  # noqa: E402

IDS = ['B010', 'B017', 'B021', 'B022', 'B023', 'B038', 'B039']


def wan(x):
    return f"{x / 1e4:,.1f} 万" if x < 1e7 else f"{x / 1e4:,.0f} 万"


def main():
    out = []
    out.append('| 局 | [APEX] 号 / 所在队 | 外人之间的捐款：笔 / 到账 | 其中与 [APEX] 有关（双方都是 [APEX]） | pct>=900：笔 / 到账 | 其中与 [APEX] 有关 | [APEX] 对我方在场号的陆攻：条 / 兵 | 我方对 [APEX] 的陆攻：条 / 兵 |')
    out.append('|---|---|---|---|---|---|---|---|')
    tot = Counter()
    pairs = []
    for mid in IDS:
        X = SD.Sim(mid)
        S = X.S
        squad = set(X.squad)

        def ap(p):
            return '[APEX]' in X.name(p).upper()

        apex = [p for p in range(X.H) if ap(p)]
        fd = [x for x in S['donations'] if x.get('ok') and x['from'] not in squad and x['to'] not in squad and x['from'] < X.H and x['to'] < X.H]
        hi = [r for r in fd if r['pct'] >= 900]
        apx = [r for r in fd if ap(r['from']) or ap(r['to'])]
        both = [r for r in fd if ap(r['from']) and ap(r['to'])]
        apx_hi = [r for r in hi if ap(r['from']) or ap(r['to'])]
        sm = lambda L: sum(r['delivered'] for r in L)  # noqa: E731
        hits_all = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c.get('to') in squad and c['p'] not in squad and c['p'] < X.H
                    and X.team[c['p']] != X.team[c['to']]]
        hits = [c for c in hits_all if not (c['to'] in X.leave and X.leave[c['to']]['t'] <= c['t'])]
        ah = [c for c in hits if ap(c['p'])]
        ah_husk = [c for c in hits_all if ap(c['p']) and c not in hits]
        oa = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c['p'] in squad and c.get('to') is not None and c['to'] < X.H and ap(c['to'])]
        st = lambda L: sum(c.get('sent', 0) for c in L)  # noqa: E731
        teams = Counter(X.team[p] for p in apex)
        out.append(f"| {mid} | {len(apex)} / {'、'.join(f'队{t}×{n}' for t, n in sorted(teams.items())) or '—'} | {len(fd)} / {wan(sm(fd))} | {len(apx)} / {wan(sm(apx))}（{len(both)} / {wan(sm(both))}） | "
                   f"{len(hi)} / {wan(sm(hi))} | {len(apx_hi)} / {wan(sm(apx_hi))} | {len(ah)} / {wan(st(ah))}（全部外人 {len(hits)} / {wan(st(hits))}；[APEX] 打我方已离场席位 {len(ah_husk)} / {wan(st(ah_husk))}） | {len(oa)} / {wan(st(oa))} |")
        for k, v in (('fd', len(fd)), ('fdD', sm(fd)), ('apx', len(apx)), ('apxD', sm(apx)), ('hi', len(hi)), ('hiD', sm(hi)), ('ahi', len(apx_hi)),
                     ('ah', len(ah)), ('ahT', st(ah)), ('ahh', len(ah_husk)), ('ahhT', st(ah_husk)), ('oa', len(oa)), ('oaT', st(oa)), ('late', sum(1 for r in fd if r['t'] >= 3213))):
            tot[k] += v
        c = Counter()
        d = defaultdict(int)
        for r in hi:
            k = (X.name(r['from']), X.name(r['to']))
            c[k] += 1
            d[k] += r['delivered']
        for k, v in c.most_common(3):
            pairs.append(f"{mid} {k[0]} → {k[1]}：{v} 笔 / {wan(d[k])}")
    out.append(f"| 合计 | — | {tot['fd']} / {wan(tot['fdD'])}（t>=3213 的 {tot['late']} 笔） | {tot['apx']} / {wan(tot['apxD'])} | {tot['hi']} / {wan(tot['hiD'])} | {tot['ahi']} | {tot['ah']} / {wan(tot['ahT'])}（打已离场席位 {tot['ahh']} / {wan(tot['ahhT'])}） | {tot['oa']} / {wan(tot['oaT'])} |")
    out.append('')
    out.append('pct>=900 捐款最多的几对（每局前 3）：' + '；'.join(pairs))
    txt = '\n'.join(out) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'apexchk.txt'), 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
