#!/usr/bin/env python3
"""m6_all_outcomes.py — 把三张全量表（out/_all/pages.csv、replay_facts.csv、traj.csv）和每局的 card.json、timeline.csv 拼起来，
按若干机械分组并排看结局：主队赢的局数、编队人均领土相对值（630 / 1530 / 3060 拍）。

先跑：python3 scripts/m6_all_pages.py --csv；python3 scripts/m6_all_replay.py --csv；python3 scripts/m6_all_traj.py --csv
用法：python3 scripts/m6_all_outcomes.py [--csv]        （--csv 写 out/_all/joined.csv）

人均相对值 rel(t) = 编队在 t 拍的领土合计 ÷ 全图陆地（timeline.csv 的 squadShare）÷（开局在场的编队号数 ÷ card.seededPlayers）。
  1.0 = 编队每个号正好拿到“全图陆地 ÷ 人数”那么多。编队号数：有录像的取录像里对上的席位数，否则取写过快照的号数。
  630 拍时图还没分完，rel 普遍小于 1；只在组间比较。
分组：
  A 指令通道：600–1500 拍陆攻+船的落地/放行比（replay_facts 的 nd600_1500）< 0.7 / ≥ 0.7 / 没有录像或录像不到 1530 拍
  B 页面：pages.csv 的掉队口径（落后中位峰值 ≥ 180 拍，或第一条 RESULT 时已有停住的页面，或 2500 拍前 ≥3 个号 left）
  C 被围：1500–3000 拍“没有任何可打对象”的快照对占比 ≥ 40% / < 40%
  D 出生：收场时有同像素的一对号 / 没有；有号没有任何出生指令落地 / 没有
  E 队数：2 队 / 3 队 / 4 队及以上（基准胜率不同）
  F 1530 拍人均相对值三分位
决策耗时 = traj.csv 的 avgMs（页面自己记的每拍决策耗时的累计平均），取各号在本地 600–1500 拍最后一个快照的值的中位数；一拍的时长是 56 毫秒。
每组给：局数、主队赢的局数、按队数的基准（各局 card.baseWinExpectation = 1/队数 相加，即“一支平均水平的队”该赢的局数）、
  rel630 / rel1530 / rel3060 的中位数、峰值份额相对值（card.peakSquadLandShare ÷ 人头占比）的中位数。
一个包里混了两场的（replay_facts 的 multi、或同一个号的快照拍号倒退、或 seededPlayers < 10）不进分组。
这是描述统计：赢局只有 16 局，组间差别大多在随机波动以内，脚本只列数，不做检验。
"""
import csv, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', '_all')
DATA = '/agent/repos/c136-data/bundles'


def rd(name):
    p = os.path.join(OUT, name)
    return {r['mid']: r for r in csv.DictReader(open(p))} if os.path.exists(p) else {}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    pages, rep, traj = rd('pages.csv'), rd('replay_facts.csv'), rd('traj.csv')
    rows = []
    for mid in sorted(os.listdir(DATA)):
        card = json.load(open(os.path.join(DATA, mid, 'card.json')))
        bots0, last_t, back, ms = set(), {}, False, {}
        tp = os.path.join(DATA, mid, 'traj.csv')
        if os.path.exists(tp):
            for x in csv.DictReader(open(tp)):
                try:
                    t = int(x['t'])
                except ValueError:
                    continue
                bots0.add(x['bot'])
                if t < last_t.get(x['bot'], -1):
                    back = True      # 同一个号的快照拍号倒退 = 包里混了两场
                last_t[x['bot']] = t
                if 600 <= t <= 1500:
                    try:
                        ms[x['bot']] = (float(x['avgMs']), float(x['maxMs']))   # 页面自己记的每拍决策耗时（累计平均、最大），取 600–1500 拍里最后一个快照
                    except ValueError:
                        pass
        q0 = rep.get(mid, {})
        multi = int(q0.get('multi') == '1' or back or (card.get('seededPlayers') or 0) < 10)
        # 编队席位数：有录像的取录像里对上的席位数（没写过快照的号也算），否则取写过快照的号数
        n_squad = int(q0['squad']) if q0 and not multi and q0.get('squad') else len(bots0)
        head = n_squad / card['seededPlayers'] if card.get('seededPlayers') and n_squad and not multi else None
        share = {}
        tl = os.path.join(DATA, mid, 'timeline.csv')
        if os.path.exists(tl):
            for x in csv.DictReader(open(tl)):
                try:
                    share[int(x['t'])] = float(x['squadShare'])
                except (ValueError, KeyError):
                    pass
        r = {'mid': mid, 'cohort': card['cohort'], 'teams': card.get('actualTeams'), 'won': int(bool(card['outcome']['primaryTeamWon'])),
             'result': card['outcome']['resultLabel'], 'split': int(bool(card['anomaliesSummary'].get('teamSplit'))), 'multi': multi,
             'base': card.get('baseWinExpectation'), 'squadN': n_squad, 'head': round(head, 4) if head else None}
        for t in (630, 1530, 3060):
            r[f'rel{t}'] = round(share[t] / head, 3) if head and t in share else None
        r['relPeak'] = round(card['outcome']['peakSquadLandShare'] / head, 3) if head and card['outcome'].get('peakSquadLandShare') is not None else None
        r['avgMs'] = round(statistics.median(v[0] for v in ms.values()), 2) if ms else None
        r['maxMs'] = round(max(v[1] for v in ms.values()), 1) if ms else None
        p, q, s = pages.get(mid, {}), rep.get(mid, {}), traj.get(mid, {})
        r['nd600_1500'] = None if multi else num(q.get('nd600_1500'))
        if r['nd600_1500'] is not None and r['nd600_1500'] > 1.15:
            r['nd600_1500'] = None   # 落地的比页面计数还多（A018：日志的 cmds 计数不全），这一局的比值不用
        r['hasReplay'] = int(bool(q)) and not multi
        lp = num(p.get('lagPeak'))
        r['pageLag'] = int((lp is not None and lp >= 180) or (num(p.get('stalled1')) or 0) >= 1 or (num(p.get('leftEarly')) or 0) >= 3) if p else None
        r['p2_boxed'] = num(s.get('p2_boxed'))
        r['p1_idleTgt'] = num(s.get('p1_idleTgt'))
        r['samePixel'] = None if (not q or multi) else int(num(q.get('samePixelPairs')) or 0)
        r['noSpawn'] = None if (not q or multi) else int(num(q.get('noSpawn')) or 0)
        r['batchShare'] = None if (not q or multi or not num(q.get('atkLanded'))) else round(num(q['batchRows']) / num(q['atkLanded']), 3)
        rows.append(r)
    if '--csv' in sys.argv:
        with open(os.path.join(OUT, 'joined.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/joined.csv（{len(rows)} 局）')

    def med(L, k):
        v = [r[k] for r in L if r[k] is not None]
        return f'{statistics.median(v):.2f}' if v else '-'

    def show(title, groups):
        print(f'== {title}')
        for name, L in groups:
            if not L:
                continue
            w = sum(r['won'] for r in L)
            e = sum(r['base'] or 0 for r in L)
            print(f"   {name:<34s} {len(L):3d} 局，主队赢 {w:2d}（{100 * w / len(L):3.0f}%，按队数的基准 {e:4.1f} 局）| rel630 {med(L, 'rel630')}  rel1530 {med(L, 'rel1530')}  rel3060 {med(L, 'rel3060')}  峰值 {med(L, 'relPeak')}"
                  f" | 决策耗时 {med(L, 'avgMs')} 毫秒/拍")

    mm = [r['mid'] for r in rows if r['multi']]
    print(f"# 一个包里混了两场、或开局行人数不可信的 {len(mm)} 局不进下面的分组：{' '.join(mm)}")
    for co in ('squad10', 'squad20', 'squad8', None):
        R0 = [r for r in rows if co is None or r['cohort'] == co]
        R = [r for r in R0 if not r['multi']]
        print(f"\n#### {co or '全部'}：{len(R0)} 局里主队赢 {sum(r['won'] for r in R0)} 局（各局 1/队数 相加的基准 {sum(r['base'] or 0 for r in R0):.1f} 局）；进分组的 {len(R)} 局里赢 {sum(r['won'] for r in R)} 局")
        show('A 指令通道（600–1500 拍 陆攻+船 落地/放行）', [
            ('< 0.5', [r for r in R if r['nd600_1500'] is not None and r['nd600_1500'] < 0.5]),
            ('0.5–0.7', [r for r in R if r['nd600_1500'] is not None and 0.5 <= r['nd600_1500'] < 0.7]),
            ('0.7–0.9', [r for r in R if r['nd600_1500'] is not None and 0.7 <= r['nd600_1500'] < 0.9]),
            ('≥ 0.9', [r for r in R if r['nd600_1500'] is not None and r['nd600_1500'] >= 0.9]),
            ('没有录像 / 录像不到 1530 拍 / 混了两场', [r for r in R if r['nd600_1500'] is None])])
        show('B 页面掉队（RESULT 锚点口径）', [('掉队', [r for r in R if r['pageLag'] == 1]), ('没看到', [r for r in R if r['pageLag'] == 0])])
        show('C 1500–3000 拍没有任何可打对象的快照对占比', [('≥ 40%', [r for r in R if r['p2_boxed'] is not None and r['p2_boxed'] >= 0.4]),
                                                 ('20–40%', [r for r in R if r['p2_boxed'] is not None and 0.2 <= r['p2_boxed'] < 0.4]),
                                                 ('< 20%', [r for r in R if r['p2_boxed'] is not None and r['p2_boxed'] < 0.2])])
        show('D 出生', [('收场有同像素的一对号', [r for r in R if r['samePixel']]), ('没有同像素', [r for r in R if r['samePixel'] == 0]),
                      ('有号 0 条出生指令落地', [r for r in R if r['noSpawn']]), ('每个号都有出生指令落地', [r for r in R if r['noSpawn'] == 0])])
        show('E 队数', [('2 队', [r for r in R if r['teams'] == 2]), ('3 队', [r for r in R if r['teams'] == 3]), ('4 队及以上', [r for r in R if (r['teams'] or 0) >= 4])])
        v = sorted(r['rel1530'] for r in R if r['rel1530'] is not None)
        if len(v) >= 6:
            a, b = v[len(v) // 3], v[2 * len(v) // 3]
            show(f'F 1530 拍人均相对值三分位（分界 {a:.2f} / {b:.2f}）', [
                ('低', [r for r in R if r['rel1530'] is not None and r['rel1530'] < a]),
                ('中', [r for r in R if r['rel1530'] is not None and a <= r['rel1530'] < b]),
                ('高', [r for r in R if r['rel1530'] is not None and r['rel1530'] >= b])])
        show('G 拆队', [('编队拆在几个队里', [r for r in R if r['split']]), ('同在一个队', [r for r in R if not r['split']])])


if __name__ == '__main__':
    main()
