#!/usr/bin/env python3
# logonly_bots.py — 对局包里「有日志、但不在这份录像里」的号（A015：同一支编队被分进两局，录像只有其中一局）。
# 只用对局包里的 results.csv / traj.csv / events.csv / in_game.log，不重放。
# 用法：python3 scripts/logonly_bots.py <局号> [--ticks 630,1080,1530,2250,3060]
# 输出：
#   1) 按「开局时刻 = 结果行的 at − seconds」把号分组（同一局的号开局时刻相同），连同 [HL-SPAWN] 行里的 squad=N、meId；
#   2) 不在录像里的号逐个：后端选点、几个时间点的 领土/余额/密度/邻居数、峰值、结果行；
#   3) 领土不动的最长一段（期间发令数还在涨的话一并标出）、相邻两个快照之间余额掉 ≥30% 的次数；
#   4) 调度次数（events.csv 的 DISPATCH 行）和 likelyRejected 的次数；结果行里的队伍领土合计。
import sys
sys.dont_write_bytecode = True
import os, csv, json, re, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = '/agent/repos/c136-data/bundles'


def fmt(x):
    x = float(x)
    if abs(x) >= 1e6:
        return '%.2fM' % (x / 1e6)
    if abs(x) >= 1e4:
        return '%.1fk' % (x / 1e3)
    return '%d' % x


def main():
    a = sys.argv[1:]
    mid = a[0]
    ticks = [int(x) for x in a[a.index('--ticks') + 1].split(',')] if '--ticks' in a else [630, 1080, 1530, 2250, 3060]
    b = os.path.join(DATA, mid)
    meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    in_replay = set(meta['ours'].values()) if isinstance(meta['ours'], dict) else set()
    land = meta['info']['ke']
    res = list(csv.DictReader(open(os.path.join(b, 'results.csv'), encoding='utf8')))
    traj = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(b, 'traj.csv'), encoding='utf8')):
        traj[r['bot']].append((int(r['t']), int(r['terr']), int(float(r['bal'])), int(r['nb']), int(r['neut']), int(r['cmds']), int(r['boats'])))
    for k in traj:
        traj[k].sort()
    disp = collections.defaultdict(lambda: [0, 0])
    recv = collections.Counter()
    for r in csv.DictReader(open(os.path.join(b, 'events.csv'), encoding='utf8')):
        if r['type'] == 'DISPATCH':
            disp[r['bot']][0] += 1
            if r['likelyRejected'] == 'True':
                disp[r['bot']][1] += 1
            recv[(r['bot'], r['targetName'])] += 1
    squadn = {}
    backend = {}
    with open(os.path.join(b, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for line in f:
            m = re.search(r'\[(\w+)\] \[HL-SPAWN\] me=(\d+) slot=\d+ \(squad=(\d+)', line)
            if m:
                squadn[m.group(1)] = int(m.group(3))
            m = re.search(r'\[(\w+)\] \[HL-SPAWN-BACKEND\] me=\d+ slot=\d+ role=(\w+) -> \((\d+),(\d+)\)', line)
            if m:
                backend[m.group(1)] = (m.group(2), int(m.group(3)), int(m.group(4)))
    # 1) 分组
    groups = collections.defaultdict(list)
    for r in res:
        at = datetime.datetime.fromisoformat(r['at'].replace('Z', '+00:00'))
        st = at - datetime.timedelta(seconds=int(r['seconds']))
        groups[round(st.timestamp() / 8)].append((r, st))
    print('# %s：按开局时刻（结果行 at − seconds）分组，共 %d 组' % (mid, len(groups)))
    for gi, k in enumerate(sorted(groups)):
        g = groups[k]
        sts = sorted(x[1] for x in g)
        names = [x[0]['bot'] for x in g]
        print('  第 %d 组：开局约 %s（最早最晚差 %.1f 秒），%d 个号：%s' % (
            gi + 1, sts[0].strftime('%H:%M:%S'), (sts[-1] - sts[0]).total_seconds(), len(g),
            '、'.join('%s(me=%s%s%s)' % (x[0]['bot'], x[0]['meId'],
                                       '，本地 squad=%d' % squadn[x[0]['bot']] if x[0]['bot'] in squadn else '',
                                       '，在录像里' if x[0]['bot'] in in_replay else '，不在录像里') for x in g)))
        last = max(g, key=lambda x: int(x[0]['tick']))[0]
        rate = max(int(x[0]['tick']) / max(1, int(x[0]['seconds'])) for x in g)
        print('    最后一条结果：%s 拍 %s（%s 秒，约每秒 %.1f 拍），队伍领土合计 %s' % (last['bot'], last['tick'], last['seconds'], rate, last['teamTotals'] or '（无）'))
    if len(groups) >= 2:
        ks = sorted(groups)
        d = (min(x[1] for x in groups[ks[1]]) - min(x[1] for x in groups[ks[0]])).total_seconds()
        print('  两组开局相差约 %.0f 秒' % d)
    # 2) 逐号
    out = [r for r in res if r['bot'] not in in_replay]
    print('# 不在录像里的号 %d 个（以下拍号是各自客户端的本地拍号）' % len(out))
    for r in sorted(out, key=lambda r: int(r['tick'])):
        bot = r['bot']
        tr = traj.get(bot, [])
        bk = backend.get(bot)
        print('  %s（me=%s）：后端选点 %s；结果 %s 拍 %s（第 %s 名，当时在场 %s 人），峰值领土 %s（%.1f%%），最后领土 %s，发令 %s / 受理 %s；调度 %d 次（疑似没落地 %d）' % (
            bot, r['meId'], ('(%d,%d) %s' % (bk[1], bk[2], bk[0])) if bk else '无', r['event'], r['tick'], r['place'], r['alivePlayers'],
            r['peak'], 100.0 * int(r['peak']) / land, r['lastTerritory'], r['sent'], r['accepted'], disp[bot][0], disp[bot][1]))
        pts = []
        for t in ticks:
            c = [x for x in tr if abs(x[0] - t) <= 45]
            if c:
                x = min(c, key=lambda x: abs(x[0] - t))
                pts.append('%d：%d 格 / %s / 密度 %.1f / 邻居 %d' % (x[0], x[1], fmt(x[2]), x[2] / max(1, x[1]), x[3]))
        if pts:
            print('    ' + '；'.join(pts))
        # 3) 领土不动的最长一段
        best = None
        i = 0
        while i < len(tr):
            j = i
            while j + 1 < len(tr) and tr[j + 1][1] > 0 and abs(tr[j + 1][1] - tr[i][1]) <= max(30, 0.01 * tr[i][1]):
                j += 1
            if j > i and tr[i][0] >= 630:
                span = tr[j][0] - tr[i][0]
                if best is None or span > best[0]:
                    best = (span, i, j)
            i = max(j, i + 1)
        if best and best[0] >= 450:
            _, i, j = best
            print('    领土不动最长的一段：%d~%d 拍（%d 拍）领土 %d，余额 %s→%s（密度 %.1f→%.1f），邻居数 %d→%d，期间发令数 +%d、发船数 +%d' % (
                tr[i][0], tr[j][0], tr[j][0] - tr[i][0], tr[i][1], fmt(tr[i][2]), fmt(tr[j][2]),
                tr[i][2] / max(1, tr[i][1]), tr[j][2] / max(1, tr[j][1]), tr[i][3], tr[j][3], tr[j][5] - tr[i][5], tr[j][6] - tr[i][6]))
        drops = []
        for k in range(1, len(tr)):
            if tr[k - 1][2] >= 20000 and tr[k][2] <= 0.7 * tr[k - 1][2]:
                drops.append((tr[k - 1][0], tr[k][0], tr[k - 1][2], tr[k][2], tr[k][1] - tr[k - 1][1]))
        if drops:
            print('    相邻快照余额掉 ≥30%% 的 %d 次：%s' % (len(drops), '；'.join('%d→%d 拍 %s→%s（领土 %+d）' % (d[0], d[1], fmt(d[2]), fmt(d[3]), d[4]) for d in drops[:6])))
        pk = max(tr, key=lambda x: x[1]) if tr else None
        if pk:
            after = [x for x in tr if x[0] > pk[0]]
            print('    峰值在 %d 拍（%d 格、%s）；此后最后一个快照 %s' % (pk[0], pk[1], fmt(pk[2]),
                  ('%d 拍 %d 格 / %s' % (after[-1][0], after[-1][1], fmt(after[-1][2]))) if after else '—'))
        rc = ['%s×%d' % (k[1], v) for k, v in recv.items() if k[0] == bot]
        if rc:
            print('    调度对象：' + '、'.join(rc))
    # 4) 那一局的队伍领土（来自各号的结果行）
    print('# 结果行里的队伍领土合计（各号出局 / 结束那一刻自己客户端看到的）')
    for r in sorted(res, key=lambda r: (r['bot'] in in_replay, int(r['tick']))):
        if not r['teamTotals']:
            continue
        try:
            tt = json.loads(r['teamTotals'])
        except Exception:
            continue
        tot = sum(tt.values())
        print('  %s %s 拍（%s）：%s' % (r['bot'], r['tick'], '在录像里' if r['bot'] in in_replay else '不在录像里',
              '，'.join('队%s %d（%.1f%%）' % (k, v, 100.0 * v / land) for k, v in sorted(tt.items()))))


if __name__ == '__main__':
    main()
