#!/usr/bin/env python3
"""m6_tables.py — 把我复盘过的 15 局的逐局产物（out/<局>/*.json）拼成跨局对比表（markdown），供 reports/CROSS-MATCH-SUMMARY.md 引用。
不做任何重算，只读已有产物：
  lag_periods.json   （lag_periods.py：延迟硬账，按决策拍分段）
  voronoi_summary.json（voronoi_share.mjs：好地账）
  attrib3.json       （attrib3.py：600–1500 拍三分账）
  spawn_layouts.json （spawn_layouts.py --json：c116 协调器的落点表；c110 的两局没有）
  spawn_actual.csv   （spawn_actual.mjs：每个号最后落地的出生点）
  analysis/<局>.json  （手写的逐局结论：归类、转折点、判定）
  out/_all/joined.csv、pages.csv、replay_facts.csv（m6_all_*.py --csv）
用法：python3 scripts/m6_tables.py [overview|delay|land|ai|attrib|spawn|verdict|all]
"""
import csv, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
MIDS = 'A075 A057 A059 A094 A055 A054 A031 A019 A009 A023 A050 A003 A005 B039 B043'.split()
PERIODS = ('0–600', '600–1500', '1500–3000', '3000+')


def J(mid, name):
    p = os.path.join(R, 'out', mid, name)
    return json.load(open(p)) if os.path.exists(p) else None


def allcsv(name):
    p = os.path.join(R, 'out', '_all', name)
    return {r['mid']: r for r in csv.DictReader(open(p))} if os.path.exists(p) else {}


def pct(a, b, d=0):
    return f'{100 * a / b:.{d}f}%' if b else '-'


def overview():
    jo, pg, rf = allcsv('joined.csv'), allcsv('pages.csv'), allcsv('replay_facts.csv')
    print('| 局 | 版本·编队 | 图（陆地格）· 真人 · 队数 | 结局（终局拍） | 归类 | 编队人均相对值 630 / 1530 / 3060 / 峰值 | 600–1500 落地/放行 | 页面落后峰值（拍 @ 服务器拍） | 1500 拍前被移出 | 判定 错/对/不清 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for m in MIDS:
        a = json.load(open(os.path.join(R, 'analysis', m + '.json')))
        card = json.load(open(f'/agent/repos/c136-data/bundles/{m}/card.json'))
        j, p, q = jo.get(m, {}), pg.get(m, {}), rf.get(m, {})
        v = J(m, 'voronoi_summary.json')
        ver = 'c110' if card['cohort'] == 'squad20' else 'c116'
        vd = [x['verdict'] for x in a['decisions']]
        f = lambda x: x if x not in ('', None) else '-'
        multi = j.get('multi') == '1'
        rel = '（包里混了两场）' if multi else f"{f(j.get('rel630'))} / {f(j.get('rel1530'))} / {f(j.get('rel3060'))} / {f(j.get('relPeak'))}"
        nd = '-' if multi else f(q.get('nd600_1500'))
        lv = '-' if (not q or multi) else f"{f(q.get('left1500'))}/{q.get('squad')}"
        print(f"| {m} | {ver} · {v['squadN']} 个号 | {card['mapId']}（{card['mapLand']}）· {v['humans']} · {card['actualTeams']} | {card['outcome']['resultLabel']}（{card['outcome']['endTick']}） | {a['lossArchetype']} | "
              f"{rel} | {nd} | {f(p.get('lagPeak'))} @ {f(p.get('srvPeak'))} | {lv} | {vd.count('error')}/{vd.count('good')}/{vd.count('unclear')} |")


def delay():
    print('| 局 | ' + ' | '.join(f'{p}：陆攻+船 放行→落地（落地率）延迟 P50/P90/最大；捐兵 放行→落地' for p in PERIODS) + ' | 全程：想发 / 放行 / 日志指令数 / 录像落地 |')
    print('|---|' + '---|' * (len(PERIODS) + 1))
    agg = {p: [0, 0, 0, 0] for p in PERIODS}
    for m in MIDS:
        d = J(m, 'lag_periods.json')
        cells = []
        for p in PERIODS:
            x = d['periods'].get(p)
            if not x or not (x['aAcc'] or x['dAcc']):
                cells.append('—')
                continue
            s = f"{x['aAcc']}→{x['aLand']}（{pct(x['aLand'], x['aAcc'])}）" + (f" {x['aP50']}/{x['aP90']}/{x['aMax']}" if x['aLand'] else '')
            if x['dAcc']:
                s += f"；捐 {x['dAcc']}→{x['dLand']}"
            cells.append(s)
            agg[p][0] += x['aAcc']; agg[p][1] += x['aLand']; agg[p][2] += x['dAcc']; agg[p][3] += x['dLand']
        t = d['total']
        print(f"| {m} | " + ' | '.join(cells) + f" | {t['want']} / {t['ok']} / {t['logCmds']} / {t['replayLanded']} |")
    print('| 15 局合计 | ' + ' | '.join(f"{a[0]}→{a[1]}（{pct(a[1], a[0])}）；捐 {a[2]}→{a[3]}（{pct(a[3], a[2])}）" for a in agg.values()) + ' | |')
    # 迟到的代价（600–1500）
    print()
    print('| 局 | 600–1500 落地的陆攻 | 落地时目标已不在 | 一兵未扣 | 同拍 ≥3 条的批次（条数）| 批次里最重的一拍扣掉余额的 | 21 拍内重复 |')
    print('|---|---|---|---|---|---|---|')
    for m in MIDS:
        x = J(m, 'lag_periods.json')['periods'].get('600–1500')
        if not x:
            continue
        print(f"| {m} | {x['atkLanded']} | {x['targetGone']}（{pct(x['targetGone'], x['atkLanded'])}） | {x['zero']}（{pct(x['zero'], x['atkLanded'])}） | {x['batches']}（{x['batchRows']}） | {100 * x['batchWorst']:.0f}% | {x['repeat']} |")


def land():
    print('| 局 | 真人 · 本队号 | 天然份额 vs 人头占比 | 每号天然地盘中位：本队 / 其他真人 | 630 拍吃到天然地盘的几成：本队 / 其他真人（中位） | 1500 拍：本队（在场的中位，个数）/ 其他真人 | 1500 拍本队多边形归谁：自己 / 本队别的号 / 同队路人 / 敌方 / 离场壳 / AI+无主 |')
    print('|---|---|---|---|---|---|---|')
    for m in MIDS:
        v = J(m, 'voronoi_summary.json')
        a, b = v['ticks']['630'], v['ticks']['1500']
        rg, n = b['region'], b['regionCells']
        g = lambda k: rg.get(k, 0)
        print(f"| {m} | {v['humans']} · {v['squadN']} | {v['squadNatPct']:.1f}% vs {v['headPct']:.1f}% | {v['natMedSquad']:g} / {v['natMedOther']:g} | {a['ratioMedSquad']:.2f} / {a['ratioMedOther']:.2f} | "
              f"{b['ratioMedSquad']:.2f}（{b['ratioMedSquadLive']:.2f}，{b['liveSquad']}）/ {b['ratioMedOther']:.2f} | "
              f"{pct(g('self'), n)} / {pct(g('squadSameTeam') + g('squadOtherTeam'), n)} / {pct(g('mates'), n)} / {pct(g('enemy'), n)} / {pct(g('husk'), n)} / {pct(g('ai') + g('neutral'), n)} |")


def ai():
    print('| 局 | 600 拍的 AI 地：全图 / 本队多边形内 | 到期（1800 拍）多边形内的归谁：自己 / 本队别的号 / 同队路人 / 敌方 / 离场壳 / 仍是 AI 或无主 | 全图 AI 地里本队拿到的 | 本队人头占比 |')
    print('|---|---|---|---|---|')
    for m in MIDS:
        v = J(m, 'voronoi_summary.json')
        x = v['ai']
        r, n = x['inRegion'], x['cellsIn']
        g = lambda k: r.get(k, 0)
        sq = sum(c for k, c in x['all'].items() if k.startswith('squad/'))
        to = '' if x['to'] == 1800 else f"（到 {x['to']} 拍）"
        print(f"| {m} | {x['cellsAll']} / {n} | {pct(g('self'), n)} / {pct(g('squadSameTeam') + g('squadOtherTeam'), n)} / {pct(g('mates'), n)} / {pct(g('enemy'), n)} / {pct(g('husk'), n)} / {pct(g('ai') + g('neutral'), n)}{to} | {pct(sq, x['cellsAll'], 1)} | {v['headPct']:.1f}% |")


def attrib():
    print('| 局 | ① 出生：天然地盘不到其他真人中位一半的号 | 600–1500 决策拍 | 下令 | 没有可打对象 | 按租期等（DP） | ② 保底线 ≥ 余额（取自 safeFinite / dpKeep / 每格价项） | ③ 落地的陆攻：条数 / 目标已不在 / 一兵未扣 | 一兵未扣的令想出的兵占比 | 落地延迟中位 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    T = dict(acts=0, cmd=0, boxed=0, dp=0, fl=0, s=0, k=0, p=0, landed=0, gone=0, zero=0, low=0, squad=0)
    for m in MIDS:
        d = J(m, 'attrib3.json')
        s, f, l = d['spawn'], d['floor'], d['late']
        n = f['acts']
        fl = f['floor'] + f['floorN']
        print(f"| {m} | {s['low']}/{s['squad']} | {n} | {pct(f['cmd'], n, 1)} | {pct(f['boxed'], n, 1)} | {pct(f['dp'], n, 1)} | {pct(fl, n, 1)}（{f['bySafe']} / {f['byKeep']} / {f['byPx']}） | "
              f"{l['landed']} / {l['gone']} / {l['zero']} | {pct(l['zeroWanted'], l['allWanted'], 1)} | {l['lagMed']} |")
        for k, val in (('acts', n), ('cmd', f['cmd']), ('boxed', f['boxed']), ('dp', f['dp']), ('fl', fl), ('s', f['bySafe']), ('k', f['byKeep']), ('p', f['byPx']),
                       ('landed', l['landed']), ('gone', l['gone']), ('zero', l['zero']), ('low', s['low']), ('squad', s['squad'])):
            T[k] += val
    n = T['acts']
    print(f"| 15 局合计 | {T['low']}/{T['squad']} | {n} | {pct(T['cmd'], n, 1)} | {pct(T['boxed'], n, 1)} | {pct(T['dp'], n, 1)} | {pct(T['fl'], n, 1)}（{T['s']} / {T['k']} / {T['p']}） | {T['landed']} / {T['gone']} / {T['zero']} | | |")


def spawn():
    print('| 局 | 协调器求解次数 / 不同落点表 | 第一份表落地的点 | 收场站在最后一份表上的号 | 没有任何出生指令落地的号 | 收场的阵由几种版本组合拼成 | 本队两号最近距离（像素） | 同像素的对（其中两个点不出自同一份表） | 离已站定的敌方真人 <40 像素的号 | 每号天然地盘中位：本队 / 其他真人 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    T = dict(v1=0, v1n=0, on=0, sq=0, zero=0, same=0, games=0, nosp=0, sp=0, spd=0, ne=0)
    for m in MIDS:
        s, v = J(m, 'spawn_layouts.json'), J(m, 'voronoi_summary.json')
        nat = f"{v['natMedSquad']:g} / {v['natMedOther']:g}"
        if not s:
            print(f"| {m} | （c110：没有协调器，各号本地分槽） | — | — | — | — | — | — | — | {nat} |")
            continue
        print(f"| {m} | {s['solves']} / {s['layouts']} | {s['v1Landed']}/{s['v1Bots']} | {s['onLast']}/{s['squad']} | {s['noSpawnCmd']} | {s['finalGroups']} | {s['pairMin']} | {s['samePixelPairs']}（{s['samePixelDiffVersion']}） | {s['nearEnemy']} | {nat} |")
        T['v1'] += s['v1Landed']; T['v1n'] += s['v1Bots']; T['on'] += s['onLast']; T['sq'] += s['squad']; T['nosp'] += s['noSpawnCmd']
        T['zero'] += 1 if s['v1Landed'] == 0 else 0; T['same'] += 1 if s['pairMin'] == 0 else 0; T['games'] += 1
        T['sp'] += s['samePixelPairs']; T['spd'] += s['samePixelDiffVersion']; T['ne'] += s['nearEnemy']
    print(f"| c116 的 {T['games']} 局合计 | | {T['v1']}/{T['v1n']}（一个点都没落地的 {T['zero']} 局） | {T['on']}/{T['sq']} | {T['nosp']} | | 有同像素的 {T['same']} 局 | {T['sp']}（{T['spd']}） | {T['ne']} | |")


def verdict():
    print('| 局 | 归类 | 判定 错 / 对 / 不清 | 转折点（拍：编队份额 % 前 → 后） |')
    print('|---|---|---|---|')
    for m in MIDS:
        a = json.load(open(os.path.join(R, 'analysis', m + '.json')))
        vd = [x['verdict'] for x in a['decisions']]
        tp = '；'.join(f"{t['t0']}–{t['t1']}：{t['shareBefore']} → {t['shareAfter']}" for t in a['turningPoints'])
        print(f"| {m} | {a['lossArchetype']} | {vd.count('error')} / {vd.count('good')} / {vd.count('unclear')} | {tp} |")


def main():
    sec = sys.argv[1] if len(sys.argv) > 1 else 'all'
    fns = {'overview': overview, 'delay': delay, 'land': land, 'ai': ai, 'attrib': attrib, 'spawn': spawn, 'verdict': verdict}
    for k, fn in fns.items():
        if sec in (k, 'all'):
            print(f'\n### {k}\n')
            fn()


if __name__ == '__main__':
    main()
