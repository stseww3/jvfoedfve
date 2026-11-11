#!/usr/bin/env python3
# 内置 AI 和我方号之间的地：某一段里内置 AI 从我方各号身上拿走多少格、我方从内置 AI 身上拿到多少格；
# 可以指定一个 AI，按每 150 拍一段列出它和某个我方号之间的来回，以及那个号当时的领土 / 余额。
# 用法：python3 scripts/ai_nibble.py <局号> t0 t1 [--ai 编号 --bot 我方号的引擎编号] [--bin 150]
# 数据：tmp/truth/<局号>/flow.tsv（只有涉及我方队伍的换手）、state.tsv、meta.json；
#       tmp/truth/<局号>/ai_life.tsv 有的话顺带给出这个 AI 的领土峰值和出局拍（ai_life.mjs）。
import csv
import os
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from match_digest import Match  # noqa: E402


def opt(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) < 3:
        print('用法：ai_nibble.py <局号> t0 t1 [--ai 编号 --bot 我方号的引擎编号] [--bin 150]')
        sys.exit(1)
    mid, t0, t1 = a[0], int(a[1]), int(a[2])
    M = Match(mid)
    nh = len(M.team) if hasattr(M, 'team') else 0
    humans = {p for p in M.team} if hasattr(M, 'team') else set()
    rows = []
    for r in list(csv.reader(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'flow.tsv'), encoding='utf8'), delimiter='\t'))[1:]:
        rows.append((int(r[0]), int(r[1]), int(r[2]), int(r[3])))

    def is_ai(p):
        return p != 512 and p not in humans

    lost, got = Counter(), Counter()
    by_ai_lost, by_ai_got = Counter(), Counter()
    for t, frm, to, n in rows:
        if not (t0 <= t < t1):
            continue
        if frm in M.ours and is_ai(to):
            lost[M.nm(frm)] += n
            by_ai_lost[(to, M.nm(frm))] += n
        if to in M.ours and is_ai(frm):
            got[M.nm(to)] += n
            by_ai_got[(frm, M.nm(to))] += n
    print('# %s 拍段 [%d,%d)：内置 AI 与我方号之间换手的地（格）' % (mid, t0, t1))
    print('  内置 AI 从我方拿走：%s；合计 %d' % ('，'.join('%s %d' % kv for kv in lost.most_common()) or '无', sum(lost.values())))
    print('  我方从内置 AI 拿到：%s；合计 %d' % ('，'.join('%s %d' % kv for kv in got.most_common()) or '无', sum(got.values())))
    print('  从我方拿地最多的几个内置 AI（AI 编号 ← 我方号：被拿走 / 同期这个号从它身上拿回）：')
    for (ai, b), n in by_ai_lost.most_common(6):
        print('    AI#%d ← %s：%d / %d' % (ai, b, n, by_ai_got.get((ai, b), 0)))
    ai = opt('--ai')
    bot = opt('--bot')
    if ai is None or bot is None:
        return
    ai, bot = int(ai), int(bot)
    step = int(opt('--bin', 150))
    life = {}
    lp = os.path.join(ROOT, 'tmp', 'truth', mid, 'ai_life.tsv')
    if os.path.exists(lp):
        for r in csv.DictReader(open(lp, encoding='utf8'), delimiter='\t'):
            life[int(r['p'])] = r
    if ai in life:
        r = life[ai]
        print('  AI#%d：领土峰值 %s（拍 %s），出局拍 %s' % (ai, r['peak'], r['peakTick'], r['dead']))
    b = defaultdict(lambda: [0, 0])
    for t, frm, to, n in rows:
        if not (t0 <= t < t1):
            continue
        if frm == bot and to == ai:
            b[(t - t0) // step][0] += n
        if frm == ai and to == bot:
            b[(t - t0) // step][1] += n
    tot0 = tot1 = 0
    for kk in sorted(b):
        s = t0 + kk * step
        st = M.state[M.at(s)].get(bot)
        tot0 += b[kk][0]
        tot1 += b[kk][1]
        print('    拍 %5d~%5d：AI#%d 从 %s 拿走 %4d 格，%s 从它拿回 %4d 格 ｜ 段首 %s 领土 %s、余额 %s（密度 %.0f）'
              % (s, s + step - 1, ai, M.nm(bot), b[kk][0], M.nm(bot), b[kk][1], M.nm(bot),
                 st[0] if st else '-', st[1] if st else '-', (st[1] / max(1, st[0])) if st else 0))
    print('    合计：AI#%d 从 %s 拿走 %d 格，%s 从它拿回 %d 格' % (ai, M.nm(bot), tot0, M.nm(bot), tot1))


if __name__ == '__main__':
    main()
