#!/usr/bin/env python3
"""m6_all_pages.py — 全量机械计数（123 个对局包，只读 results.csv 和 in_game.log，不重演）：
每一局里编队各号的页面落后服务器多少拍、8500 拍前离场（RESULT event=left）几个号。对应模式 IO01（页面掉队）、EG02/EG03（被移出对局）。

做法（和单局的 page_speed.py 同一套）：
  * in_game.log 没有墙上时间，但行的先后 = 写入先后；RESULT 行在 results.csv 里有 at / seconds。
    每条 RESULT 行是一个时间锚点：写在它前面的 HL-TICK 行，写入时刻不晚于它的 at。
  * “正常的钟”取 tick_clock.py 对全量非 left 行的拟合 seconds = a + b×tick（服务器拍 ↔ 开局后的秒数）。
  * 在每个锚点：服务器拍 srv = (seconds − a) / b；每个“此后还有 HL-TICK”的号（页面还在跑、也还没写自己的 RESULT），
    它此前最后一条 HL-TICK 的本地拍是 t，页面此刻的本地拍在 [t, t+90) 里，落后 = srv − (t+45)（±45 拍）。
    锚点之后再没有 HL-TICK 的号：只知道本地拍 ≥ t；它如果随后写的是 left，记为“停住的页面”，落后按 srv − t 的上界另列，不进中位数。
  * 一局的指标：
      lag1      第一条 RESULT 时刻，还在跑的各号落后拍数的中位（负数 = 钟的误差范围内没有落后）
      lagPeak   所有锚点里“还在跑的各号落后中位”的最大值，以及它出现在服务器第几拍
      slow1     第一条 RESULT 时刻落后 ≥ --lag 拍（默认 180 = 两个快照）的号数 / 当时有 HL-TICK 的号数
      left<8500 results.csv 里 event=left 且 tick < 8500 的行数；leftEarly = 其中 tick < 2500 的行数
      rows      results.csv 的行数（有 RESULT 的号数）；bots = 日志里出现过的号数
用法：python3 scripts/m6_all_pages.py [局号 ...] [--lag 180] [--csv]
      不给局号 = 全部对局包；--csv 写 out/_all/pages.csv。末尾按 编队 × 是否掉队 汇总输赢。
说明：锚点只在有 RESULT 行的时刻存在。页面掉队之后又追平、其间没有任何号写 RESULT 的局，这个脚本看不到（要用录像做漏斗，见 m6_all_replay.py）。
"""
import csv, datetime, json, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tick_clock  # noqa: E402
import m6_match_split  # noqa: E402

DATA = '/agent/repos/c136-data/bundles'
PAT_TICK = re.compile(r'^\d+\t\[([^\]]+)\] \[HL-TICK\] t=(\d+)')
PAT_RES = re.compile(r'^\d+\t\[RESULT (?:\[[^\]]*\] )?([^\]]+)\]')
PAT_ANY = re.compile(r'^\d+\t\[([^\]]+)\] \[HL-(?:GAME-INIT|SPAWN|SPAWN-BACKEND|TICK|OPENING)\]')


def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def one(mid, a, b, lag_min):
    card = json.load(open(os.path.join(DATA, mid, 'card.json')))
    rp = os.path.join(DATA, mid, 'results.csv')
    lp = os.path.join(DATA, mid, 'in_game.log')
    if not (os.path.exists(rp) and os.path.exists(lp)):
        return None
    res = list(csv.DictReader(open(rp)))
    if not res:
        return None
    t_base = min(ts(r['at']) - float(r['seconds']) for r in res)
    res_by = {r['bot']: r for r in res}
    seq, bots = [], []
    for i, line in enumerate(open(lp, errors='replace')):
        m = PAT_ANY.search(line)
        if m and m.group(1) not in bots:
            bots.append(m.group(1))
        m = PAT_TICK.match(line)
        if m:
            seq.append((i, 'T', m.group(1), int(m.group(2))))
            continue
        m = PAT_RES.match(line)
        if m and m.group(1).strip() in res_by:
            seq.append((i, 'R', m.group(1).strip(), -1))
    # 每个号的 HL-TICK 行号列表，用来判断“锚点之后还有没有 HL-TICK”
    tick_lines = {}
    for i, k, bot, t in seq:
        if k == 'T':
            tick_lines.setdefault(bot, []).append((i, t))
    anchors = [(i, bot) for i, k, bot, t in seq if k == 'R']
    out = {'mid': mid, 'cohort': card['cohort'], 'result': card['outcome']['resultLabel'], 'won': int(bool(card['outcome']['primaryTeamWon'])),
           'endTick': card['outcome']['endTick'], 'rows': len(res), 'bots': len(bots),
           'left': sum(1 for r in res if r['event'] == 'left' and float(r['tick']) < 8500),
           'leftEarly': sum(1 for r in res if r['event'] == 'left' and float(r['tick']) < 2500),
           'lag1': None, 'srv1': None, 'slow1': None, 'n1': None, 'stalled1': None, 'lagPeak': None, 'srvPeak': None, 'anchors': len(anchors)}
    done = set()
    first = True
    for ai, abot in anchors:
        r = res_by[abot]
        sec = ts(r['at']) - t_base
        srv = (sec - a) / b
        lags, stalled = [], 0
        for bot, L in tick_lines.items():
            if bot in done or bot == abot:
                continue
            before = [t for i, t in L if i < ai]
            after = [t for i, t in L if i > ai]
            if not before:
                continue
            if after:
                lags.append(srv - (before[-1] + 45))
            elif res_by.get(bot, {}).get('event') == 'left':
                stalled += 1
        done.add(abot)
        if first:
            first = False
            out['srv1'] = round(srv)
            out['n1'] = len(lags)
            out['stalled1'] = stalled
            if lags:
                out['lag1'] = round(statistics.median(lags))
                out['slow1'] = sum(1 for x in lags if x >= lag_min)
        if len(lags) >= 2:
            med = statistics.median(lags)
            if out['lagPeak'] is None or med > out['lagPeak']:
                out['lagPeak'] = round(med)
                out['srvPeak'] = round(srv)
    return out


def main():
    argv = sys.argv[1:]
    lag_min = float(argv[argv.index('--lag') + 1]) if '--lag' in argv else 180.0
    mids = [x for x in argv if not x.startswith('--') and x != str(int(lag_min))] or sorted(os.listdir(DATA))
    a, b, _, _ = tick_clock.fit()
    rows = [r for r in (one(m, a, b, lag_min) for m in mids) if r]
    # 不是同一场对局的包（m6_match_split.py）：各页面的开局时刻不同，“落后”是两场的开局时差，不是掉队。列出但不进汇总。
    split = m6_match_split.load_split()
    for r in rows:
        r['split'] = split.get(r['mid'], '')
    print(f'# 正常的钟 seconds = {a:.1f} + {1000 * b:.2f} 毫秒 × tick；落后 ≥ {lag_min:.0f} 拍算掉队。lag 的分辨率 ±45 拍（HL-TICK 每 90 拍一行）')
    print('局 | 编队 | 结果 | RESULT 行/号数 | 8500 拍前 left（其中 2500 拍前）| 第一条 RESULT：服务器拍 / 在跑的号落后中位 / 掉队号数 / 已停住的页面 | 落后中位的峰值@服务器拍')
    for r in rows:
        f = lambda x: '-' if x is None else str(x)
        print(f"{r['mid']} | {r['cohort']}{'（不是同一场）' if r['split'] else ''} | {r['result']} | {r['rows']}/{r['bots']} | {r['left']}（{r['leftEarly']}）| {f(r['srv1'])} / {f(r['lag1'])} / {f(r['slow1'])}/{f(r['n1'])} / {f(r['stalled1'])} | {f(r['lagPeak'])}@{f(r['srvPeak'])}")
    if '--csv' in argv:
        od = os.path.join(HERE, '..', 'out', '_all')
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'pages.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/pages.csv（{len(rows)} 局）')
    # 汇总：一局算“掉队局” = 落后中位的峰值 ≥ lag_min，或第一条 RESULT 时已有停住的页面，或 2500 拍前有 ≥3 个号 left
    def lagged(r):
        return (r['lagPeak'] is not None and r['lagPeak'] >= lag_min) or (r['stalled1'] or 0) >= 1 or r['leftEarly'] >= 3
    nx = [r['mid'] for r in rows if r['split']]
    rows = [r for r in rows if not r['split']]
    print(f"# 汇总（掉队局 = 落后中位峰值 ≥ {lag_min:.0f} 拍，或第一条 RESULT 时已有停住的页面，或 2500 拍前 ≥3 个号 left）；不是同一场对局的 {len(nx)} 个包不计：{' '.join(nx)}")
    for co in sorted({r['cohort'] for r in rows}):
        for flag in (True, False):
            L = [r for r in rows if r['cohort'] == co and lagged(r) == flag]
            if not L:
                continue
            won = sum(r['won'] for r in L)
            print(f"#   {co} {'掉队局' if flag else '没看到掉队'}：{len(L)} 局，主队赢 {won} 局（{100 * won / len(L):.0f}%），8500 拍前 left 行合计 {sum(r['left'] for r in L)}，"
                  f"每局 RESULT 行中位 {statistics.median(r['rows'] for r in L):.0f}")
    L1 = [r for r in rows if lagged(r)]
    L0 = [r for r in rows if not lagged(r)]
    for name, L in (('掉队局', L1), ('没看到掉队', L0)):
        if L:
            print(f"#   全部 {name}：{len(L)} 局，主队赢 {sum(r['won'] for r in L)} 局（{100 * sum(r['won'] for r in L) / len(L):.0f}%）；"
                  f"结果标签：" + '、'.join(f'{k} {v}' for k, v in sorted({x: sum(1 for r in L if r['result'] == x) for x in {r['result'] for r in L}}.items())))


if __name__ == '__main__':
    main()
