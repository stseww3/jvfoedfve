#!/usr/bin/env python3
"""page_speed.py — 各号页面的本地拍落后服务器多少、页面跑得有多快（只用对局包，不需要重演）。

依据：
  in_game.log 没有墙上时间，但行的先后 = 写入先后；RESULT 行在 results.csv 里有 at / seconds。
  所以每条 RESULT 行是一个时间锚点：写在它前面的 HL-TICK 行，写入时刻不晚于它的 at。
  “正常的钟”取 tick_clock.py 对全数据集非 left 行的拟合：seconds = a + b × tick（服务器拍 ↔ 开局后的秒数）。
用法: python3 page_speed.py <matchId> [--ref 600]
  --ref T  认为本地拍 T 时页面还没有落后（延迟曲线上 T 之前的落地延迟正常），从这一拍起算平均速度。默认 600。
输出：
  1. 每个 RESULT 锚点一行：at、seconds、这一秒服务器按正常的钟在第几拍；
     每个号此前最后一条 HL-TICK 的本地拍 t（页面此刻的本地拍在 [t, t+90) 里；之后再没有 HL-TICK 的号只知道 ≥ t）。
  2. 第一条 RESULT 时刻：每个号落后服务器多少拍 / 多少秒（区间），从 --ref 拍到此刻的平均速度（拍/秒，占正常速度的百分比）。
  3. 日志里的 [HL-SLOW-TICK] 行：条数、本地拍范围、耗时范围；HL-TICK 的 avgMs 在 --ref 拍与最后一行的值。
"""
import csv, os, re, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_clock  # noqa: E402

DATA = '/agent/repos/c136-data/bundles'


def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    ref = int(argv[argv.index('--ref') + 1]) if '--ref' in argv else 600
    a, b, _, _ = tick_clock.fit()
    res = list(csv.DictReader(open(os.path.join(DATA, mid, 'results.csv'))))
    t_base = min(ts(r['at']) - float(r['seconds']) for r in res)
    res_by = {r['bot']: r for r in res}

    pat_tick = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-TICK\] t=(\d+).*?avgMs=([\d.]+) maxMs=([\d.]+)')
    pat_slow = re.compile(r'^(\d+)\t\[([^\]]+)\] \[HL-SLOW-TICK\] t=(\d+) took ([\d.]+)ms')
    pat_res = re.compile(r'^(\d+)\t\[RESULT (?:\[[^\]]*\] )?([^\]]+)\]')
    pat_init = re.compile(r'^\d+\t\[([^\]\s]+)\] \[HL-(?:GAME-INIT|SPAWN|SPAWN-BACKEND|TICK|OPENING)\]')
    seq, bots, slow, avg_at = [], [], [], {}
    for i, line in enumerate(open(os.path.join(DATA, mid, 'in_game.log'), errors='replace')):
        m = pat_init.search(line)
        if m and m.group(1) not in bots:
            bots.append(m.group(1))
        m = pat_tick.match(line)
        if m:
            seq.append((i, 'T', m.group(2), int(m.group(3))))
            avg_at.setdefault(m.group(2), []).append((int(m.group(3)), float(m.group(4)), float(m.group(5))))
            continue
        m = pat_slow.match(line)
        if m:
            slow.append((m.group(2), int(m.group(3)), float(m.group(4))))
            continue
        m = pat_res.match(line)
        if m and m.group(2).strip() in res_by:
            seq.append((i, 'R', m.group(2).strip(), -1))

    last_line = {}
    for i, k, bot, t in seq:
        if k == 'T':
            last_line[bot] = t
    anchors = [(i, bot) for i, k, bot, t in seq if k == 'R']
    print(f'== {mid} 页面本地拍对服务器拍：正常的钟 seconds = {a:.1f} + {b * 1000:.2f} 毫秒 × tick；正常速度 {1 / b:.2f} 拍/秒')
    print('   每个 RESULT 锚点：at | 开局后秒数 | 这一秒服务器在第几拍（正常的钟）| 各号此前最后一条 HL-TICK 的本地拍（* = 这是该号日志的最后一条 HL-TICK；R = 该号的 RESULT 已写）')
    first = None
    for ai, abot in anchors:
        r = res_by[abot]
        sec = ts(r['at']) - t_base
        srv = (sec - a) / b
        cur, done = {}, set()
        for i, k, bot, t in seq:
            if i >= ai:
                break
            if k == 'T':
                cur[bot] = t
            else:
                done.add(bot)
        cells = []
        for bt in bots:
            if bt not in cur:
                cells.append(f'{bt} -')
                continue
            mark = ('*' if cur[bt] == last_line.get(bt) else '') + ('R' if bt in done else '')
            cells.append(f'{bt} {cur[bt]}{mark}')
        print(f"   {abot:8s} {r['at'][11:23]} | {sec:6.1f} | {srv:6.0f} | " + '  '.join(cells))
        if first is None:
            first = (sec, srv, cur)

    if first:
        sec, srv, cur = first
        t_ref = a + b * ref
        print(f'== 第一条 RESULT 时刻（开局后 {sec:.1f} 秒，服务器约 {srv:.0f} 拍）：各号落后多少；从本地 {ref} 拍（正常的钟第 {t_ref:.1f} 秒）到此刻 {sec - t_ref:.1f} 秒里的平均速度')
        print('   号 | 本地拍区间 | 落后 拍 | 落后 秒 | 平均速度 拍/秒 | 占正常速度')
        lo_all, hi_all = [], []
        for bt in bots:
            if bt not in cur:
                continue
            t = cur[bt]
            # 此号在第一条 RESULT 之后还有没有更晚的 HL-TICK：有 → 此刻 < 下一条的拍号；没有 → 上界未知，按 t+90 报并标注
            later = [tt for i, k, bb, tt in seq if k == 'T' and bb == bt and tt > t]
            hi = t + 90
            note = '' if later else '（之后再没有 HL-TICK，上界按 +90 估）'
            lag_lo, lag_hi = srv - hi, srv - t
            v_lo, v_hi = (t - ref) / (sec - t_ref), (hi - ref) / (sec - t_ref)
            lo_all.append(v_lo); hi_all.append(v_hi)
            print(f'   {bt:8s} | [{t}, {hi}) | {lag_lo:.0f}–{lag_hi:.0f} | {lag_lo * b:.1f}–{lag_hi * b:.1f} | {v_lo:.1f}–{v_hi:.1f} | {100 * v_lo * b:.0f}–{100 * v_hi * b:.0f}%{note}')
        if lo_all:
            print(f'   全队：平均速度 {min(lo_all):.1f}–{max(hi_all):.1f} 拍/秒，占正常速度 {100 * min(lo_all) * b:.0f}–{100 * max(hi_all) * b:.0f}%')

    print(f'== [HL-SLOW-TICK]（策略单次决策超过阈值的拍）：{len(slow)} 条')
    if slow:
        tt = [s[1] for s in slow]; ms = [s[2] for s in slow]
        per = {}
        for bt, t, m_ in slow:
            per.setdefault(bt, []).append(t)
        print(f'   本地拍 {min(tt)}–{max(tt)}，耗时 {min(ms):.1f}–{max(ms):.1f} 毫秒；各号：' + '  '.join(f'{k} {len(v)} 条（{min(v)}–{max(v)}）' for k, v in per.items()))
    print(f'== HL-TICK 的 avgMs（策略单次决策平均耗时，开局以来累计）：本地 {ref} 拍前最后一行 → 日志最后一行；maxMs 同')
    for bt in bots:
        xs = avg_at.get(bt, [])
        if not xs:
            continue
        pre = [x for x in xs if x[0] <= ref]
        p = pre[-1] if pre else xs[0]
        q = xs[-1]
        print(f'   {bt:8s} t={p[0]} avgMs={p[1]} maxMs={p[2]} → t={q[0]} avgMs={q[1]} maxMs={q[2]}')


if __name__ == '__main__':
    main()
