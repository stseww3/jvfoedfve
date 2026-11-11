#!/usr/bin/env python3
"""leave_grid.py — 录像里的 leave 指令落在哪些拍：本队号的 leave 是不是都落在同一个“16 个回合”（112 拍）的网格上；
以及本队席位被 leave 的比例和指令通道好坏的关系。

背景：A005 里本队 4 条 leave 在 1428、1540、1652、1652 拍，相隔正好 112 拍；同一局别的真人的 leave 不在这个网格上。
本脚本对每一局列出：本队席位的 leave 拍、它们对 112 取余的值、是否全部同余；其他真人的 leave 里和本队同余的有几条（随机的话约 1/16）。
只读 out/<局号>/replay_cmds.csv（replay_cmds.mjs 或 resim.mjs 写的，不模拟）和对局包的日志。

口径：
  * 本队席位 = 日志里 `[号] … me=N` 给出的席位号（和 m6_all_replay.py 同一套；c110 的号不带 [APEX] 前缀，不能按名字认）。
  * 不是同一场对局的包（m6_match_split.py）不计。
  * 同一场对局有两个包时（另一支编队的视角），另一支编队的席位不算“其他真人”。
  * 只看出生阶段之后（tick > 0）的 leave。
  * 席位阵亡之后的 leave（results.csv 里这个席位有 event=died 且拍号不晚于 leave）是收场以后页面关掉，单列，不进同余和成簇的统计。
  * 8500 拍以后的 leave 可能出自策略的自退分支（三个版本都要求 g.t > 8500），也单列，不进同余和成簇的统计。
末尾另给一张表：按 600–1500 拍的落地/放行比（out/_all/land.csv 的 nd600_1500）分档，本队席位 1500 / 2500 拍前有 leave 的比例
（out/_all/replay_facts.csv 的 left1500、left2500）。这张表不依赖 RESULT 行。

用法：python3 scripts/leave_grid.py [局号 ...] [--period 112]     不给局号 = 所有有录像指令表的包
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m6_all_replay as R  # noqa: E402
import m6_match_split  # noqa: E402

OUT = os.path.join(HERE, '..', 'out')
DATA = m6_match_split.DATA
SELF_EXIT = 8500   # 三个版本的自退分支都要求 g.t > 8500


def died_ticks(mid):
    """{席位号: 阵亡拍}，取自 results.csv 的 event=died 行（meId 是席位号，tick 是阵亡那一拍）。"""
    out = {}
    rp = os.path.join(DATA, mid, 'results.csv')
    if not os.path.exists(rp):
        return out
    for x in csv.DictReader(open(rp)):
        if x.get('event') != 'died':
            continue
        try:
            p, t = int(x['meId']), int(float(x['tick']))
        except (KeyError, ValueError):
            continue
        out[p] = min(t, out.get(p, 10 ** 9))
    return out


def main():
    a = sys.argv[1:]
    period = int(a[a.index('--period') + 1]) if '--period' in a else 112
    ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--period')]
    cards, replays = R.load_all()
    split = m6_match_split.load_split()
    if not ids:
        ids = sorted(cards)
    print(f'== leave 指令的拍号对 {period} 取余（{period // 7} 个回合）；只看出生阶段之后（tick > 0）的 leave；本队席位按日志的 me=N 认')
    tot = {'m': 0, 'multi': 0, 'same': 0, 'pairs': 0, 'pairs_same': 0, 'oth': 0, 'oth_same': 0, 'cl': 0, 'cl_rows': 0, 'rows': 0, 'post': 0, 'post_m': 0, 'late': 0, 'late_m': 0}
    skipped = []
    for mid in ids:
        best = R.pick_replay(mid, cards, replays)
        if best is None:
            continue
        if mid in split:
            skipped.append(mid)
            continue
        meta, rows = replays[best]
        H = meta['humans']
        seats, multi, _ = R.read_log(mid)
        if multi or cards[mid].get('seededPlayers') != H:
            skipped.append(mid)
            continue
        S = set(seats.values())
        peer = set()
        for o in R.same_match(mid, cards):
            if o not in split:
                peer |= set(R.read_log(o)[0].values())
        sq, post, late, oth = [], [], [], []
        died = died_ticks(mid)
        for r in rows:
            if r['kind'] != 'leave' or int(r['tick']) <= 0:
                continue
            p, t = int(r['player']), int(r['tick'])
            if p in S:
                (post if p in died and died[p] <= t else (late if t > SELF_EXIT else sq)).append(t)
            elif p < H and p not in peer and t <= SELF_EXIT:
                oth.append(t)
        if post:
            tot['post'] += len(post); tot['post_m'] += 1
        if late:
            tot['late'] += len(late); tot['late_m'] += 1
        extra = ''
        if late:
            extra += f"；另有 {SELF_EXIT} 拍后的 leave {len(late)} 条（{' '.join(str(t) for t in sorted(late))}）"
        if post:
            extra += f"；另有阵亡之后的 leave {len(post)} 条（{' '.join(str(t) for t in sorted(post))}）"
        if not sq:
            if extra:
                print(f"  {mid}: {SELF_EXIT} 拍前席位还活着时的 leave 0 条{extra}")
            continue
        tot['m'] += 1
        ticks = sorted(sq)
        distinct = sorted(set(ticks))
        res = sorted({t % period for t in ticks})
        tot['rows'] += len(ticks)
        # 同一拍 ≥3 个号一起 leave
        for t in distinct:
            n = ticks.count(t)
            if n >= 3:
                tot['cl'] += 1
                tot['cl_rows'] += n
        line = f"  {mid}: 本队 leave {len(ticks)} 条，拍号 {' '.join(str(t) for t in ticks)}；余数 {res}"
        if len(distinct) >= 2:
            tot['multi'] += 1
            pairs = [(x, y) for i, x in enumerate(distinct) for y in distinct[i + 1:]]
            same = sum(1 for x, y in pairs if (y - x) % period == 0)
            tot['pairs'] += len(pairs); tot['pairs_same'] += same
            if len(res) == 1:
                tot['same'] += 1
                line += '  <<< 不同拍的 leave 全部同余'
            else:
                line += f'；不同拍两两同余 {same}/{len(pairs)} 对'
        if oth and len(res) == 1:
            hit = sum(1 for t in oth if t % period == res[0])
            tot['oth'] += len(oth); tot['oth_same'] += hit
            line += f'；其他真人的 leave {len(oth)} 条里同余的 {hit} 条'
        print(line + extra)
    print(f"# {SELF_EXIT} 拍前席位还活着时被 leave 的局 {tot['m']}（leave 合计 {tot['rows']} 条；同一拍 ≥3 个号一起 leave 的 {tot['cl']} 次共 {tot['cl_rows']} 条）；"
          f"其中 leave 落在 ≥2 个不同拍的 {tot['multi']} 局，全部同余的 {tot['same']} 局；"
          f"不同拍两两同余 {tot['pairs_same']}/{tot['pairs']} 对（随机约 1/{period // 7}）；"
          f"在本队全部同余的局里，其他真人的 leave {tot['oth']} 条里同余的 {tot['oth_same']} 条")
    print(f"# 不计入上面的 leave：{SELF_EXIT} 拍以后的（策略的自退分支可达）{tot['late']} 条，{tot['late_m']} 局；席位阵亡之后的（页面收场后关掉）{tot['post']} 条，{tot['post_m']} 局")
    if skipped:
        print(f"# 不是同一场对局、不计的包：{' '.join(skipped)}")

    # —— 离场比例 × 指令通道 ——
    lp, fp = os.path.join(OUT, '_all', 'land.csv'), os.path.join(OUT, '_all', 'replay_facts.csv')
    if os.path.exists(lp) and os.path.exists(fp):
        land = {r['mid']: r for r in csv.DictReader(open(lp))}
        facts = {r['mid']: r for r in csv.DictReader(open(fp))}
        print('\n== 本队席位被 leave 的比例 × 600–1500 拍的落地/放行比（好地账表里有这个比值的局）')
        for co in sorted({r['cohort'] for r in land.values()}):
            G = {'< 0.7': [], '0.7–0.9': [], '≥ 0.9': []}
            for m, l in land.items():
                if l['cohort'] != co or m not in facts or facts[m].get('multi') == '1':
                    continue
                try:
                    v = float(l['nd600_1500'])
                except (TypeError, ValueError):
                    continue
                G['< 0.7' if v < 0.7 else ('0.7–0.9' if v < 0.9 else '≥ 0.9')].append(facts[m])
            for k, L in G.items():
                if not L:
                    continue
                n = lambda key: sum(int(float(r[key] or 0)) for r in L)
                sq = n('squad')
                print(f"   {co} {k}：{len(L)} 局 {sq} 个席位；1500 拍前有 leave 的 {n('left1500')} 个（{100 * n('left1500') / sq:.1f}%，{sum(1 for r in L if int(float(r['left1500'] or 0)) > 0)} 局），"
                      f"2500 拍前 {n('left2500')} 个（{100 * n('left2500') / sq:.1f}%）")


if __name__ == '__main__':
    main()
